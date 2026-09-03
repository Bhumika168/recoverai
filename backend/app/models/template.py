import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid(prefix: str = "tmpl") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class MessageTemplate(Base):
    __tablename__ = "message_templates"

    id = Column(String(36), primary_key=True, default=lambda: generate_uuid("tmpl"), index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    channel = Column(String(32), default="EMAIL", nullable=False)  # "EMAIL", "SMS", "WHATSAPP", "IN_APP"
    subject = Column(String(255), nullable=True)  # Subject for EMAIL/IN_APP
    body = Column(Text, nullable=False)
    language = Column(String(16), default="EN", nullable=False)  # "EN", "HI", "HINGLISH"
    status = Column(String(32), default="ACTIVE", nullable=False)  # "ACTIVE", "DRAFT"

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    organization = relationship("Organization", backref="message_templates")
