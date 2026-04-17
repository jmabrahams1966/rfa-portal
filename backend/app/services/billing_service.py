"""
Carrier Billing Module for RFA-2 Portal.

For TPAs and defense law firms that bill their clients per filing.
Tracks billable time, generates invoices, and provides billing dashboards.
"""

import uuid
import json
import logging
from datetime import datetime, date, timedelta
from typing import Any

from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, Text, Integer, Float,
    ForeignKey, Index, JSON, func, select, and_,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import Base
from ..models.models import RFACase, RFASubmission, RFAOrganization

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# New Models
# ---------------------------------------------------------------------------

class RFATimeEntry(Base):
    __tablename__ = "rfa_time_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("rfa_cases.id"), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("rfa_organizations.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("rfa_users.id"), nullable=False)
    submission_id = Column(UUID(as_uuid=True), ForeignKey("rfa_submissions.id"), nullable=True)
    minutes = Column(Integer, nullable=False)
    activity_type = Column(String(50), nullable=False)  # document_review / extraction_review / form_completion / submission / hearing_prep / correspondence
    notes = Column(Text, nullable=True)
    billable = Column(Boolean, default=True, nullable=False)
    rate_per_hour = Column(Integer, nullable=True)  # cents per hour
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_rfa_time_entries_case_id", "case_id"),
        Index("ix_rfa_time_entries_org_id", "org_id"),
        Index("ix_rfa_time_entries_user_id", "user_id"),
        Index("ix_rfa_time_entries_created_at", "created_at"),
    )


class RFAInvoice(Base):
    __tablename__ = "rfa_invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("rfa_organizations.id"), nullable=False)
    client_name = Column(String(255), nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    total_amount = Column(Integer, nullable=False, default=0)  # cents
    status = Column(String(50), nullable=False, default="draft")  # draft / sent / paid
    line_items = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_rfa_invoices_org_id", "org_id"),
        Index("ix_rfa_invoices_status", "status"),
        Index("ix_rfa_invoices_period", "period_start", "period_end"),
    )


class RFABillingRate(Base):
    __tablename__ = "rfa_billing_rates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("rfa_organizations.id"), nullable=False)
    rate_type = Column(String(100), nullable=False)  # per_filing / attorney_hourly / adjuster_hourly / doc_processing / ai_extraction / bulk_discount
    amount = Column(Integer, nullable=False)  # cents
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_rfa_billing_rates_org_id", "org_id"),
        Index("ix_rfa_billing_rates_rate_type", "rate_type"),
    )


# ---------------------------------------------------------------------------
# Default Rate Card
# ---------------------------------------------------------------------------

DEFAULT_RATE_CARD: dict[str, dict[str, Any]] = {
    "per_filing": {
        "amount_cents": 1250,  # $12.50
        "description": "Per RFA-2 filing submission fee",
    },
    "attorney_hourly": {
        "amount_cents": 25000,  # $250.00
        "description": "Attorney hourly rate for case work",
    },
    "adjuster_hourly": {
        "amount_cents": 8500,  # $85.00
        "description": "Claims adjuster hourly rate",
    },
    "doc_processing": {
        "amount_cents": 500,  # $5.00
        "description": "Per document processing fee",
    },
    "ai_extraction": {
        "amount_cents": 200,  # $2.00
        "description": "AI-powered data extraction per document",
    },
    "bulk_discount_10": {
        "amount_cents": -10,  # -10% represented as negative percentage marker
        "description": "10% discount for 50+ filings per month",
    },
    "bulk_discount_20": {
        "amount_cents": -20,  # -20%
        "description": "20% discount for 200+ filings per month",
    },
}

