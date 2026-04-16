"""
PHI De-identification Service for RFA-2 Workers' Compensation Portal.

Strips Protected Health Information from document text BEFORE it reaches Claude AI.
Preserves WC-relevant identifiers (case numbers, injury dates, diagnoses, etc.).
"""

import re
import uuid
from datetime import datetime


# ---------------------------------------------------------------------------
# Patterns that must be PRESERVED (matched first and masked from redaction)
# ---------------------------------------------------------------------------

# WCB Case Numbers  — G-1234567, WC1234567, etc.
_WCB_CASE_RE = re.compile(
    r"\b(?:G-\d{7}|WC\d{7,9}|WCB\s*(?:Case\s*)?#?\s*\d{5,9})\b",
    re.IGNORECASE,
)

# ICD-10 codes  — e.g. M54.5, S72.001A
_ICD10_RE = re.compile(
    r"\b[A-TV-Z]\d{2}(?:\.\d{1,4}[A-Z]?)?\b",
)

# CPT codes  — 5-digit numeric codes often preceded by "CPT"
_CPT_RE = re.compile(
    r"\b(?:CPT\s*)?(?:99\d{3}|9[0-8]\d{3}|[1-8]\d{4})\b",
)

# Date of Injury lines  — "DOI: 03/15/2022", "Date of Injury: …"
_DOI_LINE_RE = re.compile(
    r"(?:Date\s+of\s+Injury|DOI|Injury\s+Date)\s*[:\-]?\s*"
    r"\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Patterns that must be REDACTED
# ---------------------------------------------------------------------------

# SSN  — 123-45-6789 or 123456789
_SSN_RE = re.compile(
    r"\b\d{3}-\d{2}-\d{4}\b"
    r"|\b(?:SSN|Social\s+Security(?:\s+Number)?)\s*[:\-]?\s*\d{9}\b",
    re.IGNORECASE,
)

# Date of Birth lines  — "DOB: 01/15/1980", "Date of Birth: …", "Born: …"
_DOB_RE = re.compile(
    r"(?:Date\s+of\s+Birth|DOB|D\.O\.B\.|Born|Birth\s*Date)\s*[:\-]?\s*"
    r"\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}",
    re.IGNORECASE,
)

# Phone numbers  — (212) 555-1234, 212-555-1234, 212.555.1234, +1-212-555-1234
_PHONE_RE = re.compile(
    r"(?:\+1[\s\-]?)?"
    r"(?:\(\d{3}\)[\s\-]?|\d{3}[\s\-.])"
    r"\d{3}[\s\-.]\d{4}\b",
)

# Email addresses
_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
)

# Street addresses  — "123 Main St", "456 Broadway Apt 7B, New York, NY 10001"
_ADDRESS_RE = re.compile(
    r"\b\d{1,6}\s+(?:[A-Z][a-z]+\s+){1,4}"
    r"(?:St(?:reet)?|Ave(?:nue)?|Blvd|Boulevard|Dr(?:ive)?|Rd|Road|"
    r"Ln|Lane|Ct|Court|Pl(?:ace)?|Way|Pkwy|Parkway|Cir(?:cle)?|"
    r"Terr(?:ace)?|Hwy|Highway)"
    r"\.?"
    r"(?:\s*,?\s*(?:Apt|Suite|Ste|Unit|#)\s*\w+)?"
    r"(?:\s*,?\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)?"
    r"(?:\s*,?\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?)?",
)

# Named-entity patterns for patient / claimant names
_NAME_LABEL_RE = re.compile(
    r"(?:Patient|Claimant|Injured\s+Worker|Employee|Examinee|"
    r"Name\s+of\s+(?:Patient|Claimant|Injured\s+Worker))\s*"
    r"[:\-]?\s*"
    r"([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+(?:\s+(?:Jr|Sr|II|III|IV)\.?)?)",
    re.IGNORECASE,
)

# Honorific-prefixed names  — "Mr. John Smith", "Dr. Jane Doe"
_HONORIFIC_NAME_RE = re.compile(
    r"\b(?:Mr|Mrs|Ms|Miss|Dr|Prof)\.\s+"
    r"([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+(?:\s+(?:Jr|Sr|II|III|IV)\.?)?)",
)

# "Re:" or "Regarding:" lines often carry claimant names
_RE_LINE_RE = re.compile(
    r"(?:^|\n)\s*(?:Re|Regarding|In\s+[Rr]e)\s*[:\-]\s*"
    r"([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)",
)

# "Dear <Name>" lines
_DEAR_RE = re.compile(
    r"\bDear\s+(?:Mr|Mrs|Ms|Miss|Dr|Prof)\.\s+"
    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
)


def _placeholder(category: str) -> str:
    """Return a consistent redaction placeholder."""
    return f"[REDACTED-{category}]"


