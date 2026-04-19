"""
Claude AI Extraction Service for AIRA Workers' Compensation Portal.

Uses AWS Bedrock Claude to extract structured AIRA form fields from
de-identified Workers' Compensation documents.
"""

import json
import logging
from typing import Any

import boto3
from botocore.config import Config as BotoConfig

from app.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Full AIRA Reason Codes reference (all 20 WCB reason codes)
# ---------------------------------------------------------------------------

REASON_CODES: dict[str, dict[str, Any]] = {
    # Compensation
    "CNW": {"name": "Claimant Not Working", "category": "C", "description": "Claimant is not working and not receiving payments", "required_docs": ["Medical Documentation"]},
    "CVW": {"name": "Volunteer Firefighter/Ambulance Worker", "category": "C", "description": "Volunteer firefighter/ambulance worker compensation", "required_docs": ["Medical Documentation"]},
    "CNP": {"name": "Claimant Not Paid Properly", "category": "C", "description": "Claimant has not been paid properly", "required_docs": ["Medical Documentation"]},
    "CAN": {"name": "Conciliation Request", "category": "C", "description": "Claimant, Attorney, or Licensed Rep requests conciliation", "required_docs": []},
    "CAW": {"name": "Payment Adjustment (AWW)", "category": "C", "description": "Payments need to be adjusted based on Average Weekly Wage", "required_docs": ["Medical Documentation", "Wage/Payroll Documentation"]},
    "CCE": {"name": "Concurrent Employment", "category": "C", "description": "Claimant has concurrent employment", "required_docs": ["Medical Documentation", "Wage/Payroll Documentation"]},
    "CRE": {"name": "Reduced Earnings", "category": "C", "description": "Claimant is entitled to reduced earnings benefits", "required_docs": ["Medical Documentation", "Wage/Payroll Documentation"]},
    "CRI": {"name": "Convicted/Released", "category": "C", "description": "Claimant was convicted and has been released from custody", "required_docs": ["Medical Documentation", "Release from Custody Documentation"]},
    # Medical
    "MBC": {"name": "Body Parts/Conditions", "category": "M", "description": "Claimant has raised body part(s)/condition(s)", "required_docs": ["Medical Documentation"]},
    "MPI": {"name": "PAR Denied (Insurer)", "category": "M", "description": "Prior Authorization Request was denied by insurer", "required_docs": []},
    "MPM": {"name": "PAR Denied (Medical Director)", "category": "M", "description": "Prior Authorization Request was denied by medical director", "required_docs": []},
    "MCI": {"name": "Maximum Medical Improvement", "category": "M", "description": "Claimant is at maximum medical improvement", "required_docs": ["Medical Documentation", "C-4.3 Doctor's Report of MMI"]},
    "MTR": {"name": "Medical & Transportation", "category": "M", "description": "Medical and transportation reimbursement request", "required_docs": ["Medical Documentation"]},
    "MCC": {"name": "Change in Condition", "category": "M", "description": "Claimant is classified and has a change in condition", "required_docs": ["Medical Documentation"]},
    "MAN": {"name": "Insurer PAR Response", "category": "M", "description": "The insurer has denied, granted in part, or not responded to PAR", "required_docs": ["Medical Documentation"]},
    # Other
    "OCC": {"name": "Controverted Claim", "category": "O", "description": "Claim is controverted and claimant did not file", "required_docs": ["Legal Documentation"]},
    "OCD": {"name": "Discontinued/Settled Lawsuit", "category": "O", "description": "Claimant has discontinued or settled a lawsuit", "required_docs": ["Legal Documentation"]},
    "ORP": {"name": "Report Preclusion", "category": "O", "description": "Request preclusion of medical report(s)", "required_docs": ["Medical Documentation"]},
    "OEI": {"name": "Update Employer/Insurer/TPA", "category": "O", "description": "Request to update employer, insurer, or TPA information", "required_docs": []},
    "OUI": {"name": "Death Case Issues", "category": "O", "description": "New or unresolved issues related to a death case", "required_docs": ["Legal Documentation"]},
}


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


