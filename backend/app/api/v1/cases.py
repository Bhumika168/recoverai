from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.recovery_case import RecoveryCase, CaseStatus
from app.models.recovery_action import RecoveryAction, ActionStatus
from app.models.transaction import Transaction, TransactionStatus
from app.models.audit_log import AuditLog, calculate_hash
from app.models.organization import Organization, OrganizationMembership
from app.schemas.recovery_case import RecoveryCaseResponse, RecoveryCaseDetailResponse
from app.schemas.common import APIResponse
from app.exceptions import EntityNotFoundException, PolicyViolationException
from app.agents.orchestrator import recover_transaction
from app.api.deps import get_current_org_context, require_write_access

router = APIRouter(prefix="/cases", tags=["Recovery Cases"])


@router.post("/{case_id}/trigger-recovery", response_model=APIResponse[RecoveryCaseResponse])
async def trigger_case_recovery(
    case_id: str,
    org_context: tuple = Depends(require_write_access),
    db: AsyncSession = Depends(get_db),
):
    """Trigger the autonomous recovery pipeline on an existing recovery case scoped to org."""
    org, membership = org_context
    result = await db.execute(
        select(RecoveryCase).where(
            RecoveryCase.organization_id == org.id,
            RecoveryCase.id == case_id,
        )
    )
    case = result.scalar_one_or_none()
    if not case:
        raise EntityNotFoundException("RecoveryCase", case_id)
        
    updated_case = await recover_transaction(
        case.transaction_id,
        db,
        actor=f"USER:{membership.user_id}",
    )
    return APIResponse(
        message="Autonomous recovery pipeline executed",
        data=RecoveryCaseResponse.model_validate(updated_case),
    )


