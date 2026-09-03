import re
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Response, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.exceptions import RecoverAIException
from app.models.user import User
from app.models.organization import Organization, OrganizationMembership
from app.schemas.auth import (
    SignUpRequest,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    AuthResponse,
    UserResponse,
    OrganizationResponse,
    MessageResponse,
)
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    create_password_reset_token,
    verify_and_consume_reset_token,
    revoke_token,
    decode_access_token,
)
from app.api.deps import get_current_user, get_current_org_context, extract_token_from_request

router = APIRouter(prefix="/auth", tags=["Authentication"])


def slugify(text: str) -> str:
    """Generate a clean slug for organization names."""
    slug = re.sub(r"[^\w\s-]", "", text).strip().lower()
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug or "org"


def set_auth_cookie(response: Response, token: str):
    """Set secure HttpOnly cookie for session token."""
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/",
    )


def clear_auth_cookie(response: Response):
    """Clear session cookie on logout."""
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/",
    )


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignUpRequest, response: Response, db: AsyncSession = Depends(get_db)):
    """Register a new user, create an organization, and establish membership."""
    normalized_email = payload.email.strip().lower()

    # Check for existing email
    query = select(User).where(User.email == normalized_email)
    result = await db.execute(query)
    if result.scalars().first():
        raise RecoverAIException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
            error_code="EMAIL_ALREADY_EXISTS",
        )

    # 1. Create User
    hashed_pwd = hash_password(payload.password)
    user = User(
        email=normalized_email,
        full_name=payload.full_name.strip(),
        hashed_password=hashed_pwd,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    await db.flush()

    # 2. Create Organization
    org_name = payload.company_name.strip() if payload.company_name else f"{payload.full_name.strip()}'s Org"
    base_slug = slugify(org_name)
    unique_slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"

    org = Organization(
        name=org_name,
        slug=unique_slug,
    )
    db.add(org)
    await db.flush()

    # 3. Create Membership
    membership = OrganizationMembership(
        user_id=user.id,
        organization_id=org.id,
        role="OWNER",
    )
    db.add(membership)
    await db.commit()

    # 4. Issue session token
    token = create_access_token({"sub": user.id, "org_id": org.id, "email": user.email})
    set_auth_cookie(response, token)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        organization=OrganizationResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            industry=org.industry,
            company_size=org.company_size,
            country=org.country,
            currency=org.currency or "INR",
            onboarding_completed=org.onboarding_completed,
            max_retries=org.max_retries,
            high_value_threshold=org.high_value_threshold,
            auto_retry_enabled=org.auto_retry_enabled,
            role=membership.role,
        ),
        access_token=token,
    )


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    """Authenticate user with email and password."""
    normalized_email = payload.email.strip().lower()

    query = (
        select(User)
        .options(selectinload(User.memberships).selectinload(OrganizationMembership.organization))
        .where(User.email == normalized_email)
    )
    result = await db.execute(query)
    user = result.scalars().first()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise RecoverAIException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            error_code="INVALID_CREDENTIALS",
        )

    if not user.is_active:
        raise RecoverAIException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended. Please contact support.",
            error_code="ACCOUNT_INACTIVE",
        )

    membership = user.memberships[0] if user.memberships else None
    if not membership or not membership.organization:
        raise RecoverAIException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have an active organization membership.",
            error_code="NO_ORGANIZATION",
        )

    org = membership.organization
    token = create_access_token({"sub": user.id, "org_id": org.id, "email": user.email})
    set_auth_cookie(response, token)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        organization=OrganizationResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            industry=org.industry,
            company_size=org.company_size,
            country=org.country,
            currency=org.currency or "INR",
            onboarding_completed=org.onboarding_completed,
            max_retries=org.max_retries,
            high_value_threshold=org.high_value_threshold,
            auto_retry_enabled=org.auto_retry_enabled,
            role=membership.role,
        ),
        access_token=token,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Invalidate session server-side, revoke token, and clear session cookie."""
    token = extract_token_from_request(request)
    if token:
        try:
            payload = decode_access_token(token)
            user_id = payload.get("sub") if payload else None
            await revoke_token(token, user_id, db)
        except Exception:
            pass

    clear_auth_cookie(response)
    return MessageResponse(success=True, message="Successfully logged out.")


@router.get("/me", response_model=AuthResponse)
async def get_current_user_profile(
    user: User = Depends(get_current_user),
    org_context: tuple = Depends(get_current_org_context),
):
    """Retrieve current authenticated user and active organization details."""
    org, membership = org_context
    token = create_access_token({"sub": user.id, "org_id": org.id, "email": user.email})

    return AuthResponse(
        user=UserResponse.model_validate(user),
        organization=OrganizationResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            industry=org.industry,
            company_size=org.company_size,
            country=org.country,
            currency=org.currency or "INR",
            onboarding_completed=org.onboarding_completed,
            max_retries=org.max_retries,
            high_value_threshold=org.high_value_threshold,
            auto_retry_enabled=org.auto_retry_enabled,
            role=membership.role,
        ),
        access_token=token,
    )


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Request a password reset link. Returns generic response for privacy."""
    normalized_email = payload.email.strip().lower()

    query = select(User).where(User.email == normalized_email, User.is_active == True)
    result = await db.execute(query)
    user = result.scalars().first()

    if user:
        await create_password_reset_token(user.id, db)
        await db.commit()

    return MessageResponse(
        success=True,
        message="If an account exists with that email, password reset instructions have been dispatched.",
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Reset password using a valid, non-expired reset token."""
    user = await verify_and_consume_reset_token(payload.token, db)
    if not user:
        raise RecoverAIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid, expired, or previously used password reset token.",
            error_code="INVALID_RESET_TOKEN",
        )

    user.hashed_password = hash_password(payload.new_password)
    await db.commit()

    return MessageResponse(
        success=True,
        message="Password has been reset successfully. You may now sign in with your new credentials.",
    )
