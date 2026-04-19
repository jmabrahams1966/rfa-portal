"""WCB XML Builder — generates XML matching the official eFormsRfa1lc.xsd schema.

Based on the actual WCB sample XMLs (eFormsMci1.xml, eFormsCnw1.xml, etc.)
and the eFormsRfa1lc.xsd schema definition.

XML Structure:
<eForms>
  <Header>
    <APIHeader>
      <SubmitterClientId/>
      <SenderPOI/>           (R-number)
      <SubmitDate/>
    </APIHeader>
  </Header>
  <Events>
    <EventCode code="RFA-1LC">
      <TransactionSequenceNumber/>
      <WCBCaseID/>
      <DateOfInjury>
        <DoiMonth/><DoiDay/><DoiYear/>
      </DateOfInjury>
      <AttestationConfirmationCode/>
      <AttorneyLicensedRep.../>
      <Reasons>
        <Reason index="1">
          <ReasonCode/>
          <ReasonCodeCategory/>
          ...reason-specific fields...
        </Reason>
      </Reasons>
      <SupportingDocuments>
        <UploadedDocuments>...</UploadedDocuments>
        <ReferencedDocuments>...</ReferencedDocuments>
      </SupportingDocuments>
      <AdditionalProposedFinding>...</AdditionalProposedFinding>
    </EventCode>
  </Events>
</eForms>
"""

import base64
import uuid
import xml.etree.ElementTree as ET
from datetime import date, datetime
from xml.dom import minidom
from typing import Optional


# ── Reason Code Categories (all 20 WCB codes) ──────────────────────────────
REASON_CATEGORIES = {
    # Compensation (C) — RFA-1LC
    "CNW": "C",  # Compensation - not working / not receiving payments
    "CAW": "C",  # Compensation - AWW adjustments
    "CVW": "C",  # Compensation - volunteer workers
    # Compensation (C) — AIRA
    "CPD": "C",  # Compensation - permanent disability
    "CPR": "C",  # Compensation - prior findings
    "CPI": "C",  # Compensation - penalty/interest
    "CPS": "C",  # Compensation - PPD schedule award
    "CRE": "C",  # Compensation - reduced earnings
    # Medical (M)
    "MBC": "M",  # Medical - body parts/conditions
    "MCI": "M",  # Medical - maximum medical improvement
    "MOW": "M",  # Medical - ongoing/withdrawal of treatment
    "MIA": "M",  # Medical - independent medical assessment
    # Other (O)
    "OER": "O",  # Other - employer request for hearing
    "OIL": "O",  # Other - insurance lapse
    "ORD": "O",  # Other - request to discontinue/modify
    "OID": "O",  # Other - insurance dispute
    "OCD": "O",  # Other - carrier dispute
    "OUI": "O",  # Other - uninsured employer
    "OIW": "O",  # Other - injured worker request
    "OOT": "O",  # Other - other
}


