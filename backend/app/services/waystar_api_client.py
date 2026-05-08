"""Waystar API client — eligibility (270/271), claims (837), and ERA (835).

Two implementations are provided:

* ``WaystarApiClient`` — talks to a Waystar-style REST endpoint over HTTPS.
  Auth defaults to OAuth2 client credentials, with API-key fallback. Real
  Waystar endpoint paths and payload shapes can be overridden via the
  ``endpoints`` argument once the partner spec is finalized.

* ``MockWaystarApiClient`` — same async interface, fully offline. Generates
  realistic 271 / 837-ack / 835 X12 payloads using ``waystar_x12`` so the
  frontend, services, and parsers can be exercised without credentials.

Use ``get_waystar_client(...)`` to pick the right implementation based on the
caller's organization settings (mirrors the WCB pattern in
``wcb_api_client.py``).
"""

from __future__ import annotations

import logging
import random
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx

from ..config import get_settings
from . import waystar_x12 as x12

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Default endpoint map (override per-tenant if needed) ────────────────────

DEFAULT_ENDPOINTS = {
    "token":       "/oauth2/token",
    "eligibility": "/eligibility/v1/inquiries",         # accepts 270 / JSON
    "claims":      "/claims/v1/submissions",            # accepts 837 / JSON
    "claim_status":"/claims/v1/submissions/{claim_id}",
    "era_list":    "/era/v1/remittances",
    "era_detail":  "/era/v1/remittances/{era_id}",
}


# ── Real client ─────────────────────────────────────────────────────────────

