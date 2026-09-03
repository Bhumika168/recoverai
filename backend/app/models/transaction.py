import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, Enum, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid(prefix: str = "txn") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class TransactionStatus(str, enum.Enum):
    CREATED = "CREATED"
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    FAILED = "FAILED"
    ABANDONED = "ABANDONED"
    RECOVERED = "RECOVERED"
    REFUNDED = "REFUNDED"


class PaymentMethod(str, enum.Enum):
    CARD = "CARD"
    UPI = "UPI"
    NETBANKING = "NETBANKING"
    WALLET = "WALLET"
    EMI = "EMI"
    SUBSCRIPTION = "SUBSCRIPTION"
    UNKNOWN = "UNKNOWN"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=lambda: generate_uuid("txn"), index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    transaction_id = Column(String(128), nullable=True, index=True)  # Merchant-provided unique external ID within org
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_email = Column(String(255), nullable=True, index=True)
    
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.CREATED, nullable=False, index=True)
    payment_method = Column(Enum(PaymentMethod), default=PaymentMethod.UNKNOWN, nullable=False)
    
    # Provider-agnostic external references
    invoice_id = Column(String(128), nullable=True, index=True)
    subscription_id = Column(String(128), nullable=True, index=True)
    rzp_order_id = Column(String(64), nullable=True, index=True)
    rzp_payment_id = Column(String(64), nullable=True, index=True)
    rzp_invoice_id = Column(String(64), nullable=True)
    
    # Failure telemetry
    failure_code = Column(String(64), nullable=True, index=True)
    failure_reason = Column(String(512), nullable=True)
    failure_source = Column(String(64), nullable=True)  # issuer, gateway, customer, network
    error_step = Column(String(64), nullable=True)  # payment_authorization, payment_authentication
    extra_metadata = Column(JSON, nullable=True, default=dict)
    
    transaction_time = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="transactions")
    customer = relationship("Customer", back_populates="transactions")
    payment_attempts = relationship("PaymentAttempt", back_populates="transaction", cascade="all, delete-orphan")
    recovery_case = relationship("RecoveryCase", back_populates="transaction", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_org_transaction_external_id", "organization_id", "transaction_id"),
    )
