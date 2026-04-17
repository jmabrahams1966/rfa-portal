"""RFA-2 Portal — SQLAlchemy async models for Workers' Compensation RFA submissions."""
import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, Text, Integer, ForeignKey, Index, JSON,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ..database import Base


# ---------------------------------------------------------------------------
# RFA Organization
# ---------------------------------------------------------------------------
class RFAOrganization(Base):
    __tablename__ = "rfa_organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    org_type = Column(String(50), nullable=False)  # carrier / tpa / self_insured / law_firm
    w_number = Column(String(50), nullable=True)   # WCB carrier number
    wcb_user_id = Column(String(100), nullable=True)
    plan_tier = Column(String(50), nullable=False, default="starter")  # starter / growth / enterprise
    is_active = Column(Boolean, default=True, nullable=False)
    contact_name = Column(String(255), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    users = relationship("RFAUser", back_populates="organization", lazy="selectin")
    cases = relationship("RFACase", back_populates="organization", lazy="selectin")
    submissions = relationship("RFASubmission", back_populates="organization", lazy="selectin")


# ---------------------------------------------------------------------------
# RFA User
# ---------------------------------------------------------------------------
class RFAUser(Base):
    __tablename__ = "rfa_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("rfa_organizations.id"), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="adjuster")  # admin / adjuster / reviewer / read_only
    wcb_user_id = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization = relationship("RFAOrganization", back_populates="users")
    submissions = relationship("RFASubmission", back_populates="created_by_user", lazy="selectin")

    __table_args__ = (
        Index("ix_rfa_users_org_id", "org_id"),
        Index("ix_rfa_users_email", "email"),
    )


# ---------------------------------------------------------------------------
# RFA Case
# ---------------------------------------------------------------------------
class RFACase(Base):
    __tablename__ = "rfa_cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("rfa_organizations.id"), nullable=False)
    wcb_case_number = Column(String(100), nullable=False)
    claimant_name_encrypted = Column(Text, nullable=True)
    date_of_injury = Column(Date, nullable=True)
    employer_name = Column(String(255), nullable=True)
    employer_fein = Column(String(20), nullable=True)
    is_volunteer = Column(Boolean, default=False, nullable=False)
    claimant_rep_name = Column(String(255), nullable=True)
    claimant_rep_address = Column(Text, nullable=True)
    carrier_name = Column(String(255), nullable=True)
    carrier_code = Column(String(50), nullable=True)
    district = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    organization = relationship("RFAOrganization", back_populates="cases")
    submissions = relationship("RFASubmission", back_populates="case", lazy="selectin")

    __table_args__ = (
        Index("ix_rfa_cases_org_id", "org_id"),
        Index("ix_rfa_cases_wcb_case_number", "wcb_case_number"),
        Index("uq_rfa_cases_org_case", "org_id", "wcb_case_number", unique=True),
    )


# ---------------------------------------------------------------------------
# RFA Submission
# ---------------------------------------------------------------------------
class RFASubmission(Base):
    __tablename__ = "rfa_submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("rfa_organizations.id"), nullable=False)
    case_id = Column(UUID(as_uuid=True), ForeignKey("rfa_cases.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("rfa_users.id"), nullable=False)
    status = Column(String(50), nullable=False, default="draft")  # draft / validated / submitted / accepted / rejected
    reason_codes = Column(JSON, nullable=True)    # JSON array of reason codes
    form_data = Column(JSON, nullable=True)       # full form payload
    narrative = Column(Text, nullable=True)        # max 500 chars enforced at API layer
    xml_payload = Column(Text, nullable=True)
    wcb_submission_id = Column(String(100), nullable=True)
    wcb_document_id = Column(String(100), nullable=True)
    wcb_status = Column(String(50), nullable=True)
    wcb_errors = Column(JSON, nullable=True)
    certification_date = Column(Date, nullable=True)
    attestation_accepted = Column(Boolean, default=False, nullable=False)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    pdf_s3_key = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organization = relationship("RFAOrganization", back_populates="submissions")
    case = relationship("RFACase", back_populates="submissions")
    created_by_user = relationship("RFAUser", back_populates="submissions")
    documents = relationship("RFADocument", back_populates="submission", lazy="selectin")
    extractions = relationship("RFAExtraction", back_populates="submission", lazy="selectin")

    __table_args__ = (
        Index("ix_rfa_submissions_org_id", "org_id"),
        Index("ix_rfa_submissions_case_id", "case_id"),
        Index("ix_rfa_submissions_status", "status"),
        Index("ix_rfa_submissions_created_by", "created_by"),
    )


# ---------------------------------------------------------------------------
# RFA Document
# ---------------------------------------------------------------------------
class RFADocument(Base):
    __tablename__ = "rfa_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(UUID(as_uuid=True), ForeignKey("rfa_submissions.id"), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("rfa_organizations.id"), nullable=False)
    doc_type = Column(String(50), nullable=False)  # ime_report / board_decision / medical_record / operative_note / wage_records / surveillance / other
    file_name = Column(String(500), nullable=False)
    s3_key = Column(String(500), nullable=False)
    clean_text = Column(Text, nullable=True)  # de-identified extracted text
    mime_type = Column(String(100), nullable=True)
    size_bytes = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    submission = relationship("RFASubmission", back_populates="documents")
    extractions = relationship("RFAExtraction", back_populates="document", lazy="selectin")

    __table_args__ = (
        Index("ix_rfa_documents_submission_id", "submission_id"),
        Index("ix_rfa_documents_org_id", "org_id"),
    )


# ---------------------------------------------------------------------------
# RFA Extraction
# ---------------------------------------------------------------------------
class RFAExtraction(Base):
    __tablename__ = "rfa_extractions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(UUID(as_uuid=True), ForeignKey("rfa_submissions.id"), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("rfa_documents.id"), nullable=True)
    reason_codes = Column(JSON, nullable=True)       # JSON array
    extracted_fields = Column(JSON, nullable=True)   # JSON object
    confidence = Column(String(20), nullable=True)    # high / medium / low
    narrative_text = Column(Text, nullable=True)
    model_version = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    submission = relationship("RFASubmission", back_populates="extractions")
    document = relationship("RFADocument", back_populates="extractions")

    __table_args__ = (
        Index("ix_rfa_extractions_submission_id", "submission_id"),
        Index("ix_rfa_extractions_document_id", "document_id"),
    )


# ---------------------------------------------------------------------------
# RFA Audit Log
# ---------------------------------------------------------------------------
class RFAAuditLog(Base):
    __tablename__ = "rfa_audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    user_email = Column(String(255), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    description = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_rfa_audit_logs_org_id", "org_id"),
        Index("ix_rfa_audit_logs_user_id", "user_id"),
        Index("ix_rfa_audit_logs_action", "action"),
    )


# ---------------------------------------------------------------------------
# RFA Case Assignment (Team Workflow)
# ---------------------------------------------------------------------------
class RFACaseAssignment(Base):
    __tablename__ = "rfa_case_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("rfa_cases.id"), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("rfa_organizations.id"), nullable=False)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("rfa_users.id"), nullable=False)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("rfa_users.id"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(String(50), nullable=False, default="active")  # active / completed / reassigned

    __table_args__ = (
        Index("ix_rfa_case_assignments_case_id", "case_id"),
        Index("ix_rfa_case_assignments_org_id", "org_id"),
        Index("ix_rfa_case_assignments_assigned_to", "assigned_to"),
    )


# ---------------------------------------------------------------------------
# RFA Hearing (WCB Status Tracking)
# ---------------------------------------------------------------------------
class RFAHearing(Base):
    __tablename__ = "rfa_hearings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("rfa_cases.id"), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("rfa_organizations.id"), nullable=False)
    submission_id = Column(UUID(as_uuid=True), ForeignKey("rfa_submissions.id"), nullable=True)
    hearing_date = Column(DateTime(timezone=True), nullable=True)
    hearing_type = Column(String(100), nullable=True)
    location = Column(String(255), nullable=True)
    judge_name = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="scheduled")  # scheduled / completed / adjourned / cancelled
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_rfa_hearings_case_id", "case_id"),
        Index("ix_rfa_hearings_org_id", "org_id"),
        Index("ix_rfa_hearings_hearing_date", "hearing_date"),
    )


