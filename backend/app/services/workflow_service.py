"""Team Workflow & Assignment Service for RFA-2 Portal.

Handles case assignment to adjusters, review/approval workflows,
workload dashboards, and activity logging.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, func, and_, or_, case as sql_case
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.models import (
    RFACase,
    RFASubmission,
    RFAUser,
    RFACaseAssignment,
    RFAAuditLog,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Submission review statuses stored in form_data JSON
# ---------------------------------------------------------------------------
# form_data["review_status"]: pending_review | approved | rejected | draft
# form_data["assigned_to"]: user_id (UUID string)
# form_data["reviewer_id"]: user_id of reviewer
# form_data["review_notes"]: text notes from reviewer
# form_data["review_history"]: list of {action, by, at, notes}


def _get_form_data(submission: RFASubmission) -> dict[str, Any]:
    """Safely get form_data as a dict."""
    if submission.form_data and isinstance(submission.form_data, dict):
        return dict(submission.form_data)
    return {}


def _set_form_data(submission: RFASubmission, data: dict[str, Any]) -> None:
    """Set form_data on a submission."""
    submission.form_data = data


# ---------------------------------------------------------------------------
# Case Assignment
# ---------------------------------------------------------------------------

async def assign_case(
    case_id: uuid.UUID,
    adjuster_id: uuid.UUID,
    assigned_by: uuid.UUID,
    db: AsyncSession,
) -> dict[str, Any]:
    """Assign a case to an adjuster.

    If already assigned, marks the old assignment as 'reassigned' and creates a new one.

    Returns: {assignment_id, case_id, assigned_to, assigned_by, status}
    """
    # Verify case exists
    case_result = await db.execute(select(RFACase).where(RFACase.id == case_id))
    case = case_result.scalar_one_or_none()
    if not case:
        return {"error": "Case not found", "case_id": str(case_id)}

    # Verify adjuster exists and is active
    adjuster_result = await db.execute(
        select(RFAUser).where(RFAUser.id == adjuster_id, RFAUser.is_active == True)
    )
    adjuster = adjuster_result.scalar_one_or_none()
    if not adjuster:
        return {"error": "Adjuster not found or inactive", "adjuster_id": str(adjuster_id)}

    # Mark any existing active assignments as reassigned
    existing_result = await db.execute(
        select(RFACaseAssignment).where(
            RFACaseAssignment.case_id == case_id,
            RFACaseAssignment.status == "active",
        )
    )
    for old_assignment in existing_result.scalars().all():
        old_assignment.status = "reassigned"

    # Create new assignment
    assignment = RFACaseAssignment(
        id=uuid.uuid4(),
        case_id=case_id,
        org_id=case.org_id,
        assigned_to=adjuster_id,
        assigned_by=assigned_by,
        status="active",
    )
    db.add(assignment)

    # Update any submissions for this case to reflect assignment in form_data
    sub_result = await db.execute(
        select(RFASubmission).where(RFASubmission.case_id == case_id)
    )
    for sub in sub_result.scalars().all():
        fd = _get_form_data(sub)
        fd["assigned_to"] = str(adjuster_id)
        _set_form_data(sub, fd)

    # Audit log
    audit = RFAAuditLog(
        id=uuid.uuid4(),
        org_id=case.org_id,
        user_id=assigned_by,
        action="case_assigned",
        resource_type="case",
        resource_id=case_id,
        description=f"Case {case.wcb_case_number} assigned to {adjuster.full_name} ({adjuster.email})",
    )
    db.add(audit)
    await db.flush()

    return {
        "assignment_id": str(assignment.id),
        "case_id": str(case_id),
        "wcb_case_number": case.wcb_case_number,
        "assigned_to": str(adjuster_id),
        "assigned_to_name": adjuster.full_name,
        "assigned_by": str(assigned_by),
        "status": "active",
    }


# ---------------------------------------------------------------------------
# Review Workflow
# ---------------------------------------------------------------------------

async def submit_for_review(
    submission_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> dict[str, Any]:
    """Adjuster submits a draft for supervisor approval.

    Returns: {submission_id, review_status, submitted_by}
    """
    result = await db.execute(
        select(RFASubmission).where(RFASubmission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        return {"error": "Submission not found"}

    if submission.status not in ("draft", "validated"):
        return {"error": f"Cannot submit for review from status: {submission.status}"}

    fd = _get_form_data(submission)

    # Check assignment
    if fd.get("assigned_to") and fd["assigned_to"] != str(user_id):
        return {"error": "Only the assigned adjuster can submit for review"}

    # Update review status
    review_history = fd.get("review_history", [])
    review_history.append({
        "action": "submitted_for_review",
        "by": str(user_id),
        "at": datetime.utcnow().isoformat(),
    })

    fd["review_status"] = "pending_review"
    fd["submitted_for_review_by"] = str(user_id)
    fd["submitted_for_review_at"] = datetime.utcnow().isoformat()
    fd["review_history"] = review_history
    _set_form_data(submission, fd)

    # Audit
    audit = RFAAuditLog(
        id=uuid.uuid4(),
        org_id=submission.org_id,
        user_id=user_id,
        action="submission_submitted_for_review",
        resource_type="submission",
        resource_id=submission_id,
        description=f"Submission {submission_id} submitted for supervisor review",
    )
    db.add(audit)
    await db.flush()

    return {
        "submission_id": str(submission_id),
        "review_status": "pending_review",
        "submitted_by": str(user_id),
    }


async def approve_submission(
    submission_id: uuid.UUID,
    reviewer_id: uuid.UUID,
    notes: str | None,
    db: AsyncSession,
) -> dict[str, Any]:
    """Supervisor approves a submission for WCB filing.

    Returns: {submission_id, review_status, approved_by, notes}
    """
    result = await db.execute(
        select(RFASubmission).where(RFASubmission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        return {"error": "Submission not found"}

    fd = _get_form_data(submission)

    if fd.get("review_status") != "pending_review":
        return {"error": f"Submission is not pending review (current: {fd.get('review_status', 'none')})"}

    # Verify reviewer has appropriate role
    reviewer_result = await db.execute(
        select(RFAUser).where(RFAUser.id == reviewer_id)
    )
    reviewer = reviewer_result.scalar_one_or_none()
    if not reviewer:
        return {"error": "Reviewer not found"}
    if reviewer.role not in ("admin", "reviewer"):
        return {"error": "Only admins and reviewers can approve submissions"}

    review_history = fd.get("review_history", [])
    review_history.append({
        "action": "approved",
        "by": str(reviewer_id),
        "at": datetime.utcnow().isoformat(),
        "notes": notes,
    })

    fd["review_status"] = "approved"
    fd["reviewer_id"] = str(reviewer_id)
    fd["review_notes"] = notes
    fd["approved_at"] = datetime.utcnow().isoformat()
    fd["review_history"] = review_history
    _set_form_data(submission, fd)

    # Move submission to validated status (ready for WCB submit)
    submission.status = "validated"

    audit = RFAAuditLog(
        id=uuid.uuid4(),
        org_id=submission.org_id,
        user_id=reviewer_id,
        action="submission_approved",
        resource_type="submission",
        resource_id=submission_id,
        description=f"Submission {submission_id} approved by {reviewer.full_name}" + (f": {notes}" if notes else ""),
    )
    db.add(audit)
    await db.flush()

    return {
        "submission_id": str(submission_id),
        "review_status": "approved",
        "approved_by": str(reviewer_id),
        "approved_by_name": reviewer.full_name,
        "notes": notes,
    }


async def reject_submission(
    submission_id: uuid.UUID,
    reviewer_id: uuid.UUID,
    reason: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """Supervisor sends a submission back for corrections.

    Returns: {submission_id, review_status, rejected_by, reason}
    """
    result = await db.execute(
        select(RFASubmission).where(RFASubmission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        return {"error": "Submission not found"}

    fd = _get_form_data(submission)

    if fd.get("review_status") != "pending_review":
        return {"error": f"Submission is not pending review (current: {fd.get('review_status', 'none')})"}

    reviewer_result = await db.execute(
        select(RFAUser).where(RFAUser.id == reviewer_id)
    )
    reviewer = reviewer_result.scalar_one_or_none()
    if not reviewer:
        return {"error": "Reviewer not found"}
    if reviewer.role not in ("admin", "reviewer"):
        return {"error": "Only admins and reviewers can reject submissions"}

    review_history = fd.get("review_history", [])
    review_history.append({
        "action": "rejected",
        "by": str(reviewer_id),
        "at": datetime.utcnow().isoformat(),
        "reason": reason,
    })

    fd["review_status"] = "rejected"
    fd["reviewer_id"] = str(reviewer_id)
    fd["rejection_reason"] = reason
    fd["rejected_at"] = datetime.utcnow().isoformat()
    fd["review_history"] = review_history
    _set_form_data(submission, fd)

    # Reset submission back to draft
    submission.status = "draft"

    audit = RFAAuditLog(
        id=uuid.uuid4(),
        org_id=submission.org_id,
        user_id=reviewer_id,
        action="submission_rejected",
        resource_type="submission",
        resource_id=submission_id,
        description=f"Submission {submission_id} rejected by {reviewer.full_name}: {reason}",
    )
    db.add(audit)
    await db.flush()

    return {
        "submission_id": str(submission_id),
        "review_status": "rejected",
        "rejected_by": str(reviewer_id),
        "rejected_by_name": reviewer.full_name,
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# Workload Dashboard
# ---------------------------------------------------------------------------

async def get_workload_dashboard(
    org_id: uuid.UUID,
    db: AsyncSession,
) -> dict[str, Any]:
    """Get workload dashboard: cases per adjuster, pending reviews, overdue items.

    Returns: {
        adjusters: [{user_id, name, active_cases, pending_reviews, total_submissions}],
        summary: {total_cases, total_submissions, pending_reviews, drafts, submitted, overdue_count},
    }
    """
    # Get all adjusters in org
    users_result = await db.execute(
        select(RFAUser).where(
            RFAUser.org_id == org_id,
            RFAUser.is_active == True,
        )
    )
    users = users_result.scalars().all()

    adjuster_stats: list[dict[str, Any]] = []

    for user in users:
        # Count active case assignments
        assignment_count = await db.execute(
            select(func.count(RFACaseAssignment.id)).where(
                RFACaseAssignment.org_id == org_id,
                RFACaseAssignment.assigned_to == user.id,
                RFACaseAssignment.status == "active",
            )
        )
        active_cases = assignment_count.scalar() or 0

        # Count submissions created by this user
        sub_count = await db.execute(
            select(func.count(RFASubmission.id)).where(
                RFASubmission.org_id == org_id,
                RFASubmission.created_by == user.id,
            )
        )
        total_submissions = sub_count.scalar() or 0

        # Count pending reviews (submissions where form_data has review_status = pending_review
        # and created_by this user)
        pending_result = await db.execute(
            select(RFASubmission).where(
                RFASubmission.org_id == org_id,
                RFASubmission.created_by == user.id,
            )
        )
        pending_reviews = 0
        for sub in pending_result.scalars().all():
            fd = _get_form_data(sub)
            if fd.get("review_status") == "pending_review":
                pending_reviews += 1

        adjuster_stats.append({
            "user_id": str(user.id),
            "name": user.full_name,
            "email": user.email,
            "role": user.role,
            "active_cases": active_cases,
            "pending_reviews": pending_reviews,
            "total_submissions": total_submissions,
        })

    # Org-level summary
    total_cases_result = await db.execute(
        select(func.count(RFACase.id)).where(RFACase.org_id == org_id)
    )
    total_cases = total_cases_result.scalar() or 0

    total_subs_result = await db.execute(
        select(func.count(RFASubmission.id)).where(RFASubmission.org_id == org_id)
    )
    total_submissions = total_subs_result.scalar() or 0

    # Count by status
    status_result = await db.execute(
        select(RFASubmission.status, func.count(RFASubmission.id))
        .where(RFASubmission.org_id == org_id)
        .group_by(RFASubmission.status)
    )
    status_counts = {row[0]: row[1] for row in status_result.all()}

    # Pending reviews across org
    all_subs = await db.execute(
        select(RFASubmission).where(RFASubmission.org_id == org_id)
    )
    total_pending = sum(
        1 for s in all_subs.scalars().all()
        if _get_form_data(s).get("review_status") == "pending_review"
    )

    return {
        "adjusters": adjuster_stats,
        "summary": {
            "total_cases": total_cases,
            "total_submissions": total_submissions,
            "pending_reviews": total_pending,
            "drafts": status_counts.get("draft", 0),
            "validated": status_counts.get("validated", 0),
            "submitted": status_counts.get("submitted", 0),
            "accepted": status_counts.get("accepted", 0),
            "rejected": status_counts.get("rejected", 0),
        },
    }


# ---------------------------------------------------------------------------
# Activity Log
# ---------------------------------------------------------------------------

async def get_activity_log(
    org_id: uuid.UUID,
    user_id: uuid.UUID | None,
    db: AsyncSession,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Recent actions by user (or all users if user_id is None).

    Returns: [{id, action, resource_type, resource_id, description, user_id, user_email, created_at}]
    """
    query = select(RFAAuditLog).where(RFAAuditLog.org_id == org_id)

    if user_id:
        query = query.where(RFAAuditLog.user_id == user_id)

    query = query.order_by(RFAAuditLog.created_at.desc()).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        {
            "id": str(log.id),
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": str(log.resource_id) if log.resource_id else None,
            "description": log.description,
            "user_id": str(log.user_id) if log.user_id else None,
            "user_email": log.user_email,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]