# ── WCB Body Part Codes (official 50 codes) ─────────────────────────────────
WCB_BODY_PARTS = {
    # Head & Trunk - Head
    "10": {"text": "Head", "group": "Head & Trunk", "has_side": False},
    "11": {"text": "Skull", "group": "Head & Trunk", "has_side": False},
    "12": {"text": "Brain", "group": "Head & Trunk", "has_side": False},
    "13": {"text": "Ear", "group": "Head & Trunk", "has_side": True},
    "14": {"text": "Eye", "group": "Head & Trunk", "has_side": True},
    "15": {"text": "Nose", "group": "Head & Trunk", "has_side": False},
    "16": {"text": "Teeth", "group": "Head & Trunk", "has_side": False},
    "17": {"text": "Mouth", "group": "Head & Trunk", "has_side": False},
    "18": {"text": "Soft tissue of the Head", "group": "Head & Trunk", "has_side": False},
    "19": {"text": "Facial bones", "group": "Head & Trunk", "has_side": False},
    # Back & Neck
    "20": {"text": "Neck", "group": "Back & Neck", "has_side": False},
    "21": {"text": "Vertebrae (neck)", "group": "Back & Neck", "has_side": False},
    "22": {"text": "Disc in the neck", "group": "Back & Neck", "has_side": False},
    "23": {"text": "Spinal cord in the neck", "group": "Back & Neck", "has_side": False},
    "24": {"text": "Larynx", "group": "Back & Neck", "has_side": False},
    "25": {"text": "Soft tissue neck", "group": "Back & Neck", "has_side": False},
    "26": {"text": "Trachea", "group": "Back & Neck", "has_side": False},
    # Upper Extremities
    "31": {"text": "Upper arm", "group": "Extremities", "has_side": True},
    "32": {"text": "Elbow", "group": "Extremities", "has_side": True},
    "33": {"text": "Lower arm", "group": "Extremities", "has_side": True},
    "34": {"text": "Wrist", "group": "Extremities", "has_side": True},
    "35": {"text": "Hand", "group": "Extremities", "has_side": True},
    "36": {"text": "Fingers other than thumb", "group": "Extremities", "has_side": True, "fingers": True},
    "37": {"text": "Thumb", "group": "Extremities", "has_side": True},
    "38": {"text": "Shoulder", "group": "Extremities", "has_side": True},
    # Back
    "41": {"text": "Upper back area", "group": "Back & Neck", "has_side": False},
    "42": {"text": "Lower back area", "group": "Back & Neck", "has_side": False},
    "43": {"text": "Disc in the trunk", "group": "Head & Trunk", "has_side": False},
    "44": {"text": "Chest", "group": "Head & Trunk", "has_side": False},
    "45": {"text": "Sacrum and coccyx", "group": "Head & Trunk", "has_side": False},
    "46": {"text": "Pelvis", "group": "Head & Trunk", "has_side": False},
    "47": {"text": "Spinal cord in the trunk", "group": "Head & Trunk", "has_side": False},
    "48": {"text": "Internal organs other than heart & lungs", "group": "Head & Trunk", "has_side": False},
    "49": {"text": "Heart", "group": "Head & Trunk", "has_side": False},
    # Lower Extremities
    "51": {"text": "Hip", "group": "Extremities", "has_side": True},
    "52": {"text": "Upper leg", "group": "Extremities", "has_side": True},
    "53": {"text": "Knee", "group": "Extremities", "has_side": True},
    "54": {"text": "Lower leg", "group": "Extremities", "has_side": True},
    "55": {"text": "Ankle", "group": "Extremities", "has_side": True},
    "56": {"text": "Foot", "group": "Extremities", "has_side": True},
    "57": {"text": "Toes", "group": "Extremities", "has_side": True, "toes": True},
    "58": {"text": "Great toe", "group": "Extremities", "has_side": True},
    # Trunk
    "60": {"text": "Lung", "group": "Head & Trunk", "has_side": True},
    "61": {"text": "Abdomen including groin", "group": "Head & Trunk", "has_side": False},
    "62": {"text": "Buttock", "group": "Head & Trunk", "has_side": True},
    # Special
    "65": {"text": "Psychological injury", "group": "Back & Neck", "has_side": False},
    "66": {"text": "Exposure", "group": "Back & Neck", "has_side": False},
    "99": {"text": "Death", "group": "Back & Neck", "has_side": False},
    "00": {"text": "Body Part(s)/Condition(s) not listed", "group": "Back & Neck", "has_side": False},
    "01": {"text": "Consequential Indicator", "group": "Back & Neck", "has_side": False},
}


# ── WCB Error Codes ─────────────────────────────────────────────────────────
WCB_ERROR_CODES = {
    "1001": "Mandatory data not present",
    "1002": "Invalid format",
    "1003": "Corresponding data not found",
    "1004": "Must be unique",
    "1005": "Must be a valid date",
    "1006": "Must be <= current date",
    "1007": "Must be >= Date of Injury",
    "1008": "Invalid code",
    "1009": "Date ranges must not overlap",
    "1010": "Date ranges must be in chronological order",
    "1011": "Invalid data relationship",
    "1014": "Invalid record count",
    "1015": "Must be valid content",
    "1016": "Conditionally mandatory data not present",
    "1017": "Only one transaction per API call is allowed",
    "1018": "Only one EventCode type is allowed in an XML transaction file",
    "1019": "Sender is not authorized to submit an XML transaction file",
    "1020": "Sender is not authorized to submit an API XML transaction",
    "1021": "ReasonCode is not allowed",
    "1022": "R# is not valid for this sender",
    "1023": "Sender is not authorized for this Case_ID",
    "1024": "Must be < current date",
    "1025": "Invalid File Upload",
    "1026": "XML Error",
    "1027": "Internal processor error invoked by FTP",
    "1028": "Missing data element or node",
    "1029": "Duplicate Submission",
    "1030": "Value exceeds maximum",
    "1031": "Value less than minimum",
    "1032": "Not Authorized",
}


