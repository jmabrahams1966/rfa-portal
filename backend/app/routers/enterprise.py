"""Enterprise Features Router — bulk ops, analytics, workflow, deadlines, billing, OCR, multi-state."""

import uuid
from datetime import datetime, date
from fastapi import APIRouter, Depends, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from ..database import get_db
from ..middleware.auth import get_current_user, require_admin

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


# ── Bulk Import & Batch Filing ──────────────────────────────────────────────

@router.post("/batch/import")
async def batch_import(file: UploadFile = File(...), user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Import cases from CSV/Excel for batch filing."""
    from ..services.batch_service import import_cases_from_file
    data = await file.read()
    org_id = user.org_id if hasattr(user, 'org_id') else None
    return await import_cases_from_file(data, file.filename, org_id, db)

@router.post("/batch/validate")
async def batch_validate(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from ..services.batch_service import batch_validate
    return await batch_validate(body.get("submission_ids", []), db)

@router.post("/batch/build-xml")
async def batch_build_xml(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from ..services.batch_service import batch_build_xml
    return await batch_build_xml(body.get("submission_ids", []), db)

@router.post("/batch/submit")
async def batch_submit(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from ..services.batch_service import batch_submit
    return await batch_submit(body.get("submission_ids", []), db)


# ── Team Workflow ───────────────────────────────────────────────────────────

@router.post("/workflow/assign")
async def assign_case(body: dict, user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    from ..services.workflow_service import assign_case
    return await assign_case(body["case_id"], body["adjuster_id"], str(user.id), db)

@router.post("/workflow/submit-for-review")
async def submit_for_review(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from ..services.workflow_service import submit_for_review
    return await submit_for_review(body["submission_id"], str(user.id), db)

@router.post("/workflow/approve")
async def approve(body: dict, user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    from ..services.workflow_service import approve_submission
    return await approve_submission(body["submission_id"], str(user.id), body.get("notes"), db)

@router.post("/workflow/reject")
async def reject(body: dict, user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    from ..services.workflow_service import reject_submission
    return await reject_submission(body["submission_id"], str(user.id), body.get("reason"), db)

@router.get("/workflow/dashboard")
async def workload(user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    from ..services.workflow_service import get_workload_dashboard
    org_id = user.org_id if hasattr(user, 'org_id') else None
    return await get_workload_dashboard(org_id, db)


# ── Deadlines ───────────────────────────────────────────────────────────────

@router.get("/deadlines")
async def check_deadlines(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from ..services.deadline_service import check_all_deadlines
    org_id = user.org_id if hasattr(user, 'org_id') else None
    return await check_all_deadlines(org_id, db)

@router.get("/deadlines/case/{case_id}")
async def case_deadlines(case_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from ..services.deadline_service import calculate_deadlines
    return await calculate_deadlines(case_id, db)

@router.post("/deadlines/alerts")
async def send_alerts(user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    from ..services.deadline_service import send_deadline_alerts
    org_id = user.org_id if hasattr(user, 'org_id') else None
    return await send_deadline_alerts(org_id, db)


# ── WCB Status ──────────────────────────────────────────────────────────────

@router.post("/wcb/check-status/{submission_id}")
async def check_status(submission_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from ..services.wcb_status_service import check_wcb_status
    return await check_wcb_status(submission_id, db)

@router.get("/wcb/hearings")
async def hearings(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from ..services.wcb_status_service import get_hearing_schedule
    org_id = user.org_id if hasattr(user, 'org_id') else None
    return await get_hearing_schedule(org_id, db)

@router.post("/wcb/sync")
async def wcb_sync(user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    from ..services.wcb_sync_service import sync_hearing_schedule, sync_board_decisions
    org_id = user.org_id if hasattr(user, 'org_id') else None
    hearings = await sync_hearing_schedule(org_id, db)
    decisions = await sync_board_decisions(org_id, db)
    return {"hearings": hearings, "decisions": decisions}

@router.get("/wcb/case-lifecycle/{case_id}")
async def case_lifecycle(case_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from ..services.wcb_sync_service import get_case_lifecycle
    return await get_case_lifecycle(case_id, db)


# ── Analytics ───────────────────────────────────────────────────────────────

@router.get("/analytics")
async def analytics(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from ..services.analytics_service import get_outcome_analytics
    org_id = user.org_id if hasattr(user, 'org_id') else None
    return await get_outcome_analytics(org_id, db)

@router.get("/analytics/district/{reason_code}")
async def district_comparison(reason_code: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from ..services.analytics_service import get_district_comparison
    org_id = user.org_id if hasattr(user, 'org_id') else None
    return await get_district_comparison(org_id, reason_code, db)

@router.get("/analytics/adjusters")
async def adjuster_performance(user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    from ..services.analytics_service import get_adjuster_performance
    org_id = user.org_id if hasattr(user, 'org_id') else None
    return await get_adjuster_performance(org_id, db)


# ── Narrative AI ────────────────────────────────────────────────────────────

@router.post("/narrative/optimize")
async def optimize_narrative(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from ..services.narrative_service import optimize_narrative
    return await optimize_narrative(body["reason_code"], body.get("district"), body["narrative"], db)

@router.get("/narrative/patterns/{reason_code}")
async def winning_patterns(reason_code: str, district: Optional[str] = None, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from ..services.narrative_service import get_winning_patterns
    return await get_winning_patterns(reason_code, district, db)


# ── Attorney Intelligence ───────────────────────────────────────────────────

@router.get("/attorneys/{attorney_name}")
async def attorney_profile(attorney_name: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from ..services.attorney_service import get_attorney_profile
    return await get_attorney_profile(attorney_name, db)

@router.get("/attorneys")
async def attorney_rankings(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from ..services.attorney_service import get_attorney_rankings
    org_id = user.org_id if hasattr(user, 'org_id') else None
    return await get_attorney_rankings(org_id, db)

@router.post("/attorneys/counter-arguments")
async def counter_arguments(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from ..services.attorney_service import generate_counter_arguments
    return await generate_counter_arguments(body["attorney_name"], body["reason_code"], db)


# ── Document OCR ────────────────────────────────────────────────────────────

@router.post("/ocr/extract")
async def ocr_extract(file: UploadFile = File(...), user=Depends(get_current_user)):
    from ..services.ocr_service import extract_text_from_document
    data = await file.read()
    return await extract_text_from_document(data, file.filename, file.content_type)

@router.post("/ocr/classify")
async def ocr_classify(body: dict, user=Depends(get_current_user)):
    from ..services.ocr_service import classify_document_type
    return await classify_document_type(body["text"])

@router.post("/ocr/structured")
async def ocr_structured(body: dict, user=Depends(get_current_user)):
    from ..services.ocr_service import extract_structured_data
    return await extract_structured_data(body["text"], body["doc_type"])


# ── Compliance ──────────────────────────────────────────────────────────────

@router.get("/compliance")
async def compliance_dashboard(period: str = "month", user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    from ..services.compliance_service import get_compliance_dashboard
    org_id = user.org_id if hasattr(user, 'org_id') else None
    return await get_compliance_dashboard(org_id, db, period)

@router.get("/compliance/report")
async def compliance_report(start: str = None, end: str = None, user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    from ..services.compliance_service import generate_compliance_report
    org_id = user.org_id if hasattr(user, 'org_id') else None
    s = date.fromisoformat(start) if start else date.today().replace(day=1)
    e = date.fromisoformat(end) if end else date.today()
    return await generate_compliance_report(org_id, db, s, e)

@router.get("/compliance/audit")
async def audit_trail(user_id: Optional[str] = None, action: Optional[str] = None, page: int = 1, user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    from ..services.compliance_service import get_audit_trail
    org_id = user.org_id if hasattr(user, 'org_id') else None
    return await get_audit_trail(org_id, db, {"user_id": user_id, "action": action, "page": page})

@router.get("/compliance/soc2")
async def soc2_check(user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    from ..services.compliance_service import check_soc2_requirements
    org_id = user.org_id if hasattr(user, 'org_id') else None
    return await check_soc2_requirements(org_id, db)


# ── Multi-State ─────────────────────────────────────────────────────────────

@router.get("/states")
async def list_states(user=Depends(get_current_user)):
    from ..services.multistate_service import get_supported_states
    return get_supported_states()

@router.get("/states/{state_code}")
async def state_config(state_code: str, user=Depends(get_current_user)):
    from ..services.multistate_service import get_state_config
    return get_state_config(state_code)

@router.get("/states/{state_code}/reason-codes")
async def state_codes(state_code: str, user=Depends(get_current_user)):
    from ..services.multistate_service import get_state_reason_codes
    return get_state_reason_codes(state_code)


# ── Billing ─────────────────────────────────────────────────────────────────

@router.post("/billing/track-time")
async def track_time(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from ..services.billing_service import track_time
    return await track_time(body["case_id"], str(user.id), body["minutes"], body["activity_type"], body.get("notes"), db)

@router.get("/billing/case/{case_id}")
async def case_billing(case_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from ..services.billing_service import get_case_billing
    return await get_case_billing(case_id, db)

@router.post("/billing/invoice")
async def generate_invoice(body: dict, user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    from ..services.billing_service import generate_invoice
    org_id = user.org_id if hasattr(user, 'org_id') else None
    return await generate_invoice(org_id, db, body.get("period_start"), body.get("period_end"), body.get("client_name"))

@router.get("/billing/dashboard")
async def billing_dashboard(user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    from ..services.billing_service import get_billing_dashboard
    org_id = user.org_id if hasattr(user, 'org_id') else None
    return await get_billing_dashboard(org_id, db)

@router.get("/billing/rates")
async def rate_card(user=Depends(get_current_user)):
    from ..services.billing_service import get_rate_card
    org_id = user.org_id if hasattr(user, 'org_id') else None
    return await get_rate_card(org_id)
