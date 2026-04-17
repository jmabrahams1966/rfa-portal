"""
Claimant Attorney Intelligence Service for RFA-2 Portal.

Builds attorney profiles from filing history, ranks attorneys by difficulty,
generates AI-powered counter-arguments, and predicts attorney responses.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional
from collections import Counter

import boto3
from botocore.config import Config as BotoConfig
from sqlalchemy import select, and_, func, case, extract
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, Index

from app.config import get_settings
from app.database import Base
from app.models.models import RFASubmission, RFACase

logger = logging.getLogger(__name__)

DECIDED_STATUSES = ("accepted", "rejected")


# ---------------------------------------------------------------------------
# New Model: RFAAttorneyProfile
# ---------------------------------------------------------------------------
class RFAAttorneyProfile(Base):
    __tablename__ = "rfa_attorney_profiles"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attorney_name = Column(String(255), unique=True, nullable=False)
    total_cases = Column(Integer, nullable=False, default=0)
    objection_rate = Column(Float, nullable=True)
    settlement_rate = Column(Float, nullable=True)
    avg_days_to_resolution = Column(Float, nullable=True)
    common_objections = Column(JSON, nullable=True)  # JSON array of common objection strings
    districts_active = Column(JSON, nullable=True)   # JSON array of district names
    last_updated = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_rfa_attorney_profiles_name", "attorney_name"),
    )


# ---------------------------------------------------------------------------
# Bedrock client helper
# ---------------------------------------------------------------------------
def _get_bedrock_client():
    """Create a Bedrock Runtime client."""
    settings = get_settings()
    kwargs: dict[str, Any] = {
        "region_name": settings.bedrock_region,
        "config": BotoConfig(
            retries={"max_attempts": 3, "mode": "adaptive"},
            read_timeout=120,
        ),
    }
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    return boto3.client("bedrock-runtime", **kwargs)


def _invoke_claude(system: str, user_message: str) -> str:
    """Send a message to Claude via Bedrock and return the assistant text."""
    settings = get_settings()
    client = _get_bedrock_client()

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "temperature": 0.2,
        "system": system,
        "messages": [{"role": "user", "content": user_message}],
    })

    response = client.invoke_model(
        modelId=settings.bedrock_model_id,
        contentType="application/json",
        accept="application/json",
        body=body,
    )
    response_body = json.loads(response["body"].read())
    text = response_body["content"][0]["text"].strip()

    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    return text.strip()


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

async def get_attorney_profile(
    attorney_name: str,
    db: AsyncSession,
) -> dict:
    """
    Build a comprehensive profile from all filings involving this attorney.

    Analyzes total cases, objection rate, settlement rate, response patterns,
    common objection grounds, and district performance.
    """
    # Fetch all submissions linked to cases with this attorney
    q = (
        select(
            RFASubmission.id,
            RFASubmission.wcb_status,
            RFASubmission.status,
            RFASubmission.reason_codes,
            RFASubmission.wcb_errors,
            RFASubmission.form_data,
            RFASubmission.submitted_at,
            RFASubmission.updated_at,
            RFACase.district,
        )
        .join(RFACase, RFASubmission.case_id == RFACase.id)
        .where(RFACase.claimant_rep_name == attorney_name)
        .order_by(RFASubmission.created_at.desc())
    )
    result = await db.execute(q)
    rows = result.all()

    if not rows:
        return {
            "attorney_name": attorney_name,
            "total_cases": 0,
            "objection_rate": 0.0,
            "settlement_rate": 0.0,
            "avg_days_to_resolution": 0.0,
            "top_reason_codes": [],
            "response_pattern": "unknown",
            "common_objections": [],
            "district_performance": [],
            "found": False,
        }

    total_cases = len(rows)
    objection_count = 0
    settlement_count = 0
    resolution_days = []
    reason_counter: Counter = Counter()
    objection_grounds: list[str] = []
    district_stats: dict[str, dict[str, int]] = {}

    for row in rows:
        # Count objections (rejected by WCB or form_data indicates objection)
        form_data = row.form_data or {}
        has_objection = form_data.get("attorney_objected", False)
        if has_objection or row.wcb_status == "rejected":
            objection_count += 1

        # Count settlements
        if form_data.get("settled", False) or row.status == "settled":
            settlement_count += 1

        # Resolution time
        if row.submitted_at and row.updated_at and row.wcb_status in DECIDED_STATUSES:
            delta = (row.updated_at - row.submitted_at).total_seconds() / 86400
            if delta > 0:
                resolution_days.append(delta)

        # Reason codes
        codes = row.reason_codes if isinstance(row.reason_codes, list) else []
        for c in codes:
            cc = c if isinstance(c, str) else (c.get("code") if isinstance(c, dict) else str(c))
            reason_counter[cc] += 1

        # Objection grounds from wcb_errors or form_data
        if row.wcb_errors:
            errors = row.wcb_errors if isinstance(row.wcb_errors, list) else [row.wcb_errors]
            for err in errors:
                ground = err if isinstance(err, str) else (err.get("reason", str(err)) if isinstance(err, dict) else str(err))
                objection_grounds.append(ground)

        objection_text = form_data.get("objection_grounds")
        if objection_text:
            if isinstance(objection_text, list):
                objection_grounds.extend(objection_text)
            else:
                objection_grounds.append(str(objection_text))

        # District stats
        district = row.district or "Unknown"
        if district not in district_stats:
            district_stats[district] = {"total": 0, "accepted": 0, "rejected": 0}
        district_stats[district]["total"] += 1
        if row.wcb_status == "accepted":
            district_stats[district]["accepted"] += 1
        elif row.wcb_status == "rejected":
            district_stats[district]["rejected"] += 1

    objection_rate = round((objection_count / total_cases * 100), 2) if total_cases else 0.0
    settlement_rate = round((settlement_count / total_cases * 100), 2) if total_cases else 0.0
    avg_resolution = round(sum(resolution_days) / len(resolution_days), 1) if resolution_days else 0.0

    # Determine response pattern
    if objection_rate >= 75:
        response_pattern = "always_objects"
    elif objection_rate >= 40:
        response_pattern = "sometimes_objects"
    elif objection_rate >= 10:
        response_pattern = "rarely_objects"
    else:
        response_pattern = "seldom_responds"

    # Top objection grounds
    obj_counter = Counter(objection_grounds)
    top_objections = [{"ground": g, "count": c} for g, c in obj_counter.most_common(10)]

    # District performance
    district_perf = []
    for d, stats in sorted(district_stats.items()):
        favorable = stats["accepted"] > stats["rejected"]
        district_perf.append({
            "district": d,
            "total": stats["total"],
            "accepted": stats["accepted"],
            "rejected": stats["rejected"],
            "favorable": favorable,
        })

    # Update or create the cached profile
    profile_q = select(RFAAttorneyProfile).where(RFAAttorneyProfile.attorney_name == attorney_name)
    profile_result = await db.execute(profile_q)
    profile = profile_result.scalar_one_or_none()

    if profile:
        profile.total_cases = total_cases
        profile.objection_rate = objection_rate
        profile.settlement_rate = settlement_rate
        profile.avg_days_to_resolution = avg_resolution
        profile.common_objections = [o["ground"] for o in top_objections[:5]]
        profile.districts_active = list(district_stats.keys())
        profile.last_updated = datetime.utcnow()
    else:
        profile = RFAAttorneyProfile(
            attorney_name=attorney_name,
            total_cases=total_cases,
            objection_rate=objection_rate,
            settlement_rate=settlement_rate,
            avg_days_to_resolution=avg_resolution,
            common_objections=[o["ground"] for o in top_objections[:5]],
            districts_active=list(district_stats.keys()),
            last_updated=datetime.utcnow(),
        )
        db.add(profile)

    await db.flush()

    return {
        "attorney_name": attorney_name,
        "total_cases": total_cases,
        "objection_rate": objection_rate,
        "settlement_rate": settlement_rate,
        "avg_days_to_resolution": avg_resolution,
        "top_reason_codes": [{"code": c, "count": n} for c, n in reason_counter.most_common(10)],
        "response_pattern": response_pattern,
        "common_objections": top_objections,
        "district_performance": district_perf,
        "found": True,
    }


async def get_attorney_rankings(
    org_id: str,
    db: AsyncSession,
) -> list:
    """
    Rank claimant attorneys by difficulty based on objection rate
    and time to resolve, scoped to the organization's cases.
    """
    q = (
        select(
            RFACase.claimant_rep_name,
            func.count(RFASubmission.id).label("total_filings"),
            func.count(case((RFASubmission.wcb_status == "rejected", 1))).label("rejected_count"),
            func.count(case((RFASubmission.wcb_status.in_(DECIDED_STATUSES), 1))).label("decided"),
            func.avg(
                case(
                    (
                        and_(
                            RFASubmission.submitted_at.isnot(None),
                            RFASubmission.wcb_status.in_(DECIDED_STATUSES),
                        ),
                        extract("epoch", RFASubmission.updated_at) - extract("epoch", RFASubmission.submitted_at),
                    )
                )
            ).label("avg_resolution_seconds"),
        )
        .join(RFACase, RFASubmission.case_id == RFACase.id)
        .where(
            and_(
                RFASubmission.org_id == org_id,
                RFACase.claimant_rep_name.isnot(None),
            )
        )
        .group_by(RFACase.claimant_rep_name)
        .having(func.count(RFASubmission.id) >= 1)
        .order_by(func.count(RFASubmission.id).desc())
    )
    result = await db.execute(q)

    rankings = []
    for r in result.all():
        objection_rate = round((r.rejected_count / r.decided * 100), 2) if r.decided else 0.0
        avg_days = round((r.avg_resolution_seconds or 0) / 86400, 1)

        # Difficulty score: weighted combo of objection rate and resolution time
        difficulty_score = round(objection_rate * 0.6 + min(avg_days, 180) / 180 * 40, 1)

        rankings.append({
            "attorney_name": r.claimant_rep_name,
            "total_filings": r.total_filings,
            "decided": r.decided,
            "rejected": r.rejected_count,
            "objection_rate": objection_rate,
            "avg_resolution_days": avg_days,
            "difficulty_score": difficulty_score,
        })

    # Sort by difficulty score descending
    rankings.sort(key=lambda x: x["difficulty_score"], reverse=True)
    return rankings


async def generate_counter_arguments(
    attorney_name: str,
    reason_code: str,
    db: AsyncSession,
) -> dict:
    """
    Use Claude to generate counter-arguments based on the attorney's
    typical objection patterns for a given reason code.
    """
    # Get attorney profile data
    profile = await get_attorney_profile(attorney_name, db)

    objection_list = profile.get("common_objections", [])
    objection_texts = [o["ground"] if isinstance(o, dict) else str(o) for o in objection_list]

    if not objection_texts:
        objection_texts = [
            "Insufficient medical evidence",
            "Causation not established",
            "Claimant has not reached MMI",
        ]

    system_prompt = (
        "You are a Workers' Compensation defense strategist for NYS WCB RFA-2 filings. "
        "Generate preemptive counter-arguments to anticipated attorney objections. "
        "Reference relevant NYS Workers' Compensation Law sections where applicable. "
        "Respond ONLY with valid JSON."
    )

    user_message = f"""Attorney: {attorney_name}
