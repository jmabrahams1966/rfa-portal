"""
Multi-State Expansion Framework for Workers' Compensation filings.

Extensible architecture where each state's WC filing has its own configuration,
validation rules, and XML generation logic. Currently supports NY, NJ, CT, PA.
"""

import xml.etree.ElementTree as ET
from datetime import date
from xml.dom import minidom
from typing import Any

from .xml_service import build_rfa2_xml, validate_submission as validate_ny_submission


# ---------------------------------------------------------------------------
# State Configuration Registry
# ---------------------------------------------------------------------------

STATE_CONFIGS: dict[str, dict[str, Any]] = {
    "NY": {
        "name": "New York",
        "board": "NYS Workers' Compensation Board",
        "form_name": "AIRA",
        "form_description": "Request for Further Action",
        "api_endpoint": "https://onboard.wcb.ny.gov/api/submit",
        "reason_codes": [
            {"code": "CPD", "name": "Controvert Prior Decision/Order — Disability"},
            {"code": "CPR", "name": "Controvert Prior Decision/Order — Rescission"},
            {"code": "CPI", "name": "Controvert Prior Decision/Order — Impairment"},
            {"code": "CPS", "name": "Controvert Prior Decision/Order — Section 32"},
            {"code": "MCI", "name": "Medical Issue — Classification/Impairment"},
            {"code": "MOW", "name": "Medical Issue — Other Work Capacity"},
            {"code": "MIA", "name": "Medical Issue — Independent Assessment"},
            {"code": "OER", "name": "Other Issue — Employer Request"},
            {"code": "OIL", "name": "Other Issue — Independent Living"},
            {"code": "ORD", "name": "Other Issue — Reduced Disability"},
            {"code": "OID", "name": "Other Issue — Insurance Dispute"},
            {"code": "OCD", "name": "Other Issue — Change of Doctor"},
            {"code": "OUI", "name": "Other Issue — Uninsured"},
        ],
        "xml_schema": "eFormsRfa2.xsd",
        "filing_deadlines": {
            "controvert": 25,
            "medical": 30,
            "general": 45,
            "section_32": 60,
        },
        "districts": [
            "Albany",
            "Binghamton",
            "Buffalo",
            "Hauppauge",
            "NYC",
            "Peekskill",
            "Rochester",
            "Syracuse",
        ],
        "required_fields": [
            "wcb_case_number",
            "carrier_code",
            "claimant_name",
            "date_of_injury",
            "reason_codes",
            "attestation_accepted",
        ],
    },
    "NJ": {
        "name": "New Jersey",
        "board": "NJ Division of Workers' Compensation",
        "form_name": "Application for Informal Hearing",
        "form_description": "Request for hearing before a Judge of Compensation",
        "api_endpoint": None,
        "reason_codes": [
            {"code": "TEMP_MOD", "name": "Temporary Disability Modification"},
            {"code": "PERM_CLAIM", "name": "Permanent Disability Claim"},
            {"code": "MED_AUTH", "name": "Medical Treatment Authorization"},
            {"code": "SETTLE", "name": "Settlement (Section 22)"},
            {"code": "REOPEN", "name": "Reopened Claim"},
        ],
        "xml_schema": "nj_wc_informal_hearing.xsd",
        "filing_deadlines": {"default": 60},
        "districts": [
            "Newark",
            "Hackensack",
            "New Brunswick",
            "Toms River",
            "Camden",
            "Trenton",
        ],
        "required_fields": [
            "case_number",
            "petitioner_name",
            "respondent_name",
            "date_of_injury",
            "reason_codes",
        ],
    },
    "CT": {
        "name": "Connecticut",
        "board": "CT Workers' Compensation Commission",
        "form_name": "Form 43",
        "form_description": "Notice to Discontinue or Reduce Benefits",
        "api_endpoint": None,
        "reason_codes": [
            {"code": "DISC", "name": "Discontinue Benefits"},
            {"code": "REDUCE", "name": "Reduce Benefits"},
            {"code": "MMI", "name": "Maximum Medical Improvement"},
            {"code": "LIGHT_DUTY", "name": "Light Duty Available"},
            {"code": "NONCOMPLIANCE", "name": "Claimant Non-Compliance"},
        ],
        "xml_schema": "ct_form43.xsd",
        "filing_deadlines": {"default": 30},
        "districts": [
            "Hartford",
            "Bridgeport",
            "New Haven",
            "Norwich",
            "Waterbury",
        ],
        "required_fields": [
            "case_number",
            "claimant_name",
            "employer_name",
            "date_of_injury",
            "reason_codes",
            "proposed_action_date",
        ],
    },
    "PA": {
        "name": "Pennsylvania",
        "board": "PA Bureau of Workers' Compensation",
        "form_name": "Petition to Modify/Suspend",
        "form_description": "Petition filed with the Bureau of Workers' Compensation",
        "api_endpoint": None,
        "reason_codes": [
            {"code": "SUSPEND", "name": "Petition to Suspend Compensation"},
            {"code": "MODIFY", "name": "Petition to Modify Compensation"},
            {"code": "TERMINATE", "name": "Petition to Terminate Compensation"},
            {"code": "REVIEW", "name": "Petition for Review"},
            {"code": "UTILIZATION", "name": "Utilization Review Determination"},
        ],
        "xml_schema": "pa_wc_petition.xsd",
        "filing_deadlines": {"default": 45},
        "districts": [
            "Philadelphia",
            "Pittsburgh",
            "Harrisburg",
            "Scranton",
            "Erie",
            "Allentown",
        ],
        "required_fields": [
            "claim_number",
            "claimant_name",
            "employer_name",
            "insurer_name",
            "date_of_injury",
            "reason_codes",
        ],
    },
}


