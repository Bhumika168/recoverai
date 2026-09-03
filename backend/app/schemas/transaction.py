from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.models.transaction import TransactionStatus, PaymentMethod


class TransactionBase(BaseModel):
    customer_id: str
    amount: float = Field(gt=0, description="Amount in currency major units (e.g. INR)")
    currency: str = "INR"
    status: TransactionStatus = TransactionStatus.CREATED
    payment_method: PaymentMethod = PaymentMethod.UNKNOWN
    
    transaction_id: Optional[str] = None
    customer_email: Optional[str] = None
    
    invoice_id: Optional[str] = None
    subscription_id: Optional[str] = None
    rzp_order_id: Optional[str] = None
    rzp_payment_id: Optional[str] = None
    rzp_invoice_id: Optional[str] = None
    
    failure_code: Optional[str] = None
    failure_reason: Optional[str] = None
    failure_source: Optional[str] = None
    error_step: Optional[str] = None
    extra_metadata: Optional[Dict[str, Any]] = None
    transaction_time: Optional[datetime] = None


class TransactionCreate(TransactionBase):
    pass


class ManualTransactionCreate(BaseModel):
    transaction_id: Optional[str] = None
    customer_email: Optional[str] = None
    customer_name: Optional[str] = None
    customer_id: Optional[str] = None
    amount: float = Field(gt=0)
    currency: str = "INR"
    status: str = "FAILED"
    failure_code: Optional[str] = None
    failure_reason: Optional[str] = None
    payment_method: str = "CARD"
    timestamp: Optional[str] = None
    invoice_id: Optional[str] = None
    subscription_id: Optional[str] = None


class FailedTransactionIngest(BaseModel):
    customer_email: str
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    amount: float = Field(gt=0)
    currency: str = "INR"
    payment_method: PaymentMethod = PaymentMethod.CARD
    transaction_id: Optional[str] = None
    invoice_id: Optional[str] = None
    subscription_id: Optional[str] = None
    rzp_order_id: Optional[str] = None
    rzp_payment_id: Optional[str] = None
    failure_code: str = Field(description="e.g. BAD_REQUEST_PAYMENT_TIMED_OUT, CARD_STOLEN, INSUFFICIENT_FUNDS")
    failure_reason: str = Field(description="Human readable gateway description")
    failure_source: Optional[str] = "issuer"
    error_step: Optional[str] = "payment_authorization"
    extra_metadata: Optional[Dict[str, Any]] = None


class TransactionResponse(TransactionBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
