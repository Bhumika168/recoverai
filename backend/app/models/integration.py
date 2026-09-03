import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid(prefix: str = "conn") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class PaymentProviderConnection(Base):
    __tablename__ = "payment_provider_connections"

    id = Column(String(36), primary_key=True, default=lambda: generate_uuid("conn"), index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(50), nullable=False, index=True)  # "STRIPE", "RAZORPAY", "PAYPAL", "CASHFREE", "MOCK"
    status = Column(String(50), default="NOT_CONNECTED", nullable=False)  # "NOT_CONNECTED", "CONNECTED", "ERROR", "DISCONNECTED"
    environment = Column(String(20), default="TEST", nullable=False)  # "TEST", "LIVE"
    
    api_key_masked = Column(String(100), nullable=True)
    webhook_secret_masked = Column(String(100), nullable=True)
    raw_credentials_encrypted = Column(JSON, nullable=True)  # Secure encrypted credential payload
    webhook_url = Column(String(255), nullable=True)
    
    events_received_count = Column(Integer, default=0, nullable=False)
    events_processed_count = Column(Integer, default=0, nullable=False)
    events_failed_count = Column(Integer, default=0, nullable=False)
    
    last_webhook_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(String(500), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    organization = relationship("Organization", backref="provider_connections")

    __table_args__ = (
        UniqueConstraint("organization_id", "provider", name="uq_org_provider"),
    )


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(String(36), primary_key=True, default=lambda: generate_uuid("evt"), index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(50), nullable=False, index=True)
    provider_event_id = Column(String(100), nullable=True, index=True)
    event_type = Column(String(100), nullable=False)
    payload_hash = Column(String(64), nullable=False, index=True)
    
    processing_status = Column(String(50), default="PROCESSED", nullable=False)  # "PROCESSED", "DUPLICATE", "REJECTED", "FAILED"
    processing_time_ms = Column(Float, default=0.0, nullable=False)
    
    normalized_event = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    received_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    processed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=True)

    organization = relationship("Organization", backref="webhook_events")
