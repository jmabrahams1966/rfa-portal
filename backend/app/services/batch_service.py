"""Bulk Import & Batch Filing Service for AIRA.

Handles CSV/Excel case imports, batch validation, XML generation,
and batch submission to WCB.
"""

import csv
import io
import logging
import uuid
from datetime import datetime, date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.models import RFACase, RFASubmission, RFAAuditLog

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Column mapping profiles for common carrier export formats
# ---------------------------------------------------------------------------

COLUMN_MAPPINGS: dict[str, dict[str, str]] = {
    "guidewire": {
        "ClaimNumber": "wcb_case_number",
        "ClaimantFullName": "claimant_name",
        "ClaimantFirstName": "claimant_first_name",
        "ClaimantLastName": "claimant_last_name",
        "DateOfLoss": "date_of_injury",
        "EmployerName": "employer_name",
        "EmployerFEIN": "employer_fein",
        "CarrierName": "carrier_name",
        "CarrierCode": "carrier_code",
        "District": "district",
        "DenialReasonCode": "reason_codes",
        "ClaimantRepName": "claimant_rep_name",
        "ClaimantRepAddress": "claimant_rep_address",
        "IsVolunteer": "is_volunteer",
    },
    "duck_creek": {
        "Claim_Number": "wcb_case_number",
        "Claimant_Name": "claimant_name",
        "Loss_Date": "date_of_injury",
        "Employer": "employer_name",
        "Employer_FEIN": "employer_fein",
        "Carrier": "carrier_name",
        "Carrier_Num": "carrier_code",
        "WCB_District": "district",
        "Reason_Code": "reason_codes",
    },
    "origami_risk": {
        "claim_number": "wcb_case_number",
        "injured_worker": "claimant_name",
        "injury_date": "date_of_injury",
        "employer": "employer_name",
        "fein": "employer_fein",
        "insurer": "carrier_name",
        "insurer_code": "carrier_code",
        "board_district": "district",
        "denial_reason": "reason_codes",
    },
    "generic": {
        "wcb_case_number": "wcb_case_number",
        "case_number": "wcb_case_number",
        "claim_number": "wcb_case_number",
        "claimant_name": "claimant_name",
        "claimant": "claimant_name",
        "date_of_injury": "date_of_injury",
        "injury_date": "date_of_injury",
        "doi": "date_of_injury",
        "employer_name": "employer_name",
        "employer": "employer_name",
        "employer_fein": "employer_fein",
        "fein": "employer_fein",
        "carrier_name": "carrier_name",
        "carrier": "carrier_name",
        "carrier_code": "carrier_code",
        "district": "district",
        "reason_codes": "reason_codes",
        "reason_code": "reason_codes",
        "claimant_rep_name": "claimant_rep_name",
        "claimant_rep_address": "claimant_rep_address",
        "is_volunteer": "is_volunteer",
    },
}

# In-memory batch status tracker (swap for Redis in production)
_batch_status: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detect_mapping(headers: list[str]) -> dict[str, str]:
    """Auto-detect column mapping by matching headers against known profiles."""
    headers_lower = {h.strip(): h.strip() for h in headers}

    for profile_name in ("guidewire", "duck_creek", "origami_risk"):
        profile = COLUMN_MAPPINGS[profile_name]
        matched = sum(1 for h in headers if h.strip() in profile)
        if matched >= 3:
            logger.info("Detected column profile: %s (matched %d columns)", profile_name, matched)
            return profile

    # Fall back to generic (case-insensitive match)
    generic = COLUMN_MAPPINGS["generic"]
    mapping: dict[str, str] = {}
    for h in headers:
        key = h.strip().lower().replace(" ", "_")
        if key in generic:
            mapping[h.strip()] = generic[key]
    return mapping


def _parse_date(value: str | None) -> date | None:
    """Try common date formats."""
    if not value or not value.strip():
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y", "%Y%m%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _parse_bool(value: str | None) -> bool:
    if not value:
        return False
    return value.strip().lower() in ("true", "yes", "1", "y")


def _parse_reason_codes(value: str | None) -> list[str] | None:
    """Parse reason codes from comma- or semicolon-separated string."""
    if not value or not value.strip():
        return None
    separators = [";", ",", "|"]
    for sep in separators:
        if sep in value:
            return [c.strip() for c in value.split(sep) if c.strip()]
    return [value.strip()]


