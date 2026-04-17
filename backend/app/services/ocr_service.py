"""
Document OCR Service for RFA-2 Portal.

Provides intelligent text extraction using native PDF parsing or AWS Textract,
document classification via Claude AI, and structured data extraction from
Workers' Compensation documents.
"""

import io
import json
import logging
from typing import Any, Optional

import boto3
from botocore.config import Config as BotoConfig

from app.config import get_settings

logger = logging.getLogger(__name__)

# Supported document types for classification
DOCUMENT_TYPES = [
    "IME Report",
    "Board Decision",
    "Medical Record",
    "Operative Note",
    "Wage Records",
    "Surveillance",
    "C-4 Authorization",
    "C-7 Notice",
    "Section 32 Agreement",
    "Legal Brief",
    "Other",
]


# ---------------------------------------------------------------------------
# AWS / Bedrock client helpers
# ---------------------------------------------------------------------------

def _get_textract_client():
    """Create an AWS Textract client."""
    settings = get_settings()
    kwargs: dict[str, Any] = {
        "region_name": settings.aws_region,
        "config": BotoConfig(
            retries={"max_attempts": 3, "mode": "adaptive"},
            read_timeout=120,
        ),
    }
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    return boto3.client("textract", **kwargs)


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


def _invoke_claude(system: str, user_message: str) -> str:
    """Send a message to Claude via Bedrock and return the assistant text."""
    settings = get_settings()
    client = _get_bedrock_client()

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "temperature": 0.1,
        "system": system,
        "messages": [{"role": "user", "content": user_message}],
    })

    response = client.invoke_model(
        modelId=settings.bedrock_model_id,
        contentType="application/json",
        accept="application/json",
        body=body,
    )
    response_body = json.loads(response["body"].read())
    text = response_body["content"][0]["text"].strip()

    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    return text.strip()


# ---------------------------------------------------------------------------
# Native PDF text extraction
# ---------------------------------------------------------------------------

