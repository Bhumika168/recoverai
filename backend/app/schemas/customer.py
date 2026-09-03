from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class CustomerBase(BaseModel):
    email: EmailStr
    phone: Optional[str] = None
    name: Optional[str] = None
    rzp_customer_id: Optional[str] = None
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    recovery_receptivity_score: float = Field(default=0.5, ge=0.0, le=1.0)
    extra_metadata: Optional[Dict[str, Any]] = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    risk_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    recovery_receptivity_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    extra_metadata: Optional[Dict[str, Any]] = None


class CustomerResponse(CustomerBase):
    id: str
    lifetime_recovered_amount: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
