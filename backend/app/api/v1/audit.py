from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, asc
from app.database import get_db
from app.models.audit_log import AuditLog, calculate_hash
from app.models.organization import Organization, OrganizationMembership
from app.schemas.audit_log import AuditLogResponse, AuditLedgerVerification
from app.schemas.common import APIResponse
from app.api.deps import get_current_org_context

router = APIRouter(prefix="/audit", tags=["Audit Ledger"])


@router.get("/logs", response_model=APIResponse[List[AuditLogResponse]])
async def list_audit_logs(
    entity_name: Optional[str] = None,
    entity_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """List audit records strictly scoped to the authenticated organization."""
    org, _ = org_context
    query = (
        select(AuditLog)
        .where(AuditLog.organization_id == org.id)
        .order_by(desc(AuditLog.created_at))
        .offset(offset)
        .limit(limit)
    )
    if entity_name:
        query = query.where(AuditLog.entity_name == entity_name)
    if entity_id:
        query = query.where(AuditLog.entity_id == entity_id)
        
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return APIResponse(
        message="Audit logs retrieved successfully",
        data=[AuditLogResponse.model_validate(log) for log in logs],
    )


@router.get("/verify", response_model=APIResponse[AuditLedgerVerification])
@router.get("/verify-chain", response_model=APIResponse[AuditLedgerVerification])
async def verify_audit_chain(
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Cryptographically verify that the SHA-256 hash chain of the audit ledger
    for the authenticated organization has not been tampered with or modified.
    """
    org, _ = org_context
    query = (
        select(AuditLog)
        .where(AuditLog.organization_id == org.id)
        .order_by(asc(AuditLog.created_at))
    )
    result = await db.execute(query)
    all_logs = result.scalars().all()
    
    invalid_ids = []
    
    for log in all_logs:
        expected_hash = calculate_hash(
            prev_hash=log.prev_hash or "GENESIS_RECOVERAI",
            event_type=log.event_type,
            entity_name=log.entity_name,
            entity_id=log.entity_id,
            actor=log.actor,
            state_after=log.state_after,
            timestamp_iso=log.timestamp_iso,
        )
        if expected_hash != log.sha256_hash:
            invalid_ids.append(log.id)

    is_valid = len(invalid_ids) == 0
    latest_hash = all_logs[-1].sha256_hash if all_logs else None

    return APIResponse(
        message="Audit chain verification complete",
        data=AuditLedgerVerification(
            is_valid=is_valid,
            total_entries_verified=len(all_logs),
            invalid_entry_ids=invalid_ids,
            latest_hash=latest_hash,
        ),
    )
