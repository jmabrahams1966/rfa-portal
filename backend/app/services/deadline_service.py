"""Deadline Engine Service for AIRA.

Calculates filing deadlines based on NY WCB rules, monitors approaching/overdue
deadlines, and generates alert records.
"""

import logging
import uuid
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.models import (
    RFACase,
    RFASubmission,
    RFADocument,
    RFADeadline,
    RFATask,
    RFAAuditLog,
    RFACaseAssignment,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# NY WCB Deadline Rules
# ---------------------------------------------------------------------------

DEADLINE_RULES: list[dict[str, Any]] = [
    {
        "id": "rfa2_after_ime",
        "name": "AIRA After IME Examination",
        "description": "Carrier/employer must file AIRA within 30 days of the IME examination date.",
        "trigger_event": "ime_examination",
        "days": 30,
        "deadline_type": "rfa2_filing",
        "wcb_reference": "12 NYCRR 300.2",
        "applies_to": ["carrier", "tpa", "self_insured"],
    },
    {
        "id": "rfa2_after_board_decision",
        "name": "AIRA After Board Decision",
        "description": "Must file AIRA within 30 days of a Board panel decision or administrative decision.",
        "trigger_event": "board_decision",
        "days": 30,
        "deadline_type": "rfa2_filing",
        "wcb_reference": "12 NYCRR 300.2",
        "applies_to": ["carrier", "tpa", "self_insured"],
    },
    {
        "id": "rfa2_treatment_denial",
        "name": "Medical Treatment Dispute Filing",
        "description": "AIRA must be filed within 30 days of the denial of medical treatment request.",
        "trigger_event": "treatment_denial",
        "days": 30,
        "deadline_type": "rfa2_filing",
        "wcb_reference": "WCL Section 13-a",
        "applies_to": ["carrier", "tpa", "self_insured"],
    },
    {
        "id": "section_300_23b_suspension",
        "name": "Section 300.23(b) Payment Suspension",
        "description": "Carrier must file AIRA before suspending indemnity payments. AIRA is a prerequisite for Section 300.23(b) suspension.",
        "trigger_event": "payment_suspension_intended",
        "days": 0,
        "deadline_type": "rfa2_prerequisite",
        "wcb_reference": "12 NYCRR 300.23(b)",
        "applies_to": ["carrier", "tpa", "self_insured"],
    },
    {
        "id": "ime_scheduling",
        "name": "IME Scheduling Deadline",
        "description": "IME must be scheduled within 60 days of the request being made.",
        "trigger_event": "ime_request",
        "days": 60,
        "deadline_type": "ime_scheduling",
        "wcb_reference": "12 NYCRR 300.2",
        "applies_to": ["carrier", "tpa", "self_insured"],
    },
]

# Alert thresholds (days before due date)
ALERT_THRESHOLDS = [
    {"days_before": 7, "level": "upcoming"},
    {"days_before": 3, "level": "due_soon"},
    {"days_before": 1, "level": "due_soon"},
    {"days_before": 0, "level": "overdue"},
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_deadline_status(due_date: date) -> str:
    """Compute deadline status based on due date relative to today."""
    today = date.today()
    days_remaining = (due_date - today).days

    if days_remaining < 0:
        return "overdue"
    elif days_remaining <= 3:
        return "due_soon"
    else:
        return "upcoming"


def _find_trigger_dates_from_documents(
    documents: list[Any],
    form_data: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Extract trigger events from documents and form data.

    Looks for IME reports, board decisions, treatment denials, etc.
    based on document types and form_data metadata.
    """
    triggers: list[dict[str, Any]] = []
    fd = form_data or {}

    for doc in documents:
        doc_type = doc.doc_type if hasattr(doc, "doc_type") else str(doc.get("doc_type", ""))
        created = doc.created_at if hasattr(doc, "created_at") else None

        if doc_type == "ime_report":
            # Use the document upload date as proxy for IME date;
            # in production, parse the actual IME exam date from extracted text
            ime_date = fd.get("ime_examination_date") or fd.get("ime_date")
            if ime_date:
                try:
                    from datetime import datetime
                    trigger_date = datetime.strptime(str(ime_date), "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    trigger_date = created.date() if created and hasattr(created, "date") else date.today()
            else:
                trigger_date = created.date() if created and hasattr(created, "date") else date.today()

            triggers.append({
                "trigger_event": "ime_examination",
                "trigger_date": trigger_date,
                "source": f"IME report: {doc.file_name if hasattr(doc, 'file_name') else 'unknown'}",
            })

        elif doc_type == "board_decision":
            decision_date = fd.get("board_decision_date")
            if decision_date:
                try:
                    from datetime import datetime
                    trigger_date = datetime.strptime(str(decision_date), "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    trigger_date = created.date() if created and hasattr(created, "date") else date.today()
            else:
                trigger_date = created.date() if created and hasattr(created, "date") else date.today()

            triggers.append({
                "trigger_event": "board_decision",
                "trigger_date": trigger_date,
                "source": f"Board decision: {doc.file_name if hasattr(doc, 'file_name') else 'unknown'}",
            })

    # Check form_data for explicit trigger dates
    if fd.get("treatment_denial_date"):
        try:
            from datetime import datetime
            denial_date = datetime.strptime(str(fd["treatment_denial_date"]), "%Y-%m-%d").date()
            triggers.append({
                "trigger_event": "treatment_denial",
                "trigger_date": denial_date,
                "source": "Form data: treatment denial date",
            })
        except (ValueError, TypeError):
            pass

    if fd.get("ime_request_date"):
        try:
            from datetime import datetime
            req_date = datetime.strptime(str(fd["ime_request_date"]), "%Y-%m-%d").date()
            triggers.append({
                "trigger_event": "ime_request",
                "trigger_date": req_date,
                "source": "Form data: IME request date",
            })
        except (ValueError, TypeError):
            pass

    if fd.get("payment_suspension_intended_date"):
        try:
            from datetime import datetime
            susp_date = datetime.strptime(str(fd["payment_suspension_intended_date"]), "%Y-%m-%d").date()
            triggers.append({
                "trigger_event": "payment_suspension_intended",
                "trigger_date": susp_date,
                "source": "Form data: intended payment suspension date",
            })
        except (ValueError, TypeError):
            pass

    return triggers


# ---------------------------------------------------------------------------
# Main Service Functions
# ---------------------------------------------------------------------------

async def calculate_deadlines(
    case_id: uuid.UUID,
    db: AsyncSession,
) -> list[dict[str, Any]]:
    """Calculate all filing deadlines for a case based on trigger events.

    Scans documents and form_data for trigger events (IME date, board decision,
    treatment denial, etc.) and computes deadlines according to NY WCB rules.

    Returns: [{deadline_type, trigger_event, trigger_date, due_date, days_remaining, status}]
    """
    # Load case
    case_result = await db.execute(select(RFACase).where(RFACase.id == case_id))
    case = case_result.scalar_one_or_none()
    if not case:
        return [{"error": "Case not found"}]

    # Load all submissions and their documents for this case
    subs_result = await db.execute(
        select(RFASubmission).where(RFASubmission.case_id == case_id)
    )
    submissions = subs_result.scalars().all()

    all_triggers: list[dict[str, Any]] = []
    all_documents: list[Any] = []

    for sub in submissions:
        # Load documents for each submission
        docs_result = await db.execute(
            select(RFADocument).where(RFADocument.submission_id == sub.id)
        )
        docs = docs_result.scalars().all()
        all_documents.extend(docs)

        fd = sub.form_data if isinstance(sub.form_data, dict) else {}
        triggers = _find_trigger_dates_from_documents(docs, fd)
        all_triggers.extend(triggers)

    # Build deadline rules map
    rules_by_event = {}
    for rule in DEADLINE_RULES:
        rules_by_event[rule["trigger_event"]] = rule

    deadlines: list[dict[str, Any]] = []
    today = date.today()

    for trigger in all_triggers:
        event = trigger["trigger_event"]
        rule = rules_by_event.get(event)
        if not rule:
            continue

        trigger_date = trigger["trigger_date"]
        due_date = trigger_date + timedelta(days=rule["days"]) if rule["days"] > 0 else trigger_date
        days_remaining = (due_date - today).days
        status = _compute_deadline_status(due_date)

        deadline_entry = {
            "deadline_type": rule["deadline_type"],
            "rule_id": rule["id"],
            "rule_name": rule["name"],
            "trigger_event": event,
            "trigger_date": trigger_date.isoformat(),
            "due_date": due_date.isoformat(),
            "days_remaining": days_remaining,
            "status": status,
            "wcb_reference": rule["wcb_reference"],
            "source": trigger.get("source", ""),
        }
        deadlines.append(deadline_entry)

        # Upsert RFADeadline record
        existing_dl = await db.execute(
            select(RFADeadline).where(
                RFADeadline.case_id == case_id,
                RFADeadline.deadline_type == rule["deadline_type"],
                RFADeadline.trigger_event == event,
                RFADeadline.trigger_date == trigger_date,
            )
        )
        dl_record = existing_dl.scalar_one_or_none()

        if dl_record:
            dl_record.due_date = due_date
            dl_record.status = status
        else:
            dl_record = RFADeadline(
                id=uuid.uuid4(),
                case_id=case_id,
                org_id=case.org_id,
                deadline_type=rule["deadline_type"],
                trigger_event=event,
                trigger_date=trigger_date,
                due_date=due_date,
                status=status,
                alert_sent=False,
            )
            db.add(dl_record)

    await db.flush()

    # Sort by due_date ascending
    deadlines.sort(key=lambda d: d["due_date"])
    return deadlines


async def check_all_deadlines(
    org_id: uuid.UUID,
    db: AsyncSession,
) -> dict[str, Any]:
    """Check all cases in the org for approaching/overdue deadlines.

    First recalculates deadlines for all cases, then categorizes them.

    Returns: {
        overdue: [{case_id, wcb_case_number, deadline_type, due_date, days_overdue}],
        due_this_week: [...],
        due_this_month: [...],
        total_checked: int,
    }
    """
    today = date.today()
    end_of_week = today + timedelta(days=7)
    end_of_month = today + timedelta(days=30)

    # Load all cases for org
    cases_result = await db.execute(
        select(RFACase).where(RFACase.org_id == org_id)
    )
    cases = cases_result.scalars().all()

    overdue: list[dict[str, Any]] = []
    due_this_week: list[dict[str, Any]] = []
    due_this_month: list[dict[str, Any]] = []

    for case in cases:
        # Recalculate deadlines for each case
        case_deadlines = await calculate_deadlines(case.id, db)

        for dl in case_deadlines:
            if "error" in dl:
                continue

            due_date_str = dl["due_date"]
            try:
                from datetime import datetime
                due_dt = datetime.strptime(due_date_str, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue

            entry = {
                "case_id": str(case.id),
                "wcb_case_number": case.wcb_case_number,
                "deadline_type": dl["deadline_type"],
                "rule_name": dl.get("rule_name", ""),
                "trigger_event": dl["trigger_event"],
                "due_date": due_date_str,
                "days_remaining": dl["days_remaining"],
                "status": dl["status"],
            }

            if due_dt < today:
                entry["days_overdue"] = (today - due_dt).days
                overdue.append(entry)
            elif due_dt <= end_of_week:
                due_this_week.append(entry)
            elif due_dt <= end_of_month:
                due_this_month.append(entry)

    return {
        "overdue": overdue,
        "due_this_week": due_this_week,
        "due_this_month": due_this_month,
        "total_checked": len(cases),
        "checked_at": today.isoformat(),
    }


async def send_deadline_alerts(
    org_id: uuid.UUID,
    db: AsyncSession,
) -> dict[str, Any]:
    """Generate alert records for approaching deadlines.

    Creates RFATask entries for deadlines at 7-day, 3-day, 1-day, and overdue thresholds.
    Only creates alerts if not already sent (checks alert_sent flag).

    Returns: {alerts_created: int, details: [...]}
    """
    today = date.today()

    # Load all un-alerted deadlines for this org
    deadlines_result = await db.execute(
        select(RFADeadline).where(
            RFADeadline.org_id == org_id,
            RFADeadline.alert_sent == False,
            RFADeadline.status.in_(["upcoming", "due_soon", "overdue"]),
        )
    )
    deadlines = deadlines_result.scalars().all()

    alerts_created = 0
    details: list[dict[str, Any]] = []

    for dl in deadlines:
        days_remaining = (dl.due_date - today).days

        # Determine if we should send an alert at this threshold
        should_alert = False
        alert_level = ""

        if days_remaining < 0:
            should_alert = True
            alert_level = "overdue"
            dl.status = "overdue"
        elif days_remaining <= 1:
            should_alert = True
            alert_level = "due_soon"
            dl.status = "due_soon"
        elif days_remaining <= 3:
            should_alert = True
            alert_level = "due_soon"
            dl.status = "due_soon"
        elif days_remaining <= 7:
            should_alert = True
            alert_level = "upcoming"

        if not should_alert:
            continue

        # Load case for context
        case_result = await db.execute(
            select(RFACase).where(RFACase.id == dl.case_id)
        )
        case = case_result.scalar_one_or_none()
        case_number = case.wcb_case_number if case else "Unknown"

        # Find assigned adjuster
        assignment_result = await db.execute(
            select(RFACaseAssignment).where(
                RFACaseAssignment.case_id == dl.case_id,
                RFACaseAssignment.status == "active",
            ).limit(1)
        )
        assignment = assignment_result.scalar_one_or_none()
        assigned_to = assignment.assigned_to if assignment else None

        # Determine priority
        if days_remaining < 0:
            priority = "urgent"
            title = f"OVERDUE: {dl.deadline_type} deadline for case {case_number}"
            desc = f"Deadline was {abs(days_remaining)} day(s) ago on {dl.due_date.strftime('%m/%d/%Y')}. Trigger: {dl.trigger_event}."
        elif days_remaining <= 1:
            priority = "urgent"
            title = f"DUE TOMORROW: {dl.deadline_type} deadline for case {case_number}"
            desc = f"Deadline is {dl.due_date.strftime('%m/%d/%Y')}. Trigger: {dl.trigger_event}."
        elif days_remaining <= 3:
            priority = "high"
            title = f"DUE SOON: {dl.deadline_type} deadline for case {case_number} ({days_remaining} days)"
            desc = f"Deadline is {dl.due_date.strftime('%m/%d/%Y')} ({days_remaining} days remaining). Trigger: {dl.trigger_event}."
        else:
            priority = "medium"
            title = f"Upcoming: {dl.deadline_type} deadline for case {case_number} ({days_remaining} days)"
            desc = f"Deadline is {dl.due_date.strftime('%m/%d/%Y')} ({days_remaining} days remaining). Trigger: {dl.trigger_event}."

        # Create alert task
        task = RFATask(
            id=uuid.uuid4(),
            case_id=dl.case_id,
            org_id=org_id,
            assigned_to=assigned_to,
            task_type="deadline_approaching",
            title=title,
            description=desc,
            due_date=dl.due_date,
            priority=priority,
            status="pending",
        )
        db.add(task)

        # Mark deadline as alerted
        dl.alert_sent = True

        alerts_created += 1
        details.append({
            "deadline_id": str(dl.id),
            "case_id": str(dl.case_id),
            "wcb_case_number": case_number,
            "deadline_type": dl.deadline_type,
            "due_date": dl.due_date.isoformat(),
            "days_remaining": days_remaining,
            "alert_level": alert_level,
            "priority": priority,
            "task_id": str(task.id),
        })

    # Audit log
    if alerts_created > 0:
        audit = RFAAuditLog(
            id=uuid.uuid4(),
            org_id=org_id,
            action="deadline_alerts_sent",
            resource_type="deadline",
            description=f"Generated {alerts_created} deadline alerts",
        )
        db.add(audit)

    await db.flush()

    return {
        "alerts_created": alerts_created,
        "details": details,
        "checked_at": today.isoformat(),
    }


def get_deadline_rules() -> list[dict[str, Any]]:
    """Return all deadline rules with trigger events and timeframes.

    Returns the full NY WCB deadline rule set used by the deadline engine.
    """
    return [
        {
            "id": rule["id"],
            "name": rule["name"],
            "description": rule["description"],
            "trigger_event": rule["trigger_event"],
            "days": rule["days"],
            "deadline_type": rule["deadline_type"],
            "wcb_reference": rule["wcb_reference"],
            "applies_to": rule["applies_to"],
        }
        for rule in DEADLINE_RULES
    ]
