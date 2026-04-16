"""
Claude AI Extraction Service for RFA-2 Workers' Compensation Portal.

Uses AWS Bedrock Claude to extract structured RFA-2 form fields from
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
# Full RFA-2 Reason Codes reference
# ---------------------------------------------------------------------------

REASON_CODES: dict[str, dict[str, Any]] = {
    "CPD": {
        "description": "Controvert - Payor Denies Claim",
        "sub_reasons": {
            "CPD-1": "No causal relationship between injury and employment",
            "CPD-2": "Pre-existing condition, not aggravated by employment",
            "CPD-3": "Claimant was not an employee at time of injury",
            "CPD-4": "Injury did not arise out of and in the course of employment",
            "CPD-5": "No notice of injury given within 30 days",
            "CPD-6": "Claim not filed within 2 years of accident",
            "CPD-7": "Claimant was intoxicated or under influence of controlled substance",
            "CPD-8": "Injury was willfully self-inflicted",
            "CPD-9": "Other grounds for denial (specify in narrative)",
        },
        "required_documents": ["C-7_NOTICE", "IME_REPORT"],
    },
    "CPR": {
        "description": "Controvert - Payor Requests Further Action",
        "sub_reasons": {
            "CPR-1": "Request for Independent Medical Examination (IME)",
            "CPR-2": "Request for additional medical documentation",
            "CPR-3": "Request for deposition of claimant",
            "CPR-4": "Request for surveillance authorization",
        },
        "required_documents": ["C-7_NOTICE"],
    },
    "CPI": {
        "description": "Controvert - Payor Issues Interim Payments",
        "sub_reasons": {
            "CPI-1": "Liability controverted but payments made without prejudice",
            "CPI-2": "Partial controversion - specific body parts disputed",
        },
        "required_documents": ["C-7_NOTICE", "PAYMENT_RECORDS"],
    },
    "CPS": {
        "description": "Controvert - Prior Section 32 Settlement",
        "sub_reasons": {
            "CPS-1": "Full Section 32 settlement previously approved",
            "CPS-2": "Partial Section 32 settlement covers claimed body parts",
        },
        "required_documents": ["SECTION_32_AGREEMENT"],
    },
    "MCI": {
        "description": "Maximum Certification of Improvement",
        "sub_reasons": {
            "MCI-SL": "Schedule Loss of Use determination",
            "MCI-NS": "Non-schedule permanent disability classification",
            "MCI-PTD": "Permanent total disability",
            "MCI-PPD": "Permanent partial disability",
            "MCI-TT": "Temporary total disability continuing",
            "MCI-TP": "Temporary partial disability continuing",
        },
        "required_documents": ["IME_REPORT", "MMI_CERTIFICATION"],
    },
    "MOW": {
        "description": "Modification of Award - Change in Degree of Disability",
        "sub_reasons": {
            "MOW-1": "Disability degree has decreased based on medical evidence",
            "MOW-2": "Disability degree has increased based on medical evidence",
            "MOW-3": "Disability classification has changed",
        },
        "required_documents": ["IME_REPORT", "C-4_AUTH"],
    },
    "MIA": {
        "description": "Modification of Award - Inactive Case",
        "sub_reasons": {
            "MIA-1": "Claimant has not treated in over 12 months",
            "MIA-2": "Claimant failed to appear for scheduled IME",
            "MIA-3": "Claimant is not complying with prescribed treatment",
        },
        "required_documents": ["MEDICAL_RECORDS"],
    },
    "OER": {
        "description": "Other - Employer Request for Hearing",
        "sub_reasons": {
            "OER-1": "Employer disputes lost time claimed",
            "OER-2": "Employer has light duty work available",
            "OER-3": "Employer disputes medical treatment necessity",
        },
        "required_documents": ["EMPLOYER_STATEMENT"],
    },
    "OIL": {
        "description": "Other - Insurance Carrier Requests Limitation",
        "sub_reasons": {
            "OIL-1": "Request to limit duration of benefits",
            "OIL-2": "Request to limit scope of covered treatment",
        },
        "required_documents": ["IME_REPORT", "MEDICAL_RECORDS"],
    },
    "ORD": {
        "description": "Other - Request for Direction from Board",
        "sub_reasons": {
            "ORD-1": "Dispute between treating physician and IME physician",
            "ORD-2": "Request for Board-directed IME",
            "ORD-3": "Request for resolution of procedural dispute",
        },
        "required_documents": ["MEDICAL_RECORDS"],
    },
    "OID": {
        "description": "Other - Insurance Carrier Dispute",
        "sub_reasons": {
            "OID-1": "Dispute regarding apportionment of liability",
            "OID-2": "Dispute regarding coverage or policy applicability",
        },
        "required_documents": ["POLICY_DOCUMENTS"],
    },
    "OCD": {
        "description": "Other - Claimant Dispute",
        "sub_reasons": {
            "OCD-1": "Claimant disputes disability classification",
            "OCD-2": "Claimant disputes degree of disability",
            "OCD-3": "Claimant disputes apportionment",
        },
        "required_documents": ["MEDICAL_RECORDS", "C-4_AUTH"],
    },
    "OUI": {
        "description": "Other - Uninsured Employer",
        "sub_reasons": {
            "OUI-1": "Employer failed to secure workers' compensation coverage",
        },
        "required_documents": ["EMPLOYER_RECORDS", "UEF_REFERRAL"],
    },
    "OIW": {
        "description": "Other - Injured Worker Request",
        "sub_reasons": {
            "OIW-1": "Injured worker requests hearing",
            "OIW-2": "Injured worker requests change of physician",
            "OIW-3": "Injured worker disputes employer offer of light duty",
        },
        "required_documents": ["CLAIMANT_STATEMENT"],
    },
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


_SYSTEM_PROMPT = """You are a Workers' Compensation document analyst for New York State RFA-2 filings.