_SYSTEM_PROMPT = """You are a Workers' Compensation document analyst for New York State AIRA filings.

You are analyzing a DE-IDENTIFIED document — patient names have been replaced with [REDACTED-NAME].
Do NOT attempt to reconstruct redacted information.

Your task is to extract structured data needed for an AIRA (Request for Further Action) submission
to the NYS Workers' Compensation Board.

REASON CODES (select all that apply):

Compensation:
- CNW: Claimant Not Working — Claimant is not working and not receiving payments
- CVW: Volunteer Firefighter/Ambulance Worker — Volunteer firefighter/ambulance worker compensation
- CNP: Claimant Not Paid Properly — Claimant has not been paid properly
- CAN: Conciliation Request — Claimant, Attorney, or Licensed Rep requests conciliation
- CAW: Payment Adjustment (AWW) — Payments need to be adjusted based on Average Weekly Wage
- CCE: Concurrent Employment — Claimant has concurrent employment
- CRE: Reduced Earnings — Claimant is entitled to reduced earnings benefits
- CRI: Convicted/Released — Claimant was convicted and has been released from custody

Medical:
- MBC: Body Parts/Conditions — Claimant has raised body part(s)/condition(s)
- MPI: PAR Denied (Insurer) — Prior Authorization Request was denied by insurer
- MPM: PAR Denied (Medical Director) — Prior Authorization Request was denied by medical director
- MCI: Maximum Medical Improvement — Claimant is at maximum medical improvement
- MTR: Medical & Transportation — Medical and transportation reimbursement request
- MCC: Change in Condition — Claimant is classified and has a change in condition
- MAN: Insurer PAR Response — The insurer has denied, granted in part, or not responded to PAR

Other:
- OCC: Controverted Claim — Claim is controverted and claimant did not file
- OCD: Discontinued/Settled Lawsuit — Claimant has discontinued or settled a lawsuit
- ORP: Report Preclusion — Request preclusion of medical report(s)
- OEI: Update Employer/Insurer/TPA — Request to update employer, insurer, or TPA information
- OUI: Death Case Issues — New or unresolved issues related to a death case

For MCI cases, extract:
- MMI (Maximum Medical Improvement) date
- Disability classification: schedule_loss, non_schedule, permanent_total,
  permanent_partial, temporary_total, temporary_partial
- Degree of disability (percentage or weeks of schedule loss)

RESPOND ONLY WITH VALID JSON — no markdown fences, no commentary.
"""

_USER_PROMPT_TEMPLATE = """Analyze this {doc_type} document and extract AIRA filing fields.

DOCUMENT TEXT:
---
{text}
---

Return a JSON object with these exact keys:
{{
  "reason_codes": [
    {{
      "code": "MCI",
      "sub_reason": null,
      "justification": "Brief explanation of why this code applies"
    }}
  ],
  "claimant_name": "[REDACTED-NAME] or extracted if visible",
  "date_of_injury": "MM/DD/YYYY or null",
  "body_parts": ["list of affected body parts"],
  "diagnoses": [
    {{
      "icd10": "M54.5",
      "description": "Low back pain"
    }}
  ],
  "ime_findings": "Summary of IME findings or null if not an IME report",
  "mmi_date": "MM/DD/YYYY or null",
  "disability_classification": "schedule_loss|non_schedule|permanent_total|permanent_partial|temporary_total|temporary_partial|null",
  "degree_of_disability": "percentage or weeks or null",
  "recommended_narrative": "Concise narrative for AIRA submission (max 500 chars)",
  "confidence": "HIGH|MEDIUM|LOW",
  "confidence_notes": "Explanation of confidence level",
  "missing_documents": ["list of document types still needed for complete filing"]
}}
"""


