"""
Outcome Analytics & Win Rate Service for AIRA.

Provides comprehensive analytics on AIRA submission outcomes including
acceptance rates by district, judge, attorney, adjuster, and reason code.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, func, case, and_, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import RFASubmission, RFACase, RFAUser

logger = logging.getLogger(__name__)

# WCB Districts
WCB_DISTRICTS = [
    "Buffalo", "Syracuse", "Albany", "NYC",
    "Binghamton", "Rochester", "Hauppauge", "Peekskill",
]

# Terminal statuses
DECIDED_STATUSES = ("accepted", "rejected")


def _date_filters(
    query,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """Apply optional date-range filters on RFASubmission.submitted_at."""
    if date_from:
        query = query.where(RFASubmission.submitted_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.where(RFASubmission.submitted_at <= datetime.combine(date_to, datetime.max.time()))
    return query


async def get_outcome_analytics(
    org_id: UUID,
    db: AsyncSession,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> dict:
    """
    Comprehensive outcome analytics for an organization.

    Returns acceptance rates overall and sliced by reason code, district,
    judge, claimant attorney, adjuster, plus filing trends and rejection reasons.
    """
    base_filter = and_(
        RFASubmission.org_id == org_id,
        RFASubmission.wcb_status.in_(DECIDED_STATUSES),
    )

    # --- Overall acceptance rate ---
    overall_q = select(
        func.count(RFASubmission.id).label("total"),
        func.count(case((RFASubmission.wcb_status == "accepted", 1))).label("accepted"),
    ).where(base_filter)
    overall_q = _date_filters(overall_q, date_from, date_to)
    result = await db.execute(overall_q)
    row = result.one()
    total_decided = row.total or 0
    total_accepted = row.accepted or 0
    overall_rate = round((total_accepted / total_decided * 100), 2) if total_decided else 0.0

    # --- Acceptance rate by district ---
    district_q = (
        select(
            RFACase.district,
            func.count(RFASubmission.id).label("total"),
            func.count(case((RFASubmission.wcb_status == "accepted", 1))).label("accepted"),
        )
        .join(RFACase, RFASubmission.case_id == RFACase.id)
        .where(base_filter)
        .where(RFACase.district.isnot(None))
        .group_by(RFACase.district)
    )
    district_q = _date_filters(district_q, date_from, date_to)
    result = await db.execute(district_q)
    by_district = []
    for r in result.all():
        rate = round((r.accepted / r.total * 100), 2) if r.total else 0.0
        by_district.append({"district": r.district, "total": r.total, "accepted": r.accepted, "rate": rate})

    # --- Acceptance rate by judge (stored in form_data->>'judge_name') ---
    judge_q = (
        select(
            RFASubmission.form_data["judge_name"].as_string().label("judge_name"),
            func.count(RFASubmission.id).label("total"),
            func.count(case((RFASubmission.wcb_status == "accepted", 1))).label("accepted"),
        )
        .where(base_filter)
        .where(RFASubmission.form_data["judge_name"].as_string().isnot(None))
        .group_by(RFASubmission.form_data["judge_name"].as_string())
    )
    judge_q = _date_filters(judge_q, date_from, date_to)
    result = await db.execute(judge_q)
    by_judge = []
    for r in result.all():
        if r.judge_name:
            rate = round((r.accepted / r.total * 100), 2) if r.total else 0.0
            by_judge.append({"judge_name": r.judge_name, "total": r.total, "accepted": r.accepted, "rate": rate})

    # --- Acceptance rate by claimant attorney ---
    attorney_q = (
        select(
            RFACase.claimant_rep_name,
            func.count(RFASubmission.id).label("total"),
            func.count(case((RFASubmission.wcb_status == "accepted", 1))).label("accepted"),
        )
        .join(RFACase, RFASubmission.case_id == RFACase.id)
        .where(base_filter)
        .where(RFACase.claimant_rep_name.isnot(None))
        .group_by(RFACase.claimant_rep_name)
    )
    attorney_q = _date_filters(attorney_q, date_from, date_to)
    result = await db.execute(attorney_q)
    by_attorney = []
    for r in result.all():
        rate = round((r.accepted / r.total * 100), 2) if r.total else 0.0
        by_attorney.append({"attorney_name": r.claimant_rep_name, "total": r.total, "accepted": r.accepted, "rate": rate})

    # --- Acceptance rate by adjuster (created_by user) ---
    adjuster_q = (
        select(
            RFAUser.full_name,
            RFAUser.id.label("user_id"),
            func.count(RFASubmission.id).label("total"),
            func.count(case((RFASubmission.wcb_status == "accepted", 1))).label("accepted"),
        )
        .join(RFAUser, RFASubmission.created_by == RFAUser.id)
        .where(base_filter)
        .group_by(RFAUser.id, RFAUser.full_name)
    )
    adjuster_q = _date_filters(adjuster_q, date_from, date_to)
    result = await db.execute(adjuster_q)
    by_adjuster = []
    for r in result.all():
        rate = round((r.accepted / r.total * 100), 2) if r.total else 0.0
        by_adjuster.append({
            "user_id": str(r.user_id),
            "adjuster_name": r.full_name,
            "total": r.total,
            "accepted": r.accepted,
            "rate": rate,
        })

    # --- Average time from filing to decision ---
    avg_time_q = (
        select(
            func.avg(
                extract("epoch", RFASubmission.updated_at) - extract("epoch", RFASubmission.submitted_at)
            ).label("avg_seconds")
        )
        .where(base_filter)
        .where(RFASubmission.submitted_at.isnot(None))
    )
    avg_time_q = _date_filters(avg_time_q, date_from, date_to)
    result = await db.execute(avg_time_q)
    avg_seconds = result.scalar() or 0
    avg_days_to_decision = round(avg_seconds / 86400, 1) if avg_seconds else 0.0

    # --- Monthly filing volume trend (last 12 months) ---
    twelve_months_ago = datetime.utcnow() - timedelta(days=365)
    monthly_q = (
        select(
            extract("year", RFASubmission.submitted_at).label("yr"),
            extract("month", RFASubmission.submitted_at).label("mo"),
            func.count(RFASubmission.id).label("count"),
        )
        .where(
            and_(
                RFASubmission.org_id == org_id,
                RFASubmission.submitted_at.isnot(None),
                RFASubmission.submitted_at >= twelve_months_ago,
            )
        )
        .group_by("yr", "mo")
        .order_by("yr", "mo")
    )
    result = await db.execute(monthly_q)
    monthly_trend = []
    for r in result.all():
        monthly_trend.append({"year": int(r.yr), "month": int(r.mo), "filings": r.count})

    # --- Acceptance rate by reason code ---
    # reason_codes is a JSON array; we query all decided submissions and aggregate in Python
    reason_q = (
        select(RFASubmission.reason_codes, RFASubmission.wcb_status)
        .where(base_filter)
        .where(RFASubmission.reason_codes.isnot(None))
    )
    reason_q = _date_filters(reason_q, date_from, date_to)
    result = await db.execute(reason_q)
    code_stats: dict[str, dict[str, int]] = {}
    for r in result.all():
        codes = r.reason_codes if isinstance(r.reason_codes, list) else []
        for code in codes:
            c = code if isinstance(code, str) else (code.get("code") if isinstance(code, dict) else str(code))
            if c not in code_stats:
                code_stats[c] = {"total": 0, "accepted": 0}
            code_stats[c]["total"] += 1
            if r.wcb_status == "accepted":
                code_stats[c]["accepted"] += 1

    by_reason_code = []
    for code, stats in sorted(code_stats.items(), key=lambda x: x[1]["total"], reverse=True):
        rate = round((stats["accepted"] / stats["total"] * 100), 2) if stats["total"] else 0.0
        by_reason_code.append({"reason_code": code, **stats, "rate": rate})

    # --- Top rejection reasons (from wcb_errors JSON) ---
    rejection_q = (
        select(RFASubmission.wcb_errors)
        .where(
            and_(
                RFASubmission.org_id == org_id,
                RFASubmission.wcb_status == "rejected",
                RFASubmission.wcb_errors.isnot(None),
            )
        )
    )
    rejection_q = _date_filters(rejection_q, date_from, date_to)
    result = await db.execute(rejection_q)
    rejection_counts: dict[str, int] = {}
    for r in result.all():
        errors = r.wcb_errors if isinstance(r.wcb_errors, list) else ([r.wcb_errors] if r.wcb_errors else [])
        for err in errors:
            reason = err if isinstance(err, str) else (err.get("reason", str(err)) if isinstance(err, dict) else str(err))
            rejection_counts[reason] = rejection_counts.get(reason, 0) + 1

    top_rejections = sorted(
        [{"reason": k, "count": v} for k, v in rejection_counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:10]

    return {
        "overall": {
            "total_decided": total_decided,
            "total_accepted": total_accepted,
            "total_rejected": total_decided - total_accepted,
            "acceptance_rate": overall_rate,
        },
        "by_district": by_district,
        "by_judge": by_judge,
        "by_attorney": by_attorney,
        "by_adjuster": by_adjuster,
        "by_reason_code": by_reason_code,
        "avg_days_to_decision": avg_days_to_decision,
        "monthly_trend": monthly_trend,
        "top_rejection_reasons": top_rejections,
        "date_range": {
            "from": date_from.isoformat() if date_from else None,
            "to": date_to.isoformat() if date_to else None,
        },
    }


async def get_district_comparison(
    org_id: UUID,
    reason_code: str,
    db: AsyncSession,
) -> list:
    """
    Compare acceptance rates across WCB districts for a specific reason code.

    Returns a list of dicts per district with total filings, accepted, rejected, and rate.
    """
    # Fetch all decided submissions for this org with the given reason code
    base_q = (
        select(
            RFACase.district,
            RFASubmission.wcb_status,
            RFASubmission.reason_codes,
        )
        .join(RFACase, RFASubmission.case_id == RFACase.id)
        .where(
            and_(
                RFASubmission.org_id == org_id,
                RFASubmission.wcb_status.in_(DECIDED_STATUSES),
                RFASubmission.reason_codes.isnot(None),
                RFACase.district.isnot(None),
            )
        )
    )
    result = await db.execute(base_q)

    district_stats: dict[str, dict[str, int]] = {d: {"total": 0, "accepted": 0} for d in WCB_DISTRICTS}

    for r in result.all():
        codes = r.reason_codes if isinstance(r.reason_codes, list) else []
        code_match = False
        for c in codes:
            cc = c if isinstance(c, str) else (c.get("code") if isinstance(c, dict) else str(c))
            if cc == reason_code:
                code_match = True
                break
        if not code_match:
            continue

        district = r.district
        if district not in district_stats:
            district_stats[district] = {"total": 0, "accepted": 0}
        district_stats[district]["total"] += 1
        if r.wcb_status == "accepted":
            district_stats[district]["accepted"] += 1

    comparison = []
    for district, stats in sorted(district_stats.items()):
        rejected = stats["total"] - stats["accepted"]
        rate = round((stats["accepted"] / stats["total"] * 100), 2) if stats["total"] else 0.0
        comparison.append({
            "district": district,
            "total": stats["total"],
            "accepted": stats["accepted"],
            "rejected": rejected,
            "acceptance_rate": rate,
        })

    return comparison


async def get_adjuster_performance(
    org_id: UUID,
    db: AsyncSession,
) -> list:
    """
    Per-adjuster performance metrics: filing count, acceptance rate,
    average processing time, and pending count.
    """
    # All submissions for this org grouped by created_by
    perf_q = (
        select(
            RFAUser.id.label("user_id"),
            RFAUser.full_name,
            RFAUser.email,
            func.count(RFASubmission.id).label("total_filings"),
            func.count(case((RFASubmission.wcb_status == "accepted", 1))).label("accepted"),
            func.count(case((RFASubmission.wcb_status.in_(DECIDED_STATUSES), 1))).label("decided"),
            func.count(case((RFASubmission.status == "draft", 1))).label("pending"),
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
            ).label("avg_processing_seconds"),
        )
        .join(RFAUser, RFASubmission.created_by == RFAUser.id)
        .where(RFASubmission.org_id == org_id)
        .group_by(RFAUser.id, RFAUser.full_name, RFAUser.email)
        .order_by(func.count(RFASubmission.id).desc())
    )
    result = await db.execute(perf_q)

    adjusters = []
    for r in result.all():
        acceptance_rate = round((r.accepted / r.decided * 100), 2) if r.decided else 0.0
        avg_days = round((r.avg_processing_seconds or 0) / 86400, 1)
        adjusters.append({
            "user_id": str(r.user_id),
            "full_name": r.full_name,
            "email": r.email,
            "total_filings": r.total_filings,
            "decided": r.decided,
            "accepted": r.accepted,
            "acceptance_rate": acceptance_rate,
            "avg_processing_days": avg_days,
            "pending": r.pending,
        })

    return adjusters
