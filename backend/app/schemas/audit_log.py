from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class AuditLogBase(BaseModel):
    entity_name: str
    entity_id: str
    event_type: str
    actor: str = "SYSTEM_AGENT"
    state_before: Optional[Dict[str, Any]] = None
    state_after: Dict[str, Any]
    prev_hash: Optional[str] = None
    notes: Optional[str] = None


class AuditLogCreate(AuditLogBase):
    sha256_hash: str


class AuditLogResponse(AuditLogBase):
    id: str
    sha256_hash: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLedgerVerification(BaseModel):
    is_valid: bool
    total_entries_verified: int
    invalid_entry_ids: List[str] = Field(default_factory=list)
    latest_hash: Optional[str] = None
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
