"""Dashboard router — aggregate statistics for the AIRA portal."""
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..database import get_db
from ..models.models import RFACase, RFASubmission
from ..middleware.auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# ── Response schemas ────────────────────────────────────────────────────────
class RecentSubmission(BaseModel):
    id: str
    case_id: str
    status: str
    reason_codes: list | None = None
    wcb_submission_id: str | None = None
    created_at: str | None = None


class DashboardResponse(BaseModel):
    total_cases: int
    submissions_by_status: dict[str, int]
    submissions_this_month: int
    recent_submissions: list[RecentSubmission]


class ReasonCodeBreakdown(BaseModel):
    reason_code: str
    count: int


class ReasonCodeResponse(BaseModel):
    breakdown: list[ReasonCodeBreakdown]
    total_submissions: int


# ── Endpoints ───────────────────────────────────────────────────────────────
@router.get("/", response_model=DashboardResponse)
async def dashboard(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate stats: total cases, submissions by status, recent submissions, submissions this month."""
    org_id = current_user.org_id

    # Total cases
    cases_result = await db.execute(
        select(func.count(RFACase.id)).where(RFACase.org_id == org_id)
    )
    total_cases = cases_result.scalar() or 0

    # Submissions by status
    status_result = await db.execute(
        select(RFASubmission.status, func.count(RFASubmission.id))
        .where(RFASubmission.org_id == org_id)
        .group_by(RFASubmission.status)
    )
    submissions_by_status = {row[0]: row[1] for row in status_result.all()}

    # Submissions this month
    now = datetime.now(timezone.utc)
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_result = await db.execute(
        select(func.count(RFASubmission.id))
        .where(
            RFASubmission.org_id == org_id,
            RFASubmission.created_at >= first_of_month,
        )
    )
    submissions_this_month = month_result.scalar() or 0

    # Recent submissions (last 10)
    recent_result = await db.execute(
        select(RFASubmission)
        .where(RFASubmission.org_id == org_id)
        .order_by(RFASubmission.created_at.desc())
        .limit(10)
    )
    recent = recent_result.scalars().all()

    return DashboardResponse(
        total_cases=total_cases,
        submissions_by_status=submissions_by_status,
        submissions_this_month=submissions_this_month,
        recent_submissions=[
            RecentSubmission(
                id=str(s.id),
                case_id=str(s.case_id),
                status=s.status,
                reason_codes=s.reason_codes,
                wcb_submission_id=s.wcb_submission_id,
                created_at=str(s.created_at) if s.created_at else None,
            )
            for s in recent
        ],
    )


@router.get("/reason-codes", response_model=ReasonCodeResponse)
async def reason_code_breakdown(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Breakdown of submissions by reason code."""
    org_id = current_user.org_id

    # Fetch all submissions with reason_codes for this org
    result = await db.execute(
        select(RFASubmission.reason_codes)
        .where(
            RFASubmission.org_id == org_id,
            RFASubmission.reason_codes.isnot(None),
        )
    )
    rows = result.all()

    # Count each reason code across all submissions
    code_counts: dict[str, int] = {}
    total = 0
    for (reason_codes,) in rows:
        if isinstance(reason_codes, list):
            total += 1
            for code in reason_codes:
                code_counts[code] = code_counts.get(code, 0) + 1

    breakdown = sorted(
        [ReasonCodeBreakdown(reason_code=k, count=v) for k, v in code_counts.items()],
        key=lambda x: x.count,
        reverse=True,
    )

    return ReasonCodeResponse(breakdown=breakdown, total_submissions=total)