async def extract_rfa2_fields(clean_text: str, doc_type: str) -> dict:
    """
    Extract AIRA form fields from de-identified document text using Claude via Bedrock.

    Args:
        clean_text: PHI-scrubbed document text.
        doc_type: Type of document being analyzed (e.g. "IME_REPORT",
                  "C-4_AUTH", "MEDICAL_RECORDS", "EMPLOYER_STATEMENT",
                  "LEGAL_BRIEF", "UNKNOWN").

    Returns:
        Structured dict of extracted fields plus metadata.
    """
    settings = get_settings()
    client = _get_bedrock_client()

    user_prompt = _USER_PROMPT_TEMPLATE.format(
        doc_type=doc_type,
        text=clean_text[:30_000],  # Bedrock input guard
    )

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "temperature": 0.1,
        "system": _SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": user_prompt},
        ],
    })

    try:
        response = client.invoke_model(
            modelId=settings.bedrock_model_id,
            contentType="application/json",
            accept="application/json",
            body=body,
        )
        response_body = json.loads(response["body"].read())
        assistant_text = response_body["content"][0]["text"]

        # Strip markdown fences if Claude wraps the response
        cleaned = assistant_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        extracted = json.loads(cleaned)

    except json.JSONDecodeError as e:
        logger.error("Failed to parse Claude response as JSON: %s", e)
        extracted = _empty_extraction(
            error=f"JSON parse error: {e}",
            raw_response=assistant_text if "assistant_text" in dir() else None,
        )
    except client.exceptions.ThrottlingException:
        logger.warning("Bedrock throttled — retrying not implemented in this call")
        extracted = _empty_extraction(error="Bedrock rate limit exceeded")
    except Exception as e:
        logger.exception("Bedrock extraction failed")
        extracted = _empty_extraction(error=str(e))

    # Validate and enrich
    extracted = _normalize(extracted)
    return extracted


def _empty_extraction(error: str | None = None, raw_response: str | None = None) -> dict:
    """Return a blank extraction dict when Claude fails."""
    result = {
        "reason_codes": [],
        "claimant_name": None,
        "date_of_injury": None,
        "body_parts": [],
        "diagnoses": [],
        "ime_findings": None,
        "mmi_date": None,
        "disability_classification": None,
        "degree_of_disability": None,
        "recommended_narrative": None,
        "confidence": "LOW",
        "confidence_notes": error or "Extraction failed",
        "missing_documents": [],
    }
    if error:
        result["_error"] = error
    if raw_response:
        result["_raw_response"] = raw_response[:2000]
    return result


def _normalize(extracted: dict) -> dict:
    """
    Normalize and validate the extracted fields.
    Ensures all expected keys exist and values are in expected formats.
    """
    # Ensure all keys present
    defaults = _empty_extraction()
    for key in defaults:
        if key not in extracted:
            extracted[key] = defaults[key]

    # Validate reason codes against known set
    valid_codes = set(REASON_CODES.keys())
    validated_reasons = []
    for rc in extracted.get("reason_codes", []):
        if isinstance(rc, dict) and rc.get("code") in valid_codes:
            validated_reasons.append(rc)
        elif isinstance(rc, str) and rc in valid_codes:
            validated_reasons.append({"code": rc, "sub_reason": None, "justification": None})
    extracted["reason_codes"] = validated_reasons

    # Truncate narrative to 500 chars
    narrative = extracted.get("recommended_narrative")
    if narrative and len(narrative) > 500:
        extracted["recommended_narrative"] = narrative[:497] + "..."

    # Normalize confidence
    confidence = str(extracted.get("confidence", "LOW")).upper()
    if confidence not in ("HIGH", "MEDIUM", "LOW"):
        confidence = "LOW"
    extracted["confidence"] = confidence

    # Ensure body_parts and diagnoses are lists
    if not isinstance(extracted.get("body_parts"), list):
        extracted["body_parts"] = []
    if not isinstance(extracted.get("diagnoses"), list):
        extracted["diagnoses"] = []
    if not isinstance(extracted.get("missing_documents"), list):
        extracted["missing_documents"] = []

    # Auto-populate missing_documents based on reason codes
    all_required: set[str] = set()
    for rc in extracted["reason_codes"]:
        code = rc.get("code", "")
        if code in REASON_CODES:
            for doc in REASON_CODES[code].get("required_docs", []):
                all_required.add(doc)

    existing_missing = set(extracted["missing_documents"])
    for doc in all_required:
        if doc not in existing_missing:
            extracted["missing_documents"].append(doc)

    return extracted
