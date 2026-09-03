from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.models.payment_attempt import AttemptStatus


class PaymentAttemptBase(BaseModel):
    transaction_id: str
    attempt_number: int = Field(default=1, ge=1)
    rzp_payment_id: Optional[str] = None
    status: AttemptStatus = AttemptStatus.INITIATED
    error_code: Optional[str] = None
    error_description: Optional[str] = None
    gateway_response: Optional[Dict[str, Any]] = None


class PaymentAttemptCreate(PaymentAttemptBase):
    pass


class PaymentAttemptResponse(PaymentAttemptBase):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
