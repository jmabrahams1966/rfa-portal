"""
Two-Way WCB Integration Service for AIRA.

Provides functions for pulling data back from the WCB eCase system:
hearing schedules, board decisions, payment orders, and full case lifecycle.
Currently uses mock data; in production these would hit the WCB eCase API.
"""

import uuid
import json
import logging
from datetime import datetime, date, timedelta
from typing import Any

from sqlalchemy import Column, String, Boolean, DateTime, Date, Text, Integer, ForeignKey, Index, JSON, func, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import Base
from ..models.models import (
    RFACase,
    RFASubmission,
    RFAHearing,
    RFATask,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# New Model: RFAPaymentOrder
# ---------------------------------------------------------------------------

class RFAPaymentOrder(Base):
    __tablename__ = "rfa_payment_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("rfa_cases.id"), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("rfa_organizations.id"), nullable=False)
    order_date = Column(Date, nullable=False)
    order_type = Column(String(100), nullable=False)  # payment / award / penalty / reimbursement
    amount = Column(Integer, nullable=True)  # cents to avoid float issues
    frequency = Column(String(50), nullable=True)  # weekly / biweekly / lump_sum / monthly
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    compliance_status = Column(
        String(50), nullable=False, default="pending"
    )  # compliant / non_compliant / pending
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_rfa_payment_orders_case_id", "case_id"),
        Index("ix_rfa_payment_orders_org_id", "org_id"),
        Index("ix_rfa_payment_orders_compliance_status", "compliance_status"),
    )


# ---------------------------------------------------------------------------
# Mock WCB eCase Data Generators
# ---------------------------------------------------------------------------

def _mock_hearing_data(case_number: str) -> list[dict]:
    """Generate mock hearing data as if returned from WCB eCase API."""
    today = date.today()
    return [
        {
            "hearing_id": f"H-{case_number}-001",
            "hearing_date": (today + timedelta(days=14)).isoformat(),
            "hearing_type": "Pre-Trial Conference",
            "location": "NYS WCB - NYC District Office",
            "judge_name": "Hon. Maria Rodriguez",
            "status": "scheduled",
            "notes": "Initial conference to establish issues and schedule.",
        },
        {
            "hearing_id": f"H-{case_number}-002",
            "hearing_date": (today + timedelta(days=45)).isoformat(),
            "hearing_type": "Full Hearing",
            "location": "NYS WCB - NYC District Office",
            "judge_name": "Hon. Maria Rodriguez",
            "status": "scheduled",
            "notes": "Carrier to present IME report. Claimant to present treating physician testimony.",
        },
    ]


def _mock_decision_data(case_number: str) -> list[dict]:
    """Generate mock board decision data."""
    today = date.today()
    return [
        {
            "decision_id": f"D-{case_number}-001",
            "decision_date": (today - timedelta(days=5)).isoformat(),
            "decision_type": "Preliminary Finding",
            "judge_name": "Hon. Maria Rodriguez",
            "outcome": "partially_granted",
            "summary": (
                "Board finds claimant has reached maximum medical improvement "
                "for lumbar spine injury. Permanency hearing to be scheduled. "
                "Temporary disability benefits to continue pending permanency determination."
            ),
            "follow_up_required": True,
            "follow_up_type": "prepare_hearing",
            "follow_up_deadline": (today + timedelta(days=30)).isoformat(),
        },
    ]


def _mock_payment_order_data(case_number: str) -> list[dict]:
    """Generate mock payment order data."""
    today = date.today()
    return [
        {
            "order_id": f"PO-{case_number}-001",
            "order_date": (today - timedelta(days=10)).isoformat(),
            "order_type": "payment",
            "amount_cents": 95000,  # $950.00
            "frequency": "weekly",
            "start_date": (today - timedelta(days=10)).isoformat(),
            "end_date": None,
            "notes": "Temporary total disability benefits at max statutory rate.",
        },
        {
            "order_id": f"PO-{case_number}-002",
            "order_date": (today - timedelta(days=3)).isoformat(),
            "order_type": "reimbursement",
            "amount_cents": 125000,  # $1,250.00
            "frequency": "lump_sum",
            "start_date": (today - timedelta(days=3)).isoformat(),
            "end_date": (today - timedelta(days=3)).isoformat(),
            "notes": "Medical treatment reimbursement for authorized surgery.",
        },
    ]


