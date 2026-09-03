import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.models.transaction import Transaction, TransactionStatus
from app.models.recovery_case import RecoveryCase, CaseStatus


@pytest.mark.asyncio
async def test_step20_hackathon_demonstration_mode():
    """
    Step 20: Hackathon Demonstration Mode & Measured Revenue Recovery.
    1. Reset 50-transaction deterministic dataset across failure categories
    2. Execute batch autonomous recovery workflow (Diagnosis -> Policy -> Sandbox Settlement)
    3. Verify Hard Declines are blocked by policy
    4. Verify High-Value transactions (>₹25,000) require human approval
    5. Verify Retry Limit stopping rules are enforced
    6. Verify Financial Invariant: sum(verified_settlements) == dashboard.revenue_recovered
    7. Verify SHA-256 cryptographic audit ledger verification
    8. Verify Multi-Tenant Isolation
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        run_id = uuid.uuid4().hex[:8]
        merchant_email = f"demo_merchant_{run_id}@democommerce.io"
        merchant_password = "SecureDemoP@ssword2026!"

        # =========================================================================
        # 1. MERCHANT SIGNUP & ORG CREATION
        # =========================================================================
        signup_res = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": merchant_email,
                "password": merchant_password,
                "full_name": "Demo Presenter",
                "company_name": "Demo Commerce",
            },
        )
        assert signup_res.status_code in [200, 201]
        token = signup_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        org_id = signup_res.json()["organization"]["id"]

        # =========================================================================
        # 2. RESET 50-TRANSACTION DETERMINISTIC DATASET
        # =========================================================================
        reset_res = await client.post("/api/v1/demo/reset", headers=headers)
        assert reset_res.status_code == 200
        reset_data = reset_res.json()["data"]
        assert reset_data["transactions_created"] == 50
        assert reset_data["revenue_at_risk"] > 0
        initial_risk = reset_data["revenue_at_risk"]

        # Initial dashboard state: ₹0 recovered, 50 failed transactions
        dash_initial = await client.get("/api/v1/analytics/summary", headers=headers)
        assert dash_initial.status_code == 200
        assert dash_initial.json()["data"]["revenue_at_risk"] == initial_risk
        assert dash_initial.json()["data"]["revenue_recovered"] == 0.0

        # =========================================================================
        # 3. RUN BATCH AUTONOMOUS RECOVERY WORKFLOW
        # =========================================================================
        run_res = await client.post("/api/v1/demo/run", headers=headers)
        assert run_res.status_code == 200
        run_data = run_res.json()["data"]

        assert run_data["transactions_analyzed"] == 50
        assert run_data["transactions_recovered"] > 0
        assert run_data["transactions_blocked"] > 0
        assert run_data["transactions_approval_required"] > 0
        assert run_data["transactions_stopped"] > 0
        assert (
            run_data["transactions_recovered"]
            + run_data["transactions_blocked"]
            + run_data["transactions_approval_required"]
            + run_data["transactions_stopped"]
            + run_data.get("transactions_action_scheduled", 0)
        ) == 50
        assert run_data["revenue_recovered"] > 0

        # =========================================================================
        # 4. FINANCIAL INVARIANT VERIFICATION
        # =========================================================================
        dash_after = await client.get("/api/v1/analytics/summary", headers=headers)
        assert dash_after.status_code == 200
        dash_recovered = dash_after.json()["data"]["revenue_recovered"]

        # Directly calculate recovered revenue from transactions
        txns_res = await client.get("/api/v1/transactions?limit=100", headers=headers)
        assert txns_res.status_code == 200
        txns = txns_res.json()["data"]
        independent_recovered_sum = sum(t["amount"] for t in txns if t["status"] in ["RECOVERED", "CAPTURED"])

        assert dash_recovered == independent_recovered_sum
        assert dash_recovered == run_data["revenue_recovered"]

        # =========================================================================
        # 5. POLICY GUARDRAIL VERIFICATION: HUMAN APPROVAL & HARD DECLINES
        # =========================================================================
        # Verify cases requiring human approval
        cases_res = await client.get("/api/v1/cases?status=PENDING_APPROVAL", headers=headers)
        assert cases_res.status_code == 200
        pending_cases = cases_res.json()["data"]
        assert len(pending_cases) >= 4  # 4 high-value cases held

        # Presenter executes Human Approval on one high-value case
        high_val_case = pending_cases[0]
        approve_res = await client.post(
            f"/api/v1/cases/{high_val_case['id']}/approve",
            headers=headers,
            json={"reason": "Executive approved enterprise tier recovery attempt"},
        )
        assert approve_res.status_code == 200

        # =========================================================================
        # 6. CRYPTOGRAPHIC SHA-256 AUDIT CHAIN VERIFICATION
        # =========================================================================
        audit_verify = await client.get("/api/v1/audit/verify-chain", headers=headers)
        assert audit_verify.status_code == 200
        assert audit_verify.json()["data"]["is_valid"] is True
        assert audit_verify.json()["data"]["total_entries_verified"] > 0

        # =========================================================================
        # 7. MULTI-TENANT ISOLATION
        # =========================================================================
        org_b_email = f"tenant_b_{run_id}@competitor.io"
        signup_b = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": org_b_email,
                "password": merchant_password,
                "full_name": "Org B Manager",
                "company_name": "Rival Store",
            },
        )
        assert signup_b.status_code in [200, 201]
        token_b = signup_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Org B dashboard has 0 transactions & 0 recovered revenue
        dash_b = await client.get("/api/v1/analytics/summary", headers=headers_b)
        assert dash_b.json()["data"]["revenue_at_risk"] == 0.0
        assert dash_b.json()["data"]["revenue_recovered"] == 0.0
