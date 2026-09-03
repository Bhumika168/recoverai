import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid(prefix: str = "case") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class CaseStatus(str, enum.Enum):
    DETECTED = "DETECTED"
    DIAGNOSED = "DIAGNOSED"
    POLICY_REVIEW = "POLICY_REVIEW"
    APPROVED = "APPROVED"
    ACTION_SCHEDULED = "ACTION_SCHEDULED"
    CUSTOMER_CONTACTED = "CUSTOMER_CONTACTED"
    RETRY_PENDING = "RETRY_PENDING"
    PAYMENT_ATTEMPTED = "PAYMENT_ATTEMPTED"
    VERIFICATION = "VERIFICATION"
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    RECOVERED = "RECOVERED"
    ESCALATED = "ESCALATED"
    EXHAUSTED = "EXHAUSTED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    UNRECOVERABLE = "UNRECOVERABLE"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class RecoveryCase(Base):
    __tablename__ = "recovery_cases"

    id = Column(String(36), primary_key=True, default=lambda: generate_uuid("case"), index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    campaign_id = Column(String(36), ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True)
    transaction_id = Column(String(36), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    
    status = Column(Enum(CaseStatus), default=CaseStatus.OPEN, nullable=False, index=True)
    amount_at_risk = Column(Float, nullable=False)
    recovered_amount = Column(Float, default=0.0, nullable=False)
    
    recovery_score = Column(Float, default=0.5, nullable=False)
    risk_level = Column(String(32), default="LOW", nullable=False)
    
    # Retry & state tracking
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries_allowed = Column(Integer, default=3, nullable=False)
    messages_sent_count = Column(Integer, default=0, nullable=False)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    
    strategy_summary = Column(String(1024), nullable=True)
    requires_human_approval = Column(String(5), default="false", nullable=False)
    approval_reason = Column(String(512), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    recovered_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="recovery_cases")
    campaign = relationship("Campaign", backref="enrolled_cases")
    transaction = relationship("Transaction", back_populates="recovery_case")
    customer = relationship("Customer", back_populates="recovery_cases")
    ai_decisions = relationship("AIDecision", back_populates="recovery_case", cascade="all, delete-orphan")
    actions = relationship("RecoveryAction", back_populates="recovery_case", cascade="all, delete-orphan")
