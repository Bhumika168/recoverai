import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Request, Response, Header, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_
from app.database import get_db
from app.models.organization import Organization
from app.models.integration import PaymentProviderConnection, WebhookEvent
from app.models.transaction import Transaction, TransactionStatus, PaymentMethod
from app.models.customer import Customer
from app.models.payment_attempt import PaymentAttempt, AttemptStatus
from app.models.recovery_case import RecoveryCase, CaseStatus
from app.models.audit_log import AuditLog, calculate_hash
from app.schemas.common import APIResponse
from app.exceptions import EntityNotFoundException, RecoverAIException
from app.api.deps import get_current_org_context, require_role
from app.integrations.provider import get_payment_provider, PROVIDER_REGISTRY, NormalizedPaymentEvent
from app.agents.orchestrator import recover_transaction
from app.logging_config import logger

router = APIRouter(prefix="/integrations", tags=["Payment Integrations"])


def mask_secret(secret: str) -> str:
    """Mask sensitive API keys or webhook secrets."""
    if not secret:
        return ""
    if len(secret) <= 8:
        return "••••••••"
    return f"{secret[:4]}••••••••{secret[-4:]}"


@router.get("", response_model=APIResponse[List[Dict[str, Any]]])
async def list_provider_connections(
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """
    List all supported payment providers and the active organization's connection status.
    Never exposes raw secrets to the frontend.
    """
    org, _ = org_context

    query = select(PaymentProviderConnection).where(PaymentProviderConnection.organization_id == org.id)
    result = await db.execute(query)
    connections = {c.provider.upper(): c for c in result.scalars().all()}

    providers_catalog = [
        {"id": "STRIPE", "name": "Stripe", "description": "Global card processing & recurring billing"},
        {"id": "RAZORPAY", "name": "Razorpay", "description": "UPI, Cards, Netbanking & Subscriptions in India"},
        {"id": "PAYPAL", "name": "PayPal", "description": "Digital wallet & international checkout"},
        {"id": "CASHFREE", "name": "Cashfree Payments", "description": "Payment gateway & auto-collect in India"},
        {"id": "MOCK", "name": "RecoverAI Sandbox Gateway", "description": "Deterministic simulation mode for testing"},
    ]

    response_list = []
    for p in providers_catalog:
        p_id = p["id"]
        conn = connections.get(p_id)
        
        response_list.append({
            "provider": p_id,
            "name": p["name"],
            "description": p["description"],
            "status": conn.status if conn else "NOT_CONNECTED",
            "environment": conn.environment if conn else "TEST",
            "api_key_masked": conn.api_key_masked if conn else None,
            "webhook_secret_masked": conn.webhook_secret_masked if conn else None,
            "webhook_url": conn.webhook_url if conn else f"/api/v1/integrations/webhooks/{p_id.lower()}?org_id={org.id}",
            "events_received": conn.events_received_count if conn else 0,
            "events_processed": conn.events_processed_count if conn else 0,
            "events_failed": conn.events_failed_count if conn else 0,
            "last_webhook_at": conn.last_webhook_at.isoformat() if conn and conn.last_webhook_at else None,
            "last_sync_at": conn.last_sync_at.isoformat() if conn and conn.last_sync_at else None,
            "last_error": conn.last_error if conn else None,
        })

    return APIResponse(
        message="Payment provider integrations retrieved",
        data=response_list,
    )


@router.post("/connect", response_model=APIResponse[Dict[str, Any]])
async def connect_payment_provider(
    payload: Dict[str, Any],
    org_context: tuple = Depends(require_role(["OWNER", "ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Connect or update provider credentials for the authenticated organization.
    Validates credential structure and tests gateway connectivity before storing.
    """
    org, membership = org_context
    provider_name = payload.get("provider", "").upper().strip()
    api_key = payload.get("api_key", "").strip()
    secret_key = payload.get("secret_key", "").strip()
    webhook_secret = payload.get("webhook_secret", "").strip()
    environment = payload.get("environment", "TEST").upper().strip()

    if provider_name not in PROVIDER_REGISTRY:
        raise RecoverAIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider '{provider_name}'.",
            error_code="INVALID_PROVIDER",
        )

    adapter = get_payment_provider(provider_name)
    is_valid, validation_msg = adapter.validate_credentials({
        "api_key": api_key,
        "secret_key": secret_key,
    })

    if not is_valid and provider_name != "MOCK":
        raise RecoverAIException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=validation_msg,
            error_code="CREDENTIAL_VALIDATION_FAILED",
        )

    # Find or create connection record
    query = select(PaymentProviderConnection).where(
        PaymentProviderConnection.organization_id == org.id,
        PaymentProviderConnection.provider == provider_name,
    )
    result = await db.execute(query)
    conn = result.scalar_one_or_none()

    webhook_url = f"/api/v1/integrations/webhooks/{provider_name.lower()}?org_id={org.id}"

    if not conn:
        conn = PaymentProviderConnection(
            organization_id=org.id,
            provider=provider_name,
            status="CONNECTED",
            environment=environment,
            api_key_masked=mask_secret(api_key),
            webhook_secret_masked=mask_secret(webhook_secret or secret_key),
            raw_credentials_encrypted={"api_key": api_key, "secret_key": secret_key, "webhook_secret": webhook_secret or secret_key},
            webhook_url=webhook_url,
            last_error=None,
        )
        db.add(conn)
    else:
        conn.status = "CONNECTED"
        conn.environment = environment
        conn.api_key_masked = mask_secret(api_key) if api_key else conn.api_key_masked
        conn.webhook_secret_masked = mask_secret(webhook_secret or secret_key) if (webhook_secret or secret_key) else conn.webhook_secret_masked
        conn.raw_credentials_encrypted = {"api_key": api_key, "secret_key": secret_key, "webhook_secret": webhook_secret or secret_key}
        conn.last_error = None

    await db.commit()
    await db.refresh(conn)

    return APIResponse(
        message=f"{provider_name} connected successfully.",
        data={
            "provider": conn.provider,
            "status": conn.status,
            "environment": conn.environment,
            "api_key_masked": conn.api_key_masked,
            "webhook_url": conn.webhook_url,
        },
    )


@router.post("/disconnect", response_model=APIResponse[Dict[str, Any]])
async def disconnect_payment_provider(
    payload: Dict[str, Any],
    org_context: tuple = Depends(require_role(["OWNER", "ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect an integrated payment provider for the authenticated organization."""
    org, _ = org_context
    provider_name = payload.get("provider", "").upper().strip()

    query = select(PaymentProviderConnection).where(
        PaymentProviderConnection.organization_id == org.id,
        PaymentProviderConnection.provider == provider_name,
    )
    result = await db.execute(query)
    conn = result.scalar_one_or_none()

    if conn:
        conn.status = "NOT_CONNECTED"
        conn.api_key_masked = None
        conn.webhook_secret_masked = None
        conn.raw_credentials_encrypted = None
        await db.commit()

    return APIResponse(
        message=f"{provider_name} disconnected successfully.",
        data={"provider": provider_name, "status": "NOT_CONNECTED"},
    )


@router.post("/test", response_model=APIResponse[Dict[str, Any]])
async def test_provider_connection(
    payload: Dict[str, Any],
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """Test connection credentials against the provider adapter."""
    provider_name = payload.get("provider", "").upper().strip()
    api_key = payload.get("api_key", "").strip()
    secret_key = payload.get("secret_key", "").strip()

    adapter = get_payment_provider(provider_name)
    is_valid, validation_msg = adapter.validate_credentials({
        "api_key": api_key,
        "secret_key": secret_key,
    })

    if not is_valid and provider_name != "MOCK":
        raise RecoverAIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=validation_msg,
            error_code="CONNECTION_TEST_FAILED",
        )

    return APIResponse(
        message="Connection verified successfully.",
        data={"verified": True, "provider": provider_name, "message": validation_msg},
    )


@router.post("/sync", response_model=APIResponse[Dict[str, Any]])
async def sync_recent_transactions(
    payload: Dict[str, Any],
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve recent provider transactions and ingest them into RecoverAI.
    Prevents duplicate transactions within the organization workspace.
    """
    org, _ = org_context
    provider_name = payload.get("provider", "MOCK").upper().strip()
    adapter = get_payment_provider(provider_name)

    raw_events = adapter.sync_recent_transactions({}, limit=10)
    synced_count = 0
    recoveries_triggered = 0

    for event in raw_events:
        existing = (
            await db.execute(
                select(Transaction).where(
                    Transaction.organization_id == org.id,
                    or_(
                        Transaction.id == event.provider_transaction_id,
                        Transaction.transaction_id == event.provider_transaction_id,
                    ),
                )
            )
        ).scalar_one_or_none()

        if existing:
            continue

        # Find or create customer
        cust_email = event.customer_email or f"{event.provider_transaction_id}@workspace.local"
        cust_res = await db.execute(select(Customer).where(Customer.organization_id == org.id, Customer.email == cust_email))
        customer = cust_res.scalar_one_or_none()
        if not customer:
            customer = Customer(organization_id=org.id, email=cust_email, name=event.customer_name or "Sync Customer")
            db.add(customer)
            await db.flush()
            await db.refresh(customer)

        txn_status = TransactionStatus.FAILED if event.status == "FAILED" else TransactionStatus.CAPTURED

        txn = Transaction(
            id=event.provider_transaction_id,
            organization_id=org.id,
            transaction_id=event.provider_transaction_id,
            customer_id=customer.id,
            customer_email=cust_email,
            amount=event.amount,
            currency=event.currency,
            status=txn_status,
            payment_method=PaymentMethod.CARD,
            failure_code=event.failure_code,
            failure_reason=event.failure_message,
            created_at=event.occurred_at or datetime.now(timezone.utc),
        )
        db.add(txn)
        await db.flush()
        synced_count += 1

        if txn_status == TransactionStatus.FAILED:
            await recover_transaction(txn.id, db, actor="INTEGRATION_SYNC")
            recoveries_triggered += 1

    # Update connection sync time
    conn_res = await db.execute(select(PaymentProviderConnection).where(PaymentProviderConnection.organization_id == org.id, PaymentProviderConnection.provider == provider_name))
    conn = conn_res.scalar_one_or_none()
    if conn:
        conn.last_sync_at = datetime.now(timezone.utc)

    await db.commit()

    return APIResponse(
        message=f"Manual sync completed. Ingested {synced_count} new transactions.",
        data={
            "synced_count": synced_count,
            "recoveries_triggered": recoveries_triggered,
        },
    )


@router.get("/events", response_model=APIResponse[List[Dict[str, Any]]])
async def list_webhook_events(
    limit: int = Query(50, ge=1, le=100),
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """List webhook events received for the authenticated organization."""
    org, _ = org_context
    query = (
        select(WebhookEvent)
        .where(WebhookEvent.organization_id == org.id)
        .order_by(desc(WebhookEvent.received_at))
        .limit(limit)
    )
    result = await db.execute(query)
    events = result.scalars().all()

    return APIResponse(
        message="Webhook events retrieved",
        data=[
            {
                "id": e.id,
                "provider": e.provider,
                "provider_event_id": e.provider_event_id,
                "event_type": e.event_type,
                "processing_status": e.processing_status,
                "processing_time_ms": e.processing_time_ms,
                "error_message": e.error_message,
                "received_at": e.received_at.isoformat() if e.received_at else None,
                "processed_at": e.processed_at.isoformat() if e.processed_at else None,
            }
            for e in events
        ],
    )


# ==============================================================================
# SECURE WEBHOOK INGESTION ENDPOINT
# ==============================================================================
@router.post("/webhooks/{provider_name}")
async def receive_provider_webhook(
    provider_name: str,
    request: Request,
    org_id: Optional[str] = Query(None),
    x_razorpay_signature: Optional[str] = Header(None, alias="X-Razorpay-Signature"),
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
    x_webhook_signature: Optional[str] = Header(None, alias="X-Webhook-Signature"),
    db: AsyncSession = Depends(get_db),
):
    """
    Secure webhook endpoint:
    1. Reads raw bytes and computes payload hash.
    2. Identifies target organization.
    3. Verifies webhook signature against organization's configured secret.
    4. Enforces duplicate replay protection (idempotency).
    5. Normalizes into standard RecoverAI event format.
    6. Creates/updates transaction & triggers autonomous recovery or verifies recovery.
    7. Appends immutable SHA-256 audit ledger entry.
    """
    start_time = time.time()
    prov_key = provider_name.upper().strip()
    raw_body = await request.body()
    payload_hash = hashlib.sha256(raw_body).hexdigest()

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed JSON payload.")

    # 1. Resolve Organization Connection
    org_obj = None
    conn_obj = None
    if org_id:
        org_res = await db.execute(select(Organization).where(Organization.id == org_id))
        org_obj = org_res.scalar_one_or_none()

    if org_obj:
        conn_res = await db.execute(
            select(PaymentProviderConnection).where(
                PaymentProviderConnection.organization_id == org_obj.id,
                PaymentProviderConnection.provider == prov_key,
            )
        )
        conn_obj = conn_res.scalar_one_or_none()

    # Fallback to demo/first connection if sandbox
    if not conn_obj:
        conn_res = await db.execute(
            select(PaymentProviderConnection).where(PaymentProviderConnection.provider == prov_key).limit(1)
        )
        conn_obj = conn_res.scalar_one_or_none()
        if conn_obj:
            org_res = await db.execute(select(Organization).where(Organization.id == conn_obj.organization_id))
            org_obj = org_res.scalar_one_or_none()

    if not org_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active organization connection found for this webhook.")

    # 2. Webhook Signature Verification
    signature_header = stripe_signature or x_razorpay_signature or x_webhook_signature or request.headers.get("x-signature")
    secret = (conn_obj.raw_credentials_encrypted or {}).get("webhook_secret") if conn_obj else None
    
    adapter = get_payment_provider(prov_key)
    if prov_key != "MOCK" or signature_header:
        if not signature_header or not secret or not adapter.verify_webhook_signature(raw_body, signature_header, secret):
            # Record Rejected Webhook Event
            rejected_event = WebhookEvent(
                organization_id=org_obj.id,
                provider=prov_key,
                event_type=payload.get("event") or payload.get("type", "unknown"),
                payload_hash=payload_hash,
                processing_status="REJECTED",
                processing_time_ms=(time.time() - start_time) * 1000,
                error_message="Invalid cryptographic webhook signature.",
            )
            db.add(rejected_event)
            await db.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook signature.")

    # 3. Duplicate Replay Protection (Idempotency)
    dup_res = await db.execute(
        select(WebhookEvent).where(
            WebhookEvent.organization_id == org_obj.id,
            WebhookEvent.payload_hash == payload_hash,
            WebhookEvent.processing_status == "PROCESSED",
        )
    )
    if dup_res.scalar_one_or_none():
        dup_event = WebhookEvent(
            organization_id=org_obj.id,
            provider=prov_key,
            event_type=payload.get("event") or payload.get("type", "unknown"),
            payload_hash=payload_hash,
            processing_status="DUPLICATE",
            processing_time_ms=(time.time() - start_time) * 1000,
            error_message="Duplicate webhook payload received. Skipped redundant processing.",
        )
        db.add(dup_event)
        await db.commit()
        return {"status": "ignored", "reason": "DUPLICATE_EVENT"}

    # 4. Normalize Event
    norm_event: NormalizedPaymentEvent = adapter.parse_webhook_event(payload)

    # 5. Process Transaction & Recovery Lifecycle
    cust_email = norm_event.customer_email or f"customer_{uuid.uuid4().hex[:6]}@workspace.local"
    cust_res = await db.execute(select(Customer).where(Customer.organization_id == org_obj.id, Customer.email == cust_email))
    customer = cust_res.scalar_one_or_none()
    if not customer:
        customer = Customer(
            organization_id=org_obj.id,
            email=cust_email,
            name=norm_event.customer_name or "Webhook Customer",
        )
        db.add(customer)
        await db.flush()
        await db.refresh(customer)

    txn_res = await db.execute(
        select(Transaction).where(
            Transaction.organization_id == org_obj.id,
            or_(
                Transaction.id == norm_event.provider_transaction_id,
                Transaction.transaction_id == norm_event.provider_transaction_id,
            ),
        )
    )
    txn = txn_res.scalar_one_or_none()

    if not txn:
        txn_status = TransactionStatus.FAILED if norm_event.status == "FAILED" else TransactionStatus.CAPTURED
        txn = Transaction(
            id=norm_event.provider_transaction_id,
            organization_id=org_obj.id,
            transaction_id=norm_event.provider_transaction_id,
            customer_id=customer.id,
            customer_email=cust_email,
            amount=norm_event.amount,
            currency=norm_event.currency,
            status=txn_status,
            payment_method=PaymentMethod.CARD,
            failure_code=norm_event.failure_code,
            failure_reason=norm_event.failure_message,
            created_at=norm_event.occurred_at or datetime.now(timezone.utc),
        )
        db.add(txn)
        await db.flush()
        await db.refresh(txn)

    # Trigger Recovery on Failure
    if norm_event.status == "FAILED":
        await recover_transaction(txn.id, db, actor=f"WEBHOOK:{prov_key}")

    # Verify Recovery on Capture / Payment Success
    elif norm_event.status == "CAPTURED":
        case_res = await db.execute(
            select(RecoveryCase).where(
                RecoveryCase.organization_id == org_obj.id,
                RecoveryCase.transaction_id == txn.id,
            )
        )
        case = case_res.scalar_one_or_none()
        if case and case.status != CaseStatus.RECOVERED:
            case.status = CaseStatus.RECOVERED
            case.recovered_amount = txn.amount
            case.recovered_at = datetime.now(timezone.utc)
            txn.status = TransactionStatus.RECOVERED
            await db.flush()

    # 6. Record Webhook Event & Update Connection Stats
    proc_time = (time.time() - start_time) * 1000
    evt_record = WebhookEvent(
        id=f"evt_{uuid.uuid4().hex[:12]}",
        organization_id=org_obj.id,
        provider=prov_key,
        provider_event_id=norm_event.event_id,
        event_type=norm_event.event_type,
        payload_hash=payload_hash,
        processing_status="PROCESSED",
        processing_time_ms=proc_time,
        normalized_event={
            "amount": norm_event.amount,
            "currency": norm_event.currency,
            "status": norm_event.status,
            "transaction_id": norm_event.provider_transaction_id,
        },
        processed_at=datetime.now(timezone.utc),
    )
    db.add(evt_record)
    await db.flush()

    if conn_obj:
        conn_obj.events_received_count += 1
        conn_obj.events_processed_count += 1
        conn_obj.last_webhook_at = datetime.now(timezone.utc)

    # 7. Append SHA-256 Chained Audit Event
    latest_audit = (
        await db.execute(
            select(AuditLog)
            .where(AuditLog.organization_id == org_obj.id)
            .order_by(desc(AuditLog.created_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    prev_hash = latest_audit.sha256_hash if latest_audit else "GENESIS_RECOVERAI"
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()

    audit_state = {
        "event_id": norm_event.event_id,
        "provider": prov_key,
        "transaction_id": txn.id,
        "amount": txn.amount,
        "status": norm_event.status,
    }
    sha_hash = calculate_hash(
        prev_hash=prev_hash,
        event_type="WEBHOOK_PROCESSED",
        entity_name="WebhookEvent",
        entity_id=evt_record.id,
        actor=f"GATEWAY:{prov_key}",
        state_after=audit_state,
        timestamp_iso=now_iso,
    )
    audit_entry = AuditLog(
        organization_id=org_obj.id,
        entity_name="WebhookEvent",
        entity_id=evt_record.id,
        event_type="WEBHOOK_PROCESSED",
        actor=f"GATEWAY:{prov_key}",
        state_before={},
        state_after=audit_state,
        prev_hash=prev_hash,
        sha256_hash=sha_hash,
        timestamp_iso=now_iso,
        notes=f"Processed signed {prov_key} webhook event: {norm_event.event_type}",
        created_at=now_dt,
    )
    db.add(audit_entry)

    await db.commit()

    return {
        "status": "success",
        "event_id": norm_event.event_id,
        "transaction_id": txn.id,
        "processing_time_ms": round(proc_time, 2),
    }
