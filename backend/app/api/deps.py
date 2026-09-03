from typing import Optional, Tuple
from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.exceptions import RecoverAIException
from app.models.user import User
from app.models.organization import Organization, OrganizationMembership
from app.services.auth_service import decode_access_token, is_token_revoked


def extract_token_from_request(request: Request) -> Optional[str]:
    """Extract authentication token from Authorization header or cookie."""
    # 1. Check Authorization Bearer header (explicit API authorization)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:].strip()

    # 2. Check HttpOnly session cookie
    cookie_token = request.cookies.get(settings.COOKIE_NAME)
    if cookie_token:
        return cookie_token

    return None


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate token and resolve current authenticated User."""
    token = extract_token_from_request(request)
    if not token:
        raise RecoverAIException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
            error_code="UNAUTHENTICATED",
        )

    # Server-side token invalidation check (e.g. after logout)
    if await is_token_revoked(token, db):
        raise RecoverAIException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been terminated or logged out. Please sign in again.",
            error_code="SESSION_REVOKED",
        )

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise RecoverAIException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token.",
            error_code="INVALID_TOKEN",
        )

    user_id = payload["sub"]
    query = select(User).where(User.id == user_id, User.is_active == True)
    result = await db.execute(query)
    user = result.scalars().first()

    if not user:
        raise RecoverAIException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or inactive.",
            error_code="USER_NOT_FOUND",
        )

    return user


async def get_current_org_context(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Tuple[Organization, OrganizationMembership]:
    """Resolve the active Organization and Membership role for the authenticated user."""
    query = (
        select(OrganizationMembership)
        .options(selectinload(OrganizationMembership.organization))
        .where(OrganizationMembership.user_id == user.id)
    )
    result = await db.execute(query)
    membership = result.scalars().first()

    if not membership or not membership.organization:
        raise RecoverAIException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to an active organization.",
            error_code="NO_ORGANIZATION",
        )

    return membership.organization, membership


def require_role(allowed_roles: list[str]):
    """
    Role-Based Access Control (RBAC) Dependency.
    Ensures the user's role in the organization satisfies allowed roles.
    Supported: OWNER, ADMIN, MEMBER, VIEWER
    """
    async def role_checker(
        org_context: Tuple[Organization, OrganizationMembership] = Depends(get_current_org_context),
    ) -> Tuple[Organization, OrganizationMembership]:
        org, membership = org_context
        user_role = (membership.role or "MEMBER").upper()
        normalized_allowed = [r.upper() for r in allowed_roles]
        
        if user_role not in normalized_allowed:
            raise RecoverAIException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role in {normalized_allowed}, but user has role '{user_role}'.",
                error_code="INSUFFICIENT_PERMISSIONS",
            )
        return org, membership

    return role_checker


async def require_write_access(
    org_context: Tuple[Organization, OrganizationMembership] = Depends(get_current_org_context),
) -> Tuple[Organization, OrganizationMembership]:
    """Rejects read-only VIEWER role from state mutations."""
    org, membership = org_context
    if (membership.role or "MEMBER").upper() == "VIEWER":
        raise RecoverAIException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Action restricted: Read-only VIEWER accounts cannot modify resources.",
            error_code="VIEWER_READ_ONLY",
        )
    return org, membership

