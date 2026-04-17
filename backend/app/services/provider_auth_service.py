"""
Provider Prior Authorization AI Service for RFA-2 Portal.

Handles AI-powered clinical data extraction, narrative generation,
payer optimization, denial analysis, appeal generation, peer-to-peer
preparation, outcome tracking, and analytics.

Uses Claude via AWS Bedrock for all AI operations.
"""

import json
import logging
import uuid
from datetime import datetime, date
from typing import Any, Optional

import boto3
from botocore.config import Config as BotoConfig
from sqlalchemy import select, and_, func, update, case as sql_case
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.provider_auth import (
    AuthRequest,
    AuthDocument,
    AuthLearning,
    PayerAuthProfile,
)
from app.services.phi_service import deidentify

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Bedrock client helper (mirrors narrative_service pattern)
# ---------------------------------------------------------------------------
def _get_bedrock_client():
    """Create a Bedrock Runtime client."""
    settings = get_settings()
    kwargs: dict[str, Any] = {
        "region_name": settings.bedrock_region,
        "config": BotoConfig(
            retries={"max_attempts": 3, "mode": "adaptive"},
            read_timeout=180,
        ),
    }
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    return boto3.client("bedrock-runtime", **kwargs)


def _invoke_claude(system: str, user_message: str, max_tokens: int = 8192) -> str:
    """Send a message to Claude via Bedrock and return the assistant text."""
    settings = get_settings()
    client = _get_bedrock_client()

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": 0.2,
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

    # Strip markdown fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    return text.strip()


def _parse_json_response(text: str) -> dict:
    """Parse a JSON response from Claude, handling edge cases."""
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON in the response
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

    logger.error("Failed to parse Claude JSON response: %s", text[:500])
    return {}