ACTIVITY_TYPES = [
    "document_review",
    "extraction_review",
    "form_completion",
    "submission",
    "hearing_prep",
    "correspondence",
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def track_time(
    case_id: str,
    user_id: str,
    minutes: int,
    activity_type: str,
    notes: str,
    db: AsyncSession,
) -> dict:
    """
    Log billable time on a case.

    Activity types: document_review, extraction_review, form_completion,
    submission, hearing_prep, correspondence.
    """
    if activity_type not in ACTIVITY_TYPES:
        raise ValueError(
            f"Invalid activity_type '{activity_type}'. "
            f"Must be one of: {', '.join(ACTIVITY_TYPES)}"
        )

    if minutes <= 0:
        raise ValueError("Minutes must be a positive integer.")

    # Look up the case to get org_id
    case_result = await db.execute(
        select(RFACase).where(RFACase.id == case_id)
    )
    case = case_result.scalar_one_or_none()
    if not case:
        raise ValueError(f"Case not found: {case_id}")

    org_id = case.org_id

    # Determine the rate based on org billing rates or defaults
    rate_cents = await _resolve_hourly_rate(org_id, activity_type, db)

    entry = RFATimeEntry(
        id=uuid.uuid4(),
        case_id=case_id,
        org_id=org_id,
        user_id=user_id,
        minutes=minutes,
        activity_type=activity_type,
        notes=notes,
        billable=True,
        rate_per_hour=rate_cents,
    )
    db.add(entry)
    await db.flush()

    cost_cents = int(rate_cents * (minutes / 60.0))

    return {
        "time_entry_id": str(entry.id),
        "case_id": str(case_id),
        "user_id": str(user_id),
        "minutes": minutes,
        "activity_type": activity_type,
        "rate_per_hour": f"${rate_cents / 100:.2f}",
        "cost": f"${cost_cents / 100:.2f}",
        "billable": True,
    }


async def get_case_billing(case_id: str, db: AsyncSession) -> dict:
    """
    Total billable time and cost for a case.

    Returns time entries grouped by activity, filing fees,
    document processing fees, and total cost.
    """
    # Time entries
    te_result = await db.execute(
        select(RFATimeEntry).where(
            RFATimeEntry.case_id == case_id,
            RFATimeEntry.billable == True,
        )
    )
    time_entries = te_result.scalars().all()

    # Submissions for filing fees
    sub_result = await db.execute(
        select(RFASubmission).where(RFASubmission.case_id == case_id)
    )
    submissions = sub_result.scalars().all()

    # Get the case's org_id for rate lookup
    case_result = await db.execute(
        select(RFACase).where(RFACase.id == case_id)
    )
    case = case_result.scalar_one_or_none()
    if not case:
        raise ValueError(f"Case not found: {case_id}")

    org_id = case.org_id
    per_filing_rate = await _resolve_rate(org_id, "per_filing", db)
    doc_processing_rate = await _resolve_rate(org_id, "doc_processing", db)
    ai_extraction_rate = await _resolve_rate(org_id, "ai_extraction", db)

    # Group time entries by activity type
    entries_by_activity: dict[str, list[dict]] = {}
    total_minutes = 0
    total_time_cost_cents = 0

    for entry in time_entries:
        rate = entry.rate_per_hour or 0
        entry_cost = int(rate * (entry.minutes / 60.0))
        total_minutes += entry.minutes
        total_time_cost_cents += entry_cost

        entry_data = {
            "id": str(entry.id),
            "minutes": entry.minutes,
            "rate_per_hour_cents": rate,
            "cost_cents": entry_cost,
            "notes": entry.notes,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
        }

        if entry.activity_type not in entries_by_activity:
            entries_by_activity[entry.activity_type] = []
        entries_by_activity[entry.activity_type].append(entry_data)

    # Filing fees: count submitted filings
    submitted_count = sum(
        1 for s in submissions if s.status in ("submitted", "accepted")
    )
    filing_fees_cents = submitted_count * per_filing_rate

    # Document processing fees: count documents across all submissions
    doc_count = 0
    extraction_count = 0
    for sub in submissions:
        if sub.documents:
            doc_count += len(sub.documents)
        if sub.extractions:
            extraction_count += len(sub.extractions)

    doc_fees_cents = doc_count * doc_processing_rate
    extraction_fees_cents = extraction_count * ai_extraction_rate

    total_cost_cents = total_time_cost_cents + filing_fees_cents + doc_fees_cents + extraction_fees_cents

    return {
        "case_id": str(case_id),
        "wcb_case_number": case.wcb_case_number,
        "time_entries": entries_by_activity,
        "filing_fees": {
            "submissions_count": submitted_count,
            "per_filing_rate_cents": per_filing_rate,
            "total_cents": filing_fees_cents,
        },
        "document_fees": {
            "documents_count": doc_count,
            "per_doc_rate_cents": doc_processing_rate,
            "total_cents": doc_fees_cents,
        },
        "extraction_fees": {
            "extractions_count": extraction_count,
            "per_extraction_rate_cents": ai_extraction_rate,
            "total_cents": extraction_fees_cents,
        },
        "total_hours": round(total_minutes / 60.0, 2),
        "total_time_cost": f"${total_time_cost_cents / 100:.2f}",
        "total_fees": f"${(filing_fees_cents + doc_fees_cents + extraction_fees_cents) / 100:.2f}",
        "total_cost": f"${total_cost_cents / 100:.2f}",
        "total_cost_cents": total_cost_cents,
    }


async def generate_invoice(
    org_id: str,
    db: AsyncSession,
    period_start: date,
    period_end: date,
    client_name: str | None = None,
) -> dict:
    """
    Generate an invoice for all billable activity in the given period.

    Returns structured invoice data including per-case breakdown
    and an HTML representation for PDF generation.
    """
    # Determine client name
    if not client_name:
        org_result = await db.execute(
            select(RFAOrganization).where(RFAOrganization.id == org_id)
        )
        org = org_result.scalar_one_or_none()
        client_name = org.name if org else "Unknown Client"

    # Get all time entries in the period
    te_result = await db.execute(
        select(RFATimeEntry).where(
            RFATimeEntry.org_id == org_id,
            RFATimeEntry.billable == True,
            RFATimeEntry.created_at >= datetime.combine(period_start, datetime.min.time()),
            RFATimeEntry.created_at <= datetime.combine(period_end, datetime.max.time()),
        )
    )
    time_entries = te_result.scalars().all()

    # Get all submissions in the period
    sub_result = await db.execute(
        select(RFASubmission).where(
            RFASubmission.org_id == org_id,
            RFASubmission.created_at >= datetime.combine(period_start, datetime.min.time()),
            RFASubmission.created_at <= datetime.combine(period_end, datetime.max.time()),
        )
    )
    submissions = sub_result.scalars().all()

    # Rates
    per_filing_rate = await _resolve_rate(org_id, "per_filing", db)
    doc_processing_rate = await _resolve_rate(org_id, "doc_processing", db)
    ai_extraction_rate = await _resolve_rate(org_id, "ai_extraction", db)

    # Build per-case line items
    case_ids = set()
    for te in time_entries:
        case_ids.add(str(te.case_id))
    for sub in submissions:
        case_ids.add(str(sub.case_id))

    line_items: list[dict] = []
    grand_total_cents = 0

    for cid in sorted(case_ids):
        # Fetch case info
        case_result = await db.execute(
            select(RFACase).where(RFACase.id == cid)
        )
        case = case_result.scalar_one_or_none()
        case_number = case.wcb_case_number if case else cid

        # Time for this case
        case_time_entries = [te for te in time_entries if str(te.case_id) == cid]
        case_minutes = sum(te.minutes for te in case_time_entries)
        case_time_cost = sum(
            int((te.rate_per_hour or 0) * (te.minutes / 60.0))
            for te in case_time_entries
        )

        # Filings for this case
        case_submissions = [s for s in submissions if str(s.case_id) == cid]
        case_filed = sum(1 for s in case_submissions if s.status in ("submitted", "accepted"))
        case_filing_fees = case_filed * per_filing_rate

        # Documents for this case
        case_doc_count = 0
        case_extraction_count = 0
        for sub in case_submissions:
            if sub.documents:
                case_doc_count += len(sub.documents)
            if sub.extractions:
                case_extraction_count += len(sub.extractions)

        case_doc_fees = case_doc_count * doc_processing_rate
        case_extraction_fees = case_extraction_count * ai_extraction_rate

        case_total = case_time_cost + case_filing_fees + case_doc_fees + case_extraction_fees
        grand_total_cents += case_total

        line_items.append({
            "case_id": cid,
            "wcb_case_number": case_number,
            "time_hours": round(case_minutes / 60.0, 2),
            "time_cost_cents": case_time_cost,
            "filings": case_filed,
            "filing_fees_cents": case_filing_fees,
            "documents": case_doc_count,
            "doc_fees_cents": case_doc_fees,
            "extractions": case_extraction_count,
            "extraction_fees_cents": case_extraction_fees,
            "subtotal_cents": case_total,
        })

    # Apply bulk discount if applicable
    total_filings = sum(item["filings"] for item in line_items)
    discount_cents = 0
    discount_description = None
    if total_filings >= 200:
        discount_cents = int(grand_total_cents * 0.20)
        discount_description = "20% bulk discount (200+ filings)"
    elif total_filings >= 50:
        discount_cents = int(grand_total_cents * 0.10)
        discount_description = "10% bulk discount (50+ filings)"

    final_total = grand_total_cents - discount_cents

    # Create the invoice record
    invoice = RFAInvoice(
        id=uuid.uuid4(),
        org_id=org_id,
        client_name=client_name,
        period_start=period_start,
        period_end=period_end,
        total_amount=final_total,
        status="draft",
        line_items={
            "items": line_items,
            "discount": {
                "amount_cents": discount_cents,
                "description": discount_description,
            } if discount_cents > 0 else None,
        },
    )
    db.add(invoice)
    await db.flush()

    # Generate HTML for PDF rendering
    html = _generate_invoice_html(
        invoice_id=str(invoice.id),
        client_name=client_name,
        period_start=period_start,
        period_end=period_end,
        line_items=line_items,
        discount_cents=discount_cents,
        discount_description=discount_description,
        final_total=final_total,
    )

    return {
        "invoice_id": str(invoice.id),
        "client_name": client_name,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "line_items": line_items,
        "subtotal": f"${grand_total_cents / 100:.2f}",
        "subtotal_cents": grand_total_cents,
        "discount": {
            "amount": f"${discount_cents / 100:.2f}",
            "description": discount_description,
        } if discount_cents > 0 else None,
        "total": f"${final_total / 100:.2f}",
        "total_cents": final_total,
        "total_filings": total_filings,
        "status": "draft",
        "html": html,
    }


async def get_billing_dashboard(org_id: str, db: AsyncSession) -> dict:
    """
    Billing dashboard with revenue breakdowns, unbilled time,
    and outstanding invoices.
    """
    today = date.today()
    month_start = today.replace(day=1)
    quarter_month = ((today.month - 1) // 3) * 3 + 1
    quarter_start = today.replace(month=quarter_month, day=1)
    year_start = today.replace(month=1, day=1)

    # --- Revenue from invoices ---
    inv_result = await db.execute(
        select(RFAInvoice).where(RFAInvoice.org_id == org_id)
    )
    invoices = inv_result.scalars().all()

    paid_invoices = [inv for inv in invoices if inv.status == "paid"]
    sent_invoices = [inv for inv in invoices if inv.status == "sent"]
    draft_invoices = [inv for inv in invoices if inv.status == "draft"]

    def revenue_in_period(inv_list: list, start: date, end: date) -> int:
        return sum(
            inv.total_amount for inv in inv_list
            if inv.period_start >= start and inv.period_end <= end
        )

    revenue_this_month = revenue_in_period(paid_invoices, month_start, today)
    revenue_this_quarter = revenue_in_period(paid_invoices, quarter_start, today)
    revenue_this_year = revenue_in_period(paid_invoices, year_start, today)

    # --- Revenue by client ---
    revenue_by_client: dict[str, int] = {}
    for inv in paid_invoices:
        client = inv.client_name
        revenue_by_client[client] = revenue_by_client.get(client, 0) + inv.total_amount

    # --- Revenue by case (from time entries and fees) ---
    te_result = await db.execute(
        select(RFATimeEntry).where(
            RFATimeEntry.org_id == org_id,
            RFATimeEntry.billable == True,
        )
    )
    all_time_entries = te_result.scalars().all()

    revenue_by_case: dict[str, int] = {}
    for te in all_time_entries:
        cid = str(te.case_id)
        cost = int((te.rate_per_hour or 0) * (te.minutes / 60.0))
        revenue_by_case[cid] = revenue_by_case.get(cid, 0) + cost

    # --- Unbilled time ---
    # Time entries not yet included in any invoice (created after the latest invoice period_end)
    latest_invoice_end = max(
        (inv.period_end for inv in invoices), default=date.min
    )
    unbilled_entries = [
        te for te in all_time_entries
        if te.created_at and te.created_at.date() > latest_invoice_end
    ]
    unbilled_minutes = sum(te.minutes for te in unbilled_entries)
    unbilled_cost = sum(
        int((te.rate_per_hour or 0) * (te.minutes / 60.0))
        for te in unbilled_entries
    )

    # --- Outstanding invoices ---
    outstanding = [
        {
            "invoice_id": str(inv.id),
            "client_name": inv.client_name,
            "period": f"{inv.period_start.isoformat()} — {inv.period_end.isoformat()}",
            "total": f"${inv.total_amount / 100:.2f}",
            "total_cents": inv.total_amount,
            "status": inv.status,
        }
        for inv in sent_invoices
    ]

    # --- Average revenue per filing ---
    sub_result = await db.execute(
        select(RFASubmission).where(
            RFASubmission.org_id == org_id,
            RFASubmission.status.in_(["submitted", "accepted"]),
        )
    )
    total_submitted = len(sub_result.scalars().all())
    total_paid_revenue = sum(inv.total_amount for inv in paid_invoices)
    avg_revenue_per_filing = (
        int(total_paid_revenue / total_submitted) if total_submitted > 0 else 0
    )

    return {
        "revenue": {
            "this_month": f"${revenue_this_month / 100:.2f}",
            "this_month_cents": revenue_this_month,
            "this_quarter": f"${revenue_this_quarter / 100:.2f}",
            "this_quarter_cents": revenue_this_quarter,
            "this_year": f"${revenue_this_year / 100:.2f}",
            "this_year_cents": revenue_this_year,
        },
        "revenue_by_client": {
            client: {"total": f"${cents / 100:.2f}", "total_cents": cents}
            for client, cents in sorted(revenue_by_client.items(), key=lambda x: -x[1])
        },
        "revenue_by_case": {
            cid: {"total": f"${cents / 100:.2f}", "total_cents": cents}
            for cid, cents in sorted(revenue_by_case.items(), key=lambda x: -x[1])[:20]
        },
        "unbilled": {
            "hours": round(unbilled_minutes / 60.0, 2),
            "cost": f"${unbilled_cost / 100:.2f}",
            "cost_cents": unbilled_cost,
            "entry_count": len(unbilled_entries),
        },
        "outstanding_invoices": outstanding,
        "outstanding_total": f"${sum(inv.total_amount for inv in sent_invoices) / 100:.2f}",
        "outstanding_total_cents": sum(inv.total_amount for inv in sent_invoices),
        "average_revenue_per_filing": f"${avg_revenue_per_filing / 100:.2f}",
        "average_revenue_per_filing_cents": avg_revenue_per_filing,
        "total_filings": total_submitted,
        "invoices_summary": {
            "draft": len(draft_invoices),
            "sent": len(sent_invoices),
            "paid": len(paid_invoices),
        },
    }


async def get_rate_card(org_id: str, db: AsyncSession | None = None) -> dict:
    """
    Billing rates for an organization. Returns org-specific rates if
    configured, otherwise falls back to defaults.
    """
    org_rates: dict[str, dict] = {}

    if db:
        rate_result = await db.execute(
            select(RFABillingRate).where(RFABillingRate.org_id == org_id)
        )
        rates = rate_result.scalars().all()
        for rate in rates:
            org_rates[rate.rate_type] = {
                "amount_cents": rate.amount,
                "description": rate.description,
                "custom": True,
            }

    # Merge with defaults, org overrides take precedence
    card: dict[str, dict] = {}
    for rate_type, defaults in DEFAULT_RATE_CARD.items():
        if rate_type in org_rates:
            card[rate_type] = org_rates[rate_type]
        else:
            card[rate_type] = {
                **defaults,
                "custom": False,
            }

    # Format amounts for display
    for rate_type, info in card.items():
        cents = info["amount_cents"]
        if cents < 0:
            info["display"] = f"{abs(cents)}% discount"
        else:
            info["display"] = f"${cents / 100:.2f}"

    return {
        "org_id": str(org_id),
        "rates": card,
        "activity_types": ACTIVITY_TYPES,
    }


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------

async def _resolve_rate(org_id: str, rate_type: str, db: AsyncSession) -> int:
    """Resolve billing rate: org-specific first, then default."""
    result = await db.execute(
        select(RFABillingRate).where(
            RFABillingRate.org_id == org_id,
            RFABillingRate.rate_type == rate_type,
        )
    )
    custom = result.scalar_one_or_none()
    if custom:
        return custom.amount

    default = DEFAULT_RATE_CARD.get(rate_type)
    return default["amount_cents"] if default else 0


async def _resolve_hourly_rate(
    org_id: str, activity_type: str, db: AsyncSession
) -> int:
    """Determine the hourly rate based on activity type."""
    # Hearing prep and correspondence are billed at attorney rate,
    # everything else at adjuster rate
    if activity_type in ("hearing_prep", "correspondence"):
        return await _resolve_rate(org_id, "attorney_hourly", db)
    return await _resolve_rate(org_id, "adjuster_hourly", db)


def _generate_invoice_html(
    invoice_id: str,
    client_name: str,
    period_start: date,
    period_end: date,
    line_items: list[dict],
    discount_cents: int,
    discount_description: str | None,
    final_total: int,
) -> str:
    """Generate HTML representation of an invoice for PDF rendering."""

    rows_html = ""
    for item in line_items:
        rows_html += f"""
        <tr>
            <td>{item['wcb_case_number']}</td>
            <td>{item['time_hours']}h</td>
            <td>${item['time_cost_cents'] / 100:.2f}</td>
            <td>{item['filings']}</td>
            <td>${item['filing_fees_cents'] / 100:.2f}</td>
            <td>{item['documents']}</td>
            <td>${item['doc_fees_cents'] / 100:.2f}</td>
            <td>${item['extraction_fees_cents'] / 100:.2f}</td>
            <td><strong>${item['subtotal_cents'] / 100:.2f}</strong></td>
        </tr>"""

    discount_row = ""
    if discount_cents > 0:
        discount_row = f"""
        <tr class="discount">
            <td colspan="8" style="text-align:right;">{discount_description}</td>
            <td><strong>-${discount_cents / 100:.2f}</strong></td>
        </tr>"""

    subtotal_cents = sum(item["subtotal_cents"] for item in line_items)

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Invoice {invoice_id[:8]}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; }}
        .header {{ display: flex; justify-content: space-between; margin-bottom: 30px; }}
        .header h1 {{ color: #1a56db; margin: 0; }}
        .meta {{ margin-bottom: 20px; }}
        .meta p {{ margin: 4px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th {{ background: #1a56db; color: white; padding: 10px 8px; text-align: left; font-size: 12px; }}
        td {{ padding: 8px; border-bottom: 1px solid #e5e7eb; font-size: 13px; }}
        tr:hover {{ background: #f9fafb; }}
        .totals {{ margin-top: 20px; text-align: right; }}
        .totals p {{ margin: 4px 0; font-size: 14px; }}
        .totals .grand-total {{ font-size: 20px; color: #1a56db; font-weight: bold; }}
        .discount td {{ color: #059669; font-style: italic; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #e5e7eb; font-size: 12px; color: #6b7280; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>RFA-2 Portal</h1>
            <p>Workers' Compensation Filing Services</p>
        </div>
        <div style="text-align:right;">
            <h2>INVOICE</h2>
            <p>#{invoice_id[:8].upper()}</p>
        </div>
    </div>

    <div class="meta">
        <p><strong>Client:</strong> {client_name}</p>
        <p><strong>Period:</strong> {period_start.strftime('%B %d, %Y')} — {period_end.strftime('%B %d, %Y')}</p>
        <p><strong>Generated:</strong> {date.today().strftime('%B %d, %Y')}</p>
    </div>

    <table>
        <thead>
            <tr>
                <th>Case #</th>
                <th>Hours</th>
                <th>Time Cost</th>
                <th>Filings</th>
                <th>Filing Fees</th>
                <th>Docs</th>
                <th>Doc Fees</th>
                <th>AI Fees</th>
                <th>Subtotal</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
            {discount_row}
        </tbody>
    </table>

    <div class="totals">
        <p>Subtotal: ${subtotal_cents / 100:.2f}</p>
        {"<p>Discount: -$" + f"{discount_cents / 100:.2f}" + "</p>" if discount_cents > 0 else ""}
        <p class="grand-total">Total Due: ${final_total / 100:.2f}</p>
    </div>

    <div class="footer">
        <p>Payment terms: Net 30. Please remit payment to the address on file.</p>
        <p>Questions? Contact billing@rfa-portal.com</p>
    </div>
</body>
</html>"""
