import uuid
import random
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.customer import Customer
from app.models.transaction import Transaction, TransactionStatus, PaymentMethod
from app.models.payment_attempt import PaymentAttempt, AttemptStatus
from app.models.recovery_case import RecoveryCase, CaseStatus
from app.models.recovery_action import RecoveryAction, ActionStatus, ActionType
from app.models.ai_decision import AIDecision
from app.models.audit_log import AuditLog, calculate_hash
from app.models.user import User
from app.models.organization import Organization, OrganizationMembership
from app.services.auth_service import hash_password
from app.agents.orchestrator import recover_transaction
from app.logging_config import logger


DEMO_CUSTOMERS = [
    {"name": "Ananya Sharma", "email": "ananya.sharma@techcorp.in", "phone": "+919811223344", "risk": 0.05},
    {"name": "Vikram Malhotra", "email": "vikram.m@zenithsaas.com", "phone": "+919822334455", "risk": 0.10},
    {"name": "Priya Venkatesh", "email": "priya.v@finscale.io", "phone": "+919833445566", "risk": 0.08},
    {"name": "Rohan Deshmukh", "email": "rohan.d@urbancloud.co", "phone": "+919844556677", "risk": 0.15},
    {"name": "Meera Krishnan", "email": "meera@nexusretail.com", "phone": "+919855667788", "risk": 0.02},
    {"name": "Arjun Singhania", "email": "arjun@singhaniaholdings.com", "phone": "+919866778899", "risk": 0.20},
]

DEMO_SCENARIOS = [
    {
        "customer_idx": 0,
        "amount": 14999.0,
        "currency": "INR",
        "method": PaymentMethod.CARD,
        "code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
        "reason": "Bank authorization server did not respond within 30s window",
        "recovered": True,
        "days_ago": 4,
    },
    {
        "customer_idx": 1,
        "amount": 42500.0,  # High Value (> 25k)
        "currency": "INR",
        "method": PaymentMethod.CARD,
        "code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
        "reason": "High-value enterprise checkout gateway handoff latency",
        "recovered": False,
        "days_ago": 3,
    },
    {
        "customer_idx": 2,
        "amount": 3499.0,
        "currency": "INR",
        "method": PaymentMethod.UPI,
        "code": "CHECKOUT_ABANDONED",
        "reason": "Customer navigated away during UPI mandate approval window",
        "recovered": True,
        "days_ago": 2,
    },
    {
        "customer_idx": 3,
        "amount": 2199.0,
        "currency": "INR",
        "method": PaymentMethod.CARD,
        "code": "CARD_STOLEN_OR_LOST",
        "reason": "Card status returned as restricted/lost by issuing bank",
        "recovered": False,
        "days_ago": 2,
    },
    {
        "customer_idx": 4,
        "amount": 8999.0,
        "currency": "INR",
        "method": PaymentMethod.SUBSCRIPTION,
        "code": "INSUFFICIENT_FUNDS",
        "reason": "Account limit exceeded on monthly recurring SaaS subscription",
        "recovered": True,
        "days_ago": 1,
    },
    {
        "customer_idx": 5,
        "amount": 85000.0,  # High Value Enterprise
        "currency": "INR",
        "method": PaymentMethod.CARD,
        "code": "GATEWAY_ERROR",
        "reason": "Issuing bank core switch unavailable during settlement cycle",
        "recovered": False,
        "days_ago": 0,
    },
]


