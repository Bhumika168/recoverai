import hmac
import hashlib
import json
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import AsyncSessionLocal
from app.models.organization import Organization
from app.models.transaction import Transaction, TransactionStatus
from app.models.recovery_case import RecoveryCase, CaseStatus
from app.models.integration import PaymentProviderConnection
from app.integrations.provider import get_payment_provider, PROVIDER_REGISTRY


@pytest.mark.asyncio
async def test_step18_provider_integrations_and_production_readiness():
    """
    Step 18: Real Provider Integrations & Production Readiness Verification.
    1. Provider-Agnostic Registry & Interface verification
    2. Secure Credential Connect & Masking (no plaintext secrets exposed)
    3. Generic Organization-Scoped Webhook with HMAC SHA-256 Signature Verification
    4. Idempotent Webhook Replay Protection (Duplicate webhook does not create duplicate financial records)
    5. Disconnect Provider Workflow
    6. Dedicated Health Check Probes (/health/live, /health/ready, /health)
    7. Multi-Tenant Isolation & Zero Data Leakage
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        run_id = uuid.uuid4().hex[:8]
        merchant_email = f"step18_merchant_{run_id}@nexuspay.io"
        merchant_password = "SecureProductionP@ssword2026!"

        # =========================================================================
        # 1. PROVIDER REGISTRY & ADAPTER ABSTRACTION
        # =========================================================================
        assert "STRIPE" in PROVIDER_REGISTRY
        assert "CASHFREE" in PROVIDER_REGISTRY
        assert "MOCK" in PROVIDER_REGISTRY

        mock_provider = get_payment_provider("MOCK")
        assert mock_provider.provider_name in ["MOCK", "MOCK_GATEWAY"]
        is_valid, _ = mock_provider.validate_credentials({"api_key": "mock_key"})
        assert is_valid is True

        # =========================================================================
        # 2. DEDICATED HEALTH PROBES (LIVENESS & READINESS)
        # =========================================================================
        live_res = await client.get("/health/live")
        assert live_res.status_code == 200
        assert live_res.json()["status"] == "alive"

        ready_res = await client.get("/health/ready")
        assert ready_res.status_code == 200
        assert ready_res.json()["status"] == "ready"
        assert ready_res.json()["database"] == "connected"

        health_res = await client.get("/health")
        assert health_res.status_code == 200
        assert health_res.json()["status"] == "healthy"

        # =========================================================================
        # 3. MERCHANT SIGNUP & AUTHENTICATION
        # =========================================================================
        signup_res = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": merchant_email,
                "password": merchant_password,
                "full_name": "Valerie Croft",
                "company_name": "Nexus Payment Systems",
            },
        )
        assert signup_res.status_code in [200, 201]
        auth_data = signup_res.json()
        token = auth_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        org_id = auth_data["organization"]["id"]

        # =========================================================================
        # 4. PROVIDER CONNECTION & SECRET MASKING
        # =========================================================================
        # Connect Sandbox/Mock Gateway
        connect_res = await client.post(
            "/api/v1/integrations/connect",
            headers=headers,
            json={
                "provider": "MOCK",
                "api_key": "mock_api_key_sandbox_9988",
                "secret_key": "mock_secret_key_ultra_secure_7766",
                "webhook_secret": "whsec_mock_production_hash_1234",
                "environment": "TEST",
            },
        )
        assert connect_res.status_code == 200
        conn_data = connect_res.json()["data"]
        assert conn_data["status"] == "CONNECTED"
        # Verify secret is masked (not plaintext)
        assert "mock_secret_key_ultra_secure_7766" not in str(connect_res.json())

        # List integrations and verify masking in catalog
        list_integ_res = await client.get("/api/v1/integrations", headers=headers)
        assert list_integ_res.status_code == 200
        mock_conn = next((i for i in list_integ_res.json()["data"] if i["provider"] == "MOCK"), None)
        assert mock_conn is not None
        assert mock_conn["status"] == "CONNECTED"
        assert mock_conn["api_key_masked"] is not None
        assert "mock_api_key_sandbox_9988" not in mock_conn["api_key_masked"]

        # =========================================================================
        # 5. GENERIC ORGANIZATION-SCORED WEBHOOK INGESTION
        # =========================================================================
        webhook_txn_id = f"TXN-WHK-{run_id}-001"
        webhook_payload = {
            "id": f"evt_{run_id}_01",
            "type": "payment.failed",
            "transaction_id": webhook_txn_id,
            "amount": 16500.0,
            "currency": "INR",
            "status": "FAILED",
            "failure_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
            "failure_reason": "Bank server timeout during authorization",
            "customer_email": f"cust_{run_id}@client.io",
        }
        raw_payload_bytes = json.dumps(webhook_payload).encode("utf-8")
        webhook_secret = "whsec_mock_production_hash_1234"
        valid_signature = hmac.new(webhook_secret.encode("utf-8"), raw_payload_bytes, hashlib.sha256).hexdigest()

        # Send signed webhook
        wh_res = await client.post(
            f"/api/v1/integrations/webhooks/mock?org_id={org_id}",
            content=raw_payload_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Signature": valid_signature,
            },
        )
        assert wh_res.status_code == 200
        wh_result = wh_res.json()
        assert wh_result["status"] == "success"

        # Verify transaction and recovery case created
        dash_res = await client.get("/api/v1/analytics/summary", headers=headers)
        assert dash_res.status_code == 200
        dash_data = dash_res.json()["data"]
        assert dash_data["revenue_at_risk"] == 16500.0
        assert dash_data["transaction_summary"]["failed"] == 1

        # =========================================================================
        # 6. IDEMPOTENCY / REPLAY PROTECTION
        # =========================================================================
        # Send EXACT SAME webhook payload again -> must be rejected or deduplicated safely
        wh_replay_res = await client.post(
            f"/api/v1/integrations/webhooks/mock?org_id={org_id}",
            content=raw_payload_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Signature": valid_signature,
            },
        )
        # Should be acknowledged as duplicate without incrementing financial metrics
        assert wh_replay_res.status_code in [200, 409]

        # Dashboard metrics must remain exactly ₹16,500 (NO duplicate count)
        dash_check_replay = await client.get("/api/v1/analytics/summary", headers=headers)
        assert dash_check_replay.json()["data"]["revenue_at_risk"] == 16500.0
        assert dash_check_replay.json()["data"]["transaction_summary"]["total"] == 1

        # =========================================================================
        # 7. INVALID WEBHOOK SIGNATURE REJECTION
        # =========================================================================
        bad_wh_res = await client.post(
            f"/api/v1/integrations/webhooks/mock?org_id={org_id}",
            content=raw_payload_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Signature": "invalid_forged_signature_attack",
            },
        )
        assert bad_wh_res.status_code in [400, 401, 403]

        # =========================================================================
        # 8. DISCONNECT PROVIDER LIFECYCLE
        # =========================================================================
        disconnect_res = await client.post(
            "/api/v1/integrations/disconnect",
            headers=headers,
            json={"provider": "MOCK"},
        )
        assert disconnect_res.status_code == 200
        assert disconnect_res.json()["data"]["status"] == "NOT_CONNECTED"

        # Verify list reflects NOT_CONNECTED
        list_after_disc = await client.get("/api/v1/integrations", headers=headers)
        mock_conn_after = next((i for i in list_after_disc.json()["data"] if i["provider"] == "MOCK"), None)
        assert mock_conn_after["status"] == "NOT_CONNECTED"

        # =========================================================================
        # 9. MULTI-TENANT ISOLATION
        # =========================================================================
        org_b_email = f"tenant_b_{run_id}@competitorcorp.net"
        signup_b = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": org_b_email,
                "password": merchant_password,
                "full_name": "Tenant B Lead",
                "company_name": "Rival Systems",
            },
        )
        assert signup_b.status_code in [200, 201]
        token_b = signup_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Org B dashboard is 0
        dash_b = await client.get("/api/v1/analytics/summary", headers=headers_b)
        assert dash_b.json()["data"]["revenue_at_risk"] == 0.0

        # Org B cannot access Org A's webhook events
        events_b = await client.get("/api/v1/integrations/events", headers=headers_b)
        assert events_b.status_code == 200
        assert len(events_b.json()["data"]) == 0
