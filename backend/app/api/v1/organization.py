import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, EmailStr

from app.config import settings
from app.database import get_db
from app.models.organization import Organization, OrganizationMembership, OrganizationInvitation
from app.models.user import User
from app.models.audit_log import AuditLog, calculate_hash
from app.schemas.organization import OrganizationUpdateRequest, OrganizationDetailsResponse
from app.schemas.auth import MessageResponse
from app.schemas.common import APIResponse
from app.exceptions import RecoverAIException, EntityNotFoundException
from app.api.deps import get_current_org_context, get_current_user, require_role, require_write_access

router = APIRouter(prefix="/organization", tags=["Organization"])


class InviteMemberRequest(BaseModel):
    email: EmailStr
    role: str = "MEMBER"  # ADMIN, MEMBER, VIEWER


class UpdateMemberRoleRequest(BaseModel):
    role: str  # ADMIN, MEMBER, VIEWER


@router.get("/current", response_model=OrganizationDetailsResponse)
async def get_current_organization(
    org_context: tuple = Depends(get_current_org_context),
):
    """Retrieve details, onboarding state, and recovery policies of the authenticated organization."""
    org, membership = org_context
    return OrganizationDetailsResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        industry=org.industry,
        company_size=org.company_size,
        country=org.country,
        currency=org.currency,
        onboarding_completed=org.onboarding_completed,
        max_retries=org.max_retries,
        high_value_threshold=org.high_value_threshold,
        auto_retry_enabled=org.auto_retry_enabled,
        role=membership.role,
        created_at=org.created_at,
        updated_at=org.updated_at,
    )


