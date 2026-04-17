"""
NYS WCB MTG Compliance Engine — checks auth requests against Medical Treatment Guidelines.

Evaluates prior authorization requests for compliance with NYS Workers' Compensation Board
Medical Treatment Guidelines. Produces compliance scores, approval probability assessments,
detailed checklists, and actionable recommendations.
"""

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .mtg_guidelines import (
    WCB_TREATMENT_GUIDELINES,
    get_procedure,
    get_category_for_procedure,
    find_procedures_by_cpt,
    find_procedures_by_icd10,
    get_all_procedure_keys,
    get_all_categories,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Requirement weight definitions
# =============================================================================

# Critical requirements: 15 points each
CRITICAL_WEIGHT = 15
# Important requirements: 10 points each
IMPORTANT_WEIGHT = 10
# Supporting requirements: 5 points each
SUPPORTING_WEIGHT = 5

# Approval probability thresholds
PROBABILITY_LEVELS = {
    "very_likely": {"min": 85, "label": "Very Likely", "description": "Strong submission with comprehensive documentation"},
    "likely": {"min": 70, "label": "Likely", "description": "Good submission, minor gaps may exist"},
    "uncertain": {"min": 50, "label": "Uncertain", "description": "Significant gaps that may lead to denial"},
    "unlikely": {"min": 30, "label": "Unlikely", "description": "Major deficiencies — additional documentation strongly recommended"},
    "very_unlikely": {"min": 0, "label": "Very Unlikely", "description": "Fundamental requirements not met — rework submission before filing"},
}


def _get_probability_level(score: int) -> str:
    """Map a compliance score (0-100) to a probability level string."""
    if score >= 85:
        return "very_likely"
    elif score >= 70:
        return "likely"
    elif score >= 50:
        return "uncertain"
    elif score >= 30:
        return "unlikely"
    else:
        return "very_unlikely"


def _normalize_treatment_class(name: str) -> str:
    """Normalize medication/treatment class names for matching."""
    return name.lower().strip().replace(" ", "_").replace("-", "_")


def _match_medication_class(med_class: str, required_class: str) -> bool:
    """Check if a medication class matches a required class, with alias support."""
    aliases = {
        "nsaids": ["nsaid", "nsaids", "ibuprofen", "naproxen", "meloxicam", "diclofenac", "celecoxib",
                    "anti_inflammatory", "non_steroidal_anti_inflammatory"],
        "nsaids_or_oral_steroids": ["nsaid", "nsaids", "nsaids_or_oral_steroids", "oral_steroids",
                                     "prednisone", "medrol", "methylprednisolone", "dexamethasone"],
        "nsaids_or_muscle_relaxants": ["nsaid", "nsaids", "muscle_relaxants", "muscle_relaxant",
                                        "cyclobenzaprine", "tizanidine", "methocarbamol", "baclofen"],
        "muscle_relaxants": ["muscle_relaxant", "muscle_relaxants", "cyclobenzaprine", "tizanidine",
                              "methocarbamol", "baclofen", "flexeril", "zanaflex"],
        "neuropathic_agents": ["neuropathic", "neuropathic_agents", "gabapentin", "pregabalin",
                                "lyrica", "neurontin", "duloxetine", "cymbalta", "amitriptyline"],
        "acetaminophen": ["acetaminophen", "tylenol", "apap"],
        "analgesics": ["analgesic", "analgesics", "acetaminophen", "tylenol", "tramadol"],
        "short_term_opioids": ["opioid", "opioids", "short_term_opioids", "hydrocodone", "oxycodone",
                                "tramadol", "codeine"],
        "cognitive_enhancers_if_prescribed": ["cognitive_enhancers", "donepezil", "memantine",
                                               "methylphenidate", "modafinil", "amantadine"],
        "oral_steroids_taper": ["oral_steroids", "oral_steroids_taper", "prednisone", "medrol",
                                 "methylprednisolone", "dexamethasone", "steroid_taper"],
        "topical_analgesics": ["topical", "topical_analgesics", "lidocaine_patch", "capsaicin",
                                "diclofenac_gel", "voltaren_gel"],
        "topical_nsaids": ["topical_nsaids", "diclofenac_gel", "voltaren_gel", "topical_anti_inflammatory"],
    }

    norm_med = _normalize_treatment_class(med_class)
    norm_req = _normalize_treatment_class(required_class)

    if norm_med == norm_req:
        return True

    known_aliases = aliases.get(norm_req, [])
    return norm_med in known_aliases


def _match_injection_type(injection_type: str, required_type: str) -> bool:
    """Check if an injection type matches a required type."""
    aliases = {
        "epidural_steroid": ["epidural", "esi", "epidural_steroid", "epidural_steroid_injection",
                              "transforaminal_epidural", "interlaminar_epidural", "caudal_epidural",
                              "tfesi", "ilesi"],
        "cervical_epidural_steroid": ["cervical_epidural", "cervical_esi", "cervical_epidural_steroid",
                                       "cervical_transforaminal"],
        "facet_block": ["facet", "facet_block", "facet_injection", "facet_joint_injection",
                         "intra_articular_facet"],
        "medial_branch_block": ["mbb", "medial_branch", "medial_branch_block"],
        "selective_nerve_root_block": ["snrb", "selective_nerve_root", "selective_nerve_root_block",
                                        "nerve_root_block"],
        "intra_articular_corticosteroid": ["intra_articular", "intra_articular_corticosteroid",
                                            "knee_injection", "joint_injection", "cortisone_injection"],
        "intra_articular_hip_corticosteroid": ["hip_injection", "intra_articular_hip",
                                                 "intra_articular_hip_corticosteroid"],
        "subacromial_corticosteroid": ["subacromial", "subacromial_injection", "subacromial_corticosteroid",
                                        "shoulder_injection"],
        "carpal_tunnel_corticosteroid": ["carpal_tunnel_injection", "carpal_tunnel_corticosteroid",
                                          "ct_injection"],
        "tendon_sheath_corticosteroid": ["tendon_sheath", "tendon_sheath_corticosteroid",
                                          "trigger_finger_injection", "a1_pulley_injection"],
        "viscosupplementation": ["viscosupplementation", "hyaluronic_acid", "synvisc", "euflexxa",
                                  "gel_one", "hyalgan"],
        "nerve_block": ["nerve_block", "peripheral_nerve_block"],
    }

    norm_inj = _normalize_treatment_class(injection_type)
    norm_req = _normalize_treatment_class(required_type)

    if norm_inj == norm_req:
        return True

    known_aliases = aliases.get(norm_req, [])
    return norm_inj in known_aliases


def _match_imaging_type(imaging_type: str, required_type: str) -> bool:
    """Check if an imaging study matches a required type."""
    aliases = {
        "MRI_lumbar": ["mri_lumbar", "mri_l_spine", "mri_lumbar_spine", "lumbar_mri"],
        "MRI_cervical": ["mri_cervical", "mri_c_spine", "mri_cervical_spine", "cervical_mri"],
        "MRI_shoulder": ["mri_shoulder", "shoulder_mri"],
        "MRI_knee": ["mri_knee", "knee_mri"],
        "MRI_hip": ["mri_hip", "hip_mri"],
        "MRI_brain": ["mri_brain", "brain_mri", "mri_head"],
        "MRI_spine_at_pain_level": ["mri_spine", "mri_lumbar", "mri_cervical", "mri_thoracic",
                                     "lumbar_mri", "cervical_mri"],
        "MRI_at_affected_level": ["mri_lumbar", "mri_cervical", "mri_thoracic", "mri_spine",
                                   "lumbar_mri", "cervical_mri"],
        "MRI_or_CT_at_affected_level": ["mri_lumbar", "mri_cervical", "ct_lumbar", "ct_cervical",
                                          "mri_spine", "ct_spine"],
        "CT_lumbar": ["ct_lumbar", "ct_l_spine", "lumbar_ct"],
        "CT_cervical": ["ct_cervical", "ct_c_spine", "cervical_ct"],
        "CT_head_if_acute": ["ct_head", "head_ct", "ct_brain"],
        "CT_if_MRI_contraindicated": ["ct_lumbar", "ct_cervical", "ct_spine"],
        "flexion_extension_xrays": ["flex_ext", "flexion_extension", "dynamic_xrays",
                                     "flexion_extension_xrays", "flex_ext_xrays"],
        "plain_xrays_knee_weight_bearing": ["knee_xray", "xray_knee", "plain_xrays_knee",
                                              "weight_bearing_knee_xray", "standing_knee_xray"],
        "plain_xrays_knee_AP_lateral_sunrise": ["knee_xray", "xray_knee", "plain_xrays_knee",
                                                  "ap_lateral_knee", "sunrise_view"],
        "plain_xrays_hip_AP_pelvis_and_lateral": ["hip_xray", "xray_hip", "pelvis_xray",
                                                    "ap_pelvis", "hip_lateral"],
        "plain_xrays_shoulder": ["shoulder_xray", "xray_shoulder"],
        "plain_xrays_ankle_AP_lateral_mortise": ["ankle_xray", "xray_ankle", "ankle_films"],
        "plain_xrays_pelvis_or_SI_joints": ["pelvis_xray", "si_joint_xray", "xray_pelvis"],
    }

    norm_img = _normalize_treatment_class(imaging_type)
    norm_req = _normalize_treatment_class(required_type)

    if norm_img == norm_req:
        return True

    known_aliases = aliases.get(required_type, [])
    return norm_img in [_normalize_treatment_class(a) for a in known_aliases]


# =============================================================================
# Core compliance checking
# =============================================================================

def check_compliance(auth_data: dict, procedure_key: str) -> dict:
    """
    Check an authorization request against NYS WCB MTG guidelines for a specific procedure.

    Parameters
    ----------
    auth_data : dict
        Authorization request data containing:
        - conservative_treatments: list of {type, duration_weeks, sessions, outcome}
        - medications: list of {name, class, duration_weeks}
        - injections: list of {type, date, response}
        - imaging: list of {type, date, findings}
        - diagnostics: list of {type, date, findings}
        - functional_scores: {odi, ndi, vas, dash, koos, womac, harris_hip, etc.}
        - symptom_duration_weeks: int
        - work_status: str
        - clinical_findings: list of str
        - diagnosis_codes: list of str

    procedure_key : str
        Key identifying the procedure (e.g., "lumbar_fusion", "knee_arthroscopy")

    Returns
    -------
    dict
        Compliance assessment with score, checklist, recommendations, and approval probability.
    """
    procedure = get_procedure(procedure_key)
    if not procedure:
        return {
            "error": f"Procedure '{procedure_key}' not found in MTG guidelines",
            "available_procedures": get_all_procedure_keys(),
        }

    checklist = []
    missing_critical = []
    missing_recommended = []
    strengths = []
    weaknesses = []
    recommendations = []

    # Extract auth_data fields with defaults
    conservative_treatments = auth_data.get("conservative_treatments", [])
    medications = auth_data.get("medications", [])
    injections = auth_data.get("injections", [])
    imaging = auth_data.get("imaging", [])
    diagnostics = auth_data.get("diagnostics", [])
    functional_scores = auth_data.get("functional_scores", {})
    symptom_duration_weeks = auth_data.get("symptom_duration_weeks", 0)
    work_status = auth_data.get("work_status", "")
    clinical_findings = auth_data.get("clinical_findings", [])
    diagnosis_codes = auth_data.get("diagnosis_codes", [])

    cons_req = procedure.get("conservative_requirements", {})
    img_req = procedure.get("imaging_requirements", {})
    diag_req = procedure.get("diagnostic_requirements", {})

    # -------------------------------------------------------------------------
    # 1. Physical Therapy compliance
    # -------------------------------------------------------------------------
    pt_req = cons_req.get("physical_therapy", {})
    min_pt_weeks = pt_req.get("min_weeks", 0)
    min_pt_sessions = pt_req.get("min_sessions", 0)

    if min_pt_weeks > 0 or min_pt_sessions > 0:
        pt_treatments = [t for t in conservative_treatments
                         if _normalize_treatment_class(t.get("type", "")) in
                         ["physical_therapy", "pt", "physiotherapy", "supervised_pt"]]

        total_pt_weeks = sum(t.get("duration_weeks", 0) for t in pt_treatments)
        total_pt_sessions = sum(t.get("sessions", 0) for t in pt_treatments)

        pt_met = total_pt_weeks >= min_pt_weeks and total_pt_sessions >= min_pt_sessions

        if pt_met:
            detail = f"{total_pt_weeks} weeks, {total_pt_sessions} sessions completed"
            strengths.append("Adequate physical therapy documented")
        elif total_pt_weeks > 0 or total_pt_sessions > 0:
            detail = (f"{total_pt_weeks} weeks, {total_pt_sessions} sessions — "
                      f"requires >= {min_pt_weeks} weeks and >= {min_pt_sessions} sessions")
            weaknesses.append(f"PT insufficient: {total_pt_weeks}/{min_pt_weeks} weeks, "
                              f"{total_pt_sessions}/{min_pt_sessions} sessions")
            recommendations.append(
                f"Complete at least {min_pt_weeks} weeks ({min_pt_sessions} sessions) of "
                f"supervised PT before resubmitting")
        else:
            detail = f"No PT documented — requires >= {min_pt_weeks} weeks ({min_pt_sessions} sessions)"
            missing_critical.append("Physical therapy documentation")
            weaknesses.append("No physical therapy documented")
            recommendations.append(
                f"Document {min_pt_weeks}+ weeks of supervised physical therapy with specific program details")

        checklist.append({
            "requirement": f"Physical Therapy >= {min_pt_weeks} weeks / {min_pt_sessions} sessions",
            "met": pt_met,
            "detail": detail,
            "weight": CRITICAL_WEIGHT,
            "category": "conservative_care",
        })

    # -------------------------------------------------------------------------
    # 2. Medication compliance
    # -------------------------------------------------------------------------
    med_req = cons_req.get("medications", {})
    required_meds = med_req.get("required", [])
    med_min_duration = med_req.get("min_duration_weeks", 0)

    if required_meds:
        for req_med in required_meds:
            matching_meds = [m for m in medications
                            if _match_medication_class(m.get("class", m.get("name", "")), req_med)]
            med_duration = max((m.get("duration_weeks", 0) for m in matching_meds), default=0)

            med_met = len(matching_meds) > 0 and (med_min_duration == 0 or med_duration >= med_min_duration)

            if med_met:
                detail = f"{req_med} taken for {med_duration} weeks"
            elif matching_meds:
                detail = f"{req_med} documented but duration insufficient ({med_duration}/{med_min_duration} weeks)"
                recommendations.append(f"Document {req_med} use for at least {med_min_duration} weeks")
            else:
                detail = f"{req_med} not documented — REQUIRED"
                missing_critical.append(f"Medication trial: {req_med}")
                recommendations.append(f"Document trial of {req_med} with duration and response")

            checklist.append({
                "requirement": f"Medication: {req_med} >= {med_min_duration} weeks",
                "met": med_met,
                "detail": detail,
                "weight": IMPORTANT_WEIGHT,
                "category": "medications",
            })

    # -------------------------------------------------------------------------
    # 3. Injection compliance
    # -------------------------------------------------------------------------
    inj_req = cons_req.get("injections", {})
    min_injection_attempts = inj_req.get("min_attempts", 0)
    required_inj_types = inj_req.get("types", [])

    if min_injection_attempts > 0:
        matching_injections = []
        for inj in injections:
            inj_type = inj.get("type", "")
            for req_type in required_inj_types:
                if _match_injection_type(inj_type, req_type):
                    matching_injections.append(inj)
                    break

        inj_met = len(matching_injections) >= min_injection_attempts

        if inj_met:
            failed_inj = [i for i in matching_injections
                          if i.get("response", "").lower() in
                          ["failed", "no_relief", "minimal_relief", "less_than_50_percent",
                           "<50%", "poor", "none", "temporary"]]
            if failed_inj:
                detail = f"{len(matching_injections)} injection(s) attempted, {len(failed_inj)} with inadequate relief"
                strengths.append("Failed injection therapy documented")
            else:
                detail = f"{len(matching_injections)} injection(s) attempted"
        else:
            types_str = ", ".join(required_inj_types)
            detail = (f"{len(matching_injections)}/{min_injection_attempts} required injections documented. "
                      f"Types: {types_str}")
            missing_critical.append(f"Injection therapy: minimum {min_injection_attempts} attempt(s)")
            recommendations.append(
                f"Document at least {min_injection_attempts} injection attempt(s) ({types_str}) "
                f"with dates and response to each")

        checklist.append({
            "requirement": f"Failed >= {min_injection_attempts} injection(s)",
            "met": inj_met,
            "detail": detail,
            "weight": CRITICAL_WEIGHT,
            "category": "injections",
        })

    # -------------------------------------------------------------------------
    # 4. Total conservative care duration
    # -------------------------------------------------------------------------
    total_cons_weeks = cons_req.get("total_conservative_duration_weeks", 0)

    if total_cons_weeks > 0:
        cons_met = symptom_duration_weeks >= total_cons_weeks

        if cons_met:
            detail = f"{symptom_duration_weeks} weeks of conservative care documented"
            if symptom_duration_weeks >= total_cons_weeks * 1.5:
                strengths.append("Extended conservative care trial exceeding minimum")
        else:
            detail = (f"{symptom_duration_weeks}/{total_cons_weeks} weeks documented — "
                      f"minimum {total_cons_weeks} weeks required")
            missing_critical.append(f"Minimum {total_cons_weeks} weeks of conservative care")
            recommendations.append(
                f"Document at least {total_cons_weeks} weeks of comprehensive conservative care "
                f"before requesting this procedure")

        checklist.append({
            "requirement": f"Total conservative care >= {total_cons_weeks} weeks",
            "met": cons_met,
            "detail": detail,
            "weight": CRITICAL_WEIGHT,
            "category": "conservative_care",
        })

    # -------------------------------------------------------------------------
    # 5. Required imaging
    # -------------------------------------------------------------------------
    required_imaging = img_req.get("required", [])
    findings_required = img_req.get("findings_required", [])

    for req_img in required_imaging:
        matching_images = [i for i in imaging if _match_imaging_type(i.get("type", ""), req_img)]
        img_met = len(matching_images) > 0

        if img_met:
            findings = matching_images[0].get("findings", "")
            detail = f"{req_img} obtained" + (f" — findings: {findings}" if findings else "")
            # Check if findings correlate with clinical picture
            if findings:
                strengths.append(f"Imaging ({req_img}) with documented findings")
        else:
            detail = f"{req_img} NOT documented — REQUIRED"
            missing_critical.append(f"Imaging: {req_img}")
            recommendations.append(f"Obtain and include {req_img} results in submission")

        checklist.append({
            "requirement": f"Imaging: {req_img}",
            "met": img_met,
            "detail": detail,
            "weight": CRITICAL_WEIGHT,
            "category": "imaging",
        })

    # -------------------------------------------------------------------------
    # 6. Required diagnostics
    # -------------------------------------------------------------------------
    required_diags = diag_req.get("required", [])
    conditional_diags = diag_req.get("conditional", [])

    for req_diag in required_diags:
        matching_diags = [d for d in diagnostics
                          if _normalize_treatment_class(d.get("type", "")) ==
                          _normalize_treatment_class(req_diag)]
        diag_met = len(matching_diags) > 0

        if diag_met:
            findings = matching_diags[0].get("findings", "")
            detail = f"{req_diag} completed" + (f" — {findings}" if findings else "")
        else:
            detail = f"{req_diag} NOT documented — REQUIRED"
            missing_critical.append(f"Diagnostic: {req_diag}")
            recommendations.append(f"Complete {req_diag} and include results in submission")

        checklist.append({
            "requirement": f"Diagnostic: {req_diag}",
            "met": diag_met,
            "detail": detail,
            "weight": CRITICAL_WEIGHT,
            "category": "diagnostics",
        })

    for cond_diag in conditional_diags:
        matching_diags = [d for d in diagnostics
                          if _normalize_treatment_class(d.get("type", "")) ==
                          _normalize_treatment_class(cond_diag)]
        diag_met = len(matching_diags) > 0

        if diag_met:
            findings = matching_diags[0].get("findings", "")
            detail = f"{cond_diag} completed" + (f" — {findings}" if findings else "")
        else:
            detail = f"{cond_diag} not provided (conditional — may strengthen submission)"
            missing_recommended.append(f"Diagnostic: {cond_diag}")

        checklist.append({
            "requirement": f"Diagnostic (conditional): {cond_diag}",
            "met": diag_met,
            "detail": detail,
            "weight": SUPPORTING_WEIGHT,
            "category": "diagnostics",
        })

    # -------------------------------------------------------------------------
    # 7. Functional scores
    # -------------------------------------------------------------------------
    category_key = get_category_for_procedure(procedure_key)

    # Determine which functional score is most relevant
    relevant_score = None
    relevant_score_name = None
    relevant_threshold = None

    if category_key == "spine":
        if any(k in procedure_key for k in ["cervical", "acdf"]):
            relevant_score = functional_scores.get("ndi")
            relevant_score_name = "NDI"
            relevant_threshold = 30
        else:
            relevant_score = functional_scores.get("odi")
            relevant_score_name = "ODI"
            relevant_threshold = 40
    elif category_key == "orthopedic":
        if "knee" in procedure_key or "acl" in procedure_key:
            relevant_score = functional_scores.get("koos") or functional_scores.get("womac")
            relevant_score_name = "KOOS/WOMAC"
            relevant_threshold = None  # Variable
        elif "hip" in procedure_key:
            relevant_score = functional_scores.get("harris_hip") or functional_scores.get("womac")
            relevant_score_name = "Harris Hip Score/WOMAC"
            relevant_threshold = None
        elif "shoulder" in procedure_key or "rotator" in procedure_key:
            relevant_score = functional_scores.get("dash") or functional_scores.get("ases")
            relevant_score_name = "DASH/ASES"
            relevant_threshold = None
        elif "carpal" in procedure_key:
            relevant_score = functional_scores.get("dash") or functional_scores.get("boston_ctsq")
            relevant_score_name = "DASH/Boston CTSQ"
            relevant_threshold = None

    # For spine procedures with specific thresholds
    if relevant_score_name and relevant_threshold:
        score_met = relevant_score is not None and relevant_score >= relevant_threshold

        if relevant_score is not None:
            if score_met:
                detail = f"{relevant_score_name} = {relevant_score} (threshold: >= {relevant_threshold})"
                strengths.append(f"Functional impairment documented ({relevant_score_name} = {relevant_score})")
            else:
                detail = f"{relevant_score_name} = {relevant_score} — below threshold of {relevant_threshold}"
                weaknesses.append(f"{relevant_score_name} below threshold ({relevant_score} < {relevant_threshold})")
        else:
            detail = f"{relevant_score_name} not documented — REQUIRED for strong submission"
            score_met = False
            missing_critical.append(f"{relevant_score_name} functional score documentation")
            recommendations.append(
                f"Obtain {relevant_score_name} score and include in submission — "
                f"threshold is >= {relevant_threshold}")

        checklist.append({
            "requirement": f"Functional Score: {relevant_score_name} >= {relevant_threshold}",
            "met": score_met,
            "detail": detail,
            "weight": IMPORTANT_WEIGHT,
            "category": "functional_scores",
        })
    elif relevant_score_name:
        score_met = relevant_score is not None
        if score_met:
            detail = f"{relevant_score_name} = {relevant_score}"
            strengths.append(f"Functional outcome score documented ({relevant_score_name})")
        else:
            detail = f"{relevant_score_name} not documented — recommended"
            missing_recommended.append(f"{relevant_score_name} functional score")
            recommendations.append(f"Include {relevant_score_name} score to strengthen submission")

        checklist.append({
            "requirement": f"Functional Score: {relevant_score_name}",
            "met": score_met,
            "detail": detail,
            "weight": IMPORTANT_WEIGHT,
            "category": "functional_scores",
        })

    # VAS pain score (universal)
    vas = functional_scores.get("vas")
    if vas is not None:
        checklist.append({
            "requirement": "VAS Pain Score documented",
            "met": True,
            "detail": f"VAS = {vas}/10",
            "weight": SUPPORTING_WEIGHT,
            "category": "functional_scores",
        })
    else:
        checklist.append({
            "requirement": "VAS Pain Score documented",
            "met": False,
            "detail": "VAS not documented — recommended for all submissions",
            "weight": SUPPORTING_WEIGHT,
            "category": "functional_scores",
        })
        missing_recommended.append("VAS pain score")

    # -------------------------------------------------------------------------
    # 8. Work status documentation
    # -------------------------------------------------------------------------
    work_documented = bool(work_status and work_status.strip())

    if work_documented:
        detail = f"Work status: {work_status}"
        if work_status.lower() in ["out_of_work", "disabled", "total_disability",
                                     "modified_duty", "light_duty", "restricted"]:
            strengths.append("Work disability/restriction documented")
    else:
        detail = "Work status not documented — include for stronger submission"
        missing_recommended.append("Work status documentation")
        recommendations.append("Include current work status and functional limitations in narrative")

    checklist.append({
        "requirement": "Work status documented",
        "met": work_documented,
        "detail": detail,
        "weight": SUPPORTING_WEIGHT,
        "category": "documentation",
    })

    # -------------------------------------------------------------------------
    # 9. Clinical findings correlation
    # -------------------------------------------------------------------------
    clinical_criteria = procedure.get("clinical_criteria", [])
    has_clinical_findings = len(clinical_findings) > 0

    if has_clinical_findings:
        detail = f"{len(clinical_findings)} clinical findings documented"
        strengths.append("Clinical findings documented in submission")
    else:
        detail = "No clinical findings documented — include exam findings that support the procedure"
        missing_recommended.append("Clinical examination findings")
        recommendations.append(
            "Document specific clinical examination findings that correlate with imaging "
            "and support the need for this procedure")

    checklist.append({
        "requirement": "Clinical findings documented and correlating",
        "met": has_clinical_findings,
        "detail": detail,
        "weight": IMPORTANT_WEIGHT,
        "category": "clinical",
    })

    # -------------------------------------------------------------------------
    # 10. Diagnosis code match
    # -------------------------------------------------------------------------
    procedure_icd10 = procedure.get("icd10_codes", [])
    if diagnosis_codes and procedure_icd10:
        matching_codes = []
        for dx in diagnosis_codes:
            for proc_icd in procedure_icd10:
                clean_proc = proc_icd.rstrip("*")
                if dx == proc_icd or dx.startswith(clean_proc):
                    matching_codes.append(dx)
                    break

        dx_met = len(matching_codes) > 0

        if dx_met:
            detail = f"Matching ICD-10 codes: {', '.join(matching_codes)}"
        else:
            detail = (f"No matching ICD-10 codes. Submitted: {', '.join(diagnosis_codes[:5])}. "
                      f"Expected: {', '.join(procedure_icd10[:5])}")
            weaknesses.append("Diagnosis codes may not match procedure guidelines")
            recommendations.append(
                "Verify ICD-10 codes match the MTG-approved indications for this procedure")
    elif diagnosis_codes:
        dx_met = True
        detail = f"Diagnosis codes provided: {', '.join(diagnosis_codes[:5])}"
    else:
        dx_met = False
        detail = "No diagnosis codes provided"
        missing_critical.append("ICD-10 diagnosis codes")

    checklist.append({
        "requirement": "ICD-10 diagnosis codes match procedure indications",
        "met": dx_met,
        "detail": detail,
        "weight": IMPORTANT_WEIGHT,
        "category": "coding",
    })

    # -------------------------------------------------------------------------
    # 11. Exclusion criteria check
    # -------------------------------------------------------------------------
    exclusion_criteria = procedure.get("exclusion_criteria", [])
    # We can only check exclusions if clinical findings mention them
    exclusion_flags = []
    clinical_findings_lower = [f.lower() for f in clinical_findings]

    exclusion_keywords = {
        "active_infection": ["infection", "sepsis", "abscess"],
        "substance_abuse": ["substance abuse", "drug abuse", "addiction", "active substance"],
        "psychiatric": ["uncontrolled psychiatric", "psychosis", "somatization"],
        "bmi_over_40": ["bmi >40", "bmi over 40", "morbid obesity"],
        "coagulopathy": ["coagulopathy", "bleeding disorder", "anticoagulation"],
    }

    for exc_key, keywords in exclusion_keywords.items():
        for finding in clinical_findings_lower:
            if any(kw in finding for kw in keywords):
                exclusion_flags.append(exc_key)
                break

    if exclusion_flags:
        checklist.append({
            "requirement": "No exclusion criteria present",
            "met": False,
            "detail": f"Potential exclusion criteria identified: {', '.join(exclusion_flags)}",
            "weight": CRITICAL_WEIGHT,
            "category": "exclusions",
        })
        weaknesses.append(f"Potential exclusion criteria: {', '.join(exclusion_flags)}")
        recommendations.append(
            "Address identified exclusion criteria — document why they do not apply or "
            "have been managed")
    else:
        checklist.append({
            "requirement": "No exclusion criteria present",
            "met": True,
            "detail": "No exclusion criteria identified in submission data",
            "weight": SUPPORTING_WEIGHT,
            "category": "exclusions",
        })

    # -------------------------------------------------------------------------
    # 12. Frequency limits (for injection procedures)
    # -------------------------------------------------------------------------
    freq_limits = procedure.get("frequency_limits")
    if freq_limits:
        max_per_year = freq_limits.get("max_per_region_per_year") or freq_limits.get("max_per_joint_per_year")
        if max_per_year:
            # Count injections of this type in the past year
            prior_count = len(injections)  # Simplified — real implementation would filter by date
            freq_met = prior_count < max_per_year
            detail = (f"{prior_count} prior injection(s) documented "
                      f"(max {max_per_year} per region per year)")

            checklist.append({
                "requirement": f"Frequency limit: max {max_per_year} per region per year",
                "met": freq_met,
                "detail": detail,
                "weight": IMPORTANT_WEIGHT,
                "category": "frequency",
            })

            if not freq_met:
                weaknesses.append(f"Frequency limit may be exceeded ({prior_count}/{max_per_year} per year)")

    # -------------------------------------------------------------------------
    # Calculate compliance score
    # -------------------------------------------------------------------------
    total_possible = sum(item["weight"] for item in checklist)
    total_earned = sum(item["weight"] for item in checklist if item["met"])

    if total_possible > 0:
        # Normalize to 0-100 scale
        compliance_score = round((total_earned / total_possible) * 100)
    else:
        compliance_score = 100  # No requirements (e.g., acute trauma)

    met_count = sum(1 for item in checklist if item["met"])
    total_count = len(checklist)

    approval_probability = _get_probability_level(compliance_score)

    # Add general recommendations based on score
    if compliance_score < 70:
        recommendations.append(
            "Consider addressing missing critical items before submission to improve "
            "approval probability")
    if not strengths:
        recommendations.append(
            "Submission lacks documented strengths — add specific clinical details "
            "that support medical necessity")

    return {
        "procedure": procedure_key,
        "procedure_name": procedure["name"],
        "compliance_score": compliance_score,
        "approval_probability": approval_probability,
        "checklist": checklist,
        "met_count": met_count,
        "total_count": total_count,
        "missing_critical": missing_critical,
        "missing_recommended": missing_recommended,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendations": recommendations,
        "mtg_reference": procedure.get("mtg_reference", ""),
        "category": get_category_for_procedure(procedure_key),
    }


# =============================================================================
# Procedure information retrieval
# =============================================================================

def get_procedure_requirements(procedure_key: str) -> dict:
    """
    Return all requirements for a specific procedure.

    Returns a structured summary of everything needed for compliance.
    """
    procedure = get_procedure(procedure_key)
    if not procedure:
        return {"error": f"Procedure '{procedure_key}' not found", "available": get_all_procedure_keys()}

    cons_req = procedure.get("conservative_requirements", {})

    return {
        "procedure_key": procedure_key,
        "procedure_name": procedure["name"],
        "category": get_category_for_procedure(procedure_key),
        "cpt_codes": procedure.get("cpt_codes", []),
        "icd10_codes": procedure.get("icd10_codes", []),
        "conservative_requirements": {
            "physical_therapy": cons_req.get("physical_therapy", {}),
            "medications": cons_req.get("medications", {}),
            "injections": cons_req.get("injections", {}),
            "activity_modification": cons_req.get("activity_modification", {}),
            "total_duration_weeks": cons_req.get("total_conservative_duration_weeks", 0),
            "additional_requirements": cons_req.get("additional_requirements", []),
        },
        "imaging_requirements": procedure.get("imaging_requirements", {}),
        "diagnostic_requirements": procedure.get("diagnostic_requirements", {}),
        "clinical_criteria": procedure.get("clinical_criteria", []),
        "exclusion_criteria": procedure.get("exclusion_criteria", []),
        "approval_factors": procedure.get("approval_factors", {}),
        "global_period_days": procedure.get("global_period_days", 0),
        "frequency_limits": procedure.get("frequency_limits"),
        "mtg_reference": procedure.get("mtg_reference", ""),
    }


def get_all_procedures() -> list[dict]:
    """
    Return a summary of all procedures with category, name, and CPT codes.
    """
    results = []
    for cat_key, cat_data in WCB_TREATMENT_GUIDELINES.items():
        for proc_key, proc_data in cat_data["procedures"].items():
            results.append({
                "procedure_key": proc_key,
                "category": cat_data["category"],
                "category_key": cat_key,
                "name": proc_data["name"],
                "cpt_codes": proc_data.get("cpt_codes", []),
                "icd10_codes": proc_data.get("icd10_codes", []),
                "global_period_days": proc_data.get("global_period_days", 0),
                "conservative_weeks_required": proc_data.get("conservative_requirements", {}).get(
                    "total_conservative_duration_weeks", 0),
                "mtg_reference": proc_data.get("mtg_reference", ""),
            })
    return results


def search_procedure(query: str) -> list[dict]:
    """
    Search procedures by name, CPT code, ICD-10 code, or keyword.

    Returns matching procedures ranked by relevance.
    """
    query_lower = query.lower().strip()
    results = []
    seen_keys = set()

    # 1. Exact CPT code match
    cpt_matches = find_procedures_by_cpt(query.strip())
    for cat_key, proc_key in cpt_matches:
        if proc_key not in seen_keys:
            proc = get_procedure(proc_key)
            results.append({
                "procedure_key": proc_key,
                "category": cat_key,
                "name": proc["name"],
                "cpt_codes": proc.get("cpt_codes", []),
                "match_type": "cpt_code",
                "relevance": 100,
            })
            seen_keys.add(proc_key)

    # 2. ICD-10 code match
    icd_matches = find_procedures_by_icd10(query.strip())
    for cat_key, proc_key in icd_matches:
        if proc_key not in seen_keys:
            proc = get_procedure(proc_key)
            results.append({
                "procedure_key": proc_key,
                "category": cat_key,
                "name": proc["name"],
                "icd10_codes": proc.get("icd10_codes", []),
                "match_type": "icd10_code",
                "relevance": 95,
            })
            seen_keys.add(proc_key)

    # 3. Name / keyword search
    for proc_key in get_all_procedure_keys():
        if proc_key in seen_keys:
            continue
        proc = get_procedure(proc_key)
        name_lower = proc["name"].lower()
        key_lower = proc_key.lower()

        # Check name match
        if query_lower in name_lower or query_lower in key_lower:
            relevance = 90 if query_lower in key_lower else 80
            results.append({
                "procedure_key": proc_key,
                "category": get_category_for_procedure(proc_key),
                "name": proc["name"],
                "cpt_codes": proc.get("cpt_codes", []),
                "match_type": "name",
                "relevance": relevance,
            })
            seen_keys.add(proc_key)
            continue

        # Check keyword match in clinical criteria
        criteria = proc.get("clinical_criteria", [])
        for criterion in criteria:
            if query_lower in criterion.lower():
                results.append({
                    "procedure_key": proc_key,
                    "category": get_category_for_procedure(proc_key),
                    "name": proc["name"],
                    "match_type": "clinical_criteria",
                    "relevance": 60,
                })
                seen_keys.add(proc_key)
                break

    # Sort by relevance
    results.sort(key=lambda x: x.get("relevance", 0), reverse=True)
    return results


# =============================================================================
# Detailed approval probability calculation
# =============================================================================

def calculate_approval_probability(compliance_result: dict) -> dict:
    """
    Detailed probability calculation with improvement actions.

    Parameters
    ----------
    compliance_result : dict
        Output from check_compliance()

    Returns
    -------
    dict
        Detailed probability assessment with improvement actions.
    """
    score = compliance_result.get("compliance_score", 0)
    level = _get_probability_level(score)
    level_info = PROBABILITY_LEVELS[level]

    checklist = compliance_result.get("checklist", [])
    missing_critical = compliance_result.get("missing_critical", [])
    missing_recommended = compliance_result.get("missing_recommended", [])

    # Count met vs unmet by category
    category_scores = {}
    for item in checklist:
        cat = item.get("category", "other")
        if cat not in category_scores:
            category_scores[cat] = {"met": 0, "total": 0, "weight_met": 0, "weight_total": 0}
        category_scores[cat]["total"] += 1
        category_scores[cat]["weight_total"] += item["weight"]
        if item["met"]:
            category_scores[cat]["met"] += 1
            category_scores[cat]["weight_met"] += item["weight"]

    # Calculate improvement potential
    improvement_actions = []
    for item in checklist:
        if not item["met"]:
            potential_gain = item["weight"]
            total_possible = sum(i["weight"] for i in checklist)
            pct_gain = round((potential_gain / total_possible) * 100) if total_possible > 0 else 0
            improvement_actions.append({
                "action": item["requirement"],
                "detail": item["detail"],
                "category": item.get("category", "other"),
                "weight": potential_gain,
                "score_improvement_pct": pct_gain,
                "priority": "critical" if item["weight"] >= CRITICAL_WEIGHT else
                           "important" if item["weight"] >= IMPORTANT_WEIGHT else "supporting",
            })

    # Sort by impact
    improvement_actions.sort(key=lambda x: x["weight"], reverse=True)

    # Projected score if all critical items addressed
    critical_unmet = [a for a in improvement_actions if a["priority"] == "critical"]
    potential_gain = sum(a["score_improvement_pct"] for a in critical_unmet)
    projected_score = min(100, score + potential_gain)
    projected_level = _get_probability_level(projected_score)

    explanation_parts = []
    if missing_critical:
        explanation_parts.append(
            f"Missing {len(missing_critical)} critical requirement(s): "
            f"{'; '.join(missing_critical[:3])}")
    if compliance_result.get("strengths"):
        explanation_parts.append(
            f"Strengths: {'; '.join(compliance_result['strengths'][:3])}")
    if compliance_result.get("weaknesses"):
        explanation_parts.append(
            f"Weaknesses: {'; '.join(compliance_result['weaknesses'][:3])}")

    explanation = ". ".join(explanation_parts) if explanation_parts else level_info["description"]

    return {
        "probability_pct": score,
        "level": level,
        "level_label": level_info["label"],
        "explanation": explanation,
        "category_breakdown": category_scores,
        "improvement_actions": improvement_actions,
        "projected_score_if_critical_addressed": projected_score,
        "projected_level_if_critical_addressed": projected_level,
        "critical_gaps": len(critical_unmet),
        "total_gaps": len(improvement_actions),
    }


# =============================================================================
# AI-powered compliance review
# =============================================================================

async def ai_compliance_review(auth_request_id: str, db: AsyncSession) -> dict:
    """
    Use Claude AI via Bedrock for a deeper compliance review.

    Pulls all documents and extracted data for the auth request, compares
    against MTG guidelines, and identifies subtle compliance issues.

    Parameters
    ----------
    auth_request_id : str
        UUID of the authorization request.
    db : AsyncSession
        Database session.

    Returns
    -------
    dict
        AI assessment with compliance score, recommendations, missing elements,
        and narrative suggestions.
    """
    import boto3
    from ..config import get_settings

    settings = get_settings()

    # Pull auth request data from database
    from ..models.models import RFASubmission, RFACase

    try:
        import uuid
        req_id = uuid.UUID(auth_request_id)
    except ValueError:
        return {"error": f"Invalid auth_request_id: {auth_request_id}"}

    result = await db.execute(
        select(RFASubmission).where(RFASubmission.id == req_id)
    )
    submission = result.scalar_one_or_none()

    if not submission:
        return {"error": f"Submission {auth_request_id} not found"}

    # Build context from submission data
    submission_data = {
        "id": str(submission.id),
        "status": submission.status,
        "form_data": submission.form_data if hasattr(submission, "form_data") else {},
        "extracted_data": submission.extracted_data if hasattr(submission, "extracted_data") else {},
    }

    # Determine procedure from submission data
    form_data = submission_data.get("form_data", {}) or {}
    extracted = submission_data.get("extracted_data", {}) or {}

    procedure_key = (
        form_data.get("procedure_key")
        or extracted.get("procedure_key")
        or _infer_procedure_from_data(form_data, extracted)
    )

    # Run rule-based compliance check first
    auth_data = _build_auth_data_from_submission(form_data, extracted)
    rule_based_result = None
    if procedure_key:
        rule_based_result = check_compliance(auth_data, procedure_key)

    # Build AI prompt
    procedure_info = get_procedure(procedure_key) if procedure_key else None

    prompt = f"""You are a NYS Workers' Compensation Board Medical Treatment Guidelines (MTG) compliance expert.

Review this prior authorization request and provide a detailed compliance assessment.

## Submission Data
{json.dumps(submission_data, indent=2, default=str)}

## Procedure
{json.dumps({"key": procedure_key, "name": procedure_info["name"] if procedure_info else "Unknown"}, indent=2)}

## MTG Guidelines for this Procedure
{json.dumps(procedure_info, indent=2, default=str) if procedure_info else "Procedure not identified — assess based on available data."}

## Rule-Based Compliance Result
{json.dumps(rule_based_result, indent=2, default=str) if rule_based_result else "Not available."}

## Instructions
Provide a detailed compliance review in JSON format with these fields:
1. "ai_assessment": A narrative paragraph assessing overall compliance with MTG guidelines
2. "compliance_score": Integer 0-100 (your independent assessment)
3. "agrees_with_rule_check": Boolean — whether you agree with the rule-based score
4. "recommendations": List of specific, actionable recommendations to improve compliance
5. "missing_elements": List of specific documentation elements that are missing or insufficient
6. "narrative_suggestions": List of specific phrases or documentation to add to the medical narrative
7. "risk_factors": List of factors that could lead to denial
8. "mtg_citations": List of specific MTG sections relevant to this request

Respond with ONLY valid JSON."""

    try:
        bedrock = boto3.client(
            "bedrock-runtime",
            region_name=settings.bedrock_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )

        response = bedrock.invoke_model(
            modelId=settings.bedrock_model_id,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
            }),
        )

        response_body = json.loads(response["body"].read())
        ai_text = response_body.get("content", [{}])[0].get("text", "{}")

        # Parse AI response
        try:
            ai_result = json.loads(ai_text)
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            import re
            json_match = re.search(r"\{.*\}", ai_text, re.DOTALL)
            if json_match:
                ai_result = json.loads(json_match.group())
            else:
                ai_result = {
                    "ai_assessment": ai_text,
                    "compliance_score": rule_based_result.get("compliance_score", 0) if rule_based_result else 0,
                    "recommendations": [],
                    "missing_elements": [],
                    "narrative_suggestions": [],
                }

        # Merge rule-based and AI results
        return {
            "auth_request_id": auth_request_id,
            "procedure_key": procedure_key,
            "procedure_name": procedure_info["name"] if procedure_info else "Unknown",
            "rule_based_score": rule_based_result.get("compliance_score", 0) if rule_based_result else None,
            "ai_compliance_score": ai_result.get("compliance_score", 0),
            "combined_score": _combine_scores(
                rule_based_result.get("compliance_score") if rule_based_result else None,
                ai_result.get("compliance_score")),
            "ai_assessment": ai_result.get("ai_assessment", ""),
            "agrees_with_rule_check": ai_result.get("agrees_with_rule_check", True),
            "recommendations": ai_result.get("recommendations", []),
            "missing_elements": ai_result.get("missing_elements", []),
            "narrative_suggestions": ai_result.get("narrative_suggestions", []),
            "risk_factors": ai_result.get("risk_factors", []),
            "mtg_citations": ai_result.get("mtg_citations", []),
            "rule_based_checklist": rule_based_result.get("checklist", []) if rule_based_result else [],
            "rule_based_recommendations": rule_based_result.get("recommendations", []) if rule_based_result else [],
        }

    except Exception as e:
        logger.error(f"AI compliance review failed: {e}")
        # Return rule-based result as fallback
        return {
            "auth_request_id": auth_request_id,
            "procedure_key": procedure_key,
            "procedure_name": procedure_info["name"] if procedure_info else "Unknown",
            "rule_based_score": rule_based_result.get("compliance_score", 0) if rule_based_result else None,
            "ai_compliance_score": None,
            "combined_score": rule_based_result.get("compliance_score", 0) if rule_based_result else 0,
            "ai_assessment": f"AI review unavailable: {str(e)}. See rule-based assessment below.",
            "recommendations": rule_based_result.get("recommendations", []) if rule_based_result else [],
            "missing_elements": rule_based_result.get("missing_critical", []) if rule_based_result else [],
            "narrative_suggestions": [],
            "risk_factors": [],
            "mtg_citations": [rule_based_result.get("mtg_reference", "")] if rule_based_result else [],
            "rule_based_checklist": rule_based_result.get("checklist", []) if rule_based_result else [],
            "rule_based_recommendations": rule_based_result.get("recommendations", []) if rule_based_result else [],
            "ai_error": str(e),
        }


