"""Compliance & MTG Guidelines Router — check auth requests against WCB treatment guidelines."""

import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from pydantic import BaseModel

from ..database import get_db
from ..middleware.auth import get_current_user
from ..models.provider_auth import AuthRequest, AuthDocument

router = APIRouter(prefix="/compliance", tags=["compliance"])


class ComplianceCheckRequest(BaseModel):
    procedure_key: str
    conservative_treatments: list[dict] = []
    medications: list[dict] = []
    injections: list[dict] = []
    imaging: list[dict] = []
    diagnostics: list[dict] = []
    functional_scores: dict = {}
    symptom_duration_weeks: int = 0
    work_status: str = ""
    clinical_findings: list[str] = []
    diagnosis_codes: list[str] = []


# ── Procedure Library ────────────────────────────────────────────────────────

@router.get("/procedures/")
async def list_procedures(
    category: Optional[str] = None,
    user=Depends(get_current_user),
):
    """List all procedures with MTG requirements summary."""
    from ..services.mtg_guidelines import WCB_TREATMENT_GUIDELINES
    from ..services.compliance_checker import get_all_procedures
    procs = get_all_procedures()
    if category:
        procs = [p for p in procs if p["category"].lower() == category.lower()]
    return {"procedures": procs, "total": len(procs)}


@router.get("/procedures/{procedure_key}/")
async def get_procedure_detail(
    procedure_key: str,
    user=Depends(get_current_user),
):
    """Get full MTG requirements for a specific procedure."""
    from ..services.compliance_checker import get_procedure_requirements
    reqs = get_procedure_requirements(procedure_key)
    if not reqs:
        return {"error": f"Procedure '{procedure_key}' not found"}
    return reqs


@router.get("/procedures/search/")
async def search_procedures(
    q: str = Query(..., min_length=2),
    user=Depends(get_current_user),
):
    """Search procedures by name, CPT code, or ICD-10."""
    from ..services.compliance_checker import search_procedure
    return {"results": search_procedure(q)}


# ── Compliance Checking ──────────────────────────────────────────────────────

@router.post("/check/")
async def check_compliance(
    body: ComplianceCheckRequest,
    user=Depends(get_current_user),
):
    """Check compliance against MTG guidelines for a procedure."""
    from ..services.compliance_checker import check_compliance, calculate_approval_probability
    result = check_compliance(body.model_dump(), body.procedure_key)
    probability = calculate_approval_probability(result)
    return {**result, "approval_detail": probability}


