import io
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db


@pytest.mark.asyncio
async def test_csv_upload_preview_mapping_and_import():
    await init_db()
    sfx = uuid.uuid4().hex[:6]
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Signup & complete onboarding for Alpha
        signup_res = await client.post(
            "/api/v1/auth/signup",
            json={
                "full_name": "Alpha Lead",
                "email": f"alpha_lead_{sfx}@alpha.io",
                "password": "AlphaPassword123!",
                "company_name": "Alpha Retail Corp",
            },
        )
        assert signup_res.status_code == 201
        token = signup_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        await client.patch(
            "/api/v1/organization/current",
            json={"onboarding_completed": True},
            headers=headers,
        )

        # 2. Upload CSV with 5 transactions (3 failed, 1 captured, 1 abandoned)
        csv_content = (
            "TxnID,CustomerEmail,Amount,Status,FailureReason,Date,PaymentMethod\n"
            f"TXN_{sfx}_01,user1_{sfx}@test.com,12500.00,FAILED,Bank authorization timeout,2026-08-20T10:00:00Z,CARD\n"
            f"TXN_{sfx}_02,user2_{sfx}@test.com,4500.00,CAPTURED,,2026-08-20T11:00:00Z,UPI\n"
            f"TXN_{sfx}_03,user3_{sfx}@test.com,8200.00,FAILED,Insufficient account funds,2026-08-20T12:00:00Z,CARD\n"
            f"TXN_{sfx}_04,user4_{sfx}@test.com,15000.00,ABANDONED,User exited checkout,2026-08-20T13:00:00Z,NETBANKING\n"
            f"TXN_{sfx}_05,user5_{sfx}@test.com,3000.00,FAILED,Card expired,2026-08-20T14:00:00Z,CARD\n"
        ).encode("utf-8")

        files = {"file": ("test_transactions.csv", csv_content, "text/csv")}
        preview_res = await client.post(
            "/api/v1/transactions/preview-csv",
            files=files,
            headers=headers,
        )
        assert preview_res.status_code == 200
        preview_data = preview_res.json()["data"]
        assert preview_data["rows_detected"] == 5
        assert len(preview_data["headers_detected"]) >= 7
        assert len(preview_data["preview_rows"]) == 5
        assert preview_data["valid_rows_count"] == 5

        # 3. Import the 5 mapped transactions
        import_rows = [
            {
                "transaction_id": f"TXN_{sfx}_01",
                "customer_email": f"user1_{sfx}@test.com",
                "amount": 12500.00,
                "currency": "INR",
                "status": "FAILED",
                "failure_reason": "Bank authorization timeout",
                "payment_method": "CARD",
                "timestamp": "2026-08-20T10:00:00Z",
            },
            {
                "transaction_id": f"TXN_{sfx}_02",
                "customer_email": f"user2_{sfx}@test.com",
                "amount": 4500.00,
                "currency": "INR",
                "status": "CAPTURED",
                "payment_method": "UPI",
                "timestamp": "2026-08-20T11:00:00Z",
            },
            {
                "transaction_id": f"TXN_{sfx}_03",
                "customer_email": f"user3_{sfx}@test.com",
                "amount": 8200.00,
                "currency": "INR",
                "status": "FAILED",
                "failure_reason": "Insufficient account funds",
                "payment_method": "CARD",
                "timestamp": "2026-08-20T12:00:00Z",
            },
            {
                "transaction_id": f"TXN_{sfx}_04",
                "customer_email": f"user4_{sfx}@test.com",
                "amount": 15000.00,
                "currency": "INR",
                "status": "ABANDONED",
                "failure_reason": "User exited checkout",
                "payment_method": "NETBANKING",
                "timestamp": "2026-08-20T13:00:00Z",
            },
            {
                "transaction_id": f"TXN_{sfx}_05",
                "customer_email": f"user5_{sfx}@test.com",
                "amount": 3000.00,
                "currency": "INR",
                "status": "FAILED",
                "failure_reason": "Card expired",
                "payment_method": "CARD",
                "timestamp": "2026-08-20T14:00:00Z",
            },
        ]

        import_res = await client.post(
            "/api/v1/transactions/import-csv",
            json={"rows": import_rows},
            headers=headers,
        )
        assert import_res.status_code == 200
        summary = import_res.json()["data"]
        assert summary["imported_count"] == 5
        assert summary["failed_recoveries_triggered"] == 4  # 3 failed + 1 abandoned

        # 4. Verify Dashboard Metrics reflect exact imported data (12500 + 8200 + 15000 + 3000 = 38700)
        dash_res = await client.get("/api/v1/analytics/summary", headers=headers)
        assert dash_res.status_code == 200
        dash_data = dash_res.json()["data"]
        assert dash_data["revenue_at_risk"] == 38700.0
        assert dash_data["active_recovery_cases"] == 4
        assert dash_data["total_cases"] == 4

        # 5. Verify Transactions List
        txns_res = await client.get("/api/v1/transactions", headers=headers)
        assert txns_res.status_code == 200
        txns = txns_res.json()["data"]
        assert len(txns) == 5

        # 6. Verify Recovery Queue Cases
        cases_res = await client.get("/api/v1/cases", headers=headers)
        assert cases_res.status_code == 200
        cases = cases_res.json()["data"]
        assert len(cases) == 4
        for c in cases:
            assert c["amount_at_risk"] in [12500.0, 8200.0, 15000.0, 3000.0]
            assert c["status"] in ["DETECTED", "DIAGNOSED", "POLICY_CHECK", "ACTION_READY", "AWAITING_APPROVAL", "IN_PROGRESS", "OPEN"]

        # 7. Verify SHA-256 Audit Trail Integrity
        audit_res = await client.get("/api/v1/audit/logs", headers=headers)
        assert audit_res.status_code == 200
        logs = audit_res.json()["data"]
        assert len(logs) >= 5

        verify_res = await client.get("/api/v1/audit/verify", headers=headers)
        assert verify_res.status_code == 200
        assert verify_res.json()["data"]["is_valid"] is True
