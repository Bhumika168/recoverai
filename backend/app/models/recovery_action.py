import uuid
from datetime import datetime, timezone
import enum
from sqlalchemy import Column, String, Float, DateTime, JSON, ForeignKey, Enum, Index
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid(prefix: str = "act") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class ActionType(str, enum.Enum):
    DELAYED_RETRY = "DELAYED_RETRY"
    PAYMENT_LINK = "PAYMENT_LINK"
    SMART_NOTIFICATION = "SMART_NOTIFICATION"
    SWITCH_METHOD = "SWITCH_METHOD"
    HUMAN_ESCALATION = "HUMAN_ESCALATION"
    NO_ACTION = "NO_ACTION"


class ActionStatus(str, enum.Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    SCHEDULED = "SCHEDULED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class RecoveryAction(Base):
    __tablename__ = "recovery_actions"

    id = Column(String(36), primary_key=True, default=lambda: generate_uuid("act"), index=True)
    case_id = Column(String(36), ForeignKey("recovery_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    
    action_type = Column(Enum(ActionType), nullable=False, index=True)
    status = Column(Enum(ActionStatus), default=ActionStatus.SCHEDULED, nullable=False, index=True)
    
    # Execution details
    channel = Column(String(32), default="GATEWAY", nullable=False) # GATEWAY, SMS, EMAIL, WHATSAPP, DASHBOARD
    idempotency_key = Column(String(64), unique=True, nullable=False, index=True)
    
    # Razorpay generated artifact references
    rzp_payment_link_id = Column(String(64), nullable=True, index=True)
    rzp_short_url = Column(String(255), nullable=True)
    
    # Payload & Result
    payload = Column(JSON, nullable=True, default=dict)
    result = Column(JSON, nullable=True, default=dict)
    
    # Policy check signature (verification that action passed policy before execution)
    policy_passed = Column(String(8), default="YES", nullable=False)
    policy_rule_notes = Column(String(512), nullable=True)

    scheduled_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    recovery_case = relationship("RecoveryCase", back_populates="actions")

    __table_args__ = (
        Index("ix_actions_case_status", "case_id", "status"),
    )