async def seed_database_if_empty(db: AsyncSession) -> int:
    """Seeds the isolated default demo merchant workspace with representative data."""
    demo_email = "demo@recoverai.com"
    existing_user = (await db.execute(select(User).where(User.email == demo_email))).scalar_one_or_none()
    
    if not existing_user:
        demo_user = User(
            email=demo_email,
            full_name="Alex Vance",
            hashed_password=hash_password("RecoverAI2026!"),
            is_active=True,
            is_verified=True,
        )
        db.add(demo_user)
        await db.flush()

        demo_org = Organization(
            name="Global Merchant Workspace",
            slug="global-merchant-workspace",
            industry="Fintech",
            company_size="50-200",
            country="India",
            currency="INR",
            onboarding_completed=True,
            max_retries=3,
            high_value_threshold=25000.0,
            auto_retry_enabled=True,
        )
        db.add(demo_org)
        await db.flush()

        membership = OrganizationMembership(
            user_id=demo_user.id,
            organization_id=demo_org.id,
            role="OWNER",
        )
        db.add(membership)
        await db.flush()
        await db.commit()
        logger.info(f"[Seed] Created demo user: {demo_email} and organization: {demo_org.name}")
    else:
        # Fetch demo organization
        demo_org = (
            await db.execute(select(Organization).where(Organization.slug == "global-merchant-workspace"))
        ).scalar_one_or_none()

    if not demo_org:
        return 0

    count = (
        await db.execute(select(func.count(RecoveryCase.id)).where(RecoveryCase.organization_id == demo_org.id))
    ).scalar() or 0
    if count >= 3:
        logger.info(f"[Seed] Demo organization already has {count} cases. Skipping case seed.")
        return count

    logger.info("[Seed] Seeding demo workspace with financial recovery cases...")

    created_customers = []
    for c_data in DEMO_CUSTOMERS:
        existing = (
            await db.execute(
                select(Customer).where(
                    Customer.organization_id == demo_org.id,
                    Customer.email == c_data["email"],
                )
            )
        ).scalar_one_or_none()
        if not existing:
            cust = Customer(
                organization_id=demo_org.id,
                email=c_data["email"],
                name=c_data["name"],
                phone=c_data["phone"],
                risk_score=c_data["risk"],
                recovery_receptivity_score=0.85,
            )
            db.add(cust)
            await db.flush()
            await db.refresh(cust)
            created_customers.append(cust)
        else:
            created_customers.append(existing)

    for scen in DEMO_SCENARIOS:
        cust = created_customers[scen["customer_idx"]]
        created_dt = datetime.now(timezone.utc) - timedelta(days=scen["days_ago"], hours=random.randint(1, 12))
        
        txn = Transaction(
            organization_id=demo_org.id,
            customer_id=cust.id,
            amount=scen["amount"],
            currency=scen["currency"],
            status=TransactionStatus.FAILED,
            payment_method=scen["method"],
            rzp_order_id=f"order_demo_{uuid.uuid4().hex[:8]}",
            rzp_payment_id=f"pay_demo_{uuid.uuid4().hex[:8]}",
            failure_code=scen["code"],
            failure_reason=scen["reason"],
            failure_source="issuer",
            error_step="payment_authorization",
            created_at=created_dt,
        )
        db.add(txn)
        await db.flush()
        await db.refresh(txn)

        attempt = PaymentAttempt(
            transaction_id=txn.id,
            attempt_number=1,
            rzp_payment_id=txn.rzp_payment_id,
            status=AttemptStatus.FAILED,
            error_code=scen["code"],
            error_description=scen["reason"],
            created_at=created_dt,
        )
        db.add(attempt)

        # Run recovery pipeline
        case = await recover_transaction(
            transaction_id=txn.id,
            db=db,
            actor="SYSTEM_SEED",
            simulated_immediate_success=scen["recovered"],
        )
        
        case.organization_id = demo_org.id
        case.created_at = created_dt
        if scen["recovered"]:
            case.status = CaseStatus.RECOVERED
            case.recovered_amount = scen["amount"]
            case.recovered_at = created_dt + timedelta(minutes=random.randint(15, 120))
            txn.status = TransactionStatus.RECOVERED
            cust.lifetime_recovered_amount += scen["amount"]

        await db.flush()

    await db.commit()
    logger.info("[Seed] Demo workspace seeding completed successfully.")
    return len(DEMO_SCENARIOS)