# =============================================================================
# Internal helpers
# =============================================================================

def _combine_scores(rule_score: int | None, ai_score: int | None) -> int:
    """Combine rule-based and AI scores. Rule-based gets 60% weight, AI 40%."""
    if rule_score is not None and ai_score is not None:
        return round(rule_score * 0.6 + ai_score * 0.4)
    elif rule_score is not None:
        return rule_score
    elif ai_score is not None:
        return ai_score
    return 0


def _infer_procedure_from_data(form_data: dict, extracted_data: dict) -> str | None:
    """Attempt to infer the procedure key from submission data."""
    # Check for CPT codes
    cpt_codes = (
        form_data.get("cpt_codes", [])
        or extracted_data.get("cpt_codes", [])
        or []
    )

    for cpt in cpt_codes:
        matches = find_procedures_by_cpt(str(cpt))
        if matches:
            return matches[0][1]  # Return first matching procedure key

    # Check for procedure name mentions
    procedure_name = (
        form_data.get("procedure_name", "")
        or extracted_data.get("procedure_name", "")
        or form_data.get("treatment_requested", "")
        or extracted_data.get("treatment_requested", "")
        or ""
    )

    if procedure_name:
        results = search_procedure(procedure_name)
        if results:
            return results[0]["procedure_key"]

    return None


def _build_auth_data_from_submission(form_data: dict, extracted_data: dict) -> dict:
    """Build the auth_data dict expected by check_compliance from submission data."""
    # Merge form_data and extracted_data, preferring extracted (more structured)
    merged = {**form_data, **extracted_data}

    return {
        "conservative_treatments": merged.get("conservative_treatments", []),
        "medications": merged.get("medications", []),
        "injections": merged.get("injections", []),
        "imaging": merged.get("imaging", []),
        "diagnostics": merged.get("diagnostics", []),
        "functional_scores": merged.get("functional_scores", {}),
        "symptom_duration_weeks": merged.get("symptom_duration_weeks", 0),
        "work_status": merged.get("work_status", ""),
        "clinical_findings": merged.get("clinical_findings", []),
        "diagnosis_codes": merged.get("diagnosis_codes", []),
    }
