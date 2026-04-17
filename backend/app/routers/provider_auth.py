"""Provider Prior Authorization router — full prior auth lifecycle.

Endpoints:
  POST   /provider-auth/requests/              — create new auth request
  GET    /provider-auth/requests/              — list auth requests (filter, paginate)
  GET    /provider-auth/requests/{id}/         — detail with documents + narrative
  PUT    /provider-auth/requests/{id}/         — update auth request

  POST   /provider-auth/requests/{id}/documents/   — upload document (S3 + PHI + clinical extraction)
  GET    /provider-auth/requests/{id}/documents/   — list documents for request

  POST   /provider-auth/requests/{id}/generate-narrative/  — AI narrative generation
  POST   /provider-auth/requests/{id}/optimize/            — optimize narrative for payer
  PUT    /provider-auth/requests/{id}/narrative/            — manual narrative edit

  POST   /provider-auth/requests/{id}/submit/    — mark as submitted
  POST   /provider-auth/requests/{id}/denial/    — record denial + AI analysis
  POST   /provider-auth/requests/{id}/appeal/    — generate appeal letter
  POST   /provider-auth/requests/{id}/peer-to-peer/  — peer-to-peer talking points
  POST   /provider-auth/requests/{id}/outcome/   — record final outcome

  GET    /provider-auth/analytics/     — practice-wide auth analytics
  GET    /provider-auth/payer-profiles/ — payer auth profiles
  GET    /provider-auth/dashboard/     — summary dashboard stats
"""
import uuid
import base64
import logging
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import (
    APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form,
)
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models.provider_auth import (
    AuthRequest, AuthDocument, AuthLearning, PayerAuthProfile,
)
from ..middleware.auth import get_current_user
from ..services.phi_service import deidentify
from ..services.provider_auth_service import (
    extract_clinical_data,
    generate_auth_narrative,
    optimize_for_payer,
    analyze_denial,
    generate_appeal,
    prepare_peer_to_peer,
    record_outcome,
    get_auth_analytics,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/provider-auth", tags=["provider-auth"])


# ═══════════════════════════════════════════════════════════════════════════
# Request / Response Schemas
# ═══════════════════════════════════════════════════════════════════════════

class AuthRequestCreate(BaseModel):
    patient_name: str
    patient_dob: Optional[date] = None
    patient_mrn: str
    diagnosis_primary: str
    diagnosis_codes: list[str]
    proposed_procedure: str
    proposed_cpt_codes: list[str]
    surgeon_name: str
    surgeon_npi: str
    payer_name: str
    payer_id: str
    insurance_type: str
    clinical_urgency: str
    wcb_case_number: Optional[str] = None
    date_of_injury: Optional[date] = None


class AuthRequestUpdate(BaseModel):
    patient_name: Optional[str] = None
    patient_dob: Optional[date] = None
    patient_mrn: Optional[str] = None
    diagnosis_primary: Optional[str] = None
    diagnosis_codes: Optional[list[str]] = None
    proposed_procedure: Optional[str] = None
    proposed_cpt_codes: Optional[list[str]] = None
    surgeon_name: Optional[str] = None
    surgeon_npi: Optional[str] = None
    payer_name: Optional[str] = None
    payer_id: Optional[str] = None
    insurance_type: Optional[str] = None
    clinical_urgency: Optional[str] = None
    wcb_case_number: Optional[str] = None
    date_of_injury: Optional[date] = None


class DenialRecord(BaseModel):
    denial_reason: str
    denial_date: date


class OutcomeRecord(BaseModel):
    outcome: str  # "approved" or "denied"
    notes: Optional[str] = None
    auth_number: Optional[str] = None
    approved_procedure: Optional[str] = None


class NarrativeEdit(BaseModel):
    narrative: str


class AuthDocumentResponse(BaseModel):
    id: str
    auth_request_id: str
    doc_type: str
    file_name: str
    s3_key: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    extracted_data: Optional[dict] = None
    created_at: Optional[str] = None


class AuthRequestResponse(BaseModel):
    id: str
    org_id: str
    created_by: str
    patient_name: str
    patient_dob: Optional[date] = None
    patient_mrn: str
    diagnosis_primary: str
    diagnosis_codes: Optional[list[str]] = None
    proposed_procedure: str
    proposed_cpt_codes: Optional[list[str]] = None
    surgeon_name: str
    surgeon_npi: str
    payer_name: str
    payer_id: str
    insurance_type: str
    clinical_urgency: str
    wcb_case_number: Optional[str] = None
    date_of_injury: Optional[date] = None
    status: str
    narrative: Optional[str] = None
    narrative_confidence: Optional[str] = None
    missing_elements: Optional[list[str]] = None
    optimized_narrative: Optional[str] = None
    denial_reason: Optional[str] = None
    denial_date: Optional[date] = None
    denial_analysis: Optional[dict] = None
    appeal_letter: Optional[str] = None
    peer_to_peer_points: Optional[list[str]] = None
    outcome: Optional[str] = None
    outcome_notes: Optional[str] = None
    auth_number: Optional[str] = None
    approved_procedure: Optional[str] = None
    submitted_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AuthRequestDetailResponse(AuthRequestResponse):
    documents: list[AuthDocumentResponse] = []


class PayerProfileResponse(BaseModel):
    id: str
    payer_name: str
    payer_id: str
    approval_rate: Optional[float] = None
    avg_turnaround_days: Optional[int] = None
    required_documents: Optional[list[str]] = None
    tips: Optional[list[str]] = None
    common_denial_reasons: Optional[list[str]] = None
    updated_at: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════
# Auth Request CRUD
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/requests/", response_model=AuthRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_auth_request(
    body: AuthRequestCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new prior authorization request."""
    auth_req = AuthRequest(
        id=uuid.uuid4(),
        org_id=current_user.org_id,
        created_by=current_user.id,
        patient_name=body.patient_name,
        patient_dob=body.patient_dob,
        patient_mrn=body.patient_mrn,
        diagnosis_primary=body.diagnosis_primary,
        diagnosis_codes=body.diagnosis_codes,
        proposed_procedure=body.proposed_procedure,
        proposed_cpt_codes=body.proposed_cpt_codes,
        surgeon_name=body.surgeon_name,
        surgeon_npi=body.surgeon_npi,
        payer_name=body.payer_name,
        payer_id=body.payer_id,
        insurance_type=body.insurance_type,
        clinical_urgency=body.clinical_urgency,
        wcb_case_number=body.wcb_case_number,
        date_of_injury=body.date_of_injury,
        status="draft",
    )
    db.add(auth_req)
    await db.flush()
    return _auth_request_response(auth_req)


@router.get("/requests/", response_model=list[AuthRequestResponse])
async def list_auth_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    payer_name: Optional[str] = Query(None),
    insurance_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all auth requests for the organization with optional filters."""
    query = select(AuthRequest).where(AuthRequest.org_id == current_user.org_id)

    if status_filter:
        query = query.where(AuthRequest.status == status_filter)
    if payer_name:
        query = query.where(AuthRequest.payer_name.ilike(f"%{payer_name}%"))
    if insurance_type:
        query = query.where(AuthRequest.insurance_type == insurance_type)

    query = query.order_by(AuthRequest.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return [_auth_request_response(r) for r in result.scalars().all()]


@router.get("/requests/{request_id}/", response_model=AuthRequestDetailResponse)
async def get_auth_request(
    request_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get auth request detail with all documents and current narrative."""
    result = await db.execute(
        select(AuthRequest)
        .options(selectinload(AuthRequest.documents))
        .where(AuthRequest.id == request_id, AuthRequest.org_id == current_user.org_id)
    )
    auth_req = result.scalar_one_or_none()
    if not auth_req:
        raise HTTPException(status_code=404, detail="Auth request not found")

    resp = AuthRequestDetailResponse(**_auth_request_response(auth_req).model_dump())
    resp.documents = [_doc_response(d) for d in (auth_req.documents or [])]
    return resp


@router.put("/requests/{request_id}/", response_model=AuthRequestResponse)
async def update_auth_request(
    request_id: uuid.UUID,
    body: AuthRequestUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing auth request."""
    auth_req = await _get_auth_request_or_404(db, request_id, current_user.org_id)

    if auth_req.status not in ("draft", "narrative_generated", "optimized"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot update auth request with status '{auth_req.status}'",
        )

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(auth_req, key, value)

    auth_req.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return _auth_request_response(auth_req)


# ═══════════════════════════════════════════════════════════════════════════
# Document Upload
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/requests/{request_id}/documents/", response_model=AuthDocumentResponse)
async def upload_document(
    request_id: uuid.UUID,
    file: UploadFile = File(...),
    doc_type: str = Form("clinical_record"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a document to an auth request.

    - Attempts S3 upload with SSE-AES256 encryption
    - Falls back to base64 if S3 is unavailable
    - Runs PHI de-identification on extracted text
    - Runs clinical data extraction via extract_clinical_data()
    - Saves AuthDocument record with extracted data
    """
    auth_req = await _get_auth_request_or_404(db, request_id, current_user.org_id)

    file_bytes = await file.read()
    file_name = file.filename or "untitled"
    mime_type = file.content_type or "application/octet-stream"
    size_bytes = len(file_bytes)

    # ── S3 upload (with base64 fallback) ────────────────────────────────
    s3_key = f"provider-auth-docs/{current_user.org_id}/{request_id}/{uuid.uuid4()}/{file_name}"
    try:
        import boto3
        from ..config import get_settings
        settings = get_settings()
        s3 = boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
        )
        s3.put_object(
            Bucket="rfa-portal-documents",
            Key=s3_key,
            Body=file_bytes,
            ContentType=mime_type,
            ServerSideEncryption="AES256",
        )
        logger.info("Uploaded %s to S3: %s", file_name, s3_key)
    except Exception as exc:
        logger.warning("S3 upload failed (%s), using base64 fallback", exc)
        encoded = base64.b64encode(file_bytes).decode()
        s3_key = f"base64://{file_name}/{len(encoded)}"

    # ── Text extraction ─────────────────────────────────────────────────
    raw_text = ""
    if mime_type == "application/pdf":
        try:
            import fitz  # PyMuPDF
            pdf = fitz.open(stream=file_bytes, filetype="pdf")
            raw_text = "\n".join(page.get_text() for page in pdf)
            pdf.close()
        except Exception as exc:
            logger.warning("PDF text extraction failed (%s), using filename", exc)
            raw_text = file_name
    else:
        try:
            raw_text = file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            raw_text = file_name

    # ── PHI de-identification ───────────────────────────────────────────
    clean_text = raw_text
    if raw_text and raw_text != file_name:
        clean_text, _log = deidentify(raw_text)

    # ── Clinical data extraction ────────────────────────────────────────
    extracted_data = None
    try:
        extracted_data = await extract_clinical_data(clean_text, doc_type)
    except Exception as exc:
        logger.warning("Clinical data extraction failed for doc %s: %s", file_name, exc)

    # ── Save AuthDocument record ────────────────────────────────────────
    doc = AuthDocument(
        id=uuid.uuid4(),
        auth_request_id=auth_req.id,
        org_id=current_user.org_id,
        doc_type=doc_type,
        file_name=file_name,
        s3_key=s3_key,
        clean_text=clean_text,
        mime_type=mime_type,
        size_bytes=size_bytes,
        extracted_data=extracted_data,
    )
    db.add(doc)
    await db.flush()

    return _doc_response(doc)


@router.get("/requests/{request_id}/documents/", response_model=list[AuthDocumentResponse])
async def list_documents(
    request_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all documents for an auth request."""
    await _get_auth_request_or_404(db, request_id, current_user.org_id)

    result = await db.execute(
        select(AuthDocument).where(
            AuthDocument.auth_request_id == request_id,
            AuthDocument.org_id == current_user.org_id,
        ).order_by(AuthDocument.created_at.desc())
    )
    return [_doc_response(d) for d in result.scalars().all()]


# ═══════════════════════════════════════════════════════════════════════════
# AI Narrative Generation
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/requests/{request_id}/generate-narrative/")
async def generate_narrative(
    request_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate the prior auth narrative from all uploaded documents."""
    result = await db.execute(
        select(AuthRequest)
        .options(selectinload(AuthRequest.documents))
        .where(AuthRequest.id == request_id, AuthRequest.org_id == current_user.org_id)
    )
    auth_req = result.scalar_one_or_none()
    if not auth_req:
        raise HTTPException(status_code=404, detail="Auth request not found")

    if not auth_req.documents:
        raise HTTPException(status_code=400, detail="No documents uploaded. Upload clinical records first.")

    # Gather all clean text and extracted data from documents
    clinical_texts = []
    extracted_data_list = []
    for doc in auth_req.documents:
        if doc.clean_text:
            clinical_texts.append(doc.clean_text)
        if doc.extracted_data:
            extracted_data_list.append(doc.extracted_data)

    narrative_result = await generate_auth_narrative(
        patient_name=auth_req.patient_name,
        diagnosis_primary=auth_req.diagnosis_primary,
        diagnosis_codes=auth_req.diagnosis_codes,
        proposed_procedure=auth_req.proposed_procedure,
        proposed_cpt_codes=auth_req.proposed_cpt_codes,
        surgeon_name=auth_req.surgeon_name,
        clinical_texts=clinical_texts,
        extracted_data=extracted_data_list,
    )

    auth_req.narrative = narrative_result.get("narrative", "")
    auth_req.narrative_confidence = narrative_result.get("confidence", "medium")
    auth_req.missing_elements = narrative_result.get("missing_elements", [])
    auth_req.status = "narrative_generated"
    auth_req.updated_at = datetime.now(timezone.utc)
    await db.flush()

    return {
        "request_id": str(auth_req.id),
        "narrative": auth_req.narrative,
        "confidence": auth_req.narrative_confidence,
        "missing_elements": auth_req.missing_elements,
    }


@router.post("/requests/{request_id}/optimize/")
async def optimize_narrative(
    request_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Optimize the narrative for the specific payer."""
    auth_req = await _get_auth_request_or_404(db, request_id, current_user.org_id)

    if not auth_req.narrative:
        raise HTTPException(status_code=400, detail="No narrative generated yet. Generate a narrative first.")

    # Look up payer profile for optimization context
    payer_profile = None
    payer_result = await db.execute(
        select(PayerAuthProfile).where(PayerAuthProfile.payer_id == auth_req.payer_id)
    )
    payer_profile_row = payer_result.scalar_one_or_none()
    payer_context = None
    if payer_profile_row:
        payer_context = {
            "payer_name": payer_profile_row.payer_name,
            "required_documents": payer_profile_row.required_documents,
            "tips": payer_profile_row.tips,
            "common_denial_reasons": payer_profile_row.common_denial_reasons,
        }

    optimize_result = await optimize_for_payer(
        narrative=auth_req.narrative,
        payer_name=auth_req.payer_name,
        payer_id=auth_req.payer_id,
        insurance_type=auth_req.insurance_type,
        procedure=auth_req.proposed_procedure,
        cpt_codes=auth_req.proposed_cpt_codes,
        payer_context=payer_context,
    )

    auth_req.optimized_narrative = optimize_result.get("optimized_narrative", auth_req.narrative)
    auth_req.status = "optimized"
    auth_req.updated_at = datetime.now(timezone.utc)
    await db.flush()

    return {
        "request_id": str(auth_req.id),
        "original_narrative": auth_req.narrative,
        "optimized_narrative": auth_req.optimized_narrative,
        "changes": optimize_result.get("changes", []),
        "payer_specific_tips": optimize_result.get("payer_specific_tips", []),
    }


@router.put("/requests/{request_id}/narrative/", response_model=AuthRequestResponse)
async def edit_narrative(
    request_id: uuid.UUID,
    body: NarrativeEdit,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually edit the narrative (surgeon makes changes before submission)."""
    auth_req = await _get_auth_request_or_404(db, request_id, current_user.org_id)

    auth_req.narrative = body.narrative
    auth_req.updated_at = datetime.now(timezone.utc)
    await db.flush()

    return _auth_request_response(auth_req)


# ═══════════════════════════════════════════════════════════════════════════
# Submission
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/requests/{request_id}/submit/", response_model=AuthRequestResponse)
async def submit_auth_request(
    request_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark auth request as submitted. Record submission date."""
    auth_req = await _get_auth_request_or_404(db, request_id, current_user.org_id)

    if auth_req.status in ("submitted", "approved", "denied"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot submit auth request with status '{auth_req.status}'",
        )

    if not auth_req.narrative and not auth_req.optimized_narrative:
        raise HTTPException(status_code=400, detail="No narrative generated. Generate a narrative before submitting.")

    auth_req.status = "submitted"
    auth_req.submitted_at = datetime.now(timezone.utc)
    auth_req.updated_at = datetime.now(timezone.utc)
    await db.flush()

    return _auth_request_response(auth_req)


# ═══════════════════════════════════════════════════════════════════════════
# Denial & Appeal
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/requests/{request_id}/denial/")
async def record_denial(
    request_id: uuid.UUID,
    body: DenialRecord,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record a denial and trigger AI analysis with appeal recommendations."""
    result = await db.execute(
        select(AuthRequest)
        .options(selectinload(AuthRequest.documents))
        .where(AuthRequest.id == request_id, AuthRequest.org_id == current_user.org_id)
    )
    auth_req = result.scalar_one_or_none()
    if not auth_req:
        raise HTTPException(status_code=404, detail="Auth request not found")

    auth_req.denial_reason = body.denial_reason
    auth_req.denial_date = body.denial_date
    auth_req.status = "denied"
    auth_req.updated_at = datetime.now(timezone.utc)

    # Gather clinical context for analysis
    clinical_texts = [doc.clean_text for doc in (auth_req.documents or []) if doc.clean_text]

    denial_analysis = await analyze_denial(
        denial_reason=body.denial_reason,
        narrative=auth_req.optimized_narrative or auth_req.narrative or "",
        diagnosis_primary=auth_req.diagnosis_primary,
        diagnosis_codes=auth_req.diagnosis_codes,
        proposed_procedure=auth_req.proposed_procedure,
        proposed_cpt_codes=auth_req.proposed_cpt_codes,
        payer_name=auth_req.payer_name,
        clinical_texts=clinical_texts,
    )

    auth_req.denial_analysis = denial_analysis
    await db.flush()

    return {
        "request_id": str(auth_req.id),
        "denial_reason": body.denial_reason,
        "denial_date": str(body.denial_date),
        "analysis": denial_analysis.get("analysis", ""),
        "appeal_letter_draft": denial_analysis.get("appeal_letter_draft", ""),
        "peer_to_peer_recommended": denial_analysis.get("peer_to_peer_recommended", False),
        "additional_evidence_needed": denial_analysis.get("additional_evidence_needed", []),
        "success_probability": denial_analysis.get("success_probability", "unknown"),
    }


@router.post("/requests/{request_id}/appeal/")
async def generate_appeal_letter(
    request_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate and record a formal appeal letter."""
    result = await db.execute(
        select(AuthRequest)
        .options(selectinload(AuthRequest.documents))
        .where(AuthRequest.id == request_id, AuthRequest.org_id == current_user.org_id)
    )
    auth_req = result.scalar_one_or_none()
    if not auth_req:
        raise HTTPException(status_code=404, detail="Auth request not found")

    if not auth_req.denial_reason:
        raise HTTPException(status_code=400, detail="No denial recorded. Record a denial first.")

    clinical_texts = [doc.clean_text for doc in (auth_req.documents or []) if doc.clean_text]

    appeal_result = await generate_appeal(
        denial_reason=auth_req.denial_reason,
        denial_analysis=auth_req.denial_analysis,
        narrative=auth_req.optimized_narrative or auth_req.narrative or "",
        patient_name=auth_req.patient_name,
        diagnosis_primary=auth_req.diagnosis_primary,
        diagnosis_codes=auth_req.diagnosis_codes,
        proposed_procedure=auth_req.proposed_procedure,
        proposed_cpt_codes=auth_req.proposed_cpt_codes,
        surgeon_name=auth_req.surgeon_name,
        payer_name=auth_req.payer_name,
        clinical_texts=clinical_texts,
    )

    auth_req.appeal_letter = appeal_result.get("appeal_letter", "")
    auth_req.status = "appealing"
    auth_req.updated_at = datetime.now(timezone.utc)
    await db.flush()

    return {
        "request_id": str(auth_req.id),
        "appeal_letter": auth_req.appeal_letter,
        "key_arguments": appeal_result.get("key_arguments", []),
        "cited_guidelines": appeal_result.get("cited_guidelines", []),
    }


@router.post("/requests/{request_id}/peer-to-peer/")
async def generate_peer_to_peer(
    request_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate peer-to-peer review talking points."""
    result = await db.execute(
        select(AuthRequest)
        .options(selectinload(AuthRequest.documents))
        .where(AuthRequest.id == request_id, AuthRequest.org_id == current_user.org_id)
    )
    auth_req = result.scalar_one_or_none()
    if not auth_req:
        raise HTTPException(status_code=404, detail="Auth request not found")

    if not auth_req.denial_reason:
        raise HTTPException(status_code=400, detail="No denial recorded. Record a denial first.")

    clinical_texts = [doc.clean_text for doc in (auth_req.documents or []) if doc.clean_text]

    p2p_result = await prepare_peer_to_peer(
        denial_reason=auth_req.denial_reason,
        denial_analysis=auth_req.denial_analysis,
        narrative=auth_req.optimized_narrative or auth_req.narrative or "",
        diagnosis_primary=auth_req.diagnosis_primary,
        diagnosis_codes=auth_req.diagnosis_codes,
        proposed_procedure=auth_req.proposed_procedure,
        proposed_cpt_codes=auth_req.proposed_cpt_codes,
        surgeon_name=auth_req.surgeon_name,
        payer_name=auth_req.payer_name,
        clinical_texts=clinical_texts,
    )

    auth_req.peer_to_peer_points = p2p_result.get("talking_points", [])
    auth_req.updated_at = datetime.now(timezone.utc)
    await db.flush()

    return {
        "request_id": str(auth_req.id),
        "talking_points": auth_req.peer_to_peer_points,
        "key_literature": p2p_result.get("key_literature", []),
        "anticipated_objections": p2p_result.get("anticipated_objections", []),
        "rebuttals": p2p_result.get("rebuttals", []),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Outcome Recording
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/requests/{request_id}/outcome/", response_model=AuthRequestResponse)
async def record_auth_outcome(
    request_id: uuid.UUID,
    body: OutcomeRecord,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record final outcome (approved/denied) and feed the learning loop."""
    auth_req = await _get_auth_request_or_404(db, request_id, current_user.org_id)

    if body.outcome not in ("approved", "denied"):
        raise HTTPException(status_code=422, detail="Outcome must be 'approved' or 'denied'")

    auth_req.outcome = body.outcome
    auth_req.outcome_notes = body.notes
    auth_req.auth_number = body.auth_number
    auth_req.approved_procedure = body.approved_procedure
    auth_req.status = body.outcome
    auth_req.updated_at = datetime.now(timezone.utc)

    # Feed the learning loop
    try:
        await record_outcome(
            auth_request_id=str(auth_req.id),
            org_id=str(auth_req.org_id),
            payer_name=auth_req.payer_name,
            payer_id=auth_req.payer_id,
            insurance_type=auth_req.insurance_type,
            procedure=auth_req.proposed_procedure,
            cpt_codes=auth_req.proposed_cpt_codes,
            diagnosis_codes=auth_req.diagnosis_codes,
            surgeon_name=auth_req.surgeon_name,
            outcome=body.outcome,
            denial_reason=auth_req.denial_reason,
            narrative_used=auth_req.optimized_narrative or auth_req.narrative,
        )
    except Exception as exc:
        logger.warning("Failed to record outcome in learning loop: %s", exc)

    await db.flush()
    return _auth_request_response(auth_req)


# ═══════════════════════════════════════════════════════════════════════════
# Analytics
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/analytics/")
async def auth_analytics(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Practice-wide auth analytics: approval rates, denial reasons, trends."""
    analytics = await get_auth_analytics(org_id=str(current_user.org_id))
    return analytics


@router.get("/payer-profiles/", response_model=list[PayerProfileResponse])
async def list_payer_profiles(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List payer auth profiles with approval rates, tips, required docs."""
    result = await db.execute(
        select(PayerAuthProfile).order_by(PayerAuthProfile.payer_name)
    )
    profiles = result.scalars().all()
    return [_payer_profile_response(p) for p in profiles]


# ═══════════════════════════════════════════════════════════════════════════
# Dashboard
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/dashboard/")
async def auth_dashboard(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Summary stats: pending, awaiting decision, recently approved/denied, approval rate."""
    org_id = current_user.org_id

    # Total counts by status
    status_counts_result = await db.execute(
        select(AuthRequest.status, sa_func.count(AuthRequest.id))
        .where(AuthRequest.org_id == org_id)
        .group_by(AuthRequest.status)
    )
    status_counts = {row[0]: row[1] for row in status_counts_result.all()}

    # Recently approved (last 30 days)
    thirty_days_ago = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    thirty_days_ago = thirty_days_ago.replace(day=max(1, thirty_days_ago.day - 30))

    recent_approved_result = await db.execute(
        select(sa_func.count(AuthRequest.id))
        .where(
            AuthRequest.org_id == org_id,
            AuthRequest.outcome == "approved",
            AuthRequest.updated_at >= thirty_days_ago,
        )
    )
    recent_approved = recent_approved_result.scalar() or 0

    recent_denied_result = await db.execute(
        select(sa_func.count(AuthRequest.id))
        .where(
            AuthRequest.org_id == org_id,
            AuthRequest.outcome == "denied",
            AuthRequest.updated_at >= thirty_days_ago,
        )
    )
    recent_denied = recent_denied_result.scalar() or 0

    # Approval rate this month
    total_decided = recent_approved + recent_denied
    approval_rate = round((recent_approved / total_decided * 100), 1) if total_decided > 0 else 0.0

    # Pending auths (draft, narrative_generated, optimized)
    pending = sum(status_counts.get(s, 0) for s in ("draft", "narrative_generated", "optimized"))

    # Awaiting decision (submitted)
    awaiting_decision = status_counts.get("submitted", 0)

    return {
        "pending_auths": pending,
        "awaiting_decision": awaiting_decision,
        "recently_approved": recent_approved,
        "recently_denied": recent_denied,
        "approval_rate_this_month": approval_rate,
        "total_decided_this_month": total_decided,
        "status_breakdown": status_counts,
        "total_requests": sum(status_counts.values()),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Internal Helpers
# ═══════════════════════════════════════════════════════════════════════════

async def _get_auth_request_or_404(
    db: AsyncSession, request_id: uuid.UUID, org_id,
) -> AuthRequest:
    result = await db.execute(
        select(AuthRequest).where(
            AuthRequest.id == request_id, AuthRequest.org_id == org_id,
        )
    )
    auth_req = result.scalar_one_or_none()
    if not auth_req:
        raise HTTPException(status_code=404, detail="Auth request not found")
    return auth_req


def _auth_request_response(r: AuthRequest) -> AuthRequestResponse:
    return AuthRequestResponse(
        id=str(r.id),
        org_id=str(r.org_id),
        created_by=str(r.created_by),
        patient_name=r.patient_name,
        patient_dob=r.patient_dob,
        patient_mrn=r.patient_mrn,
        diagnosis_primary=r.diagnosis_primary,
        diagnosis_codes=r.diagnosis_codes,
        proposed_procedure=r.proposed_procedure,
        proposed_cpt_codes=r.proposed_cpt_codes,
        surgeon_name=r.surgeon_name,
        surgeon_npi=r.surgeon_npi,
        payer_name=r.payer_name,
        payer_id=r.payer_id,
        insurance_type=r.insurance_type,
        clinical_urgency=r.clinical_urgency,
        wcb_case_number=r.wcb_case_number,
        date_of_injury=r.date_of_injury,
        status=r.status,
        narrative=r.narrative,
        narrative_confidence=r.narrative_confidence,
        missing_elements=r.missing_elements,
        optimized_narrative=r.optimized_narrative,
        denial_reason=r.denial_reason,
        denial_date=r.denial_date,
        denial_analysis=r.denial_analysis,
        appeal_letter=r.appeal_letter,
        peer_to_peer_points=r.peer_to_peer_points,
        outcome=r.outcome,
        outcome_notes=r.outcome_notes,
        auth_number=r.auth_number,
        approved_procedure=r.approved_procedure,
        submitted_at=str(r.submitted_at) if r.submitted_at else None,
        created_at=str(r.created_at) if r.created_at else None,
        updated_at=str(r.updated_at) if r.updated_at else None,
    )


def _doc_response(d: AuthDocument) -> AuthDocumentResponse:
    return AuthDocumentResponse(
        id=str(d.id),
        auth_request_id=str(d.auth_request_id),
        doc_type=d.doc_type,
        file_name=d.file_name,
        s3_key=d.s3_key,
        mime_type=d.mime_type,
        size_bytes=d.size_bytes,
        extracted_data=d.extracted_data,
        created_at=str(d.created_at) if d.created_at else None,
    )


def _payer_profile_response(p: PayerAuthProfile) -> PayerProfileResponse:
    return PayerProfileResponse(
        id=str(p.id),
        payer_name=p.payer_name,
        payer_id=p.payer_id,
        approval_rate=p.approval_rate,
        avg_turnaround_days=p.avg_turnaround_days,
        required_documents=p.required_documents,
        tips=p.tips,
        common_denial_reasons=p.common_denial_reasons,
        updated_at=str(p.updated_at) if p.updated_at else None,
    )
