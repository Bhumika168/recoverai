import hmac
import hashlib
import json
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db, AsyncSessionLocal
from app.models.organization import Organization, OrganizationMembership
from app.models.user import User
from app.models.integration import PaymentProviderConnection, WebhookEvent
from app.models.transaction import Transaction, TransactionStatus
from app.models.recovery_case import RecoveryCase, CaseStatus
from app.models.audit_log import AuditLog
from sqlalchemy import select


@pytest.mark.asyncio
async def test_step10_complete_provider_and_webhook_pipeline():
    await init_db()
    sfx = uuid.uuid4().hex[:6]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. SETUP ORG ALPHA
        signup_a = await client.post(
            "/api/v1/auth/signup",
            json={
                "full_name": "Integration Admin A",
                "email": f"admin_a_{sfx}@alpha.io",
                "password": "Password123!",
                "company_name": f"Alpha Corp {sfx}",
            },
        )
        assert signup_a.status_code == 201
        token_a = signup_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Complete onboarding
        await client.patch("/api/v1/organization/current", json={"onboarding_completed": True}, headers=headers_a)

        # ======================================================================
        # TEST 1 & 2 — Connect Provider & Invalid Credentials Check
        # ======================================================================
        # Invalid credentials test
        invalid_res = await client.post(
            "/api/v1/integrations/connect",
            json={
                "provider": "STRIPE",
                "api_key": "invalid_key",
                "secret_key": "secret",
                "environment": "TEST",
            },
            headers=headers_a,
        )
        assert invalid_res.status_code in [400, 422]

        # Valid connection
        valid_res = await client.post(
            "/api/v1/integrations/connect",
            json={
                "provider": "STRIPE",
                "api_key": "sk_test_51Mz000000000000000000000",
                "secret_key": "whsec_stripe_test_secret_12345",
                "webhook_secret": "whsec_stripe_test_secret_12345",
                "environment": "TEST",
            },
            headers=headers_a,
        )
        assert valid_res.status_code == 200
        conn_data = valid_res.json()["data"]
        assert conn_data["status"] == "CONNECTED"
        assert "••••" in conn_data["api_key_masked"]

        # List integrations
        list_res = await client.get("/api/v1/integrations", headers=headers_a)
        assert list_res.status_code == 200
        providers = list_res.json()["data"]
        stripe_p = next(p for p in providers if p["provider"] == "STRIPE")
        assert stripe_p["status"] == "CONNECTED"

        # Get Org ID
        me_res = await client.get("/api/v1/auth/me", headers=headers_a)
        org_a_id = me_res.json()["organization"]["id"]

        # ======================================================================
        # TEST 3 — Valid Signed Webhook (Failed Payment)
        # ======================================================================
        failed_txn_id = f"ch_failed_{sfx}"
        failed_payload = {
            "id": f"evt_stripe_fail_{sfx}",
            "type": "charge.failed",
            "data": {
                "object": {
                    "id": failed_txn_id,
                    "amount": 750000,
                    "currency": "usd",
                    "status": "failed",
                    "failure_code": "insufficient_funds",
                    "failure_message": "Card declined due to insufficient balance",
                    "receipt_email": "payer@enterprise.com",
                    "billing_details": {"name": "Payer Enterprise"},
                }
            },
        }
        failed_bytes = json.dumps(failed_payload).encode("utf-8")
        secret_stripe = "whsec_stripe_test_secret_12345"
        sig_header = hmac.new(secret_stripe.encode("utf-8"), failed_bytes, hashlib.sha256).hexdigest()

        wh_res = await client.post(
            f"/api/v1/integrations/webhooks/stripe?org_id={org_a_id}",
            content=failed_bytes,
            headers={"Stripe-Signature": sig_header, "Content-Type": "application/json"},
        )
        assert wh_res.status_code == 200
        assert wh_res.json()["status"] == "success"

        # Verify transaction and recovery case created automatically
        txn_list = (await client.get("/api/v1/transactions", headers=headers_a)).json()["data"]
        matching_txn = next((t for t in txn_list if t["id"] == failed_txn_id), None)
        assert matching_txn is not None
        assert matching_txn["amount"] == 7500.0
        assert matching_txn["status"] == "FAILED"

        # Recovery case must exist
        cases_list = (await client.get("/api/v1/cases", headers=headers_a)).json()["data"]
        matching_case = next((c for c in cases_list if c["transaction_id"] == failed_txn_id), None)
        assert matching_case is not None
        assert matching_case["status"] in ["IN_PROGRESS", "OPEN"]

        # ======================================================================
        # TEST 4 — Invalid Webhook Signature Rejected
        # ======================================================================
        bad_sig_res = await client.post(
            f"/api/v1/integrations/webhooks/stripe?org_id={org_a_id}",
            content=failed_bytes,
            headers={"Stripe-Signature": "invalid_forged_signature", "Content-Type": "application/json"},
        )
        assert bad_sig_res.status_code in [400, 401]

        # ======================================================================
        # TEST 5 — Duplicate Webhook Replay Protection
        # ======================================================================
        dup_res = await client.post(
            f"/api/v1/integrations/webhooks/stripe?org_id={org_a_id}",
            content=failed_bytes,
            headers={"Stripe-Signature": sig_header, "Content-Type": "application/json"},
        )
        assert dup_res.status_code == 200
        assert dup_res.json()["reason"] == "DUPLICATE_EVENT"

        # Webhook event count for DUPLICATE
        events_res = await client.get("/api/v1/integrations/events", headers=headers_a)
        assert events_res.status_code == 200
        evts = events_res.json()["data"]
        assert any(e["processing_status"] == "DUPLICATE" for e in evts)

        # ======================================================================
        # TEST 6 & 7 — Successful Payment Webhook & Verified Recovery
        # ======================================================================
        success_payload = {
            "id": f"evt_stripe_success_{sfx}",
            "type": "charge.captured",
            "data": {
                "object": {
                    "id": failed_txn_id,
                    "amount": 750000,
                    "currency": "usd",
                    "status": "succeeded",
                    "receipt_email": "payer@enterprise.com",
                    "billing_details": {"name": "Payer Enterprise"},
                }
            },
        }
        success_bytes = json.dumps(success_payload).encode("utf-8")
        success_sig = hmac.new(secret_stripe.encode("utf-8"), success_bytes, hashlib.sha256).hexdigest()

        wh_success_res = await client.post(
            f"/api/v1/integrations/webhooks/stripe?org_id={org_a_id}",
            content=success_bytes,
            headers={"Stripe-Signature": success_sig, "Content-Type": "application/json"},
        )
        assert wh_success_res.status_code == 200

        # Case must be updated to RECOVERED with verified amount
        case_detail = (await client.get(f"/api/v1/cases/{matching_case['id']}", headers=headers_a)).json()["data"]
        assert case_detail["status"] == "RECOVERED"
        assert case_detail["recovered_amount"] == 7500.0

        # ======================================================================
        # TEST 8 — Multi-Tenant Isolation (Org Beta)
        # ======================================================================
        signup_b = await client.post(
            "/api/v1/auth/signup",
            json={
                "full_name": "Integration Admin B",
                "email": f"admin_b_{sfx}@beta.io",
                "password": "Password123!",
                "company_name": f"Beta Corp {sfx}",
            },
        )
        assert signup_b.status_code == 201
        token_b = signup_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Beta integrations list should be NOT_CONNECTED for all
        beta_ints = (await client.get("/api/v1/integrations", headers=headers_b)).json()["data"]
        assert all(p["status"] == "NOT_CONNECTED" for p in beta_ints)

        # Beta webhook events list should be empty
        beta_evts = (await client.get("/api/v1/integrations/events", headers=headers_b)).json()["data"]
        assert len(beta_evts) == 0
