from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class OrganizationUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    industry: Optional[str] = Field(None, max_length=100)
    company_size: Optional[str] = Field(None, max_length=50)
    country: Optional[str] = Field(None, max_length=100)
    currency: Optional[str] = Field(None, min_length=3, max_length=10)
    onboarding_completed: Optional[bool] = None
    
    # Recovery Guardrails
    max_retries: Optional[int] = Field(None, ge=1, le=10)
    high_value_threshold: Optional[float] = Field(None, ge=0.0)
    require_human_approval: Optional[bool] = None
    hard_decline_behavior: Optional[str] = None
    auto_escalate_rules: Optional[str] = None
    auto_retry_enabled: Optional[bool] = None


class OrganizationDetailsResponse(BaseModel):
    id: str
    name: str
    slug: str
    industry: Optional[str] = None
    company_size: Optional[str] = None
    country: Optional[str] = None
    currency: str = "INR"
    onboarding_completed: bool = False
    max_retries: int = 3
    high_value_threshold: float = 25000.0
    require_human_approval: bool = True
    hard_decline_behavior: str = "SUPPRESS"
    auto_escalate_rules: str = "AFTER_MAX_RETRIES"
    auto_retry_enabled: bool = True
    role: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
