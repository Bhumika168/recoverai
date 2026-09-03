from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.models.recovery_case import CaseStatus
from app.schemas.transaction import TransactionResponse
from app.schemas.customer import CustomerResponse
from app.schemas.ai_decision import AIDecisionResponse
from app.schemas.recovery_action import RecoveryActionResponse


class RecoveryCaseBase(BaseModel):
    transaction_id: str
    customer_id: str
    status: CaseStatus = CaseStatus.OPEN
    amount_at_risk: float
    recovered_amount: float = 0.0
    recovery_score: int = Field(default=50, ge=0, le=100)
    risk_level: str = "MEDIUM"
    retry_count: int = 0
    max_retries_allowed: int = 3
    next_retry_at: Optional[datetime] = None
    strategy_summary: Optional[str] = None
    requires_human_approval: str = "NO"
    approval_reason: Optional[str] = None
    extra_metadata: Optional[Dict[str, Any]] = None


class RecoveryCaseCreate(RecoveryCaseBase):
    pass


class RecoveryCaseUpdate(BaseModel):
    status: Optional[CaseStatus] = None
    recovered_amount: Optional[float] = None
    recovery_score: Optional[int] = Field(default=None, ge=0, le=100)
    retry_count: Optional[int] = None
    next_retry_at: Optional[datetime] = None
    strategy_summary: Optional[str] = None
    requires_human_approval: Optional[str] = None
    approval_reason: Optional[str] = None
    extra_metadata: Optional[Dict[str, Any]] = None


class RecoveryCaseResponse(RecoveryCaseBase):
    id: str
    created_at: datetime
    updated_at: datetime
    recovered_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class RecoveryCaseDetailResponse(RecoveryCaseResponse):
    transaction: Optional[TransactionResponse] = None
    customer: Optional[CustomerResponse] = None
    ai_decisions: List[AIDecisionResponse] = Field(default_factory=list)
    actions: List[RecoveryActionResponse] = Field(default_factory=list)
