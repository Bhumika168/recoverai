import uuid
from datetime import datetime, timezone
import enum
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Enum, Index
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid(prefix: str = "att") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class AttemptStatus(str, enum.Enum):
    INITIATED = "INITIATED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PaymentAttempt(Base):
    __tablename__ = "payment_attempts"

    id = Column(String(36), primary_key=True, default=lambda: generate_uuid("att"), index=True)
    transaction_id = Column(String(36), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_number = Column(Integer, default=1, nullable=False)
    
    # Razorpay payment attempt references
    rzp_payment_id = Column(String(64), nullable=True, index=True)
    status = Column(Enum(AttemptStatus), default=AttemptStatus.INITIATED, nullable=False, index=True)
    
    error_code = Column(String(128), nullable=True)
    error_description = Column(String(512), nullable=True)
    gateway_response = Column(JSON, nullable=True, default=dict)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    transaction = relationship("Transaction", back_populates="payment_attempts")

    __table_args__ = (
        Index("ix_attempts_txn_attempt", "transaction_id", "attempt_number"),
    )