# ---------------------------------------------------------------------------
# State-Specific Validation Rules
# ---------------------------------------------------------------------------

_NJ_VALIDATION_RULES: dict[str, dict] = {
    "TEMP_MOD": {
        "required_docs": ["medical_report", "wage_statement"],
        "fields": ["current_disability_rate", "proposed_rate"],
    },
    "PERM_CLAIM": {
        "required_docs": ["ime_report", "disability_evaluation"],
        "fields": ["permanency_percentage", "body_part"],
    },
    "MED_AUTH": {
        "required_docs": ["treatment_plan", "medical_records"],
        "fields": ["treatment_description", "provider_name"],
    },
    "SETTLE": {
        "required_docs": ["settlement_agreement"],
        "fields": ["settlement_amount"],
    },
    "REOPEN": {
        "required_docs": ["medical_report"],
        "fields": ["original_closing_date", "reason_for_reopening"],
    },
}

_CT_VALIDATION_RULES: dict[str, dict] = {
    "DISC": {
        "required_docs": ["medical_report", "employer_statement"],
        "fields": ["proposed_discontinue_date", "basis_for_discontinuance"],
    },
    "REDUCE": {
        "required_docs": ["medical_report", "wage_records"],
        "fields": ["current_rate", "proposed_rate", "effective_date"],
    },
    "MMI": {
        "required_docs": ["mmi_certification", "ime_report"],
        "fields": ["mmi_date", "permanency_rating"],
    },
    "LIGHT_DUTY": {
        "required_docs": ["job_description", "medical_clearance"],
        "fields": ["job_title", "physical_requirements", "available_date"],
    },
    "NONCOMPLIANCE": {
        "required_docs": ["correspondence_log", "medical_records"],
        "fields": ["noncompliance_type", "dates_of_noncompliance"],
    },
}

_PA_VALIDATION_RULES: dict[str, dict] = {
    "SUSPEND": {
        "required_docs": ["medical_report", "return_to_work_notice"],
        "fields": ["suspension_date", "basis_for_suspension"],
    },
    "MODIFY": {
        "required_docs": ["medical_report", "labor_market_survey"],
        "fields": ["current_rate", "proposed_rate", "earning_capacity"],
    },
    "TERMINATE": {
        "required_docs": ["ime_report", "medical_records"],
        "fields": ["full_recovery_date", "physician_name"],
    },
    "REVIEW": {
        "required_docs": ["medical_records"],
        "fields": ["review_basis"],
    },
    "UTILIZATION": {
        "required_docs": ["utilization_review_report"],
        "fields": ["treatment_under_review", "ur_determination"],
    },
}

