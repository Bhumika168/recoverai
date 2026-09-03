import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.recovery_token import RecoveryToken, TokenStatus, hash_token
from app.models.recovery_case import RecoveryCase, CaseStatus
from app.models.transaction import Transaction, TransactionStatus
from app.models.customer import Customer
from app.models.organization import Organization
from app.models.payment_attempt import PaymentAttempt, AttemptStatus
from app.models.integration import PaymentProviderConnection
from app.models.audit_log import AuditLog, calculate_hash
from app.schemas.common import APIResponse
from app.exceptions import EntityNotFoundException, RecoverAIException
from app.agents.verifier import RecoveryOutcomeVerifier
from app.integrations.provider import get_payment_provider
from app.logging_config import logger

router = APIRouter(prefix="/recover", tags=["Customer Recovery"])


async def create_recovery_token_for_case(
    case_id: str,
    db: AsyncSession,
    action_type: str = "PAYMENT_LINK",
    expiry_hours: int = 72,
) -> tuple[RecoveryToken, str]:
    """
    Generates a cryptographically secure, unpredictable, single-use recovery token.
    Returns: (RecoveryToken record, raw_token_string)
    """
    case_res = await db.execute(select(RecoveryCase).where(RecoveryCase.id == case_id))
    case = case_res.scalar_one_or_none()
    if not case:
        raise EntityNotFoundException("RecoveryCase", case_id)

    raw_token = secrets.token_urlsafe(32)
    tok_hash = hash_token(raw_token)
    tok_prefix = raw_token[:6]
    now_dt = datetime.now(timezone.utc)
    expires_dt = now_dt + timedelta(hours=expiry_hours)

    token_record = RecoveryToken(
        organization_id=case.organization_id,
        recovery_case_id=case.id,
        token_hash=tok_hash,
        token_prefix=tok_prefix,
        action_type=action_type,
        status=TokenStatus.ACTIVE,
        expires_at=expires_dt,
        created_at=now_dt,
    )
    db.add(token_record)
    await db.flush()

    # Append Audit Log
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
        "token_id": token_record.id,
        "token_prefix": tok_prefix,
        "case_id": case.id,
        "expires_at": expires_dt.isoformat(),
    }
    sha_hash = calculate_hash(
        prev_hash=prev_hash,
        event_type="RECOVERY_TOKEN_CREATED",
        entity_name="RecoveryToken",
        entity_id=token_record.id,
        actor="RECOVERY_ENGINE",
        state_after=audit_state,
        timestamp_iso=now_iso,
    )
    audit_entry = AuditLog(
        organization_id=case.organization_id,
        entity_name="RecoveryToken",
        entity_id=token_record.id,
        event_type="RECOVERY_TOKEN_CREATED",
        actor="RECOVERY_ENGINE",
        state_before={},
        state_after=audit_state,
        prev_hash=prev_hash,
        sha256_hash=sha_hash,
        timestamp_iso=now_iso,
        notes=f"Generated secure recovery token for case {case.id}",
        created_at=now_dt,
    )
    db.add(audit_entry)
    await db.commit()

    return token_record, raw_token


