import uuid
import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db
from app.models.recovery_token import RecoveryToken, TokenStatus
from app.models.recovery_case import RecoveryCase, CaseStatus
from app.api.v1.customer_recovery import create_recovery_token_for_case


@pytest.mark.asyncio
async def test_step13_complete_customer_recovery_experience():
    await init_db()
    sfx = uuid.uuid4().hex[:6]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # ======================================================================
        # 1. SETUP ORG ALPHA & FAILED TRANSACTION
        # ======================================================================
        signup_a = await client.post(
            "/api/v1/auth/signup",
            json={
                "full_name": "Merchant Owner",
                "email": f"merchant_{sfx}@alpha.io",
                "password": "Password123!",
                "company_name": f"Acme Global {sfx}",
            },
        )
        assert signup_a.status_code == 201
        token_a = signup_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}
        await client.patch("/api/v1/organization/current", json={"onboarding_completed": True}, headers=headers_a)

        # Ingest failed transaction (₹8,500)
        txn_res = await client.post(
            "/api/v1/transactions",
            json={
                "transaction_id": f"TXN_CUST_REC_{sfx}",
                "amount": 8500.0,
                "currency": "INR",
                "customer_email": f"sarah_{sfx}@client.com",
                "customer_name": "Sarah Jenkins",
                "payment_method": "CARD",
                "status": "FAILED",
                "failure_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
                "failure_reason": "Cardholder timeout during 3DS",
            },
            headers=headers_a,
        )
        assert txn_res.status_code == 201
        txn_id = txn_res.json()["data"]["id"]

        # Retrieve spawned RecoveryCase
        cases_res = await client.get("/api/v1/cases", headers=headers_a)
        case = next(c for c in cases_res.json()["data"] if c["transaction_id"] == txn_id)
        case_id = case["id"]

        # ======================================================================
        # TEST 1 — Generate Secure Single-Use Recovery Token via Campaign Outreach
        # ======================================================================
        com_dispatch = await client.post(
            f"/api/v1/cases/{case_id}/dispatch-communication",
            json={"channel": "EMAIL"},
            headers=headers_a,
        )
        assert com_dispatch.status_code == 200

        # Retrieve communications to get link
        comms_res = await client.get(f"/api/v1/cases/{case_id}/communications", headers=headers_a)
        assert comms_res.status_code == 200
        rendered_body = comms_res.json()["data"][0]["body"]
        assert "/recover/" in rendered_body

        # Extract raw token
        raw_token = rendered_body.split("/recover/")[1].split()[0].replace("\n", "").replace(")", "").strip()

        # ======================================================================
        # TEST 2 — Public Recovery Link Resolution & Data Minimization
        # ======================================================================
        # Customer opens recovery link (Unauthenticated, public)
        rec_data_res = await client.get(f"/api/v1/recover/{raw_token}")
        assert rec_data_res.status_code == 200
        rec_data = rec_data_res.json()["data"]
        
        # Verify minimized payload
        assert rec_data["status"] == "ACTIVE"
        assert rec_data["merchant_name"] == f"Acme Global {sfx}"
        assert rec_data["amount"] == 8500.0
        assert rec_data["currency"] == "INR"
        assert rec_data["customer_first_name"] == "Sarah"
        assert rec_data["is_test_mode"] is True
        
        # Verify ZERO internal IDs or AI prompts are exposed
        assert "organization_id" not in rec_data
        assert "transaction_id" not in rec_data
        assert "recovery_case_id" not in rec_data
        assert "ai_prompt" not in rec_data

        # ======================================================================
        # TEST 3 — Invalid / Random Token Rejection (404)
        # ======================================================================
        invalid_res = await client.get("/api/v1/recover/random_non_existent_fake_token_12345")
        assert invalid_res.status_code == 404

        # ======================================================================
        # TEST 4 — Initiate Customer Payment Flow (CUSTOMER_PAYMENT_STARTED audit)
        # ======================================================================
        initiate_res = await client.post(f"/api/v1/recover/{raw_token}/initiate-payment")
        assert initiate_res.status_code == 200
        assert initiate_res.json()["data"]["flow"] == "SANDBOX_FLOW"

        # ======================================================================
        # TEST 5 — Complete Verified Sandbox Payment
        # ======================================================================
        complete_res = await client.post(f"/api/v1/recover/{raw_token}/complete-sandbox")
        assert complete_res.status_code == 200
        assert complete_res.json()["data"]["status"] == "RECOVERED"
        assert complete_res.json()["data"]["amount"] == 8500.0

        # ======================================================================
        # TEST 6 — Single-Use Protection (Cannot reuse token)
        # ======================================================================
        # Attempting second payment with same token is rejected
        reuse_pay_res = await client.post(f"/api/v1/recover/{raw_token}/complete-sandbox")
        assert reuse_pay_res.status_code == 400

        # Opening used token shows status USED
        opened_again_res = await client.get(f"/api/v1/recover/{raw_token}")
        assert opened_again_res.status_code == 200
        assert opened_again_res.json()["data"]["status"] == "USED"

        # ======================================================================
        # TEST 7 — Merchant Dashboard & Case State Updated Dynamically
        # ======================================================================
        # Check merchant summary
        summary_res = await client.get("/api/v1/analytics/summary", headers=headers_a)
        assert summary_res.status_code == 200
        summary_data = summary_res.json()["data"]
        assert summary_data["revenue_recovered"] == 8500.0
        assert summary_data["recovered_cases"] == 1

        # Check case timeline has chronological audit records
        timeline_res = await client.get(f"/api/v1/cases/{case_id}/timeline", headers=headers_a)
        assert timeline_res.status_code == 200
        events = [e["event_type"] for e in timeline_res.json()["data"]]
        assert "RECOVERY_TOKEN_CREATED" in events
        assert "RECOVERY_LINK_OPENED" in events
        assert "CUSTOMER_PAYMENT_STARTED" in events
        assert "RECOVERY_VERIFIED" in events

        # ======================================================================
        # TEST 8 — Customer Opt-Out from Recovery Link
        # ======================================================================
        # Create second failed transaction & token for opt-out test
        await client.post(
            "/api/v1/transactions",
            json={
                "transaction_id": f"TXN_OPT_REC_{sfx}",
                "amount": 3500.0,
                "currency": "INR",
                "customer_email": f"optout_cust_{sfx}@client.com",
                "customer_name": "David Miller",
                "payment_method": "UPI",
                "status": "FAILED",
                "failure_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
                "failure_reason": "Timeout",
            },
            headers=headers_a,
        )
        case_opt_id = next(c["id"] for c in (await client.get("/api/v1/cases", headers=headers_a)).json()["data"] if c["transaction_id"] == f"TXN_OPT_REC_{sfx}")
        await client.post(f"/api/v1/cases/{case_opt_id}/dispatch-communication", json={"channel": "EMAIL"}, headers=headers_a)
        comms_opt = (await client.get(f"/api/v1/cases/{case_opt_id}/communications", headers=headers_a)).json()["data"]
        raw_token_opt = comms_opt[0]["body"].split("/recover/")[1].split()[0].replace("\n", "").replace(")", "").strip()

        # Customer opts out via link footer
        opt_res = await client.post(f"/api/v1/recover/{raw_token_opt}/opt-out")
        assert opt_res.status_code == 200
        assert opt_res.json()["data"]["status"] == "OPTED_OUT"

        # Subsequent opening shows revoked/cancelled
        check_opt = await client.get(f"/api/v1/recover/{raw_token_opt}")
        assert check_opt.json()["data"]["status"] == "REVOKED"