_STATE_VALIDATION_RULES: dict[str, dict[str, dict]] = {
    "NJ": _NJ_VALIDATION_RULES,
    "CT": _CT_VALIDATION_RULES,
    "PA": _PA_VALIDATION_RULES,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_supported_states() -> list[dict]:
    """List all supported states with their form names and metadata."""
    states = []
    for code, config in STATE_CONFIGS.items():
        states.append({
            "state_code": code,
            "name": config["name"],
            "board": config["board"],
            "form_name": config["form_name"],
            "form_description": config.get("form_description", ""),
            "reason_code_count": len(config["reason_codes"]),
            "district_count": len(config["districts"]),
            "has_api_endpoint": config.get("api_endpoint") is not None,
        })
    return states


def get_state_config(state_code: str) -> dict:
    """Full configuration for a state. Raises ValueError if unsupported."""
    state_code = state_code.upper()
    if state_code not in STATE_CONFIGS:
        raise ValueError(
            f"Unsupported state: {state_code}. "
            f"Supported states: {', '.join(STATE_CONFIGS.keys())}"
        )
    return STATE_CONFIGS[state_code]


def get_state_reason_codes(state_code: str) -> list[dict]:
    """Reason codes for a state."""
    config = get_state_config(state_code)
    return config["reason_codes"]


def get_state_districts(state_code: str) -> list[str]:
    """Districts/offices for a state."""
    config = get_state_config(state_code)
    return config["districts"]


def get_state_deadlines(state_code: str) -> dict:
    """Deadline rules for a state."""
    config = get_state_config(state_code)
    return config["filing_deadlines"]


# ---------------------------------------------------------------------------
# XML Generation
# ---------------------------------------------------------------------------

async def build_state_xml(state_code: str, submission_data: dict) -> str:
    """
    Generate state-specific XML for a WC filing submission.

    For NY, delegates to the existing xml_service.build_rfa2_xml.
    For other states, generates a generic XML structure following their schema patterns.
    """
    state_code = state_code.upper()
    config = get_state_config(state_code)

    if state_code == "NY":
        return build_rfa2_xml(submission_data)

    if state_code == "NJ":
        return _build_nj_xml(config, submission_data)

    if state_code == "CT":
        return _build_ct_xml(config, submission_data)

    if state_code == "PA":
        return _build_pa_xml(config, submission_data)

    return _build_generic_xml(state_code, config, submission_data)


def _pretty_xml(root: ET.Element) -> str:
    """Render an ElementTree root to a pretty-printed XML string."""
    rough = ET.tostring(root, encoding="unicode", xml_declaration=False)
    parsed = minidom.parseString(rough)
    pretty = parsed.toprettyxml(indent="  ", encoding=None)
    lines = pretty.split("\n")
    if lines and lines[0].startswith("<?xml"):
        lines[0] = '<?xml version="1.0" encoding="utf-8"?>'
    else:
        lines.insert(0, '<?xml version="1.0" encoding="utf-8"?>')
    return "\n".join(line for line in lines if line.strip())


def _add_text(parent: ET.Element, tag: str, text: str) -> ET.Element:
    el = ET.SubElement(parent, tag)
    el.text = text
    return el


def _build_nj_xml(config: dict, data: dict) -> str:
    """Generate NJ Application for Informal Hearing XML."""
    root = ET.Element("InformalHearingApplication")
    root.set("xmlns", "http://www.nj.gov/labor/wc/eforms")
    root.set("state", "NJ")

    header = ET.SubElement(root, "Header")
    _add_text(header, "CaseNumber", data.get("case_number", ""))
    _add_text(header, "FilingDate", data.get("filing_date", date.today().isoformat()))
    _add_text(header, "District", data.get("district", ""))

    petitioner = ET.SubElement(root, "Petitioner")
    _add_text(petitioner, "Name", data.get("petitioner_name", ""))
    _add_text(petitioner, "Type", data.get("petitioner_type", "employer"))
    _add_text(petitioner, "Address", data.get("petitioner_address", ""))
    _add_text(petitioner, "Phone", data.get("petitioner_phone", ""))
    _add_text(petitioner, "Attorney", data.get("petitioner_attorney", ""))

    respondent = ET.SubElement(root, "Respondent")
    _add_text(respondent, "Name", data.get("respondent_name", ""))
    _add_text(respondent, "Address", data.get("respondent_address", ""))
    _add_text(respondent, "Attorney", data.get("respondent_attorney", ""))

    claim = ET.SubElement(root, "ClaimDetails")
    _add_text(claim, "DateOfInjury", data.get("date_of_injury", ""))
    _add_text(claim, "EmployerName", data.get("employer_name", ""))
    _add_text(claim, "InsuranceCarrier", data.get("insurance_carrier", ""))
    _add_text(claim, "PolicyNumber", data.get("policy_number", ""))

    reasons_el = ET.SubElement(root, "ReasonCodes")
    for rc in data.get("reason_codes", []):
        rc_el = ET.SubElement(reasons_el, "ReasonCode")
        rc_el.set("code", rc.get("code", ""))
        _add_text(rc_el, "Description", rc.get("description", ""))
        details = rc.get("details")
        if details and isinstance(details, dict):
            details_el = ET.SubElement(rc_el, "Details")
            for key, value in details.items():
                _add_text(details_el, key, str(value) if value is not None else "")

    narrative = data.get("narrative", "")
    if narrative:
        _add_text(root, "StatementOfClaim", narrative[:1000])

    docs = data.get("supporting_documents", [])
    if docs:
        docs_el = ET.SubElement(root, "Exhibits")
        for doc in docs:
            doc_el = ET.SubElement(docs_el, "Exhibit")
            doc_el.set("type", doc.get("type", ""))
            doc_el.set("fileName", doc.get("file_name", ""))

    return _pretty_xml(root)


def _build_ct_xml(config: dict, data: dict) -> str:
    """Generate CT Form 43 XML."""
    root = ET.Element("Form43")
    root.set("xmlns", "http://wcc.state.ct.us/eforms")
    root.set("state", "CT")

    header = ET.SubElement(root, "Header")
    _add_text(header, "CaseNumber", data.get("case_number", ""))
    _add_text(header, "FilingDate", data.get("filing_date", date.today().isoformat()))
    _add_text(header, "District", data.get("district", ""))

    claimant = ET.SubElement(root, "Claimant")
    _add_text(claimant, "Name", data.get("claimant_name", ""))
    _add_text(claimant, "SSNLast4", data.get("ssn_last4", ""))
    _add_text(claimant, "DateOfInjury", data.get("date_of_injury", ""))
    _add_text(claimant, "Address", data.get("claimant_address", ""))

    employer = ET.SubElement(root, "Employer")
    _add_text(employer, "Name", data.get("employer_name", ""))
    _add_text(employer, "Address", data.get("employer_address", ""))
    _add_text(employer, "FEIN", data.get("employer_fein", ""))

    insurer = ET.SubElement(root, "Insurer")
    _add_text(insurer, "Name", data.get("insurer_name", ""))
    _add_text(insurer, "PolicyNumber", data.get("policy_number", ""))
    _add_text(insurer, "AdjusterName", data.get("adjuster_name", ""))
    _add_text(insurer, "AdjusterPhone", data.get("adjuster_phone", ""))

    action = ET.SubElement(root, "ProposedAction")
    reasons_el = ET.SubElement(action, "ReasonCodes")
    for rc in data.get("reason_codes", []):
        rc_el = ET.SubElement(reasons_el, "ReasonCode")
        rc_el.set("code", rc.get("code", ""))
        _add_text(rc_el, "Description", rc.get("description", ""))
        details = rc.get("details")
        if details and isinstance(details, dict):
            details_el = ET.SubElement(rc_el, "Details")
            for key, value in details.items():
                _add_text(details_el, key, str(value) if value is not None else "")

    _add_text(action, "ProposedDate", data.get("proposed_action_date", ""))
    _add_text(action, "CurrentWeeklyRate", str(data.get("current_weekly_rate", "")))
    _add_text(action, "ProposedWeeklyRate", str(data.get("proposed_weekly_rate", "")))

    narrative = data.get("narrative", "")
    if narrative:
        _add_text(root, "BasisForAction", narrative[:1000])

    medical = ET.SubElement(root, "MedicalEvidence")
    _add_text(medical, "PhysicianName", data.get("physician_name", ""))
    _add_text(medical, "LastExamDate", data.get("last_exam_date", ""))
    _add_text(medical, "Diagnosis", data.get("diagnosis", ""))

    docs = data.get("supporting_documents", [])
    if docs:
        docs_el = ET.SubElement(root, "Attachments")
        for doc in docs:
            doc_el = ET.SubElement(docs_el, "Attachment")
            doc_el.set("type", doc.get("type", ""))
            doc_el.set("fileName", doc.get("file_name", ""))

    return _pretty_xml(root)


def _build_pa_xml(config: dict, data: dict) -> str:
    """Generate PA Petition to Modify/Suspend XML."""
    root = ET.Element("WorkersCompPetition")
    root.set("xmlns", "http://www.dli.pa.gov/wc/eforms")
    root.set("state", "PA")

    header = ET.SubElement(root, "Header")
    _add_text(header, "ClaimNumber", data.get("claim_number", ""))
    _add_text(header, "FilingDate", data.get("filing_date", date.today().isoformat()))
    _add_text(header, "District", data.get("district", ""))
    _add_text(header, "BureauClaimNumber", data.get("bureau_claim_number", ""))

    claimant = ET.SubElement(root, "Claimant")
    _add_text(claimant, "Name", data.get("claimant_name", ""))
    _add_text(claimant, "SSNLast4", data.get("ssn_last4", ""))
    _add_text(claimant, "DateOfInjury", data.get("date_of_injury", ""))
    _add_text(claimant, "Address", data.get("claimant_address", ""))
    _add_text(claimant, "InjuryDescription", data.get("injury_description", ""))

    employer = ET.SubElement(root, "Employer")
    _add_text(employer, "Name", data.get("employer_name", ""))
    _add_text(employer, "Address", data.get("employer_address", ""))
    _add_text(employer, "FEIN", data.get("employer_fein", ""))

    insurer = ET.SubElement(root, "Insurer")
    _add_text(insurer, "Name", data.get("insurer_name", ""))
    _add_text(insurer, "PolicyNumber", data.get("policy_number", ""))
    _add_text(insurer, "ClaimsAdjuster", data.get("claims_adjuster", ""))

    petition = ET.SubElement(root, "PetitionDetails")
    reasons_el = ET.SubElement(petition, "PetitionTypes")
    for rc in data.get("reason_codes", []):
        rc_el = ET.SubElement(reasons_el, "PetitionType")
        rc_el.set("code", rc.get("code", ""))
        _add_text(rc_el, "Description", rc.get("description", ""))
        details = rc.get("details")
        if details and isinstance(details, dict):
            details_el = ET.SubElement(rc_el, "Details")
            for key, value in details.items():
                _add_text(details_el, key, str(value) if value is not None else "")

    _add_text(petition, "EffectiveDate", data.get("effective_date", ""))
    _add_text(petition, "CurrentCompRate", str(data.get("current_comp_rate", "")))
    _add_text(petition, "ProposedCompRate", str(data.get("proposed_comp_rate", "")))

    narrative = data.get("narrative", "")
    if narrative:
        _add_text(root, "BasisForPetition", narrative[:2000])

    _add_text(root, "AttorneyName", data.get("attorney_name", ""))
    _add_text(root, "AttorneyBarNumber", data.get("attorney_bar_number", ""))

    docs = data.get("supporting_documents", [])
    if docs:
        docs_el = ET.SubElement(root, "Exhibits")
        for doc in docs:
            doc_el = ET.SubElement(docs_el, "Exhibit")
            doc_el.set("type", doc.get("type", ""))
            doc_el.set("fileName", doc.get("file_name", ""))

    return _pretty_xml(root)


def _build_generic_xml(state_code: str, config: dict, data: dict) -> str:
    """Fallback generic XML for any state not yet given custom templates."""
    root = ET.Element("WorkersCompFiling")
    root.set("state", state_code)

    header = ET.SubElement(root, "Header")
    _add_text(header, "FormName", config["form_name"])
    _add_text(header, "Board", config["board"])
    _add_text(header, "CaseNumber", data.get("case_number", ""))
    _add_text(header, "FilingDate", data.get("filing_date", date.today().isoformat()))
    _add_text(header, "District", data.get("district", ""))

    claimant = ET.SubElement(root, "Claimant")
    _add_text(claimant, "Name", data.get("claimant_name", ""))
    _add_text(claimant, "DateOfInjury", data.get("date_of_injury", ""))

    employer = ET.SubElement(root, "Employer")
    _add_text(employer, "Name", data.get("employer_name", ""))

    reasons_el = ET.SubElement(root, "ReasonCodes")
    for rc in data.get("reason_codes", []):
        rc_el = ET.SubElement(reasons_el, "ReasonCode")
        rc_el.set("code", rc.get("code", ""))
        _add_text(rc_el, "Description", rc.get("description", ""))

    narrative = data.get("narrative", "")
    if narrative:
        _add_text(root, "Narrative", narrative[:1000])

    docs = data.get("supporting_documents", [])
    if docs:
        docs_el = ET.SubElement(root, "Documents")
        for doc in docs:
            doc_el = ET.SubElement(docs_el, "Document")
            doc_el.set("type", doc.get("type", ""))
            doc_el.set("fileName", doc.get("file_name", ""))

    return _pretty_xml(root)


# ---------------------------------------------------------------------------
# State-Specific Validation
# ---------------------------------------------------------------------------

async def validate_state_submission(state_code: str, data: dict) -> list[dict]:
    """
    Validate a submission against state-specific rules.

    For NY, delegates to the existing xml_service.validate_submission.
    For other states, applies generic + state-specific validation.

    Returns list of findings: [{rule, severity, message}, ...]
    """
    state_code = state_code.upper()
    config = get_state_config(state_code)

    if state_code == "NY":
        return validate_ny_submission(data)

    findings: list[dict] = []

    # --- Generic required-field checks ---
    for field in config.get("required_fields", []):
        if not data.get(field):
            findings.append({
                "rule": f"REQUIRED_{field.upper()}",
                "severity": "error",
                "message": f"Field '{field}' is required for {config['name']} {config['form_name']} filings.",
            })

    # --- Reason codes must be valid for this state ---
    valid_codes = {rc["code"] for rc in config["reason_codes"]}
    reason_codes = data.get("reason_codes", [])

    if not reason_codes:
        findings.append({
            "rule": "REQUIRED_REASON_CODE",
            "severity": "error",
            "message": "At least one reason code must be selected.",
        })

    for rc in reason_codes:
        code = rc.get("code", "")
        if code not in valid_codes:
            findings.append({
                "rule": "INVALID_REASON_CODE",
                "severity": "error",
                "message": (
                    f"Reason code '{code}' is not valid for "
                    f"{config['name']} {config['form_name']} filings. "
                    f"Valid codes: {', '.join(sorted(valid_codes))}"
                ),
            })

    # --- District must be valid for this state ---
    district = data.get("district")
    if district and district not in config["districts"]:
        findings.append({
            "rule": "INVALID_DISTRICT",
            "severity": "warning",
            "message": (
                f"District '{district}' is not a recognized "
                f"{config['name']} district. "
                f"Valid districts: {', '.join(config['districts'])}"
            ),
        })

    # --- Date of injury validation ---
    doi = data.get("date_of_injury")
    if doi:
        try:
            from datetime import datetime
            doi_date = datetime.strptime(doi, "%Y-%m-%d").date() if "-" in doi else datetime.strptime(doi, "%m/%d/%Y").date()
            if doi_date > date.today():
                findings.append({
                    "rule": "FUTURE_DATE_OF_INJURY",
                    "severity": "error",
                    "message": "Date of injury cannot be in the future.",
                })
        except ValueError:
            findings.append({
                "rule": "INVALID_DATE_FORMAT",
                "severity": "error",
                "message": f"Date of injury '{doi}' is not a valid date.",
            })

    # --- State-specific reason code validation ---
    state_rules = _STATE_VALIDATION_RULES.get(state_code, {})
    submitted_doc_types = {
        doc.get("type", "") for doc in data.get("supporting_documents", [])
    }

    for rc in reason_codes:
        code = rc.get("code", "")
        rules = state_rules.get(code)
        if not rules:
            continue

        # Check required documents for this reason code
        for req_doc in rules.get("required_docs", []):
            if req_doc not in submitted_doc_types:
                findings.append({
                    "rule": "MISSING_REQUIRED_DOCUMENT",
                    "severity": "warning",
                    "message": (
                        f"Reason code '{code}' in {config['name']} requires "
                        f"document type '{req_doc}' which has not been attached."
                    ),
                })

        # Check required fields in the reason code details
        details = rc.get("details", {})
        if isinstance(details, dict):
            for req_field in rules.get("fields", []):
                if not details.get(req_field):
                    findings.append({
                        "rule": f"MISSING_DETAIL_{req_field.upper()}",
                        "severity": "warning",
                        "message": (
                            f"Reason code '{code}' in {config['name']} should include "
                            f"'{req_field}' in its details."
                        ),
                    })

    # --- CT-specific: Form 43 requires 30-day notice ---
    if state_code == "CT":
        proposed_date = data.get("proposed_action_date")
        if proposed_date:
            try:
                from datetime import datetime
                prop = datetime.strptime(proposed_date, "%Y-%m-%d").date()
                days_until = (prop - date.today()).days
                if days_until < 30:
                    findings.append({
                        "rule": "CT_INSUFFICIENT_NOTICE",
                        "severity": "error",
                        "message": (
                            f"Connecticut Form 43 requires at least 30 days notice. "
                            f"Proposed action date is only {days_until} days away."
                        ),
                    })
            except ValueError:
                findings.append({
                    "rule": "INVALID_PROPOSED_DATE",
                    "severity": "error",
                    "message": f"Proposed action date '{proposed_date}' is not a valid date.",
                })

    # --- PA-specific: Petition requires attorney for certain types ---
    if state_code == "PA":
        attorney_required_codes = {"SUSPEND", "MODIFY", "TERMINATE"}
        has_attorney_code = any(
            rc.get("code") in attorney_required_codes for rc in reason_codes
        )
        if has_attorney_code and not data.get("attorney_name"):
            findings.append({
                "rule": "PA_ATTORNEY_RECOMMENDED",
                "severity": "warning",
                "message": (
                    "PA petitions to Suspend, Modify, or Terminate compensation "
                    "typically require attorney representation."
                ),
            })

    # --- NJ-specific: Statute of limitations check ---
    if state_code == "NJ" and doi:
        try:
            from datetime import datetime
            doi_date = datetime.strptime(doi, "%Y-%m-%d").date() if "-" in doi else datetime.strptime(doi, "%m/%d/%Y").date()
            years_since = (date.today() - doi_date).days / 365.25
            if years_since > 2:
                findings.append({
                    "rule": "NJ_STATUTE_WARNING",
                    "severity": "warning",
                    "message": (
                        f"Date of injury is over {int(years_since)} years ago. "
                        "NJ workers' compensation claims generally have a 2-year "
                        "statute of limitations. Verify applicability."
                    ),
                })
        except ValueError:
            pass  # Already caught above

    return findings
