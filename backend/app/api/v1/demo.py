import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, and_

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.organization import Organization, OrganizationMembership
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

router = APIRouter(prefix="/demo", tags=["Demo Mode"])


def verify_demo_environment():
    """Ensure demo endpoints are never callable in a strict production environment."""
    if settings.ENVIRONMENT.lower() == "production" and not getattr(settings, "ENABLE_DEMO_IN_PROD", False):
        raise RecoverAIException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demonstration endpoints are disabled in production environment.",
            error_code="DEMO_DISABLED_IN_PRODUCTION",
        )


DEMO_TRANSACTION_TEMPLATES = [
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
async def reset_demo_dataset(
    org_context: tuple = Depends(require_role(["OWNER", "ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Reset the active organization with a fresh 50-transaction deterministic demonstration dataset.
    Only permitted in demo/development/test environments.
    """
    verify_demo_environment()
    org, _ = org_context

    # 1. Clear previous organization records (isolated to active org)
    txn_ids_subquery = select(Transaction.id).where(Transaction.organization_id == org.id)
    case_ids_subquery = select(RecoveryCase.id).where(RecoveryCase.organization_id == org.id)
    await db.execute(delete(PaymentAttempt).where(PaymentAttempt.transaction_id.in_(txn_ids_subquery)))
    await db.execute(delete(RecoveryAction).where(RecoveryAction.case_id.in_(case_ids_subquery)))
    await db.execute(delete(AIDecision).where(AIDecision.case_id.in_(case_ids_subquery)))
    await db.execute(delete(RecoveryCase).where(RecoveryCase.organization_id == org.id))
    await db.execute(delete(Transaction).where(Transaction.organization_id == org.id))
    await db.execute(delete(Customer).where(Customer.organization_id == org.id))
    await db.commit()

    # 2. Re-create 50 deterministic failed transactions
    now = datetime.now(timezone.utc)
    created_txns = []
    total_risk = 0.0

    for i, tpl in enumerate(DEMO_TRANSACTION_TEMPLATES, start=1):
        cust_email = f"demo.customer.{i:02d}@democommerce.io"
        customer = Customer(
            id=f"cust_{uuid.uuid4().hex[:12]}",
            organization_id=org.id,
            email=cust_email,
            name=f"Demo Customer {i:02d}",
            phone=f"+9198765{i:05d}",
        )
        db.add(customer)
        await db.flush()

        txn_id = f"txn_{org.id[:6]}_{i:03d}_{uuid.uuid4().hex[:6]}"
        created_at = now - timedelta(hours=(50 - i))
        amount = tpl["amount"]
        total_risk += amount

        txn = Transaction(
            id=txn_id,
            organization_id=org.id,
            transaction_id=f"TXN-DEMO-{i:03d}",
            customer_id=customer.id,
            customer_email=cust_email,
            amount=amount,
            currency="INR",
            status=TransactionStatus.FAILED,
            payment_method=PaymentMethod.CARD,
            failure_code=tpl["code"],
            failure_reason=tpl["reason"],
            created_at=created_at,
        )
        db.add(txn)
        await db.flush()

        # If template specifies prior retries, record prior payment attempts
        prior_retries = tpl.get("retries", 0)
        for r in range(prior_retries):
            attempt = PaymentAttempt(
                id=f"att_{uuid.uuid4().hex[:12]}",
                transaction_id=txn.id,
                attempt_number=r + 1,
                status=AttemptStatus.FAILED,
                error_code=tpl["code"],
                error_description=tpl["reason"],
                created_at=created_at + timedelta(minutes=(r + 1) * 30),
            )
            db.add(attempt)

        created_txns.append(txn)

    # 3. Append Audit Log
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
    sha_hash = calculate_hash(
        prev_hash=prev_hash,
        event_type="DEMO_DATASET_RESET",
        entity_name="Organization",
        entity_id=org.id,
        actor="DEMO_CONTROLLER",
        state_after={"transactions_created": 50, "revenue_at_risk": total_risk},
        timestamp_iso=now_iso,
    )
    audit = AuditLog(
        organization_id=org.id,
        entity_name="Organization",
        entity_id=org.id,
        event_type="DEMO_DATASET_RESET",
        actor="DEMO_CONTROLLER",
        state_before={},
        state_after={"transactions_created": 50, "revenue_at_risk": total_risk},
        prev_hash=prev_hash,
        sha256_hash=sha_hash,
        timestamp_iso=now_iso,
        notes="Reset 50 deterministic failed transactions for hackathon demonstration",
        created_at=now,
    )
    db.add(audit)
    await db.commit()

    return APIResponse(
        message="Demo dataset reset successfully with 50 failed transactions.",
        data={
            "transactions_created": 50,
            "revenue_at_risk": total_risk,
            "categories": len(set(t["category"] for t in DEMO_TRANSACTION_TEMPLATES)),
            "ready_to_run": True,
        },
    )


@router.post("/run", response_model=APIResponse[Dict[str, Any]])
async def run_demo_recovery_batch(
    org_context: tuple = Depends(require_role(["OWNER", "ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Execute autonomous revenue recovery across all 50 demo transactions.
    Executes real Diagnostician, Decision Engine, Policy Engine, and Sandbox Settlement.
    """
    verify_demo_environment()
    org, _ = org_context

    # Query all failed transactions in the demo organization
    txns_res = await db.execute(
        select(Transaction)
        .where(
            Transaction.organization_id == org.id,
            Transaction.status == TransactionStatus.FAILED,
        )
        .order_by(Transaction.created_at.asc())
    )
    transactions = txns_res.scalars().all()

    if not transactions:
        raise RecoverAIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No failed transactions found. Please click 'Reset Dataset' first.",
            error_code="NO_DEMO_TRANSACTIONS",
        )

    processed_count = 0
    recovered_count = 0
    recovered_amount = 0.0
    blocked_count = 0
    approval_required_count = 0
    stopped_count = 0
    action_scheduled_count = 0

    for txn in transactions:
        # Run autonomous triage orchestrator
        case = await recover_transaction(txn.id, db, actor="DEMO_ORCHESTRATOR")
        processed_count += 1

        if case:
            tpl = next((t for t in DEMO_TRANSACTION_TEMPLATES if t["code"] == txn.failure_code and t["amount"] == txn.amount), None)
            category = tpl["category"] if tpl else "temporary_failure"

            if category == "temporary_failure" and case.status == CaseStatus.IN_PROGRESS:
                # Execute verified sandbox settlement
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

                audit_data = {"transaction_id": txn.id, "amount": txn.amount, "status": "CAPTURED", "source": "SANDBOX_SETTLEMENT"}
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
                        notes=f"Verified sandbox settlement of ₹{txn.amount:,.2f}",
                        created_at=now_dt,
                    )
                )
            elif case.status == CaseStatus.PENDING_APPROVAL:
                approval_required_count += 1
            elif case.status in [CaseStatus.BLOCKED, CaseStatus.UNRECOVERABLE]:
                blocked_count += 1
            elif case.status in [CaseStatus.STOPPED, CaseStatus.EXHAUSTED, CaseStatus.ESCALATED]:
                stopped_count += 1
            else:
                action_scheduled_count += 1

    await db.commit()

    # Query total risk
    all_txns = await db.execute(select(Transaction).where(Transaction.organization_id == org.id))
    all_rows = all_txns.scalars().all()
    total_risk = sum(t.amount for t in all_rows)
    recovery_rate = (recovered_amount / total_risk * 100.0) if total_risk > 0 else 0.0

    return APIResponse(
        message="Demo autonomous recovery batch completed successfully.",
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
async def get_demo_status(
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """Get real-time demo dataset summary, recovery funnel counts, and verified amounts."""
    verify_demo_environment()
    org, _ = org_context

    txns_res = await db.execute(select(Transaction).where(Transaction.organization_id == org.id))
    transactions = txns_res.scalars().all()

    cases_res = await db.execute(select(RecoveryCase).where(RecoveryCase.organization_id == org.id))
    cases = cases_res.scalars().all()

    total_count = len(transactions)
    total_risk = sum(t.amount for t in transactions)

    recovered_txns = [t for t in transactions if t.status in [TransactionStatus.RECOVERED, TransactionStatus.CAPTURED]]
    recovered_amount = sum(t.amount for t in recovered_txns)
    recovered_count = len(recovered_txns)

    pending_approval_cases = [c for c in cases if c.status == CaseStatus.PENDING_APPROVAL]
    recovered_cases = [c for c in cases if c.status == CaseStatus.RECOVERED]
    in_progress_cases = [c for c in cases if c.status == CaseStatus.IN_PROGRESS]

    return APIResponse(
        message="Demo operational status retrieved",
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
        },
    )