# ── WCB Document Form Types ─────────────────────────────────────────────────
WCB_DOCUMENT_FORMS = {
    "AFF-1": "Affidavit for Death Benefits",
    "BIRTH-CERT": "Birth Certificate",
    "C-4.3": "Doctor's Report of MMI/Permanent Impairment",
    "C-62": "Claim for Compensation in Death Case",
    "C-64": "Proof of Death by Physician",
    "C-65": "Proof of Burial and Funeral Expenses",
    "C-257": "Claimant's Record of Medical-Travel Expenses",
    "C-258": "Claimant's Record of Job Search",
    "C-258.1": "Injured Worker's Record of Independent Job Search",
    "DEATH-CERT": "Death Certificate",
    "DEPOSITION": "Deposition",
    "EXHIBIT": "Exhibit",
    "MARR-CERT": "Marriage Certificate",
    "MED-NARR": "Medical Narrative",
    "OC-400.1": "Application for Fee",
    "CORR": "Correspondence",
    "CORR-EMB": "Correspondence (Embedded)",
    "DISC-LAW-EMB": "Discontinued Lawsuit",
    "FULL-SCHOOL-ENR-EMB": "Full Time School Enrollment",
    "PAYSTUB-EMB": "Paystub(s)",
    "PAYROLL-EMB": "Payroll Documents",
    "REL-FROM-CUST-EMB": "Released From Custody",
    "TAX-EMB": "Tax Document",
    "IME-4": "Report of Independent Medical Examination",
    "FROI-04": "First Report of Injury - Denial",
    "SROI-04": "Subsequent Report of Injury - Denial",
}


# ── Finger / Toe / Side Location Codes ──────────────────────────────────────
FINGER_CODES = {"F1": "Index", "F2": "Middle", "F3": "Ring", "F4": "Little"}
TOE_CODES = {"T1": "1st", "T2": "2nd", "T3": "3rd", "T4": "4th (Little)"}
SIDE_CODES = {"R": "Right", "L": "Left", "B": "Bilateral"}


# ── Disability Designation Codes ─────────────────────────────────────────────
DISABILITY_DESIGNATIONS = {
    "HIA": "Held In Abeyance",
    "NCLT": "No Compensable Lost Time",
    "NLT": "No Lost Time",
    "NME": "No Medical Evidence",
    "ILT": "Intermittent Lost Time",
    "PPD": "Permanent Partial Disability",
    "TPD": "Temporary Partial Disability",
    "TTD": "Temporary Total Disability",
    "RE": "Reduced Earnings",
    "TRE": "Tentative Reduced Earnings",
    "TR": "Tentative Rate",
}


# ── AWW Calculation Methods ─────────────────────────────────────────────────
AWW_METHODS = {
    "FRSR": "Per First Report of Injury/Subsequent Report",
    "P260": "Per payroll using 260 multiple",
    "P300": "Per payroll using 300 multiple",
    "P200": "Per payroll using 200 multiple",
    "S260": "Per similar worker payroll using 260 multiple",
    "S300": "Per similar worker payroll using 300 multiple",
    "S200": "Per similar worker payroll using 200 multiple",
    "OTHR": "Other",
}


# ── Legacy body-part-name-to-code lookup (maps names to WCB_BODY_PARTS keys)
_BODY_PART_NAME_TO_CODE = {v["text"].lower(): k for k, v in WCB_BODY_PARTS.items()}
# Add common aliases
_BODY_PART_NAME_TO_CODE.update({
    "cervical spine": "21",
    "thoracic spine": "41",
    "lumbar spine": "42",
    "forearm": "33",
    "finger": "36",
    "fingers": "36",
    "toe": "57",
    "toes": "57",
    "thigh": "52",
    "groin": "61",
})


def _resolve_body_part_code(bp: dict) -> str:
    """Resolve a body part dict to a WCB body part code string.

    Accepts either a direct 'code' key or a 'name' key that gets looked up.
    """
    if bp.get("code") and bp["code"] in WCB_BODY_PARTS:
        return bp["code"]
    name = bp.get("name", "").lower().strip()
    return _BODY_PART_NAME_TO_CODE.get(name, bp.get("code", "00"))


