import uuid
from datetime import datetime, timezone
import enum
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, JSON, Index, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid(prefix: str = "cmp") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class CampaignChannel(str, enum.Enum):
    MULTI_CHANNEL = "MULTI_CHANNEL"
    SMS = "SMS"
    WHATSAPP = "WHATSAPP"
    EMAIL = "EMAIL"
    SMART_LINK = "SMART_LINK"


class CampaignStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(String(36), primary_key=True, default=lambda: generate_uuid("cmp"), index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(512), nullable=True)
    
    recovery_type = Column(String(64), default="FAILED_PAYMENT", nullable=False)  # "FAILED_PAYMENT", "SUBSCRIPTION", "CHECKOUT_ABANDONED", "OVERDUE_INVOICE", "PAYMENT_METHOD_UPDATE", "MANDATE_RETRY"
    status = Column(String(32), default="ACTIVE", nullable=False, index=True)  # "DRAFT", "ACTIVE", "PAUSED", "COMPLETED", "ARCHIVED"
    
    target_segment = Column(String(64), default="ALL_FAILURES", nullable=False)  # "ALL_FAILURES", "HIGH_VALUE", "CART_ABANDONED", "RECURRING_SUB"
    channel = Column(Enum(CampaignChannel), default=CampaignChannel.MULTI_CHANNEL, nullable=False)
    channels_list = Column(JSON, default=lambda: ["EMAIL", "SMS", "WHATSAPP"], nullable=True)
    
    min_amount = Column(Float, default=0.0, nullable=False)
    max_amount = Column(Float, default=1000000.0, nullable=False)
    max_recovery_attempts = Column(Integer, default=3, nullable=False)
    retry_delay_hours = Column(Integer, default=24, nullable=False)
    escalation_rules = Column(JSON, default=lambda: {"escalate_after_attempts": 3, "require_approval_above": 50000.0}, nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Real Persisted Performance Metrics
    enrolled_cases_count = Column(Integer, default=0, nullable=False)
    messages_sent_count = Column(Integer, default=0, nullable=False)
    actions_executed_count = Column(Integer, default=0, nullable=False)
    total_targeted_count = Column(Integer, default=0, nullable=False)
    total_recovered_count = Column(Integer, default=0, nullable=False)
    total_revenue_recovered = Column(Float, default=0.0, nullable=False)
    recovered_amount = Column(Float, default=0.0, nullable=False)
    recovery_rate = Column(Float, default=0.0, nullable=False)  # 0.0 to 100.0 %
    
    configuration = Column(JSON, nullable=True, default=dict)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    last_activity_at = Column(DateTime(timezone=True), nullable=True)

    organization = relationship("Organization", backref="campaigns")

    __table_args__ = (
        Index("ix_campaigns_org_status", "organization_id", "status"),
    )