def _extract_text_native_pdf(file_bytes: bytes) -> tuple[Optional[str], int]:
    """
    Extract text from a PDF using PyMuPDF (fitz).
    Returns (text, page_count). Returns (None, page_count) if no text layer found.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning("PyMuPDF not installed; falling back to pdfplumber")
        return _extract_text_pdfplumber(file_bytes)

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        page_count = len(doc)
        text_parts = []
        for page in doc:
            text = page.get_text("text")
            if text and text.strip():
                text_parts.append(text.strip())
        doc.close()

        if text_parts:
            return "\n\n".join(text_parts), page_count
        return None, page_count
    except Exception as e:
        logger.warning("PyMuPDF extraction failed: %s", e)
        return None, 0


def _extract_text_pdfplumber(file_bytes: bytes) -> tuple[Optional[str], int]:
    """
    Fallback PDF text extraction using pdfplumber.
    Returns (text, page_count). Returns (None, page_count) if no text found.
    """
    try:
        import pdfplumber
    except ImportError:
        logger.warning("pdfplumber not installed; cannot extract native PDF text")
        return None, 0

    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            page_count = len(pdf.pages)
            text_parts = []
            for page in pdf.pages:
                text = page.extract_text()
                if text and text.strip():
                    text_parts.append(text.strip())
            if text_parts:
                return "\n\n".join(text_parts), page_count
            return None, page_count
    except Exception as e:
        logger.warning("pdfplumber extraction failed: %s", e)
        return None, 0


# ---------------------------------------------------------------------------
# AWS Textract OCR
# ---------------------------------------------------------------------------

def _extract_text_textract(file_bytes: bytes) -> tuple[str, float]:
    """
    Use AWS Textract to OCR a document.
    Returns (extracted_text, average_confidence).
    """
    client = _get_textract_client()

    try:
        response = client.detect_document_text(
            Document={"Bytes": file_bytes}
        )

        lines = []
        confidences = []
        for block in response.get("Blocks", []):
            if block["BlockType"] == "LINE":
                lines.append(block.get("Text", ""))
                confidences.append(block.get("Confidence", 0))

        text = "\n".join(lines)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return text, round(avg_confidence, 2)

    except Exception as e:
        logger.exception("Textract OCR failed")
        raise


def _extract_text_textract_multipage(file_bytes: bytes) -> tuple[str, float]:
    """
    Use Textract analyze_document for multi-page PDFs (via S3 or synchronous).
    For documents under 5MB, use synchronous detect_document_text per page.
    """
    # For larger documents, we split into pages and OCR each
    try:
        import fitz
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        all_text = []
        all_confidences = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            # Render page to image for Textract
            pix = page.get_pixmap(dpi=200)
            img_bytes = pix.tobytes("png")

            try:
                text, confidence = _extract_text_textract(img_bytes)
                all_text.append(f"--- Page {page_num + 1} ---\n{text}")
                all_confidences.append(confidence)
            except Exception as e:
                logger.warning("Textract failed for page %d: %s", page_num + 1, e)
                all_text.append(f"--- Page {page_num + 1} ---\n[OCR FAILED]")

        doc.close()
        combined_text = "\n\n".join(all_text)
        avg_conf = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
        return combined_text, round(avg_conf, 2)

    except ImportError:
        # If PyMuPDF not available, try single-shot Textract
        return _extract_text_textract(file_bytes)


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

async def extract_text_from_document(
    file_bytes: bytes,
    filename: str,
    mime_type: str,
) -> dict:
    """
    Intelligent text extraction from a document.

    Strategy:
    - PDF with text layer: extract directly using PyMuPDF/pdfplumber
    - Scanned PDF or image: use AWS Textract OCR
    - Returns method used, confidence, and metadata
    """
    is_pdf = mime_type == "application/pdf" or filename.lower().endswith(".pdf")
    is_image = mime_type.startswith("image/") or filename.lower().endswith(
        (".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp")
    )

    text = None
    method = "unknown"
    confidence = 0.0
    page_count = 1
    word_count = 0

    if is_pdf:
        # Try native extraction first
        native_text, page_count = _extract_text_native_pdf(file_bytes)
        if native_text and len(native_text.strip()) > 50:
            text = native_text
            method = "native"
            confidence = 99.0
        else:
            # Scanned PDF -- use Textract
            try:
                if page_count > 1:
                    text, confidence = _extract_text_textract_multipage(file_bytes)
                else:
                    text, confidence = _extract_text_textract(file_bytes)
                method = "ocr"
            except Exception as e:
                logger.error("Textract OCR failed for PDF %s: %s", filename, e)
                # Last resort: return whatever native extraction got
                text = native_text or ""
                method = "native_fallback"
                confidence = 10.0

    elif is_image:
        # Always use Textract for images
        try:
            text, confidence = _extract_text_textract(file_bytes)
            method = "ocr"
        except Exception as e:
            logger.error("Textract OCR failed for image %s: %s", filename, e)
            text = ""
            method = "ocr_failed"
            confidence = 0.0

    else:
        # Unsupported type -- try Textract anyway
        try:
            text, confidence = _extract_text_textract(file_bytes)
            method = "ocr"
        except Exception:
            text = ""
            method = "unsupported"
            confidence = 0.0

    word_count = len(text.split()) if text else 0

    return {
        "text": text or "",
        "method": method,
        "confidence": confidence,
        "page_count": page_count,
        "word_count": word_count,
        "filename": filename,
        "mime_type": mime_type,
    }


async def classify_document_type(text: str) -> dict:
    """
    Use Claude to auto-classify a Workers' Compensation document.

    Returns the document type, confidence, and key findings.
    """
    if not text or len(text.strip()) < 20:
        return {
            "doc_type": "Other",
            "confidence": "LOW",
            "key_findings": ["Insufficient text for classification."],
        }

    system_prompt = (
        "You are a document classifier for NYS Workers' Compensation documents. "
        "Classify the document into one of these types: "
        + ", ".join(DOCUMENT_TYPES)
        + ". Respond ONLY with valid JSON."
    )

    # Use first 5000 chars for classification
    excerpt = text[:5000]
    user_message = f"""Classify this Workers' Compensation document:

{excerpt}

