"""RFA-2 Portal — Provider-side Prior Authorization models.

SQLAlchemy async models for the provider prior authorization workflow:
AuthRequest, AuthDocument, AuthLearning, PayerAuthProfile.
"""

import uuid
from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, Text, Integer, Float,
    ForeignKey, Index, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from ..database import Base


# ---------------------------------------------------------------------------
# Auth Request — the core prior authorization submission
# ---------------------------------------------------------------------------
class AuthRequest(Base):
    __tablename__ = "rfa_auth_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("rfa_organizations.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("rfa_users.id"), nullable=False)

    # Patient info
    patient_name = Column(String(200), nullable=False)
    patient_dob = Column(Date, nullable=False)
    patient_mrn = Column(String(50), nullable=False)

    # Workers' comp (optional — not all auths are WC)
    wcb_case_number = Column(String(20), nullable=True)
    date_of_injury = Column(Date, nullable=True)

    # Diagnosis
    diagnosis_primary = Column(String(200), nullable=False)
    diagnosis_codes = Column(Text, nullable=False)  # comma-separated ICD-10

    # Proposed procedure
    proposed_procedure = Column(String(200), nullable=False)
    proposed_cpt_codes = Column(Text, nullable=False)  # comma-separated

    # Surgeon
    surgeon_name = Column(String(200), nullable=False)
    surgeon_npi = Column(String(20), nullable=False)

    # Payer
    payer_name = Column(String(200), nullable=False)
    payer_id = Column(String(50), nullable=False)
    insurance_type = Column(String(30), nullable=False)  # commercial, medicare, medicaid, workers_comp, self_pay

    # Auth lifecycle
    auth_number = Column(String(50), nullable=True)  # assigned after approval
    status = Column(
        String(30), nullable=False, default="draft",
    )  # draft, documents_uploaded, narrative_generated, submitted, approved,
    #    denied, appealed, appeal_approved, appeal_denied,
    #    peer_to_peer_scheduled, peer_to_peer_completed

    # AI-generated narrative
    narrative = Column(Text, nullable=True)
    narrative_version = Column(Integer, nullable=False, default=0)

    # Denial handling
    denial_reason = Column(Text, nullable=True)
    denial_date = Column(Date, nullable=True)

    # Appeal handling
    appeal_letter = Column(Text, nullable=True)
    appeal_date = Column(Date, nullable=True)
    appeal_outcome = Column(String(20), nullable=True)

    # Peer-to-peer
    peer_to_peer_notes = Column(Text, nullable=True)
    peer_to_peer_date = Column(Date, nullable=True)

    # Approval
    approved_date = Column(Date, nullable=True)
    approved_procedure = Column(String(200), nullable=True)

    # AI-extracted summaries
    conservative_treatment_summary = Column(Text, nullable=True)
    imaging_summary = Column(Text, nullable=True)
    functional_scores = Column(Text, nullable=True)  # ODI, NDI, VAS

    # Urgency
    clinical_urgency = Column(String(20), nullable=True)  # routine, urgent, emergent

    # Timestamps
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organization = relationship("RFAOrganization", lazy="selectin")
    creator = relationship("RFAUser", lazy="selectin")
    documents = relationship("AuthDocument", back_populates="auth_request", lazy="selectin")
    learnings = relationship("AuthLearning", back_populates="auth_request", lazy="selectin")

    __table_args__ = (
        Index("ix_rfa_auth_requests_org_id", "org_id"),
        Index("ix_rfa_auth_requests_created_by", "created_by"),
        Index("ix_rfa_auth_requests_status", "status"),
        Index("ix_rfa_auth_requests_payer_name", "payer_name"),
        Index("ix_rfa_auth_requests_insurance_type", "insurance_type"),
        Index("ix_rfa_auth_requests_patient_mrn", "patient_mrn"),
        Index("ix_rfa_auth_requests_surgeon_npi", "surgeon_npi"),
        Index("ix_rfa_auth_requests_created_at", "created_at"),
    )