@router.patch("/current", response_model=OrganizationDetailsResponse)
async def update_current_organization(
    payload: OrganizationUpdateRequest,
    org_context: tuple = Depends(require_role(["OWNER", "ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    """Update profile details, custom recovery policies, or mark onboarding complete (OWNER, ADMIN only)."""
    org, membership = org_context

    if payload.name is not None:
        org.name = payload.name.strip()
    if payload.industry is not None:
        org.industry = payload.industry.strip()
    if payload.company_size is not None:
        org.company_size = payload.company_size.strip()
    if payload.country is not None:
        org.country = payload.country.strip()
    if payload.currency is not None:
        org.currency = payload.currency.strip().upper()
    if payload.onboarding_completed is not None:
        org.onboarding_completed = payload.onboarding_completed
    if payload.max_retries is not None:
        org.max_retries = payload.max_retries
    if payload.high_value_threshold is not None:
        org.high_value_threshold = payload.high_value_threshold
    if payload.auto_retry_enabled is not None:
        org.auto_retry_enabled = payload.auto_retry_enabled

    await db.commit()
    await db.refresh(org)

    return OrganizationDetailsResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        industry=org.industry,
        company_size=org.company_size,
        country=org.country,
        currency=org.currency,
        onboarding_completed=org.onboarding_completed,
        max_retries=org.max_retries,
        high_value_threshold=org.high_value_threshold,
        auto_retry_enabled=org.auto_retry_enabled,
        role=membership.role,
        created_at=org.created_at,
        updated_at=org.updated_at,
    )


@router.get("/members", response_model=APIResponse[List[dict]])
async def list_organization_members(
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """List all registered members of the organization."""
    org, _ = org_context
    query = (
        select(OrganizationMembership)
        .options(selectinload(OrganizationMembership.user))
        .where(OrganizationMembership.organization_id == org.id)
    )
    result = await db.execute(query)
    memberships = result.scalars().all()

    data = [
        {
            "id": m.id,
            "user_id": m.user_id,
            "email": m.user.email if m.user else "",
            "full_name": m.user.full_name if m.user else "",
            "role": m.role,
            "joined_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in memberships
    ]
    return APIResponse(message="Members retrieved", data=data)


@router.post("/invitations", response_model=APIResponse[dict], status_code=status.HTTP_201_CREATED)
async def invite_member(
    payload: InviteMemberRequest,
    org_context: tuple = Depends(require_role(["OWNER", "ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    """Invite a new team member to the organization with a specific role (OWNER, ADMIN only)."""
    org, membership = org_context
    target_email = payload.email.strip().lower()
    role = payload.role.upper()
    if role not in ["ADMIN", "MEMBER", "VIEWER"]:
        raise RecoverAIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be ADMIN, MEMBER, or VIEWER.",
            error_code="INVALID_ROLE",
        )

    # Check if already a member
    existing_mem = await db.execute(
        select(OrganizationMembership)
        .join(User)
        .where(OrganizationMembership.organization_id == org.id, User.email == target_email)
    )
    if existing_mem.scalars().first():
        raise RecoverAIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This user is already a member of the organization.",
            error_code="USER_ALREADY_MEMBER",
        )

    raw_token = secrets.token_urlsafe(32)
    tok_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    invitation = OrganizationInvitation(
        organization_id=org.id,
        email=target_email,
        role=role,
        token_hash=tok_hash,
        token_prefix=raw_token[:6],
        status="PENDING",
        expires_at=expires_at,
        invited_by_user_id=membership.user_id,
    )
    db.add(invitation)
    await db.commit()

    return APIResponse(
        message=f"Invitation created for {target_email}",
        data={
            "id": invitation.id,
            "email": target_email,
            "role": role,
            "invite_link": f"{settings.APP_URL}/signup?invite={raw_token}",
            "expires_at": expires_at.isoformat(),
        },
    )


@router.get("/invitations", response_model=APIResponse[List[dict]])
async def list_pending_invitations(
    org_context: tuple = Depends(require_role(["OWNER", "ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    """List pending team invitations (OWNER, ADMIN only)."""
    org, _ = org_context
    query = (
        select(OrganizationInvitation)
        .where(OrganizationInvitation.organization_id == org.id, OrganizationInvitation.status == "PENDING")
        .order_by(desc(OrganizationInvitation.created_at))
    )
    result = await db.execute(query)
    invites = result.scalars().all()

    return APIResponse(
        message="Invitations retrieved",
        data=[
            {
                "id": inv.id,
                "email": inv.email,
                "role": inv.role,
                "status": inv.status,
                "expires_at": inv.expires_at.isoformat(),
                "created_at": inv.created_at.isoformat(),
            }
            for inv in invites
        ],
    )


@router.delete("/invitations/{invitation_id}", response_model=MessageResponse)
async def revoke_invitation(
    invitation_id: str,
    org_context: tuple = Depends(require_role(["OWNER", "ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a pending team invitation (OWNER, ADMIN only)."""
    org, _ = org_context
    query = select(OrganizationInvitation).where(
        OrganizationInvitation.id == invitation_id,
        OrganizationInvitation.organization_id == org.id,
    )
    res = await db.execute(query)
    inv = res.scalar_one_or_none()
    if not inv:
        raise EntityNotFoundException("OrganizationInvitation", invitation_id)

    inv.status = "REVOKED"
    await db.commit()
    return MessageResponse(success=True, message="Invitation revoked successfully.")


@router.patch("/members/{membership_id}/role", response_model=APIResponse[dict])
async def update_member_role(
    membership_id: str,
    payload: UpdateMemberRoleRequest,
    org_context: tuple = Depends(require_role(["OWNER", "ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    """Update a team member's role (OWNER, ADMIN only)."""
    org, actor_membership = org_context
    target_role = payload.role.upper()
    if target_role not in ["ADMIN", "MEMBER", "VIEWER"]:
        raise RecoverAIException(status_code=400, detail="Invalid role specified.", error_code="INVALID_ROLE")

    query = select(OrganizationMembership).where(
        OrganizationMembership.id == membership_id,
        OrganizationMembership.organization_id == org.id,
    )
    res = await db.execute(query)
    mem = res.scalar_one_or_none()
    if not mem:
        raise EntityNotFoundException("OrganizationMembership", membership_id)

    if mem.role == "OWNER" and actor_membership.role != "OWNER":
        raise RecoverAIException(status_code=403, detail="Only owners can modify owner roles.", error_code="FORBIDDEN")

    mem.role = target_role
    await db.commit()

    return APIResponse(message="Member role updated", data={"id": mem.id, "role": mem.role})