def _parse_csv_bytes(file_bytes: bytes) -> tuple[list[str], list[dict[str, str]]]:
    """Parse CSV bytes into headers and rows."""
    text = file_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    rows = list(reader)
    return headers, rows


def _parse_excel_bytes(file_bytes: bytes) -> tuple[list[str], list[dict[str, str]]]:
    """Parse Excel bytes into headers and rows. Requires openpyxl."""
    try:
        import openpyxl
    except ImportError:
        raise RuntimeError("openpyxl is required for Excel file parsing. Install with: pip install openpyxl")

    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    headers = [str(c) if c else "" for c in next(rows_iter)]
    rows: list[dict[str, str]] = []
    for row in rows_iter:
        row_dict = {headers[i]: str(row[i]) if row[i] is not None else "" for i in range(len(headers))}
        rows.append(row_dict)
    wb.close()
    return headers, rows


# ---------------------------------------------------------------------------
# Main service functions
# ---------------------------------------------------------------------------

async def import_cases_from_file(
    file_bytes: bytes,
    filename: str,
    org_id: uuid.UUID,
    db: AsyncSession,
) -> dict[str, Any]:
    """Parse CSV/Excel of cases. Create RFACase + RFASubmission for each row.

    Returns: {imported: int, skipped: int, errors: list[dict]}
    """
    batch_id = str(uuid.uuid4())
    _batch_status[batch_id] = {
        "operation": "import",
        "status": "in_progress",
        "total": 0,
        "processed": 0,
        "imported": 0,
        "skipped": 0,
        "errors": [],
        "started_at": datetime.utcnow().isoformat(),
    }

    try:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext in ("xlsx", "xls"):
            headers, rows = _parse_excel_bytes(file_bytes)
        elif ext in ("csv", "tsv", "txt"):
            headers, rows = _parse_csv_bytes(file_bytes)
        else:
            return {"imported": 0, "skipped": 0, "errors": [{"row": 0, "error": f"Unsupported file type: .{ext}"}], "batch_id": batch_id}

        mapping = _detect_mapping(headers)
        if not mapping:
            return {"imported": 0, "skipped": 0, "errors": [{"row": 0, "error": "Could not detect column mapping. Check column headers."}], "batch_id": batch_id}

        _batch_status[batch_id]["total"] = len(rows)

        imported = 0
        skipped = 0
        errors: list[dict[str, Any]] = []

        for row_idx, raw_row in enumerate(rows, start=2):  # row 2 = first data row
            try:
                # Map columns
                mapped: dict[str, Any] = {}
                for src_col, target_field in mapping.items():
                    if src_col in raw_row:
                        mapped[target_field] = raw_row[src_col]

                # Combine first/last name if separate
                if "claimant_first_name" in mapped and "claimant_last_name" in mapped:
                    first = mapped.pop("claimant_first_name", "").strip()
                    last = mapped.pop("claimant_last_name", "").strip()
                    mapped["claimant_name"] = f"{first} {last}".strip()

                wcb_case_number = (mapped.get("wcb_case_number") or "").strip()
                if not wcb_case_number:
                    errors.append({"row": row_idx, "error": "Missing WCB case number"})
                    skipped += 1
                    continue

                # Check for duplicate within org
                existing = await db.execute(
                    select(RFACase).where(
                        RFACase.org_id == org_id,
                        RFACase.wcb_case_number == wcb_case_number,
                    )
                )
                if existing.scalar_one_or_none():
                    skipped += 1
                    continue

                # Create case
                case = RFACase(
                    id=uuid.uuid4(),
                    org_id=org_id,
                    wcb_case_number=wcb_case_number,
                    claimant_name_encrypted=mapped.get("claimant_name", ""),
                    date_of_injury=_parse_date(mapped.get("date_of_injury")),
                    employer_name=mapped.get("employer_name", ""),
                    employer_fein=mapped.get("employer_fein"),
                    is_volunteer=_parse_bool(mapped.get("is_volunteer")),
                    claimant_rep_name=mapped.get("claimant_rep_name"),
                    claimant_rep_address=mapped.get("claimant_rep_address"),
                    carrier_name=mapped.get("carrier_name"),
                    carrier_code=mapped.get("carrier_code"),
                    district=mapped.get("district"),
                )
                db.add(case)
                await db.flush()

                # Create draft submission
                reason_codes = _parse_reason_codes(mapped.get("reason_codes"))
                submission = RFASubmission(
                    id=uuid.uuid4(),
                    org_id=org_id,
                    case_id=case.id,
                    created_by=uuid.UUID("00000000-0000-0000-0000-000000000001"),  # system import
                    status="draft",
                    reason_codes=reason_codes,
                    form_data={"imported_from": filename, "row": row_idx, "raw": raw_row},
                )
                db.add(submission)
                imported += 1

            except Exception as exc:
                errors.append({"row": row_idx, "error": str(exc)})

            _batch_status[batch_id]["processed"] = row_idx - 1

        await db.flush()

        # Audit log
        audit = RFAAuditLog(
            id=uuid.uuid4(),
            org_id=org_id,
            action="batch_import",
            resource_type="cases",
            description=f"Imported {imported} cases from {filename} ({skipped} skipped, {len(errors)} errors)",
        )
        db.add(audit)

        _batch_status[batch_id].update({
            "status": "completed",
            "imported": imported,
            "skipped": skipped,
            "errors": errors,
            "completed_at": datetime.utcnow().isoformat(),
        })

        return {"imported": imported, "skipped": skipped, "errors": errors, "batch_id": batch_id}

    except Exception as exc:
        _batch_status[batch_id].update({"status": "failed", "errors": [{"row": 0, "error": str(exc)}]})
        raise


