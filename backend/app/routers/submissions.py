"""Submissions router — full AIRA submission lifecycle.

Endpoints:
  POST   /submissions                      — create draft
  GET    /submissions                      — list with status filter
  GET    /submissions/{id}                 — detail with documents + extractions
  PUT    /submissions/{id}                 — update draft
  POST   /submissions/{id}/upload          — upload document (S3 + PHI + AI)
  POST   /submissions/{id}/extract         — manual AI extraction
  POST   /submissions/{id}/validate        — WCB business rule validation
  POST   /submissions/{id}/build-xml       — generate XML payload
  POST   /submissions/{id}/submit          — submit to WCB (mock)
  GET    /submissions/{id}/pdf             — party-service PDF download
  POST   /submissions/{id}/attest          — accept attestation
"""
import uuid
import random
import base64
import logging
from datetime import date, datetime, timezone
from io import BytesIO

from fastapi import (
    APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models.models import (
    RFASubmission, RFACase, RFADocument, RFAExtraction, RFAAuditLog,
)
from ..middleware.auth import get_current_user, require_adjuster
from ..services.phi_service import deidentify

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/submissions", tags=["submissions"])

VALID_DOC_TYPES = {
    "ime_report", "board_decision", "medical_record",
    "operative_note", "wage_records", "surveillance", "other",
}


# ── Request / Response schemas ──────────────────────────────────────────────
class SubmissionCreate(BaseModel):
    case_id: str
    reason_codes: list[str] | None = None
    form_data: dict | None = None


class SubmissionUpdate(BaseModel):
    form_data: dict | None = None
    narrative: str | None = None
    reason_codes: list[str] | None = None


class DocumentResponse(BaseModel):
    id: str
    doc_type: str
    file_name: str
    s3_key: str
    mime_type: str | None = None
    size_bytes: int | None = None
    created_at: str | None = None


class ExtractionResponse(BaseModel):
    id: str
    document_id: str | None = None
    reason_codes: list | None = None
    extracted_fields: dict | None = None
    confidence: str | None = None
    narrative_text: str | None = None
    model_version: str | None = None
    created_at: str | None = None


class SubmissionResponse(BaseModel):
    id: str
    org_id: str
    case_id: str
    created_by: str
    status: str
    reason_codes: list | None = None
    form_data: dict | None = None
    narrative: str | None = None
    xml_payload: str | None = None
    wcb_submission_id: str | None = None
    wcb_document_id: str | None = None
    wcb_status: str | None = None
    wcb_errors: list | None = None
    certification_date: date | None = None
    attestation_accepted: bool = False
    submitted_at: str | None = None
    pdf_s3_key: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class SubmissionDetailResponse(SubmissionResponse):
    documents: list[DocumentResponse] = []
    extractions: list[ExtractionResponse] = []


class ValidationResult(BaseModel):
    valid: bool
    errors: list[str] = []
    warnings: list[str] = []


class AttestRequest(BaseModel):
    accepted: bool = True


# ═══════════════════════════════════════════════════════════════════════════
# CRUD
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
async def create_submission(
    body: SubmissionCreate,
    current_user=Depends(require_adjuster),
    db: AsyncSession = Depends(get_db),
):
    """Create a new draft submission for a case."""
    case = await _get_case_for_org(db, body.case_id, current_user.org_id)

    submission = RFASubmission(
        id=uuid.uuid4(),
        org_id=current_user.org_id,
        case_id=case.id,
        created_by=current_user.id,
        status="draft",
        reason_codes=body.reason_codes,
        form_data=body.form_data,
    )
    db.add(submission)

    _audit(db, current_user, "submission_created", "submission", submission.id,
           f"Created draft submission for case {case.wcb_case_number}")
    await db.flush()
    return _to_response(submission)


@router.get("/", response_model=list[SubmissionResponse])
async def list_submissions(
    status_filter: str | None = Query(None, alias="status"),
    case_id: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List submissions with optional status and case filters."""
    query = select(RFASubmission).where(RFASubmission.org_id == current_user.org_id)
    if status_filter:
        query = query.where(RFASubmission.status == status_filter)
    if case_id:
        query = query.where(RFASubmission.case_id == uuid.UUID(case_id))
    query = query.order_by(RFASubmission.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    return [_to_response(s) for s in result.scalars().all()]


@router.get("/{submission_id}", response_model=SubmissionDetailResponse)
async def get_submission(
    submission_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get submission detail with documents and extractions."""
    result = await db.execute(
        select(RFASubmission)
        .options(
            selectinload(RFASubmission.documents),
            selectinload(RFASubmission.extractions),
        )
        .where(RFASubmission.id == submission_id, RFASubmission.org_id == current_user.org_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    resp = SubmissionDetailResponse(**_to_response(submission).model_dump())
    resp.documents = [_doc_response(d) for d in (submission.documents or [])]
    resp.extractions = [_ext_response(e) for e in (submission.extractions or [])]
    return resp


@router.put("/{submission_id}", response_model=SubmissionResponse)
async def update_submission(
    submission_id: uuid.UUID,
    body: SubmissionUpdate,
    current_user=Depends(require_adjuster),
    db: AsyncSession = Depends(get_db),
):
    """Update a draft submission (form_data, narrative, reason_codes)."""
    submission = await _get_or_404(db, submission_id, current_user.org_id)

    if submission.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft submissions can be updated")

    if body.narrative is not None and len(body.narrative) > 500:
        raise HTTPException(status_code=400, detail="Narrative must be 500 characters or fewer")

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(submission, key, value)

    _audit(db, current_user, "submission_updated", "submission", submission.id,
           "Updated draft submission")
    await db.flush()
    return _to_response(submission)


# ═══════════════════════════════════════════════════════════════════════════
# Document Upload
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/{submission_id}/upload", response_model=DocumentResponse)
async def upload_document(
    submission_id: uuid.UUID,
    file: UploadFile = File(...),
    doc_type: str = Form("other"),
    current_user=Depends(require_adjuster),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a document to a submission.

    - Attempts S3 upload with SSE-AES256 encryption
    - Falls back to base64 if S3 is unavailable
    - Extracts text from PDF (filename fallback if extraction fails)
    - Runs PHI de-identification on extracted text
    - Triggers AI extraction on clean text
    """
    submission = await _get_or_404(db, submission_id, current_user.org_id)

    if doc_type not in VALID_DOC_TYPES:
        raise HTTPException(status_code=422, detail=f"Invalid doc_type. Must be one of: {', '.join(sorted(VALID_DOC_TYPES))}")

    file_bytes = await file.read()
    file_name = file.filename or "untitled"
    mime_type = file.content_type or "application/octet-stream"
    size_bytes = len(file_bytes)

    # ── S3 upload (with base64 fallback) ────────────────────────────────
    s3_key = f"rfa-docs/{current_user.org_id}/{submission_id}/{uuid.uuid4()}/{file_name}"
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

    # ── Save Document record ────────────────────────────────────────────
    doc = RFADocument(
        id=uuid.uuid4(),
        submission_id=submission.id,
        org_id=current_user.org_id,
        doc_type=doc_type,
        file_name=file_name,
        s3_key=s3_key,
        clean_text=clean_text,
        mime_type=mime_type,
        size_bytes=size_bytes,
    )
    db.add(doc)
    await db.flush()

    # ── AI Extraction ───────────────────────────────────────────────────
    try:
        from ..services.extraction_service import extract_rfa2_fields
        extraction_result = await extract_rfa2_fields(clean_text)
        extraction = RFAExtraction(
            id=uuid.uuid4(),
            submission_id=submission.id,
            document_id=doc.id,
            reason_codes=extraction_result.get("reason_codes"),
            extracted_fields=extraction_result.get("fields"),
            confidence=extraction_result.get("confidence", "medium"),
            narrative_text=extraction_result.get("narrative"),
            model_version=extraction_result.get("model_version", "claude-sonnet-4"),
        )
        db.add(extraction)
        await db.flush()
    except Exception as exc:
        logger.warning("AI extraction failed for doc %s: %s", doc.id, exc)

    _audit(db, current_user, "document_uploaded", "document", doc.id,
           f"Uploaded {file_name} ({doc_type}) to submission {submission_id}")
    await db.flush()

    return _doc_response(doc)


# ═══════════════════════════════════════════════════════════════════════════
# Manual AI Extraction
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/{submission_id}/extract", response_model=list[ExtractionResponse])
async def trigger_extraction(
    submission_id: uuid.UUID,
    current_user=Depends(require_adjuster),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger AI extraction on all documents in this submission."""
    result = await db.execute(
        select(RFASubmission)
        .options(selectinload(RFASubmission.documents))
        .where(RFASubmission.id == submission_id, RFASubmission.org_id == current_user.org_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if not submission.documents:
        raise HTTPException(status_code=400, detail="No documents to extract from")

    from ..services.extraction_service import extract_rfa2_fields

    extractions_out: list[RFAExtraction] = []
    for doc in submission.documents:
        if not doc.clean_text:
            continue
        try:
            res = await extract_rfa2_fields(doc.clean_text)
        except Exception as exc:
            logger.warning("Extraction failed for doc %s: %s", doc.id, exc)
            continue

        ext = RFAExtraction(
            id=uuid.uuid4(),
            submission_id=submission.id,
            document_id=doc.id,
            reason_codes=res.get("reason_codes"),
            extracted_fields=res.get("fields"),
            confidence=res.get("confidence", "medium"),
            narrative_text=res.get("narrative"),
            model_version=res.get("model_version", "claude-sonnet-4"),
        )
        db.add(ext)
        extractions_out.append(ext)

    _audit(db, current_user, "extraction_triggered", "submission", submission.id,
           f"Manual extraction on {len(extractions_out)} documents")
    await db.flush()

    return [_ext_response(e) for e in extractions_out]


# ═══════════════════════════════════════════════════════════════════════════
# Validate
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/{submission_id}/validate", response_model=ValidationResult)
async def validate_submission_endpoint(
    submission_id: uuid.UUID,
    current_user=Depends(require_adjuster),
    db: AsyncSession = Depends(get_db),
):
    """Run WCB business rule validation on the submission."""
    submission = await _get_or_404(db, submission_id, current_user.org_id)

    try:
        from ..services.xml_service import validate_submission as run_validation
        result = await run_validation(submission)
        errors = result.get("errors", [])
        warnings = result.get("warnings", [])
    except (ImportError, Exception) as exc:
        logger.info("xml_service validation unavailable (%s), using inline rules", exc)
        errors, warnings = _inline_validate(submission)

    valid = len(errors) == 0

    if valid and submission.status == "draft":
        submission.status = "validated"
        _audit(db, current_user, "submission_validated", "submission", submission.id,
               "Submission passed validation")
        await db.flush()

    return ValidationResult(valid=valid, errors=errors, warnings=warnings)


# ═══════════════════════════════════════════════════════════════════════════
# Build XML
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/{submission_id}/build-xml")
async def build_xml(
    submission_id: uuid.UUID,
    current_user=Depends(require_adjuster),
    db: AsyncSession = Depends(get_db),
):
    """Generate the WCB XML payload and store it on the submission."""
    submission = await _get_or_404(db, submission_id, current_user.org_id)

    try:
        from ..services.xml_service import build_rfa2_xml
        xml_payload = await build_rfa2_xml(submission)
    except (ImportError, Exception) as exc:
        logger.info("xml_service unavailable (%s), using inline builder", exc)
        xml_payload = _inline_build_xml(submission)

    submission.xml_payload = xml_payload

    _audit(db, current_user, "xml_generated", "submission", submission.id,
           "Generated XML payload")
    await db.flush()

    return {"submission_id": str(submission.id), "xml_payload": xml_payload}


# ═══════════════════════════════════════════════════════════════════════════
# Submit to WCB (mock)
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/{submission_id}/submit", response_model=SubmissionResponse)
async def submit_to_wcb(
    submission_id: uuid.UUID,
    current_user=Depends(require_adjuster),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit to WCB API (mock).

    In production this would POST to the real WCB OnBoard API.
    Generates a fake WCB submission ID and document ID, sets status to submitted.
    """
    submission = await _get_or_404(db, submission_id, current_user.org_id)

    if submission.status not in ("draft", "validated"):
        raise HTTPException(status_code=400,
                            detail=f"Cannot submit a submission with status '{submission.status}'")

    if not submission.attestation_accepted:
        raise HTTPException(status_code=400,
                            detail="Attestation must be accepted before submission")

    # Build XML if missing
    if not submission.xml_payload:
        try:
            from ..services.xml_service import build_rfa2_xml
            submission.xml_payload = await build_rfa2_xml(submission)
        except Exception:
            submission.xml_payload = _inline_build_xml(submission)

    # Mock WCB response
    wcb_submission_id = f"WCB-2026-{random.randint(100000, 999999)}"
    wcb_document_id = f"DOC-{uuid.uuid4().hex[:12].upper()}"

    submission.status = "submitted"
    submission.wcb_submission_id = wcb_submission_id
    submission.wcb_document_id = wcb_document_id
    submission.wcb_status = "received"
    submission.submitted_at = datetime.now(timezone.utc)

    _audit(db, current_user, "submission_submitted", "submission", submission.id,
           f"Submitted to WCB (mock): {wcb_submission_id}")
    await db.flush()

    return _to_response(submission)


# ═══════════════════════════════════════════════════════════════════════════
# PDF Download
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/{submission_id}/pdf")
async def download_pdf(
    submission_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate / download a party-service PDF for the submission."""
    submission = await _get_or_404(db, submission_id, current_user.org_id)

    case_result = await db.execute(select(RFACase).where(RFACase.id == submission.case_id))
    case = case_result.scalar_one_or_none()

    lines = [
        "AIRA Submission — Party Service Copy",
        "=" * 50,
        f"Submission ID: {submission.id}",
        f"WCB Submission ID: {submission.wcb_submission_id or 'N/A'}",
        f"Status: {submission.status}",
        f"Case Number: {case.wcb_case_number if case else 'N/A'}",
        f"Reason Codes: {', '.join(submission.reason_codes or [])}",
        f"Narrative: {submission.narrative or 'N/A'}",
        f"Attestation Accepted: {submission.attestation_accepted}",
        f"Certification Date: {submission.certification_date or 'N/A'}",
        f"Submitted At: {submission.submitted_at or 'N/A'}",
        f"Created At: {submission.created_at}",
    ]

    # Try reportlab for real PDF, fall back to plain text
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas as pdf_canvas

        buf = BytesIO()
        c = pdf_canvas.Canvas(buf, pagesize=letter)
        w, h = letter

        c.setFont("Helvetica-Bold", 16)
        c.drawString(72, h - 72, lines[0])
        c.setFont("Helvetica", 11)
        y = h - 110
        for line in lines[2:]:
            c.drawString(72, y, line)
            y -= 18
        c.save()
        buf.seek(0)

        return StreamingResponse(
            buf,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=RFA2_{submission_id}.pdf"},
        )
    except ImportError:
        content = "\n".join(lines).encode()
        return StreamingResponse(
            BytesIO(content),
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename=RFA2_{submission_id}.txt"},
        )


# ═══════════════════════════════════════════════════════════════════════════
# Attestation
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/{submission_id}/attest", response_model=SubmissionResponse)
async def accept_attestation(
    submission_id: uuid.UUID,
    body: AttestRequest,
    current_user=Depends(require_adjuster),
    db: AsyncSession = Depends(get_db),
):
    """Accept (or revoke) the certification / attestation for a submission."""
    submission = await _get_or_404(db, submission_id, current_user.org_id)

    submission.attestation_accepted = body.accepted
    submission.certification_date = date.today()

    _audit(db, current_user, "attestation_accepted", "submission", submission.id,
           f"Attestation {'accepted' if body.accepted else 'revoked'}")
    await db.flush()

    return _to_response(submission)


# ═══════════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════════

async def _get_or_404(db: AsyncSession, sid: uuid.UUID, org_id) -> RFASubmission:
    result = await db.execute(
        select(RFASubmission).where(RFASubmission.id == sid, RFASubmission.org_id == org_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    return sub


async def _get_case_for_org(db: AsyncSession, case_id: str, org_id) -> RFACase:
    result = await db.execute(
        select(RFACase).where(RFACase.id == uuid.UUID(case_id), RFACase.org_id == org_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


def _audit(db, user, action: str, resource_type: str, resource_id, description: str):
    db.add(RFAAuditLog(
        id=uuid.uuid4(),
        org_id=user.org_id,
        user_id=user.id,
        user_email=user.email,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        description=description,
    ))


def _to_response(s: RFASubmission) -> SubmissionResponse:
    return SubmissionResponse(
        id=str(s.id),
        org_id=str(s.org_id),
        case_id=str(s.case_id),
        created_by=str(s.created_by),
        status=s.status,
        reason_codes=s.reason_codes,
        form_data=s.form_data,
        narrative=s.narrative,
        xml_payload=s.xml_payload,
        wcb_submission_id=s.wcb_submission_id,
        wcb_document_id=s.wcb_document_id,
        wcb_status=s.wcb_status,
        wcb_errors=s.wcb_errors,
        certification_date=s.certification_date,
        attestation_accepted=s.attestation_accepted,
        submitted_at=str(s.submitted_at) if s.submitted_at else None,
        pdf_s3_key=s.pdf_s3_key,
        created_at=str(s.created_at) if s.created_at else None,
        updated_at=str(s.updated_at) if s.updated_at else None,
    )


def _doc_response(d: RFADocument) -> DocumentResponse:
    return DocumentResponse(
        id=str(d.id),
        doc_type=d.doc_type,
        file_name=d.file_name,
        s3_key=d.s3_key,
        mime_type=d.mime_type,
        size_bytes=d.size_bytes,
        created_at=str(d.created_at) if d.created_at else None,
    )


def _ext_response(e: RFAExtraction) -> ExtractionResponse:
    return ExtractionResponse(
        id=str(e.id),
        document_id=str(e.document_id) if e.document_id else None,
        reason_codes=e.reason_codes,
        extracted_fields=e.extracted_fields,
        confidence=e.confidence,
        narrative_text=e.narrative_text,
        model_version=e.model_version,
        created_at=str(e.created_at) if e.created_at else None,
    )


def _inline_validate(submission: RFASubmission) -> tuple[list[str], list[str]]:
    """Fallback validation when xml_service is not available."""
    errors: list[str] = []
    warnings: list[str] = []

    if not submission.reason_codes:
        errors.append("At least one reason code is required")
    if not submission.form_data:
        errors.append("Form data is required")
    if submission.narrative and len(submission.narrative) > 500:
        errors.append("Narrative exceeds 500 character limit")
    if not submission.narrative:
        warnings.append("No narrative provided — consider adding one")

    fd = submission.form_data or {}
    if not fd.get("claimant_name"):
        warnings.append("Claimant name is missing from form data")
    if not fd.get("date_of_injury"):
        warnings.append("Date of injury is missing from form data")
    if not fd.get("wcb_case_number"):
        warnings.append("WCB case number is missing from form data")

    return errors, warnings


def _inline_build_xml(submission: RFASubmission) -> str:
    """Fallback XML builder when xml_service is not available."""
    fd = submission.form_data or {}
    rc_xml = "".join(f"    <ReasonCode>{rc}</ReasonCode>\n" for rc in (submission.reason_codes or []))

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<RFA2Submission xmlns="urn:ny-wcb:rfa2">
  <SubmissionId>{submission.id}</SubmissionId>
  <CaseId>{submission.case_id}</CaseId>
  <Status>{submission.status}</Status>
  <ReasonCodes>
{rc_xml}  </ReasonCodes>
  <Narrative>{submission.narrative or ''}</Narrative>
  <FormData>
    <ClaimantName>{fd.get('claimant_name', '')}</ClaimantName>
    <DateOfInjury>{fd.get('date_of_injury', '')}</DateOfInjury>
    <WCBCaseNumber>{fd.get('wcb_case_number', '')}</WCBCaseNumber>
    <EmployerName>{fd.get('employer_name', '')}</EmployerName>
  </FormData>
  <CertificationDate>{submission.certification_date or ''}</CertificationDate>
  <AttestationAccepted>{str(submission.attestation_accepted).lower()}</AttestationAccepted>
</RFA2Submission>"""
