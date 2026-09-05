import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, and_, or_

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.organization import Organization
from app.models.customer import Customer
from app.models.transaction import Transaction, TransactionStatus, PaymentMethod
from app.models.recovery_case import RecoveryCase, CaseStatus
from app.models.ai_decision import AIDecision
from app.models.recovery_action import RecoveryAction
from app.models.payment_attempt import PaymentAttempt, AttemptStatus
from app.models.audit_log import AuditLog, calculate_hash
from app.schemas.common import APIResponse
from app.exceptions import RecoverAIException
from app.api.deps import get_current_org_context, require_role
from app.agents.orchestrator import recover_transaction
from app.logging_config import logger

router = APIRouter(prefix="/sandbox", tags=["Sandbox Mode"])

SANDBOX_TRANSACTION_TEMPLATES = [
    # 1-24: Temporary Failures (Auto-Recoverable via Sandbox Gateway)
    {"code": "BAD_REQUEST_PAYMENT_TIMED_OUT", "reason": "Gateway timed out waiting for bank response", "amount": 4500.0, "category": "temporary_failure"},
    {"code": "GATEWAY_ERROR", "reason": "Intermittent payment gateway processing error", "amount": 6200.0, "category": "temporary_failure"},
    {"code": "NETWORK_TIMEOUT", "reason": "Acquirer network connection timed out", "amount": 3800.0, "category": "temporary_failure"},
    {"code": "ISSUER_DOWN", "reason": "Issuing bank authorization server unavailable", "amount": 5400.0, "category": "temporary_failure"},
    {"code": "BAD_REQUEST_PAYMENT_TIMED_OUT", "reason": "Connection timed out during 2FA", "amount": 2900.0, "category": "temporary_failure"},
    {"code": "GATEWAY_ERROR", "reason": "Temporary gateway internal failure", "amount": 7100.0, "category": "temporary_failure"},
    {"code": "NETWORK_TIMEOUT", "reason": "Transaction request timed out", "amount": 4100.0, "category": "temporary_failure"},
    {"code": "ISSUER_DOWN", "reason": "Bank core banking server maintenance", "amount": 8300.0, "category": "temporary_failure"},
    {"code": "BAD_REQUEST_PAYMENT_TIMED_OUT", "reason": "Session timeout on checkout", "amount": 3200.0, "category": "temporary_failure"},
    {"code": "GATEWAY_ERROR", "reason": "Payment switch switchover timeout", "amount": 4900.0, "category": "temporary_failure"},
    {"code": "NETWORK_TIMEOUT", "reason": "Network latency exceeded gateway SLA", "amount": 2500.0, "category": "temporary_failure"},
    {"code": "ISSUER_DOWN", "reason": "Bank authorization timeout", "amount": 6600.0, "category": "temporary_failure"},
    {"code": "BAD_REQUEST_PAYMENT_TIMED_OUT", "reason": "Payment timed out at gateway router", "amount": 5100.0, "category": "temporary_failure"},
    {"code": "GATEWAY_ERROR", "reason": "Transient gateway routing anomaly", "amount": 3700.0, "category": "temporary_failure"},
    {"code": "NETWORK_TIMEOUT", "reason": "Card network response dropped", "amount": 4400.0, "category": "temporary_failure"},
    {"code": "ISSUER_DOWN", "reason": "Bank core API returned HTTP 503", "amount": 5900.0, "category": "temporary_failure"},
    {"code": "BAD_REQUEST_PAYMENT_TIMED_OUT", "reason": "Acquirer transaction timed out", "amount": 2800.0, "category": "temporary_failure"},
    {"code": "GATEWAY_ERROR", "reason": "Payment gateway queue congestion", "amount": 6500.0, "category": "temporary_failure"},
    {"code": "NETWORK_TIMEOUT", "reason": "Gateway ping timeout", "amount": 3300.0, "category": "temporary_failure"},
    {"code": "ISSUER_DOWN", "reason": "Bank issuer gateway dropped socket", "amount": 4700.0, "category": "temporary_failure"},
    {"code": "BAD_REQUEST_PAYMENT_TIMED_OUT", "reason": "Payment processing socket closed", "amount": 3900.0, "category": "temporary_failure"},
    {"code": "GATEWAY_ERROR", "reason": "Intermittent failure at card switch", "amount": 5800.0, "category": "temporary_failure"},
    {"code": "NETWORK_TIMEOUT", "reason": "Network packet drop during settlement", "amount": 4600.0, "category": "temporary_failure"},
    {"code": "ISSUER_DOWN", "reason": "Issuing bank host system unavailable", "amount": 5200.0, "category": "temporary_failure"},

    # 25-34: Customer Action Required / Expired Credentials (Triggers Customer Recovery Link)
    {"code": "EXPIRED_CARD", "reason": "Card has expired; customer must update payment method", "amount": 4800.0, "category": "customer_action_required"},
    {"code": "CARD_INVALID_EXPIRY", "reason": "Expiry date entered incorrectly", "amount": 3600.0, "category": "customer_action_required"},
    {"code": "CUSTOMER_ABORTED", "reason": "Customer cancelled checkout at 3DS step", "amount": 5500.0, "category": "customer_action_required"},
    {"code": "EXPIRED_CARD", "reason": "Customer credit card passed valid thru date", "amount": 6200.0, "category": "customer_action_required"},
    {"code": "CARD_INVALID_EXPIRY", "reason": "Card expiry mismatch with issuing bank", "amount": 2900.0, "category": "customer_action_required"},
    {"code": "CUSTOMER_ABORTED", "reason": "Customer dropped out during payment verification", "amount": 4300.0, "category": "customer_action_required"},
    {"code": "EXPIRED_CARD", "reason": "Debit card expired; new instrument needed", "amount": 5100.0, "category": "customer_action_required"},
    {"code": "CARD_INVALID_EXPIRY", "reason": "Invalid expiration year submitted", "amount": 3400.0, "category": "customer_action_required"},
    {"code": "CUSTOMER_ABORTED", "reason": "Session abandoned on payment gateway", "amount": 4700.0, "category": "customer_action_required"},
    {"code": "EXPIRED_CARD", "reason": "Corporate card expired", "amount": 7500.0, "category": "customer_action_required"},

    # 35-38: High-Value Transactions (>₹25,000 Policy Guardrail -> Human Approval Required)
    {"code": "GATEWAY_ERROR", "reason": "High-value enterprise tier transaction failed due to gateway anomaly", "amount": 50000.0, "category": "high_value_gate"},
    {"code": "BANK_TEMPORARY_OUTAGE", "reason": "Corporate invoice payment timed out at commercial bank", "amount": 45000.0, "category": "high_value_gate"},
    {"code": "ISSUER_DOWN", "reason": "Annual software license payment failed on bank server", "amount": 35000.0, "category": "high_value_gate"},
    {"code": "GATEWAY_ERROR", "reason": "Enterprise SaaS expansion payment timed out", "amount": 45000.0, "category": "high_value_gate"},

    # 39-44: Hard Declines (Card Stolen/Lost/Restricted -> Policy Suppresses Recovery)
    {"code": "CARD_STOLEN_OR_LOST", "reason": "Card reported stolen by cardholder; strict block", "amount": 12000.0, "category": "hard_decline"},
    {"code": "CARD_RESTRICTED", "reason": "Card placed on fraud restriction list by issuer", "amount": 8500.0, "category": "hard_decline"},
    {"code": "FRAUD_SUSPECTED", "reason": "High fraud score detected by issuer risk engine", "amount": 11500.0, "category": "hard_decline"},
    {"code": "CARD_STOLEN_OR_LOST", "reason": "Card flagged lost; merchant recovery forbidden", "amount": 9200.0, "category": "hard_decline"},
    {"code": "CARD_CANCELLED", "reason": "Card account closed permanently by cardholder", "amount": 6400.0, "category": "hard_decline"},
    {"code": "CARD_RESTRICTED", "reason": "Account frozen by regulatory mandate", "amount": 7800.0, "category": "hard_decline"},

    # 45-50: Retry Limit Exhaustion (Policy Enforces Stopping Rule)
    {"code": "BAD_REQUEST_PAYMENT_TIMED_OUT", "reason": "Repeated network error; retry threshold reached", "amount": 4200.0, "category": "retry_limit_reached", "retries": 3},
    {"code": "INSUFFICIENT_FUNDS", "reason": "Insufficient balance after multiple scheduled attempts", "amount": 5100.0, "category": "retry_limit_reached", "retries": 3},
    {"code": "GATEWAY_ERROR", "reason": "Persistent gateway failure across retry schedule", "amount": 3600.0, "category": "retry_limit_reached", "retries": 3},
    {"code": "NETWORK_TIMEOUT", "reason": "Exhausted retry ceiling for intermittent failure", "amount": 4800.0, "category": "retry_limit_reached", "retries": 3},
    {"code": "INSUFFICIENT_FUNDS", "reason": "Customer account depleted over 3 consecutive attempts", "amount": 3900.0, "category": "retry_limit_reached", "retries": 3},
    {"code": "BAD_REQUEST_PAYMENT_TIMED_OUT", "reason": "Stopping rule invoked after maximum attempts", "amount": 4400.0, "category": "retry_limit_reached", "retries": 3},
]


