"""
WCB XML Generation Service for AIRA Workers' Compensation Portal.

Generates XML matching the WCB eFormsRfa2 schema and validates
submissions against WCB business rules.
"""

import xml.etree.ElementTree as ET
from datetime import date, datetime
from typing import Any
from xml.dom import minidom


# ---------------------------------------------------------------------------
# Required documents per reason code
# ---------------------------------------------------------------------------

REQUIRED_DOCUMENTS: dict[str, list[str]] = {
    "CPD": ["C-7_NOTICE", "IME_REPORT"],
    "CPR": ["C-7_NOTICE"],
    "CPI": ["C-7_NOTICE", "PAYMENT_RECORDS"],
    "CPS": ["SECTION_32_AGREEMENT"],
    "MCI": ["IME_REPORT", "MMI_CERTIFICATION"],
    "MOW": ["IME_REPORT", "C-4_AUTH"],
    "MIA": ["MEDICAL_RECORDS"],
    "OER": ["EMPLOYER_STATEMENT"],
    "OIL": ["IME_REPORT", "MEDICAL_RECORDS"],
    "ORD": ["MEDICAL_RECORDS"],
    "OID": ["POLICY_DOCUMENTS"],
    "OCD": ["MEDICAL_RECORDS", "C-4_AUTH"],
    "OUI": ["EMPLOYER_RECORDS", "UEF_REFERRAL"],
    "OIW": ["CLAIMANT_STATEMENT"],
}

_NAMESPACE = "http://www.wcb.ny.gov/eforms/rfa2"


def build_rfa2_xml(submission_data: dict) -> str:
    """
    Generate XML matching the WCB eFormsRfa2 schema.

    Args:
        submission_data: dict with keys:
            - wcb_case_number (str)
            - carrier_code (str)
            - carrier_name (str)
            - submitted_by (str)
            - submission_date (str, YYYY-MM-DD) — defaults to today
            - claimant_name (str)
            - date_of_injury (str, MM/DD/YYYY)
            - employer_name (str)
            - employer_fein (str)
            - district (str)
            - is_volunteer (bool)
            - representative_name (str, optional)
            - representative_address (str, optional)
            - reason_codes (list of dicts with code, sub_reason, certification_date, details)
            - narrative (str, max 500)
            - attestation_accepted (bool)
            - supporting_documents (list of dicts with type, file_name, wcb_doc_id)

    Returns:
        Pretty-printed XML string.
    """
    root = ET.Element("RFA2Submission")
    root.set("xmlns", _NAMESPACE)

    # --- Header ---
    header = ET.SubElement(root, "Header")
    _add_text(header, "WCBCaseNumber", submission_data.get("wcb_case_number", ""))
    _add_text(header, "CarrierCode", submission_data.get("carrier_code", ""))
    _add_text(header, "CarrierName", submission_data.get("carrier_name", ""))
    _add_text(header, "SubmittedBy", submission_data.get("submitted_by", ""))
    _add_text(
        header,
        "SubmissionDate",
        submission_data.get("submission_date", date.today().isoformat()),
    )

    # --- Claimant ---
    claimant = ET.SubElement(root, "Claimant")
    _add_text(claimant, "Name", submission_data.get("claimant_name", ""))
    _add_text(claimant, "DateOfInjury", submission_data.get("date_of_injury", ""))
    _add_text(claimant, "EmployerName", submission_data.get("employer_name", ""))
    _add_text(claimant, "EmployerFEIN", submission_data.get("employer_fein", ""))
    _add_text(claimant, "District", submission_data.get("district", ""))
    _add_text(
        claimant,
        "IsVolunteer",
        "true" if submission_data.get("is_volunteer") else "false",
    )

    # --- Claimant Representative (optional) ---
    rep_name = submission_data.get("representative_name")
    rep_address = submission_data.get("representative_address")
    if rep_name or rep_address:
        rep_el = ET.SubElement(root, "ClaimantRepresentative")
        _add_text(rep_el, "Name", rep_name or "")
        _add_text(rep_el, "Address", rep_address or "")

    # --- Reason Codes ---
    reason_codes_el = ET.SubElement(root, "ReasonCodes")
    for rc in submission_data.get("reason_codes", []):
        rc_el = ET.SubElement(reason_codes_el, "ReasonCode")
        rc_el.set("code", rc.get("code", ""))

        _add_text(rc_el, "SubReason", rc.get("sub_reason", ""))
        _add_text(rc_el, "CertificationDate", rc.get("certification_date", ""))

        details = rc.get("details")
        if details and isinstance(details, dict):
            details_el = ET.SubElement(rc_el, "Details")
            for key, value in details.items():
                _add_text(details_el, key, str(value) if value is not None else "")
        elif details and isinstance(details, str):
            _add_text(rc_el, "Details", details)

    # --- Narrative ---
    narrative = submission_data.get("narrative", "")
    _add_text(root, "Narrative", narrative[:500] if narrative else "")

    # --- Attestation ---
    attestation_el = ET.SubElement(root, "Attestation")
    attestation_el.set(
        "accepted",
        "true" if submission_data.get("attestation_accepted") else "false",
    )

    # --- Supporting Documents ---
    docs = submission_data.get("supporting_documents", [])
    if docs:
        docs_el = ET.SubElement(root, "SupportingDocuments")
        for doc in docs:
            doc_el = ET.SubElement(docs_el, "Document")
            doc_el.set("type", doc.get("type", ""))
            doc_el.set("fileName", doc.get("file_name", ""))
            if doc.get("wcb_doc_id"):
                doc_el.set("wcbDocId", doc["wcb_doc_id"])

    # Pretty-print
    rough = ET.tostring(root, encoding="unicode", xml_declaration=False)
    parsed = minidom.parseString(rough)
    pretty = parsed.toprettyxml(indent="  ", encoding=None)

    # minidom adds its own xml declaration; replace to ensure utf-8
    lines = pretty.split("\n")
    if lines and lines[0].startswith("<?xml"):
        lines[0] = '<?xml version="1.0" encoding="utf-8"?>'
    else:
        lines.insert(0, '<?xml version="1.0" encoding="utf-8"?>')

    return "\n".join(line for line in lines if line.strip())