You are analyzing a DE-IDENTIFIED document — patient names have been replaced with [REDACTED-NAME].
Do NOT attempt to reconstruct redacted information.

Your task is to extract structured data needed for an RFA-2 (Request for Further Action) submission
to the NYS Workers' Compensation Board.

REASON CODES (select all that apply):
- CPD: Controvert - Payor Denies Claim (9 sub-reasons: denial grounds)
- CPR: Controvert - Payor Requests Further Action
- CPI: Controvert - Payor Issues Interim Payments
- CPS: Controvert - Prior Section 32 Settlement
- MCI: Maximum Certification of Improvement (disability classification)
- MOW: Modification of Award - Change in Degree
- MIA: Modification of Award - Inactive Case
- OER: Other - Employer Request for Hearing
- OIL: Other - Insurance Carrier Requests Limitation
- ORD: Other - Request for Direction from Board
- OID: Other - Insurance Carrier Dispute
- OCD: Other - Claimant Dispute
- OUI: Other - Uninsured Employer
- OIW: Other - Injured Worker Request

For MCI cases, extract:
- MMI (Maximum Medical Improvement) date
- Disability classification: schedule_loss, non_schedule, permanent_total,
  permanent_partial, temporary_total, temporary_partial
- Degree of disability (percentage or weeks of schedule loss)

RESPOND ONLY WITH VALID JSON — no markdown fences, no commentary.
"""

_USER_PROMPT_TEMPLATE = """Analyze this {doc_type} document and extract RFA-2 filing fields.

DOCUMENT TEXT:
---
{text}
---

Return a JSON object with these exact keys:
{{
  "reason_codes": [
    {{
      "code": "MCI",
      "sub_reason": "MCI-SL",
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
  "recommended_narrative": "Concise narrative for RFA-2 submission (max 500 chars)",
  "confidence": "HIGH|MEDIUM|LOW",
  "confidence_notes": "Explanation of confidence level",
  "missing_documents": ["list of document types still needed for complete filing"]
}}
"""


async def extract_rfa2_fields(clean_text: str, doc_type: str) -> dict:
    """
    Extract RFA-2 form fields from de-identified document text using Claude via Bedrock.

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
            for doc in REASON_CODES[code].get("required_documents", []):
                all_required.add(doc)

    existing_missing = set(extracted["missing_documents"])
    for doc in all_required:
        if doc not in existing_missing:
            extracted["missing_documents"].append(doc)

    return extracted