Reason Code: {reason_code}
Attorney's Objection Rate: {profile.get('objection_rate', 0)}%
Attorney's Response Pattern: {profile.get('response_pattern', 'unknown')}

This attorney typically objects on these grounds:
{chr(10).join(f"- {obj}" for obj in objection_texts)}

Generate preemptive counter-arguments for each objection ground as it relates to reason code {reason_code}.

Return JSON:
{{
  "counter_arguments": [
    {{
      "objection": "The typical objection",
      "counter": "The counter-argument to use",
      "supporting_law": "Relevant WCL section or Board precedent"
    }}
  ],
  "strategy_notes": "Overall strategy recommendation for this attorney"
}}"""

    try:
        response_text = _invoke_claude(system_prompt, user_message)
        result_data = json.loads(response_text)
        return {
            "attorney_name": attorney_name,
            "reason_code": reason_code,
            "counter_arguments": result_data.get("counter_arguments", []),
            "strategy_notes": result_data.get("strategy_notes", ""),
            "attorney_profile_summary": {
                "objection_rate": profile.get("objection_rate", 0),
                "response_pattern": profile.get("response_pattern", "unknown"),
                "total_cases": profile.get("total_cases", 0),
            },
        }
    except json.JSONDecodeError as e:
        logger.error("Failed to parse Claude counter-arguments response: %s", e)
        return {
            "attorney_name": attorney_name,
            "reason_code": reason_code,
            "counter_arguments": [],
            "strategy_notes": "AI analysis unavailable.",
            "error": str(e),
        }
    except Exception as e:
        logger.exception("Counter-argument generation failed")
        return {
            "attorney_name": attorney_name,
            "reason_code": reason_code,
            "counter_arguments": [],
            "strategy_notes": "AI service unavailable.",
            "error": str(e),
        }


async def predict_attorney_response(
    attorney_name: str,
    reason_code: str,
    db: AsyncSession,
) -> dict:
    """
    Predict whether the attorney will object, settle, or not respond,
    based on historical filing data.
    """
    # Get full filing history for this attorney + reason code
    q = (
        select(
            RFASubmission.wcb_status,
            RFASubmission.status,
            RFASubmission.form_data,
            RFASubmission.reason_codes,
        )
        .join(RFACase, RFASubmission.case_id == RFACase.id)
        .where(RFACase.claimant_rep_name == attorney_name)
    )
    result = await db.execute(q)
    rows = result.all()

    # Filter to matching reason code
    matching = []
    all_filings = []
    for row in rows:
        all_filings.append(row)
        codes = row.reason_codes if isinstance(row.reason_codes, list) else []
        for c in codes:
            cc = c if isinstance(c, str) else (c.get("code") if isinstance(c, dict) else str(c))
            if cc == reason_code:
                matching.append(row)
                break

    # Use matching if available, otherwise all filings
    analysis_set = matching if matching else all_filings
    total = len(analysis_set)

    if total == 0:
        return {
            "attorney_name": attorney_name,
            "reason_code": reason_code,
            "prediction": "unknown",
            "confidence": "LOW",
            "probabilities": {
                "object": 0.33,
                "settle": 0.33,
                "no_response": 0.34,
            },
            "basis": "No historical data available for this attorney.",
            "sample_size": 0,
        }

    # Count outcomes
    object_count = 0
    settle_count = 0
    no_response_count = 0

    for row in analysis_set:
        form_data = row.form_data or {}
        objected = form_data.get("attorney_objected", False) or row.wcb_status == "rejected"
        settled = form_data.get("settled", False) or row.status == "settled"
        no_resp = form_data.get("no_response", False)

        if settled:
            settle_count += 1
        elif objected:
            object_count += 1
        elif no_resp or row.wcb_status == "accepted":
            no_response_count += 1
        else:
            # Default unresolved to no_response
            no_response_count += 1

    obj_prob = round(object_count / total, 2) if total else 0.0
    settle_prob = round(settle_count / total, 2) if total else 0.0
    no_resp_prob = round(no_response_count / total, 2) if total else 0.0

    # Normalize probabilities
    prob_sum = obj_prob + settle_prob + no_resp_prob
    if prob_sum > 0:
        obj_prob = round(obj_prob / prob_sum, 2)
        settle_prob = round(settle_prob / prob_sum, 2)
        no_resp_prob = round(1.0 - obj_prob - settle_prob, 2)

    # Determine prediction
    if obj_prob >= settle_prob and obj_prob >= no_resp_prob:
        prediction = "object"
    elif settle_prob >= obj_prob and settle_prob >= no_resp_prob:
        prediction = "settle"
    else:
        prediction = "no_response"

    # Confidence based on sample size and margin
    probs = [obj_prob, settle_prob, no_resp_prob]
    probs.sort(reverse=True)
    margin = probs[0] - probs[1]

    if total >= 10 and margin >= 0.3:
        confidence = "HIGH"
    elif total >= 5 and margin >= 0.15:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    basis = f"Based on {total} historical filings"
    if matching:
        basis += f" ({len(matching)} with reason code {reason_code})"
    else:
        basis += f" (none with reason code {reason_code}; using all filings)"

    return {
        "attorney_name": attorney_name,
        "reason_code": reason_code,
        "prediction": prediction,
        "confidence": confidence,
        "probabilities": {
            "object": obj_prob,
            "settle": settle_prob,
            "no_response": no_resp_prob,
        },
        "basis": basis,
        "sample_size": total,
        "matching_reason_code_count": len(matching),
    }