Return JSON:
{{
  "doc_type": "One of: {', '.join(DOCUMENT_TYPES)}",
  "confidence": "HIGH|MEDIUM|LOW",
  "key_findings": ["List of 3-5 key findings from the document"]
}}"""

    try:
        response_text = _invoke_claude(system_prompt, user_message)
        result = json.loads(response_text)

        # Validate doc_type
        doc_type = result.get("doc_type", "Other")
        if doc_type not in DOCUMENT_TYPES:
            doc_type = "Other"

        return {
            "doc_type": doc_type,
            "confidence": result.get("confidence", "LOW"),
            "key_findings": result.get("key_findings", []),
        }
    except json.JSONDecodeError as e:
        logger.error("Failed to parse classification response: %s", e)
        return {
            "doc_type": "Other",
            "confidence": "LOW",
            "key_findings": ["Classification failed due to AI response error."],
            "error": str(e),
        }
    except Exception as e:
        logger.exception("Document classification failed")
        return {
            "doc_type": "Other",
            "confidence": "LOW",
            "key_findings": ["Classification service unavailable."],
            "error": str(e),
        }


async def extract_structured_data(text: str, doc_type: str) -> dict:
    """
    Extract structured fields from unstructured document text based on type.

    Extraction schemas vary by document type:
    - IME Report: physician, exam date, diagnoses, findings, MMI, disability
    - Board Decision: decision date, judge, district, order, next hearing
    - Wage Records: employer, wages, period, AWW
    """
    if not text or len(text.strip()) < 20:
        return {"doc_type": doc_type, "fields": {}, "error": "Insufficient text"}

    # Build type-specific extraction instructions
    field_instructions = _get_field_instructions(doc_type)

    system_prompt = (
        "You are a data extraction specialist for NYS Workers' Compensation documents. "
        "Extract structured fields from the document text. "
        "Use null for fields that cannot be determined. "
        "Respond ONLY with valid JSON."
    )

    excerpt = text[:15000]
    user_message = f"""Document Type: {doc_type}

DOCUMENT TEXT:
{excerpt}

Extract the following fields:
{field_instructions}

Return a JSON object with the extracted fields."""

    try:
        response_text = _invoke_claude(system_prompt, user_message)
        result = json.loads(response_text)
        return {
            "doc_type": doc_type,
            "fields": result,
        }
    except json.JSONDecodeError as e:
        logger.error("Failed to parse structured extraction response: %s", e)
        return {"doc_type": doc_type, "fields": {}, "error": str(e)}
    except Exception as e:
        logger.exception("Structured data extraction failed")
        return {"doc_type": doc_type, "fields": {}, "error": str(e)}


async def highlight_key_findings(text: str, reason_codes: list[str]) -> list:
    """
    Identify text spans relevant to the selected reason codes.
    Returns a list of spans with start/end positions and relevance info
    for UI highlighting.
    """
    if not text or not reason_codes:
        return []

    system_prompt = (
        "You are a Workers' Compensation document analyst. "
        "Identify text passages that are relevant to the given RFA-2 reason codes. "
        "Return exact quotes from the document that support or relate to each reason code. "
        "Respond ONLY with valid JSON."
    )

    excerpt = text[:10000]
    codes_str = ", ".join(reason_codes)
    user_message = f"""Reason Codes: {codes_str}

DOCUMENT TEXT:
{excerpt}

