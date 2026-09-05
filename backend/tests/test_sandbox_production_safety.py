import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings


@pytest.mark.asyncio
async def test_production_safety_and_sandbox_workflow():
    """
    Verify Production Safety and Autonomous Sandbox Workflow:
    1. In ENVIRONMENT=production, /api/v1/demo/reset strictly returns 403 Forbidden.
    2. /api/v1/sandbox/reset succeeds, creates 50 isolated synthetic transactions.
    3. Normal non-sandbox merchant transactions are never touched or deleted by sandbox resets.
    4. /api/v1/analytics/top-opportunities and /summary succeed without enum representation errors.
    5. /api/v1/sandbox/run executes AI orchestration with strict policy guardrails:
       - High-value transactions (>₹25,000) flagged as PENDING_APPROVAL.
       - Hard declines flagged as BLOCKED.
       - Retry limits reached flagged as STOPPED.
       - Recoverable failures settled safely via SANDBOX_GATEWAY.
    6. Verifies cryptographic SHA-256 audit ledger records for sandbox actions.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        run_id = uuid.uuid4().hex[:8]
        merchant_email = f"prod_safety_{run_id}@safestore.io"
        merchant_password = "SecurePassword123!"

        # 1. Signup merchant
        signup_res = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": merchant_email,
                "password": merchant_password,
                "full_name": "Prod Merchant",
                "company_name": "SafeStore Prod",
            },
        )
        assert signup_res.status_code in [200, 201]
        token = signup_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        org_id = signup_res.json()["organization"]["id"]

        # Create a real non-sandbox merchant customer and transaction
        cust_res = await client.post(
            "/api/v1/customers",
            headers=headers,
            json={
                "email": f"real_cust_{run_id}@example.com",
                "name": "Real Production Customer",
                "phone": "+919999999999",
            },
        )
        assert cust_res.status_code == 201
        real_cust_id = cust_res.json()["data"]["id"]

        real_txn_res = await client.post(
            "/api/v1/transactions",
            headers=headers,
            json={
                "transaction_id": f"TXN-REAL-PROD-{run_id}",
                "customer_id": real_cust_id,
                "amount": 15000.0,
                "currency": "INR",
                "status": "FAILED",
                "payment_method": "CARD",
                "failure_code": "GATEWAY_ERROR",
                "failure_reason": "Real live gateway failure",
            },
        )
        assert real_txn_res.status_code == 201
        real_txn_id = real_txn_res.json()["data"]["id"]

        # 2. Verify /demo/reset is strictly forbidden in production
        original_env = settings.ENVIRONMENT
        try:
            settings.ENVIRONMENT = "production"

            demo_res = await client.post("/api/v1/demo/reset", headers=headers)
            assert demo_res.status_code == 403, f"Expected 403 in production, got {demo_res.status_code}"
            assert "Demonstration endpoints are disabled in production" in demo_res.json()["message"]

            demo_run_res = await client.post("/api/v1/demo/run", headers=headers)
            assert demo_run_res.status_code == 403, f"Expected 403 in production, got {demo_run_res.status_code}"

            # 3. Verify /sandbox/reset works in production
            sbx_reset_res = await client.post("/api/v1/sandbox/reset", headers=headers)
            assert sbx_reset_res.status_code == 200
            sbx_reset_data = sbx_reset_res.json()["data"]
            assert sbx_reset_data["transactions_created"] == 50
            assert sbx_reset_data["is_sandbox"] is True
            assert sbx_reset_data["revenue_at_risk"] > 0

            # 4. Verify the real transaction was NOT deleted
            real_check = await client.get(f"/api/v1/transactions/{real_txn_id}", headers=headers)
            assert real_check.status_code == 200, "Real merchant transaction was incorrectly deleted by sandbox reset!"
            assert real_check.json()["data"]["id"] == real_txn_id

            # 5. Verify /api/v1/analytics/top-opportunities and /summary work without errors
            summary_res = await client.get("/api/v1/analytics/summary", headers=headers)
            assert summary_res.status_code == 200

            sbx_status_pre = await client.get("/api/v1/sandbox/status", headers=headers)
            assert sbx_status_pre.status_code == 200
            assert sbx_status_pre.json()["data"]["revenue_at_risk"] == sbx_reset_data["revenue_at_risk"]

            top_opps = await client.get("/api/v1/analytics/top-opportunities", headers=headers)
            assert top_opps.status_code == 200

            # 6. Run sandbox recovery batch
            run_res = await client.post("/api/v1/sandbox/run", headers=headers)
            assert run_res.status_code == 200
            run_data = run_res.json()["data"]
            assert run_data["transactions_analyzed"] >= 50
            assert run_data["transactions_recovered"] > 0
            assert run_data["revenue_recovered"] > 0
            assert run_data["transactions_approval_required"] >= 4  # High value > ₹25k
            assert run_data["transactions_blocked"] >= 6  # Hard declines
            assert run_data["transactions_stopped"] >= 6  # Retry limit exhausted

            # 7. Verify status endpoint
            status_res = await client.get("/api/v1/sandbox/status", headers=headers)
            assert status_res.status_code == 200
            status_data = status_res.json()["data"]
            assert status_data["revenue_recovered"] == run_data["revenue_recovered"]
            assert status_data["cases_pending_approval"] >= 4

            # 8. Verify audit log contains cryptographic chained SHA-256 records
            audit_res = await client.get("/api/v1/audit/logs?limit=150", headers=headers)
            assert audit_res.status_code == 200
            logs = audit_res.json()["data"]
            event_types = {l["event_type"] for l in logs}
            assert "SANDBOX_DATASET_RESET" in event_types
            assert "RECOVERY_VERIFIED" in event_types
            for l in logs:
                assert l["sha256_hash"] is not None
                assert len(l["sha256_hash"]) == 64

            # Verify cryptographic ledger chain integrity
            chain_res = await client.get("/api/v1/audit/verify-chain", headers=headers)
            assert chain_res.status_code == 200
            assert chain_res.json()["data"]["is_valid"] is True

        finally:
            settings.ENVIRONMENT = original_env
