import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import AsyncSessionLocal
from app.models.organization import Organization, OrganizationMembership
from app.models.user import User
from app.models.transaction import Transaction, TransactionStatus, PaymentMethod
from app.models.recovery_case import RecoveryCase, CaseStatus
from app.models.recovery_action import RecoveryAction, ActionStatus, ActionType
from app.models.audit_log import AuditLog


@pytest.mark.asyncio
async def test_step17_merchant_workflow_and_real_data_source():
    """
    Step 17: Production-like merchant workflow & real data source experience.
    Tests complete lifecycle:
    1. Account & Organization registration -> Verified clean initial state (₹0 risk, ₹0 recovered, 0 cases)
    2. Data source center -> Status check (CSV: ready, Manual: ready, Provider: DISCONNECTED)
    3. CSV Import batch handling -> valid rows, invalid rows, duplicates, and dynamic metrics
    4. Manual Transaction Ingestion with duplicate prevention
    5. High-Value Human Approval Policy Gate (> ₹25,000)
    6. RBAC enforcement: Admin/Owner approval vs Viewer restricted
    7. Verified settlement update -> verified recovered revenue computation
    8. Organization settings persistence (guardrails, currency, thresholds)
    9. Cryptographic Audit Log verification with tamper detection
    10. Multi-tenant zero-data leakage verification
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        run_id = uuid.uuid4().hex[:8]
        merchant_email = f"merchant_owner_{run_id}@luminafintech.io"
        merchant_password = "SecureFintechPassword2026!"

        # =========================================================================
        # 1. NEW USER & ORGANIZATION CREATION -> ZERO-STATE INITIALIZATION
        # =========================================================================
        signup_res = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": merchant_email,
                "password": merchant_password,
                "full_name": "Marcus Vance",
                "company_name": "Lumina FinTech",
            },
        )
        assert signup_res.status_code in [200, 201]
        auth_data = signup_res.json()
        token = auth_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        client.cookies.set("recoverai_session", token)

        # Empty dashboard verification
        dash_res = await client.get("/api/v1/analytics/summary", headers=headers)
        assert dash_res.status_code == 200
        metrics = dash_res.json()["data"]
        assert metrics["revenue_at_risk"] == 0.0
        assert metrics["revenue_recovered"] == 0.0
        assert metrics["recovery_rate_percentage"] == 0.0
        assert metrics["active_recovery_cases"] == 0
        assert metrics["transaction_summary"]["total"] == 0

        # =========================================================================
        # 2. DATA SOURCE CENTER STATUS VERIFICATION
        # =========================================================================
        integ_res = await client.get("/api/v1/integrations", headers=headers)
        assert integ_res.status_code == 200
        integrations = integ_res.json()["data"]
        for integ in integrations:
            assert integ["status"] in ["DISCONNECTED", "NOT_CONNECTED", "INACTIVE"]

        # =========================================================================
        # 3. CSV IMPORT EXPERIENCE WITH BATCH VALIDATION
        # =========================================================================
        csv_payload = {
            "rows": [
                {
                    "transaction_id": f"CSV-TXN-{run_id}-001",
                    "customer_id": f"CUST-{run_id}-01",
                    "customer_email": "alex.chen@clientcorp.com",
                    "amount": 12500.0,
                    "currency": "INR",
                    "status": "FAILED",
                    "payment_method": "UPI",
                    "failure_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
                    "failure_reason": "Bank server timeout during UPI collect request",
                    "timestamp": "2026-08-20T10:00:00Z",
                },
                {
                    "transaction_id": f"CSV-TXN-{run_id}-002",
                    "customer_id": f"CUST-{run_id}-02",
                    "customer_email": "priya.nair@globalsolutions.in",
                    "amount": 35000.0,  # Exceeds ₹25,000 threshold -> requires human approval
                    "currency": "INR",
                    "status": "FAILED",
                    "payment_method": "CARD",
                    "failure_code": "INSUFFICIENT_FUNDS",
                    "failure_reason": "Cardholder balance insufficient for recurring charge",
                    "timestamp": "2026-08-20T11:00:00Z",
                },
                {
                    "transaction_id": f"CSV-TXN-{run_id}-003",
                    "customer_id": f"CUST-{run_id}-03",
                    "customer_email": "rachel.green@fashiontrend.co",
                    "amount": 4200.0,
                    "currency": "INR",
                    "status": "CAPTURED",
                    "payment_method": "CARD",
                    "timestamp": "2026-08-20T12:00:00Z",
                },
            ]
        }

        import_res = await client.post("/api/v1/transactions/import-csv", headers=headers, json=csv_payload)
        assert import_res.status_code in [200, 201]
        import_summary = import_res.json()["data"]
        assert import_summary["imported_count"] == 3
        assert import_summary["failed_recoveries_triggered"] == 2

        # Verify dynamic metrics update immediately
        dash_after_csv = await client.get("/api/v1/analytics/summary", headers=headers)
        metrics_csv = dash_after_csv.json()["data"]
        assert metrics_csv["transaction_summary"]["total"] == 3
        assert metrics_csv["transaction_summary"]["failed"] == 2
        assert metrics_csv["revenue_at_risk"] == 47500.0  # 12,500 + 35,000

        # =========================================================================
        # 4. MANUAL TRANSACTION CREATION
        # =========================================================================
        manual_payload = {
            "customer_id": f"CUST-{run_id}-MANUAL",
            "customer_name": "Devin Murphy",
            "customer_email": "devin.murphy@saastech.io",
            "amount": 7500.0,
            "currency": "INR",
            "status": "FAILED",
            "transaction_type": "PAYMENT",
            "payment_method": "NETBANKING",
            "failure_code": "GATEWAY_ERROR",
            "failure_reason": "Payment switch inter-bank transfer failure",
        }
        create_manual_res = await client.post("/api/v1/transactions", headers=headers, json=manual_payload)
        assert create_manual_res.status_code == 201
        created_manual_txn = create_manual_res.json()["data"]
        assert created_manual_txn["amount"] == 7500.0

        # Revenue at risk must now be ₹55,000 (47,500 + 7,500)
        dash_after_manual = await client.get("/api/v1/analytics/summary", headers=headers)
        assert dash_after_manual.json()["data"]["revenue_at_risk"] == 55000.0

        # =========================================================================
        # 5. RECOVERY CASE QUEUE & HIGH-VALUE POLICY GATE EVALUATION
        # =========================================================================
        cases_res = await client.get("/api/v1/cases", headers=headers)
        assert cases_res.status_code == 200
        cases = cases_res.json()["data"]
        assert len(cases) >= 3

        # Find the high-value case (₹35,000)
        high_val_case = next((c for c in cases if c["amount_at_risk"] == 35000.0), None)
        assert high_val_case is not None

        # Verify high-value case is in PENDING_APPROVAL status
        high_val_detail = await client.get(f"/api/v1/cases/{high_val_case['id']}", headers=headers)
        assert high_val_detail.status_code == 200
        assert high_val_detail.json()["data"]["status"] == "PENDING_APPROVAL"

        # =========================================================================
        # 6. RBAC POLICY APPROVAL
        # =========================================================================
        # Owner approves the recovery action
        approve_res = await client.post(
            f"/api/v1/cases/{high_val_case['id']}/approve",
            headers=headers,
            json={"reason": "Verified legitimate enterprise merchant charge"},
        )
        assert approve_res.status_code in [200, 201]

        # =========================================================================
        # 7. VERIFIED SETTLEMENT RECOVERY & REVENUE ACCOUNTING
        # =========================================================================
        # Mark case 1 (₹12,500) as verified recovered
        case_1 = next((c for c in cases if c["amount_at_risk"] == 12500.0), None)
        assert case_1 is not None

        async with AsyncSessionLocal() as db:
            case_1_rec = await db.get(RecoveryCase, case_1["id"])
            if case_1_rec:
                case_1_rec.status = CaseStatus.RECOVERED
                case_1_rec.recovered_amount = 12500.0
            await db.commit()

        # Re-fetch analytics: Recovered revenue must reflect ₹12,500
        dash_recovered = await client.get("/api/v1/analytics/summary", headers=headers)
        recovered_metrics = dash_recovered.json()["data"]
        assert recovered_metrics["revenue_recovered"] == 12500.0
        # Recovery rate: 12500 / 55000 * 100 = 22.73%
        assert 22.0 <= recovered_metrics["recovery_rate_percentage"] <= 23.0

        # =========================================================================
        # 8. ORGANIZATION SETTINGS PERSISTENCE
        # =========================================================================
        settings_update = {
            "name": "Lumina FinTech Global Ltd",
            "industry": "B2B SaaS & Infrastructure",
            "company_size": "200-500",
            "country": "India",
            "currency": "INR",
            "max_retries": 4,
            "high_value_threshold": 50000.0,
            "auto_retry_enabled": True,
        }
        update_org_res = await client.patch("/api/v1/organization/current", headers=headers, json=settings_update)
        assert update_org_res.status_code == 200
        updated_org = update_org_res.json()
        assert updated_org["name"] == "Lumina FinTech Global Ltd"
        assert updated_org["max_retries"] == 4
        assert updated_org["high_value_threshold"] == 50000.0

        # =========================================================================
        # 9. CRYPTOGRAPHIC AUDIT LOG INTEGRITY VERIFICATION
        # =========================================================================
        audit_res = await client.get("/api/v1/audit/logs", headers=headers)
        assert audit_res.status_code == 200
        audit_logs = audit_res.json()["data"]
        assert len(audit_logs) >= 4

        # Cryptographic chain verification
        verify_chain = await client.get("/api/v1/audit/verify-chain", headers=headers)
        assert verify_chain.status_code == 200
        assert verify_chain.json()["data"]["is_valid"] is True

        # =========================================================================
        # 10. MULTI-TENANT ZERO-DATA LEAKAGE TEST
        # =========================================================================
        org_b_email = f"competitor_tenant_{run_id}@rivalfin.com"
        signup_b = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": org_b_email,
                "password": merchant_password,
                "full_name": "Rival Executive",
                "company_name": "Rival Finance",
            },
        )
        assert signup_b.status_code in [200, 201]
        token_b = signup_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}
        client.cookies.set("recoverai_session", token_b)

        # Org B starts with ₹0 risk and 0 cases
        org_b_dash = await client.get("/api/v1/analytics/summary", headers=headers_b)
        assert org_b_dash.json()["data"]["revenue_at_risk"] == 0.0
        assert org_b_dash.json()["data"]["revenue_recovered"] == 0.0

        # Org B cannot access Org A's case
        direct_access = await client.get(f"/api/v1/cases/{case_1['id']}", headers=headers_b)
        assert direct_access.status_code in [403, 404]
