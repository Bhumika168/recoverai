import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db


@pytest.mark.asyncio
async def test_crud_and_case_lifecycle():
    await init_db()
    unique_suffix = uuid.uuid4().hex[:6]
    test_email = f"merchant_{unique_suffix}@acmecorp.com"
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Sign up user to obtain authenticated session
        signup_res = await ac.post(
            "/api/v1/auth/signup",
            json={
                "full_name": "Acme Admin",
                "email": test_email,
                "password": "Password123!",
                "company_name": f"Acme Corp {unique_suffix}",
            },
        )
        assert signup_res.status_code == 201
        auth_data = signup_res.json()
        token = auth_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create a customer
        cust_payload = {
            "email": f"cust_{unique_suffix}@client.com",
            "name": f"Acme Client {unique_suffix}",
            "phone": "+919876543210",
            "risk_score": 0.1,
            "recovery_receptivity_score": 0.9,
        }
        res = await ac.post("/api/v1/customers", json=cust_payload)
        assert res.status_code == 201
        cust_data = res.json()
        assert cust_data["success"] is True
        customer_id = cust_data["data"]["id"]
        assert customer_id.startswith("cust_")

        # 2. Create manual failed transaction
        fail_payload = {
            "customer_email": f"cust_{unique_suffix}@client.com",
            "customer_name": f"Acme Client {unique_suffix}",
            "amount": 14999.0,
            "currency": "INR",
            "payment_method": "CARD",
            "failure_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
            "failure_reason": "Bank authorization server did not respond in 30 seconds",
        }
        res = await ac.post("/api/v1/transactions", json=fail_payload, headers=headers)
        assert res.status_code == 201
        txn_data = res.json()
        assert txn_data["success"] is True
        txn_id = txn_data["data"]["id"]
        assert txn_id.startswith("txn_")
        assert txn_data["data"]["status"] == "FAILED"

        # 3. Verify recovery case was automatically opened
        res = await ac.get("/api/v1/cases", headers=headers)
        assert res.status_code == 200
        cases_data = res.json()
        assert len(cases_data["data"]) >= 1
        matched_cases = [c for c in cases_data["data"] if c["transaction_id"] == txn_id]
        assert len(matched_cases) == 1
        case = matched_cases[0]
        assert case["amount_at_risk"] == 14999.0
        case_id = case["id"]

        # 4. Fetch case details with relationships
        res = await ac.get(f"/api/v1/cases/{case_id}", headers=headers)
        assert res.status_code == 200
        case_detail = res.json()["data"]
        assert case_detail["transaction"]["id"] == txn_id

        # 5. Verify audit logs and cryptographic chain integrity
        res = await ac.get("/api/v1/audit/logs", headers=headers)
        assert res.status_code == 200
        logs = res.json()["data"]
        assert len(logs) >= 1

        # 6. Verify audit chain cryptographic proof
        res = await ac.get("/api/v1/audit/verify-chain", headers=headers)
        assert res.status_code == 200
        verification = res.json()["data"]
        assert verification["is_valid"] is True
        assert verification["total_entries_verified"] >= 1
        assert len(verification["invalid_entry_ids"]) == 0
