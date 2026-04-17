"""
Narrative AI Optimization Service for RFA-2 Portal.

Uses historical accepted filing data and Claude AI to optimize RFA-2
narratives for higher acceptance rates at the WCB.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

import boto3
from botocore.config import Config as BotoConfig
from sqlalchemy import select, and_, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID

from app.config import get_settings
from app.database import Base
from app.models.models import RFASubmission, RFACase

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# New Model: RFANarrativePattern
# ---------------------------------------------------------------------------
class RFANarrativePattern(Base):
    __tablename__ = "rfa_narrative_patterns"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(PG_UUID(as_uuid=True), nullable=True)
    reason_code = Column(String(50), nullable=False)
    district = Column(String(100), nullable=False)
    pattern_text = Column(Text, nullable=False)
    success_count = Column(Integer, nullable=False, default=0)
    failure_count = Column(Integer, nullable=False, default=0)
    effectiveness_rate = Column(Float, nullable=True)
    last_used = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_rfa_narrative_patterns_reason_district", "reason_code", "district"),
        Index("ix_rfa_narrative_patterns_org_id", "org_id"),
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
        "temperature": 0.3,
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

    # Strip markdown fences
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    return text.strip()


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

async def optimize_narrative(
    reason_code: str,
    district: str,
    draft_narrative: str,
    db: AsyncSession,
) -> dict:
    """
    Optimize a draft RFA-2 narrative based on historically accepted filings.

    Queries past accepted filings with the same reason code and district,
    then uses Claude to suggest improvements matching winning patterns.
    """
    # Fetch up to 5 accepted narratives with matching reason code + district
    accepted_q = (
        select(RFASubmission.narrative)
        .join(RFACase, RFASubmission.case_id == RFACase.id)
        .where(
            and_(
                RFASubmission.wcb_status == "accepted",
                RFASubmission.narrative.isnot(None),
                RFACase.district == district,
            )
        )
        .order_by(RFASubmission.updated_at.desc())
        .limit(20)
    )
    result = await db.execute(accepted_q)
    all_narratives = result.scalars().all()

    # Filter to those containing the reason code (stored as JSON array)
    matching_narratives = []
    # We also need to check reason_codes; re-query with reason_codes
    accepted_full_q = (
        select(RFASubmission.narrative, RFASubmission.reason_codes)
        .join(RFACase, RFASubmission.case_id == RFACase.id)
        .where(
            and_(
                RFASubmission.wcb_status == "accepted",
                RFASubmission.narrative.isnot(None),
                RFACase.district == district,
            )
        )
        .order_by(RFASubmission.updated_at.desc())
        .limit(50)
    )
    result = await db.execute(accepted_full_q)
    for row in result.all():
        codes = row.reason_codes if isinstance(row.reason_codes, list) else []
        for c in codes:
            cc = c if isinstance(c, str) else (c.get("code") if isinstance(c, dict) else str(c))
            if cc == reason_code:
                matching_narratives.append(row.narrative)
                break
        if len(matching_narratives) >= 5:
            break

    # Also pull from narrative patterns table
    pattern_q = (
        select(RFANarrativePattern.pattern_text, RFANarrativePattern.effectiveness_rate)
        .where(
            and_(
                RFANarrativePattern.reason_code == reason_code,
                RFANarrativePattern.district == district,
                RFANarrativePattern.effectiveness_rate > 0.5,
            )
        )
        .order_by(RFANarrativePattern.effectiveness_rate.desc())
        .limit(3)
    )
    pattern_result = await db.execute(pattern_q)
    patterns = [r.pattern_text for r in pattern_result.all()]

    # Build Claude prompt
    system_prompt = (
        "You are a Workers' Compensation narrative optimization expert for NYS WCB RFA-2 filings. "
        "Your goal is to rewrite the draft narrative to maximize the likelihood of acceptance by the WCB. "
        "The narrative must be factual, professional, and MUST NOT exceed 500 characters. "
        "Respond ONLY with valid JSON."
    )

    examples_text = ""
    if matching_narratives:
        examples_text = "ACCEPTED NARRATIVES (same reason code + district):\n"
        for i, n in enumerate(matching_narratives, 1):
            examples_text += f"{i}. {n}\n"
    else:
        examples_text = "No historical accepted narratives found for this combination.\n"

    if patterns:
        examples_text += "\nKNOWN WINNING PATTERNS:\n"
        for p in patterns:
            examples_text += f"- {p}\n"

    user_message = f"""{examples_text}

REASON CODE: {reason_code}
DISTRICT: {district}

DRAFT NARRATIVE:
{draft_narrative}

Optimize this draft narrative to match the winning patterns. The result MUST be 500 characters or fewer.

