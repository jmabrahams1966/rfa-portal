"""WCB OnBoard API Client — OAuth2 + REST + SignalR for RFA-1LC/AIRA submission.

Authentication flow:
1. POST to Token URL with Client ID + Client Secret (OAuth2 Client Credentials)
2. Receive access_token
3. POST XML to Access URL with Bearer token
4. Connect to SignalR for real-time acknowledgment notifications

Based on WCB eForms Registration Instructions (April 2026).
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Optional

import httpx
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class WCBApiClient:
    """Client for NYS Workers' Compensation Board OnBoard eForms API."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_url: str,
        access_url: str,
        sender_poi: str,  # R-number of the submitting attorney/firm
        system_name: str = "RFA-Portal",
        is_sandbox: bool = True,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.access_url = access_url
        self.sender_poi = sender_poi
        self.system_name = system_name
        self.is_sandbox = is_sandbox
        self._access_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None

    async def _get_access_token(self) -> str:
        """Get OAuth2 access token using Client Credentials grant."""
        if self._access_token and self._token_expires and datetime.utcnow() < self._token_expires:
            return self._access_token

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                self.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            token_data = response.json()

        self._access_token = token_data["access_token"]
        expires_in = token_data.get("expires_in", 3600)
        from datetime import timedelta
        self._token_expires = datetime.utcnow() + timedelta(seconds=expires_in - 60)  # 60s buffer

        logger.info("WCB OAuth2 token obtained, expires in %d seconds", expires_in)
        return self._access_token

    async def submit_xml(self, xml_payload: str, transaction_id: str = None) -> dict:
        """Submit XML to WCB OnBoard API.

        Args:
            xml_payload: Complete XML string matching eFormsRfa1lc.xsd schema
            transaction_id: Unique transaction sequence number

        Returns:
            dict with submission_id, status, and any immediate response data
        """
        token = await self._get_access_token()

        if not transaction_id:
            transaction_id = str(uuid.uuid4().int)[:12]

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/xml",
            "X-System-Name": self.system_name,
            "X-Transaction-Id": transaction_id,
        }

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                self.access_url,
                content=xml_payload.encode("utf-8"),
                headers=headers,
            )

        if response.status_code in (200, 201, 202):
            logger.info("WCB submission accepted: %s", response.text[:200])
            return {
                "success": True,
                "status_code": response.status_code,
                "response": response.text,
                "transaction_id": transaction_id,
            }
        else:
            logger.error("WCB submission failed: %d — %s", response.status_code, response.text[:500])
            return {
                "success": False,
                "status_code": response.status_code,
                "error": response.text,
                "transaction_id": transaction_id,
            }

    async def check_status(self, submission_id: str) -> dict:
        """Check status of a previously submitted eForm (if endpoint available)."""
        token = await self._get_access_token()
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.access_url}/status/{submission_id}",
                    headers={"Authorization": f"Bearer {token}"},
                )
                return response.json()
        except Exception as e:
            logger.error("WCB status check failed: %s", e)
            return {"error": str(e)}


class MockWCBApiClient(WCBApiClient):
    """Mock client for development/testing without real WCB credentials."""

    def __init__(self, **kwargs):
        super().__init__(
            client_id="mock-client-id",
            client_secret="mock-secret",
            token_url="https://mock.wcb.ny.gov/token",
            access_url="https://mock.wcb.ny.gov/api/eforms",
            sender_poi="R999999",
            is_sandbox=True,
            **kwargs,
        )

    async def _get_access_token(self) -> str:
        return "mock-access-token"

    async def submit_xml(self, xml_payload: str, transaction_id: str = None) -> dict:
        import random
        tid = transaction_id or str(uuid.uuid4().int)[:12]
        submission_id = f"WCB-{datetime.utcnow().strftime('%Y')}-{random.randint(100000, 999999)}"

        # Simulate 90% success rate
        if random.random() < 0.9:
            return {
                "success": True,
                "status_code": 202,
                "submission_id": submission_id,
                "document_id": f"DOC-{random.randint(100000000, 999999999)}",
                "transaction_id": tid,
                "message": "Submission accepted for processing. Acknowledgment will be sent via SignalR.",
            }
        else:
            return {
                "success": False,
                "status_code": 400,
                "transaction_id": tid,
                "error": "Validation error: WCBCaseID not found or sender not authorized for this case.",
                "errors": [
                    {"field": "WCBCaseID", "code": "E001", "message": "Case not found in WCB system"},
                ],
            }


def get_wcb_client(org_settings: dict = None) -> WCBApiClient:
    """Factory — returns real or mock client based on configuration."""
    if org_settings and org_settings.get("wcb_client_id"):
        return WCBApiClient(
            client_id=org_settings["wcb_client_id"],
            client_secret=org_settings["wcb_client_secret"],
            token_url=org_settings["wcb_token_url"],
            access_url=org_settings["wcb_access_url"],
            sender_poi=org_settings.get("wcb_sender_poi", ""),
            system_name=org_settings.get("wcb_system_name", "RFA-Portal"),
            is_sandbox=org_settings.get("wcb_is_sandbox", True),
        )
    return MockWCBApiClient()


# ── SignalR Acknowledgment Listener ──────────────────────────────────────────

SIGNALR_INSTRUCTIONS = """
SignalR Integration Notes (for production):

The WCB uses Microsoft SignalR for real-time acknowledgment delivery.
After submitting via API, the WCB processes the submission asynchronously
and sends the acknowledgment (accept/reject with errors) via SignalR.

To implement:
1. Install: pip install signalrcore
2. Connect to WCB SignalR hub URL (provided after registration)
3. Register handler for "ReceiveAcknowledgment" event
4. Parse the acknowledgment XML using eFormsXMLAckTemplate.xml format
5. Update submission status in database

The origin URL of your server must be registered with WCB for
SignalR security pass-through.

Contact: eForms@wcb.ny.gov for SignalR endpoint details.
"""


def parse_acknowledgment_xml(ack_xml: str) -> dict:
    """Parse WCB acknowledgment XML response."""
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(ack_xml)
        ns = {"": ""}  # WCB may or may not use namespaces

        result = {
            "file_status": "",
            "file_status_message": "",
            "events": [],
        }

        # File-level status
        fs = root.find("FileStatus")
        if fs is not None and fs.text:
            result["file_status"] = fs.text
        fsm = root.find("FileStatusMessage")
        if fsm is not None and fsm.text:
            result["file_status_message"] = fsm.text

        # Event-level results
        events = root.find("Events")
        if events is not None:
            for event in events:
                ev = {
                    "wcb_case_id": "",
                    "transaction_id": "",
                    "submission_id": "",
                    "status": "",
                    "errors": [],
                }
                for child in event:
                    tag = child.tag
                    if tag == "WCBCaseID" and child.text:
                        ev["wcb_case_id"] = child.text
                    elif tag == "TransactionSequenceNumber" and child.text:
                        ev["transaction_id"] = child.text
                    elif tag == "SubmissionId" and child.text:
                        ev["submission_id"] = child.text
                    elif tag == "SubmissionStatus" and child.text:
                        ev["status"] = child.text
                    elif tag == "Errors":
                        for err in child:
                            error = {}
                            for err_field in err:
                                error[err_field.tag] = err_field.text or ""
                            ev["errors"].append(error)
                result["events"].append(ev)

        return result
    except Exception as e:
        return {"error": f"Failed to parse acknowledgment: {e}", "raw": ack_xml[:500]}
