import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db


@pytest.mark.asyncio
async def test_step12_complete_dashboard_and_analytics_suite():
    await init_db()
    sfx = uuid.uuid4().hex[:6]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # ======================================================================
        # 1. SETUP ORG ALPHA (Brand New Organization)
        # ======================================================================
        signup_a = await client.post(
            "/api/v1/auth/signup",
            json={
                "full_name": "Dashboard Admin Alpha",
                "email": f"dash_alpha_{sfx}@alpha.io",
                "password": "Password123!",
                "company_name": f"Alpha Dash Corp {sfx}",
            },
        )
        assert signup_a.status_code == 201
        token_a = signup_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}
        await client.patch("/api/v1/organization/current", json={"onboarding_completed": True}, headers=headers_a)

        # ======================================================================
        # TEST 1 — Empty Organization Summary (₹0, 0, None)
        # ======================================================================
        summary_empty = await client.get("/api/v1/analytics/summary", headers=headers_a)
        assert summary_empty.status_code == 200
        empty_data = summary_empty.json()["data"]
        assert empty_data["revenue_at_risk"] == 0.0
        assert empty_data["revenue_recovered"] == 0.0
        assert empty_data["recovery_rate_percentage"] == 0.0
        assert empty_data["active_recovery_cases"] == 0
        assert empty_data["total_cases"] == 0
        assert empty_data["organization_name"] == f"Alpha Dash Corp {sfx}"
        assert empty_data["transaction_summary"]["total"] == 0

        # Empty Trend and Funnel
        trend_empty = await client.get("/api/v1/analytics/revenue-trend", headers=headers_a)
        assert trend_empty.status_code == 200
        assert len(trend_empty.json()["data"]) == 0

        # ======================================================================
        # TEST 2 — Add Transactions (Success, Failed, Pending)
        # ======================================================================
        # 1 Successful Txn (₹10,000)
        await client.post(
            "/api/v1/transactions",
            json={
                "transaction_id": f"TXN_SUCC_{sfx}",
                "amount": 10000.0,
                "currency": "INR",
                "customer_email": f"cust_succ_{sfx}@client.com",
                "payment_method": "UPI",
                "status": "CAPTURED",
            },
            headers=headers_a,
        )

        # 2 Failed Txns (₹15,000 + ₹25,000 = ₹40,000 at risk)
        await client.post(
            "/api/v1/transactions",
            json={
                "transaction_id": f"TXN_FAIL_1_{sfx}",
                "amount": 15000.0,
                "currency": "INR",
                "customer_email": f"cust_fail1_{sfx}@client.com",
                "payment_method": "CARD",
                "status": "FAILED",
                "failure_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
                "failure_reason": "Timeout during 3DS",
            },
            headers=headers_a,
        )
        await client.post(
            "/api/v1/transactions",
            json={
                "transaction_id": f"TXN_FAIL_2_{sfx}",
                "amount": 25000.0,
                "currency": "INR",
                "customer_email": f"cust_fail2_{sfx}@client.com",
                "payment_method": "NETBANKING",
                "status": "FAILED",
                "failure_code": "GATEWAY_ERROR",
                "failure_reason": "Bank server unreachable",
            },
            headers=headers_a,
        )

        # Re-fetch summary
        summary_populated = await client.get("/api/v1/analytics/summary", headers=headers_a)
        assert summary_populated.status_code == 200
        pop_data = summary_populated.json()["data"]
        assert pop_data["revenue_at_risk"] == 40000.0
        assert pop_data["revenue_recovered"] == 0.0
        assert pop_data["active_recovery_cases"] == 2
        assert pop_data["transaction_summary"]["total"] == 3
        assert pop_data["transaction_summary"]["successful"] == 1
        assert pop_data["transaction_summary"]["failed"] == 2

        # ======================================================================
        # TEST 3 — Time Range Filtering (7d, 30d, 90d, today)
        # ======================================================================
        summary_7d = await client.get("/api/v1/analytics/summary?range=7d", headers=headers_a)
        assert summary_7d.status_code == 200
        assert summary_7d.json()["data"]["revenue_at_risk"] == 40000.0

        # ======================================================================
        # TEST 4 — Verified Recovery (Simulate recovery on case 1 for ₹15,000)
        # ======================================================================
        cases_res = await client.get("/api/v1/cases", headers=headers_a)
        cases = cases_res.json()["data"]
        case_15k = next(c for c in cases if c["transaction_id"] == f"TXN_FAIL_1_{sfx}")
        
        # Trigger autonomous recovery & approve if needed
        await client.post(f"/api/v1/cases/{case_15k['id']}/trigger-recovery", headers=headers_a)

        # Ingest webhook capture event to verify real recovery
        connect_res = await client.post(
            "/api/v1/integrations/connect",
            json={
                "provider": "MOCK",
                "api_key": "mock_api_key_test",
                "secret_key": "mock_secret_test",
                "environment": "SANDBOX",
            },
            headers=headers_a,
        )
        assert connect_res.status_code in [200, 201]

        # Reconcile payment via webhook
        import hmac, hashlib
        sig = hmac.new(b"mock_secret_test", f"TXN_FAIL_1_{sfx}".encode("utf-8"), hashlib.sha256).hexdigest()
        org_a_id = signup_a.json()["organization"]["id"]
        wh_res = await client.post(
            f"/api/v1/integrations/webhooks/mock?org_id={org_a_id}",
            json={
                "event_id": f"evt_rec_{sfx}",
                "event_type": "payment.captured",
                "transaction_id": f"TXN_FAIL_1_{sfx}",
                "amount": 15000.0,
                "currency": "INR",
                "status": "CAPTURED",
            },
            headers={"X-Signature": sig},
        )
        assert wh_res.status_code == 200

        # Re-fetch summary to verify updated numbers
        summary_after_rec = await client.get("/api/v1/analytics/summary", headers=headers_a)
        data_after = summary_after_rec.json()["data"]
        assert data_after["revenue_recovered"] == 15000.0
        assert data_after["recovered_cases"] == 1
        assert data_after["revenue_at_risk"] == 25000.0
        # Recovery Rate: 15000 / 40000 * 100 = 37.5%
        assert data_after["recovery_rate_percentage"] == 37.5

        # ======================================================================
        # TEST 5 — Revenue Trend & Charts
        # ======================================================================
        trend_res = await client.get("/api/v1/analytics/revenue-trend?range=30d", headers=headers_a)
        assert trend_res.status_code == 200
        trend_pts = trend_res.json()["data"]
        assert len(trend_pts) >= 2
        assert trend_pts[-1]["recovered"] == 15000.0

        # ======================================================================
        # TEST 6 — Failure Breakdown & Recovery Funnel
        # ======================================================================
        breakdown_res = await client.get("/api/v1/analytics/failure-breakdown", headers=headers_a)
        assert breakdown_res.status_code == 200
        breakdown_data = breakdown_res.json()["data"]
        assert len(breakdown_data) >= 1

        funnel_res = await client.get("/api/v1/analytics/recovery-funnel", headers=headers_a)
        assert funnel_res.status_code == 200
        funnel_stages = funnel_res.json()["data"]
        assert len(funnel_stages) == 5
        assert funnel_stages[0]["stage"] == "Revenue At Risk"
        assert funnel_stages[4]["stage"] == "Verified Recovered"
        assert funnel_stages[4]["count"] == 1

        # ======================================================================
        # TEST 7 — Recent Activity Feed & Top Opportunities
        # ======================================================================
        act_res = await client.get("/api/v1/analytics/recent-activity?limit=10", headers=headers_a)
        assert act_res.status_code == 200
        act_list = act_res.json()["data"]
        assert len(act_list) >= 1

        opp_res = await client.get("/api/v1/analytics/top-opportunities", headers=headers_a)
        assert opp_res.status_code == 200
        opp_list = opp_res.json()["data"]
        assert len(opp_list) >= 1
        assert opp_list[0]["amount"] == 25000.0

        # ======================================================================
        # TEST 8 — Real Data Sources Status
        # ======================================================================
        ds_res = await client.get("/api/v1/analytics/data-sources", headers=headers_a)
        assert ds_res.status_code == 200
        ds_data = ds_res.json()["data"]
        assert ds_data["payment_providers"]["connected"] is True
        assert ds_data["manual_entry"]["available"] is True

        # ======================================================================
        # TEST 9 — Multi-Tenant Isolation (Org Beta)
        # ======================================================================
        signup_b = await client.post(
            "/api/v1/auth/signup",
            json={
                "full_name": "Dashboard Admin Beta",
                "email": f"dash_beta_{sfx}@beta.io",
                "password": "Password123!",
                "company_name": f"Beta Dash Corp {sfx}",
            },
        )
        assert signup_b.status_code == 201
        token_b = signup_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Beta must see ₹0 and 0 cases (no leakage from Alpha)
        summary_b = await client.get("/api/v1/analytics/summary", headers=headers_b)
        assert summary_b.status_code == 200
        b_data = summary_b.json()["data"]
        assert b_data["revenue_at_risk"] == 0.0
        assert b_data["revenue_recovered"] == 0.0
        assert b_data["total_cases"] == 0
        assert b_data["transaction_summary"]["total"] == 0

        # Beta has 0 connected payment providers
        ds_b = await client.get("/api/v1/analytics/data-sources", headers=headers_b)
        assert ds_b.status_code == 200
        assert ds_b.json()["data"]["payment_providers"]["connected"] is False