def deidentify(text: str) -> tuple[str, dict]:
    """
    De-identify PHI from Workers' Compensation document text.

    Returns:
        tuple of (cleaned_text, redaction_log)
        redaction_log keys:
            - redactions: list of {category, original_length, position, placeholder}
            - stats: counts per category
            - preserved: list of preserved WC identifiers found
            - timestamp: ISO timestamp of processing
            - redaction_id: unique ID for this run
    """
    if not text or not text.strip():
        return text, {
            "redactions": [],
            "stats": {},
            "preserved": [],
            "timestamp": datetime.utcnow().isoformat(),
            "redaction_id": str(uuid.uuid4()),
        }

    redaction_id = str(uuid.uuid4())
    redactions: list[dict] = []
    preserved: list[dict] = []

    # ---------------------------------------------------------------
    # Step 1: Identify positions to PRESERVE so we don't redact them.
    # ---------------------------------------------------------------
    preserve_spans: list[tuple[int, int]] = []

    for pat, label in [
        (_WCB_CASE_RE, "WCB_CASE"),
        (_ICD10_RE, "ICD10"),
        (_CPT_RE, "CPT"),
        (_DOI_LINE_RE, "DATE_OF_INJURY"),
    ]:
        for m in pat.finditer(text):
            preserve_spans.append((m.start(), m.end()))
            preserved.append({
                "category": label,
                "value": m.group(),
                "position": m.start(),
            })

    def _in_preserved(start: int, end: int) -> bool:
        """Check if a span overlaps with any preserved span."""
        for ps, pe in preserve_spans:
            if start < pe and end > ps:
                return True
        return False

    # ---------------------------------------------------------------
    # Step 2: Redact PHI patterns (ordered from most specific to broadest)
    # ---------------------------------------------------------------
    result = text
    offset = 0  # track cumulative shift from replacements

    # Collect all redaction matches first, then apply in order of position
    matches: list[tuple[int, int, str, str]] = []  # (start, end, category, matched_text)

    # SSN
    for m in _SSN_RE.finditer(text):
        if not _in_preserved(m.start(), m.end()):
            matches.append((m.start(), m.end(), "SSN", m.group()))

    # DOB
    for m in _DOB_RE.finditer(text):
        if not _in_preserved(m.start(), m.end()):
            matches.append((m.start(), m.end(), "DOB", m.group()))

    # Email
    for m in _EMAIL_RE.finditer(text):
        if not _in_preserved(m.start(), m.end()):
            matches.append((m.start(), m.end(), "EMAIL", m.group()))

    # Phone
    for m in _PHONE_RE.finditer(text):
        if not _in_preserved(m.start(), m.end()):
            matches.append((m.start(), m.end(), "PHONE", m.group()))

    # Address
    for m in _ADDRESS_RE.finditer(text):
        if not _in_preserved(m.start(), m.end()):
            matches.append((m.start(), m.end(), "ADDRESS", m.group()))

    # Named patient/claimant  — redact only the name portion (group 1)
    for pat in [_NAME_LABEL_RE, _RE_LINE_RE, _DEAR_RE]:
        for m in pat.finditer(text):
            if m.lastindex and m.lastindex >= 1:
                name_start = m.start(1)
                name_end = m.end(1)
                if not _in_preserved(name_start, name_end):
                    matches.append((name_start, name_end, "NAME", m.group(1)))

    # Honorific names  — redact the whole "Mr. John Smith"
    for m in _HONORIFIC_NAME_RE.finditer(text):
        if not _in_preserved(m.start(), m.end()):
            matches.append((m.start(), m.end(), "NAME", m.group()))

    # Sort by position (earliest first) and de-duplicate overlapping spans
    matches.sort(key=lambda x: x[0])
    deduped: list[tuple[int, int, str, str]] = []
    last_end = -1
    for start, end, cat, matched in matches:
        if start >= last_end:
            deduped.append((start, end, cat, matched))
            last_end = end

    # Apply replacements from end to start to preserve positions
    result_chars = list(text)
    for start, end, cat, matched in reversed(deduped):
        placeholder = _placeholder(cat)
        result_chars[start:end] = list(placeholder)
        redactions.append({
            "category": cat,
            "original_length": len(matched),
            "position": start,
            "placeholder": placeholder,
        })

    cleaned_text = "".join(result_chars)

    # Reverse redactions list so it's in document order
    redactions.reverse()

    # Build stats
    stats: dict[str, int] = {}
    for r in redactions:
        stats[r["category"]] = stats.get(r["category"], 0) + 1

    redaction_log = {
        "redactions": redactions,
        "stats": stats,
        "preserved": preserved,
        "timestamp": datetime.utcnow().isoformat(),
        "redaction_id": redaction_id,
    }

    return cleaned_text, redaction_log
