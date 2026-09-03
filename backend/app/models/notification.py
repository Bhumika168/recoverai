import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid(prefix: str = "notif") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class MerchantNotification(Base):
    __tablename__ = "merchant_notifications"

    id = Column(String(36), primary_key=True, default=lambda: generate_uuid("notif"), index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String(32), default="INFO", nullable=False)  # "INFO", "WARNING", "CRITICAL", "SUCCESS"
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    related_case_id = Column(String(36), ForeignKey("recovery_cases.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    organization = relationship("Organization", backref="merchant_notifications")
    related_case = relationship("RecoveryCase", backref="merchant_notifications")