Return JSON:
{{
  "optimized_narrative": "...",
  "confidence": "HIGH|MEDIUM|LOW",
  "suggestions": ["list of specific improvements made"],
  "char_count": 123
}}"""

    try:
        response_text = _invoke_claude(system_prompt, user_message)
        result_data = json.loads(response_text)

        # Enforce 500 char limit
        optimized = result_data.get("optimized_narrative", draft_narrative)
        if len(optimized) > 500:
            optimized = optimized[:497] + "..."
        result_data["optimized_narrative"] = optimized
        result_data["char_count"] = len(optimized)

        return result_data

    except json.JSONDecodeError as e:
        logger.error("Failed to parse Claude narrative response: %s", e)
        return {
            "optimized_narrative": draft_narrative,
            "confidence": "LOW",
            "suggestions": ["AI optimization failed; returning original draft."],
            "char_count": len(draft_narrative),
            "error": str(e),
        }
    except Exception as e:
        logger.exception("Narrative optimization failed")
        return {
            "optimized_narrative": draft_narrative,
            "confidence": "LOW",
            "suggestions": ["AI service unavailable; returning original draft."],
            "char_count": len(draft_narrative),
            "error": str(e),
        }


async def get_winning_patterns(
    reason_code: str,
    district: str,
    db: AsyncSession,
) -> dict:
    """
    Analyze accepted narratives for common phrases, structure, and keywords
    for a given reason code and district.
    """
    # Fetch accepted narratives
    q = (
        select(RFASubmission.narrative)
        .join(RFACase, RFASubmission.case_id == RFACase.id)
        .where(
            and_(
                RFASubmission.wcb_status == "accepted",
                RFASubmission.narrative.isnot(None),
                RFACase.district == district,
            )
        )
        .order_by(RFASubmission.updated_at.desc())
        .limit(100)
    )
    result = await db.execute(q)
    all_rows = result.all()

    # Filter by reason code
    narratives = []
    for row in all_rows:
        narratives.append(row.narrative)

    # Also check reason_codes match
    q2 = (
        select(RFASubmission.narrative, RFASubmission.reason_codes)
        .join(RFACase, RFASubmission.case_id == RFACase.id)
        .where(
            and_(
                RFASubmission.wcb_status == "accepted",
                RFASubmission.narrative.isnot(None),
                RFACase.district == district,
            )
        )
        .order_by(RFASubmission.updated_at.desc())
        .limit(100)
    )
    result2 = await db.execute(q2)
    narratives = []
    for row in result2.all():
        codes = row.reason_codes if isinstance(row.reason_codes, list) else []
        for c in codes:
            cc = c if isinstance(c, str) else (c.get("code") if isinstance(c, dict) else str(c))
            if cc == reason_code:
                narratives.append(row.narrative)
                break

    if not narratives:
        return {
            "common_phrases": [],
            "avg_length": 0,
            "structure_pattern": "No accepted narratives found for this combination.",
            "sample_narratives": [],
            "total_analyzed": 0,
        }

    # Use Claude to analyze patterns
    system_prompt = (
        "You are an analyst examining accepted WCB RFA-2 narratives. "
        "Identify common patterns that lead to acceptance. "
        "Respond ONLY with valid JSON."
    )

    narratives_text = "\n".join(f"{i+1}. {n}" for i, n in enumerate(narratives[:20]))
    avg_len = sum(len(n) for n in narratives) // len(narratives)

    user_message = f"""Analyze these {len(narratives)} accepted RFA-2 narratives for reason code {reason_code} in {district} district:

{narratives_text}

Return JSON:
{{
  "common_phrases": ["list of recurring phrases or keywords"],
  "structure_pattern": "Description of the common narrative structure",
  "key_elements": ["list of elements that appear in most accepted narratives"]
}}"""

    try:
        response_text = _invoke_claude(system_prompt, user_message)
        analysis = json.loads(response_text)
    except Exception as e:
        logger.exception("Winning patterns analysis failed")
        analysis = {
            "common_phrases": [],
            "structure_pattern": "Analysis unavailable",
            "key_elements": [],
        }

    return {
        "common_phrases": analysis.get("common_phrases", []),
        "avg_length": avg_len,
        "structure_pattern": analysis.get("structure_pattern", ""),
        "key_elements": analysis.get("key_elements", []),
        "sample_narratives": narratives[:5],
        "total_analyzed": len(narratives),
    }


async def track_narrative_effectiveness(
    submission_id: str,
    outcome: str,
    db: AsyncSession,
) -> None:
    """
    After a WCB decision, log whether the narrative was associated with
    acceptance or rejection. Builds training data over time.

    Args:
        submission_id: UUID string of the submission.
        outcome: "accepted" or "rejected".
    """
    # Fetch the submission with its narrative and case info
    q = (
        select(RFASubmission.narrative, RFASubmission.reason_codes, RFACase.district)
        .join(RFACase, RFASubmission.case_id == RFACase.id)
        .where(RFASubmission.id == submission_id)
    )
    result = await db.execute(q)
    row = result.one_or_none()
    if not row or not row.narrative or not row.district:
        logger.warning("Cannot track narrative effectiveness: submission %s missing data", submission_id)
        return

    narrative = row.narrative
    district = row.district
    codes = row.reason_codes if isinstance(row.reason_codes, list) else []

    for code_entry in codes:
        reason_code = code_entry if isinstance(code_entry, str) else (
            code_entry.get("code") if isinstance(code_entry, dict) else str(code_entry)
        )

        # Check if pattern already exists
        pattern_q = (
            select(RFANarrativePattern)
            .where(
                and_(
                    RFANarrativePattern.reason_code == reason_code,
                    RFANarrativePattern.district == district,
                    RFANarrativePattern.pattern_text == narrative,
                )
            )
        )
        result = await db.execute(pattern_q)
        existing = result.scalar_one_or_none()

        if existing:
            if outcome == "accepted":
                existing.success_count += 1
            else:
                existing.failure_count += 1
            total = existing.success_count + existing.failure_count
            existing.effectiveness_rate = existing.success_count / total if total else 0.0
            existing.last_used = datetime.utcnow()
        else:
            success = 1 if outcome == "accepted" else 0
            failure = 0 if outcome == "accepted" else 1
            pattern = RFANarrativePattern(
                reason_code=reason_code,
                district=district,
                pattern_text=narrative,
                success_count=success,
                failure_count=failure,
                effectiveness_rate=float(success),
                last_used=datetime.utcnow(),
            )
            db.add(pattern)

    await db.flush()
    logger.info(
        "Tracked narrative effectiveness for submission %s: %s",
        submission_id, outcome,
    )
