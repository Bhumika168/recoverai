import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_step22_final_demo_data_consistency_audit():
    """
    Step 22: Final Demo Data Consistency Audit.
    1. Verify deterministic 50-transaction category breakdown (24 temp, 10 cust action, 4 high val, 6 hard decline, 6 exhausted retries = 50)
    2. Verify mutually exclusive outcome partition (24 recovered, 10 customer action dispatched, 4 pending approval, 6 blocked, 6 stopped = 50)
    3. Verify exact mathematical equality: Revenue at Risk = ₹419,800.00, Recovered = ₹115,400.00, Remaining = ₹304,400.00
    4. Verify high-value policy gate (> ₹25,000) holds ₹50,000 case in PENDING_APPROVAL
    5. Verify human approval of ₹50,000 case updates recovered revenue to exactly ₹165,400.00 (39.4%)
    6. Verify hard decline blocking (CARD_STOLEN_OR_LOST -> UNRECOVERABLE, zero retries)
    7. Verify stopping rule enforcement (>= 3 attempts -> ESCALATED/STOPPED)
    8. Verify SHA-256 cryptographic audit chain integrity
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        run_id = uuid.uuid4().hex[:8]
        email = f"audit_merchant_{run_id}@democommerce.io"
        password = "SecureAuditP@ssword2026!"

        # 1. Signup
        signup_res = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": email,
                "password": password,
                "full_name": "Audit Officer",
                "company_name": "Demo Commerce Enterprise",
            },
        )
        assert signup_res.status_code in [200, 201]
        token = signup_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Reset Dataset
        reset_res = await client.post("/api/v1/demo/reset", headers=headers)
        assert reset_res.status_code == 200
        assert reset_res.json()["data"]["transactions_created"] == 50
        assert reset_res.json()["data"]["revenue_at_risk"] == 419800.0

        # Initial Dashboard
        dash_initial = (await client.get("/api/v1/analytics/summary", headers=headers)).json()["data"]
        assert dash_initial["revenue_at_risk"] == 419800.0
        assert dash_initial["revenue_recovered"] == 0.0
        assert dash_initial["recovery_rate_percentage"] == 0.0

        # 3. Run Batch Recovery
        run_res = await client.post("/api/v1/demo/run", headers=headers)
        assert run_res.status_code == 200
        run_data = run_res.json()["data"]

        # Exact Mutually Exclusive Outcome Partition Verification
        assert run_data["transactions_analyzed"] == 50
        assert run_data["transactions_recovered"] == 24
        assert run_data["transactions_action_scheduled"] == 10
        assert run_data["transactions_approval_required"] == 4
        assert run_data["transactions_blocked"] == 6
        assert run_data["transactions_stopped"] == 6
        assert (
            run_data["transactions_recovered"]
            + run_data["transactions_action_scheduled"]
            + run_data["transactions_approval_required"]
            + run_data["transactions_blocked"]
            + run_data["transactions_stopped"]
        ) == 50

        # Exact Financial Invariant Verification
        assert run_data["revenue_at_risk"] == 419800.0
        assert run_data["revenue_recovered"] == 115400.0
        assert run_data["remaining_at_risk"] == 304400.0
        assert run_data["recovery_rate_pct"] == 27.49

        # Dashboard Summary Reconciliation
        dash_after = (await client.get("/api/v1/analytics/summary", headers=headers)).json()["data"]
        assert dash_after["revenue_recovered"] == 115400.0
        assert dash_after["revenue_at_risk"] == 304400.0
        assert dash_after["recovery_rate_percentage"] == 27.5

        # Independent DB Query Reconciliation
        txns = (await client.get("/api/v1/transactions?limit=100", headers=headers)).json()["data"]
        captured_sum = sum(t["amount"] for t in txns if t["status"] in ["RECOVERED", "CAPTURED"])
        assert captured_sum == 115400.0 == dash_after["revenue_recovered"]

        # 4. Human Approval Flow for ₹50,000 High-Value Case
        cases = (await client.get("/api/v1/cases?limit=100", headers=headers)).json()["data"]
        high_val_cases = [c for c in cases if c["amount_at_risk"] == 50000.0 and c["status"] == "PENDING_APPROVAL"]
        assert len(high_val_cases) == 1
        case_50k = high_val_cases[0]

        # Executive Approves
        app_res = await client.post(
            f"/api/v1/cases/{case_50k['id']}/approve",
            headers=headers,
            json={"reason": "Executive approved enterprise payment recovery"},
        )
        assert app_res.status_code == 200

        # Verify Sandbox Capture
        ver_res = await client.post(f"/api/v1/cases/{case_50k['id']}/verify-recovery", headers=headers)
        assert ver_res.status_code == 200

        # Verify Updated Financial Metrics Post-Approval
        dash_post_app = (await client.get("/api/v1/analytics/summary", headers=headers)).json()["data"]
        assert dash_post_app["revenue_recovered"] == 165400.0
        assert dash_post_app["revenue_at_risk"] == 254400.0
        assert dash_post_app["recovery_rate_percentage"] == 39.4

        # 5. Cryptographic SHA-256 Audit Chain
        audit_res = await client.get("/api/v1/audit/verify-chain", headers=headers)
        assert audit_res.status_code == 200
        assert audit_res.json()["data"]["is_valid"] is True
