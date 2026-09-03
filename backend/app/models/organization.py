import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, Integer, Float, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid(prefix: str = "org") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=lambda: generate_uuid("org"), index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)

    # Workspace Profile (Step 01)
    industry = Column(String(100), nullable=True)
    company_size = Column(String(50), nullable=True)
    country = Column(String(100), nullable=True)
    currency = Column(String(10), default="INR", nullable=False)
    environment = Column(String(32), default="Production", nullable=True)
    onboarding_completed = Column(Boolean, default=False, nullable=False)

    # Recovery Guardrails (Step 02)
    max_retries = Column(Integer, default=3, nullable=False)
    high_value_threshold = Column(Float, default=25000.0, nullable=False)
    require_human_approval = Column(Boolean, default=True, nullable=False)
    hard_decline_behavior = Column(String(32), default="SUPPRESS", nullable=False)  # SUPPRESS, FLAG, NOTIFY
    auto_escalate_rules = Column(String(64), default="AFTER_MAX_RETRIES", nullable=False)
    auto_retry_enabled = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    memberships = relationship("OrganizationMembership", back_populates="organization", cascade="all, delete-orphan")
    customers = relationship("Customer", back_populates="organization", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="organization", cascade="all, delete-orphan")
    recovery_cases = relationship("RecoveryCase", back_populates="organization", cascade="all, delete-orphan")


class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"

    id = Column(String(36), primary_key=True, default=lambda: generate_uuid("mbr"), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(32), default="OWNER", nullable=False)  # OWNER, ADMIN, ANALYST, VIEWER

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_user_organization"),
    )

    # Relationships
    user = relationship("User", back_populates="memberships")
    organization = relationship("Organization", back_populates="memberships")


class OrganizationInvitation(Base):
    __tablename__ = "organization_invitations"

    id = Column(String(36), primary_key=True, default=lambda: generate_uuid("inv"), index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    role = Column(String(32), default="MEMBER", nullable=False)  # ADMIN, MEMBER, VIEWER
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    token_prefix = Column(String(12), nullable=False)
    status = Column(String(32), default="PENDING", nullable=False)  # PENDING, ACCEPTED, REVOKED, EXPIRED
    expires_at = Column(DateTime(timezone=True), nullable=False)
    invited_by_user_id = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    organization = relationship("Organization", backref="invitations")
