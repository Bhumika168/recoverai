import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid(prefix: str = "cust") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(36), primary_key=True, default=lambda: generate_uuid("cust"), index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    rzp_customer_id = Column(String(64), unique=True, nullable=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(32), nullable=True, index=True)
    name = Column(String(255), nullable=True)
    
    # Financial profile
    risk_score = Column(Float, default=0.0, nullable=False)  # 0.0 (safe) to 1.0 (high risk)
    recovery_receptivity_score = Column(Float, default=0.5, nullable=False)  # 0.0 to 1.0
    lifetime_recovered_amount = Column(Float, default=0.0, nullable=False)
    
    extra_metadata = Column(JSON, nullable=True, default=dict)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="customers")
    transactions = relationship("Transaction", back_populates="customer", cascade="all, delete-orphan")
    recovery_cases = relationship("RecoveryCase", back_populates="customer", cascade="all, delete-orphan")
