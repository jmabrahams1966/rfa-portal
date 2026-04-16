"""Cases router — CRUD for RFA cases with search and submission history."""
import uuid
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models.models import RFACase, RFASubmission, RFAAuditLog
from ..middleware.auth import get_current_user, require_adjuster

router = APIRouter(prefix="/cases", tags=["cases"])


# ── Schemas ─────────────────────────────────────────────────────────────────
class CaseCreate(BaseModel):
    wcb_case_number: str
    claimant_name_encrypted: str | None = None
    date_of_injury: date | None = None
    employer_name: str | None = None
    employer_fein: str | None = None
    is_volunteer: bool = False
    claimant_rep_name: str | None = None
    claimant_rep_address: str | None = None
    carrier_name: str | None = None
    carrier_code: str | None = None
    district: str | None = None


class CaseUpdate(BaseModel):
    claimant_name_encrypted: str | None = None
    date_of_injury: date | None = None
    employer_name: str | None = None
    employer_fein: str | None = None
    is_volunteer: bool | None = None
    claimant_rep_name: str | None = None
    claimant_rep_address: str | None = None
    carrier_name: str | None = None
    carrier_code: str | None = None
    district: str | None = None


class SubmissionSummary(BaseModel):
    id: str
    status: str
    reason_codes: list | None = None
    wcb_submission_id: str | None = None
    submitted_at: str | None = None
    created_at: str | None = None


class CaseResponse(BaseModel):
    id: str
    org_id: str
    wcb_case_number: str
    claimant_name_encrypted: str | None = None
    date_of_injury: date | None = None
    employer_name: str | None = None
    employer_fein: str | None = None
    is_volunteer: bool
    claimant_rep_name: str | None = None
    claimant_rep_address: str | None = None
    carrier_name: str | None = None
    carrier_code: str | None = None
    district: str | None = None
    created_at: str | None = None


class CaseDetailResponse(CaseResponse):
    submissions: list[SubmissionSummary] = []


# ── Endpoints ───────────────────────────────────────────────────────────────
@router.post("/", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    body: CaseCreate,
    current_user=Depends(require_adjuster),
    db: AsyncSession = Depends(get_db),
):
    """Create a new case. Rejects duplicates within the same org."""
    existing = await db.execute(
        select(RFACase).where(
            RFACase.org_id == current_user.org_id,
            RFACase.wcb_case_number == body.wcb_case_number,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Case number already exists for this organization",
        )

    case = RFACase(
        id=uuid.uuid4(),
        org_id=current_user.org_id,
        **body.model_dump(),
    )
    db.add(case)

    # Audit
    db.add(RFAAuditLog(
        id=uuid.uuid4(),
        org_id=current_user.org_id,
        user_id=current_user.id,
        user_email=current_user.email,
        action="case_created",
        resource_type="case",
        resource_id=case.id,
        description=f"Created case {body.wcb_case_number}",
    ))

    await db.flush()
    return _case_to_response(case)


@router.get("/", response_model=list[CaseResponse])
async def list_cases(
    search: str | None = Query(None, description="Search by WCB case number"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all cases for the org. Optionally filter by wcb_case_number."""
    query = select(RFACase).where(RFACase.org_id == current_user.org_id)

    if search:
        query = query.where(RFACase.wcb_case_number.ilike(f"%{search}%"))

    query = query.order_by(RFACase.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    cases = result.scalars().all()
    return [_case_to_response(c) for c in cases]


@router.get("/{case_id}", response_model=CaseDetailResponse)
async def get_case(
    case_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get case detail with submission history."""
    result = await db.execute(
        select(RFACase)
        .options(selectinload(RFACase.submissions))
        .where(RFACase.id == case_id, RFACase.org_id == current_user.org_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    resp = CaseDetailResponse(**_case_to_response(case).model_dump())
    resp.submissions = [
        SubmissionSummary(
            id=str(s.id),
            status=s.status,
            reason_codes=s.reason_codes,
            wcb_submission_id=s.wcb_submission_id,
            submitted_at=str(s.submitted_at) if s.submitted_at else None,
            created_at=str(s.created_at) if s.created_at else None,
        )
        for s in (case.submissions or [])
    ]
    return resp


@router.put("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: uuid.UUID,
    body: CaseUpdate,
    current_user=Depends(require_adjuster),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing case."""
    case = await _get_case_or_404(db, case_id, current_user.org_id)
    updates = body.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(case, key, value)

    db.add(RFAAuditLog(
        id=uuid.uuid4(),
        org_id=current_user.org_id,
        user_id=current_user.id,
        user_email=current_user.email,
        action="case_updated",
        resource_type="case",
        resource_id=case.id,
        description=f"Updated case {case.wcb_case_number}",
    ))

    await db.flush()
    return _case_to_response(case)


# ── Helpers ─────────────────────────────────────────────────────────────────
async def _get_case_or_404(
    db: AsyncSession, case_id: uuid.UUID, org_id: uuid.UUID
) -> RFACase:
    result = await db.execute(
        select(RFACase).where(RFACase.id == case_id, RFACase.org_id == org_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


def _case_to_response(case: RFACase) -> CaseResponse:
    return CaseResponse(
        id=str(case.id),
        org_id=str(case.org_id),
        wcb_case_number=case.wcb_case_number,
        claimant_name_encrypted=case.claimant_name_encrypted,
        date_of_injury=case.date_of_injury,
        employer_name=case.employer_name,
        employer_fein=case.employer_fein,
        is_volunteer=case.is_volunteer,
        claimant_rep_name=case.claimant_rep_name,
        claimant_rep_address=case.claimant_rep_address,
        carrier_name=case.carrier_name,
        carrier_code=case.carrier_code,
        district=case.district,
        created_at=str(case.created_at) if case.created_at else None,
    )
