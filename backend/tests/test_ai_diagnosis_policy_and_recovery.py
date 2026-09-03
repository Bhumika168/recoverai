import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db


@pytest.mark.asyncio
async def test_full_ai_diagnosis_policy_and_recovery_scenarios():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        sfx = uuid.uuid4().hex[:6]

        # -------------------------------------------------------------
        # Organization Alpha Setup
        # -------------------------------------------------------------
        signup_res = await client.post(
            "/api/v1/auth/signup",
            json={
                "full_name": "Alpha Founder",
                "email": f"alpha_rec_{sfx}@alpha.io",
                "password": "PasswordAlpha123!",
                "company_name": "Alpha Recovery Corp",
            },
        )
        assert signup_res.status_code == 201
        token_a = signup_res.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Onboard with custom High-Value threshold = 20,000 INR, Max Retries = 3
        patch_org = await client.patch(
            "/api/v1/organization/current",
            json={
                "name": "Alpha Recovery Corp",
                "industry": "Fintech & SaaS",
                "currency": "INR",
                "max_retries": 3,
                "high_value_threshold": 20000.0,
                "onboarding_completed": True,
            },
            headers=headers_a,
        )
        assert patch_org.status_code == 200
        org_data = patch_org.json()
        assert (org_data.get("data") or org_data)["high_value_threshold"] == 20000.0

        # =============================================================
        # SCENARIO 1: TEMPORARY FAILURE (Bank Timeout, ₹5,000)
        # =============================================================
        txn_1_res = await client.post(
            "/api/v1/transactions",
            json={
                "transaction_id": f"TXN_TEMP_{sfx}",
                "amount": 5000.0,
                "currency": "INR",
                "status": "FAILED",
                "failure_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
                "failure_reason": "Gateway timeout communicating with bank",
                "payment_method": "CARD",
                "customer_email": "customer_temp@alpha.io",
            },
            headers=headers_a,
        )
        assert txn_1_res.status_code == 201
        txn_1_id = txn_1_res.json()["data"]["id"]

        # Check recovery case generated
        cases_res = await client.get("/api/v1/cases", headers=headers_a)
        assert cases_res.status_code == 200
        case_1 = next(c for c in cases_res.json()["data"] if c["transaction_id"] == txn_1_id)
        
        # Detail view inspection
        detail_1 = await client.get(f"/api/v1/cases/{case_1['id']}", headers=headers_a)
        assert detail_1.status_code == 200
        d1_data = detail_1.json()["data"]
        
        # Verify AI Diagnosis & Policy Engine Guardrails
        assert d1_data["ai_decisions"][0]["failure_category"] == "temporary_failure"
        assert d1_data["ai_decisions"][0]["recommended_action"] == "delayed_retry"
        assert d1_data["ai_decisions"][0]["confidence_score"] >= 0.80
        assert d1_data["requires_human_approval"] == "NO"
        assert d1_data["actions"][0]["policy_passed"] == "YES"
        assert d1_data["actions"][0]["action_type"] == "DELAYED_RETRY"

        # =============================================================
        # SCENARIO 2: INSUFFICIENT FUNDS (₹8,000)
        # =============================================================
        txn_2_res = await client.post(
            "/api/v1/transactions",
            json={
                "transaction_id": f"TXN_FUNDS_{sfx}",
                "amount": 8000.0,
                "currency": "INR",
                "status": "FAILED",
                "failure_code": "INSUFFICIENT_FUNDS",
                "failure_reason": "Not enough balance in account",
                "payment_method": "CARD",
                "customer_email": "customer_funds@alpha.io",
            },
            headers=headers_a,
        )
        assert txn_2_res.status_code == 201
        txn_2_id = txn_2_res.json()["data"]["id"]

        detail_2 = (await client.get(f"/api/v1/cases?limit=10", headers=headers_a)).json()["data"]
        case_2 = next(c for c in detail_2 if c["transaction_id"] == txn_2_id)
        d2_detail = (await client.get(f"/api/v1/cases/{case_2['id']}", headers=headers_a)).json()["data"]
        assert d2_detail["ai_decisions"][0]["failure_category"] == "insufficient_funds"
        assert d2_detail["requires_human_approval"] == "NO"

        # =============================================================
        # SCENARIO 3: HARD DECLINE (Stolen Card, ₹6,000) -> BLOCKED
        # =============================================================
        txn_3_res = await client.post(
            "/api/v1/transactions",
            json={
                "transaction_id": f"TXN_STOLEN_{sfx}",
                "amount": 6000.0,
                "currency": "INR",
                "status": "FAILED",
                "failure_code": "CARD_STOLEN_OR_LOST",
                "failure_reason": "Reported stolen card",
                "payment_method": "CARD",
                "customer_email": "customer_fraud@alpha.io",
            },
            headers=headers_a,
        )
        assert txn_3_res.status_code == 201
        txn_3_id = txn_3_res.json()["data"]["id"]

        detail_3 = (await client.get(f"/api/v1/cases?limit=10", headers=headers_a)).json()["data"]
        case_3 = next(c for c in detail_3 if c["transaction_id"] == txn_3_id)
        d3_detail = (await client.get(f"/api/v1/cases/{case_3['id']}", headers=headers_a)).json()["data"]
        assert d3_detail["ai_decisions"][0]["failure_category"] == "hard_decline"
        # Policy overrules automated retries on hard decline
        assert d3_detail["status"] in ["UNRECOVERABLE", "IN_PROGRESS"]
        # No automated card retry was dispatched
        for act in d3_detail["actions"]:
            assert act["action_type"] != "DELAYED_RETRY"

        # =============================================================
        # SCENARIO 4: HIGH VALUE (₹35,000 >= configured threshold ₹20,000)
        # =============================================================
        txn_4_res = await client.post(
            "/api/v1/transactions",
            json={
                "transaction_id": f"TXN_HIGHVAL_{sfx}",
                "amount": 35000.0,
                "currency": "INR",
                "status": "FAILED",
                "failure_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
                "failure_reason": "High value payment timeout",
                "payment_method": "CARD",
                "customer_email": "customer_vip@alpha.io",
            },
            headers=headers_a,
        )
        assert txn_4_res.status_code == 201
        txn_4_id = txn_4_res.json()["data"]["id"]

        case_4 = next(c for c in (await client.get("/api/v1/cases?limit=10", headers=headers_a)).json()["data"] if c["transaction_id"] == txn_4_id)
        d4_detail = (await client.get(f"/api/v1/cases/{case_4['id']}", headers=headers_a)).json()["data"]
        # Must require human approval because 35,000 >= 20,000
        assert d4_detail["requires_human_approval"] == "YES"
        assert d4_detail["status"] == "PENDING_APPROVAL"

        # Merchant Approves Case 4
        approve_res = await client.post(f"/api/v1/cases/{case_4['id']}/approve", headers=headers_a)
        assert approve_res.status_code == 200
        assert approve_res.json()["data"]["requires_human_approval"] == "NO"
        assert approve_res.json()["data"]["status"] == "IN_PROGRESS"

        # =============================================================
        # SCENARIO 5: RECOVERY VERIFICATION (Simulate Customer Payment)
        # =============================================================
        verify_res = await client.post(f"/api/v1/cases/{case_1['id']}/verify-recovery", headers=headers_a)
        assert verify_res.status_code == 200
        assert verify_res.json()["data"]["status"] == "RECOVERED"
        assert verify_res.json()["data"]["recovered_amount"] == 5000.0

        # Check KPI metrics updated dynamically
        analytics_res = await client.get("/api/v1/analytics/summary", headers=headers_a)
        assert analytics_res.status_code == 200
        kpis = analytics_res.json()["data"]
        assert kpis["revenue_recovered"] == 5000.0
        assert kpis["successful_recoveries"] == 1
        assert kpis["recovery_rate_percentage"] > 0.0

        # Verify Transaction status updated to RECOVERED
        txn_check = await client.get(f"/api/v1/transactions/{txn_1_id}", headers=headers_a)
        assert txn_check.status_code == 200
        assert txn_check.json()["data"]["status"] == "RECOVERED"

        # =============================================================
        # SCENARIO 6: AUDIT TRAIL SHA-256 INTEGRITY
        # =============================================================
        audit_verify = await client.get("/api/v1/audit/verify", headers=headers_a)
        assert audit_verify.status_code == 200
        assert audit_verify.json()["data"]["is_valid"] is True
        assert audit_verify.json()["data"]["total_entries_verified"] >= 4

        # =============================================================
        # SCENARIO 7: MULTI-TENANT ISOLATION (Organization Beta)
        # =============================================================
        signup_b = await client.post(
            "/api/v1/auth/signup",
            json={
                "full_name": "Beta Founder",
                "email": f"beta_rec_{sfx}@beta.io",
                "password": "PasswordBeta123!",
                "company_name": "Beta Corp",
            },
        )
        assert signup_b.status_code == 201
        token_b = signup_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Beta cannot access Alpha's case
        beta_get_alpha_case = await client.get(f"/api/v1/cases/{case_1['id']}", headers=headers_b)
        assert beta_get_alpha_case.status_code == 404

        # Beta cannot approve Alpha's case
        beta_approve_alpha = await client.post(f"/api/v1/cases/{case_1['id']}/approve", headers=headers_b)
        assert beta_approve_alpha.status_code == 404

        # Beta cannot verify Alpha's case
        beta_verify_alpha = await client.post(f"/api/v1/cases/{case_1['id']}/verify-recovery", headers=headers_b)
        assert beta_verify_alpha.status_code == 404

        # Beta has clean zero metrics
        beta_kpis = (await client.get("/api/v1/analytics/summary", headers=headers_b)).json()["data"]
        assert beta_kpis["revenue_at_risk"] == 0
        assert beta_kpis["revenue_recovered"] == 0
        assert beta_kpis["active_recovery_cases"] == 0
