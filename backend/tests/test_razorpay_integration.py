import hmac
import hashlib
import json
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.main import app
from app.database import init_db, AsyncSessionLocal
from app.config import settings
from app.models.recovery_case import RecoveryCase, CaseStatus
from app.models.transaction import Transaction, TransactionStatus, PaymentMethod
from app.models.recovery_action import RecoveryAction, ActionStatus, ActionType
from app.integrations.provider import (
    MockPaymentProvider,
    RazorpayPaymentProvider,
    get_payment_provider,
)
from app.integrations.razorpay.models import (
    RazorpayOrderPayload,
    RazorpayPaymentLinkPayload,
    RazorpayCustomerPayload,
)
from app.integrations.razorpay.webhooks import RazorpayWebhookVerifier, RazorpayWebhookHandler


# --------------------------------------------------------------------------
# 1. Test MockPaymentProvider
# --------------------------------------------------------------------------
def test_mock_payment_provider_operations():
    provider = MockPaymentProvider()
    assert provider.provider_name == "MOCK_GATEWAY"

    # Order creation
    order_payload = RazorpayOrderPayload(amount=299900, currency="INR", receipt="rcpt_test_001")
    order_res = provider.create_order(order_payload)
    assert order_res.id.startswith("order_mock_")
    assert order_res.amount == 299900
    assert order_res.status == "created"

    # Payment Link creation
    plink_payload = RazorpayPaymentLinkPayload(
        amount=199900,
        currency="INR",
        description="Test Recovery Link",
        customer={"email": "payer@example.com"},
    )
    plink_res = provider.create_payment_link(plink_payload)
    assert plink_res.id.startswith("plink_mock_")
    assert "https://rzp.io/i/" in plink_res.short_url
    assert plink_res.amount == 199900

    # Payment fetch
    payment_res = provider.fetch_payment("pay_mock_123")
    assert payment_res.id == "pay_mock_123"
    assert payment_res.status == "captured"

    # Customer creation
    cust_payload = RazorpayCustomerPayload(email="cust@test.com", name="Test Customer")
    cust_res = provider.create_customer(cust_payload)
    assert cust_res.id.startswith("cust_mock_")
    assert cust_res.email == "cust@test.com"


# --------------------------------------------------------------------------
# 2. Test RazorpayWebhookVerifier (HMAC SHA-256)
# --------------------------------------------------------------------------
def test_razorpay_webhook_signature_verification():
    secret = "secret_webhook_key_xyz_123"
    body_payload = json.dumps({"event": "payment.failed", "account_id": "acc_test_1"}).encode("utf-8")

    # Generate valid signature
    valid_signature = hmac.new(secret.encode("utf-8"), body_payload, hashlib.sha256).hexdigest()

    # Verify valid signature
    assert RazorpayWebhookVerifier.verify_signature(body_payload, valid_signature, secret=secret) is True

    # Verify tampered body is rejected
    tampered_body = json.dumps({"event": "payment.failed", "account_id": "acc_TAMPERED"}).encode("utf-8")
    assert RazorpayWebhookVerifier.verify_signature(tampered_body, valid_signature, secret=secret) is False

    # Verify invalid signature is rejected
    assert RazorpayWebhookVerifier.verify_signature(body_payload, "invalid_signature_hex", secret=secret) is False

    # Verify empty signature is rejected
    assert RazorpayWebhookVerifier.verify_signature(body_payload, "", secret=secret) is False


