from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class SignUpRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    company_name: Optional[str] = Field(None, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrganizationResponse(BaseModel):
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
    auto_retry_enabled: bool = True
    role: str

    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    user: UserResponse
    organization: OrganizationResponse
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    success: bool
    message: str
