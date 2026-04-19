"""WCB Status Tracking Service for AIRA.

Polls WCB API for status updates (mocked), parses responses,
manages hearing schedules, and creates follow-up tasks.
"""

import logging
import random
import uuid
from datetime import datetime, date, timedelta
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.models import (
    RFACase,
    RFASubmission,
    RFAHearing,
    RFATask,
    RFAAuditLog,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mock WCB response templates
# ---------------------------------------------------------------------------

_MOCK_HEARING_TYPES = [
    "Pre-Hearing Conference",
    "Formal Hearing",
    "Continued Hearing",
    "Medical Evidence Hearing",
    "Stipulation Hearing",
]

_MOCK_JUDGES = [
    "ALJ Sarah Thompson",
    "ALJ Michael Chen",
    "ALJ Patricia Rodriguez",
    "ALJ David Williams",
    "ALJ Jennifer Martinez",
]

_MOCK_LOCATIONS = [
    "NY WCB - Manhattan District Office, 215 W 125th St",
    "NY WCB - Brooklyn District Office, 111 Livingston St",
    "NY WCB - Albany District Office, 100 Broadway Center",
    "NY WCB - Buffalo District Office, 295 Main St",
    "NY WCB - Syracuse District Office, 935 James St",
    "NY WCB - Virtual Hearing Room",
]

_MOCK_REJECTION_REASONS = [
    {"code": "RFA-ERR-001", "message": "Missing required reason code documentation"},
    {"code": "RFA-ERR-002", "message": "Invalid WCB case number format"},
    {"code": "RFA-ERR-003", "message": "IME report not attached or incomplete"},
    {"code": "RFA-ERR-004", "message": "Submission exceeds 30-day filing deadline"},
    {"code": "RFA-ERR-005", "message": "Duplicate submission for same case and reason code"},
    {"code": "RFA-ERR-006", "message": "Missing employer FEIN or carrier code"},
    {"code": "RFA-ERR-007", "message": "Narrative exceeds 500 character limit"},
    {"code": "RFA-ERR-008", "message": "Claimant representative information required for controverted claim"},
]


def _generate_mock_wcb_response(submission: RFASubmission) -> dict[str, Any]:
    """Generate a mock WCB API response for a submission.

    Simulates realistic WCB response patterns:
    - 50% accepted (with hearing scheduled)
    - 20% rejected (with error details)
    - 30% still pending
    """
    roll = random.random()

    if roll < 0.50:
        # Accepted - hearing scheduled
        hearing_date = datetime.utcnow() + timedelta(days=random.randint(14, 90))
        return {
            "status": "accepted",
            "wcb_confirmation": f"WCB-CONF-{uuid.uuid4().hex[:10].upper()}",
            "accepted_at": datetime.utcnow().isoformat(),
            "hearing": {
                "scheduled": True,
                "date": hearing_date.isoformat(),
                "type": random.choice(_MOCK_HEARING_TYPES),
                "location": random.choice(_MOCK_LOCATIONS),
                "judge": random.choice(_MOCK_JUDGES),
            },
            "notes": "AIRA accepted. Hearing scheduled. Parties will be notified.",
        }
    elif roll < 0.70:
        # Rejected
        error = random.choice(_MOCK_REJECTION_REASONS)
        return {
            "status": "rejected",
            "rejected_at": datetime.utcnow().isoformat(),
            "errors": [error],
            "notes": f"AIRA rejected: {error['message']}. You may correct and resubmit.",
            "resubmit_allowed": True,
            "resubmit_deadline": (datetime.utcnow() + timedelta(days=15)).isoformat(),
        }
    else:
        # Still pending
        return {
            "status": "pending",
            "notes": "Submission is being reviewed by the Board. Check back later.",
            "estimated_review_date": (datetime.utcnow() + timedelta(days=random.randint(3, 14))).isoformat(),
        }


# ---------------------------------------------------------------------------
# Main Service Functions
# ---------------------------------------------------------------------------

async def check_wcb_status(
    submission_id: uuid.UUID,
    db: AsyncSession,
) -> dict[str, Any]:
    """Poll WCB API for status update on a submission.

    In production, this calls the real WCB eCase API.
    Currently mocked with realistic responses.

    Returns: {submission_id, previous_status, new_status, response}
    """
    result = await db.execute(
        select(RFASubmission).where(RFASubmission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        return {"error": "Submission not found", "submission_id": str(submission_id)}

    if submission.status not in ("submitted", "pending"):
        return {
            "submission_id": str(submission_id),
            "status": submission.status,
            "message": f"Submission is in '{submission.status}' state, not eligible for status check",
        }

    previous_status = submission.wcb_status or submission.status

    # Mock WCB API call
    response = _generate_mock_wcb_response(submission)

    # Process the response
    parsed = await parse_wcb_response(response, submission_id, db)

    return {
        "submission_id": str(submission_id),
        "previous_status": previous_status,
        "new_status": response["status"],
        "response": response,
        "parsed": parsed,
    }


async def parse_wcb_response(
    response_data: dict[str, Any],
    submission_id: uuid.UUID,
    db: AsyncSession,
) -> dict[str, Any]:
    """Parse a WCB response, update submission status, create follow-up tasks.

    Returns: {updated, hearing_created, tasks_created}
    """
    result = await db.execute(
        select(RFASubmission).where(RFASubmission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        return {"error": "Submission not found"}

    wcb_status = response_data.get("status", "unknown")
    hearing_created = False
    tasks_created: list[str] = []

    # Update submission status
    if wcb_status == "accepted":
        submission.status = "accepted"
        submission.wcb_status = "accepted"
        submission.wcb_errors = None

        # Create hearing if scheduled
        hearing_data = response_data.get("hearing", {})
        if hearing_data.get("scheduled"):
            hearing_date_str = hearing_data.get("date")
            hearing_date = None
            if hearing_date_str:
                try:
                    hearing_date = datetime.fromisoformat(hearing_date_str)
                except (ValueError, TypeError):
                    pass

            hearing = RFAHearing(
                id=uuid.uuid4(),
                case_id=submission.case_id,
                org_id=submission.org_id,
                submission_id=submission.id,
                hearing_date=hearing_date,
                hearing_type=hearing_data.get("type", "Hearing"),
                location=hearing_data.get("location"),
                judge_name=hearing_data.get("judge"),
                status="scheduled",
                notes=response_data.get("notes"),
            )
            db.add(hearing)
            hearing_created = True

            # Create preparation task
            if hearing_date:
                prep_due = (hearing_date - timedelta(days=7)).date()
                task = await create_follow_up_task(
                    case_id=submission.case_id,
                    task_type="prepare_hearing",
                    due_date=prep_due,
                    description=f"Prepare for {hearing_data.get('type', 'hearing')} on {hearing_date.strftime('%m/%d/%Y')} at {hearing_data.get('location', 'TBD')}. Judge: {hearing_data.get('judge', 'TBD')}",
                    org_id=submission.org_id,
                    db=db,
                )
                tasks_created.append(str(task.get("task_id", "")))

    elif wcb_status == "rejected":
        submission.status = "rejected"
        submission.wcb_status = "rejected"
        submission.wcb_errors = response_data.get("errors", [])

        # Create respond/resubmit task
        resubmit_deadline = response_data.get("resubmit_deadline")
        due = None
        if resubmit_deadline:
            try:
                due = datetime.fromisoformat(resubmit_deadline).date()
            except (ValueError, TypeError):
                due = (datetime.utcnow() + timedelta(days=15)).date()
        else:
            due = (datetime.utcnow() + timedelta(days=15)).date()

        errors_summary = "; ".join(
            e.get("message", "") for e in response_data.get("errors", [])
        )
        task = await create_follow_up_task(
            case_id=submission.case_id,
            task_type="respond_objection",
            due_date=due,
            description=f"AIRA rejected: {errors_summary}. Correct and resubmit before {due.strftime('%m/%d/%Y')}.",
            org_id=submission.org_id,
            db=db,
        )
        tasks_created.append(str(task.get("task_id", "")))

    elif wcb_status == "pending":
        submission.wcb_status = "pending"
        # Create a follow-up check task
        check_date = (datetime.utcnow() + timedelta(days=3)).date()
        task = await create_follow_up_task(
            case_id=submission.case_id,
            task_type="file_followup",
            due_date=check_date,
            description="Check WCB status again for pending submission.",
            org_id=submission.org_id,
            db=db,
        )
        tasks_created.append(str(task.get("task_id", "")))

    # Audit
    audit = RFAAuditLog(
        id=uuid.uuid4(),
        org_id=submission.org_id,
        action=f"wcb_status_{wcb_status}",
        resource_type="submission",
        resource_id=submission.id,
        description=f"WCB status update: {wcb_status} for submission {submission.id}",
    )
    db.add(audit)
    await db.flush()

    return {
        "updated": True,
        "new_status": wcb_status,
        "hearing_created": hearing_created,
        "tasks_created": tasks_created,
    }


async def get_hearing_schedule(
    org_id: uuid.UUID,
    db: AsyncSession,
) -> list[dict[str, Any]]:
    """Get all upcoming hearings across all cases for an org.

    Returns hearings ordered by date, including associated case info.
    """
    result = await db.execute(
        select(RFAHearing)
        .where(
            RFAHearing.org_id == org_id,
            RFAHearing.status.in_(["scheduled", "adjourned"]),
        )
        .order_by(RFAHearing.hearing_date.asc())
    )
    hearings = result.scalars().all()

    hearing_list: list[dict[str, Any]] = []

    for h in hearings:
        # Load case info
        case_result = await db.execute(
            select(RFACase).where(RFACase.id == h.case_id)
        )
        case = case_result.scalar_one_or_none()

        days_until = None
        if h.hearing_date:
            delta = h.hearing_date.date() if hasattr(h.hearing_date, "date") else h.hearing_date
            if isinstance(delta, date):
                days_until = (delta - date.today()).days
            else:
                days_until = (h.hearing_date - datetime.utcnow()).days

        hearing_list.append({
            "hearing_id": str(h.id),
            "case_id": str(h.case_id),
            "wcb_case_number": case.wcb_case_number if case else None,
            "claimant_name": case.claimant_name_encrypted if case else None,
            "submission_id": str(h.submission_id) if h.submission_id else None,
            "hearing_date": h.hearing_date.isoformat() if h.hearing_date else None,
            "hearing_type": h.hearing_type,
            "location": h.location,
            "judge_name": h.judge_name,
            "status": h.status,
            "days_until": days_until,
            "notes": h.notes,
        })

    return hearing_list


async def create_follow_up_task(
    case_id: uuid.UUID,
    task_type: str,
    due_date: date,
    description: str,
    org_id: uuid.UUID,
    db: AsyncSession,
) -> dict[str, Any]:
    """Auto-create tasks from WCB responses.

    task_type: prepare_hearing, respond_objection, file_followup, deadline_approaching

    Returns: {task_id, task_type, due_date, title, priority}
    """
    # Generate title based on task type
    title_map = {
        "prepare_hearing": "Prepare for WCB Hearing",
        "respond_objection": "Respond to WCB Rejection / Correct AIRA",
        "file_followup": "Follow Up on Pending WCB Submission",
        "deadline_approaching": "Filing Deadline Approaching",
    }
    title = title_map.get(task_type, f"Task: {task_type}")

    # Determine priority based on urgency
    days_remaining = (due_date - date.today()).days
    if days_remaining <= 1:
        priority = "urgent"
    elif days_remaining <= 3:
        priority = "high"
    elif days_remaining <= 7:
        priority = "medium"
    else:
        priority = "low"

    # Load case to get any assigned adjuster
    case_result = await db.execute(select(RFACase).where(RFACase.id == case_id))
    case = case_result.scalar_one_or_none()

    # Find assigned adjuster from case assignments
    from ..models.models import RFACaseAssignment
    assignment_result = await db.execute(
        select(RFACaseAssignment).where(
            RFACaseAssignment.case_id == case_id,
            RFACaseAssignment.status == "active",
        ).limit(1)
    )
    assignment = assignment_result.scalar_one_or_none()
    assigned_to = assignment.assigned_to if assignment else None

    task = RFATask(
        id=uuid.uuid4(),
        case_id=case_id,
        org_id=org_id,
        assigned_to=assigned_to,
        task_type=task_type,
        title=title,
        description=description,
        due_date=due_date,
        priority=priority,
        status="pending",
    )
    db.add(task)
    await db.flush()

    logger.info(
        "Created task %s (%s) for case %s, due %s, priority %s",
        task.id, task_type, case_id, due_date, priority,
    )

    return {
        "task_id": str(task.id),
        "task_type": task_type,
        "title": title,
        "description": description,
        "due_date": due_date.isoformat(),
        "priority": priority,
        "assigned_to": str(assigned_to) if assigned_to else None,
    }