def _mock_ecase_status(case_number: str) -> dict:
    """Generate mock eCase status data."""
    today = date.today()
    return {
        "case_number": case_number,
        "status": "active",
        "classification": "Lost Time",
        "district": "NYC",
        "judge_assigned": "Hon. Maria Rodriguez",
        "claimant_attorney": "Smith & Associates, P.C.",
        "next_hearing_date": (today + timedelta(days=14)).isoformat(),
        "last_activity": (today - timedelta(days=2)).isoformat(),
        "last_activity_description": "Carrier filed AIRA — Request for Further Action",
        "open_issues": [
            "Degree of disability",
            "Medical treatment authorization",
        ],
        "benefit_status": "ongoing",
        "current_weekly_rate": 950.00,
        "date_of_injury": (today - timedelta(days=365)).isoformat(),
        "accident_description": "Lifting injury — lumbar spine",
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def sync_hearing_schedule(org_id: str, db: AsyncSession) -> dict:
    """
    Pull upcoming hearings from WCB eCase (mock) and sync to local database.

    Creates new RFAHearing records or updates existing ones based on
    hearing_id matching. Returns summary of sync operation.
    """
    # Fetch all cases for this org to get their WCB case numbers
    result = await db.execute(
        select(RFACase).where(RFACase.org_id == org_id)
    )
    cases = result.scalars().all()

    synced = 0
    new_hearings = 0
    updated = 0

    for case in cases:
        mock_hearings = _mock_hearing_data(case.wcb_case_number)

        for hearing_data in mock_hearings:
            # Check if this hearing already exists by matching on case_id + hearing_date + hearing_type
            hearing_date_parsed = datetime.fromisoformat(hearing_data["hearing_date"])
            existing_result = await db.execute(
                select(RFAHearing).where(
                    RFAHearing.case_id == case.id,
                    RFAHearing.org_id == org_id,
                    RFAHearing.hearing_date == hearing_date_parsed,
                    RFAHearing.hearing_type == hearing_data["hearing_type"],
                )
            )
            existing = existing_result.scalar_one_or_none()

            if existing:
                # Update existing hearing
                existing.location = hearing_data["location"]
                existing.judge_name = hearing_data["judge_name"]
                existing.status = hearing_data["status"]
                existing.notes = hearing_data["notes"]
                updated += 1
            else:
                # Create new hearing record
                new_hearing = RFAHearing(
                    id=uuid.uuid4(),
                    case_id=case.id,
                    org_id=org_id,
                    hearing_date=hearing_date_parsed,
                    hearing_type=hearing_data["hearing_type"],
                    location=hearing_data["location"],
                    judge_name=hearing_data["judge_name"],
                    status=hearing_data["status"],
                    notes=hearing_data["notes"],
                )
                db.add(new_hearing)
                new_hearings += 1

            synced += 1

    await db.flush()
    logger.info(
        "Hearing sync complete for org %s: %d synced, %d new, %d updated",
        org_id, synced, new_hearings, updated,
    )

    return {
        "synced": synced,
        "new_hearings": new_hearings,
        "updated": updated,
        "cases_checked": len(cases),
    }


async def sync_board_decisions(org_id: str, db: AsyncSession) -> dict:
    """
    Pull recent board decisions from WCB (mock) and update submission
    statuses. Creates follow-up tasks when decisions require action.
    """
    result = await db.execute(
        select(RFACase).where(RFACase.org_id == org_id)
    )
    cases = result.scalars().all()

    synced = 0
    decisions_processed = 0
    follow_ups_created = 0

    for case in cases:
        mock_decisions = _mock_decision_data(case.wcb_case_number)

        for decision in mock_decisions:
            decisions_processed += 1

            # Update any submissions for this case to reflect the decision
            sub_result = await db.execute(
                select(RFASubmission).where(
                    RFASubmission.case_id == case.id,
                    RFASubmission.org_id == org_id,
                    RFASubmission.status.in_(["submitted", "accepted"]),
                )
            )
            submissions = sub_result.scalars().all()

            for submission in submissions:
                outcome = decision["outcome"]
                if outcome in ("granted", "partially_granted"):
                    submission.wcb_status = f"decision_{outcome}"
                elif outcome == "denied":
                    submission.wcb_status = "decision_denied"
                else:
                    submission.wcb_status = f"decision_{outcome}"
                synced += 1

            # Create follow-up task if the decision requires action
            if decision.get("follow_up_required"):
                follow_up_deadline = date.fromisoformat(decision["follow_up_deadline"])
                new_task = RFATask(
                    id=uuid.uuid4(),
                    case_id=case.id,
                    org_id=org_id,
                    task_type=decision.get("follow_up_type", "respond_objection"),
                    title=f"Follow-up: {decision['decision_type']} — {case.wcb_case_number}",
                    description=(
                        f"Board decision on {decision['decision_date']}: "
                        f"{decision['summary']}\n\n"
                        f"Action required by {decision['follow_up_deadline']}."
                    ),
                    due_date=follow_up_deadline,
                    priority="high" if (follow_up_deadline - date.today()).days < 14 else "medium",
                    status="pending",
                )
                db.add(new_task)
                follow_ups_created += 1

    await db.flush()
    logger.info(
        "Decision sync complete for org %s: %d synced, %d decisions, %d follow-ups",
        org_id, synced, decisions_processed, follow_ups_created,
    )

    return {
        "synced": synced,
        "decisions": decisions_processed,
        "follow_ups_created": follow_ups_created,
        "cases_checked": len(cases),
    }


async def sync_payment_orders(org_id: str, db: AsyncSession) -> dict:
    """
    Pull payment orders and awards from WCB (mock). Creates RFAPaymentOrder
    records and identifies compliance issues.
    """
    result = await db.execute(
        select(RFACase).where(RFACase.org_id == org_id)
    )
    cases = result.scalars().all()

    synced = 0
    orders_created = 0
    compliance_issues = 0

    for case in cases:
        mock_orders = _mock_payment_order_data(case.wcb_case_number)

        for order_data in mock_orders:
            order_date = date.fromisoformat(order_data["order_date"])

            # Check if this order already exists
            existing_result = await db.execute(
                select(RFAPaymentOrder).where(
                    RFAPaymentOrder.case_id == case.id,
                    RFAPaymentOrder.org_id == org_id,
                    RFAPaymentOrder.order_date == order_date,
                    RFAPaymentOrder.order_type == order_data["order_type"],
                    RFAPaymentOrder.amount == order_data["amount_cents"],
                )
            )
            existing = existing_result.scalar_one_or_none()

            if existing:
                synced += 1
                # Check compliance: if order is older than 14 days and still pending
                if existing.compliance_status == "pending":
                    days_since = (date.today() - order_date).days
                    if days_since > 14:
                        existing.compliance_status = "non_compliant"
                        existing.notes = (
                            f"{existing.notes or ''}\n"
                            f"Auto-flagged as non-compliant: {days_since} days since order "
                            f"with no compliance confirmation."
                        ).strip()
                        compliance_issues += 1
                continue

            start_date = date.fromisoformat(order_data["start_date"]) if order_data.get("start_date") else None
            end_date = date.fromisoformat(order_data["end_date"]) if order_data.get("end_date") else None

            new_order = RFAPaymentOrder(
                id=uuid.uuid4(),
                case_id=case.id,
                org_id=org_id,
                order_date=order_date,
                order_type=order_data["order_type"],
                amount=order_data["amount_cents"],
                frequency=order_data.get("frequency"),
                start_date=start_date,
                end_date=end_date,
                compliance_status="pending",
                notes=order_data.get("notes"),
            )
            db.add(new_order)
            orders_created += 1
            synced += 1

    await db.flush()
    logger.info(
        "Payment order sync complete for org %s: %d synced, %d new, %d compliance issues",
        org_id, synced, orders_created, compliance_issues,
    )

    return {
        "synced": synced,
        "orders": orders_created,
        "compliance_issues": compliance_issues,
        "cases_checked": len(cases),
    }


async def get_case_lifecycle(case_id: str, db: AsyncSession) -> dict:
    """
    Build a complete case timeline from filing through resolution.

    Returns all submissions, hearings, decisions, payment orders,
    and compliance status as a chronologically sorted timeline.
    """
    # Fetch the case
    case_result = await db.execute(
        select(RFACase).where(RFACase.id == case_id)
    )
    case = case_result.scalar_one_or_none()
    if not case:
        raise ValueError(f"Case not found: {case_id}")

    timeline: list[dict] = []

    # --- Case creation ---
    timeline.append({
        "event_type": "case_created",
        "date": case.created_at.isoformat() if case.created_at else None,
        "title": "Case Created",
        "description": f"WCB Case {case.wcb_case_number} created in system.",
        "details": {
            "wcb_case_number": case.wcb_case_number,
            "employer": case.employer_name,
            "date_of_injury": case.date_of_injury.isoformat() if case.date_of_injury else None,
            "district": case.district,
        },
    })

    # --- Submissions ---
    sub_result = await db.execute(
        select(RFASubmission).where(RFASubmission.case_id == case_id)
    )
    submissions = sub_result.scalars().all()
    for sub in submissions:
        timeline.append({
            "event_type": "submission",
            "date": (sub.submitted_at or sub.created_at).isoformat(),
            "title": f"AIRA Submission — {sub.status.title()}",
            "description": sub.narrative[:200] if sub.narrative else "No narrative provided.",
            "details": {
                "submission_id": str(sub.id),
                "status": sub.status,
                "wcb_status": sub.wcb_status,
                "reason_codes": sub.reason_codes,
                "wcb_submission_id": sub.wcb_submission_id,
            },
        })

    # --- Hearings ---
    hearing_result = await db.execute(
        select(RFAHearing).where(RFAHearing.case_id == case_id)
    )
    hearings = hearing_result.scalars().all()
    for hearing in hearings:
        timeline.append({
            "event_type": "hearing",
            "date": hearing.hearing_date.isoformat() if hearing.hearing_date else hearing.created_at.isoformat(),
            "title": f"Hearing: {hearing.hearing_type or 'General'}",
            "description": hearing.notes or "",
            "details": {
                "hearing_id": str(hearing.id),
                "hearing_type": hearing.hearing_type,
                "location": hearing.location,
                "judge_name": hearing.judge_name,
                "status": hearing.status,
            },
        })

    # --- Payment Orders ---
    order_result = await db.execute(
        select(RFAPaymentOrder).where(RFAPaymentOrder.case_id == case_id)
    )
    orders = order_result.scalars().all()
    for order in orders:
        amount_display = f"${order.amount / 100:.2f}" if order.amount else "N/A"
        timeline.append({
            "event_type": "payment_order",
            "date": order.order_date.isoformat(),
            "title": f"Payment Order: {order.order_type.replace('_', ' ').title()}",
            "description": f"Amount: {amount_display}, Frequency: {order.frequency or 'N/A'}",
            "details": {
                "order_id": str(order.id),
                "order_type": order.order_type,
                "amount_cents": order.amount,
                "frequency": order.frequency,
                "start_date": order.start_date.isoformat() if order.start_date else None,
                "end_date": order.end_date.isoformat() if order.end_date else None,
                "compliance_status": order.compliance_status,
            },
        })

    # --- Tasks ---
    task_result = await db.execute(
        select(RFATask).where(RFATask.case_id == case_id)
    )
    tasks = task_result.scalars().all()
    for task in tasks:
        timeline.append({
            "event_type": "task",
            "date": task.created_at.isoformat() if task.created_at else None,
            "title": f"Task: {task.title}",
            "description": task.description or "",
            "details": {
                "task_id": str(task.id),
                "task_type": task.task_type,
                "priority": task.priority,
                "status": task.status,
                "due_date": task.due_date.isoformat() if task.due_date else None,
            },
        })

    # Sort timeline chronologically
    def sort_key(event: dict) -> str:
        d = event.get("date")
        return d if d else "0000-00-00"

    timeline.sort(key=sort_key)

    # Compute compliance summary
    total_orders = len(orders)
    compliant_orders = sum(1 for o in orders if o.compliance_status == "compliant")
    non_compliant_orders = sum(1 for o in orders if o.compliance_status == "non_compliant")
    pending_orders = sum(1 for o in orders if o.compliance_status == "pending")

    return {
        "case_id": str(case.id),
        "wcb_case_number": case.wcb_case_number,
        "date_of_injury": case.date_of_injury.isoformat() if case.date_of_injury else None,
        "employer_name": case.employer_name,
        "district": case.district,
        "timeline": timeline,
        "summary": {
            "total_events": len(timeline),
            "submissions": len(submissions),
            "hearings": len(hearings),
            "payment_orders": total_orders,
            "tasks": len(tasks),
            "compliance": {
                "total_orders": total_orders,
                "compliant": compliant_orders,
                "non_compliant": non_compliant_orders,
                "pending": pending_orders,
            },
        },
    }


async def check_ecase_status(wcb_case_number: str) -> dict:
    """
    Check current case status from the WCB eCase system.

    In production, this would make an HTTP request to the WCB eCase API
    or scrape the eCase web interface. Currently returns mock data.
    """
    logger.info("Checking eCase status for case %s (mock)", wcb_case_number)
    return _mock_ecase_status(wcb_case_number)
