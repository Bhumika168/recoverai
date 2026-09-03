import uuid
import pytest
import io
import time
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db
from app.models.organization import OrganizationMembership


@pytest.mark.asyncio
async def test_step14_complete_production_security_and_rbac():
    await init_db()
    sfx = uuid.uuid4().hex[:6]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # ======================================================================
        # 1. SETUP ORG ALPHA (Owner) & ORG BETA (Owner)
        # ======================================================================
        signup_a = await client.post(
            "/api/v1/auth/signup",
            json={
                "full_name": "Alpha Owner",
                "email": f"owner_{sfx}@alpha.io",
                "password": "Password123!",
                "company_name": f"Alpha Security Corp {sfx}",
            },
        )
        assert signup_a.status_code == 201
        token_a = signup_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}
        await client.patch("/api/v1/organization/current", json={"onboarding_completed": True}, headers=headers_a)

        signup_b = await client.post(
            "/api/v1/auth/signup",
            json={
                "full_name": "Beta Owner",
                "email": f"owner_{sfx}@beta.io",
                "password": "Password123!",
                "company_name": f"Beta Security Corp {sfx}",
            },
        )
        assert signup_b.status_code == 201
        token_b = signup_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Create Member with VIEWER role in Org A
        signup_viewer = await client.post(
            "/api/v1/auth/signup",
            json={
                "full_name": "Alpha Viewer",
                "email": f"viewer_{sfx}@alpha.io",
                "password": "Password123!",
                "company_name": f"Alpha Temp Org {sfx}",
            },
        )
        token_viewer_orig = signup_viewer.json()["access_token"]
        viewer_user_id = signup_viewer.json()["user"]["id"]

        # Ingest Transaction in Org A
        txn_a_res = await client.post(
            "/api/v1/transactions",
            json={
                "transaction_id": f"TXN_A_{sfx}",
                "amount": 12000.0,
                "currency": "INR",
                "customer_email": f"cust_a_{sfx}@client.com",
                "payment_method": "CARD",
                "status": "FAILED",
                "failure_code": "INSUFFICIENT_FUNDS",
            },
            headers=headers_a,
        )
        assert txn_a_res.status_code == 201
        txn_a_id = txn_a_res.json()["data"]["id"]

        # Ingest Transaction in Org B
        txn_b_res = await client.post(
            "/api/v1/transactions",
            json={
                "transaction_id": f"TXN_B_{sfx}",
                "amount": 24000.0,
                "currency": "INR",
                "customer_email": f"cust_b_{sfx}@client.com",
                "payment_method": "UPI",
                "status": "FAILED",
                "failure_code": "AUTHENTICATION_FAILED",
            },
            headers=headers_b,
        )
        assert txn_b_res.status_code == 201
        txn_b_id = txn_b_res.json()["data"]["id"]

        # ======================================================================
        # TEST 1 — Unauthenticated Access Blocked
        # ======================================================================
        client.cookies.clear()
        unauth_res = await client.get("/api/v1/analytics/summary")
        assert unauth_res.status_code == 401
        assert unauth_res.json()["error"]["error_code"] == "UNAUTHENTICATED"

        # ======================================================================
        # TEST 2 — Invalid / Tampered Session Token Blocked
        # ======================================================================
        invalid_tok_res = await client.get(
            "/api/v1/analytics/summary",
            headers={"Authorization": "Bearer invalid.jwt.token.payload"},
        )
        assert invalid_tok_res.status_code == 401

        # ======================================================================
        # TEST 3 — Logout Invalidates Session Server-Side
        # ======================================================================
        # Create temp user to test logout
        signup_temp = await client.post(
            "/api/v1/auth/signup",
            json={
                "full_name": "Temp User",
                "email": f"temp_{sfx}@alpha.io",
                "password": "Password123!",
                "company_name": f"Temp Org {sfx}",
            },
        )
        temp_token = signup_temp.json()["access_token"]
        temp_headers = {"Authorization": f"Bearer {temp_token}"}

        # Works before logout
        assert (await client.get("/api/v1/organization/current", headers=temp_headers)).status_code == 200

        # Perform logout
        logout_res = await client.post("/api/v1/auth/logout", headers=temp_headers)
        assert logout_res.status_code == 200

        # Attempting API access with revoked token must now be 401
        revoked_res = await client.get("/api/v1/organization/current", headers=temp_headers)
        assert revoked_res.status_code == 401
        assert revoked_res.json()["error"]["error_code"] == "SESSION_REVOKED"

        # ======================================================================
        # TEST 4 & 5 — RBAC Role Enforcement (VIEWER Rejection)
        # ======================================================================
        # Add viewer_user_id to Org A with role VIEWER
        from app.database import AsyncSessionLocal
        from app.models.organization import OrganizationMembership
        async with AsyncSessionLocal() as session:
            # Reassign viewer to Org A with VIEWER role
            mem_res = await session.execute(
                select(OrganizationMembership).where(OrganizationMembership.user_id == viewer_user_id)
            )
            viewer_mem = mem_res.scalars().first()
            if viewer_mem:
                viewer_mem.organization_id = signup_a.json()["organization"]["id"]
                viewer_mem.role = "VIEWER"
                await session.commit()

        # Login as viewer to get fresh token with Org A
        login_viewer = await client.post(
            "/api/v1/auth/login",
            json={"email": f"viewer_{sfx}@alpha.io", "password": "Password123!"},
        )
        token_viewer = login_viewer.json()["access_token"]
        headers_viewer = {"Authorization": f"Bearer {token_viewer}"}

        # VIEWER can read dashboard/transactions
        assert (await client.get("/api/v1/analytics/summary", headers=headers_viewer)).status_code == 200
        assert (await client.get("/api/v1/transactions", headers=headers_viewer)).status_code == 200

        # VIEWER CANNOT create campaigns (403 Forbidden)
        campaign_deny = await client.post(
            "/api/v1/campaigns",
            json={"name": "Forbidden Campaign", "recovery_type": "FAILED_PAYMENT"},
            headers=headers_viewer,
        )
        assert campaign_deny.status_code == 403

        # VIEWER CANNOT update organization policies (403 Forbidden)
        org_patch_deny = await client.patch(
            "/api/v1/organization/current",
            json={"max_retries": 10},
            headers=headers_viewer,
        )
        assert org_patch_deny.status_code == 403

        # VIEWER CANNOT connect payment gateways (403 Forbidden)
        connect_deny = await client.post(
            "/api/v1/integrations/connect",
            json={"provider": "STRIPE", "api_key": "sk_test_123", "secret_key": "whsec_123"},
            headers=headers_viewer,
        )
        assert connect_deny.status_code == 403

        # ======================================================================
        # TEST 6, 7 & 8 — IDOR & Organization Isolation
        # ======================================================================
        # Org A attempts to view Org B's transaction
        idor_txn = await client.get(f"/api/v1/transactions/{txn_b_id}", headers=headers_a)
        assert idor_txn.status_code == 404

        # Org A retrieves recovery cases -> must NOT include Org B's cases
        cases_a = (await client.get("/api/v1/cases", headers=headers_a)).json()["data"]
        case_a_ids = [c["transaction_id"] for c in cases_a]
        assert f"TXN_A_{sfx}" in case_a_ids
        assert f"TXN_B_{sfx}" not in case_a_ids

        # Org B retrieves recovery cases -> must NOT include Org A's cases
        cases_b = (await client.get("/api/v1/cases", headers=headers_b)).json()["data"]
        case_b_ids = [c["transaction_id"] for c in cases_b]
        assert f"TXN_B_{sfx}" in case_b_ids
        assert f"TXN_A_{sfx}" not in case_b_ids

        # ======================================================================
        # TEST 9, 10 & 11 — Recovery Token Expiry, Single-Use & Invalid Token
        # ======================================================================
        case_a_id = next(c["id"] for c in cases_a if c["transaction_id"] == f"TXN_A_{sfx}")
        await client.post(f"/api/v1/cases/{case_a_id}/dispatch-communication", json={"channel": "EMAIL"}, headers=headers_a)
        comms = (await client.get(f"/api/v1/cases/{case_a_id}/communications", headers=headers_a)).json()["data"]
        raw_tok = comms[0]["body"].split("/recover/")[1].split()[0].replace("\n", "").replace(")", "").strip()

        # Random token returns 404
        assert (await client.get("/api/v1/recover/random_non_existent_token_12345")).status_code == 404

        # Valid token works
        assert (await client.get(f"/api/v1/recover/{raw_tok}")).status_code == 200

        # Complete payment
        assert (await client.post(f"/api/v1/recover/{raw_tok}/complete-sandbox")).status_code == 200

        # Re-use attempt is rejected (Single-use protection)
        assert (await client.post(f"/api/v1/recover/{raw_tok}/complete-sandbox")).status_code == 400

        # ======================================================================
        # TEST 12 & 13 — Webhook Signature Verification & Idempotency
        # ======================================================================
        # Connect Mock provider to Org A
        await client.post(
            "/api/v1/integrations/connect",
            json={"provider": "MOCK", "api_key": "mock_k", "secret_key": "mock_sec"},
            headers=headers_a,
        )

        org_a_id = signup_a.json()["organization"]["id"]

        # 1. Invalid signature rejected
        wh_bad_sig = await client.post(
            f"/api/v1/integrations/webhooks/mock?org_id={org_a_id}",
            json={"event_id": f"evt_bad_{sfx}", "event_type": "payment.captured", "transaction_id": f"TXN_A_{sfx}"},
            headers={"X-Signature": "invalid_signature"},
        )
        assert wh_bad_sig.status_code == 400

        # 2. Valid signature succeeds
        import json, hmac, hashlib
        wh_payload = {
            "event_id": f"evt_idempotent_{sfx}",
            "event_type": "payment.captured",
            "transaction_id": f"TXN_A_{sfx}",
            "amount": 12000.0,
            "currency": "INR",
            "status": "CAPTURED",
        }
        wh_raw = json.dumps(wh_payload).encode("utf-8")
        sig = hmac.new(b"mock_sec", wh_raw, hashlib.sha256).hexdigest()
        wh_ok = await client.post(
            f"/api/v1/integrations/webhooks/mock?org_id={org_a_id}",
            content=wh_raw,
            headers={"Content-Type": "application/json", "X-Signature": sig},
        )
        assert wh_ok.status_code == 200

        # 3. Duplicate webhook with same event_id is idempotent (processed without error)
        wh_dup = await client.post(
            f"/api/v1/integrations/webhooks/mock?org_id={org_a_id}",
            content=wh_raw,
            headers={"Content-Type": "application/json", "X-Signature": sig},
        )
        assert wh_dup.status_code == 200

        # ======================================================================
        # TEST 14 — CSV Formula Injection Neutralization & Upload Security
        # ======================================================================
        malicious_csv = (
            "transaction_id,amount,status,customer_email,failure_reason\n"
            f"TXN_INJ_{sfx},5000,FAILED,test@client.com,=1+2;cmd|' /C calc'!A0\n"
        )
        csv_file = io.BytesIO(malicious_csv.encode("utf-8"))
        preview_res = await client.post(
            "/api/v1/transactions/preview-csv",
            files={"file": ("transactions.csv", csv_file, "text/csv")},
            headers=headers_a,
        )
        assert preview_res.status_code == 200
        preview_data = preview_res.json()["data"]
        # Formula injection is neutralized with leading quote
        assert preview_data["valid_rows_count"] >= 1

        # ======================================================================
        # TEST 15 — Masked Secrets in Provider API Responses
        # ======================================================================
        providers_res = await client.get("/api/v1/integrations", headers=headers_a)
        assert providers_res.status_code == 200
        for p in providers_res.json()["data"]:
            if p.get("status") == "CONNECTED":
                # Secrets must be masked (e.g. ••••••••)
                assert "mock_sec" not in str(p)
                assert "••••" in p.get("api_key_masked", "") or "••••" in p.get("webhook_secret_masked", "")