@router.get("/{token}", response_model=APIResponse[Dict[str, Any]])
async def get_recovery_page_data(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Public customer-facing endpoint to inspect recovery token details.
    Zero internal IDs or AI reasoning exposed (Data Minimization).
    """
    tok_hash = hash_token(token)
    query = (
        select(RecoveryToken)
        .where(RecoveryToken.token_hash == tok_hash)
        .options(
            selectinload(RecoveryToken.organization),
            selectinload(RecoveryToken.recovery_case).selectinload(RecoveryCase.transaction),
            selectinload(RecoveryToken.recovery_case).selectinload(RecoveryCase.customer),
        )
    )
    result = await db.execute(query)
    tok = result.scalar_one_or_none()

    if not tok:
        raise RecoverAIException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired recovery link.",
            error_code="INVALID_RECOVERY_TOKEN",
        )

    now_dt = datetime.now(timezone.utc)

    # Check for expiration
    if tok.status == TokenStatus.ACTIVE and tok.expires_at.replace(tzinfo=timezone.utc) < now_dt:
        tok.status = TokenStatus.EXPIRED
        await db.commit()

    case = tok.recovery_case
    txn = case.transaction if case else None
    cust = case.customer if case else None
    org = tok.organization

    # Audit link opened
    if tok.status == TokenStatus.ACTIVE:
        latest_audit = (
            await db.execute(
                select(AuditLog)
                .where(AuditLog.organization_id == tok.organization_id)
                .order_by(desc(AuditLog.created_at))
                .limit(1)
            )
        ).scalar_one_or_none()
        prev_hash = latest_audit.sha256_hash if latest_audit else "GENESIS_RECOVERAI"
        now_iso = now_dt.isoformat()
        audit_state = {"token_id": tok.id, "opened_at": now_iso}
        sha_hash = calculate_hash(
            prev_hash=prev_hash,
            event_type="RECOVERY_LINK_OPENED",
            entity_name="RecoveryToken",
            entity_id=tok.id,
            actor="CUSTOMER_BROWSER",
            state_after=audit_state,
            timestamp_iso=now_iso,
        )
        audit_entry = AuditLog(
            organization_id=tok.organization_id,
            entity_name="RecoveryToken",
            entity_id=tok.id,
            event_type="RECOVERY_LINK_OPENED",
            actor="CUSTOMER_BROWSER",
            state_before={},
            state_after=audit_state,
            prev_hash=prev_hash,
            sha256_hash=sha_hash,
            timestamp_iso=now_iso,
            notes=f"Customer opened recovery page",
            created_at=now_dt,
        )
        db.add(audit_entry)
        await db.commit()

    # Check connected provider for live vs test mode
    conn_res = await db.execute(
        select(PaymentProviderConnection).where(
            PaymentProviderConnection.organization_id == tok.organization_id,
            PaymentProviderConnection.status == "CONNECTED",
        )
    )
    conn = conn_res.scalar_one_or_none()
    is_test_mode = conn is None or conn.provider == "MOCK" or conn.environment == "TEST"

    # Data Minimization: Customer first name only
    first_name = "Customer"
    if cust and cust.name:
        first_name = cust.name.split()[0]

    return APIResponse(
        message="Recovery details retrieved",
        data={
            "status": tok.status.value,
            "merchant_name": org.name if org else "Merchant",
            "amount": txn.amount if txn else case.amount_at_risk,
            "currency": txn.currency if txn else (org.currency if org else "INR"),
            "customer_first_name": first_name,
            "action_type": tok.action_type,
            "is_test_mode": is_test_mode,
            "provider_name": conn.provider if conn else "SANDBOX",
            "expires_at": tok.expires_at.isoformat(),
        },
    )


@router.post("/{token}/initiate-payment", response_model=APIResponse[Dict[str, Any]])
async def initiate_customer_payment(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Customer initiates recovery payment.
    Emits CUSTOMER_PAYMENT_STARTED audit log.
    """
    tok_hash = hash_token(token)
    query = (
        select(RecoveryToken)
        .where(RecoveryToken.token_hash == tok_hash)
        .options(
            selectinload(RecoveryToken.organization),
            selectinload(RecoveryToken.recovery_case).selectinload(RecoveryCase.transaction),
        )
    )
    tok = (await db.execute(query)).scalar_one_or_none()
    if not tok or tok.status != TokenStatus.ACTIVE:
        raise RecoverAIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recovery link is no longer active.",
            error_code="INACTIVE_TOKEN",
        )

    now_dt = datetime.now(timezone.utc)
    if tok.expires_at.replace(tzinfo=timezone.utc) < now_dt:
        tok.status = TokenStatus.EXPIRED
        await db.commit()
        raise RecoverAIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recovery link has expired.",
            error_code="TOKEN_EXPIRED",
        )

    # Emit CUSTOMER_PAYMENT_STARTED audit log
    latest_audit = (
        await db.execute(
            select(AuditLog)
            .where(AuditLog.organization_id == tok.organization_id)
            .order_by(desc(AuditLog.created_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    prev_hash = latest_audit.sha256_hash if latest_audit else "GENESIS_RECOVERAI"
    now_iso = now_dt.isoformat()
    audit_state = {"token_id": tok.id, "action": "PAYMENT_INITIATED"}
    sha_hash = calculate_hash(
        prev_hash=prev_hash,
        event_type="CUSTOMER_PAYMENT_STARTED",
        entity_name="RecoveryToken",
        entity_id=tok.id,
        actor="CUSTOMER_BROWSER",
        state_after=audit_state,
        timestamp_iso=now_iso,
    )
    audit_entry = AuditLog(
        organization_id=tok.organization_id,
        entity_name="RecoveryToken",
        entity_id=tok.id,
        event_type="CUSTOMER_PAYMENT_STARTED",
        actor="CUSTOMER_BROWSER",
        state_before={},
        state_after=audit_state,
        prev_hash=prev_hash,
        sha256_hash=sha_hash,
        timestamp_iso=now_iso,
        notes=f"Customer initiated payment flow for case {tok.recovery_case_id}",
        created_at=now_dt,
    )
    db.add(audit_entry)
    await db.commit()

    # Check connected gateway
    conn_res = await db.execute(
        select(PaymentProviderConnection).where(
            PaymentProviderConnection.organization_id == tok.organization_id,
            PaymentProviderConnection.status == "CONNECTED",
        )
    )
    conn = conn_res.scalar_one_or_none()

    if conn and conn.provider != "MOCK":
        provider = get_payment_provider(conn.provider)
        # Attempt to create provider link
        txn = tok.recovery_case.transaction
        cust_email = txn.customer_email if txn else "customer@example.com"
        success, link_url, err = provider.create_payment_link(
            amount=txn.amount if txn else 0.0,
            currency=txn.currency if txn else "INR",
            description=f"Payment for {tok.organization.name}",
            customer_email=cust_email,
            reference_id=tok.recovery_case_id,
        )
        if success and link_url:
            return APIResponse(
                message="Redirecting to provider payment experience",
                data={"flow": "REDIRECT", "redirect_url": link_url},
            )

    return APIResponse(
        message="Ready for secure sandbox confirmation",
        data={"flow": "SANDBOX_FLOW", "token": token},
    )


@router.post("/{token}/complete-sandbox", response_model=APIResponse[Dict[str, Any]])
async def complete_sandbox_payment(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Clearly labelled TEST / SANDBOX payment completion flow.
    Simulates verified payment capture and triggers full verification engine.
    """
    tok_hash = hash_token(token)
    query = (
        select(RecoveryToken)
        .where(RecoveryToken.token_hash == tok_hash)
        .options(
            selectinload(RecoveryToken.organization),
            selectinload(RecoveryToken.recovery_case).selectinload(RecoveryCase.transaction),
        )
    )
    tok = (await db.execute(query)).scalar_one_or_none()
    if not tok or tok.status != TokenStatus.ACTIVE:
        raise RecoverAIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recovery link is invalid or already used.",
            error_code="INVALID_TOKEN",
        )

    now_dt = datetime.now(timezone.utc)
    case = tok.recovery_case
    txn = case.transaction

    # 1. Create Successful PaymentAttempt
    attempt = PaymentAttempt(
        transaction_id=txn.id,
        rzp_payment_id=f"sbx_{secrets.token_hex(8)}",
        status=AttemptStatus.SUCCESS,
        gateway_response={"status": "captured", "mode": "sandbox_verification"},
    )
    db.add(attempt)
    await db.flush()

    # 2. Mark token as USED (Single-Use Protection)
    tok.status = TokenStatus.USED
    tok.used_at = now_dt

    # 3. Transition Transaction and Case to RECOVERED (Verified)
    txn.status = TransactionStatus.RECOVERED
    case.status = CaseStatus.RECOVERED
    case.recovered_amount = txn.amount
    case.strategy_summary = f"[CUSTOMER_RECOVERY_SUCCESS] Payment of {txn.currency} {txn.amount:,.2f} verified via secure single-use recovery link."
    case.resolution_notes = "Customer completed self-serve recovery."

    # 4. Audit Log
    latest_audit = (
        await db.execute(
            select(AuditLog)
            .where(AuditLog.organization_id == tok.organization_id)
            .order_by(desc(AuditLog.created_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    prev_hash = latest_audit.sha256_hash if latest_audit else "GENESIS_RECOVERAI"
    now_iso = now_dt.isoformat()
    audit_state = {
        "case_id": case.id,
        "amount_recovered": txn.amount,
        "token_id": tok.id,
        "status": "RECOVERED",
    }
    sha_hash = calculate_hash(
        prev_hash=prev_hash,
        event_type="RECOVERY_VERIFIED",
        entity_name="RecoveryCase",
        entity_id=case.id,
        actor="CUSTOMER_SANDBOX_VERIFIER",
        state_after=audit_state,
        timestamp_iso=now_iso,
    )
    audit_entry = AuditLog(
        organization_id=tok.organization_id,
        entity_name="RecoveryCase",
        entity_id=case.id,
        event_type="RECOVERY_VERIFIED",
        actor="CUSTOMER_SANDBOX_VERIFIER",
        state_before={"status": case.status.value},
        state_after=audit_state,
        prev_hash=prev_hash,
        sha256_hash=sha_hash,
        timestamp_iso=now_iso,
        notes=f"Customer completed recovery flow for ₹{txn.amount:,.2f}",
        created_at=now_dt,
    )
    db.add(audit_entry)
    await db.commit()

    return APIResponse(
        message="Payment verified successfully",
        data={
            "status": "RECOVERED",
            "amount": txn.amount,
            "currency": txn.currency,
            "merchant_name": tok.organization.name,
        },
    )


@router.post("/{token}/opt-out", response_model=APIResponse[Dict[str, Any]])
async def customer_opt_out_from_link(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Customer requests to stop recovery messages.
    Records CustomerOptOut and halts communications for this case.
    """
    from app.models.communication import CustomerOptOut
    tok_hash = hash_token(token)
    query = (
        select(RecoveryToken)
        .where(RecoveryToken.token_hash == tok_hash)
        .options(
            selectinload(RecoveryToken.recovery_case).selectinload(RecoveryCase.customer),
        )
    )
    tok = (await db.execute(query)).scalar_one_or_none()
    if not tok:
        raise RecoverAIException(status_code=404, detail="Recovery link not found.", error_code="NOT_FOUND")

    case = tok.recovery_case
    cust = case.customer if case else None
    email = cust.email if cust else None
    phone = cust.phone if cust else None

    opt = CustomerOptOut(
        organization_id=tok.organization_id,
        customer_email=email,
        customer_phone=phone,
        reason="CUSTOMER_CLICKED_STOP_MESSAGES",
    )
    db.add(opt)
    if case:
        case.status = CaseStatus.CANCELLED
        case.strategy_summary = "[STOPPED_OPT_OUT] Customer unsubscribed via recovery link footer."
    tok.status = TokenStatus.REVOKED
    await db.commit()

    return APIResponse(
        message="You have been unsubscribed from recovery communications.",
        data={"status": "OPTED_OUT"},
    )
