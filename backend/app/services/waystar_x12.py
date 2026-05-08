"""ASC X12 EDI parser/builder for healthcare transactions used with Waystar.

Supports the four transaction sets the RFA portal interacts with:
  - 270  Eligibility Inquiry            (request)
  - 271  Eligibility Response           (response)
  - 837P Health Care Claim Professional (request)
  - 835  Health Care Claim Payment/ERA  (response)

The implementation is intentionally dependency-free. It models X12 at the
segment/element level so callers can pass structured Python dicts in and get
either an X12 string or a parsed dict back.

X12 envelope reminder:

    ISA*...~                  Interchange header
      GS*...~                 Functional group header
        ST*270*0001~          Transaction set header
          ...transaction segments...
        SE*N*0001~            Transaction set trailer
      GE*1*1~                 Functional group trailer
    IEA*1*000000001~          Interchange trailer

Element separator defaults to ``*``, sub-element to ``:``, segment terminator
to ``~``. They are read from the ISA when parsing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable


# ── Delimiters ──────────────────────────────────────────────────────────────

@dataclass
class EDIDelimiters:
    element: str = "*"
    sub_element: str = ":"
    segment: str = "~"
    repetition: str = "^"

    @classmethod
    def from_isa(cls, raw: str) -> "EDIDelimiters":
        """Pull delimiters from the first 106 chars of an ISA segment."""
        if len(raw) < 106 or not raw.startswith("ISA"):
            return cls()
        element = raw[3]
        repetition = raw[82]
        sub_element = raw[104]
        segment = raw[105]
        return cls(
            element=element,
            sub_element=sub_element,
            segment=segment,
            repetition=repetition,
        )


# ── Generic segment model ───────────────────────────────────────────────────

@dataclass
class Segment:
    tag: str
    elements: list[str] = field(default_factory=list)

    def get(self, idx: int, default: str = "") -> str:
        """1-indexed element accessor (X12 convention: NM101 -> idx=1)."""
        return self.elements[idx - 1] if 0 < idx <= len(self.elements) else default

    def to_string(self, d: EDIDelimiters) -> str:
        body = d.element.join([self.tag] + self.elements)
        return body + d.segment


def tokenize(raw: str) -> tuple[EDIDelimiters, list[Segment]]:
    """Split a raw X12 string into segments using delimiters from the ISA."""
    raw = raw.strip().lstrip("﻿")
    if not raw.startswith("ISA"):
        raise ValueError("X12 payload must begin with an ISA segment")
    d = EDIDelimiters.from_isa(raw)
    chunks = [c.strip() for c in raw.split(d.segment) if c.strip()]
    segments: list[Segment] = []
    for chunk in chunks:
        # Normalize embedded newlines from pretty-printed X12.
        clean = chunk.replace("\r", "").replace("\n", "")
        if not clean:
            continue
        parts = clean.split(d.element)
        segments.append(Segment(tag=parts[0], elements=parts[1:]))
    return d, segments


# ── Envelope ────────────────────────────────────────────────────────────────

@dataclass
class TransactionSet:
    transaction_id: str        # 270 / 271 / 837 / 835
    control_number: str
    segments: list[Segment]    # segments between ST and SE inclusive

    def find_all(self, tag: str) -> list[Segment]:
        return [s for s in self.segments if s.tag == tag]

    def first(self, tag: str) -> Segment | None:
        for s in self.segments:
            if s.tag == tag:
                return s
        return None


@dataclass
class EDIDocument:
    delimiters: EDIDelimiters
    isa: Segment
    iea: Segment
    transactions: list[TransactionSet]

    @property
    def sender_id(self) -> str:
        return self.isa.get(6).strip()

    @property
    def receiver_id(self) -> str:
        return self.isa.get(8).strip()

    @property
    def interchange_control_number(self) -> str:
        return self.isa.get(13).strip()


def parse_envelope(raw: str) -> EDIDocument:
    """Parse ISA/GS/ST/.../SE/GE/IEA into structured transaction sets."""
    d, segments = tokenize(raw)
    isa = segments[0]
    iea = next((s for s in reversed(segments) if s.tag == "IEA"), None)
    if iea is None:
        raise ValueError("Missing IEA trailer")

    transactions: list[TransactionSet] = []
    cursor = 0
    while cursor < len(segments):
        seg = segments[cursor]
        if seg.tag == "ST":
            tx_id = seg.get(1)
            ctrl = seg.get(2)
            body: list[Segment] = [seg]
            cursor += 1
            while cursor < len(segments) and segments[cursor].tag != "SE":
                body.append(segments[cursor])
                cursor += 1
            if cursor < len(segments):
                body.append(segments[cursor])  # SE
            transactions.append(TransactionSet(tx_id, ctrl, body))
        cursor += 1

    return EDIDocument(delimiters=d, isa=isa, iea=iea, transactions=transactions)


# ── Envelope builder ────────────────────────────────────────────────────────

def _isa_id(value: str, length: int = 15) -> str:
    return (value or "")[:length].ljust(length)


def _today() -> tuple[str, str, str]:
    now = datetime.utcnow()
    return now.strftime("%y%m%d"), now.strftime("%H%M"), now.strftime("%Y%m%d")


def build_envelope(
    *,
    sender_id: str,
    receiver_id: str,
    sender_qualifier: str = "ZZ",
    receiver_qualifier: str = "ZZ",
    transactions: list[tuple[str, list[Segment]]],   # [(functional_id, segments)]
    icn: int = 1,
    gcn: int = 1,
    usage: str = "T",          # T=test, P=production
    delimiters: EDIDelimiters | None = None,
) -> str:
    """Wrap pre-built transaction segments in ISA/GS/.../GE/IEA."""
    d = delimiters or EDIDelimiters()
    yymmdd, hhmm, ccyymmdd = _today()
    icn_str = f"{icn:09d}"
    gcn_str = str(gcn)

    isa = Segment(
        tag="ISA",
        elements=[
            "00", "          ",          # auth qualifier + info (10)
            "00", "          ",          # security qualifier + info (10)
            sender_qualifier, _isa_id(sender_id),
            receiver_qualifier, _isa_id(receiver_id),
            yymmdd, hhmm,
            d.repetition,                # repetition separator (ISA11)
            "00501",                     # version
            icn_str,
            "0",                         # ack requested
            usage,
            d.sub_element,               # component element separator
        ],
    )

    out: list[Segment] = [isa]
    for functional_id, tx_segments in transactions:
        gs = Segment(
            tag="GS",
            elements=[
                functional_id,            # HS=270/271, HC=837, HP=835
                sender_id, receiver_id,
                ccyymmdd, hhmm,
                gcn_str,
                "X",                      # responsible agency
                "005010X" + ({"HS":"279A1","HB":"279A1","HC":"222A1","HP":"221A1"}.get(functional_id, "279A1")),
            ],
        )
        out.append(gs)
        out.extend(tx_segments)
        out.append(Segment(tag="GE", elements=["1", gcn_str]))

    out.append(Segment(tag="IEA", elements=["1", icn_str]))
    return "".join(s.to_string(d) for s in out)


# ── Helpers for transaction builders ────────────────────────────────────────

def _wrap_st_se(transaction_id: str, control_number: str, body: list[Segment]) -> list[Segment]:
    impl_ref = {
        "270": "005010X279A1",
        "271": "005010X279A1",
        "837": "005010X222A1",
        "835": "005010X221A1",
    }.get(transaction_id, "005010X279A1")
    st = Segment(tag="ST", elements=[transaction_id, control_number, impl_ref])
    se = Segment(tag="SE", elements=[str(len(body) + 2), control_number])
    return [st, *body, se]


def _format_dob(value: str | None) -> str:
    if not value:
        return ""
    s = str(value).replace("-", "").replace("/", "")
    if len(s) == 8 and s.isdigit():
        return s
    try:
        return datetime.fromisoformat(str(value)).strftime("%Y%m%d")
    except Exception:
        return ""


# ── 270 Eligibility Inquiry builder ─────────────────────────────────────────

def build_270(
    *,
    payer_name: str,
    payer_id: str,
    provider_name: str,
    provider_npi: str,
    subscriber_first: str,
    subscriber_last: str,
    subscriber_member_id: str,
    subscriber_dob: str,
    service_date: str | None = None,
    service_type_codes: Iterable[str] = ("30",),    # 30 = health benefit plan coverage
    control_number: str = "0001",
    trace_number: str = "10000000001",
) -> list[Segment]:
    """Return the segments (ST..SE) for a 270 eligibility inquiry.

    Pass them to ``build_envelope(..., transactions=[("HS", segments)])``.
    """
    yymmdd, hhmm, ccyymmdd = _today()
    body: list[Segment] = [
        Segment("BHT", ["0022", "13", trace_number, ccyymmdd, hhmm]),
        # 2100A — Information Source (payer)
        Segment("HL", ["1", "", "20", "1"]),
        Segment("NM1", ["PR", "2", payer_name, "", "", "", "", "PI", payer_id]),
        # 2100B — Information Receiver (provider)
        Segment("HL", ["2", "1", "21", "1"]),
        Segment("NM1", ["1P", "2", provider_name, "", "", "", "", "XX", provider_npi]),
        # 2100C — Subscriber
        Segment("HL", ["3", "2", "22", "0"]),
        Segment("TRN", ["1", trace_number, provider_npi.zfill(10)]),
        Segment("NM1", [
            "IL", "1", subscriber_last, subscriber_first, "", "", "", "MI",
            subscriber_member_id,
        ]),
        Segment("DMG", ["D8", _format_dob(subscriber_dob)]),
    ]
    if service_date:
        body.append(Segment("DTP", ["291", "D8", _format_dob(service_date)]))
    for stc in service_type_codes:
        body.append(Segment("EQ", [stc]))

    return _wrap_st_se("270", control_number, body)


# ── 271 parser ──────────────────────────────────────────────────────────────

EB_CODE_LABELS = {
    "1": "Active Coverage",
    "2": "Active - Full Risk Capitation",
    "3": "Active - Services Capitated",
    "4": "Active - Services Capitated to Primary Care Physician",
    "5": "Active - Pending Investigation",
    "6": "Inactive",
    "7": "Inactive - Pending Eligibility Update",
    "8": "Inactive - Pending Investigation",
    "A": "Co-Insurance",
    "B": "Co-Payment",
    "C": "Deductible",
    "G": "Out of Pocket (Stop Loss)",
    "F": "Limitations",
    "I": "Non-Covered",
    "L": "Primary Care Provider",
    "MC": "Managed Care Coordinator",
    "N": "Services Restricted to Following Provider",
    "R": "Other or Additional Payor",
    "U": "Contact Following Entity for Eligibility or Benefit Information",
    "V": "Cannot Process",
    "X": "Health Care Facility",
    "Y": "Spend Down",
}


def parse_271(transaction: TransactionSet) -> dict[str, Any]:
    """Convert a 271 transaction set into a structured dict."""
    if transaction.transaction_id != "271":
        raise ValueError(f"Expected 271, got {transaction.transaction_id}")

    out: dict[str, Any] = {
        "transaction_id": "271",
        "trace": "",
        "payer": {},
        "provider": {},
        "subscriber": {},
        "dependent": None,
        "benefits": [],
        "errors": [],
    }

    current_loop: str | None = None
    current_party: dict[str, Any] | None = None
    current_eb: dict[str, Any] | None = None

    for seg in transaction.segments:
        tag = seg.tag

        if tag == "BHT":
            out["trace"] = seg.get(3)

        elif tag == "HL":
            level = seg.get(3)
            current_loop = {
                "20": "payer", "21": "provider",
                "22": "subscriber", "23": "dependent",
            }.get(level)
            if current_loop == "dependent":
                out["dependent"] = {}
            current_party = out.get(current_loop) if current_loop else None
            current_eb = None

        elif tag == "NM1" and current_party is not None:
            current_party["entity_id"] = seg.get(1)
            current_party["last_or_org"] = seg.get(3)
            current_party["first"] = seg.get(4)
            current_party["middle"] = seg.get(5)
            current_party["id_qualifier"] = seg.get(8)
            current_party["id"] = seg.get(9)

        elif tag == "DMG" and current_party is not None:
            current_party["dob"] = seg.get(2)
            current_party["gender"] = seg.get(3)

        elif tag == "TRN":
            out["trace"] = seg.get(2) or out["trace"]

        elif tag == "EB":
            current_eb = {
                "code": seg.get(1),
                "code_label": EB_CODE_LABELS.get(seg.get(1), seg.get(1)),
                "coverage_level": seg.get(2),
                "service_type_codes": [c for c in seg.get(3).split(":") if c],
                "insurance_type": seg.get(4),
                "plan_description": seg.get(5),
                "time_period_qualifier": seg.get(6),
                "monetary_amount": seg.get(7),
                "percentage": seg.get(8),
                "messages": [],
                "dates": [],
            }
            out["benefits"].append(current_eb)

        elif tag == "MSG" and current_eb is not None:
            current_eb["messages"].append(seg.get(1))

        elif tag == "DTP" and current_eb is not None:
            current_eb["dates"].append({
                "qualifier": seg.get(1),
                "format": seg.get(2),
                "date": seg.get(3),
            })

        elif tag == "AAA":
            # Reject reasons at any loop level.
            out["errors"].append({
                "valid_request": seg.get(1),
                "reject_reason_code": seg.get(3),
                "follow_up_action_code": seg.get(4),
            })

    return out


# ── 837P (professional claim) builder ───────────────────────────────────────

@dataclass
class ServiceLine:
    procedure_code: str
    charge: float
    units: float = 1.0
    modifiers: list[str] = field(default_factory=list)
    diagnosis_pointers: list[int] = field(default_factory=lambda: [1])
    service_date: str | None = None
    place_of_service: str = "11"

    def composite(self, sub: str) -> str:
        parts = ["HC", self.procedure_code]
        for m in self.modifiers[:4]:
            parts.append(m)
        return sub.join(parts)


def build_837p(
    *,
    submitter_name: str,
    submitter_id: str,
    submitter_contact_name: str,
    submitter_phone: str,
    receiver_name: str,
    receiver_id: str,
    billing_provider_name: str,
    billing_provider_npi: str,
    billing_provider_tax_id: str,
    billing_address_line: str,
    billing_city: str,
    billing_state: str,
    billing_zip: str,
    subscriber_first: str,
    subscriber_last: str,
    subscriber_member_id: str,
    subscriber_dob: str,
    subscriber_gender: str,
    payer_name: str,
    payer_id: str,
    claim_id: str,
    total_charge: float,
    diagnosis_codes: list[str],
    service_lines: list[ServiceLine],
    place_of_service: str = "11",
    accept_assignment: str = "A",
    benefits_assignment: str = "Y",
    release_of_info: str = "Y",
    control_number: str = "0001",
    sub_element: str = ":",
) -> list[Segment]:
    """Return ST..SE segments for a single 837P claim."""
    yymmdd, hhmm, ccyymmdd = _today()

    body: list[Segment] = [
        Segment("BHT", ["0019", "00", claim_id, ccyymmdd, hhmm, "CH"]),
        # 1000A — Submitter
        Segment("NM1", ["41", "2", submitter_name, "", "", "", "", "46", submitter_id]),
        Segment("PER", ["IC", submitter_contact_name, "TE", submitter_phone]),
        # 1000B — Receiver
        Segment("NM1", ["40", "2", receiver_name, "", "", "", "", "46", receiver_id]),
        # 2000A — Billing provider
        Segment("HL", ["1", "", "20", "1"]),
        Segment("PRV", ["BI", "PXC", "207Q00000X"]),
        Segment("NM1", [
            "85", "2", billing_provider_name, "", "", "", "", "XX", billing_provider_npi,
        ]),
        Segment("N3", [billing_address_line]),
        Segment("N4", [billing_city, billing_state, billing_zip]),
        Segment("REF", ["EI", billing_provider_tax_id]),
        # 2000B — Subscriber
        Segment("HL", ["2", "1", "22", "0"]),
        Segment("SBR", ["P", "18", "", "", "", "", "", "", "CI"]),
        Segment("NM1", [
            "IL", "1", subscriber_last, subscriber_first, "", "", "", "MI",
            subscriber_member_id,
        ]),
        Segment("DMG", ["D8", _format_dob(subscriber_dob), subscriber_gender]),
        # 2010BB — Payer
        Segment("NM1", ["PR", "2", payer_name, "", "", "", "", "PI", payer_id]),
        # 2300 — Claim
        Segment("CLM", [
            claim_id,
            f"{total_charge:.2f}",
            "", "",
            sub_element.join([place_of_service, "B", "1"]),
            "Y",                       # provider/supplier signature
            accept_assignment,
            benefits_assignment,
            release_of_info,
        ]),
    ]

    # 2300 — Diagnosis codes (HI segment, ABK for principal, ABF for additional).
    if diagnosis_codes:
        hi_elements: list[str] = []
        for i, dx in enumerate(diagnosis_codes[:12]):
            qualifier = "ABK" if i == 0 else "ABF"
            hi_elements.append(sub_element.join([qualifier, dx]))
        body.append(Segment("HI", hi_elements))

    # 2400 — Service lines
    for idx, line in enumerate(service_lines, start=1):
        body.append(Segment("LX", [str(idx)]))
        body.append(Segment("SV1", [
            line.composite(sub_element),
            f"{line.charge:.2f}",
            "UN",
            f"{line.units:g}",
            line.place_of_service or place_of_service,
            "",
            sub_element.join(str(p) for p in (line.diagnosis_pointers or [1])[:4]),
        ]))
        if line.service_date:
            body.append(Segment("DTP", ["472", "D8", _format_dob(line.service_date)]))

    return _wrap_st_se("837", control_number, body)


# ── 835 (ERA) parser ────────────────────────────────────────────────────────

CAS_GROUP_LABELS = {
    "CO": "Contractual Obligations",
    "CR": "Correction and Reversal",
    "OA": "Other Adjustments",
    "PI": "Payor Initiated Reductions",
    "PR": "Patient Responsibility",
}

CLP_STATUS_LABELS = {
    "1": "Processed as Primary",
    "2": "Processed as Secondary",
    "3": "Processed as Tertiary",
    "4": "Denied",
    "19": "Processed as Primary, Forwarded to Additional Payer",
    "20": "Processed as Secondary, Forwarded to Additional Payer",
    "22": "Reversal of Previous Payment",
    "23": "Not Our Claim, Forwarded to Additional Payer",
    "25": "Predetermination Pricing Only - No Payment",
}


def parse_835(transaction: TransactionSet) -> dict[str, Any]:
    """Convert an 835 transaction set into a structured dict."""
    if transaction.transaction_id != "835":
        raise ValueError(f"Expected 835, got {transaction.transaction_id}")

    out: dict[str, Any] = {
        "transaction_id": "835",
        "payment": {},
        "trace": {},
        "payer": {},
        "payee": {},
        "claims": [],
    }

    current_claim: dict[str, Any] | None = None
    current_service: dict[str, Any] | None = None
    current_party_key: str | None = None

    for seg in transaction.segments:
        tag = seg.tag

        if tag == "BPR":
            out["payment"] = {
                "transaction_handling_code": seg.get(1),
                "amount": _safe_float(seg.get(2)),
                "credit_or_debit": seg.get(3),
                "method": seg.get(4),
                "sender_dfi": seg.get(7),
                "sender_account": seg.get(9),
                "receiver_dfi": seg.get(13),
                "receiver_account": seg.get(15),
                "effective_date": seg.get(16),
            }

        elif tag == "TRN":
            out["trace"] = {
                "type": seg.get(1),
                "reference_id": seg.get(2),
                "originator_id": seg.get(3),
            }

        elif tag == "N1":
            entity = seg.get(1)
            party_key = "payer" if entity == "PR" else ("payee" if entity == "PE" else None)
            if party_key:
                current_party_key = party_key
                out[party_key] = {
                    "name": seg.get(2),
                    "id_qualifier": seg.get(3),
                    "id": seg.get(4),
                }

        elif tag in ("N3", "N4") and current_party_key:
            party = out[current_party_key]
            if tag == "N3":
                party["address"] = seg.get(1)
            else:
                party["city"] = seg.get(1)
                party["state"] = seg.get(2)
                party["zip"] = seg.get(3)

        elif tag == "CLP":
            current_claim = {
                "patient_control_number": seg.get(1),
                "status_code": seg.get(2),
                "status": CLP_STATUS_LABELS.get(seg.get(2), seg.get(2)),
                "total_charge": _safe_float(seg.get(3)),
                "total_paid": _safe_float(seg.get(4)),
                "patient_responsibility": _safe_float(seg.get(5)),
                "claim_filing_indicator": seg.get(6),
                "payer_claim_control_number": seg.get(7),
                "facility_type": seg.get(8),
                "frequency_code": seg.get(9),
                "patient": {},
                "service_lines": [],
                "adjustments": [],
                "remarks": [],
            }
            out["claims"].append(current_claim)
            current_service = None

        elif tag == "NM1" and current_claim is not None:
            entity = seg.get(1)
            person = {
                "entity_id": entity,
                "last_or_org": seg.get(3),
                "first": seg.get(4),
                "id_qualifier": seg.get(8),
                "id": seg.get(9),
            }
            if entity in ("QC", "IL"):                # patient / insured
                current_claim["patient"] = person
            else:
                current_claim.setdefault("parties", []).append(person)

        elif tag == "SVC" and current_claim is not None:
            composite = seg.get(1).split(":")
            current_service = {
                "procedure_qualifier": composite[0] if composite else "",
                "procedure_code": composite[1] if len(composite) > 1 else "",
                "modifiers": composite[2:6] if len(composite) > 2 else [],
                "charge": _safe_float(seg.get(2)),
                "paid": _safe_float(seg.get(3)),
                "revenue_code": seg.get(4),
                "units": _safe_float(seg.get(5)),
                "adjustments": [],
                "remarks": [],
                "dates": [],
            }
            current_claim["service_lines"].append(current_service)

        elif tag == "CAS":
            target = current_service if current_service is not None else current_claim
            if target is not None:
                group = seg.get(1)
                # CAS supports up to 6 (reason_code, amount, quantity) triplets.
                for i in range(2, len(seg.elements), 3):
                    code = seg.get(i)
                    if not code:
                        continue
                    target.setdefault("adjustments", []).append({
                        "group_code": group,
                        "group_label": CAS_GROUP_LABELS.get(group, group),
                        "reason_code": code,
                        "amount": _safe_float(seg.get(i + 1)),
                        "quantity": _safe_float(seg.get(i + 2)),
                    })

        elif tag == "MIA" and current_claim is not None:
            current_claim["inpatient_adjudication"] = {
                "covered_days": seg.get(1),
                "lifetime_psych_days": seg.get(2),
                "claim_drg_amount": _safe_float(seg.get(3)),
            }

        elif tag == "MOA" and current_claim is not None:
            current_claim["outpatient_adjudication"] = {
                "reimbursement_rate": seg.get(1),
                "claim_hcpcs_payable_amount": _safe_float(seg.get(2)),
                "remark_codes": [e for e in seg.elements[2:7] if e],
            }

        elif tag == "DTM":
            entry = {"qualifier": seg.get(1), "date": seg.get(2)}
            if current_service is not None:
                current_service["dates"].append(entry)
            elif current_claim is not None:
                current_claim.setdefault("dates", []).append(entry)
            else:
                out.setdefault("dates", []).append(entry)

        elif tag == "LQ":
            target = current_service if current_service is not None else current_claim
            if target is not None:
                target.setdefault("remarks", []).append({
                    "code_list": seg.get(1),
                    "code": seg.get(2),
                })

    return out


def _safe_float(value: str) -> float:
    try:
        return float(value) if value not in ("", None) else 0.0
    except (TypeError, ValueError):
        return 0.0


# ── Convenience: parse any envelope and dispatch ─────────────────────────────

def parse_x12(raw: str) -> dict[str, Any]:
    """Parse a raw X12 string and return structured transactions.

    Returns ``{"interchange": {...}, "transactions": [{...}, ...]}`` where each
    transaction is the appropriate parsed shape (271, 835) or a raw segment list.
    """
    doc = parse_envelope(raw)
    out: dict[str, Any] = {
        "interchange": {
            "sender_id": doc.sender_id,
            "receiver_id": doc.receiver_id,
            "control_number": doc.interchange_control_number,
        },
        "transactions": [],
    }
    for tx in doc.transactions:
        if tx.transaction_id == "271":
            out["transactions"].append(parse_271(tx))
        elif tx.transaction_id == "835":
            out["transactions"].append(parse_835(tx))
        else:
            out["transactions"].append({
                "transaction_id": tx.transaction_id,
                "control_number": tx.control_number,
                "segments": [
                    {"tag": s.tag, "elements": s.elements} for s in tx.segments
                ],
            })
    return out