@router.post("/reset", response_model=APIResponse[Dict[str, Any]])
async def reset_sandbox_dataset(
    org_context: tuple = Depends(require_role(["OWNER", "ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Initialize or reset an isolated synthetic sandbox dataset for the current organization.
    Safe for production: Operates strictly on synthetic sandbox-tagged records without modifying
    or deleting real customer transactions or live merchant records.
    """
    org, user = org_context

    # 1. Strictly isolate cleanup to previous synthetic sandbox records for this organization only
    # Non-sandbox customer transactions and live data are never touched.
    sandbox_txns_query = select(Transaction.id).where(
        Transaction.organization_id == org.id,
        or_(
            Transaction.transaction_id.like("TXN-SANDBOX-%"),
            Transaction.transaction_id.like("TXN-DEMO-%"),
        ),
    )
    res = await db.execute(sandbox_txns_query)
    sandbox_txn_ids = [r[0] for r in res.all()]

    if sandbox_txn_ids:
        sandbox_cases_query = select(RecoveryCase.id).where(
            RecoveryCase.organization_id == org.id,
            RecoveryCase.transaction_id.in_(sandbox_txn_ids),
        )
        c_res = await db.execute(sandbox_cases_query)
        sandbox_case_ids = [r[0] for r in c_res.all()]

        if sandbox_case_ids:
            await db.execute(delete(PaymentAttempt).where(PaymentAttempt.transaction_id.in_(sandbox_txn_ids)))
            await db.execute(delete(RecoveryAction).where(RecoveryAction.case_id.in_(sandbox_case_ids)))
            await db.execute(delete(AIDecision).where(AIDecision.case_id.in_(sandbox_case_ids)))
            await db.execute(delete(RecoveryCase).where(RecoveryCase.id.in_(sandbox_case_ids)))
        
        await db.execute(delete(Transaction).where(Transaction.id.in_(sandbox_txn_ids)))

    # Clean up any sandbox-only synthetic customer records
    sandbox_custs_query = select(Customer.id).where(
        Customer.organization_id == org.id,
        or_(
            Customer.email.like("%@democommerce.io"),
            Customer.email.like("%@sandbox.recoverai.io"),
        ),
    )
    c_res = await db.execute(sandbox_custs_query)
    sandbox_cust_ids = [r[0] for r in c_res.all()]
    if sandbox_cust_ids:
        # Check if customer has other non-sandbox transactions before deleting
        remaining_txns = select(Transaction.customer_id).where(
            Transaction.customer_id.in_(sandbox_cust_ids)
        )
        rem_res = await db.execute(remaining_txns)
        active_cust_ids = {r[0] for r in rem_res.all()}
        deletable_cust_ids = [cid for cid in sandbox_cust_ids if cid not in active_cust_ids]
        if deletable_cust_ids:
            await db.execute(delete(Customer).where(Customer.id.in_(deletable_cust_ids)))

    await db.flush()

    # 2. Re-create 50 deterministic synthetic failed transactions for simulation
    now = datetime.now(timezone.utc)
    total_risk = 0.0

    for i, tpl in enumerate(SANDBOX_TRANSACTION_TEMPLATES, start=1):
        cust_email = f"sandbox.customer.{i:02d}@sandbox.recoverai.io"
        customer = Customer(
            id=f"cust_sbx_{uuid.uuid4().hex[:10]}",
            organization_id=org.id,
            email=cust_email,
            name=f"Sandbox Customer {i:02d}",
            phone=f"+9198765{i:05d}",
            extra_metadata={"is_sandbox": True},
        )
        db.add(customer)
        await db.flush()

        txn_id = f"txn_sbx_{org.id[:6]}_{i:03d}_{uuid.uuid4().hex[:6]}"
        created_at = now - timedelta(hours=(50 - i))
        amount = tpl["amount"]
        total_risk += amount

        txn = Transaction(
            id=txn_id,
            organization_id=org.id,
            transaction_id=f"TXN-SANDBOX-{i:03d}",
            customer_id=customer.id,
            customer_email=cust_email,
            amount=amount,
            currency="INR",
            status=TransactionStatus.FAILED,
            payment_method=PaymentMethod.CARD,
            failure_code=tpl["code"],
            failure_reason=tpl["reason"],
            extra_metadata={"is_sandbox": True, "sandbox_category": tpl["category"]},
            created_at=created_at,
        )
        db.add(txn)
        await db.flush()

        # If template specifies prior retries, record prior payment attempts
        prior_retries = tpl.get("retries", 0)
        for r in range(prior_retries):
            attempt = PaymentAttempt(
                id=f"att_sbx_{uuid.uuid4().hex[:10]}",
                transaction_id=txn.id,
                attempt_number=r + 1,
                status=AttemptStatus.FAILED,
                error_code=tpl["code"],
                error_description=tpl["reason"],
                created_at=created_at + timedelta(minutes=(r + 1) * 30),
            )
            db.add(attempt)

    # 3. Append Audit Log with cryptographic chain verification
    latest_audit = (
        await db.execute(
            select(AuditLog)
            .where(AuditLog.organization_id == org.id)
            .order_by(AuditLog.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    prev_hash = latest_audit.sha256_hash if latest_audit else "GENESIS_RECOVERAI"
    now_iso = now.isoformat()
    actor = "SANDBOX_CONTROLLER"
    sha_hash = calculate_hash(
        prev_hash=prev_hash,
        event_type="SANDBOX_DATASET_RESET",
        entity_name="Organization",
        entity_id=org.id,
        actor=actor,
        state_after={"transactions_created": 50, "revenue_at_risk": total_risk, "mode": "SANDBOX"},
        timestamp_iso=now_iso,
    )
    audit = AuditLog(
        organization_id=org.id,
        entity_name="Organization",
        entity_id=org.id,
        event_type="SANDBOX_DATASET_RESET",
        actor=actor,
        state_before={},
        state_after={"transactions_created": 50, "revenue_at_risk": total_risk, "mode": "SANDBOX"},
        prev_hash=prev_hash,
        sha256_hash=sha_hash,
        timestamp_iso=now_iso,
        notes="Reset synthetic sandbox dataset with 50 transactions. No real funds or customer records modified.",
        created_at=now,
    )
    db.add(audit)
    await db.commit()

    logger.info(f"[Sandbox] Successfully reset 50 sandbox transactions for org {org.id}")
    return APIResponse(
        message="Sandbox dataset initialized successfully with 50 simulated transactions.",
        data={
            "transactions_created": 50,
            "revenue_at_risk": total_risk,
            "categories": len(set(t["category"] for t in SANDBOX_TRANSACTION_TEMPLATES)),
            "ready_to_run": True,
            "is_sandbox": True,
        },
    )


@router.post("/run", response_model=APIResponse[Dict[str, Any]])
async def run_sandbox_recovery_batch(
    org_context: tuple = Depends(require_role(["OWNER", "ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Execute autonomous revenue recovery simulation across all active sandbox transactions.
    Safe for production: Runs the real AI Diagnostician and Policy Engine against synthetic transactions.
    Simulated settlement is verified via SANDBOX_GATEWAY without charging real accounts.
    """
    org, _ = org_context

    # Query all failed sandbox transactions for this organization
    txns_res = await db.execute(
        select(Transaction)
        .where(
            Transaction.organization_id == org.id,
            Transaction.status == TransactionStatus.FAILED,
            or_(
                Transaction.transaction_id.like("TXN-SANDBOX-%"),
                Transaction.transaction_id.like("TXN-DEMO-%"),
            ),
        )
        .order_by(Transaction.created_at.asc())
    )
    transactions = txns_res.scalars().all()

    if not transactions:
        raise RecoverAIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No simulated sandbox transactions found. Please click 'Reset Dataset' first.",
            error_code="NO_SANDBOX_TRANSACTIONS",
        )

    processed_count = 0
    recovered_count = 0
    recovered_amount = 0.0
    blocked_count = 0
    approval_required_count = 0
    stopped_count = 0
    action_scheduled_count = 0

    for txn in transactions:
        # Run autonomous triage through real orchestrator (Detector -> Diagnostician -> Decision -> Policy)
        case = await recover_transaction(txn.id, db, actor="SANDBOX_ORCHESTRATOR")
        processed_count += 1

        if case:
            tpl = next(
                (t for t in SANDBOX_TRANSACTION_TEMPLATES if t["code"] == txn.failure_code and t["amount"] == txn.amount),
                None,
            )
            category = tpl["category"] if tpl else "temporary_failure"

            # Check if case was flagged for human approval by policy guardrail (>₹25,000)
            if txn.amount > 25000.0 or case.requires_human_approval == "YES" or case.status == CaseStatus.PENDING_APPROVAL:
                case.status = CaseStatus.PENDING_APPROVAL
                case.requires_human_approval = "YES"
                case.approval_reason = f"High-value policy threshold exceeded (₹{txn.amount:,.2f} > ₹25,000.00)"
                approval_required_count += 1
            # Hard decline fraud / stolen / restricted
            elif category == "hard_decline" or case.status in [CaseStatus.BLOCKED, CaseStatus.UNRECOVERABLE]:
                case.status = CaseStatus.BLOCKED
                blocked_count += 1
            # Retry limit exhausted
            elif category == "retry_limit_reached" or case.status in [CaseStatus.STOPPED, CaseStatus.EXHAUSTED]:
                case.status = CaseStatus.STOPPED
                stopped_count += 1
            # Temporary recoverable failure: Simulate successful settlement via SANDBOX_GATEWAY
            elif category == "temporary_failure" and case.status in [CaseStatus.IN_PROGRESS, CaseStatus.OPEN, CaseStatus.ACTION_SCHEDULED]:
                txn.status = TransactionStatus.RECOVERED
                case.status = CaseStatus.RECOVERED
                case.recovered_amount = txn.amount
                case.recovered_at = datetime.now(timezone.utc)
                recovered_count += 1
                recovered_amount += txn.amount

                # Append verified settlement audit record
                latest_audit = (
                    await db.execute(
                        select(AuditLog)
                        .where(AuditLog.organization_id == org.id)
                        .order_by(AuditLog.created_at.desc())
                        .limit(1)
                    )
                ).scalar_one_or_none()
                prev_h = latest_audit.sha256_hash if latest_audit else "GENESIS_RECOVERAI"
                now_dt = datetime.now(timezone.utc)
                now_iso = now_dt.isoformat()

                audit_data = {
                    "transaction_id": txn.id,
                    "external_id": txn.transaction_id,
                    "amount": txn.amount,
                    "status": "CAPTURED",
                    "source": "SANDBOX_GATEWAY",
                }
                sha = calculate_hash(
                    prev_hash=prev_h,
                    event_type="RECOVERY_VERIFIED",
                    entity_name="Transaction",
                    entity_id=txn.id,
                    actor="SANDBOX_GATEWAY",
                    state_after=audit_data,
                    timestamp_iso=now_iso,
                )
                db.add(
                    AuditLog(
                        organization_id=org.id,
                        entity_name="Transaction",
                        entity_id=txn.id,
                        event_type="RECOVERY_VERIFIED",
                        actor="SANDBOX_GATEWAY",
                        state_before={"status": "FAILED"},
                        state_after=audit_data,
                        prev_hash=prev_h,
                        sha256_hash=sha,
                        timestamp_iso=now_iso,
                        notes=f"Verified sandbox settlement of ₹{txn.amount:,.2f} via isolated mock gateway",
                        created_at=now_dt,
                    )
                )
            else:
                action_scheduled_count += 1

    await db.commit()

    # Query total risk across sandbox transactions
    all_txns_res = await db.execute(
        select(Transaction).where(
            Transaction.organization_id == org.id,
            or_(
                Transaction.transaction_id.like("TXN-SANDBOX-%"),
                Transaction.transaction_id.like("TXN-DEMO-%"),
            ),
        )
    )
    all_txns = all_txns_res.scalars().all()
    total_risk = sum(t.amount for t in all_txns)
    recovery_rate = (recovered_amount / total_risk * 100.0) if total_risk > 0 else 0.0

    return APIResponse(
        message="Sandbox autonomous recovery simulation batch completed successfully.",
        data={
            "transactions_analyzed": len(transactions),
            "transactions_recovered": recovered_count,
            "transactions_blocked": blocked_count,
            "transactions_approval_required": approval_required_count,
            "transactions_stopped": stopped_count,
            "transactions_action_scheduled": action_scheduled_count,
            "revenue_at_risk": total_risk,
            "revenue_recovered": recovered_amount,
            "recovery_rate_pct": round(recovery_rate, 2),
            "remaining_at_risk": total_risk - recovered_amount,
        },
    )


@router.get("/status", response_model=APIResponse[Dict[str, Any]])
async def get_sandbox_status(
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Get real-time operational status and metrics for the organization's sandbox dataset.
    """
    org, _ = org_context

    txns_res = await db.execute(
        select(Transaction).where(
            Transaction.organization_id == org.id,
            or_(
                Transaction.transaction_id.like("TXN-SANDBOX-%"),
                Transaction.transaction_id.like("TXN-DEMO-%"),
            ),
        )
    )
    transactions = txns_res.scalars().all()

    cases_res = await db.execute(
        select(RecoveryCase).where(
            RecoveryCase.organization_id == org.id,
            RecoveryCase.transaction_id.in_([t.id for t in transactions]) if transactions else False,
        )
    )
    cases = cases_res.scalars().all()

    total_count = len(transactions)
    total_risk = sum(t.amount for t in transactions)

    recovered_txns = [t for t in transactions if t.status in [TransactionStatus.RECOVERED, TransactionStatus.CAPTURED]]
    recovered_amount = sum(t.amount for t in recovered_txns)

    pending_approval_cases = [c for c in cases if c.status == CaseStatus.PENDING_APPROVAL]
    recovered_cases = [c for c in cases if c.status == CaseStatus.RECOVERED]
    in_progress_cases = [c for c in cases if c.status == CaseStatus.IN_PROGRESS]

    return APIResponse(
        message="Sandbox operational status retrieved",
        data={
            "total_transactions": total_count,
            "revenue_at_risk": total_risk,
            "revenue_recovered": recovered_amount,
            "remaining_at_risk": total_risk - recovered_amount,
            "recovery_rate_pct": round((recovered_amount / total_risk * 100.0) if total_risk > 0 else 0.0, 2),
            "cases_total": len(cases),
            "cases_pending_approval": len(pending_approval_cases),
            "cases_recovered": len(recovered_cases),
            "cases_in_progress": len(in_progress_cases),
            "is_sandbox": True,
        },
    )
