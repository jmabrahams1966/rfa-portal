"""Case Folder Integration Service for RFA-2 Portal.

Handles SFTP drops, CMS integrations (Guidewire, Duck Creek, Origami Risk),
and outbound webhooks for status change notifications.
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.models import (
    RFACase,
    RFASubmission,
    RFADocument,
    RFAOrganization,
    RFAAuditLog,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CMS field mapping per vendor
# ---------------------------------------------------------------------------

CMS_FIELD_MAPS: dict[str, dict[str, str]] = {
    "guidewire": {
        "claimNumber": "wcb_case_number",
        "claimantFullName": "claimant_name",
        "dateOfLoss": "date_of_injury",
        "employerName": "employer_name",
        "employerFEIN": "employer_fein",
        "carrierName": "carrier_name",
        "carrierCode": "carrier_code",
        "district": "district",
        "claimantRepName": "claimant_rep_name",
        "claimantRepAddress": "claimant_rep_address",
        "isVolunteer": "is_volunteer",
    },
    "duck_creek": {
        "claim_number": "wcb_case_number",
        "claimant_name": "claimant_name",
        "loss_date": "date_of_injury",
        "employer": "employer_name",
        "employer_fein": "employer_fein",
        "carrier": "carrier_name",
        "carrier_num": "carrier_code",
        "wcb_district": "district",
    },
    "origami_risk": {
        "claimNumber": "wcb_case_number",
        "injuredWorker": "claimant_name",
        "injuryDate": "date_of_injury",
        "employer": "employer_name",
        "fein": "employer_fein",
        "insurer": "carrier_name",
        "insurerCode": "carrier_code",
        "boardDistrict": "district",
    },
}

# Webhook event types
WEBHOOK_EVENTS = [
    "submission.created",
    "submission.submitted",
    "submission.accepted",
    "submission.rejected",
]

# File type detection by extension
_CASE_FILE_EXTENSIONS = {".csv", ".tsv", ".xlsx", ".xls"}
_DOCUMENT_EXTENSIONS = {".pdf", ".tiff", ".tif", ".png", ".jpg", ".jpeg", ".doc", ".docx"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date_flexible(value: Any) -> Any:
    """Parse a date string into a date object, tolerating multiple formats."""
    if value is None:
        return None
    if hasattr(value, "date"):
        return value if not hasattr(value, "hour") else value.date()
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%Y%m%d"):
            try:
                from datetime import datetime as dt
                return dt.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
    return None


def _map_cms_fields(cms_type: str, raw_data: dict[str, Any]) -> dict[str, Any]:
    """Map CMS-specific field names to our internal schema."""
    field_map = CMS_FIELD_MAPS.get(cms_type, {})
    mapped: dict[str, Any] = {}
    for src_key, target_key in field_map.items():
        if src_key in raw_data:
            mapped[target_key] = raw_data[src_key]
    # Pass through any unmapped fields into form_data for reference
    mapped["_raw_cms_data"] = raw_data
    return mapped


def _detect_file_type(file_path: str) -> str:
    """Detect whether a file is a case list or a document based on extension."""
    ext = Path(file_path).suffix.lower()
    if ext in _CASE_FILE_EXTENSIONS:
        return "case_list"
    if ext in _DOCUMENT_EXTENSIONS:
        return "document"
    return "unknown"


# ---------------------------------------------------------------------------
# SFTP Drop Processing
# ---------------------------------------------------------------------------

async def process_sftp_drop(
    file_path: str,
    org_id: uuid.UUID,
    db: AsyncSession,
) -> dict[str, Any]:
    """Process a file dropped via SFTP.

    Auto-detects whether the file is a case list CSV/Excel or an IME document PDF.
    For case lists, delegates to batch_service.import_cases_from_file.
    For documents, creates an RFADocument record linked to the most recent case.

    Returns: {file_type, action, details}
    """
    file_type = _detect_file_type(file_path)
    filename = Path(file_path).name

    if file_type == "case_list":
        # Read file and delegate to batch import
        from .batch_service import import_cases_from_file

        try:
            with open(file_path, "rb") as f:
                file_bytes = f.read()
        except FileNotFoundError:
            return {"file_type": "case_list", "action": "error", "details": f"File not found: {file_path}"}

        result = await import_cases_from_file(file_bytes, filename, org_id, db)
        return {"file_type": "case_list", "action": "imported", "details": result}

    elif file_type == "document":
        # Try to extract case number from filename (e.g., "WCL-2024-12345_IME_Report.pdf")
        stem = Path(file_path).stem
        parts = stem.split("_")
        case_number_candidate = parts[0] if parts else stem

        # Look up case
        case_result = await db.execute(
            select(RFACase).where(
                RFACase.org_id == org_id,
                RFACase.wcb_case_number == case_number_candidate,
            )
        )
        case = case_result.scalar_one_or_none()

        if not case:
            # Try to find most recent case for org as fallback
            case_result = await db.execute(
                select(RFACase)
                .where(RFACase.org_id == org_id)
                .order_by(RFACase.created_at.desc())
                .limit(1)
            )
            case = case_result.scalar_one_or_none()

        if not case:
            return {"file_type": "document", "action": "error", "details": "No matching case found and no cases exist for this org"}

        # Find active submission for the case
        sub_result = await db.execute(
            select(RFASubmission)
            .where(RFASubmission.case_id == case.id)
            .order_by(RFASubmission.created_at.desc())
            .limit(1)
        )
        submission = sub_result.scalar_one_or_none()

        if not submission:
            # Create a draft submission
            submission = RFASubmission(
                id=uuid.uuid4(),
                org_id=org_id,
                case_id=case.id,
                created_by=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                status="draft",
            )
            db.add(submission)
            await db.flush()

        # Detect doc type from filename
        doc_type = "other"
        lower_name = filename.lower()
        if "ime" in lower_name:
            doc_type = "ime_report"
        elif "board" in lower_name or "decision" in lower_name:
            doc_type = "board_decision"
        elif "medical" in lower_name or "record" in lower_name:
            doc_type = "medical_record"
        elif "operative" in lower_name:
            doc_type = "operative_note"
        elif "wage" in lower_name:
            doc_type = "wage_records"
        elif "surveillance" in lower_name:
            doc_type = "surveillance"

        # S3 key would be generated by upload service; for SFTP we use the local path as placeholder
        s3_key = f"sftp/{org_id}/{case.wcb_case_number}/{filename}"

        doc = RFADocument(
            id=uuid.uuid4(),
            submission_id=submission.id,
            org_id=org_id,
            doc_type=doc_type,
            file_name=filename,
            s3_key=s3_key,
            mime_type=_guess_mime(filename),
            size_bytes=Path(file_path).stat().st_size if Path(file_path).exists() else None,
        )
        db.add(doc)

        # Audit
        audit = RFAAuditLog(
            id=uuid.uuid4(),
            org_id=org_id,
            action="sftp_document_ingested",
            resource_type="document",
            resource_id=doc.id,
            description=f"SFTP drop: {filename} -> case {case.wcb_case_number} ({doc_type})",
        )
        db.add(audit)
        await db.flush()

        return {
            "file_type": "document",
            "action": "ingested",
            "details": {
                "document_id": str(doc.id),
                "case_id": str(case.id),
                "submission_id": str(submission.id),
                "doc_type": doc_type,
                "filename": filename,
            },
        }

    else:
        return {"file_type": "unknown", "action": "skipped", "details": f"Unsupported file type: {filename}"}


def _guess_mime(filename: str) -> str:
    """Guess MIME type from extension."""
    ext = Path(filename).suffix.lower()
    mime_map = {
        ".pdf": "application/pdf",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".csv": "text/csv",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    return mime_map.get(ext, "application/octet-stream")


# ---------------------------------------------------------------------------
# CMS Ingestion
# ---------------------------------------------------------------------------

async def ingest_from_cms(
    cms_type: str,
    case_data: dict[str, Any],
    org_id: uuid.UUID,
    db: AsyncSession,
) -> dict[str, Any]:
    """Accept case data from external CMS via webhook. Create/update RFACase.

    Supported cms_type values: guidewire, duck_creek, origami_risk

    Returns: {action: created|updated, case_id, wcb_case_number}
    """
    if cms_type not in CMS_FIELD_MAPS:
        return {"action": "error", "error": f"Unsupported CMS type: {cms_type}. Supported: {list(CMS_FIELD_MAPS.keys())}"}

    mapped = _map_cms_fields(cms_type, case_data)
    wcb_case_number = mapped.get("wcb_case_number")

    if not wcb_case_number:
        return {"action": "error", "error": "No case number found in payload"}

    # Check if case exists
    existing_result = await db.execute(
        select(RFACase).where(
            RFACase.org_id == org_id,
            RFACase.wcb_case_number == str(wcb_case_number),
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        # Update existing case
        update_fields: dict[str, Any] = {}
        if mapped.get("claimant_name"):
            update_fields["claimant_name_encrypted"] = mapped["claimant_name"]
        if mapped.get("date_of_injury"):
            update_fields["date_of_injury"] = _parse_date_flexible(mapped["date_of_injury"])
        if mapped.get("employer_name"):
            update_fields["employer_name"] = mapped["employer_name"]
        if mapped.get("employer_fein"):
            update_fields["employer_fein"] = mapped["employer_fein"]
        if mapped.get("carrier_name"):
            update_fields["carrier_name"] = mapped["carrier_name"]
        if mapped.get("carrier_code"):
            update_fields["carrier_code"] = mapped["carrier_code"]
        if mapped.get("district"):
            update_fields["district"] = mapped["district"]
        if mapped.get("claimant_rep_name"):
            update_fields["claimant_rep_name"] = mapped["claimant_rep_name"]
        if mapped.get("claimant_rep_address"):
            update_fields["claimant_rep_address"] = mapped["claimant_rep_address"]

        if update_fields:
            await db.execute(
                update(RFACase)
                .where(RFACase.id == existing.id)
                .values(**update_fields)
            )

        audit = RFAAuditLog(
            id=uuid.uuid4(),
            org_id=org_id,
            action="cms_case_updated",
            resource_type="case",
            resource_id=existing.id,
            description=f"CMS ({cms_type}) updated case {wcb_case_number}",
        )
        db.add(audit)
        await db.flush()

        return {"action": "updated", "case_id": str(existing.id), "wcb_case_number": str(wcb_case_number)}

    else:
        # Create new case
        case = RFACase(
            id=uuid.uuid4(),
            org_id=org_id,
            wcb_case_number=str(wcb_case_number),
            claimant_name_encrypted=mapped.get("claimant_name", ""),
            date_of_injury=_parse_date_flexible(mapped.get("date_of_injury")),
            employer_name=mapped.get("employer_name", ""),
            employer_fein=mapped.get("employer_fein"),
            is_volunteer=bool(mapped.get("is_volunteer", False)),
            claimant_rep_name=mapped.get("claimant_rep_name"),
            claimant_rep_address=mapped.get("claimant_rep_address"),
            carrier_name=mapped.get("carrier_name"),
            carrier_code=mapped.get("carrier_code"),
            district=mapped.get("district"),
        )
        db.add(case)

        audit = RFAAuditLog(
            id=uuid.uuid4(),
            org_id=org_id,
            action="cms_case_created",
            resource_type="case",
            resource_id=case.id,
            description=f"CMS ({cms_type}) created case {wcb_case_number}",
        )
        db.add(audit)
        await db.flush()

        return {"action": "created", "case_id": str(case.id), "wcb_case_number": str(wcb_case_number)}


# ---------------------------------------------------------------------------
# Outbound Webhooks
# ---------------------------------------------------------------------------

async def send_webhook(
    org_id: uuid.UUID,
    event_type: str,
    payload: dict[str, Any],
    db: AsyncSession,
) -> dict[str, Any]:
    """Send webhook notification to carrier's CMS when filing status changes.

    Event types: submission.created, submission.submitted,
                 submission.accepted, submission.rejected

    Webhook URLs are stored in the organization's settings.
    Returns: {sent: bool, status_code, response_body} or {sent: false, error}
    """
    if event_type not in WEBHOOK_EVENTS:
        return {"sent": False, "error": f"Invalid event type: {event_type}. Valid: {WEBHOOK_EVENTS}"}

    # Load org to get webhook URL
    org_result = await db.execute(
        select(RFAOrganization).where(RFAOrganization.id == org_id)
    )
    org = org_result.scalar_one_or_none()
    if not org:
        return {"sent": False, "error": "Organization not found"}

    # Webhook URLs are stored as JSON in the contact_email field's companion
    # In production, this would be a dedicated webhook_config column.
    # For now, we check a convention: if the org has a contact_email that contains
    # webhook config, or we look for a webhook URL pattern.
    # We'll use a simple approach: store webhook URLs in a module-level registry
    # keyed by org_id, which can be populated via API.
    webhook_url = _webhook_registry.get(str(org_id))

    if not webhook_url:
        logger.info("No webhook URL configured for org %s, skipping", org_id)
        return {"sent": False, "error": "No webhook URL configured for this organization"}

    webhook_payload = {
        "event": event_type,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "org_id": str(org_id),
        "data": payload,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                webhook_url,
                json=webhook_payload,
                headers={
                    "Content-Type": "application/json",
                    "X-RFA-Event": event_type,
                    "X-RFA-Org-Id": str(org_id),
                },
            )

        audit = RFAAuditLog(
            id=uuid.uuid4(),
            org_id=org_id,
            action="webhook_sent",
            resource_type="webhook",
            description=f"Webhook {event_type} sent to {webhook_url} (HTTP {response.status_code})",
        )
        db.add(audit)
        await db.flush()

        return {
            "sent": True,
            "status_code": response.status_code,
            "response_body": response.text[:500],
        }

    except httpx.TimeoutException:
        logger.error("Webhook timeout for org %s to %s", org_id, webhook_url)
        return {"sent": False, "error": "Webhook request timed out"}
    except Exception as exc:
        logger.error("Webhook error for org %s: %s", org_id, str(exc))
        return {"sent": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Webhook URL Registry (in-memory; swap for DB column in production)
# ---------------------------------------------------------------------------

_webhook_registry: dict[str, str] = {}


def register_webhook_url(org_id: uuid.UUID, url: str) -> None:
    """Register a webhook URL for an organization."""
    _webhook_registry[str(org_id)] = url
    logger.info("Registered webhook URL for org %s: %s", org_id, url)


def unregister_webhook_url(org_id: uuid.UUID) -> None:
    """Remove a webhook URL for an organization."""
    _webhook_registry.pop(str(org_id), None)


def get_webhook_url(org_id: uuid.UUID) -> str | None:
    """Get the registered webhook URL for an organization."""
    return _webhook_registry.get(str(org_id))
