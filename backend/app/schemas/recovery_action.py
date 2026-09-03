from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.models.recovery_action import ActionType, ActionStatus


class RecoveryActionBase(BaseModel):
    case_id: str
    action_type: ActionType
    status: ActionStatus = ActionStatus.SCHEDULED
    channel: str = "GATEWAY"
    idempotency_key: str
    rzp_payment_link_id: Optional[str] = None
    rzp_short_url: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    policy_passed: str = "YES"
    policy_rule_notes: Optional[str] = None
    scheduled_at: datetime = Field(default_factory=datetime.utcnow)


class RecoveryActionCreate(RecoveryActionBase):
    pass


class RecoveryActionResponse(RecoveryActionBase):
    id: str
    executed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
