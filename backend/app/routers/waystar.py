"""Waystar router — eligibility (270/271), claims (837), and ERA (835).

Endpoints:
    POST /waystar/eligibility           — submit a 270 inquiry, return parsed 271
    POST /waystar/claims                — submit an 837P claim, return ack
    GET  /waystar/claims/{claim_id}     — claim status
    GET  /waystar/era                   — list 835 remittances
    GET  /waystar/era/{era_id}          — fetch and parse a single 835
    POST /waystar/x12/parse             — utility: parse a raw X12 string
    POST /waystar/x12/build/270         — utility: build a 270 envelope
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..middleware.auth import get_current_user
from ..services import waystar_x12 as x12
from ..services.waystar_api_client import get_waystar_client


router = APIRouter(prefix="/waystar", tags=["waystar"])


# ── Schemas ────────────────────────────────────────────────────────────────

class EligibilityRequest(BaseModel):
    payer_name: str
    payer_id: str
    provider_name: str
    provider_npi: str
    subscriber_first: str
    subscriber_last: str
    subscriber_member_id: str
    subscriber_dob: str
    service_date: Optional[str] = None
    service_type_codes: list[str] = Field(default_factory=lambda: ["30"])


class ServiceLineIn(BaseModel):
    procedure_code: str
    charge: float
    units: float = 1.0
    modifiers: list[str] = Field(default_factory=list)
    diagnosis_pointers: list[int] = Field(default_factory=lambda: [1])
    service_date: Optional[str] = None
    place_of_service: str = "11"


class ClaimRequest(BaseModel):
    submitter_name: str
    submitter_id: str
    submitter_contact_name: str
    submitter_phone: str
    receiver_name: str = "WAYSTAR"
    receiver_id: str = "WAYSTAR"
    billing_provider_name: str
    billing_provider_npi: str
    billing_provider_tax_id: str
    billing_address_line: str
    billing_city: str
    billing_state: str
    billing_zip: str
    subscriber_first: str
    subscriber_last: str
    subscriber_member_id: str
    subscriber_dob: str
    subscriber_gender: str
    payer_name: str
    payer_id: str
    claim_id: str
    total_charge: float
    diagnosis_codes: list[str]
    service_lines: list[ServiceLineIn]
    place_of_service: str = "11"


class X12RawRequest(BaseModel):
    raw: str


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/eligibility")
async def post_eligibility(
    payload: EligibilityRequest,
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    """270 → 271. Returns the request X12, raw response, and parsed 271."""
    client = get_waystar_client()
    result = await client.check_eligibility(payload.model_dump())
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"message": "Eligibility request failed", **result},
        )
    return result


@router.post("/claims")
async def post_claim(
    payload: ClaimRequest,
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    """837P claim submission. Returns the X12 sent and the ack."""
    client = get_waystar_client()
    body = payload.model_dump()
    body["service_lines"] = [
        x12.ServiceLine(**line) for line in body["service_lines"]
    ]
    result = await client.submit_claim(body)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Claim rejected", **result},
        )
    return result


@router.get("/claims/{claim_id}")
async def get_claim_status(
    claim_id: str,
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    client = get_waystar_client()
    return await client.get_claim_status(claim_id)


@router.get("/era")
async def list_era(
    since: Optional[str] = Query(None),
    until: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    """List recent 835 remittances available for download."""
    client = get_waystar_client()
    return await client.list_remittances(since=since, until=until, limit=limit)


@router.get("/era/{era_id}")
async def get_era(
    era_id: str,
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    """Fetch a single 835 remittance and return both raw + parsed forms."""
    client = get_waystar_client()
    return await client.get_remittance(era_id)


@router.post("/x12/parse")
async def parse_raw_x12(
    payload: X12RawRequest,
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    """Utility: accept a raw X12 string (271, 835, or any envelope) and return parsed JSON."""
    try:
        return x12.parse_x12(payload.raw)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse X12: {exc}",
        )


@router.post("/x12/build/270")
async def build_270_only(
    payload: EligibilityRequest,
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    """Utility: build a 270 envelope without sending it. Useful for QA."""
    segments = x12.build_270(**payload.model_dump())
    envelope = x12.build_envelope(
        sender_id="RFAPORTAL",
        receiver_id="WAYSTAR",
        transactions=[("HS", segments)],
    )
    return {"x12": envelope}