# ---------------------------------------------------------------------------
# Auth Document — uploaded clinical documents
# ---------------------------------------------------------------------------
class AuthDocument(Base):
    __tablename__ = "rfa_auth_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    auth_request_id = Column(UUID(as_uuid=True), ForeignKey("rfa_auth_requests.id"), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("rfa_organizations.id"), nullable=False)

    doc_type = Column(String(30), nullable=False)
    # clinical_note, mri_report, ct_report, xray_report, pt_records,
    # injection_records, emg_report, medication_history, operative_report,
    # prom_scores, c4_form, ime_report, other

    file_name = Column(String(500), nullable=False)
    s3_key = Column(String(500), nullable=False)
    clean_text = Column(Text, nullable=True)  # de-identified for AI
    extracted_data = Column(JSONB, nullable=True)  # structured data AI extracted
    mime_type = Column(String(100), nullable=True)
    size_bytes = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    auth_request = relationship("AuthRequest", back_populates="documents")

    __table_args__ = (
        Index("ix_rfa_auth_documents_auth_request_id", "auth_request_id"),
        Index("ix_rfa_auth_documents_org_id", "org_id"),
        Index("ix_rfa_auth_documents_doc_type", "doc_type"),
    )


# ---------------------------------------------------------------------------
# Auth Learning — outcome tracking for AI improvement
# ---------------------------------------------------------------------------
class AuthLearning(Base):
    __tablename__ = "rfa_auth_learning"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("rfa_organizations.id"), nullable=False)
    auth_request_id = Column(UUID(as_uuid=True), ForeignKey("rfa_auth_requests.id"), nullable=False)

    payer_name = Column(String(200), nullable=False)
    insurance_type = Column(String(30), nullable=False)
    procedure_category = Column(String(50), nullable=False)  # spine_fusion, spine_decompression, joint_replacement, etc.
    diagnosis_category = Column(String(50), nullable=False)

    narrative_text = Column(Text, nullable=True)  # the narrative that was submitted
    outcome = Column(String(20), nullable=False)  # approved, denied

    denial_reason = Column(Text, nullable=True)
    approval_factors = Column(JSONB, nullable=True)  # what elements correlated with approval
    denial_factors = Column(JSONB, nullable=True)   # what elements correlated with denial
    learning_notes = Column(Text, nullable=True)    # AI analysis of why approved/denied

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    auth_request = relationship("AuthRequest", back_populates="learnings")

    __table_args__ = (
        Index("ix_rfa_auth_learning_org_id", "org_id"),
        Index("ix_rfa_auth_learning_auth_request_id", "auth_request_id"),
        Index("ix_rfa_auth_learning_payer_name", "payer_name"),
        Index("ix_rfa_auth_learning_procedure_category", "procedure_category"),
        Index("ix_rfa_auth_learning_outcome", "outcome"),
        Index("ix_rfa_auth_learning_payer_procedure", "payer_name", "procedure_category"),
    )


# ---------------------------------------------------------------------------
# Payer Auth Profile — aggregated payer intelligence
# ---------------------------------------------------------------------------
class PayerAuthProfile(Base):
    __tablename__ = "rfa_payer_auth_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("rfa_organizations.id"), nullable=False)

    payer_name = Column(String(200), nullable=False)
    insurance_type = Column(String(30), nullable=False)

    # Stats
    total_auths = Column(Integer, nullable=False, default=0)
    approved_count = Column(Integer, nullable=False, default=0)
    denied_count = Column(Integer, nullable=False, default=0)
    approval_rate = Column(Float, nullable=True)
    avg_days_to_decision = Column(Float, nullable=True)

    # AI-learned intelligence
    common_denial_reasons = Column(JSONB, nullable=True)
    required_documents = Column(JSONB, nullable=True)  # what this payer specifically requires
    preferred_narrative_style = Column(Text, nullable=True)  # AI-learned preferred language
    tips = Column(Text, nullable=True)  # AI-generated tips for this payer

    # Timestamps
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_rfa_payer_auth_profiles_org_id", "org_id"),
        Index("ix_rfa_payer_auth_profiles_payer_name", "payer_name"),
        Index("ix_rfa_payer_auth_profiles_insurance_type", "insurance_type"),
        Index("ix_rfa_payer_auth_profiles_org_payer", "org_id", "payer_name", unique=True),
    )
