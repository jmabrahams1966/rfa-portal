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


# ── Reason Code Categories ───────────────────────────────────────────────────
REASON_CATEGORIES = {
    "CNW": "C",  # Compensation - not working / not receiving payments
    "CAW": "C",  # Compensation - AWW adjustments
    "CVW": "C",  # Compensation - volunteer
    "MBC": "M",  # Medical - body parts/conditions
    "MCI": "M",  # Medical - maximum medical improvement
    # RFA-2 codes (for future expansion)
    "CPD": "C", "CPR": "C", "CPI": "C", "CPS": "C",
    "MOW": "M", "MIA": "M",
    "OER": "O", "OIL": "O", "ORD": "O", "OID": "O",
    "OCD": "O", "OUI": "O", "OIW": "O",
}

# ── WCB Body Part Codes ──────────────────────────────────────────────────────
BODY_PART_CODES = {
    "head": "01", "skull": "02", "brain": "03", "ear": "04", "eye": "05",
    "nose": "06", "mouth": "07", "neck": "10", "cervical spine": "11",
    "upper back": "15", "thoracic spine": "16",
    "lower back": "20", "lumbar spine": "21", "sacrum": "22",
    "shoulder": "25", "upper arm": "26", "elbow": "27",
    "forearm": "28", "wrist": "30", "hand": "31", "finger": "36",
    "hip": "40", "thigh": "41", "knee": "42",
    "lower leg": "43", "ankle": "45", "foot": "46", "toe": "47",
    "chest": "50", "abdomen": "55", "pelvis": "60",
}


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
                bp_code = BODY_PART_CODES.get(bp.get("name", "").lower(), bp.get("code", ""))
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