def build_wcb_xml(data: dict) -> str:
    """Build WCB-compliant XML matching eFormsRfa1lc.xsd.

    Args:
        data: {
            "client_id": str,           # OAuth2 client ID
            "sender_poi": str,          # R-number (e.g., "R999999")
            "wcb_case_id": str,         # WCB Case Number (digits only)
            "date_of_injury": str,      # "YYYY-MM-DD"
            "attestation": bool,
            "attorney_first_name": str,
            "attorney_last_name": str,
            "attorney_rnum": str,       # R-number
            "attorney_phone": str,
            "reason_codes": [{"code": "MCI", "sub_reason": "CU", ...}],
            "documents": [{"form_id": "C-4.3", "name": "...", "filename": "...", "file_type": "PDF", "provider": "...", "service_date": "...", "description": "...", "base64_data": "..."}],
            "referenced_docs": [{"document_id": "...", "form_id": "CORR"}],
            "additional_findings": {...},  # MCI-specific fields
            "narrative": str,
            "transaction_id": str,
        }
    """
    root = ET.Element("eForms")

    # ── Header ───────────────────────────────────────────────────────
    header = ET.SubElement(root, "Header")
    api_header = ET.SubElement(header, "APIHeader")
    ET.SubElement(api_header, "SubmitterClientId").text = data.get("client_id", "")
    ET.SubElement(api_header, "SenderPOI").text = data.get("sender_poi", "")
    ET.SubElement(api_header, "SubmitDate").text = date.today().isoformat()

    # ── Events ───────────────────────────────────────────────────────
    events = ET.SubElement(root, "Events")
    event_code = data.get("event_code", "RFA-1LC")
    event = ET.SubElement(events, "EventCode", code=event_code)

    # Transaction ID
    tid = data.get("transaction_id", str(uuid.uuid4().int)[:12])
    ET.SubElement(event, "TransactionSequenceNumber").text = tid

    # Case ID
    case_id = data.get("wcb_case_id", "").replace("G-", "").replace("g-", "").replace("WC", "")
    ET.SubElement(event, "WCBCaseID").text = case_id

    # Date of Injury
    doi = data.get("date_of_injury", "")
    if doi:
        doi_elem = ET.SubElement(event, "DateOfInjury")
        parts = doi.split("-")
        if len(parts) == 3:
            ET.SubElement(doi_elem, "DoiMonth").text = parts[1]
            ET.SubElement(doi_elem, "DoiDay").text = parts[2]
            ET.SubElement(doi_elem, "DoiYear").text = parts[0]

    # Attestation
    ET.SubElement(event, "AttestationConfirmationCode").text = "Y" if data.get("attestation") else "N"

    # Attorney/Licensed Rep
    if data.get("attorney_first_name"):
        ET.SubElement(event, "AttorneyLicensedRepFirstName").text = data["attorney_first_name"]
    if data.get("attorney_last_name"):
        ET.SubElement(event, "AttorneyLicensedRepLastName").text = data["attorney_last_name"]
    if data.get("attorney_rnum"):
        ET.SubElement(event, "AttorneyLicensedRepRnum").text = data["attorney_rnum"]
    if data.get("attorney_phone"):
        ET.SubElement(event, "AttorneyLicensedRepPhone").text = data["attorney_phone"].replace("-", "").replace("(", "").replace(")", "").replace(" ", "")

    # ── Reasons ──────────────────────────────────────────────────────
    reasons_elem = ET.SubElement(event, "Reasons")
    for idx, reason in enumerate(data.get("reason_codes", []), 1):
        reason_elem = ET.SubElement(reasons_elem, "Reason", index=str(idx))
        code = reason.get("code", "")
        ET.SubElement(reason_elem, "ReasonCode").text = code
        ET.SubElement(reason_elem, "ReasonCodeCategory").text = REASON_CATEGORIES.get(code, "O")

        # Reason-specific fields
        if code == "MCI":
            if reason.get("claimant_agreement"):
                ET.SubElement(reason_elem, "ClaimantAgreementWithIME").text = reason["claimant_agreement"]  # CU, CD
        elif code == "CNW":
            if reason.get("cnw_reason"):
                ET.SubElement(reason_elem, "CNWReasonCode").text = reason["cnw_reason"]
        elif code == "CAW":
            if reason.get("caw_type"):
                ET.SubElement(reason_elem, "CAWTypeCode").text = reason["caw_type"]

    # ── Supporting Documents ─────────────────────────────────────────
    if data.get("documents") or data.get("referenced_docs"):
        support_docs = ET.SubElement(event, "SupportingDocuments")

        if data.get("documents"):
            uploaded = ET.SubElement(support_docs, "UploadedDocuments")
            for idx, doc in enumerate(data["documents"], 1):
                ud = ET.SubElement(uploaded, "UploadedDocument", index=str(idx))
                ET.SubElement(ud, "UploadFormId").text = doc.get("form_id", "OTHER")
                ET.SubElement(ud, "UploadDocumentFormName").text = doc.get("name", "")
                ET.SubElement(ud, "UploadFileName").text = doc.get("filename", "")
                ET.SubElement(ud, "UploadFileType").text = doc.get("file_type", "PDF")
                if doc.get("provider"):
                    ET.SubElement(ud, "UploadHealthCareProviderName").text = doc["provider"]
                if doc.get("service_date"):
                    ET.SubElement(ud, "UploadServiceDate").text = doc["service_date"]
                if doc.get("size"):
                    ET.SubElement(ud, "UploadFileSize").text = str(doc["size"])
                if doc.get("description"):
                    ET.SubElement(ud, "UploadDocumentDescription").text = doc["description"]
                if doc.get("base64_data"):
                    ET.SubElement(ud, "UploadSupportingDocumentImage").text = doc["base64_data"]

        if data.get("referenced_docs"):
            refs = ET.SubElement(support_docs, "ReferencedDocuments")
            for idx, ref in enumerate(data["referenced_docs"], 1):
                rd = ET.SubElement(refs, "ReferencedDocument", index=str(idx))
                ET.SubElement(rd, "ReferenceDocumentId").text = ref.get("document_id", "")
                ET.SubElement(rd, "ReferenceFormId").text = ref.get("form_id", "CORR")

    # ── Additional Proposed Finding (for MCI and complex filings) ────
    findings = data.get("additional_findings", {})
    if findings:
        apf = ET.SubElement(event, "AdditionalProposedFinding")

        # Body parts
        if findings.get("ancr"):
            ET.SubElement(apf, "AdditionalProposedFindingANCR").text = "Y" if findings["ancr"] else "N"

        if findings.get("body_parts"):
            bp_container = ET.SubElement(apf, "AdditionalProposedFindingBodyParts")
            for idx, bp in enumerate(findings["body_parts"], 1):
                bp_elem = ET.SubElement(bp_container, "AdditionalProposedFindingBodyPart", index=str(idx))
                bp_code = _resolve_body_part_code(bp)
                ET.SubElement(bp_elem, "AdditionalProposedFindingBodyPartCode").text = str(bp_code)
                if bp.get("location"):
                    ET.SubElement(bp_elem, "AdditionalProposedFindingBodyPartLocationCode").text = bp["location"]  # L, R, B

        if findings.get("body_part_text"):
            ET.SubElement(apf, "AdditionalProposedFindingBodyPartAdditionalText").text = findings["body_part_text"]

        # AWW
        if findings.get("aww"):
            ET.SubElement(apf, "AdditionalProposedFindingAWW").text = "Y"
            if findings.get("aww_amount"):
                ET.SubElement(apf, "EstablishAWWPrimaryEmployerDollarAmount").text = str(findings["aww_amount"])
            if findings.get("aww_method"):
                ET.SubElement(apf, "EstablishAWWCalculationMethod").text = findings["aww_method"]

        # Lost wage benefit
        if findings.get("award_lost_wage"):
            ET.SubElement(apf, "AdditionalProposedFindingAwardLostWageBen").text = "Y"

            if findings.get("award_periods"):
                periods_elem = ET.SubElement(apf, "AdditionalProposedFindingAwardPeriods")
                for idx, period in enumerate(findings["award_periods"], 1):
                    ap = ET.SubElement(periods_elem, "ALWBAwardPeriod", index=str(idx))
                    if period.get("from_date"):
                        ET.SubElement(ap, "AwardPeriodFromDate").text = period["from_date"]
                    if period.get("to_date"):
                        ET.SubElement(ap, "AwardPeriodToDate").text = period["to_date"]
                    if period.get("text"):
                        ET.SubElement(ap, "AwardPeriodFreeText").text = period["text"]

                    if period.get("designations"):
                        desigs = ET.SubElement(ap, "AwardPeriodDesignations")
                        for didx, desig in enumerate(period["designations"], 1):
                            d = ET.SubElement(desigs, "AwardPeriodDesignation", index=str(didx))
                            ET.SubElement(d, "AwardPeriodDesignationCode").text = desig.get("code", "")
                            if desig.get("percentage"):
                                ET.SubElement(d, "AwardPeriodDisabilityPercentage").text = str(desig["percentage"])
                            if desig.get("award_indicator"):
                                ET.SubElement(d, "AwardPeriodAwardIndicator").text = desig["award_indicator"]

        # Attorney fee
        if findings.get("attorney_fee"):
            ET.SubElement(apf, "AdditionalProposedFindingAttorneyFeeReq").text = "Y"

    # ── Pretty print ─────────────────────────────────────────────────
    rough = ET.tostring(root, encoding="unicode", xml_declaration=False)
    dom = minidom.parseString(rough)
    pretty = dom.toprettyxml(indent="  ", encoding=None)
    # Remove extra XML declaration from minidom
    lines = pretty.split("\n")
    if lines and lines[0].startswith("<?xml"):
        lines[0] = '<?xml version="1.0" encoding="utf-8"?>'
    return "\n".join(lines)
