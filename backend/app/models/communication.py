import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid(prefix: str = "com") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class CommunicationLog(Base):
    __tablename__ = "communication_logs"

    id = Column(String(36), primary_key=True, default=lambda: generate_uuid("com"), index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    recovery_case_id = Column(String(36), ForeignKey("recovery_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    template_id = Column(String(36), ForeignKey("message_templates.id", ondelete="SET NULL"), nullable=True)
    
    channel = Column(String(32), nullable=False)  # "EMAIL", "SMS", "WHATSAPP", "IN_APP", "WEBHOOK"
    recipient_reference = Column(String(255), nullable=False)  # email address or phone number
    provider_message_id = Column(String(100), nullable=True)
    
    subject = Column(String(255), nullable=True)
    rendered_body = Column(Text, nullable=False)
    
    status = Column(String(32), default="QUEUED", nullable=False)  # "QUEUED", "SENT", "DELIVERED", "FAILED", "BOUNCED", "CANCELLED"
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    error_code = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    organization = relationship("Organization", backref="communication_logs")
    recovery_case = relationship("RecoveryCase", backref="communication_logs")
    template = relationship("MessageTemplate", backref="communication_logs")


class CustomerOptOut(Base):
    __tablename__ = "customer_opt_outs"

    id = Column(String(36), primary_key=True, default=lambda: generate_uuid("opt"), index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_email = Column(String(255), nullable=True, index=True)
    customer_phone = Column(String(64), nullable=True, index=True)
    reason = Column(String(255), default="USER_UNSUBSCRIBED", nullable=False)
    opted_out_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    organization = relationship("Organization", backref="customer_opt_outs")

    __table_args__ = (
        UniqueConstraint("organization_id", "customer_email", name="uq_org_cust_email_optout"),
    )
