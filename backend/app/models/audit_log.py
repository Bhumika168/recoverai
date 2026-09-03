import uuid
import hashlib
import json
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from app.database import Base


def generate_uuid(prefix: str = "aud") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def calculate_hash(
    entity_name: str = "RecoveryCase",
    entity_id: str = "N/A",
    event_type: str = "EVENT",
    actor: str = "SYSTEM",
    state_after: dict = None,
    prev_hash: str = "GENESIS_RECOVERAI",
    timestamp_iso: str = None,
    **kwargs,
) -> str:
    payload = {
        "entity_name": entity_name,
        "entity_id": entity_id,
        "event_type": event_type,
        "actor": actor,
        "state_after": state_after or {},
        "prev_hash": prev_hash or "GENESIS_RECOVERAI",
    }
    if timestamp_iso:
        payload["timestamp_iso"] = timestamp_iso
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: generate_uuid("aud"), index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    entity_name = Column(String(64), nullable=False, index=True)
    entity_id = Column(String(64), nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    actor = Column(String(64), nullable=False)  # SYSTEM, AI_AGENT, MERCHANT_USER, WEBHOOK
    
    state_before = Column(JSON, nullable=True)
    state_after = Column(JSON, nullable=False)
    
    # Hash chain integrity
    prev_hash = Column(String(64), nullable=True)
    sha256_hash = Column(String(64), nullable=False, unique=True, index=True)
    timestamp_iso = Column(String(64), nullable=False)
    notes = Column(String(512), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