# ---------------------------------------------------------------------------
# RFA Task (Follow-up Tasks)
# ---------------------------------------------------------------------------
class RFATask(Base):
    __tablename__ = "rfa_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("rfa_cases.id"), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("rfa_organizations.id"), nullable=False)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("rfa_users.id"), nullable=True)
    task_type = Column(String(100), nullable=False)  # prepare_hearing / respond_objection / file_followup / deadline_approaching
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(Date, nullable=True)
    priority = Column(String(50), nullable=False, default="medium")  # low / medium / high / urgent
    status = Column(String(50), nullable=False, default="pending")  # pending / in_progress / completed
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_rfa_tasks_case_id", "case_id"),
        Index("ix_rfa_tasks_org_id", "org_id"),
        Index("ix_rfa_tasks_assigned_to", "assigned_to"),
        Index("ix_rfa_tasks_due_date", "due_date"),
        Index("ix_rfa_tasks_status", "status"),
    )


# ---------------------------------------------------------------------------
# RFA Deadline (Deadline Engine)
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# RFA Narrative Pattern (Narrative AI Optimization)
# ---------------------------------------------------------------------------
class RFANarrativePattern(Base):
    __tablename__ = "rfa_narrative_patterns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=True)
    reason_code = Column(String(50), nullable=False)
    district = Column(String(100), nullable=False)
    pattern_text = Column(Text, nullable=False)
    success_count = Column(Integer, nullable=False, default=0)
    failure_count = Column(Integer, nullable=False, default=0)
    effectiveness_rate = Column(String(20), nullable=True)
    last_used = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_rfa_narrative_patterns_reason_district", "reason_code", "district"),
        Index("ix_rfa_narrative_patterns_org_id", "org_id"),
    )


