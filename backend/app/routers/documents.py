"""Documents router — upload and manage supporting documents."""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..models.models import RFADocument, RFASubmission
from ..middleware.auth import get_current_user, require_adjuster

router = APIRouter(prefix="/documents", tags=["documents"])

VALID_DOC_TYPES = {"ime_report", "board_decision", "medical_record", "operative_note", "wage_records", "surveillance", "other"}


# ---------- Schemas ----------
class DocumentCreate(BaseModel):
    submission_id: uuid.UUID
    doc_type: str
    file_name: str
    s3_key: str
    clean_text: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None


class DocumentResponse(BaseModel):
    id: uuid.UUID
    submission_id: uuid.UUID
    org_id: uuid.UUID
    doc_type: str
    file_name: str
    s3_key: str
    clean_text: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    created_at: str | None = None


# ---------- Endpoints ----------
@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    submission_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(RFADocument).where(
        RFADocument.submission_id == submission_id,
        RFADocument.org_id == current_user.org_id,
    )
    result = await db.execute(query)
    docs = result.scalars().all()
    return [_doc_to_response(d) for d in docs]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await _get_doc_or_404(db, document_id, current_user.org_id)
    return _doc_to_response(doc)


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    body: DocumentCreate,
    current_user=Depends(require_adjuster),
    db: AsyncSession = Depends(get_db),
):
    if body.doc_type not in VALID_DOC_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid doc_type. Must be one of: {', '.join(sorted(VALID_DOC_TYPES))}",
        )

    # Verify submission belongs to org
    sub_result = await db.execute(
        select(RFASubmission).where(
            RFASubmission.id == body.submission_id,
            RFASubmission.org_id == current_user.org_id,
        )
    )
    if not sub_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    doc = RFADocument(
        id=uuid.uuid4(),
        submission_id=body.submission_id,
        org_id=current_user.org_id,
        doc_type=body.doc_type,
        file_name=body.file_name,
        s3_key=body.s3_key,
        clean_text=body.clean_text,
        mime_type=body.mime_type,
        size_bytes=body.size_bytes,
    )
    db.add(doc)
    await db.flush()
    return _doc_to_response(doc)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    current_user=Depends(require_adjuster),
    db: AsyncSession = Depends(get_db),
):
    doc = await _get_doc_or_404(db, document_id, current_user.org_id)
    await db.delete(doc)
    await db.flush()


# ---------- Helpers ----------
async def _get_doc_or_404(db: AsyncSession, doc_id: uuid.UUID, org_id: uuid.UUID) -> RFADocument:
    result = await db.execute(
        select(RFADocument).where(RFADocument.id == doc_id, RFADocument.org_id == org_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc


def _doc_to_response(doc: RFADocument) -> DocumentResponse:
    return DocumentResponse(
        id=doc.id,
        submission_id=doc.submission_id,
        org_id=doc.org_id,
        doc_type=doc.doc_type,
        file_name=doc.file_name,
        s3_key=doc.s3_key,
        clean_text=doc.clean_text,
        mime_type=doc.mime_type,
        size_bytes=doc.size_bytes,
        created_at=str(doc.created_at) if doc.created_at else None,
    )
