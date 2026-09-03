import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid(prefix: str = "dec") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class AIDecision(Base):
    __tablename__ = "ai_decisions"

    id = Column(String(36), primary_key=True, default=lambda: generate_uuid("dec"), index=True)
    case_id = Column(String(36), ForeignKey("recovery_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Diagnosis
    failure_category = Column(String(64), nullable=False, index=True) 
    # e.g., ISSUER_DOWNTIME, INSUFFICIENT_FUNDS, NETWORK_DROPOUT, HARD_DECLINE, CHECKOUT_ABANDONMENT, AUTHENTICATION_FAILED
    
    root_cause_explanation = Column(String(1024), nullable=False)
    confidence_score = Column(Float, nullable=False) # 0.0 to 1.0
    recovery_probability = Column(Float, nullable=False) # 0.0 to 1.0
    
    # Reasoning Chain & Structured Rationale
    reasoning_steps = Column(JSON, nullable=False, default=list)
    risk_factors = Column(JSON, nullable=False, default=list)
    
    # Recommendation
    recommended_action = Column(String(64), nullable=False) # DELAYED_RETRY, PAYMENT_LINK, SWITCH_METHOD, NO_ACTION, HUMAN_ESCALATION
    recommended_delay_minutes = Column(Integer, default=0, nullable=False)
    recommended_channel = Column(String(32), default="GATEWAY", nullable=False)
    
    # LLM Meta
    model_name = Column(String(64), default="gemini-2.5-flash", nullable=False)
    prompt_tokens = Column(Integer, default=0, nullable=False)
    completion_tokens = Column(Integer, default=0, nullable=False)
    latency_ms = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    recovery_case = relationship("RecoveryCase", back_populates="ai_decisions")

    __table_args__ = (
        Index("ix_decisions_case_created", "case_id", "created_at"),
    )
