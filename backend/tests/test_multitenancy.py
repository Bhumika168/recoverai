import io
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db


@pytest.mark.asyncio
async def test_multi_tenant_isolation_and_onboarding_flow():
    await init_db()
    sfx = uuid.uuid4().hex[:6]
    email_a = f"alice_{sfx}@company-a.com"
    email_b = f"bob_{sfx}@company-b.com"
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register Org A (Owner role, onboarding_completed: false)
        signup_a = await client.post(
            "/api/v1/auth/signup",
            json={
                "full_name": "Alice Smith",
                "email": email_a,
                "password": "PasswordA123!",
                "company_name": f"Company Alpha {sfx}",
            },
        )
        assert signup_a.status_code == 201
        data_a = signup_a.json()
        token_a = data_a["access_token"]
        org_a_id = data_a["organization"]["id"]
        assert data_a["organization"]["onboarding_completed"] is False
        assert data_a["organization"]["role"] == "OWNER"

        # 2. Register Org B (Owner role, onboarding_completed: false)
        signup_b = await client.post(
            "/api/v1/auth/signup",
            json={
                "full_name": "Bob Jones",
                "email": email_b,
                "password": "PasswordB123!",
                "company_name": f"Company Beta {sfx}",
            },
        )
        assert signup_b.status_code == 201
        data_b = signup_b.json()
        token_b = data_b["access_token"]
        org_b_id = data_b["organization"]["id"]
        assert org_a_id != org_b_id

        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # 3. Check Initial Empty State for Org A
        summary_a_init = await client.get("/api/v1/analytics/summary", headers=headers_a)
        assert summary_a_init.status_code == 200
        stats_a = summary_a_init.json()["data"]
        assert stats_a["total_cases"] == 0
        assert stats_a["revenue_at_risk"] == 0.0
        assert stats_a["revenue_recovered"] == 0.0
        assert stats_a["active_recovery_cases"] == 0
        assert stats_a["recovery_rate_percentage"] == 0.0

        # 4. Org A completes 3-Step Onboarding with Guardrails
        onboard_a = await client.patch(
            "/api/v1/organization/current",
            json={
                "industry": "Fintech & Banking",
                "company_size": "51-200 employees",
                "country": "India",
                "currency": "INR",
                "onboarding_completed": True,
                "max_retries": 4,
                "high_value_threshold": 30000.0,
                "require_human_approval": True,
                "hard_decline_behavior": "SUPPRESS",
                "auto_escalate_rules": "AFTER_MAX_RETRIES",
            },
            headers=headers_a,
        )
        assert onboard_a.status_code == 200
        org_a_updated = onboard_a.json()
        assert org_a_updated["industry"] == "Fintech & Banking"
        assert org_a_updated["onboarding_completed"] is True
        assert org_a_updated["max_retries"] == 4
        assert org_a_updated["high_value_threshold"] == 30000.0

        # 5. Org A creates a manual failed transaction
        txn_create_a = await client.post(
            "/api/v1/transactions",
            json={
                "transaction_id": f"txn_manual_a_{sfx}",
                "customer_email": f"cust1_{sfx}@client-a.com",
                "customer_name": "Client A Customer",
                "amount": 12500.0,
                "currency": "INR",
                "status": "FAILED",
                "payment_method": "CARD",
                "failure_reason": "Bank timeout during auth",
            },
            headers=headers_a,
        )
        assert txn_create_a.status_code == 201
        txn_a = txn_create_a.json()["data"]
        txn_a_id = txn_a["id"]

        # Duplicate manual transaction ID is rejected
        dup_create_a = await client.post(
            "/api/v1/transactions",
            json={
                "transaction_id": f"txn_manual_a_{sfx}",
                "customer_email": f"cust1_{sfx}@client-a.com",
                "amount": 5000.0,
                "currency": "INR",
                "status": "FAILED",
            },
            headers=headers_a,
        )
        assert dup_create_a.status_code == 409

        # 6. Org A summary updates dynamically
        summary_a_after = await client.get("/api/v1/analytics/summary", headers=headers_a)
        stats_a_after = summary_a_after.json()["data"]
        assert stats_a_after["total_cases"] == 1
        assert stats_a_after["revenue_at_risk"] == 12500.0
        assert stats_a_after["active_recovery_cases"] == 1

        # 7. Verify ISOLATION: Org B sees ZERO transactions and ZERO cases
        txns_b = await client.get("/api/v1/transactions", headers=headers_b)
        assert txns_b.status_code == 200
        assert len(txns_b.json()["data"]) == 0

        cases_b = await client.get("/api/v1/cases", headers=headers_b)
        assert cases_b.status_code == 200
        assert len(cases_b.json()["data"]) == 0

        summary_b = await client.get("/api/v1/analytics/summary", headers=headers_b)
        assert summary_b.status_code == 200
        assert summary_b.json()["data"]["total_cases"] == 0
        assert summary_b.json()["data"]["revenue_at_risk"] == 0.0

        # 8. Verify Org B cannot access Org A's transaction directly
        get_a_by_b = await client.get(f"/api/v1/transactions/{txn_a_id}", headers=headers_b)
        assert get_a_by_b.status_code == 404

        # 9. Test CSV Preview with duplicate and invalid validation
        csv_content = (
            "transaction_id,amount,status,timestamp,customer_email,failure_reason,payment_method\n"
            f"txn_csv_b_{sfx}_01,7500.00,FAILED,2026-08-25T10:00:00Z,vip_{sfx}@company-b.com,Insufficient balance,UPI\n"
            f"txn_csv_b_{sfx}_02,4200.00,CAPTURED,2026-08-25T11:00:00Z,user2_{sfx}@company-b.com,,CARD\n"
            f"txn_csv_b_{sfx}_01,999.00,FAILED,2026-08-25T12:00:00Z,dup_{sfx}@company-b.com,Duplicate ID in CSV,CARD\n"
            f"txn_invalid,invalid_amount,FAILED,2026-08-25T13:00:00Z,bad_{sfx}@company-b.com,Invalid amount,CARD\n"
        )
        files = {"file": ("test_data.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
        preview_res = await client.post("/api/v1/transactions/preview-csv", files=files, headers=headers_b)
        assert preview_res.status_code == 200
        preview_data = preview_res.json()["data"]
        assert preview_data["rows_detected"] == 4
        assert preview_data["valid_rows_count"] == 2
        assert preview_data["invalid_rows_count"] == 1
        assert preview_data["duplicate_rows_count"] == 1

        # 10. Org B commits valid rows from CSV Import
        csv_import_res = await client.post(
            "/api/v1/transactions/import-csv",
            json={
                "rows": preview_data["sample_rows"]
            },
            headers=headers_b,
        )
        assert csv_import_res.status_code == 200
        import_summary = csv_import_res.json()["data"]
        assert import_summary["imported_count"] == 2
        assert import_summary["failed_recoveries_triggered"] == 1

        # 11. Org B now sees ONLY its own imported transactions
        txns_b_after = await client.get("/api/v1/transactions", headers=headers_b)
        assert txns_b_after.status_code == 200
        assert len(txns_b_after.json()["data"]) == 2

        summary_b_after = await client.get("/api/v1/analytics/summary", headers=headers_b)
        assert summary_b_after.json()["data"]["total_cases"] == 1
        assert summary_b_after.json()["data"]["revenue_at_risk"] == 7500.0

        # 12. Check Audit Ledger Scoping
        audit_a = await client.get("/api/v1/audit/logs", headers=headers_a)
        assert audit_a.status_code == 200
        audit_a_logs = audit_a.json()["data"]
        assert any(l["event_type"] == "TRANSACTION_MANUALLY_CREATED" for l in audit_a_logs)

        audit_b = await client.get("/api/v1/audit/logs", headers=headers_b)
        assert audit_b.status_code == 200
        audit_b_logs = audit_b.json()["data"]
        assert any(l["event_type"] == "CSV_TRANSACTIONS_IMPORTED" for l in audit_b_logs)
        assert not any(l["entity_id"] == txn_a_id for l in audit_b_logs)
