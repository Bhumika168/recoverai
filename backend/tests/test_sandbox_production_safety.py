import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.models.recovery_case import CaseStatus


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_production_demo_endpoints_disabled():
    """Verify that in ENVIRONMENT=production, all /demo/* endpoints return 403 Forbidden."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create authenticated merchant
        uid = uuid.uuid4().hex[:6]
        signup = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": f"demo_block_{uid}@democommerce.io",
                "password": "Password123!",
                "full_name": "Demo Block Test",
                "company_name": "Demo Block Corp",
            },
        )
        token = signup.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        original_env = settings.ENVIRONMENT
        try:
            settings.ENVIRONMENT = "production"

            # /demo/reset
            res_reset = await client.post("/api/v1/demo/reset", headers=headers)
            assert res_reset.status_code == 403
            assert res_reset.json()["error"]["error_code"] == "DEMO_DISABLED_IN_PRODUCTION"

            # /demo/run
            res_run = await client.post("/api/v1/demo/run", headers=headers)
            assert res_run.status_code == 403
            assert res_run.json()["error"]["error_code"] == "DEMO_DISABLED_IN_PRODUCTION"

            # /demo/status
            res_status = await client.get("/api/v1/demo/status", headers=headers)
            assert res_status.status_code == 403
            assert res_status.json()["error"]["error_code"] == "DEMO_DISABLED_IN_PRODUCTION"
        finally:
            settings.ENVIRONMENT = original_env


@pytest.mark.asyncio
async def test_unauthenticated_sandbox_rejected():
    """Verify that unauthenticated requests to /sandbox/* are rejected with 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_reset = await client.post("/api/v1/sandbox/reset")
        assert res_reset.status_code == 401
        assert res_reset.json()["error"]["error_code"] == "UNAUTHENTICATED"

        res_run = await client.post("/api/v1/sandbox/run")
        assert res_run.status_code == 401
        assert res_run.json()["error"]["error_code"] == "UNAUTHENTICATED"

        res_status = await client.get("/api/v1/sandbox/status")
        assert res_status.status_code == 401
        assert res_status.json()["error"]["error_code"] == "UNAUTHENTICATED"


@pytest.mark.asyncio
async def test_authenticated_sandbox_session_and_tenant_isolation():
    """
    Verify:
    1. /sandbox/* resolves organization strictly from authenticated session.
    2. Sandbox data in Org A is strictly isolated from Org B.
    3. Normal non-sandbox merchant transactions are preserved.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create Org A
        uid_a = uuid.uuid4().hex[:6]
        signup_a = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": f"org_a_{uid_a}@merchant.com",
                "password": "Password123!",
                "full_name": "Org A Admin",
                "company_name": f"Org A {uid_a}",
            },
        )
        token_a = signup_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}
        org_a_id = signup_a.json()["organization"]["id"]

        # Create Org B
        uid_b = uuid.uuid4().hex[:6]
        signup_b = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": f"org_b_{uid_b}@merchant.com",
                "password": "Password123!",
                "full_name": "Org B Admin",
                "company_name": f"Org B {uid_b}",
            },
        )
        token_b = signup_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}
        org_b_id = signup_b.json()["organization"]["id"]

        # Create a real non-sandbox transaction in Org A
        cust_a = await client.post(
            "/api/v1/customers",
            headers=headers_a,
            json={"email": f"real_cust_{uid_a}@realcommerce.com", "name": "Real Customer A"},
        )
        real_txn = await client.post(
            "/api/v1/transactions",
            headers=headers_a,
            json={
                "transaction_id": f"TXN-REAL-A-{uid_a}",
                "customer_id": cust_a.json()["data"]["id"],
                "amount": 10000.0,
                "currency": "INR",
                "status": "FAILED",
                "payment_method": "CARD",
                "failure_code": "GATEWAY_ERROR",
                "failure_reason": "Real failure",
            },
        )
        real_txn_id = real_txn.json()["data"]["id"]

        # Org A resets sandbox dataset (even in production mode)
        original_env = settings.ENVIRONMENT
        try:
            settings.ENVIRONMENT = "production"
            reset_a = await client.post("/api/v1/sandbox/reset", headers=headers_a)
            assert reset_a.status_code == 200
            assert reset_a.json()["data"]["transactions_created"] == 50

            # Org A's real transaction must NOT be deleted
            check_real = await client.get(f"/api/v1/transactions/{real_txn_id}", headers=headers_a)
            assert check_real.status_code == 200

            # Org B's sandbox must be completely empty (0 transactions, 0 cases)
            status_b = await client.get("/api/v1/sandbox/status", headers=headers_b)
            assert status_b.status_code == 200
            assert status_b.json()["data"]["total_transactions"] == 0
            assert status_b.json()["data"]["revenue_at_risk"] == 0.0

            # Org A runs sandbox recovery
            run_a = await client.post("/api/v1/sandbox/run", headers=headers_a)
            assert run_a.status_code == 200
            assert run_a.json()["data"]["transactions_recovered"] > 0

            # Org B's metrics still remain 0
            status_b_after = await client.get("/api/v1/sandbox/status", headers=headers_b)
            assert status_b_after.json()["data"]["revenue_recovered"] == 0.0
            assert status_b_after.json()["data"]["total_transactions"] == 0
        finally:
            settings.ENVIRONMENT = original_env


@pytest.mark.asyncio
async def test_sandbox_cannot_invoke_live_provider():
    """
    Verify that /sandbox/* operations are strictly routed through SANDBOX_GATEWAY
    and cannot invoke live financial execution or payment gateways.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        uid = uuid.uuid4().hex[:6]
        signup = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": f"sbx_gateway_{uid}@merchant.com",
                "password": "Password123!",
                "full_name": "Gateway Check",
                "company_name": f"Gateway Corp {uid}",
            },
        )
        token = signup.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Reset & Run
        await client.post("/api/v1/sandbox/reset", headers=headers)
        await client.post("/api/v1/sandbox/run", headers=headers)

        # Inspect audit records to verify mock sandbox provider attribution
        audit_res = await client.get("/api/v1/audit/logs?limit=50", headers=headers)
        assert audit_res.status_code == 200
        logs = audit_res.json()["data"]

        settlement_logs = [l for l in logs if l["event_type"] == "RECOVERY_VERIFIED"]
        assert len(settlement_logs) > 0
        for l in settlement_logs:
            assert l["actor"] == "SANDBOX_GATEWAY"
            assert l["state_after"]["source"] == "SANDBOX_GATEWAY"
            assert "mock gateway" in l["notes"].lower() or "sandbox" in l["notes"].lower()


@pytest.mark.asyncio
async def test_policy_guardrails_human_approval_and_retry_stopping():
    """
    Verify:
    1. High-value transactions (>₹25,000) are flagged as PENDING_APPROVAL and require human approval.
    2. Hard declines (fraud/stolen) are BLOCKED.
    3. Retry limits (3 attempts) are STOPPED.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        uid = uuid.uuid4().hex[:6]
        signup = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": f"policy_{uid}@merchant.com",
                "password": "Password123!",
                "full_name": "Policy Tester",
                "company_name": f"Policy Test {uid}",
            },
        )
        token = signup.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        await client.post("/api/v1/sandbox/reset", headers=headers)
        run_res = await client.post("/api/v1/sandbox/run", headers=headers)
        assert run_res.status_code == 200
        data = run_res.json()["data"]

        # Policy guardrails verification
        assert data["transactions_approval_required"] >= 4, "High value >₹25k not gated to approval!"
        assert data["transactions_blocked"] >= 6, "Hard declines not blocked!"
        assert data["transactions_stopped"] >= 6, "Retry limit exhaustion not stopped!"

        # Query cases to inspect individual statuses
        cases_res = await client.get("/api/v1/cases?limit=100", headers=headers)
        assert cases_res.status_code == 200
        cases = cases_res.json()["data"]

        # Check high-value case
        high_val = [c for c in cases if c["amount_at_risk"] == 50000.0]
        assert len(high_val) > 0
        assert high_val[0]["status"] == "PENDING_APPROVAL"
        assert high_val[0]["requires_human_approval"] == "YES"
        assert high_val[0]["recovered_amount"] == 0.0

        # Check hard decline case (stolen card)
        stolen = [c for c in cases if c["amount_at_risk"] == 12000.0]
        assert len(stolen) > 0
        assert stolen[0]["status"] in ["BLOCKED", "UNRECOVERABLE"]
        assert stolen[0]["recovered_amount"] == 0.0


@pytest.mark.asyncio
async def test_verified_recovery_required_before_revenue_counted():
    """
    Verify:
    1. Revenue recovered strictly counts verified settlements.
    2. Invariant: sum(recovered_amount) == summary.revenue_recovered.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        uid = uuid.uuid4().hex[:6]
        signup = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": f"verified_{uid}@merchant.com",
                "password": "Password123!",
                "full_name": "Verified Tester",
                "company_name": f"Verified Test {uid}",
            },
        )
        token = signup.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        await client.post("/api/v1/sandbox/reset", headers=headers)

        # Before run: revenue recovered must be 0
        status_pre = await client.get("/api/v1/sandbox/status", headers=headers)
        assert status_pre.json()["data"]["revenue_recovered"] == 0.0

        run_res = await client.post("/api/v1/sandbox/run", headers=headers)
        recovered_expected = run_res.json()["data"]["revenue_recovered"]

        # After run: summary matches
        summary_res = await client.get("/api/v1/analytics/summary", headers=headers)
        assert summary_res.status_code == 200
        assert summary_res.json()["data"]["revenue_recovered"] == recovered_expected

        cases_res = await client.get("/api/v1/cases?limit=100", headers=headers)
        cases = cases_res.json()["data"]
        sum_cases = sum(c["recovered_amount"] for c in cases if c["status"] == "RECOVERED")
        assert sum_cases == recovered_expected


@pytest.mark.asyncio
async def test_audit_chain_remains_valid():
    """Verify cryptographic SHA-256 ledger integrity after sandbox actions."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        uid = uuid.uuid4().hex[:6]
        signup = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": f"chain_{uid}@merchant.com",
                "password": "Password123!",
                "full_name": "Chain Tester",
                "company_name": f"Chain Test {uid}",
            },
        )
        token = signup.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        await client.post("/api/v1/sandbox/reset", headers=headers)
        await client.post("/api/v1/sandbox/run", headers=headers)

        chain_res = await client.get("/api/v1/audit/verify-chain", headers=headers)
        assert chain_res.status_code == 200
        data = chain_res.json()["data"]
        assert data["is_valid"] is True
        assert data["total_entries_verified"] > 0
        assert data["invalid_entry_ids"] == []


@pytest.mark.asyncio
async def test_analytics_top_opportunities_no_longer_500():
    """Verify that /analytics/top-opportunities succeeds with 200 without PostgreSQL enum errors."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        uid = uuid.uuid4().hex[:6]
        signup = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": f"opps_{uid}@merchant.com",
                "password": "Password123!",
                "full_name": "Opps Tester",
                "company_name": f"Opps Test {uid}",
            },
        )
        token = signup.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        await client.post("/api/v1/sandbox/reset", headers=headers)
        await client.post("/api/v1/sandbox/run", headers=headers)

        opps_res = await client.get("/api/v1/analytics/top-opportunities?limit=5", headers=headers)
        assert opps_res.status_code == 200
        assert isinstance(opps_res.json()["data"], list)


@pytest.mark.asyncio
async def test_cors_headers_present_on_api_errors():
    """Verify that Access-Control-Allow-Origin is present on API error responses."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        origin_header = {"Origin": "https://recoverai-frontend-3ny5.onrender.com"}

        # 401 Unauthorized
        res_401 = await client.get("/api/v1/sandbox/status", headers=origin_header)
        assert res_401.status_code == 401
        assert "access-control-allow-origin" in res_401.headers
        assert res_401.headers["access-control-allow-origin"] in [
            "https://recoverai-frontend-3ny5.onrender.com",
            "*",
        ]

        # 404 Not Found
        res_404 = await client.get("/api/v1/non-existent-route", headers=origin_header)
        assert res_404.status_code == 404
        assert "access-control-allow-origin" in res_404.headers
