import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc
from app.config import settings
from app.models.campaign import Campaign, CampaignStatus
from app.models.recovery_case import RecoveryCase, CaseStatus
from app.models.transaction import Transaction, TransactionStatus
from app.models.customer import Customer
from app.models.organization import Organization
from app.models.template import MessageTemplate
from app.models.communication import CommunicationLog, CustomerOptOut
from app.models.notification import MerchantNotification
from app.models.audit_log import AuditLog, calculate_hash
from app.notifications.provider import get_notification_provider, sanitize_and_render_template, DEFAULT_TEMPLATES
from app.logging_config import logger


# Valid Case State Transition Graph
VALID_TRANSITIONS: Dict[CaseStatus, List[CaseStatus]] = {
    CaseStatus.DETECTED: [CaseStatus.DIAGNOSED, CaseStatus.CANCELLED, CaseStatus.BLOCKED],
    CaseStatus.DIAGNOSED: [CaseStatus.POLICY_REVIEW, CaseStatus.BLOCKED, CaseStatus.CANCELLED],
    CaseStatus.POLICY_REVIEW: [CaseStatus.APPROVED, CaseStatus.PENDING_APPROVAL, CaseStatus.BLOCKED, CaseStatus.UNRECOVERABLE, CaseStatus.ESCALATED],
    CaseStatus.PENDING_APPROVAL: [CaseStatus.APPROVED, CaseStatus.STOPPED, CaseStatus.CANCELLED, CaseStatus.IN_PROGRESS],
    CaseStatus.APPROVED: [CaseStatus.ACTION_SCHEDULED, CaseStatus.IN_PROGRESS, CaseStatus.CANCELLED],
    CaseStatus.ACTION_SCHEDULED: [CaseStatus.CUSTOMER_CONTACTED, CaseStatus.RETRY_PENDING, CaseStatus.PAYMENT_ATTEMPTED, CaseStatus.CANCELLED],
    CaseStatus.CUSTOMER_CONTACTED: [CaseStatus.RETRY_PENDING, CaseStatus.PAYMENT_ATTEMPTED, CaseStatus.VERIFICATION, CaseStatus.RECOVERED, CaseStatus.EXHAUSTED],
    CaseStatus.RETRY_PENDING: [CaseStatus.PAYMENT_ATTEMPTED, CaseStatus.CANCELLED, CaseStatus.STOPPED],
    CaseStatus.PAYMENT_ATTEMPTED: [CaseStatus.VERIFICATION, CaseStatus.FAILED, CaseStatus.RETRY_PENDING, CaseStatus.RECOVERED, CaseStatus.EXHAUSTED],
    CaseStatus.VERIFICATION: [CaseStatus.RECOVERED, CaseStatus.FAILED, CaseStatus.EXHAUSTED],
    
    # Backward compatibility with existing general states
    CaseStatus.OPEN: [CaseStatus.IN_PROGRESS, CaseStatus.PENDING_APPROVAL, CaseStatus.RECOVERED, CaseStatus.UNRECOVERABLE, CaseStatus.STOPPED, CaseStatus.ESCALATED, CaseStatus.ACTION_SCHEDULED, CaseStatus.CUSTOMER_CONTACTED],
    CaseStatus.IN_PROGRESS: [CaseStatus.RECOVERED, CaseStatus.EXHAUSTED, CaseStatus.ESCALATED, CaseStatus.UNRECOVERABLE, CaseStatus.STOPPED, CaseStatus.FAILED, CaseStatus.CUSTOMER_CONTACTED, CaseStatus.RETRY_PENDING, CaseStatus.VERIFICATION],
    CaseStatus.UNRECOVERABLE: [],
    CaseStatus.RECOVERED: [],
    CaseStatus.EXHAUSTED: [],
    CaseStatus.BLOCKED: [],
    CaseStatus.STOPPED: [],
    CaseStatus.CANCELLED: [],
    CaseStatus.FAILED: [CaseStatus.IN_PROGRESS, CaseStatus.RETRY_PENDING, CaseStatus.EXHAUSTED, CaseStatus.STOPPED],
    CaseStatus.ESCALATED: [CaseStatus.APPROVED, CaseStatus.STOPPED, CaseStatus.RECOVERED],
}


def validate_case_transition(current_status: CaseStatus, target_status: CaseStatus) -> bool:
    """Verifies that a state transition follows the defined recovery workflow graph."""
    if current_status == target_status:
        return True
    allowed = VALID_TRANSITIONS.get(current_status, [])
    return target_status in allowed