async def batch_validate(
    submission_ids: list[uuid.UUID],
    db: AsyncSession,
) -> dict[str, Any]:
    """Run validation on multiple submissions.

    Returns: {valid: int, invalid: int, errors_by_id: dict}
    """
    valid = 0
    invalid = 0
    errors_by_id: dict[str, list[str]] = {}

    for sub_id in submission_ids:
        result = await db.execute(
            select(RFASubmission).where(RFASubmission.id == sub_id)
        )
        submission = result.scalar_one_or_none()
        if not submission:
            errors_by_id[str(sub_id)] = ["Submission not found"]
            invalid += 1
            continue

        field_errors: list[str] = []

        # Load related case
        case_result = await db.execute(
            select(RFACase).where(RFACase.id == submission.case_id)
        )
        case = case_result.scalar_one_or_none()

        if not case:
            field_errors.append("Associated case not found")
        else:
            if not case.wcb_case_number:
                field_errors.append("Missing WCB case number")
            if not case.claimant_name_encrypted:
                field_errors.append("Missing claimant name")
            if not case.date_of_injury:
                field_errors.append("Missing date of injury")
            if not case.employer_name:
                field_errors.append("Missing employer name")

        if not submission.reason_codes or len(submission.reason_codes) == 0:
            field_errors.append("No reason codes specified")

        if not submission.attestation_accepted:
            field_errors.append("Attestation not accepted (required for submission)")

        if field_errors:
            errors_by_id[str(sub_id)] = field_errors
            invalid += 1
        else:
            submission.status = "validated"
            valid += 1

    await db.flush()
    return {"valid": valid, "invalid": invalid, "errors_by_id": errors_by_id}


async def batch_build_xml(
    submission_ids: list[uuid.UUID],
    db: AsyncSession,
) -> dict[str, Any]:
    """Generate XML for multiple submissions.

    Returns: {generated: int, failed: int, results: dict}
    """
    generated = 0
    failed = 0
    results: dict[str, dict[str, Any]] = {}

    for sub_id in submission_ids:
        result = await db.execute(
            select(RFASubmission).where(RFASubmission.id == sub_id)
        )
        submission = result.scalar_one_or_none()
        if not submission:
            results[str(sub_id)] = {"status": "error", "error": "Submission not found"}
            failed += 1
            continue

        if submission.status not in ("draft", "validated"):
            results[str(sub_id)] = {"status": "skipped", "error": f"Cannot generate XML for status: {submission.status}"}
            failed += 1
            continue

        # Load case for XML generation
        case_result = await db.execute(
            select(RFACase).where(RFACase.id == submission.case_id)
        )
        case = case_result.scalar_one_or_none()
        if not case:
            results[str(sub_id)] = {"status": "error", "error": "Case not found"}
            failed += 1
            continue

        try:
            xml_payload = _build_rfa2_xml(case, submission)
            submission.xml_payload = xml_payload
            submission.status = "validated"
            results[str(sub_id)] = {"status": "success"}
            generated += 1
        except Exception as exc:
            results[str(sub_id)] = {"status": "error", "error": str(exc)}
            failed += 1

    await db.flush()
    return {"generated": generated, "failed": failed, "results": results}