def _add_text(parent: ET.Element, tag: str, text: str) -> ET.Element:
    """Add a child element with text content."""
    el = ET.SubElement(parent, tag)
    el.text = text
    return el


# ---------------------------------------------------------------------------
# Submission Validation
# ---------------------------------------------------------------------------

def validate_submission(data: dict) -> list[dict]:
    """
    Validate an AIRA submission against WCB business rules.

    Args:
        data: The same submission_data dict used by build_rfa2_xml.

    Returns:
        List of validation findings, each a dict with:
            - rule (str): rule identifier
            - severity (str): "error" or "warning"
            - message (str): human-readable description
    """
    findings: list[dict] = []

    # ----- Rule: WCB Case Number is required -----
    if not data.get("wcb_case_number"):
        findings.append({
            "rule": "REQUIRED_CASE_NUMBER",
            "severity": "error",
            "message": "WCB Case Number is required.",
        })

    # ----- Rule: Carrier information -----
    if not data.get("carrier_code") and not data.get("carrier_name"):
        findings.append({
            "rule": "REQUIRED_CARRIER",
            "severity": "error",
            "message": "Carrier code or carrier name is required.",
        })

    # ----- Rule: At least one reason code -----
    reason_codes = data.get("reason_codes", [])
    if not reason_codes:
        findings.append({
            "rule": "REQUIRED_REASON_CODE",
            "severity": "error",
            "message": "At least one reason code must be selected.",
        })

    # ----- Rule: Certification date cannot be today -----
    today_str = date.today().isoformat()
    today_variants = [
        today_str,
        date.today().strftime("%m/%d/%Y"),
        date.today().strftime("%m-%d-%Y"),
    ]
    for rc in reason_codes:
        cert_date = rc.get("certification_date", "")
        if cert_date in today_variants:
            findings.append({
                "rule": "CERT_DATE_NOT_TODAY",
                "severity": "error",
                "message": (
                    f"Certification date for reason code {rc.get('code', '?')} "
                    f"cannot be today's date ({today_str}). "
                    "WCB requires the certification date to be a past date."
                ),
            })

    # ----- Rule: Reason codes must be valid -----
    valid_codes = set(REQUIRED_DOCUMENTS.keys())
    for rc in reason_codes:
        code = rc.get("code", "")
        if code not in valid_codes:
            findings.append({
                "rule": "INVALID_REASON_CODE",
                "severity": "error",
                "message": f"Reason code '{code}' is not a valid AIRA reason code.",
            })

    # ----- Rule: Required documents per reason code -----
    submitted_doc_types = {
        doc.get("type", "") for doc in data.get("supporting_documents", [])
    }
    for rc in reason_codes:
        code = rc.get("code", "")
        required = REQUIRED_DOCUMENTS.get(code, [])
        for req_doc in required:
            if req_doc not in submitted_doc_types:
                findings.append({
                    "rule": "MISSING_REQUIRED_DOCUMENT",
                    "severity": "warning",
                    "message": (
                        f"Reason code {code} requires document type '{req_doc}' "
                        f"which has not been attached."
                    ),
                })

    # ----- Rule: Attestation must be accepted -----
    if not data.get("attestation_accepted"):
        findings.append({
            "rule": "ATTESTATION_REQUIRED",
            "severity": "error",
            "message": "Attestation must be accepted before submission.",
        })

    # ----- Rule: Narrative max 500 characters -----
    narrative = data.get("narrative", "")
    if narrative and len(narrative) > 500:
        findings.append({
            "rule": "NARRATIVE_TOO_LONG",
            "severity": "error",
            "message": (
                f"Narrative is {len(narrative)} characters. "
                f"Maximum allowed is 500 characters."
            ),
        })

    # ----- Rule: Date of injury is required -----
    if not data.get("date_of_injury"):
        findings.append({
            "rule": "REQUIRED_DATE_OF_INJURY",
            "severity": "error",
            "message": "Date of injury is required.",
        })

    # ----- Rule: Claimant name is required -----
    if not data.get("claimant_name"):
        findings.append({
            "rule": "REQUIRED_CLAIMANT_NAME",
            "severity": "error",
            "message": "Claimant name is required.",
        })

    # ----- Rule: Only one draft per case -----
    # This is enforced at the database/API layer, but flag it if metadata present.
    if data.get("_existing_draft_id"):
        findings.append({
            "rule": "DUPLICATE_DRAFT",
            "severity": "error",
            "message": (
                f"An existing draft (ID: {data['_existing_draft_id']}) already exists "
                f"for case {data.get('wcb_case_number', '?')}. "
                "Only one draft per case is permitted."
            ),
        })

    # ----- Rule: Volunteer case restrictions -----
    if data.get("is_volunteer"):
        # Volunteers cannot use certain reason codes
        restricted_for_volunteers = {"OER", "OUI"}
        for rc in reason_codes:
            code = rc.get("code", "")
            if code in restricted_for_volunteers:
                findings.append({
                    "rule": "VOLUNTEER_RESTRICTED_CODE",
                    "severity": "error",
                    "message": (
                        f"Reason code {code} is not applicable to volunteer "
                        f"firefighter/ambulance worker cases."
                    ),
                })

        # Volunteer cases require district specification
        if not data.get("district"):
            findings.append({
                "rule": "VOLUNTEER_REQUIRES_DISTRICT",
                "severity": "warning",
                "message": "Volunteer cases should specify the WCB district office.",
            })

    # ----- Rule: MCI-specific validations -----
    mci_codes = [rc for rc in reason_codes if rc.get("code") == "MCI"]
    for rc in mci_codes:
        details = rc.get("details", {})
        if isinstance(details, dict):
            if not details.get("mmi_date"):
                findings.append({
                    "rule": "MCI_REQUIRES_MMI_DATE",
                    "severity": "error",
                    "message": "MCI reason code requires a Maximum Medical Improvement (MMI) date.",
                })
            if not details.get("disability_classification"):
                findings.append({
                    "rule": "MCI_REQUIRES_CLASSIFICATION",
                    "severity": "error",
                    "message": "MCI reason code requires a disability classification.",
                })
            if not details.get("degree_of_disability"):
                findings.append({
                    "rule": "MCI_REQUIRES_DEGREE",
                    "severity": "warning",
                    "message": "MCI reason code should include a degree of disability.",
                })

    # ----- Rule: Submission date should not be in the future -----
    sub_date_str = data.get("submission_date")
    if sub_date_str:
        try:
            sub_date = datetime.strptime(sub_date_str, "%Y-%m-%d").date()
            if sub_date > date.today():
                findings.append({
                    "rule": "FUTURE_SUBMISSION_DATE",
                    "severity": "error",
                    "message": "Submission date cannot be in the future.",
                })
        except ValueError:
            findings.append({
                "rule": "INVALID_SUBMISSION_DATE",
                "severity": "error",
                "message": f"Submission date '{sub_date_str}' is not a valid date (expected YYYY-MM-DD).",
            })

    return findings