async def enroll_case_in_campaign(
    case: RecoveryCase,
    transaction: Transaction,
    db: AsyncSession,
) -> Optional[Campaign]:
    """
    Finds matching active campaign for the organization workspace and enrolls the case.
    """
    if not case.organization_id:
        return None

    query = (
        select(Campaign)
        .where(
            Campaign.organization_id == case.organization_id,
            Campaign.status == "ACTIVE",
            Campaign.min_amount <= transaction.amount,
            Campaign.max_amount >= transaction.amount,
        )
        .order_by(desc(Campaign.created_at))
        .limit(1)
    )
    result = await db.execute(query)
    campaign = result.scalar_one_or_none()

    if campaign:
        case.campaign_id = campaign.id
        campaign.enrolled_cases_count += 1
        campaign.total_targeted_count += 1
        campaign.last_activity_at = datetime.now(timezone.utc)
        await db.flush()

    return campaign


async def execute_campaign_step(
    case_id: str,
    db: AsyncSession,
    channel: Optional[str] = None,
    custom_template_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes automated campaign communication step:
    1. Checks Stop Conditions (recovered, opted-out, exhausted, paused).
    2. Renders sanitized message template.
    3. Dispatches message via NotificationProvider abstraction.
    4. Records CommunicationLog & updates case state.
    5. Appends SHA-256 Audit Log.
    """
    query = (
        select(RecoveryCase)
        .where(RecoveryCase.id == case_id)
    )
    res = await db.execute(query)
    case = res.scalar_one_or_none()
    if not case:
        return {"status": "error", "message": "Recovery case not found"}

    txn_res = await db.execute(select(Transaction).where(Transaction.id == case.transaction_id))
    txn = txn_res.scalar_one_or_none()
    cust_res = await db.execute(select(Customer).where(Customer.id == case.customer_id))
    cust = cust_res.scalar_one_or_none()
    org_res = await db.execute(select(Organization).where(Organization.id == case.organization_id))
    org = org_res.scalar_one_or_none()

    org_name = org.name if org else "Merchant"
    cust_name = cust.name if cust else "Customer"
    cust_email = cust.email if cust else (txn.customer_email if txn else "customer@example.com")
    cust_phone = cust.phone if cust else None

    # =========================================================================
    # STOP CONDITIONS
    # =========================================================================
    # 1. Stop if already recovered
    if case.status == CaseStatus.RECOVERED or (txn and txn.status == TransactionStatus.RECOVERED):
        return {"status": "stopped", "reason": "PAYMENT_ALREADY_RECOVERED"}

    # 2. Stop if customer opted out
    optout_res = await db.execute(
        select(CustomerOptOut).where(
            CustomerOptOut.organization_id == case.organization_id,
            or_(
                CustomerOptOut.customer_email == cust_email,
                CustomerOptOut.customer_phone == cust_phone,
            ),
        )
    )
    if optout_res.scalar_one_or_none():
        case.status = CaseStatus.CANCELLED
        await db.flush()
        return {"status": "stopped", "reason": "CUSTOMER_OPTED_OUT"}

    # 3. Stop if frequency / attempt cap reached (max 3 messages per case)
    if case.messages_sent_count >= 3:
        case.status = CaseStatus.EXHAUSTED
        await db.flush()
        return {"status": "stopped", "reason": "MAX_ATTEMPTS_EXHAUSTED"}

    # 4. Check active campaign
    campaign = None
    if case.campaign_id:
        camp_res = await db.execute(select(Campaign).where(Campaign.id == case.campaign_id))
        campaign = camp_res.scalar_one_or_none()
        if campaign and campaign.status == "PAUSED":
            return {"status": "held", "reason": "CAMPAIGN_PAUSED"}

    # =========================================================================
    # SELECT TEMPLATE & CHANNEL
    # =========================================================================
    dispatch_channel = (channel or (campaign.channel.value if campaign else "EMAIL")).upper()
    if dispatch_channel == "MULTI_CHANNEL":
        dispatch_channel = "EMAIL"

    template = None
    if custom_template_id:
        tmpl_res = await db.execute(
            select(MessageTemplate).where(
                MessageTemplate.id == custom_template_id,
                MessageTemplate.organization_id == case.organization_id,
            )
        )
        template = tmpl_res.scalar_one_or_none()

    if not template:
        # Fallback to org default or first matching template
        tmpl_res = await db.execute(
            select(MessageTemplate).where(
                MessageTemplate.organization_id == case.organization_id,
                MessageTemplate.channel == dispatch_channel,
                MessageTemplate.status == "ACTIVE",
            ).limit(1)
        )
        template = tmpl_res.scalar_one_or_none()

    from app.api.v1.customer_recovery import create_recovery_token_for_case
    tok_rec, raw_tok = await create_recovery_token_for_case(case_id=case.id, db=db, action_type="PAYMENT_LINK")
    payment_link = f"{settings.APP_URL}/recover/{raw_tok}"

    variables = {
        "customer_name": cust_name,
        "amount": f"{txn.amount:,.2f}" if txn else "0.00",
        "currency": txn.currency if txn else "INR",
        "payment_method": txn.payment_method.value if txn else "Card",
        "payment_link": payment_link,
        "company_name": org_name,
        "merchant_name": org_name,
        "due_date": "Immediately",
    }

    if template:
        subject = sanitize_and_render_template(template.subject or f"Payment Update from {org_name}", variables)
        body = sanitize_and_render_template(template.body, variables)
    else:
        # Default fallback template
        subject = f"Action Required: Complete your payment to {org_name}"
        body = f"Hi {cust_name},\n\nYour payment of {variables['currency']} {variables['amount']} to {org_name} was unsuccessful.\n\nPlease retry using the secure payment link:\n{payment_link}\n\nThank you,\n{org_name}"

    # =========================================================================
    # DISPATCH MESSAGE
    # =========================================================================
    provider = get_notification_provider(dispatch_channel)
    recipient = cust_email if dispatch_channel in ["EMAIL", "IN_APP"] else (cust_phone or cust_email)
    
    success, msg_id, err_code = provider.send(
        channel=dispatch_channel,
        recipient=recipient,
        subject=subject,
        body=body,
    )

    now_dt = datetime.now(timezone.utc)

    log_entry = CommunicationLog(
        organization_id=case.organization_id,
        recovery_case_id=case.id,
        template_id=template.id if template else None,
        channel=dispatch_channel,
        recipient_reference=recipient,
        provider_message_id=msg_id,
        subject=subject,
        rendered_body=body,
        status="DELIVERED" if success else "FAILED",
        sent_at=now_dt if success else None,
        delivered_at=now_dt if success else None,
        failed_at=now_dt if not success else None,
        error_code=err_code,
    )
    db.add(log_entry)

    # Update case & campaign counters
    case.messages_sent_count += 1
    case.status = CaseStatus.CUSTOMER_CONTACTED
    if campaign:
        campaign.messages_sent_count += 1
        campaign.actions_executed_count += 1
        campaign.last_activity_at = now_dt

    # Record Merchant Notification
    notif = MerchantNotification(
        organization_id=case.organization_id,
        title=f"Customer Outreach Dispatched ({dispatch_channel})",
        message=f"Sent recovery reminder for case {case.id} (₹{txn.amount:,.2f}) to {recipient}",
        severity="INFO",
        related_case_id=case.id,
    )
    db.add(notif)
    await db.flush()

    # Append SHA-256 Audit Log
    latest_audit = (
        await db.execute(
            select(AuditLog)
            .where(AuditLog.organization_id == case.organization_id)
            .order_by(desc(AuditLog.created_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    prev_hash = latest_audit.sha256_hash if latest_audit else "GENESIS_RECOVERAI"
    now_iso = now_dt.isoformat()

    audit_state = {
        "case_id": case.id,
        "channel": dispatch_channel,
        "recipient": recipient,
        "message_id": msg_id,
        "status": "DELIVERED" if success else "FAILED",
    }
    sha_hash = calculate_hash(
        prev_hash=prev_hash,
        event_type="MESSAGE_SENT",
        entity_name="CommunicationLog",
        entity_id=log_entry.id,
        actor="CAMPAIGN_ENGINE",
        state_after=audit_state,
        timestamp_iso=now_iso,
    )
    audit_entry = AuditLog(
        organization_id=case.organization_id,
        entity_name="CommunicationLog",
        entity_id=log_entry.id,
        event_type="MESSAGE_SENT",
        actor="CAMPAIGN_ENGINE",
        state_before={},
        state_after=audit_state,
        prev_hash=prev_hash,
        sha256_hash=sha_hash,
        timestamp_iso=now_iso,
        notes=f"Dispatched {dispatch_channel} recovery message to {recipient}",
        created_at=now_dt,
    )
    db.add(audit_entry)

    await db.commit()

    return {
        "status": "success",
        "message_id": msg_id,
        "channel": dispatch_channel,
        "recipient": recipient,
        "case_status": case.status.value,
    }