# --------------------------------------------------------------------------
# 3. Test Webhook Ingestion & Autonomous Recovery Trigger
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_webhook_payment_failed_triggers_recovery():
    await init_db()
    secret = "rzp_test_secret_9988"
    unique = uuid.uuid4().hex[:6]
    rzp_pay_id = f"pay_test_{unique}"
    rzp_ord_id = f"order_test_{unique}"
    email = f"webhook_user_{unique}@test.com"

    webhook_event = {
        "entity": "event",
        "account_id": "acc_test_recoverai",
        "event": "payment.failed",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": rzp_pay_id,
                    "entity": "payment",
                    "amount": 185000,  # 1850.00 INR
                    "currency": "INR",
                    "status": "failed",
                    "order_id": rzp_ord_id,
                    "method": "card",
                    "email": email,
                    "contact": "+919876543210",
                    "error_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
                    "error_description": "Payment authorization timed out at issuing bank gateway",
                    "error_source": "issuer",
                    "error_step": "payment_authorization",
                }
            }
        },
        "created_at": 1724345678,
    }

    raw_body = json.dumps(webhook_event).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Send webhook HTTP request
        headers = {
            "Content-Type": "application/json",
            "X-Razorpay-Signature": signature,
        }
        
        # Override secret for the test
        original_secret = settings.RAZORPAY_WEBHOOK_SECRET
        settings.RAZORPAY_WEBHOOK_SECRET = secret

        try:
            res = await ac.post("/api/webhooks/razorpay", content=raw_body, headers=headers)
            assert res.status_code == 200
            data = res.json()
            assert data["success"] is True
            assert data["result"]["status"] == "PROCESSED"
            assert data["result"]["event"] == "payment.failed"
            txn_id = data["result"]["transaction_id"]
            case_id = data["result"]["recovery_case_id"]

            # Verify RecoveryCase in DB
            async with AsyncSessionLocal() as session:
                case_res = await session.execute(
                    select(RecoveryCase)
                    .where(RecoveryCase.id == case_id)
                    .options(selectinload(RecoveryCase.transaction))
                )
                case = case_res.scalar_one()
                assert case.amount_at_risk == 1850.0
                assert case.status in [CaseStatus.IN_PROGRESS, CaseStatus.OPEN]
                assert case.transaction.rzp_payment_id == rzp_pay_id

        finally:
            settings.RAZORPAY_WEBHOOK_SECRET = original_secret


# --------------------------------------------------------------------------
# 4. Test Webhook Payment Link Paid Reconciles Recovery to RECOVERED
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_webhook_payment_link_paid_reconciliation():
    await init_db()
    secret = "rzp_test_secret_9988"
    unique = uuid.uuid4().hex[:6]
    plink_id = f"plink_test_{unique}"
    pay_id = f"pay_plink_{unique}"

    # Seed transaction, case, and action with plink_id
    async with AsyncSessionLocal() as session:
        from app.models.customer import Customer
        customer = Customer(email=f"payer_{unique}@test.com", name="Link Payer")
        session.add(customer)
        await session.flush()
        await session.refresh(customer)

        txn = Transaction(
            customer_id=customer.id,
            amount=5000.0,
            currency="INR",
            status=TransactionStatus.FAILED,
            payment_method=PaymentMethod.CARD,
            failure_code="CHECKOUT_ABANDONED",
        )
        session.add(txn)
        await session.flush()
        await session.refresh(txn)

        case = RecoveryCase(
            transaction_id=txn.id,
            customer_id=customer.id,
            status=CaseStatus.IN_PROGRESS,
            amount_at_risk=5000.0,
            recovered_amount=0.0,
        )
        session.add(case)
        await session.flush()
        await session.refresh(case)

        action = RecoveryAction(
            case_id=case.id,
            action_type=ActionType.PAYMENT_LINK,
            status=ActionStatus.SCHEDULED,
            idempotency_key=f"idemp_link_{unique}",
            rzp_payment_link_id=plink_id,
            rzp_short_url=f"https://rzp.io/i/{plink_id}",
        )
        session.add(action)
        await session.commit()

    # Prepare payment_link.paid webhook
    webhook_event = {
        "entity": "event",
        "account_id": "acc_test_recoverai",
        "event": "payment_link.paid",
        "contains": ["payment_link", "payment"],
        "payload": {
            "payment_link": {
                "entity": {
                    "id": plink_id,
                    "amount": 500000,  # 5000.00 INR
                    "status": "paid",
                }
            },
            "payment": {
                "entity": {
                    "id": pay_id,
                    "amount": 500000,
                    "status": "captured",
                }
            },
        },
        "created_at": 1724345999,
    }

    raw_body = json.dumps(webhook_event).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        original_secret = settings.RAZORPAY_WEBHOOK_SECRET
        settings.RAZORPAY_WEBHOOK_SECRET = secret

        try:
            res = await ac.post(
                "/api/webhooks/razorpay",
                content=raw_body,
                headers={"Content-Type": "application/json", "X-Razorpay-Signature": signature},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["result"]["status"] == "RECOVERED_VIA_LINK"
            assert data["result"]["plink_id"] == plink_id

            # Verify RecoveryCase is RECOVERED with full amount in database
            async with AsyncSessionLocal() as session:
                case_db = (
                    await session.execute(select(RecoveryCase).where(RecoveryCase.id == case.id))
                ).scalar_one()
                assert case_db.status == CaseStatus.RECOVERED
                assert case_db.recovered_amount == 5000.0
                assert case_db.recovered_at is not None
        finally:
            settings.RAZORPAY_WEBHOOK_SECRET = original_secret