@router.post("/batch-evaluate", response_model=APIResponse[dict])
async def batch_evaluate_cases(
    payload: Optional[dict] = None,
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Batch evaluate eligible recovery cases for the authenticated organization.
    Runs diagnosis, policy checks, recovery action creation, and idempotency protection.
    """
    org, membership = org_context
    case_ids = (payload or {}).get("case_ids")

    query = select(RecoveryCase).where(
        RecoveryCase.organization_id == org.id,
        RecoveryCase.status.in_([CaseStatus.OPEN, CaseStatus.IN_PROGRESS, CaseStatus.PENDING_APPROVAL]),
    )
    if case_ids:
        query = query.where(RecoveryCase.id.in_(case_ids))

    result = await db.execute(query)
    cases = result.scalars().all()

    processed_count = 0
    approved_count = 0
    held_count = 0
    blocked_count = 0

    for case in cases:
        try:
            updated = await recover_transaction(
                case.transaction_id,
                db,
                actor=f"USER:{membership.user_id}",
            )
            processed_count += 1
            if updated.requires_human_approval == "YES":
                held_count += 1
            elif updated.status == CaseStatus.STOPPED:
                blocked_count += 1
            else:
                approved_count += 1
        except Exception:
            pass

    return APIResponse(
        message=f"Batch evaluation complete. Processed {processed_count} cases.",
        data={
            "total_evaluated": len(cases),
            "processed_count": processed_count,
            "approved_count": approved_count,
            "held_for_approval": held_count,
            "blocked_or_stopped": blocked_count,
        },
    )


@router.post("/{case_id}/approve", response_model=APIResponse[RecoveryCaseResponse])
async def approve_held_case(
    case_id: str,
    org_context: tuple = Depends(require_write_access),
    db: AsyncSession = Depends(get_db),
):
    """Merchant one-click approval for high-value or escalated cases held by policy."""
    org, membership = org_context
    query = (
        select(RecoveryCase)
        .where(
            RecoveryCase.organization_id == org.id,
            RecoveryCase.id == case_id,
        )
        .options(selectinload(RecoveryCase.transaction), selectinload(RecoveryCase.actions))
    )
    result = await db.execute(query)
    case = result.scalar_one_or_none()
    if not case:
        raise EntityNotFoundException("RecoveryCase", case_id)

    if case.status not in [CaseStatus.PENDING_APPROVAL, CaseStatus.ESCALATED]:
        raise PolicyViolationException("APPROVAL_INVALID", f"Case is not in an approval-required status (current: {case.status.value})")

    # Clear human approval hold
    case.requires_human_approval = "NO"
    case.status = CaseStatus.IN_PROGRESS
    case.strategy_summary = f"[HUMAN_APPROVED] Cleared by merchant: {case.strategy_summary or ''}"
    
    # Update pending actions to EXECUTING / COMPLETED
    if case.actions:
        for act in case.actions:
            if act.status == ActionStatus.PENDING_APPROVAL:
                act.status = ActionStatus.EXECUTING
                act.executed_at = datetime.now(timezone.utc)

    # Append Audit Log
    latest_audit = (
        await db.execute(
            select(AuditLog)
            .where(AuditLog.organization_id == org.id)
            .order_by(desc(AuditLog.created_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    prev_hash = latest_audit.sha256_hash if latest_audit else "GENESIS_RECOVERAI"
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()

    audit_state_after = {
        "case_id": case.id,
        "status": case.status.value,
        "requires_human_approval": "NO",
        "action": "HUMAN_APPROVED",
    }
    sha_hash = calculate_hash(
        prev_hash=prev_hash,
        event_type="HUMAN_APPROVED",
        entity_name="RecoveryCase",
        entity_id=case.id,
        actor=f"USER:{membership.user_id}",
        state_after=audit_state_after,
        timestamp_iso=now_iso,
    )
    audit_entry = AuditLog(
        organization_id=org.id,
        entity_name="RecoveryCase",
        entity_id=case.id,
        event_type="HUMAN_APPROVED",
        actor=f"USER:{membership.user_id}",
        state_before={"status": "PENDING_APPROVAL"},
        state_after=audit_state_after,
        prev_hash=prev_hash,
        sha256_hash=sha_hash,
        timestamp_iso=now_iso,
        notes=f"Merchant authorized high-value recovery execution for case {case.id}",
        created_at=now_dt,
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(case)

    return APIResponse(
        message="Recovery case approved and scheduled for execution",
        data=RecoveryCaseResponse.model_validate(case),
    )


@router.post("/{case_id}/reject", response_model=APIResponse[RecoveryCaseResponse])
async def reject_held_case(
    case_id: str,
    org_context: tuple = Depends(require_write_access),
    db: AsyncSession = Depends(get_db),
):
    """Merchant rejection of held recovery action."""
    org, membership = org_context
    query = (
        select(RecoveryCase)
        .where(
            RecoveryCase.organization_id == org.id,
            RecoveryCase.id == case_id,
        )
        .options(selectinload(RecoveryCase.transaction), selectinload(RecoveryCase.actions))
    )
    result = await db.execute(query)
    case = result.scalar_one_or_none()
    if not case:
        raise EntityNotFoundException("RecoveryCase", case_id)

    case.requires_human_approval = "NO"
    case.status = CaseStatus.UNRECOVERABLE
    case.strategy_summary = f"[HUMAN_REJECTED] Dismissed by merchant: {case.strategy_summary or ''}"
    
    if case.actions:
        for act in case.actions:
            if act.status == ActionStatus.PENDING_APPROVAL:
                act.status = ActionStatus.CANCELLED

    # Append Audit Log
    latest_audit = (
        await db.execute(
            select(AuditLog)
            .where(AuditLog.organization_id == org.id)
            .order_by(desc(AuditLog.created_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    prev_hash = latest_audit.sha256_hash if latest_audit else "GENESIS_RECOVERAI"
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()

    audit_state_after = {
        "case_id": case.id,
        "status": CaseStatus.UNRECOVERABLE.value,
        "action": "HUMAN_REJECTED",
    }
    sha_hash = calculate_hash(
        prev_hash=prev_hash,
        event_type="HUMAN_REJECTED",
        entity_name="RecoveryCase",
        entity_id=case.id,
        actor=f"USER:{membership.user_id}",
        state_after=audit_state_after,
        timestamp_iso=now_iso,
    )
    audit_entry = AuditLog(
        organization_id=org.id,
        entity_name="RecoveryCase",
        entity_id=case.id,
        event_type="HUMAN_REJECTED",
        actor=f"USER:{membership.user_id}",
        state_before={"status": case.status.value},
        state_after=audit_state_after,
        prev_hash=prev_hash,
        sha256_hash=sha_hash,
        timestamp_iso=now_iso,
        notes=f"Merchant rejected recovery execution for case {case.id}",
        created_at=now_dt,
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(case)

    return APIResponse(
        message="Recovery case rejected and blocked from execution",
        data=RecoveryCaseResponse.model_validate(case),
    )


@router.post("/{case_id}/simulate-recovery", response_model=APIResponse[RecoveryCaseResponse])
@router.post("/{case_id}/verify-recovery", response_model=APIResponse[RecoveryCaseResponse])
async def simulate_successful_recovery(
    case_id: str,
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Simulate customer completion of recovery action (e.g., payment link paid / card retried).
    Explicit verification endpoint for testing the complete end-to-end recovery pipeline.
    """
    org, membership = org_context
    query = (
        select(RecoveryCase)
        .where(
            RecoveryCase.organization_id == org.id,
            RecoveryCase.id == case_id,
        )
        .options(selectinload(RecoveryCase.transaction), selectinload(RecoveryCase.actions))
    )
    result = await db.execute(query)
    case = result.scalar_one_or_none()
    if not case:
        raise EntityNotFoundException("RecoveryCase", case_id)

    # 1. Update Case to RECOVERED
    now_dt = datetime.now(timezone.utc)
    case.status = CaseStatus.RECOVERED
    case.recovered_amount = case.amount_at_risk
    case.recovered_at = now_dt
    case.strategy_summary = f"[RECOVERED] Verified simulated customer payment: {case.strategy_summary or ''}"

    # 2. Update Transaction to RECOVERED
    if case.transaction:
        case.transaction.status = TransactionStatus.RECOVERED

    # 3. Update Actions to COMPLETED
    if case.actions:
        for act in case.actions:
            act.status = ActionStatus.COMPLETED
            act.result = {"verified": True, "notes": "Simulated customer payment verified"}

    # 4. Append Audit Event
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

    audit_state_after = {
        "case_id": case.id,
        "transaction_id": case.transaction_id,
        "status": CaseStatus.RECOVERED.value,
        "recovered_amount": case.recovered_amount,
    }
    sha_hash = calculate_hash(
        prev_hash=prev_hash,
        event_type="RECOVERY_VERIFIED",
        entity_name="RecoveryCase",
        entity_id=case.id,
        actor=f"USER:{membership.user_id}",
        state_after=audit_state_after,
        timestamp_iso=now_iso,
    )
    audit_entry = AuditLog(
        organization_id=org.id,
        entity_name="RecoveryCase",
        entity_id=case.id,
        event_type="RECOVERY_VERIFIED",
        actor=f"USER:{membership.user_id}",
        state_before={"status": "IN_PROGRESS"},
        state_after=audit_state_after,
        prev_hash=prev_hash,
        sha256_hash=sha_hash,
        timestamp_iso=now_iso,
        notes=f"Revenue recovery verified: ₹{case.recovered_amount:,.2f} restored",
        created_at=now_dt,
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(case)

    return APIResponse(
        message=f"Recovery verified! ₹{case.recovered_amount:,.2f} successfully recovered.",
        data=RecoveryCaseResponse.model_validate(case),
    )


@router.get("", response_model=APIResponse[List[RecoveryCaseResponse]])
async def list_cases(
    status_filter: Optional[CaseStatus] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """List recovery cases strictly scoped to the authenticated organization."""
    org, _ = org_context
    query = (
        select(RecoveryCase)
        .where(RecoveryCase.organization_id == org.id)
        .order_by(desc(RecoveryCase.created_at))
        .offset(offset)
        .limit(limit)
    )
    if status_filter:
        query = query.where(RecoveryCase.status == status_filter)
        
    result = await db.execute(query)
    cases = result.scalars().all()
    
    return APIResponse(
        message="Recovery cases retrieved successfully",
        data=[RecoveryCaseResponse.model_validate(c) for c in cases],
    )


@router.get("/{case_id}", response_model=APIResponse[RecoveryCaseDetailResponse])
async def get_case_detail(
    case_id: str,
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full case details scoped to the authenticated organization."""
    org, _ = org_context
    query = (
        select(RecoveryCase)
        .where(
            RecoveryCase.organization_id == org.id,
            RecoveryCase.id == case_id,
        )
        .options(
            selectinload(RecoveryCase.transaction),
            selectinload(RecoveryCase.customer),
            selectinload(RecoveryCase.ai_decisions),
            selectinload(RecoveryCase.actions),
        )
    )
    result = await db.execute(query)
    case = result.scalar_one_or_none()
    if not case:
        raise EntityNotFoundException("RecoveryCase", case_id)
        
    return APIResponse(
        message="Recovery case details retrieved",
        data=RecoveryCaseDetailResponse.model_validate(case),
    )


@router.post("/{case_id}/dispatch-communication", response_model=APIResponse[dict])
async def dispatch_case_communication(
    case_id: str,
    payload: Optional[dict] = None,
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """Trigger automated customer recovery communication step for this case."""
    from app.agents.campaign_engine import execute_campaign_step
    org, _ = org_context
    case_res = await db.execute(
        select(RecoveryCase).where(RecoveryCase.id == case_id, RecoveryCase.organization_id == org.id)
    )
    if not case_res.scalar_one_or_none():
        raise EntityNotFoundException("RecoveryCase", case_id)

    channel = (payload or {}).get("channel")
    template_id = (payload or {}).get("template_id")

    result = await execute_campaign_step(
        case_id=case_id,
        db=db,
        channel=channel,
        custom_template_id=template_id,
    )
    return APIResponse(message="Communication processed", data=result)


@router.get("/{case_id}/timeline", response_model=APIResponse[List[dict]])
async def get_case_timeline(
    case_id: str,
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full chronological audit timeline events for this recovery case."""
    org, _ = org_context
    case_res = await db.execute(
        select(RecoveryCase).where(RecoveryCase.id == case_id, RecoveryCase.organization_id == org.id)
    )
    case = case_res.scalar_one_or_none()
    if not case:
        raise EntityNotFoundException("RecoveryCase", case_id)

    # Fetch audit events for this case, associated transaction, and any linked recovery tokens
    from app.models.recovery_token import RecoveryToken
    tokens_res = await db.execute(select(RecoveryToken.id).where(RecoveryToken.recovery_case_id == case.id))
    token_ids = [r[0] for r in tokens_res.fetchall()]

    entity_ids = [case.id, case.transaction_id] + token_ids
    query = (
        select(AuditLog)
        .where(
            AuditLog.organization_id == org.id,
            AuditLog.entity_id.in_(entity_ids),
        )
        .order_by(AuditLog.created_at)
    )
    audit_res = await db.execute(query)
    logs = audit_res.scalars().all()

    timeline_items = []
    for log in logs:
        timeline_items.append({
            "id": log.id,
            "event_type": log.event_type,
            "actor": log.actor,
            "notes": log.notes,
            "timestamp": log.created_at.isoformat() if log.created_at else None,
            "state_after": log.state_after,
            "sha256_hash": log.sha256_hash,
        })

    return APIResponse(message="Case timeline retrieved", data=timeline_items)


@router.post("/{case_id}/opt-out", response_model=APIResponse[dict])
async def customer_opt_out(
    case_id: str,
    payload: Optional[dict] = None,
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """Customer opt-out / unsubscribe. Halts automated communications."""
    from app.models.communication import CustomerOptOut
    org, _ = org_context
    case_res = await db.execute(
        select(RecoveryCase)
        .where(RecoveryCase.id == case_id, RecoveryCase.organization_id == org.id)
        .options(selectinload(RecoveryCase.customer))
    )
    case = case_res.scalar_one_or_none()
    if not case:
        raise EntityNotFoundException("RecoveryCase", case_id)

    email = case.customer.email if case.customer else None
    phone = case.customer.phone if case.customer else None
    reason = (payload or {}).get("reason", "CUSTOMER_UNSUBSCRIBE")

    opt = CustomerOptOut(
        organization_id=org.id,
        customer_email=email,
        customer_phone=phone,
        reason=reason,
    )
    db.add(opt)
    case.status = CaseStatus.CANCELLED
    case.strategy_summary = f"[STOPPED_OPT_OUT] Customer unsubscribed from communications."
    await db.commit()

    return APIResponse(message="Customer opted out. Case communications stopped.", data={"status": "CANCELLED"})


@router.get("/{case_id}/communications", response_model=APIResponse[List[dict]])
async def get_case_communications(
    case_id: str,
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve communication logs for this recovery case."""
    from app.models.communication import CommunicationLog
    org, _ = org_context
    logs_res = await db.execute(
        select(CommunicationLog)
        .where(CommunicationLog.recovery_case_id == case_id, CommunicationLog.organization_id == org.id)
        .order_by(desc(CommunicationLog.created_at))
    )
    logs = logs_res.scalars().all()

    return APIResponse(
        message="Communications retrieved",
        data=[
            {
                "id": l.id,
                "channel": l.channel,
                "recipient": l.recipient_reference,
                "subject": l.subject,
                "body": l.rendered_body,
                "status": l.status,
                "sent_at": l.sent_at.isoformat() if l.sent_at else None,
                "provider_message_id": l.provider_message_id,
            }
            for l in logs
        ],
    )

