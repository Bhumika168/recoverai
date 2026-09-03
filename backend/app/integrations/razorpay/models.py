from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class RazorpayCustomerPayload(BaseModel):
    name: Optional[str] = None
    email: str
    contact: Optional[str] = None
    notes: Optional[Dict[str, str]] = Field(default_factory=dict)


class RazorpayCustomerResponse(BaseModel):
    id: str
    name: Optional[str] = None
    email: str
    contact: Optional[str] = None
    created_at: Optional[int] = None


class RazorpayOrderPayload(BaseModel):
    amount: int = Field(gt=0, description="Amount in smallest currency sub-unit (paise for INR)")
    currency: str = "INR"
    receipt: Optional[str] = None
    notes: Optional[Dict[str, str]] = Field(default_factory=dict)
    partial_payment: bool = False


class RazorpayOrderResponse(BaseModel):
    id: str
    entity: str = "order"
    amount: int
    amount_paid: int = 0
    amount_due: int = 0
    currency: str = "INR"
    receipt: Optional[str] = None
    status: str
    attempts: int = 0
    notes: Dict[str, Any] = Field(default_factory=dict)
    created_at: int


class RazorpayPaymentLinkPayload(BaseModel):
    amount: int = Field(gt=0, description="Amount in paise for INR")
    currency: str = "INR"
    accept_partial: bool = False
    description: str
    customer: Optional[Dict[str, Any]] = None
    notify: Optional[Dict[str, bool]] = Field(default_factory=lambda: {"sms": True, "email": True})
    reminder_enable: bool = True
    notes: Optional[Dict[str, str]] = Field(default_factory=dict)
    callback_url: Optional[str] = None
    callback_method: str = "get"
    expire_by: Optional[int] = None  # Unix timestamp in seconds


class RazorpayPaymentLinkResponse(BaseModel):
    id: str
    short_url: str
    amount: int
    currency: str = "INR"
    status: str
    description: str
    customer: Optional[Dict[str, Any]] = None
    amount_paid: int = 0
    expire_by: Optional[int] = None
    created_at: int


class RazorpayPaymentResponse(BaseModel):
    id: str
    entity: str = "payment"
    amount: int
    currency: str = "INR"
    status: str  # created, authorized, captured, refunded, failed
    order_id: Optional[str] = None
    invoice_id: Optional[str] = None
    method: str  # card, netbanking, wallet, emi, upi
    amount_refunded: int = 0
    refund_status: Optional[str] = None
    captured: bool = False
    description: Optional[str] = None
    email: Optional[str] = None
    contact: Optional[str] = None
    error_code: Optional[str] = None
    error_description: Optional[str] = None
    error_source: Optional[str] = None
    error_step: Optional[str] = None
    error_reason: Optional[str] = None
    created_at: int


class RazorpayWebhookEvent(BaseModel):
    entity: str = "event"
    account_id: str
    event: str  # payment.failed, payment.captured, payment.authorized, order.paid, payment_link.paid
    contains: List[str]
    payload: Dict[str, Any]
    created_at: int
