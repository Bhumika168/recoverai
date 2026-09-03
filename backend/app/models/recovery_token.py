import uuid
import enum
import hashlib
from datetime import datetime, timezone, timedelta
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, JSON, Index, Text
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid(prefix: str = "tok") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def hash_token(raw_token: str) -> str:
    """Computes SHA-256 hash of a raw recovery token for secure storage & indexed lookup."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class TokenStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    USED = "USED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class RecoveryToken(Base):
    __tablename__ = "recovery_tokens"

    id = Column(String(36), primary_key=True, default=lambda: generate_uuid("tok"), index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    recovery_case_id = Column(String(36), ForeignKey("recovery_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Hashed token for secure O(1) indexed lookup without plaintext exposure
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    token_prefix = Column(String(12), nullable=False)  # First few chars for log diagnostics
    
    action_type = Column(String(64), default="PAYMENT_LINK", nullable=False)  # PAYMENT_LINK, PAYMENT_METHOD_UPDATE, etc.
    status = Column(Enum(TokenStatus), default=TokenStatus.ACTIVE, nullable=False, index=True)
    
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    
    provider_reference = Column(String(255), nullable=True)  # Provider checkout session / order / intent ID
    token_metadata = Column(JSON, nullable=True, default=dict)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    organization = relationship("Organization", backref="recovery_tokens")
    recovery_case = relationship("RecoveryCase", backref="recovery_tokens")

    @property
    def is_valid(self) -> bool:
        if self.status != TokenStatus.ACTIVE:
            return False
        now_dt = datetime.now(timezone.utc)
        if self.expires_at.tzinfo is None:
            return self.expires_at.replace(tzinfo=timezone.utc) > now_dt
        return self.expires_at > now_dt