def _build_rfa2_xml(case: RFACase, submission: RFASubmission) -> str:
    """Build AIRA XML payload for a single submission."""
    reason_codes = submission.reason_codes or []
    reason_xml = "\n".join(f"        <ReasonCode>{code}</ReasonCode>" for code in reason_codes)

    doi_str = case.date_of_injury.isoformat() if case.date_of_injury else ""
    cert_date = submission.certification_date.isoformat() if submission.certification_date else ""
    now_str = datetime.utcnow().isoformat()

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<RFA2Submission xmlns="urn:ny-wcb:rfa2">
    <Header>
        <SubmissionId>{submission.id}</SubmissionId>
        <CaseNumber>{case.wcb_case_number}</CaseNumber>
        <GeneratedAt>{now_str}</GeneratedAt>
    </Header>
    <CaseInfo>
        <WCBCaseNumber>{case.wcb_case_number}</WCBCaseNumber>
        <DateOfInjury>{doi_str}</DateOfInjury>
        <EmployerName>{case.employer_name or ''}</EmployerName>
        <EmployerFEIN>{case.employer_fein or ''}</EmployerFEIN>
        <IsVolunteer>{'true' if case.is_volunteer else 'false'}</IsVolunteer>
        <ClaimantRepName>{case.claimant_rep_name or ''}</ClaimantRepName>
        <CarrierName>{case.carrier_name or ''}</CarrierName>
        <CarrierCode>{case.carrier_code or ''}</CarrierCode>
        <District>{case.district or ''}</District>
    </CaseInfo>
    <ReasonCodes>
{reason_xml}
    </ReasonCodes>
    <Narrative>{submission.narrative or ''}</Narrative>
    <Certification>
        <CertificationDate>{cert_date}</CertificationDate>
        <AttestationAccepted>{'true' if submission.attestation_accepted else 'false'}</AttestationAccepted>
    </Certification>
</RFA2Submission>"""
    return xml


async def batch_submit(
    submission_ids: list[uuid.UUID],
    db: AsyncSession,
) -> dict[str, Any]:
    """Submit multiple submissions to WCB (mock).

    Returns: {submitted: int, failed: int, results: dict}
    """
    import random

    submitted = 0
    failed_count = 0
    results: dict[str, dict[str, Any]] = {}

    for sub_id in submission_ids:
        result = await db.execute(
            select(RFASubmission).where(RFASubmission.id == sub_id)
        )
        submission = result.scalar_one_or_none()
        if not submission:
            results[str(sub_id)] = {"status": "error", "error": "Submission not found"}
            failed_count += 1
            continue

        if submission.status not in ("validated", "draft"):
            results[str(sub_id)] = {"status": "skipped", "error": f"Cannot submit from status: {submission.status}"}
            failed_count += 1
            continue

        if not submission.xml_payload:
            results[str(sub_id)] = {"status": "error", "error": "No XML payload generated. Run batch_build_xml first."}
            failed_count += 1
            continue

        # Mock WCB submission
        mock_wcb_id = f"WCB-{uuid.uuid4().hex[:12].upper()}"
        mock_doc_id = f"DOC-{uuid.uuid4().hex[:8].upper()}"

        # Simulate 90% success rate
        if random.random() < 0.9:
            submission.status = "submitted"
            submission.wcb_submission_id = mock_wcb_id
            submission.wcb_document_id = mock_doc_id
            submission.wcb_status = "pending"
            submission.submitted_at = datetime.utcnow()
            results[str(sub_id)] = {
                "status": "submitted",
                "wcb_submission_id": mock_wcb_id,
                "wcb_document_id": mock_doc_id,
            }
            submitted += 1
        else:
            submission.wcb_status = "submission_error"
            submission.wcb_errors = [{"code": "SYS-500", "message": "Mock: WCB system temporarily unavailable"}]
            results[str(sub_id)] = {
                "status": "failed",
                "error": "WCB system temporarily unavailable",
            }
            failed_count += 1

    await db.flush()

    return {"submitted": submitted, "failed": failed_count, "results": results}


def get_batch_status(batch_id: str) -> dict[str, Any]:
    """Track progress of a batch operation."""
    status = _batch_status.get(batch_id)
    if not status:
        return {"error": "Batch not found", "batch_id": batch_id}
    return {"batch_id": batch_id, **status}