class WaystarApiClient:
    def __init__(
        self,
        *,
        base_url: str,
        client_id: str | None = None,
        client_secret: str | None = None,
        api_key: str | None = None,
        submitter_id: str = "",
        receiver_id: str = "WAYSTAR",
        is_sandbox: bool = True,
        endpoints: dict[str, str] | None = None,
        timeout: float = 30.0,
    ):
        if not (api_key or (client_id and client_secret)):
            raise ValueError(
                "WaystarApiClient requires either api_key or (client_id + client_secret)"
            )
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.api_key = api_key
        self.submitter_id = submitter_id
        self.receiver_id = receiver_id
        self.is_sandbox = is_sandbox
        self.endpoints = {**DEFAULT_ENDPOINTS, **(endpoints or {})}
        self.timeout = timeout
        self._access_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None

    # ── auth ────────────────────────────────────────────────────────────────

    async def _auth_headers(self) -> dict[str, str]:
        if self.api_key:
            return {"Authorization": f"ApiKey {self.api_key}"}
        token = await self._get_access_token()
        return {"Authorization": f"Bearer {token}"}

    async def _get_access_token(self) -> str:
        if self._access_token and self._token_expires and datetime.utcnow() < self._token_expires:
            return self._access_token
        url = self.base_url + self.endpoints["token"]
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            payload = resp.json()
        self._access_token = payload["access_token"]
        ttl = int(payload.get("expires_in", 3600))
        self._token_expires = datetime.utcnow() + timedelta(seconds=ttl - 60)
        return self._access_token

    # ── 270/271 ─────────────────────────────────────────────────────────────

    async def check_eligibility(self, request: dict[str, Any]) -> dict[str, Any]:
        """Submit a 270 eligibility inquiry and return the parsed 271.

        ``request`` accepts the same keyword fields as ``waystar_x12.build_270``.
        """
        segments = x12.build_270(**request, control_number="0001")
        payload_270 = x12.build_envelope(
            sender_id=self.submitter_id,
            receiver_id=self.receiver_id,
            transactions=[("HS", segments)],
            usage="T" if self.is_sandbox else "P",
        )

        url = self.base_url + self.endpoints["eligibility"]
        headers = {**(await self._auth_headers()), "Content-Type": "application/edi-x12"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, content=payload_270, headers=headers)

        body = resp.text
        parsed: dict[str, Any] | None = None
        if body.lstrip().startswith("ISA"):
            try:
                parsed = x12.parse_x12(body)
            except Exception as exc:
                logger.warning("271 parse failed: %s", exc)

        return {
            "success": 200 <= resp.status_code < 300,
            "status_code": resp.status_code,
            "request_x12": payload_270,
            "response_x12": body,
            "parsed": parsed,
        }

    # ── 837 ─────────────────────────────────────────────────────────────────

    async def submit_claim(self, claim: dict[str, Any]) -> dict[str, Any]:
        """Submit a single professional claim (837P) and return the API ack."""
        # Allow callers to pass ServiceLine objects or dicts.
        lines_in = claim.pop("service_lines", [])
        service_lines = []
        for line in lines_in:
            if isinstance(line, x12.ServiceLine):
                service_lines.append(line)
            else:
                service_lines.append(x12.ServiceLine(**line))
        segments = x12.build_837p(
            **claim,
            service_lines=service_lines,
            submitter_id=self.submitter_id or claim.get("submitter_id", "WAYSTAR"),
        )
        payload_837 = x12.build_envelope(
            sender_id=self.submitter_id,
            receiver_id=self.receiver_id,
            transactions=[("HC", segments)],
            usage="T" if self.is_sandbox else "P",
        )

        url = self.base_url + self.endpoints["claims"]
        headers = {**(await self._auth_headers()), "Content-Type": "application/edi-x12"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, content=payload_837, headers=headers)

        try:
            ack = resp.json()
        except Exception:
            ack = {"raw": resp.text}

        return {
            "success": 200 <= resp.status_code < 300,
            "status_code": resp.status_code,
            "request_x12": payload_837,
            "ack": ack,
        }

    async def get_claim_status(self, claim_id: str) -> dict[str, Any]:
        url = self.base_url + self.endpoints["claim_status"].format(claim_id=claim_id)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, headers=await self._auth_headers())
        return resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"raw": resp.text}

    # ── 835 ─────────────────────────────────────────────────────────────────

    async def list_remittances(
        self,
        *,
        since: str | None = None,
        until: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        url = self.base_url + self.endpoints["era_list"]
        params: dict[str, Any] = {"limit": limit}
        if since: params["since"] = since
        if until: params["until"] = until
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, headers=await self._auth_headers(), params=params)
        return resp.json()

    async def get_remittance(self, era_id: str) -> dict[str, Any]:
        url = self.base_url + self.endpoints["era_detail"].format(era_id=era_id)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, headers=await self._auth_headers())
        body = resp.text
        if body.lstrip().startswith("ISA"):
            try:
                return {"era_id": era_id, "raw_x12": body, "parsed": x12.parse_x12(body)}
            except Exception as exc:
                return {"era_id": era_id, "raw_x12": body, "parse_error": str(exc)}
        return {"era_id": era_id, "raw": body}


# ── Mock client ─────────────────────────────────────────────────────────────

