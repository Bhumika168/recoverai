from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.models.campaign import Campaign, CampaignStatus, CampaignChannel
from app.models.recovery_case import RecoveryCase, CaseStatus
from app.models.audit_log import AuditLog, calculate_hash
from app.schemas.common import APIResponse
from app.exceptions import EntityNotFoundException, RecoverAIException
from app.api.deps import get_current_org_context, require_role, require_write_access

router = APIRouter(prefix="/campaigns", tags=["Recovery Campaigns"])


@router.get("", response_model=APIResponse[List[Dict[str, Any]]])
async def list_campaigns(
    status_filter: Optional[str] = Query(None, alias="status"),
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """List all recovery campaigns for the authenticated organization."""
    org, _ = org_context

    query = select(Campaign).where(Campaign.organization_id == org.id)
    if status_filter:
        query = query.where(Campaign.status == status_filter.upper())
    query = query.order_by(desc(Campaign.created_at))

    result = await db.execute(query)
    campaigns = result.scalars().all()

    response_data = []
    for c in campaigns:
        # Calculate dynamic recovery rate from persisted numbers
        rate = (
            (c.total_recovered_count / c.enrolled_cases_count * 100.0)
            if c.enrolled_cases_count > 0
            else 0.0
        )
        response_data.append({
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "recovery_type": c.recovery_type,
            "status": c.status,
            "target_segment": c.target_segment,
            "channels": c.channels_list or ["EMAIL", "SMS", "WHATSAPP"],
            "min_amount": c.min_amount,
            "max_amount": c.max_amount,
            "max_recovery_attempts": c.max_recovery_attempts,
            "retry_delay_hours": c.retry_delay_hours,
            "enrolled_cases_count": c.enrolled_cases_count,
            "messages_sent_count": c.messages_sent_count,
            "actions_executed_count": c.actions_executed_count,
            "recovered_amount": c.recovered_amount or c.total_revenue_recovered,
            "recovery_rate": round(rate, 1),
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "last_activity_at": c.last_activity_at.isoformat() if c.last_activity_at else None,
        })

    return APIResponse(
        message="Campaigns retrieved successfully",
        data=response_data,
    )


@router.post("", response_model=APIResponse[Dict[str, Any]], status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: Dict[str, Any],
    org_context: tuple = Depends(require_write_access),
    db: AsyncSession = Depends(get_db),
):
    """Create a new recovery campaign scoped to the authenticated organization."""
    org, _ = org_context

    name = payload.get("name", "").strip()
    if not name:
        raise RecoverAIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campaign name is required.",
            error_code="INVALID_CAMPAIGN_NAME",
        )

    recovery_type = payload.get("recovery_type", "FAILED_PAYMENT").upper()
    channels = payload.get("channels", ["EMAIL", "SMS", "WHATSAPP"])
    min_amt = float(payload.get("min_amount", 0.0))
    max_amt = float(payload.get("max_amount", 1000000.0))
    max_attempts = int(payload.get("max_recovery_attempts", 3))
    delay_hours = int(payload.get("retry_delay_hours", 24))

    campaign = Campaign(
        organization_id=org.id,
        name=name,
        description=payload.get("description"),
        recovery_type=recovery_type,
        status="ACTIVE" if payload.get("is_active", True) else "DRAFT",
        is_active=payload.get("is_active", True),
        target_segment=payload.get("target_segment", "ALL_FAILURES"),
        channels_list=channels,
        min_amount=min_amt,
        max_amount=max_amt,
        max_recovery_attempts=max_attempts,
        retry_delay_hours=delay_hours,
        escalation_rules=payload.get("escalation_rules", {"require_approval_above": 50000.0}),
    )
    db.add(campaign)
    await db.flush()

    # Append Audit Log
    now_dt = datetime.now(timezone.utc)
    latest_audit = (
        await db.execute(
            select(AuditLog)
            .where(AuditLog.organization_id == org.id)
            .order_by(desc(AuditLog.created_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    prev_hash = latest_audit.sha256_hash if latest_audit else "GENESIS_RECOVERAI"
    now_iso = now_dt.isoformat()

    audit_state = {"campaign_id": campaign.id, "name": campaign.name, "type": recovery_type}
    sha_hash = calculate_hash(
        prev_hash=prev_hash,
        event_type="CAMPAIGN_CREATED",
        entity_name="Campaign",
        entity_id=campaign.id,
        actor="MERCHANT_ADMIN",
        state_after=audit_state,
        timestamp_iso=now_iso,
    )
    audit_entry = AuditLog(
        organization_id=org.id,
        entity_name="Campaign",
        entity_id=campaign.id,
        event_type="CAMPAIGN_CREATED",
        actor="MERCHANT_ADMIN",
        state_before={},
        state_after=audit_state,
        prev_hash=prev_hash,
        sha256_hash=sha_hash,
        timestamp_iso=now_iso,
        notes=f"Created recovery campaign '{campaign.name}'",
        created_at=now_dt,
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(campaign)

    return APIResponse(
        message="Recovery campaign created successfully.",
        data={"id": campaign.id, "name": campaign.name, "status": campaign.status},
    )


@router.get("/{campaign_id}", response_model=APIResponse[Dict[str, Any]])
async def get_campaign_detail(
    campaign_id: str,
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve detailed campaign analytics and settings."""
    org, _ = org_context
    camp_res = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.organization_id == org.id)
    )
    c = camp_res.scalar_one_or_none()
    if not c:
        raise EntityNotFoundException(entity_name="Campaign", entity_id=campaign_id)

    rate = (
        (c.total_recovered_count / c.enrolled_cases_count * 100.0)
        if c.enrolled_cases_count > 0
        else 0.0
    )

    return APIResponse(
        message="Campaign details retrieved",
        data={
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "recovery_type": c.recovery_type,
            "status": c.status,
            "channels": c.channels_list or ["EMAIL", "SMS", "WHATSAPP"],
            "min_amount": c.min_amount,
            "max_amount": c.max_amount,
            "max_recovery_attempts": c.max_recovery_attempts,
            "retry_delay_hours": c.retry_delay_hours,
            "enrolled_cases_count": c.enrolled_cases_count,
            "messages_sent_count": c.messages_sent_count,
            "actions_executed_count": c.actions_executed_count,
            "recovered_amount": c.recovered_amount,
            "recovery_rate": round(rate, 1),
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "last_activity_at": c.last_activity_at.isoformat() if c.last_activity_at else None,
        },
    )


@router.post("/{campaign_id}/pause", response_model=APIResponse[Dict[str, Any]])
async def pause_campaign(
    campaign_id: str,
    org_context: tuple = Depends(require_write_access),
    db: AsyncSession = Depends(get_db),
):
    """Pause an active campaign."""
    org, _ = org_context
    camp_res = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.organization_id == org.id)
    )
    c = camp_res.scalar_one_or_none()
    if not c:
        raise EntityNotFoundException(entity_name="Campaign", entity_id=campaign_id)

    c.status = "PAUSED"
    c.is_active = False
    await db.commit()

    return APIResponse(message=f"Campaign '{c.name}' paused.", data={"status": "PAUSED"})


@router.post("/{campaign_id}/resume", response_model=APIResponse[Dict[str, Any]])
async def resume_campaign(
    campaign_id: str,
    org_context: tuple = Depends(require_write_access),
    db: AsyncSession = Depends(get_db),
):
    """Resume a paused campaign."""
    org, _ = org_context
    camp_res = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.organization_id == org.id)
    )
    c = camp_res.scalar_one_or_none()
    if not c:
        raise EntityNotFoundException(entity_name="Campaign", entity_id=campaign_id)

    c.status = "ACTIVE"
    c.is_active = True
    await db.commit()

    return APIResponse(message=f"Campaign '{c.name}' resumed.", data={"status": "ACTIVE"})


@router.post("/{campaign_id}/archive", response_model=APIResponse[Dict[str, Any]])
async def archive_campaign(
    campaign_id: str,
    org_context: tuple = Depends(require_write_access),
    db: AsyncSession = Depends(get_db),
):
    """Archive a campaign."""
    org, _ = org_context
    camp_res = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.organization_id == org.id)
    )
    c = camp_res.scalar_one_or_none()
    if not c:
        raise EntityNotFoundException(entity_name="Campaign", entity_id=campaign_id)

    c.status = "ARCHIVED"
    c.is_active = False
    await db.commit()

    return APIResponse(message=f"Campaign '{c.name}' archived.", data={"status": "ARCHIVED"})