Find text passages relevant to each reason code. Return JSON:
{{
  "highlights": [
    {{
      "text": "Exact quoted text from the document",
      "reason_code": "The applicable reason code",
      "relevance": "HIGH|MEDIUM|LOW",
      "note": "Brief explanation of why this passage is relevant"
    }}
  ]
}}"""

    try:
        response_text = _invoke_claude(system_prompt, user_message)
        result = json.loads(response_text)
        highlights = result.get("highlights", [])

        # Enrich with position data
        enriched = []
        for h in highlights:
            quote = h.get("text", "")
            start = text.find(quote)
            enriched.append({
                "text": quote,
                "reason_code": h.get("reason_code", ""),
                "relevance": h.get("relevance", "MEDIUM"),
                "note": h.get("note", ""),
                "start": start if start >= 0 else None,
                "end": (start + len(quote)) if start >= 0 else None,
            })

        return enriched

    except json.JSONDecodeError as e:
        logger.error("Failed to parse highlights response: %s", e)
        return []
    except Exception as e:
        logger.exception("Key findings highlighting failed")
        return []


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_field_instructions(doc_type: str) -> str:
    """Return extraction field instructions based on document type."""
    instructions = {
        "IME Report": """{{
  "examining_physician": "Full name of the examining physician",
  "exam_date": "Date of the examination (MM/DD/YYYY)",
  "diagnoses": [
    {{"icd10": "ICD-10 code", "description": "Diagnosis description"}}
  ],
  "findings": "Summary of clinical findings",
  "recommendations": "Physician's recommendations",
  "mmi_opinion": "Has the claimant reached Maximum Medical Improvement? (yes/no/not addressed)",
  "mmi_date": "Date of MMI if stated (MM/DD/YYYY or null)",
  "disability_rating": "Disability rating or percentage if stated",
  "body_parts_examined": ["List of body parts examined"],
  "work_restrictions": "Any work restrictions noted",
  "causation_opinion": "Physician's opinion on whether injury is work-related"
}}""",
        "Board Decision": """{{
  "decision_date": "Date of the Board decision (MM/DD/YYYY)",
  "judge_name": "Name of the Workers' Compensation Law Judge",
  "district": "WCB district (e.g., Buffalo, Syracuse, Albany, NYC)",
  "case_number": "WCB case number",
  "order_text": "Summary of the Board's order",
  "findings_of_fact": "Key findings of fact",
  "next_hearing_date": "Date of next scheduled hearing if any (MM/DD/YYYY or null)",
  "parties": ["List of parties mentioned"],
  "disposition": "Final disposition (e.g., established, disallowed, continued)"
}}""",
        "Wage Records": """{{
  "employer_name": "Name of the employer",
  "employer_fein": "Federal EIN if present",
  "wages_reported": "Total wages reported",
  "wage_period": "Period covered (e.g., '01/01/2024 - 12/31/2024')",
  "average_weekly_wage": "AWW (Average Weekly Wage) if calculable",
  "hours_worked": "Total hours worked if stated",
  "pay_rate": "Hourly/salary rate if stated",
  "overtime_included": "Whether overtime is included (yes/no/unknown)"
}}""",
        "Medical Record": """{{
  "provider_name": "Name of the treating provider",
  "visit_date": "Date of visit (MM/DD/YYYY)",
  "diagnoses": [
    {{"icd10": "ICD-10 code", "description": "Diagnosis description"}}
  ],
  "treatment_provided": "Summary of treatment",
  "medications": ["List of medications prescribed"],
  "follow_up": "Follow-up instructions",
  "work_status": "Work status determination",
  "body_parts": ["Body parts addressed"]
}}""",
        "Operative Note": """{{
  "surgeon_name": "Name of the operating surgeon",
  "surgery_date": "Date of surgery (MM/DD/YYYY)",
  "procedure_names": ["List of procedures performed"],
  "cpt_codes": ["CPT codes if listed"],
  "preoperative_diagnosis": "Preoperative diagnosis",
  "postoperative_diagnosis": "Postoperative diagnosis",
  "findings": "Intraoperative findings",
  "complications": "Any complications noted",
  "estimated_recovery": "Estimated recovery time if stated"
}}""",
        "Surveillance": """{{
  "surveillance_dates": ["Dates of surveillance"],
  "investigator": "Name of the investigator or firm",
  "subject_activities": "Summary of activities observed",
  "inconsistencies_noted": "Any inconsistencies with claimed disability",
  "video_evidence": "Whether video evidence exists (yes/no)",
  "hours_observed": "Total hours of observation"
}}""",
    }

    return instructions.get(doc_type, """{{
  "document_date": "Date on the document (MM/DD/YYYY or null)",
  "author": "Author or issuer of the document",
  "subject": "Subject or re: line",
  "key_content": "Summary of the document's main content",
  "parties_mentioned": ["List of parties or entities mentioned"],
  "dates_referenced": ["Important dates referenced in the document"],
  "action_items": ["Any action items or requirements noted"]
}}""")