@router.post("/check-auth/{auth_request_id}/")
async def check_auth_compliance(
    auth_request_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check an existing auth request against MTG guidelines using its documents."""
    # Get auth request
    auth = (await db.execute(
        select(AuthRequest).where(AuthRequest.id == uuid.UUID(auth_request_id))
    )).scalar_one_or_none()
    if not auth:
        return {"error": "Auth request not found"}

    # Get documents with extracted data
    docs = (await db.execute(
        select(AuthDocument).where(AuthDocument.auth_request_id == auth.id)
    )).scalars().all()

    # Build compliance data from extracted document data
    auth_data = _build_compliance_data_from_auth(auth, docs)

    # Determine procedure key from proposed procedure
    from ..services.compliance_checker import search_procedure, check_compliance, calculate_approval_probability
    procedure_key = _match_procedure(auth.proposed_procedure, auth.proposed_cpt_codes)

    if not procedure_key:
        return {"error": f"Could not match procedure '{auth.proposed_procedure}' to MTG guidelines", "suggestion": "Use /compliance/procedures/search/ to find the correct procedure key"}

    result = check_compliance(auth_data, procedure_key)
    probability = calculate_approval_probability(result)
    return {**result, "approval_detail": probability, "auth_request_id": auth_request_id}


@router.post("/ai-review/{auth_request_id}/")
async def ai_compliance_review(
    auth_request_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deep AI review of an auth request against MTG guidelines."""
    from ..services.compliance_checker import ai_compliance_review
    return await ai_compliance_review(auth_request_id, db)


# ── Guidelines Reference ────────────────────────────────────────────────────

@router.get("/guidelines/")
async def list_guideline_categories(user=Depends(get_current_user)):
    """List guideline categories (spine, orthopedic, concussion)."""
    from ..services.mtg_guidelines import WCB_TREATMENT_GUIDELINES
    return [
        {
            "key": k,
            "name": v["category"],
            "procedure_count": len(v["procedures"]),
            "procedures": list(v["procedures"].keys()),
        }
        for k, v in WCB_TREATMENT_GUIDELINES.items()
    ]


@router.get("/guidelines/{category}/")
async def get_guideline_category(category: str, user=Depends(get_current_user)):
    """Get all procedures and their MTG requirements for a category."""
    from ..services.mtg_guidelines import WCB_TREATMENT_GUIDELINES
    cat = WCB_TREATMENT_GUIDELINES.get(category)
    if not cat:
        return {"error": f"Category '{category}' not found. Use: spine, orthopedic, concussion"}
    return {
        "category": cat["category"],
        "procedures": {
            k: {
                "name": v["name"],
                "cpt_codes": v.get("cpt_codes", []),
                "conservative_duration_weeks": v.get("conservative_requirements", {}).get("total_conservative_duration_weeks", 0),
                "imaging_required": v.get("imaging_requirements", {}).get("required", []),
                "clinical_criteria_count": len(v.get("clinical_criteria", [])),
            }
            for k, v in cat["procedures"].items()
        },
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _build_compliance_data_from_auth(auth: AuthRequest, docs: list) -> dict:
    """Extract compliance-checkable data from an auth request and its documents."""
    data = {
        "conservative_treatments": [],
        "medications": [],
        "injections": [],
        "imaging": [],
        "diagnostics": [],
        "functional_scores": {},
        "symptom_duration_weeks": 0,
        "work_status": "",
        "clinical_findings": [],
        "diagnosis_codes": auth.diagnosis_codes.split(",") if auth.diagnosis_codes else [],
    }

    for doc in docs:
        ext = doc.extracted_data or {}

        if doc.doc_type == "pt_records":
            sessions = ext.get("sessions_completed", 0)
            weeks = ext.get("duration_weeks", 0)
            data["conservative_treatments"].append({"type": "physical_therapy", "duration_weeks": weeks, "sessions": sessions, "outcome": ext.get("outcome", "")})

        elif doc.doc_type in ("mri_report", "ct_report", "xray_report"):
            data["imaging"].append({"type": doc.doc_type.replace("_report", "").upper(), "date": ext.get("date", ""), "findings": ext.get("findings", "")})

        elif doc.doc_type == "injection_records":
            for inj in ext.get("injections", [ext]):
                data["injections"].append({"type": inj.get("type", ""), "date": inj.get("date", ""), "response": inj.get("response", "")})

        elif doc.doc_type == "emg_report":
            data["diagnostics"].append({"type": "EMG_NCS", "date": ext.get("date", ""), "findings": ext.get("findings", "")})

        elif doc.doc_type == "prom_scores":
            if ext.get("odi"): data["functional_scores"]["odi"] = ext["odi"]
            if ext.get("ndi"): data["functional_scores"]["ndi"] = ext["ndi"]
            if ext.get("vas"): data["functional_scores"]["vas"] = ext["vas"]
            if ext.get("dash"): data["functional_scores"]["dash"] = ext["dash"]

        elif doc.doc_type == "medication_history":
            for med in ext.get("medications", []):
                data["medications"].append({"name": med.get("name", ""), "class": med.get("class", ""), "duration_weeks": med.get("duration_weeks", 0)})

        elif doc.doc_type == "clinical_note":
            data["symptom_duration_weeks"] = max(data["symptom_duration_weeks"], ext.get("symptom_duration_weeks", 0))
            data["work_status"] = ext.get("work_status", data["work_status"])
            data["clinical_findings"].extend(ext.get("findings", []))

    return data


def _match_procedure(proposed_procedure: str, cpt_codes: str) -> Optional[str]:
    """Match a proposed procedure name or CPT code to a procedure key in the guidelines."""
    from ..services.compliance_checker import search_procedure
    if not proposed_procedure and not cpt_codes:
        return None

    # Try CPT code match first
    if cpt_codes:
        for code in cpt_codes.split(","):
            results = search_procedure(code.strip())
            if results:
                return results[0]["key"]

    # Try name match
    if proposed_procedure:
        results = search_procedure(proposed_procedure)
        if results:
            return results[0]["key"]

    return None