class MockWaystarApiClient(WaystarApiClient):
    """Offline Waystar client that synthesizes real X12 transactions."""

    def __init__(self, **kwargs):
        kwargs.setdefault("base_url", "https://mock.waystar.local")
        kwargs.setdefault("api_key", "mock-key")
        kwargs.setdefault("submitter_id", "RFAPORTAL")
        kwargs.setdefault("receiver_id", "WAYSTAR")
        kwargs.setdefault("is_sandbox", True)
        super().__init__(**kwargs)

    async def _get_access_token(self) -> str:
        return "mock-token"

    async def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": "ApiKey mock-key"}

    async def check_eligibility(self, request: dict[str, Any]) -> dict[str, Any]:
        request_270 = x12.build_envelope(
            sender_id=self.submitter_id,
            receiver_id=self.receiver_id,
            transactions=[("HS", x12.build_270(**request))],
        )
        response_271 = _mock_271(request)
        return {
            "success": True,
            "status_code": 200,
            "request_x12": request_270,
            "response_x12": response_271,
            "parsed": x12.parse_x12(response_271),
        }

    async def submit_claim(self, claim: dict[str, Any]) -> dict[str, Any]:
        # Build the real 837 so callers can inspect what would be sent.
        lines_in = claim.get("service_lines", [])
        service_lines = [
            l if isinstance(l, x12.ServiceLine) else x12.ServiceLine(**l)
            for l in lines_in
        ]
        body_args = {**claim, "service_lines": service_lines}
        body_args.setdefault("submitter_id", self.submitter_id)
        segments = x12.build_837p(**body_args)
        request_837 = x12.build_envelope(
            sender_id=self.submitter_id,
            receiver_id=self.receiver_id,
            transactions=[("HC", segments)],
        )
        accepted = random.random() < 0.92
        ack = {
            "claim_id": claim.get("claim_id") or f"WS-{datetime.utcnow():%Y%m%d}-{random.randint(100000,999999)}",
            "status": "accepted" if accepted else "rejected",
            "received_at": datetime.utcnow().isoformat() + "Z",
            "trace_id": str(uuid.uuid4()),
        }
        if not accepted:
            ack["errors"] = [
                {"code": "A7:562", "message": "Subscriber Insured ID number is invalid"}
            ]
        return {
            "success": accepted,
            "status_code": 202 if accepted else 422,
            "request_x12": request_837,
            "ack": ack,
        }

    async def get_claim_status(self, claim_id: str) -> dict[str, Any]:
        statuses = ["received", "validated", "forwarded_to_payer", "paid", "denied"]
        return {
            "claim_id": claim_id,
            "status": random.choice(statuses),
            "as_of": datetime.utcnow().isoformat() + "Z",
        }

    async def list_remittances(self, **kwargs) -> dict[str, Any]:
        return {
            "items": [
                {
                    "era_id": f"ERA-{i:08d}",
                    "payer_name": "MERCURY INSURANCE",
                    "payment_amount": round(random.uniform(150, 4500), 2),
                    "effective_date": (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d"),
                    "claim_count": random.randint(1, 6),
                }
                for i in range(1, 6)
            ],
            "limit": kwargs.get("limit", 50),
        }

    async def get_remittance(self, era_id: str) -> dict[str, Any]:
        raw = _mock_835(era_id)
        return {"era_id": era_id, "raw_x12": raw, "parsed": x12.parse_x12(raw)}


# ── Mock generators ─────────────────────────────────────────────────────────

def _mock_271(request: dict[str, Any]) -> str:
    """Build a syntactically valid 271 from the incoming 270 request fields."""
    yymmdd = datetime.utcnow().strftime("%y%m%d")
    today = datetime.utcnow().strftime("%Y%m%d")
    benefits = [
        x12.Segment("EB", ["1", "IND", "30", "12", request.get("payer_name", "MOCK PAYER")]),
        x12.Segment("EB", ["A", "IND", "30", "", "", "", "", "0.20"]),     # 20% coinsurance
        x12.Segment("EB", ["B", "IND", "30", "", "", "", "25"]),           # $25 copay
        x12.Segment("EB", ["C", "IND", "30", "", "", "", "1500"]),         # $1500 deductible
        x12.Segment("MSG", ["Eligibility verified — mock response"]),
        x12.Segment("DTP", ["291", "D8", today]),
    ]
    body = [
        x12.Segment("BHT", ["0022", "11", "MOCK271", today, datetime.utcnow().strftime("%H%M")]),
        x12.Segment("HL", ["1", "", "20", "1"]),
        x12.Segment("NM1", ["PR", "2", request.get("payer_name", "MOCK PAYER"), "", "", "", "", "PI", request.get("payer_id", "00000")]),
        x12.Segment("HL", ["2", "1", "21", "1"]),
        x12.Segment("NM1", ["1P", "2", request.get("provider_name", "MOCK PROVIDER"), "", "", "", "", "XX", request.get("provider_npi", "1234567890")]),
        x12.Segment("HL", ["3", "2", "22", "0"]),
        x12.Segment("TRN", ["2", "MOCK-TRACE-1", "9999999999"]),
        x12.Segment("NM1", [
            "IL", "1", request.get("subscriber_last", "DOE"), request.get("subscriber_first", "JANE"),
            "", "", "", "MI", request.get("subscriber_member_id", "MEMBER123"),
        ]),
        x12.Segment("DMG", ["D8", x12._format_dob(request.get("subscriber_dob", "1980-01-01"))]),
        *benefits,
    ]
    segments = x12._wrap_st_se("271", "0001", body)
    return x12.build_envelope(
        sender_id="WAYSTAR",
        receiver_id="RFAPORTAL",
        transactions=[("HB", segments)],
    )


def _mock_835(era_id: str) -> str:
    today = datetime.utcnow().strftime("%Y%m%d")
    body = [
        x12.Segment("BPR", ["I", "1850.00", "C", "ACH", "CCP", "01", "999999992", "DA", "123456789", "1234567890", "", "01", "999999993", "DA", "987654321", today]),
        x12.Segment("TRN", ["1", era_id, "1234567890"]),
        x12.Segment("DTM", ["405", today]),
        x12.Segment("N1", ["PR", "MERCURY INSURANCE"]),
        x12.Segment("N3", ["100 PAYER WAY"]),
        x12.Segment("N4", ["NEW YORK", "NY", "10001"]),
        x12.Segment("N1", ["PE", "RFA PORTAL CLINIC", "XX", "1234567890"]),
        x12.Segment("LX", ["1"]),
        x12.Segment("CLP", [f"PCN-{random.randint(10000,99999)}", "1", "2500.00", "1850.00", "300.00", "12", f"WAY{random.randint(100000,999999)}", "11", "1"]),
        x12.Segment("NM1", ["QC", "1", "DOE", "JANE", "", "", "", "MI", "MEMBER123"]),
        x12.Segment("SVC", ["HC:99213", "200.00", "150.00", "", "1"]),
        x12.Segment("DTM", ["472", today]),
        x12.Segment("CAS", ["CO", "45", "50.00", "1"]),
        x12.Segment("CAS", ["PR", "2", "0.00"]),
        x12.Segment("SVC", ["HC:73721", "2300.00", "1700.00", "", "1"]),
        x12.Segment("DTM", ["472", today]),
        x12.Segment("CAS", ["CO", "45", "300.00"]),
        x12.Segment("CAS", ["PR", "1", "300.00"]),
    ]
    segments = x12._wrap_st_se("835", "0001", body)
    return x12.build_envelope(
        sender_id="WAYSTAR",
        receiver_id="RFAPORTAL",
        transactions=[("HP", segments)],
    )


# ── Factory ─────────────────────────────────────────────────────────────────

def get_waystar_client(org_settings: dict[str, Any] | None = None) -> WaystarApiClient:
    """Return a real or mock client depending on which credentials are present.

    Lookup order for credentials:
      1. ``org_settings`` (per-tenant) — keys: ``waystar_base_url``,
         ``waystar_client_id``, ``waystar_client_secret``, ``waystar_api_key``,
         ``waystar_submitter_id``, ``waystar_is_sandbox``.
      2. App settings (``WAYSTAR_*`` env vars).
      3. Falls back to ``MockWaystarApiClient`` so the UI/services still work.
    """
    org = org_settings or {}
    base_url = (
        org.get("waystar_base_url")
        or getattr(settings, "waystar_base_url", "")
    )
    client_id = org.get("waystar_client_id") or getattr(settings, "waystar_client_id", "")
    client_secret = org.get("waystar_client_secret") or getattr(settings, "waystar_client_secret", "")
    api_key = org.get("waystar_api_key") or getattr(settings, "waystar_api_key", "")
    submitter_id = org.get("waystar_submitter_id") or getattr(settings, "waystar_submitter_id", "RFAPORTAL")
    is_sandbox = bool(org.get("waystar_is_sandbox", getattr(settings, "waystar_is_sandbox", True)))

    if base_url and (api_key or (client_id and client_secret)):
        return WaystarApiClient(
            base_url=base_url,
            client_id=client_id or None,
            client_secret=client_secret or None,
            api_key=api_key or None,
            submitter_id=submitter_id,
            is_sandbox=is_sandbox,
        )
    logger.info("Waystar credentials not configured — using MockWaystarApiClient")
    return MockWaystarApiClient(submitter_id=submitter_id)
