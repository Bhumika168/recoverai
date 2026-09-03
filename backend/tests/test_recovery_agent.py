import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.main import app
from app.database import init_db, AsyncSessionLocal
from app.models.customer import Customer
from app.models.transaction import Transaction, TransactionStatus, PaymentMethod
from app.models.payment_attempt import PaymentAttempt, AttemptStatus
from app.models.recovery_case import RecoveryCase, CaseStatus
from app.models.recovery_action import RecoveryAction, ActionStatus
from app.agents.orchestrator import recover_transaction
from app.agents.policy_engine import policy_engine
from app.agents.diagnostician import diagnostician
from app.agents.decision_engine import decision_engine


async def create_test_transaction(
    amount: float = 4999.0,
    failure_code: str = "BAD_REQUEST_PAYMENT_TIMED_OUT",
    failure_reason: str = "Bank gateway timed out during processing",
    payment_method: PaymentMethod = PaymentMethod.CARD,
    prior_attempts: int = 1,
) -> str:
    """Helper to seed customer, failed transaction, and payment attempts."""
    unique = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as session:
        customer = Customer(
            email=f"user_{unique}@test.com",
            name=f"Test User {unique}",
            phone="+919876543210",
        )
        session.add(customer)
        await session.flush()
        await session.refresh(customer)

        txn = Transaction(
            customer_id=customer.id,
            amount=amount,
            currency="INR",
            status=TransactionStatus.FAILED,
            payment_method=payment_method,
            rzp_order_id=f"order_{unique}",
            rzp_payment_id=f"pay_{unique}",
            failure_code=failure_code,
            failure_reason=failure_reason,
            failure_source="issuer",
        )
        session.add(txn)
        await session.flush()
        await session.refresh(txn)

        for i in range(1, prior_attempts + 1):
            attempt = PaymentAttempt(
                transaction_id=txn.id,
                attempt_number=i,
                rzp_payment_id=f"pay_{unique}_{i}",
                status=AttemptStatus.FAILED,
                error_code=failure_code,
                error_description=failure_reason,
            )
            session.add(attempt)

        await session.commit()
        return txn.id


# --------------------------------------------------------------------------
# 1. Temporary Failure Test
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_temporary_failure():
    await init_db()
    txn_id = await create_test_transaction(
        amount=1999.0,
        failure_code="BAD_REQUEST_PAYMENT_TIMED_OUT",
        failure_reason="Issuer bank authorization timeout",
    )

    async with AsyncSessionLocal() as session:
        case = await recover_transaction(txn_id, session)
        assert case is not None
        assert case.amount_at_risk == 1999.0
        # Temporary failure should schedule retry or in-progress recovery
        assert case.status in [CaseStatus.IN_PROGRESS, CaseStatus.OPEN]
        assert case.recovery_score >= 80
        assert case.requires_human_approval == "NO"
        assert "DELAYED_RETRY" in case.strategy_summary or "SCHEDULED" in case.strategy_summary


# --------------------------------------------------------------------------
# 2. Hard Decline Test (Knows When Not to Act)
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_hard_decline_suppression():
    await init_db()
    txn_id = await create_test_transaction(
        amount=3500.0,
        failure_code="CARD_STOLEN_OR_LOST",
        failure_reason="Card reported stolen or lost at issuing bank",
    )

    async with AsyncSessionLocal() as session:
        case = await recover_transaction(txn_id, session)
        assert case is not None
        # Policy must strictly prevent retries and mark unrecoverable
        assert case.status == CaseStatus.UNRECOVERABLE
        assert case.retry_count == 0  # No automated retries executed
        assert "CUSTOMER_ACTION_REQUIRED" in case.strategy_summary or "Hard issuer decline" in case.strategy_summary


# --------------------------------------------------------------------------
# 3. Repeated Failure Test (Cap at 3 retries)
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_repeated_failure_limit():
    await init_db()
    txn_id = await create_test_transaction(
        amount=4500.0,
        failure_code="BAD_REQUEST_PAYMENT_TIMED_OUT",
        failure_reason="Repeated timeout across attempts",
        prior_attempts=3,  # Already failed 3 times
    )

    async with AsyncSessionLocal() as session:
        case = await recover_transaction(txn_id, session)
        assert case is not None
        # Must escalate to merchant queue and block further automated retry attempts
        assert case.status == CaseStatus.ESCALATED
        assert "HUMAN_ESCALATION" in case.strategy_summary or "Exceeded attempt threshold" in case.strategy_summary


# --------------------------------------------------------------------------
# 4. Low Confidence Test (Requires Escalation)
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_low_confidence_escalation():
    await init_db()
    txn_id = await create_test_transaction(
        amount=2500.0,
        failure_code="STRANGE_GATEWAY_CORRUPTION_CODE",
        failure_reason="Unknown esoteric switch error",
    )

    async with AsyncSessionLocal() as session:
        # Pass low confidence override (0.50 < 0.75 threshold)
        case = await recover_transaction(txn_id, session, override_confidence=0.50)
        assert case is not None
        assert case.status == CaseStatus.PENDING_APPROVAL
        assert case.requires_human_approval == "YES"
        assert "Low confidence" in case.approval_reason or "CONFIDENCE_THRESHOLD_CHECK" in str(case.approval_reason)


# --------------------------------------------------------------------------
# 5. High-Value Transaction Test (Requires Human Approval)
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_high_value_gate():
    await init_db()
    # High-value transaction >= ₹25,000
    txn_id = await create_test_transaction(
        amount=75000.0,
        failure_code="BAD_REQUEST_PAYMENT_TIMED_OUT",
        failure_reason="High value enterprise invoice gateway timeout",
    )

    async with AsyncSessionLocal() as session:
        case = await recover_transaction(txn_id, session)
        assert case is not None
        assert case.amount_at_risk == 75000.0
        # Must be held in PENDING_APPROVAL for human sign-off
        assert case.status == CaseStatus.PENDING_APPROVAL
        assert case.requires_human_approval == "YES"
        assert "High transaction value" in case.approval_reason or "HIGH_VALUE" in case.approval_reason


# --------------------------------------------------------------------------
# 6. Duplicate Recovery Action Test (Idempotency Protection)
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_duplicate_action_blocked():
    await init_db()
    txn_id = await create_test_transaction(
        amount=3000.0,
        failure_code="BAD_REQUEST_PAYMENT_TIMED_OUT",
    )

    async with AsyncSessionLocal() as session:
        # First execution schedules the action
        case1 = await recover_transaction(txn_id, session)
        assert case1.status in [CaseStatus.IN_PROGRESS, CaseStatus.OPEN]

        # Fetch transaction and existing actions
        query = (
            select(Transaction)
            .where(Transaction.id == txn_id)
            .options(
                selectinload(Transaction.recovery_case),
                selectinload(Transaction.payment_attempts),
            )
        )
        t = (await session.execute(query)).scalar_one()
        case = t.recovery_case
        
        actions_res = await session.execute(select(RecoveryAction).where(RecoveryAction.case_id == case.id))
        existing_actions = actions_res.scalars().all()
        
        diagnosis = diagnostician.diagnose(t, t.payment_attempts)
        rec = decision_engine.decide(t, diagnosis)

        # Evaluating policy with existing scheduled actions
        verdict = policy_engine.evaluate(
            transaction=t,
            recovery_case=case,
            diagnosis=diagnosis,
            recommendation=rec,
            existing_actions=existing_actions,
        )

        # Must reject duplicate
        assert verdict.approved is False
        assert "Duplicate action detected" in verdict.rejection_reason
