import io
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db


@pytest.mark.asyncio
async def test_full_onboarding_and_two_tenant_isolation():
    await init_db()
    sfx = uuid.uuid4().hex[:6]
    
    email_alpha = f"alpha_founder_{sfx}@company-alpha.io"
    email_beta = f"beta_founder_{sfx}@company-beta.io"
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # ==========================================
        # 1. ACCOUNT A: SIGNUP -> ONBOARDING STEP 1 -> STEP 2 -> STEP 3
        # ==========================================
        signup_a = await client.post(
            "/api/v1/auth/signup",
            json={
                "full_name": "Alice Alpha",
                "email": email_alpha,
                "password": "PasswordAlpha123!",
                "company_name": "Company Alpha",
            },
        )
        assert signup_a.status_code == 201
        data_a = signup_a.json()
        token_a = data_a["access_token"]
        org_a_id = data_a["organization"]["id"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Step 1: Persist Workspace Identity
        step1_a = await client.patch(
            "/api/v1/organization/current",
            json={
                "name": "Company Alpha Enterprise",
                "industry": "Fintech & Banking",
                "company_size": "51-200 employees",
                "country": "India",
                "currency": "INR",
            },
            headers=headers_a,
        )
        assert step1_a.status_code == 200
        org_a_step1 = step1_a.json()
        assert org_a_step1["name"] == "Company Alpha Enterprise"
        assert org_a_step1["industry"] == "Fintech & Banking"
        assert org_a_step1["onboarding_completed"] is False

        # Simulate browser refresh during onboarding - verify DB persistence
        get_a_refresh = await client.get("/api/v1/organization/current", headers=headers_a)
        assert get_a_refresh.status_code == 200
        org_a_refreshed = get_a_refresh.json()
        assert org_a_refreshed["name"] == "Company Alpha Enterprise"
        assert org_a_refreshed["industry"] == "Fintech & Banking"

        # Step 2: Persist Recovery Guardrails
        step2_a = await client.patch(
            "/api/v1/organization/current",
            json={
                "max_retries": 4,
                "high_value_threshold": 35000.0,
                "require_human_approval": True,
                "hard_decline_behavior": "SUPPRESS",
                "auto_escalate_rules": "AFTER_MAX_RETRIES",
            },
            headers=headers_a,
        )
        assert step2_a.status_code == 200
        org_a_step2 = step2_a.json()
        assert org_a_step2["max_retries"] == 4
        assert org_a_step2["high_value_threshold"] == 35000.0

        # Step 3: Finalize Onboarding
        step3_a = await client.patch(
            "/api/v1/organization/current",
            json={
                "onboarding_completed": True,
            },
            headers=headers_a,
        )
        assert step3_a.status_code == 200
        assert step3_a.json()["onboarding_completed"] is True

        # Ingest failed transaction into Alpha
        create_txn_a = await client.post(
            "/api/v1/transactions",
            json={
                "transaction_id": f"txn_alpha_{sfx}",
                "customer_email": f"customer_{sfx}@alpha-client.com",
                "customer_name": "Alpha Customer One",
                "amount": 18500.0,
                "currency": "INR",
                "status": "FAILED",
                "payment_method": "CARD",
                "failure_reason": "Bank authorization timeout",
            },
            headers=headers_a,
        )
        assert create_txn_a.status_code == 201
        txn_a_id = create_txn_a.json()["data"]["id"]

        # Verify Alpha metrics
        metrics_a = await client.get("/api/v1/analytics/summary", headers=headers_a)
        assert metrics_a.status_code == 200
        summary_a = metrics_a.json()["data"]
        assert summary_a["revenue_at_risk"] == 18500.0
        assert summary_a["active_recovery_cases"] == 1
        assert summary_a["total_cases"] == 1

        # ==========================================
        # 2. ACCOUNT B: SIGNUP -> ONBOARDING STEP 1 -> STEP 2 -> STEP 3
        # ==========================================
        signup_b = await client.post(
            "/api/v1/auth/signup",
            json={
                "full_name": "Bob Beta",
                "email": email_beta,
                "password": "PasswordBeta123!",
                "company_name": "Company Beta",
            },
            headers={},
        )
        assert signup_b.status_code == 201
        data_b = signup_b.json()
        token_b = data_b["access_token"]
        org_b_id = data_b["organization"]["id"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        assert org_a_id != org_b_id

        # Complete Onboarding for Beta
        await client.patch(
            "/api/v1/organization/current",
            json={
                "name": "Company Beta Corp",
                "industry": "SaaS & Subscription",
                "company_size": "11-50 employees",
                "country": "India",
                "currency": "INR",
                "max_retries": 3,
                "high_value_threshold": 25000.0,
                "onboarding_completed": True,
            },
            headers=headers_b,
        )

        # ==========================================
        # 3. VERIFY BETA SEES PURE CLEAN ZERO DASHBOARD & ZERO DATA
        # ==========================================
        metrics_b = await client.get("/api/v1/analytics/summary", headers=headers_b)
        assert metrics_b.status_code == 200
        summary_b = metrics_b.json()["data"]
        assert summary_b["revenue_at_risk"] == 0.0
        assert summary_b["revenue_recovered"] == 0.0
        assert summary_b["recovery_rate_percentage"] == 0.0
        assert summary_b["active_recovery_cases"] == 0
        assert summary_b["successful_recoveries"] == 0
        assert summary_b["human_escalations"] == 0
        assert summary_b["total_cases"] == 0

        # Beta has 0 transactions
        txns_b = await client.get("/api/v1/transactions", headers=headers_b)
        assert txns_b.status_code == 200
        assert len(txns_b.json()["data"]) == 0

        # Beta has 0 recovery cases
        cases_b = await client.get("/api/v1/cases", headers=headers_b)
        assert cases_b.status_code == 200
        assert len(cases_b.json()["data"]) == 0

        # Beta cannot access Alpha's transaction
        get_alpha_by_beta = await client.get(f"/api/v1/transactions/{txn_a_id}", headers=headers_b)
        assert get_alpha_by_beta.status_code == 404

        # Beta audit logs only contain its own events
        audit_b = await client.get("/api/v1/audit/logs", headers=headers_b)
        assert audit_b.status_code == 200
        assert not any(l["entity_id"] == txn_a_id for l in audit_b.json()["data"])