# ---------------------------------------------------------------------------
# RFA Attorney Profile (Attorney Intelligence)
# ---------------------------------------------------------------------------
class RFAAttorneyProfile(Base):
    __tablename__ = "rfa_attorney_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attorney_name = Column(String(255), unique=True, nullable=False)
    total_cases = Column(Integer, nullable=False, default=0)
    objection_rate = Column(String(20), nullable=True)
    settlement_rate = Column(String(20), nullable=True)
    avg_days_to_resolution = Column(String(20), nullable=True)
    common_objections = Column(JSON, nullable=True)
    districts_active = Column(JSON, nullable=True)
    last_updated = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_rfa_attorney_profiles_name", "attorney_name"),
    )


# ---------------------------------------------------------------------------
# RFA Deadline (Deadline Engine)
# ---------------------------------------------------------------------------
class RFADeadline(Base):
    __tablename__ = "rfa_deadlines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("rfa_cases.id"), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("rfa_organizations.id"), nullable=False)
    submission_id = Column(UUID(as_uuid=True), ForeignKey("rfa_submissions.id"), nullable=True)
    deadline_type = Column(String(100), nullable=False)
    trigger_event = Column(String(255), nullable=False)
    trigger_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    status = Column(String(50), nullable=False, default="upcoming")  # upcoming / due_soon / overdue / met / missed
    alert_sent = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_rfa_deadlines_case_id", "case_id"),
        Index("ix_rfa_deadlines_org_id", "org_id"),
        Index("ix_rfa_deadlines_due_date", "due_date"),
        Index("ix_rfa_deadlines_status", "status"),
    )