# ---------------------------------------------------------------------------
# Extraction prompts per document type
# ---------------------------------------------------------------------------
_EXTRACTION_PROMPTS: dict[str, str] = {
    "clinical_note": (
        "Extract the following from this clinical note:\n"
        "- diagnosis: primary diagnosis\n"
        "- symptoms: list of symptoms with duration and severity\n"
        "- symptom_duration: how long symptoms have been present\n"
        "- physical_exam_findings: relevant exam findings\n"
        "- treatment_history: list of prior treatments with dates and outcomes\n"
        "- medications: current medications related to this condition\n"
        "- functional_limitations: ADL/work limitations documented\n"
        "- work_status: current work status\n"
        "Return JSON with these keys."
    ),
    "mri_report": (
        "Extract the following from this MRI report:\n"
        "- findings: overall findings summary\n"
        "- levels_affected: list of spinal levels or joints affected\n"
        "- stenosis_grade: central/foraminal stenosis severity per level\n"
        "- herniation_type: disc herniation type and location per level\n"
        "- cord_compression: presence/absence and severity\n"
        "- nerve_root_compression: specific nerve roots affected\n"
        "- ligamentum_flavum: hypertrophy noted\n"
        "- facet_arthropathy: severity per level\n"
        "- impression: radiologist impression\n"
        "Return JSON with these keys."
    ),
    "ct_report": (
        "Extract the following from this CT report:\n"
        "- findings: overall findings summary\n"
        "- levels_affected: list of levels or regions affected\n"
        "- bony_abnormalities: fractures, osteophytes, hardware\n"
        "- stenosis: canal or foraminal narrowing\n"
        "- impression: radiologist impression\n"
        "Return JSON with these keys."
    ),
    "xray_report": (
        "Extract the following from this X-ray report:\n"
        "- findings: overall findings\n"
        "- alignment: spinal alignment or joint alignment\n"
        "- instability: evidence of instability\n"
        "- degenerative_changes: disc space narrowing, osteophytes\n"
        "- impression: radiologist impression\n"
        "Return JSON with these keys."
    ),
    "pt_records": (
        "Extract the following from these physical therapy records:\n"
        "- sessions_completed: total number of sessions\n"
        "- date_range: start and end dates of therapy\n"
        "- exercises: types of exercises performed\n"
        "- progress: documented progress or lack thereof\n"
        "- functional_improvements: any improvements noted\n"
        "- functional_declines: any worsening noted\n"
        "- therapist_recommendation: discharge recommendation or continued need\n"
        "- outcome_measures: any standardized measures used\n"
        "Return JSON with these keys."
    ),
    "injection_records": (
        "Extract the following from these injection records:\n"
        "- injections: list of injections, each with:\n"
        "  - type: epidural (interlaminar/transforaminal), facet, trigger point, etc.\n"
        "  - levels: spinal levels or anatomic location\n"
        "  - date: date performed\n"
        "  - response: pain relief duration and percentage improvement\n"
        "  - complications: any noted\n"
        "- total_injections: count\n"
        "- overall_response: summary of response pattern\n"
        "Return JSON with these keys."
    ),
    "emg_report": (
        "Extract the following from this EMG/NCS report:\n"
        "- nerve_conduction_findings: NCS results\n"
        "- needle_emg_findings: needle EMG results by muscle\n"
        "- radiculopathy_level: level(s) of radiculopathy\n"
        "- severity: mild, moderate, severe\n"
        "- chronicity: acute, subacute, chronic\n"
        "- neuropathy: any peripheral neuropathy findings\n"
        "- impression: electrophysiologist impression\n"
        "Return JSON with these keys."
    ),
    "prom_scores": (
        "Extract the following patient-reported outcome scores:\n"
        "- odi_score: Oswestry Disability Index score and interpretation\n"
        "- ndi_score: Neck Disability Index score and interpretation\n"
        "- vas_score: Visual Analog Scale pain score (0-10)\n"
        "- sf36_scores: SF-36 component scores if present\n"
        "- dash_score: DASH score if present\n"
        "- phq9_score: PHQ-9 depression score if present\n"
        "- interpretation: clinical significance of scores\n"
        "Return JSON with these keys. Use null for scores not present."
    ),
    "medication_history": (
        "Extract the following from this medication history:\n"
        "- current_medications: list with name, dose, frequency, duration\n"
        "- prior_medications: list of previously tried medications with duration and reason for discontinuation\n"
        "- pain_medications: subset of current pain-related medications\n"
        "- nsaid_trials: specific NSAIDs tried with duration\n"
        "- opioid_use: current or prior opioid use\n"
        "- muscle_relaxant_trials: specific muscle relaxants tried\n"
        "- neuropathic_agents: gabapentin, pregabalin, duloxetine trials\n"
        "Return JSON with these keys."
    ),
    "operative_report": (
        "Extract the following from this operative report:\n"
        "- procedure_performed: procedure name and CPT codes\n"
        "- date_of_surgery: date performed\n"
        "- surgeon: surgeon name\n"
        "- indication: surgical indication\n"
        "- levels: spinal levels or anatomic location\n"
        "- approach: surgical approach\n"
        "- findings: intraoperative findings\n"
        "- implants: hardware/implants used\n"
        "- complications: any intraoperative complications\n"
        "- estimated_blood_loss: EBL\n"
        "Return JSON with these keys."
    ),
    "c4_form": (
        "Extract the following from this C-4 form:\n"
        "- claimant_name: injured worker name\n"
        "- wcb_case_number: WCB case number\n"
        "- date_of_injury: date of injury\n"
        "- diagnosis: diagnosis listed\n"
        "- treatment_requested: treatment being requested\n"
        "- treatment_dates: dates of treatment\n"
        "- provider: treating provider\n"
        "Return JSON with these keys."
    ),
    "ime_report": (
        "Extract the following from this IME report:\n"
        "- examiner: IME examiner name and specialty\n"
        "- exam_date: date of examination\n"
        "- history_summary: history as documented by examiner\n"
        "- exam_findings: physical examination findings\n"
        "- diagnosis: examiner's diagnosis\n"
        "- causation_opinion: opinion on causal relationship\n"
        "- treatment_recommendations: recommended treatment\n"
        "- surgery_opinion: opinion on surgical necessity\n"
        "- mmi_opinion: maximum medical improvement opinion\n"
        "- disability_opinion: disability rating opinion\n"
        "Return JSON with these keys."
    ),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def extract_clinical_data(clean_text: str, doc_type: str) -> dict:
    """
    Send de-identified document text to Claude Bedrock and extract structured
    clinical data based on the document type.

    Args:
        clean_text: De-identified document text (already run through PHI service).
        doc_type: One of the supported document types.

    Returns:
        Structured dict of extracted clinical data.
    """
    if not clean_text or not clean_text.strip():
        return {"error": "Empty document text", "extracted": False}

    extraction_prompt = _EXTRACTION_PROMPTS.get(doc_type)
    if not extraction_prompt:
        # Generic extraction for unknown types
        extraction_prompt = (
            "Extract all clinically relevant information from this document. "
            "Include: diagnoses, findings, treatments, dates, recommendations. "
            "Return JSON with descriptive keys."
        )

    system_prompt = (
        "You are a medical data extraction specialist for neurosurgery prior authorization. "
        "Extract structured clinical data from the provided document text. "
        "The text has been de-identified — do not attempt to re-identify any patients. "
        "Be thorough and precise. Include exact dates, measurements, and scores when present. "
        "Respond ONLY with valid JSON. Do not include any text outside the JSON object."
    )

    user_message = f"DOCUMENT TYPE: {doc_type}\n\n{extraction_prompt}\n\nDOCUMENT TEXT:\n{clean_text}"

    try:
        response_text = _invoke_claude(system_prompt, user_message, max_tokens=4096)
        extracted = _parse_json_response(response_text)
        if not extracted:
            return {"error": "Failed to parse extraction response", "extracted": False}
        extracted["extracted"] = True
        extracted["doc_type"] = doc_type
        return extracted
    except Exception as e:
        logger.exception("Clinical data extraction failed for doc_type=%s", doc_type)
        return {"error": str(e), "extracted": False}


async def generate_auth_narrative(
    auth_request_id: str,
    db: AsyncSession,
) -> dict:
    """
    Generate a compelling medical necessity narrative for a prior authorization.

    Pulls all uploaded documents and extracted data, the payer profile, and
    winning narratives from AuthLearning, then generates a structured narrative.

    Returns:
        {narrative, confidence, version, missing_elements}
    """
    # Fetch the auth request
    q = select(AuthRequest).where(AuthRequest.id == auth_request_id)
    result = await db.execute(q)
    auth_req = result.scalar_one_or_none()
    if not auth_req:
        return {"error": f"Auth request {auth_request_id} not found"}

    # Fetch all documents with extracted data
    doc_q = (
        select(AuthDocument)
        .where(AuthDocument.auth_request_id == auth_request_id)
        .order_by(AuthDocument.created_at)
    )
    doc_result = await db.execute(doc_q)
    documents = doc_result.scalars().all()

    # Build document summaries
    doc_summaries: list[str] = []
    extracted_data_all: list[dict] = []
    doc_types_present: set[str] = set()

    for doc in documents:
        doc_types_present.add(doc.doc_type)
        if doc.extracted_data:
            extracted_data_all.append({
                "doc_type": doc.doc_type,
                "file_name": doc.file_name,
                "data": doc.extracted_data,
            })
            doc_summaries.append(
                f"[{doc.doc_type}] {doc.file_name}:\n"
                f"{json.dumps(doc.extracted_data, indent=2, default=str)}"
            )
        elif doc.clean_text:
            doc_summaries.append(
                f"[{doc.doc_type}] {doc.file_name}:\n{doc.clean_text[:3000]}"
            )

    # Fetch payer profile
    payer_profile = None
    payer_q = (
        select(PayerAuthProfile)
        .where(
            and_(
                PayerAuthProfile.org_id == auth_req.org_id,
                PayerAuthProfile.payer_name == auth_req.payer_name,
            )
        )
    )
    payer_result = await db.execute(payer_q)
    payer_profile = payer_result.scalar_one_or_none()

    # Fetch winning narratives from AuthLearning
    # Derive a procedure category from the proposed procedure
    procedure_cat = _derive_procedure_category(auth_req.proposed_procedure)

    learning_q = (
        select(AuthLearning.narrative_text, AuthLearning.approval_factors)
        .where(
            and_(
                AuthLearning.payer_name == auth_req.payer_name,
                AuthLearning.procedure_category == procedure_cat,
                AuthLearning.outcome == "approved",
            )
        )
        .order_by(AuthLearning.created_at.desc())
        .limit(5)
    )
    learning_result = await db.execute(learning_q)
    winning_rows = learning_result.all()

    # Identify missing elements
    missing_elements: list[str] = []
    required_doc_types = {"clinical_note", "mri_report"}
    recommended_doc_types = {"pt_records", "injection_records", "prom_scores"}

    for req_type in required_doc_types:
        if req_type not in doc_types_present:
            missing_elements.append(f"Missing required document: {req_type}")
    for rec_type in recommended_doc_types:
        if rec_type not in doc_types_present:
            missing_elements.append(f"Recommended document not uploaded: {rec_type}")

    # Check payer-specific required documents
    if payer_profile and payer_profile.required_documents:
        for req_doc in payer_profile.required_documents:
            if isinstance(req_doc, str) and req_doc not in doc_types_present:
                missing_elements.append(f"Payer requires: {req_doc}")

    # Build the prompt
    system_prompt = (
        "You are a neurosurgery prior authorization specialist. Generate a compelling "
        "medical necessity narrative for surgical authorization. Structure the narrative as:\n\n"
        "1. CLINICAL HISTORY: Patient demographics, onset of symptoms, duration, severity, "
        "impact on daily function and work\n"
        "2. CONSERVATIVE TREATMENT HISTORY: List ALL failed conservative measures with dates, "
        "duration, and outcomes (PT sessions, medications with duration, injections with response, "
        "bracing, activity modification)\n"
        "3. DIAGNOSTIC FINDINGS: MRI/CT/X-ray findings that correlate with clinical symptoms. "
        "EMG if applicable.\n"
        "4. FUNCTIONAL ASSESSMENT: ODI/NDI/VAS scores, work status, ADL limitations\n"
        "5. MEDICAL NECESSITY: Why surgery is needed NOW, why continued conservative care is not "
        "appropriate, expected outcomes\n"
        "6. PROPOSED PROCEDURE: Specific procedure with CPT codes, surgical approach, levels\n\n"
        "Reference clinical guidelines (NASS, AMA, AAOS) when applicable. Use the payer's "
        "preferred documentation language based on prior approved narratives.\n\n"
        "Respond ONLY with valid JSON:\n"
        '{"narrative": "...", "confidence": "HIGH|MEDIUM|LOW"}'
    )

    # Assemble user message
    user_parts: list[str] = []

    user_parts.append(f"PATIENT: {auth_req.patient_name}")
    user_parts.append(f"DOB: {auth_req.patient_dob}")
    if auth_req.date_of_injury:
        user_parts.append(f"DATE OF INJURY: {auth_req.date_of_injury}")
    user_parts.append(f"PRIMARY DIAGNOSIS: {auth_req.diagnosis_primary}")
    user_parts.append(f"ICD-10 CODES: {auth_req.diagnosis_codes}")
    user_parts.append(f"PROPOSED PROCEDURE: {auth_req.proposed_procedure}")
    user_parts.append(f"CPT CODES: {auth_req.proposed_cpt_codes}")
    user_parts.append(f"SURGEON: {auth_req.surgeon_name} (NPI: {auth_req.surgeon_npi})")
    user_parts.append(f"PAYER: {auth_req.payer_name} ({auth_req.insurance_type})")
    user_parts.append(f"URGENCY: {auth_req.clinical_urgency or 'routine'}")

    if auth_req.conservative_treatment_summary:
        user_parts.append(f"\nCONSERVATIVE TREATMENT SUMMARY:\n{auth_req.conservative_treatment_summary}")
    if auth_req.imaging_summary:
        user_parts.append(f"\nIMAGING SUMMARY:\n{auth_req.imaging_summary}")
    if auth_req.functional_scores:
        user_parts.append(f"\nFUNCTIONAL SCORES:\n{auth_req.functional_scores}")

    if doc_summaries:
        user_parts.append("\n--- UPLOADED DOCUMENTS ---")
        for ds in doc_summaries:
            user_parts.append(ds)

    # Include payer preferences
    if payer_profile:
        user_parts.append(f"\n--- PAYER INTELLIGENCE ---")
        user_parts.append(f"Approval rate: {payer_profile.approval_rate or 'unknown'}")
        if payer_profile.preferred_narrative_style:
            user_parts.append(f"Preferred style: {payer_profile.preferred_narrative_style}")
        if payer_profile.tips:
            user_parts.append(f"Tips: {payer_profile.tips}")
        if payer_profile.common_denial_reasons:
            user_parts.append(
                f"Common denials: {json.dumps(payer_profile.common_denial_reasons, default=str)}"
            )

    # Include winning narratives
    if winning_rows:
        user_parts.append(f"\n--- PREVIOUSLY APPROVED NARRATIVES ({len(winning_rows)}) ---")
        for i, row in enumerate(winning_rows, 1):
            user_parts.append(f"\nApproved narrative {i}:\n{row.narrative_text[:2000] if row.narrative_text else 'N/A'}")
            if row.approval_factors:
                user_parts.append(f"Success factors: {json.dumps(row.approval_factors, default=str)}")

    if missing_elements:
        user_parts.append(f"\nNOTE — MISSING ELEMENTS: {', '.join(missing_elements)}")

    user_message = "\n".join(user_parts)

    try:
        response_text = _invoke_claude(system_prompt, user_message, max_tokens=8192)
        parsed = _parse_json_response(response_text)

        narrative = parsed.get("narrative", response_text)
        confidence = parsed.get("confidence", "MEDIUM")

        # Update the auth request
        new_version = auth_req.narrative_version + 1
        auth_req.narrative = narrative
        auth_req.narrative_version = new_version
        if auth_req.status == "documents_uploaded":
            auth_req.status = "narrative_generated"
        await db.flush()

        return {
            "narrative": narrative,
            "confidence": confidence,
            "version": new_version,
            "missing_elements": missing_elements,
        }

    except Exception as e:
        logger.exception("Narrative generation failed for auth_request=%s", auth_request_id)
        return {
            "error": str(e),
            "narrative": None,
            "confidence": "LOW",
            "version": auth_req.narrative_version,
            "missing_elements": missing_elements,
        }


async def optimize_for_payer(
    narrative: str,
    payer_name: str,
    insurance_type: str,
    procedure: str,
    db: AsyncSession,
) -> dict:
    """
    Optimize a prior auth narrative for a specific payer based on historical
    approval patterns.

    Returns:
        {optimized_narrative, changes_made}
    """
    # Pull payer profile
    payer_q = (
        select(PayerAuthProfile)
        .where(PayerAuthProfile.payer_name == payer_name)
        .limit(1)
    )
    payer_result = await db.execute(payer_q)
    payer_profile = payer_result.scalar_one_or_none()

    # Pull winning narratives for this payer + procedure
    procedure_cat = _derive_procedure_category(procedure)
    learning_q = (
        select(AuthLearning.narrative_text, AuthLearning.approval_factors)
        .where(
            and_(
                AuthLearning.payer_name == payer_name,
                AuthLearning.procedure_category == procedure_cat,
                AuthLearning.outcome == "approved",
            )
        )
        .order_by(AuthLearning.created_at.desc())
        .limit(5)
    )
    learning_result = await db.execute(learning_q)
    winning_rows = learning_result.all()

    # Build prompt
    payer_context_parts: list[str] = []
    if payer_profile:
        payer_context_parts.append(f"Approval rate: {payer_profile.approval_rate or 'unknown'}")
        payer_context_parts.append(f"Total auths: {payer_profile.total_auths}")
        if payer_profile.preferred_narrative_style:
            payer_context_parts.append(f"Preferred style: {payer_profile.preferred_narrative_style}")
        if payer_profile.common_denial_reasons:
            payer_context_parts.append(
                f"Common denials: {json.dumps(payer_profile.common_denial_reasons, default=str)}"
            )
        if payer_profile.required_documents:
            payer_context_parts.append(
                f"Required documents: {json.dumps(payer_profile.required_documents, default=str)}"
            )
        if payer_profile.tips:
            payer_context_parts.append(f"Tips: {payer_profile.tips}")

    winning_patterns_parts: list[str] = []
    if winning_rows:
        for i, row in enumerate(winning_rows, 1):
            if row.narrative_text:
                winning_patterns_parts.append(f"Approved #{i}:\n{row.narrative_text[:2000]}")
            if row.approval_factors:
                winning_patterns_parts.append(
                    f"Success factors: {json.dumps(row.approval_factors, default=str)}"
                )

    n_previous = payer_profile.total_auths if payer_profile else 0
    payer_context = "\n".join(payer_context_parts) if payer_context_parts else "No prior data available."
    winning_text = "\n\n".join(winning_patterns_parts) if winning_patterns_parts else "No winning narratives available."

    system_prompt = (
        "You are a prior authorization optimization specialist. "
        "Optimize the provided narrative for the specific payer. "
        "Adjust language, structure, and emphasis to match patterns that have been approved. "
        "The result must not exceed 3 pages (approximately 4500 words). "
        "Respond ONLY with valid JSON:\n"
        '{"optimized_narrative": "...", "changes_made": ["list of specific changes"]}'
    )

    user_message = (
        f"Optimize this prior auth narrative for {payer_name} ({insurance_type}).\n\n"
        f"Based on {n_previous} previous submissions, narratives that were approved "
        f"for {procedure} with this payer typically include the following patterns:\n\n"
        f"PAYER INTELLIGENCE:\n{payer_context}\n\n"
        f"PREVIOUSLY APPROVED NARRATIVES:\n{winning_text}\n\n"
        f"CURRENT NARRATIVE TO OPTIMIZE:\n{narrative}\n\n"
        "Adjust language, structure, and emphasis accordingly. Max 3 pages."
    )

    try:
        response_text = _invoke_claude(system_prompt, user_message, max_tokens=8192)
        parsed = _parse_json_response(response_text)

        return {
            "optimized_narrative": parsed.get("optimized_narrative", narrative),
            "changes_made": parsed.get("changes_made", []),
        }
    except Exception as e:
        logger.exception("Payer optimization failed for payer=%s", payer_name)
        return {
            "optimized_narrative": narrative,
            "changes_made": [],
            "error": str(e),
        }


async def analyze_denial(
    auth_request_id: str,
    denial_text: str,
    db: AsyncSession,
) -> dict:
    """
    Analyze a denial, identify gaps, and generate appeal materials.

    Returns:
        {analysis, missing_elements, appeal_letter, peer_to_peer_recommended,
         peer_to_peer_talking_points}
    """
    # Fetch auth request and documents
    q = select(AuthRequest).where(AuthRequest.id == auth_request_id)
    result = await db.execute(q)
    auth_req = result.scalar_one_or_none()
    if not auth_req:
        return {"error": f"Auth request {auth_request_id} not found"}

    # Fetch documents list
    doc_q = (
        select(AuthDocument.doc_type, AuthDocument.file_name)
        .where(AuthDocument.auth_request_id == auth_request_id)
    )
    doc_result = await db.execute(doc_q)
    doc_list = [
        f"{row.doc_type}: {row.file_name}" for row in doc_result.all()
    ]

    # Update the auth request with denial info
    auth_req.denial_reason = denial_text
    auth_req.denial_date = date.today()
    auth_req.status = "denied"
    await db.flush()

    system_prompt = (
        "You are a neurosurgery prior authorization appeals specialist. "
        "Analyze why a prior authorization was denied and provide comprehensive "
        "appeal materials. Be specific and actionable. "
        "Respond ONLY with valid JSON:\n"
        "{\n"
        '  "analysis": "detailed analysis of why denial occurred",\n'
        '  "missing_elements": ["specific gaps identified"],\n'
        '  "appeal_letter": "formal appeal letter text",\n'
        '  "peer_to_peer_recommended": true/false,\n'
        '  "peer_to_peer_talking_points": ["key talking points for call"]\n'
        "}"
    )

    user_message = (
        f"This prior authorization was denied.\n\n"
        f"DENIAL REASON: {denial_text}\n\n"
        f"ORIGINAL NARRATIVE:\n{auth_req.narrative or 'No narrative on file'}\n\n"
        f"PROCEDURE: {auth_req.proposed_procedure} (CPT: {auth_req.proposed_cpt_codes})\n"
        f"DIAGNOSIS: {auth_req.diagnosis_primary} (ICD-10: {auth_req.diagnosis_codes})\n"
        f"PAYER: {auth_req.payer_name} ({auth_req.insurance_type})\n"
        f"SURGEON: {auth_req.surgeon_name}\n\n"
        f"DOCUMENTS ON FILE:\n" + "\n".join(f"- {d}" for d in doc_list) + "\n\n"
        "Identify:\n"
        "1) What was missing from the original narrative\n"
        "2) What should be added for the appeal\n"
        "3) Whether peer-to-peer review is recommended\n"
        "4) Draft talking points for peer-to-peer if recommended\n"
        "5) Draft a formal appeal letter citing clinical guidelines"
    )

    try:
        response_text = _invoke_claude(system_prompt, user_message, max_tokens=8192)
        parsed = _parse_json_response(response_text)

        return {
            "analysis": parsed.get("analysis", "Unable to analyze denial"),
            "missing_elements": parsed.get("missing_elements", []),
            "appeal_letter": parsed.get("appeal_letter", ""),
            "peer_to_peer_recommended": parsed.get("peer_to_peer_recommended", False),
            "peer_to_peer_talking_points": parsed.get("peer_to_peer_talking_points", []),
        }
    except Exception as e:
        logger.exception("Denial analysis failed for auth_request=%s", auth_request_id)
        return {
            "analysis": f"Analysis failed: {e}",
            "missing_elements": [],
            "appeal_letter": "",
            "peer_to_peer_recommended": True,
            "peer_to_peer_talking_points": ["Request peer-to-peer to discuss clinical details"],
            "error": str(e),
        }


async def generate_appeal(
    auth_request_id: str,
    db: AsyncSession,
) -> dict:
    """
    Generate a formal appeal letter for a denied prior authorization.

    Returns:
        {appeal_letter, supporting_citations}
    """
    # Fetch auth request
    q = select(AuthRequest).where(AuthRequest.id == auth_request_id)
    result = await db.execute(q)
    auth_req = result.scalar_one_or_none()
    if not auth_req:
        return {"error": f"Auth request {auth_request_id} not found"}

    # Fetch documents with extracted data
    doc_q = (
        select(AuthDocument)
        .where(AuthDocument.auth_request_id == auth_request_id)
    )
    doc_result = await db.execute(doc_q)
    documents = doc_result.scalars().all()

    # Build extracted data summary
    extracted_summaries: list[str] = []
    for doc in documents:
        if doc.extracted_data:
            extracted_summaries.append(
                f"[{doc.doc_type}]: {json.dumps(doc.extracted_data, indent=2, default=str)}"
            )

    # Fetch winning appeal patterns
    procedure_cat = _derive_procedure_category(auth_req.proposed_procedure)
    appeal_learning_q = (
        select(AuthLearning.narrative_text, AuthLearning.approval_factors)
        .where(
            and_(
                AuthLearning.payer_name == auth_req.payer_name,
                AuthLearning.procedure_category == procedure_cat,
                AuthLearning.outcome.in_(["approved", "appeal_approved"]),
            )
        )
        .order_by(AuthLearning.created_at.desc())
        .limit(3)
    )
    appeal_result = await db.execute(appeal_learning_q)
    winning_appeals = appeal_result.all()

    winning_text = ""
    if winning_appeals:
        parts = []
        for i, row in enumerate(winning_appeals, 1):
            if row.narrative_text:
                parts.append(f"Successful appeal #{i}:\n{row.narrative_text[:2000]}")
        winning_text = "\n\n".join(parts)

    system_prompt = (
        "You are a neurosurgery prior authorization appeals specialist. "
        "Draft a formal, compelling appeal letter for a denied surgical authorization. "
        "The letter should:\n"
        "- Address the specific denial reason point by point\n"
        "- Cite relevant clinical guidelines (NASS, AMA, AAOS, ACR Appropriateness Criteria)\n"
        "- Reference the patient's specific clinical findings and failed conservative treatment\n"
        "- Include medical literature citations that support the procedure\n"
        "- Be professionally formatted for submission to the payer's medical director\n\n"
        "Respond ONLY with valid JSON:\n"
        '{"appeal_letter": "...", "supporting_citations": ["citation 1", "citation 2", ...]}'
    )

    user_message = (
        f"DENIAL REASON: {auth_req.denial_reason or 'Not specified'}\n\n"
        f"ORIGINAL NARRATIVE:\n{auth_req.narrative or 'No narrative on file'}\n\n"
        f"PATIENT DOB: {auth_req.patient_dob}\n"
        f"DIAGNOSIS: {auth_req.diagnosis_primary} (ICD-10: {auth_req.diagnosis_codes})\n"
        f"PROCEDURE: {auth_req.proposed_procedure} (CPT: {auth_req.proposed_cpt_codes})\n"
        f"SURGEON: {auth_req.surgeon_name} (NPI: {auth_req.surgeon_npi})\n"
        f"PAYER: {auth_req.payer_name} ({auth_req.insurance_type})\n\n"
        f"CLINICAL DATA FROM DOCUMENTS:\n" + "\n".join(extracted_summaries) + "\n\n"
    )

    if auth_req.conservative_treatment_summary:
        user_message += f"CONSERVATIVE TREATMENT:\n{auth_req.conservative_treatment_summary}\n\n"
    if auth_req.imaging_summary:
        user_message += f"IMAGING:\n{auth_req.imaging_summary}\n\n"
    if auth_req.functional_scores:
        user_message += f"FUNCTIONAL SCORES:\n{auth_req.functional_scores}\n\n"
    if winning_text:
        user_message += f"PREVIOUSLY SUCCESSFUL APPEALS:\n{winning_text}\n\n"

    user_message += "Draft the formal appeal letter with clinical guideline citations."

    try:
        response_text = _invoke_claude(system_prompt, user_message, max_tokens=8192)
        parsed = _parse_json_response(response_text)

        appeal_letter = parsed.get("appeal_letter", response_text)
        citations = parsed.get("supporting_citations", [])

        # Store the appeal letter on the auth request
        auth_req.appeal_letter = appeal_letter
        auth_req.appeal_date = date.today()
        auth_req.status = "appealed"
        await db.flush()

        return {
            "appeal_letter": appeal_letter,
            "supporting_citations": citations,
        }
    except Exception as e:
        logger.exception("Appeal generation failed for auth_request=%s", auth_request_id)
        return {
            "appeal_letter": "",
            "supporting_citations": [],
            "error": str(e),
        }


async def prepare_peer_to_peer(
    auth_request_id: str,
    db: AsyncSession,
) -> dict:
    """
    Generate talking points and preparation materials for a peer-to-peer
    phone call between the surgeon and the payer's medical director.

    Returns:
        {talking_points, key_studies, expected_objections, responses}
    """
    # Fetch auth request
    q = select(AuthRequest).where(AuthRequest.id == auth_request_id)
    result = await db.execute(q)
    auth_req = result.scalar_one_or_none()
    if not auth_req:
        return {"error": f"Auth request {auth_request_id} not found"}

    # Fetch extracted data from documents
    doc_q = (
        select(AuthDocument)
        .where(AuthDocument.auth_request_id == auth_request_id)
    )
    doc_result = await db.execute(doc_q)
    documents = doc_result.scalars().all()

    extracted_data_text: list[str] = []
    for doc in documents:
        if doc.extracted_data:
            extracted_data_text.append(
                f"[{doc.doc_type}]: {json.dumps(doc.extracted_data, indent=2, default=str)}"
            )

    system_prompt = (
        "You are preparing a neurosurgeon for a peer-to-peer phone call with a payer's "
        "medical director regarding a denied prior authorization. Generate:\n"
        "1. Key talking points the surgeon should make\n"
        "2. Relevant medical literature and clinical guidelines to cite\n"
        "3. Expected objections the medical director may raise\n"
        "4. Concise, evidence-based responses to each objection\n\n"
        "Be specific to the procedure and diagnosis. The surgeon needs actionable, "
        "concise points they can reference during the call.\n\n"
        "Respond ONLY with valid JSON:\n"
        "{\n"
        '  "talking_points": ["point 1", "point 2", ...],\n'
        '  "key_studies": ["study/guideline 1", ...],\n'
        '  "expected_objections": ["objection 1", ...],\n'
        '  "responses": ["response to objection 1", ...]\n'
        "}"
    )

    user_message = (
        f"DENIAL REASON: {auth_req.denial_reason or 'Not specified'}\n\n"
        f"DIAGNOSIS: {auth_req.diagnosis_primary} (ICD-10: {auth_req.diagnosis_codes})\n"
        f"PROCEDURE: {auth_req.proposed_procedure} (CPT: {auth_req.proposed_cpt_codes})\n"
        f"PAYER: {auth_req.payer_name} ({auth_req.insurance_type})\n\n"
        f"ORIGINAL NARRATIVE:\n{auth_req.narrative or 'No narrative'}\n\n"
        f"CLINICAL DATA:\n" + "\n".join(extracted_data_text) + "\n\n"
    )

    if auth_req.conservative_treatment_summary:
        user_message += f"CONSERVATIVE TREATMENT:\n{auth_req.conservative_treatment_summary}\n\n"
    if auth_req.imaging_summary:
        user_message += f"IMAGING:\n{auth_req.imaging_summary}\n\n"
    if auth_req.functional_scores:
        user_message += f"FUNCTIONAL SCORES:\n{auth_req.functional_scores}\n\n"

    user_message += (
        "Generate peer-to-peer preparation materials for the surgeon. "
        "Be concise and evidence-based."
    )

    try:
        response_text = _invoke_claude(system_prompt, user_message, max_tokens=4096)
        parsed = _parse_json_response(response_text)

        # Update auth request status
        auth_req.status = "peer_to_peer_scheduled"
        auth_req.peer_to_peer_date = date.today()
        await db.flush()

        return {
            "talking_points": parsed.get("talking_points", []),
            "key_studies": parsed.get("key_studies", []),
            "expected_objections": parsed.get("expected_objections", []),
            "responses": parsed.get("responses", []),
        }
    except Exception as e:
        logger.exception("Peer-to-peer prep failed for auth_request=%s", auth_request_id)
        return {
            "talking_points": [],
            "key_studies": [],
            "expected_objections": [],
            "responses": [],
            "error": str(e),
        }


async def record_outcome(
    auth_request_id: str,
    outcome: str,
    notes: str,
    db: AsyncSession,
) -> dict:
    """
    Record the final outcome (approved or denied) for an auth request.
    Updates AuthLearning and PayerAuthProfile with the result.

    Args:
        auth_request_id: UUID string of the auth request.
        outcome: "approved" or "denied".
        notes: Additional notes about the outcome.

    Returns:
        {recorded, learning_id}
    """
    # Fetch auth request
    q = select(AuthRequest).where(AuthRequest.id == auth_request_id)
    result = await db.execute(q)
    auth_req = result.scalar_one_or_none()
    if not auth_req:
        return {"error": f"Auth request {auth_request_id} not found"}

    # Update auth request status
    if outcome == "approved":
        auth_req.status = "approved"
        auth_req.approved_date = date.today()
    elif outcome == "denied":
        auth_req.status = "denied"
        auth_req.denial_date = date.today()
        if notes:
            auth_req.denial_reason = notes
    elif outcome == "appeal_approved":
        auth_req.status = "appeal_approved"
        auth_req.approved_date = date.today()
        auth_req.appeal_outcome = "approved"
    elif outcome == "appeal_denied":
        auth_req.status = "appeal_denied"
        auth_req.appeal_outcome = "denied"

    # Derive procedure category
    procedure_cat = _derive_procedure_category(auth_req.proposed_procedure)
    diagnosis_cat = _derive_diagnosis_category(auth_req.diagnosis_primary)

    # Analyze what made this succeed or fail using Claude
    factors = await _analyze_outcome_factors(auth_req, outcome, notes)

    # Create AuthLearning record
    learning = AuthLearning(
        org_id=auth_req.org_id,
        auth_request_id=auth_req.id,
        payer_name=auth_req.payer_name,
        insurance_type=auth_req.insurance_type,
        procedure_category=procedure_cat,
        diagnosis_category=diagnosis_cat,
        narrative_text=auth_req.narrative,
        outcome=outcome,
        denial_reason=auth_req.denial_reason if outcome in ("denied", "appeal_denied") else None,
        approval_factors=factors.get("approval_factors") if outcome in ("approved", "appeal_approved") else None,
        denial_factors=factors.get("denial_factors") if outcome in ("denied", "appeal_denied") else None,
        learning_notes=factors.get("learning_notes", ""),
    )
    db.add(learning)
    await db.flush()

    # Update PayerAuthProfile
    await _update_payer_profile(auth_req, outcome, db)

    return {
        "recorded": True,
        "learning_id": str(learning.id),
    }


async def get_auth_analytics(
    org_id: str,
    db: AsyncSession,
) -> dict:
    """
    Comprehensive prior authorization analytics for an organization.

    Returns approval rates by payer, procedure, and surgeon; average days to
    decision; common denial reasons; and narrative effectiveness analysis.
    """
    org_uuid = org_id if isinstance(org_id, uuid.UUID) else uuid.UUID(org_id)

    # --- Approval rate by payer ---
    payer_q = (
        select(
            AuthRequest.payer_name,
            func.count(AuthRequest.id).label("total"),
            func.count(
                sql_case(
                    (AuthRequest.status.in_(["approved", "appeal_approved"]), AuthRequest.id),
                )
            ).label("approved"),
            func.count(
                sql_case(
                    (AuthRequest.status.in_(["denied", "appeal_denied"]), AuthRequest.id),
                )
            ).label("denied"),
        )
        .where(
            and_(
                AuthRequest.org_id == org_uuid,
                AuthRequest.status.in_(["approved", "denied", "appeal_approved", "appeal_denied"]),
            )
        )
        .group_by(AuthRequest.payer_name)
    )
    payer_result = await db.execute(payer_q)
    by_payer = []
    for row in payer_result.all():
        total = row.total or 0
        approved = row.approved or 0
        by_payer.append({
            "payer_name": row.payer_name,
            "total": total,
            "approved": approved,
            "denied": row.denied or 0,
            "approval_rate": round(approved / total, 3) if total > 0 else 0,
        })

    # --- Approval rate by procedure ---
    procedure_q = (
        select(
            AuthRequest.proposed_procedure,
            func.count(AuthRequest.id).label("total"),
            func.count(
                sql_case(
                    (AuthRequest.status.in_(["approved", "appeal_approved"]), AuthRequest.id),
                )
            ).label("approved"),
        )
        .where(
            and_(
                AuthRequest.org_id == org_uuid,
                AuthRequest.status.in_(["approved", "denied", "appeal_approved", "appeal_denied"]),
            )
        )
        .group_by(AuthRequest.proposed_procedure)
    )
    procedure_result = await db.execute(procedure_q)
    by_procedure = []
    for row in procedure_result.all():
        total = row.total or 0
        approved = row.approved or 0
        by_procedure.append({
            "procedure": row.proposed_procedure,
            "total": total,
            "approved": approved,
            "approval_rate": round(approved / total, 3) if total > 0 else 0,
        })

    # --- Approval rate by surgeon ---
    surgeon_q = (
        select(
            AuthRequest.surgeon_name,
            AuthRequest.surgeon_npi,
            func.count(AuthRequest.id).label("total"),
            func.count(
                sql_case(
                    (AuthRequest.status.in_(["approved", "appeal_approved"]), AuthRequest.id),
                )
            ).label("approved"),
        )
        .where(
            and_(
                AuthRequest.org_id == org_uuid,
                AuthRequest.status.in_(["approved", "denied", "appeal_approved", "appeal_denied"]),
            )
        )
        .group_by(AuthRequest.surgeon_name, AuthRequest.surgeon_npi)
    )
    surgeon_result = await db.execute(surgeon_q)
    by_surgeon = []
    for row in surgeon_result.all():
        total = row.total or 0
        approved = row.approved or 0
        by_surgeon.append({
            "surgeon_name": row.surgeon_name,
            "surgeon_npi": row.surgeon_npi,
            "total": total,
            "approved": approved,
            "approval_rate": round(approved / total, 3) if total > 0 else 0,
        })

    # --- Average days to decision ---
    days_q = (
        select(
            func.avg(
                func.extract("epoch", AuthRequest.approved_date - func.cast(AuthRequest.submitted_at, Date))
            ).label("avg_days_approved"),
        )
        .where(
            and_(
                AuthRequest.org_id == org_uuid,
                AuthRequest.status.in_(["approved", "appeal_approved"]),
                AuthRequest.submitted_at.isnot(None),
                AuthRequest.approved_date.isnot(None),
            )
        )
    )
    days_result = await db.execute(days_q)
    days_row = days_result.one_or_none()
    avg_days = None
    if days_row and days_row.avg_days_approved is not None:
        avg_days = round(float(days_row.avg_days_approved), 1)

    # --- Most common denial reasons ---
    denial_q = (
        select(AuthRequest.denial_reason, func.count(AuthRequest.id).label("cnt"))
        .where(
            and_(
                AuthRequest.org_id == org_uuid,
                AuthRequest.status.in_(["denied", "appeal_denied"]),
                AuthRequest.denial_reason.isnot(None),
            )
        )
        .group_by(AuthRequest.denial_reason)
        .order_by(func.count(AuthRequest.id).desc())
        .limit(10)
    )
    denial_result = await db.execute(denial_q)
    common_denials = [
        {"reason": row.denial_reason, "count": row.cnt}
        for row in denial_result.all()
    ]

    # --- Narrative effectiveness (from AuthLearning) ---
    effectiveness_q = (
        select(
            AuthLearning.procedure_category,
            AuthLearning.outcome,
            func.count(AuthLearning.id).label("cnt"),
        )
        .where(AuthLearning.org_id == org_uuid)
        .group_by(AuthLearning.procedure_category, AuthLearning.outcome)
    )
    eff_result = await db.execute(effectiveness_q)
    effectiveness_data: dict[str, dict] = {}
    for row in eff_result.all():
        cat = row.procedure_category
        if cat not in effectiveness_data:
            effectiveness_data[cat] = {"approved": 0, "denied": 0}
        if row.outcome in ("approved", "appeal_approved"):
            effectiveness_data[cat]["approved"] += row.cnt
        else:
            effectiveness_data[cat]["denied"] += row.cnt

    narrative_effectiveness = []
    for cat, counts in effectiveness_data.items():
        total = counts["approved"] + counts["denied"]
        narrative_effectiveness.append({
            "procedure_category": cat,
            "total": total,
            "approved": counts["approved"],
            "denied": counts["denied"],
            "approval_rate": round(counts["approved"] / total, 3) if total > 0 else 0,
        })

    # --- Total counts ---
    total_q = (
        select(func.count(AuthRequest.id))
        .where(AuthRequest.org_id == org_uuid)
    )
    total_result = await db.execute(total_q)
    total_auths = total_result.scalar() or 0

    pending_q = (
        select(func.count(AuthRequest.id))
        .where(
            and_(
                AuthRequest.org_id == org_uuid,
                AuthRequest.status.in_(["draft", "documents_uploaded", "narrative_generated", "submitted"]),
            )
        )
    )
    pending_result = await db.execute(pending_q)
    pending_count = pending_result.scalar() or 0

    return {
        "total_auths": total_auths,
        "pending_count": pending_count,
        "avg_days_to_decision": avg_days,
        "by_payer": by_payer,
        "by_procedure": by_procedure,
        "by_surgeon": by_surgeon,
        "common_denial_reasons": common_denials,
        "narrative_effectiveness": narrative_effectiveness,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _derive_procedure_category(procedure: str) -> str:
    """Derive a normalized procedure category from the procedure description."""
    if not procedure:
        return "unknown"

    proc_lower = procedure.lower()

    if any(kw in proc_lower for kw in ["fusion", "arthrodesis", "alif", "plif", "tlif", "xlif", "acdf"]):
        return "spine_fusion"
    if any(kw in proc_lower for kw in ["laminectomy", "laminotomy", "decompression", "foraminotomy", "discectomy"]):
        return "spine_decompression"
    if any(kw in proc_lower for kw in ["disc replacement", "arthroplasty", "artificial disc"]):
        return "disc_replacement"
    if any(kw in proc_lower for kw in ["total knee", "tka", "knee replacement"]):
        return "joint_replacement"
    if any(kw in proc_lower for kw in ["total hip", "tha", "hip replacement"]):
        return "joint_replacement"
    if any(kw in proc_lower for kw in ["total shoulder", "tsa", "shoulder replacement"]):
        return "joint_replacement"
    if any(kw in proc_lower for kw in ["rotator cuff", "shoulder arthroscopy"]):
        return "shoulder_surgery"
    if any(kw in proc_lower for kw in ["acl", "meniscus", "knee arthroscopy"]):
        return "knee_surgery"
    if any(kw in proc_lower for kw in ["stimulator", "scs", "spinal cord stimulation", "neuromodulation"]):
        return "neuromodulation"
    if any(kw in proc_lower for kw in ["kyphoplasty", "vertebroplasty"]):
        return "vertebral_augmentation"
    if any(kw in proc_lower for kw in ["craniotomy", "craniectomy", "tumor"]):
        return "cranial_surgery"

    return "other"


def _derive_diagnosis_category(diagnosis: str) -> str:
    """Derive a normalized diagnosis category from the primary diagnosis."""
    if not diagnosis:
        return "unknown"

    diag_lower = diagnosis.lower()

    if any(kw in diag_lower for kw in ["stenosis"]):
        return "spinal_stenosis"
    if any(kw in diag_lower for kw in ["herniat", "herniation", "disc", "disk"]):
        return "disc_herniation"
    if any(kw in diag_lower for kw in ["spondylolisthesis", "listhesis"]):
        return "spondylolisthesis"
    if any(kw in diag_lower for kw in ["myelopathy"]):
        return "myelopathy"
    if any(kw in diag_lower for kw in ["radiculopathy"]):
        return "radiculopathy"
    if any(kw in diag_lower for kw in ["fracture"]):
        return "fracture"
    if any(kw in diag_lower for kw in ["deformity", "scoliosis", "kyphosis"]):
        return "spinal_deformity"
    if any(kw in diag_lower for kw in ["tumor", "neoplasm", "metasta"]):
        return "tumor"
    if any(kw in diag_lower for kw in ["degenerative", "ddd", "spondylosis"]):
        return "degenerative"

    return "other"


async def _analyze_outcome_factors(
    auth_req: AuthRequest,
    outcome: str,
    notes: str,
) -> dict:
    """Use Claude to analyze what factors contributed to the outcome."""
    system_prompt = (
        "You are analyzing the outcome of a prior authorization to identify "
        "what factors contributed to approval or denial. This analysis will be "
        "used to improve future submissions. "
        "Respond ONLY with valid JSON:\n"
        "{\n"
        '  "approval_factors": ["factor 1", ...] or null,\n'
        '  "denial_factors": ["factor 1", ...] or null,\n'
        '  "learning_notes": "brief analysis of what can be learned"\n'
        "}"
    )

    user_message = (
        f"OUTCOME: {outcome}\n"
        f"NOTES: {notes or 'None'}\n\n"
        f"PROCEDURE: {auth_req.proposed_procedure}\n"
        f"DIAGNOSIS: {auth_req.diagnosis_primary}\n"
        f"PAYER: {auth_req.payer_name} ({auth_req.insurance_type})\n\n"
        f"NARRATIVE SUBMITTED:\n{auth_req.narrative or 'No narrative'}\n\n"
    )
    if auth_req.denial_reason:
        user_message += f"DENIAL REASON: {auth_req.denial_reason}\n\n"

    user_message += "Analyze what factors contributed to this outcome."

    try:
        response_text = _invoke_claude(system_prompt, user_message, max_tokens=2048)
        return _parse_json_response(response_text)
    except Exception as e:
        logger.exception("Outcome factor analysis failed")
        return {
            "approval_factors": None,
            "denial_factors": None,
            "learning_notes": f"Automated analysis failed: {e}",
        }


async def _update_payer_profile(
    auth_req: AuthRequest,
    outcome: str,
    db: AsyncSession,
) -> None:
    """Update or create a PayerAuthProfile with the latest outcome data."""
    # Find or create profile
    profile_q = (
        select(PayerAuthProfile)
        .where(
            and_(
                PayerAuthProfile.org_id == auth_req.org_id,
                PayerAuthProfile.payer_name == auth_req.payer_name,
            )
        )
    )
    profile_result = await db.execute(profile_q)
    profile = profile_result.scalar_one_or_none()

    if not profile:
        profile = PayerAuthProfile(
            org_id=auth_req.org_id,
            payer_name=auth_req.payer_name,
            insurance_type=auth_req.insurance_type,
            total_auths=0,
            approved_count=0,
            denied_count=0,
        )
        db.add(profile)

    profile.total_auths += 1
    if outcome in ("approved", "appeal_approved"):
        profile.approved_count += 1
    elif outcome in ("denied", "appeal_denied"):
        profile.denied_count += 1

    total = profile.approved_count + profile.denied_count
    profile.approval_rate = profile.approved_count / total if total > 0 else 0.0

    # Calculate avg days to decision
    if auth_req.submitted_at and auth_req.approved_date:
        submitted_date = auth_req.submitted_at.date() if hasattr(auth_req.submitted_at, "date") else auth_req.submitted_at
        days_diff = (auth_req.approved_date - submitted_date).days
        if profile.avg_days_to_decision is not None:
            # Running average
            profile.avg_days_to_decision = (
                (profile.avg_days_to_decision * (profile.total_auths - 1) + days_diff)
                / profile.total_auths
            )
        else:
            profile.avg_days_to_decision = float(days_diff)

    # Update common denial reasons
    if outcome in ("denied", "appeal_denied") and auth_req.denial_reason:
        existing_reasons = profile.common_denial_reasons or []
        # Add new reason or increment count
        found = False
        for reason_entry in existing_reasons:
            if isinstance(reason_entry, dict) and reason_entry.get("reason") == auth_req.denial_reason:
                reason_entry["count"] = reason_entry.get("count", 1) + 1
                found = True
                break
        if not found:
            existing_reasons.append({"reason": auth_req.denial_reason, "count": 1})
        # Sort by count descending
        existing_reasons.sort(key=lambda r: r.get("count", 0) if isinstance(r, dict) else 0, reverse=True)
        profile.common_denial_reasons = existing_reasons[:20]

    # Periodically update AI-generated tips (every 5 auths)
    if profile.total_auths % 5 == 0 and profile.total_auths >= 5:
        try:
            tips = await _generate_payer_tips(profile)
            profile.tips = tips.get("tips", profile.tips)
            profile.preferred_narrative_style = tips.get(
                "preferred_style", profile.preferred_narrative_style
            )
        except Exception:
            logger.warning("Failed to generate payer tips for %s", profile.payer_name)

    await db.flush()


async def _generate_payer_tips(profile: PayerAuthProfile) -> dict:
    """Generate AI tips for a payer based on accumulated data."""
    system_prompt = (
        "You are a prior authorization strategy advisor. Based on the payer data, "
        "generate practical tips for improving approval rates. "
        "Respond ONLY with valid JSON:\n"
        '{"tips": "concise tips text", "preferred_style": "preferred narrative style description"}'
    )

    user_message = (
        f"PAYER: {profile.payer_name} ({profile.insurance_type})\n"
        f"Total auths: {profile.total_auths}\n"
        f"Approved: {profile.approved_count}\n"
        f"Denied: {profile.denied_count}\n"
        f"Approval rate: {profile.approval_rate:.1%}\n"
        f"Avg days to decision: {profile.avg_days_to_decision or 'unknown'}\n"
        f"Common denial reasons: {json.dumps(profile.common_denial_reasons or [], default=str)}\n\n"
        "Generate tips for improving approval rates with this payer "
        "and describe their preferred narrative style."
    )

    response_text = _invoke_claude(system_prompt, user_message, max_tokens=1024)
    return _parse_json_response(response_text)
