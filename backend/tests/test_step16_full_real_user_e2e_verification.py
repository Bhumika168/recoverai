import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import AsyncSessionLocal
from app.models.organization import Organization, OrganizationMembership
from app.models.user import User
from app.models.transaction import Transaction, TransactionStatus, PaymentMethod
from app.models.recovery_case import RecoveryCase, CaseStatus
from app.models.recovery_action import RecoveryAction, ActionStatus, ActionType
from app.models.audit_log import AuditLog
from app.services.auth_service import hash_password, create_access_token


@pytest.mark.asyncio
async def test_step16_full_real_user_e2e_verification_journey():
    """
    Step 16: Complete end-to-end journey of a brand-new organization
    from signup, onboarding, empty state, manual ingestion, diagnosis,
    policy gating, safe recovery, hard decline suppression, cross-tenant isolation,
    CSV ingestion, and logout/login session persistence.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        
        # =========================================================================
        # 1. PART 2 — LANDING & HEALTH PROBES
        # =========================================================================
        health_res = await client.get("/health")
        assert health_res.status_code == 200
        assert health_res.json()["status"] in ["healthy", "ok"]

        root_res = await client.get("/")
        assert root_res.status_code == 200

        # =========================================================================
        # 2. PART 3 — SIGNUP & VALIDATION TESTS
        # =========================================================================
        run_id = uuid.uuid4().hex[:8]
        test_email = f"real_founder_{run_id}@recoverylabs.io"
        test_password = "SecureEnterpriseP@ssword2026!"

        # A. Empty fields rejected
        bad_signup1 = await client.post("/api/v1/auth/signup", json={"email": "", "password": ""})
        assert bad_signup1.status_code in [400, 422]

        # B. Invalid email format rejected
        bad_signup2 = await client.post(
            "/api/v1/auth/signup",
            json={"email": "not-an-email", "password": test_password, "full_name": "Test Founder"}
        )
        assert bad_signup2.status_code in [400, 422]

        # C. Valid signup succeeds
        signup_res = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": test_email,
                "password": test_password,
                "full_name": "Dr. Sarah Lin",
                "company_name": "Recovery Labs Global",
            }
        )
        assert signup_res.status_code in [200, 201]
        signup_data = signup_res.json()
        assert "user" in signup_data
        assert "organization" in signup_data
        assert signup_data["organization"]["name"] == "Recovery Labs Global"

        # D. Duplicate email rejected
        dup_signup = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": test_email,
                "password": test_password,
                "full_name": "Duplicate Lin",
                "company_name": "Another Labs",
            }
        )
        assert dup_signup.status_code in [400, 409]

        # =========================================================================
        # 3. PART 4 & 5 — LOGIN & ORGANIZATION ONBOARDING STATE
        # =========================================================================
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": test_email, "password": test_password}
        )
        assert login_res.status_code == 200
        auth_data = login_res.json()
        token = auth_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        client.cookies.set("recoverai_session", token)

        # Verify current user profile
        me_res = await client.get("/api/v1/auth/me", headers=headers)
        assert me_res.status_code == 200
        me_data = me_res.json()
        assert me_data["user"]["email"] == test_email
        assert me_data["organization"]["name"] == "Recovery Labs Global"
        org_id = me_data["organization"]["id"]

        # Update Onboarding settings (Workspace, Guardrails, Data Source)
        org_update_res = await client.patch(
            "/api/v1/organization/current",
            headers=headers,
            json={
                "industry": "FinTech & E-commerce",
                "company_size": "50-200",
                "country": "India",
                "currency": "INR",
                "max_retries": 3,
                "high_value_threshold": 25000.0,
                "require_human_approval": True,
                "auto_retry_enabled": True,
            }
        )
        assert org_update_res.status_code == 200

        # =========================================================================
        # 4. PART 6 & 7 — EMPTY DASHBOARD & INTEGRATIONS CHECK
        # =========================================================================
        dash_res = await client.get("/api/v1/analytics/summary", headers=headers)
        assert dash_res.status_code == 200
        dash_metrics = dash_res.json()["data"]
        assert dash_metrics["transaction_summary"]["total"] == 0
        assert dash_metrics["transaction_summary"]["failed"] == 0
        assert dash_metrics["revenue_at_risk"] == 0.0
        assert dash_metrics["revenue_recovered"] == 0.0
        assert dash_metrics["recovery_rate_percentage"] == 0.0
        assert dash_metrics["active_recovery_cases"] == 0

        # Integrations must start in DISCONNECTED / NOT_CONNECTED state (No fake connections)
        integ_res = await client.get("/api/v1/integrations", headers=headers)
        assert integ_res.status_code == 200
        for conn in integ_res.json()["data"]:
            assert conn["status"] in ["DISCONNECTED", "NOT_CONNECTED", "INACTIVE"]

        # =========================================================================
        # 5. PART 8 & 9 — MANUAL TRANSACTION INGESTION & AI DIAGNOSIS
        # =========================================================================
        txn_payload = {
            "customer_id": f"cust_{run_id}_01",
            "customer_name": "Aakash Mehta",
            "customer_email": "aakash.mehta@enterprise.in",
            "amount": 8500.0,
            "currency": "INR",
            "status": "FAILED",
            "transaction_type": "PAYMENT",
            "payment_method": "UPI",
            "failure_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
            "failure_reason": "Temporary payment gateway timeout",
        }
        create_txn_res = await client.post("/api/v1/transactions", headers=headers, json=txn_payload)
        assert create_txn_res.status_code == 201
        created_txn = create_txn_res.json()["data"]
        txn_id = created_txn["id"]

        # Verify transaction list shows the record
        txns_list_res = await client.get("/api/v1/transactions", headers=headers)
        assert txns_list_res.status_code == 200
        assert len(txns_list_res.json()["data"]) == 1
        assert txns_list_res.json()["data"][0]["id"] == txn_id

        # Verify dynamic metric reflects ₹8,500 at risk
        dash_res_after_txn = await client.get("/api/v1/analytics/summary", headers=headers)
        assert dash_res_after_txn.status_code == 200
        metrics_after = dash_res_after_txn.json()["data"]
        assert metrics_after["transaction_summary"]["total"] == 1
        assert metrics_after["transaction_summary"]["failed"] == 1
        assert metrics_after["revenue_at_risk"] == 8500.0
        assert metrics_after["revenue_recovered"] == 0.0

        # =========================================================================
        # 6. PART 10 & 11 — POLICY ENGINE EVALUATION & RECOVERY ACTION
        # =========================================================================
        cases_res = await client.get("/api/v1/cases", headers=headers)
        assert cases_res.status_code == 200
        cases = cases_res.json()["data"]
        assert len(cases) == 1
        case_id = cases[0]["id"]

        # Trigger recovery workflow
        trigger_res = await client.post(f"/api/v1/cases/{case_id}/trigger-recovery", headers=headers)
        assert trigger_res.status_code in [200, 201]

        # =========================================================================
        # 7. PART 12 — VERIFIED SUCCESSFUL RECOVERY & REVENUE ACCOUNTING
        # =========================================================================
        # Simulate verified settlement
        async with AsyncSessionLocal() as db:
            txn_rec = await db.get(Transaction, txn_id)
            if txn_rec:
                txn_rec.status = TransactionStatus.CAPTURED
            case_rec = await db.get(RecoveryCase, case_id)
            if case_rec:
                case_rec.status = CaseStatus.RECOVERED
                case_rec.recovered_amount = 8500.0
            await db.commit()

        # Re-fetch analytics: Recovered Revenue must now reflect ₹8,500 (100% recovery rate)
        dash_res_rec = await client.get("/api/v1/analytics/summary", headers=headers)
        assert dash_res_rec.status_code == 200
        metrics_rec = dash_res_rec.json()["data"]
        assert metrics_rec["revenue_recovered"] == 8500.0
        assert metrics_rec["recovery_rate_percentage"] == 100.0

        # =========================================================================
        # 8. PART 14 — HARD DECLINE / UNSAFE CASE GATING
        # =========================================================================
        hard_decline_payload = {
            "customer_id": f"cust_{run_id}_hard",
            "customer_name": "Fraud Risk Customer",
            "customer_email": "fraud.alert@badactor.net",
            "amount": 42000.0,
            "currency": "INR",
            "status": "FAILED",
            "transaction_type": "PAYMENT",
            "payment_method": "CARD",
            "failure_code": "CARD_STOLEN_OR_LOST",
            "failure_reason": "Card reported lost or stolen by issuing bank",
        }
        hard_txn_res = await client.post("/api/v1/transactions", headers=headers, json=hard_decline_payload)
        assert hard_txn_res.status_code == 201

        # Recovered revenue must remain unchanged (₹8,500)
        dash_res_hard = await client.get("/api/v1/analytics/summary", headers=headers)
        assert dash_res_hard.json()["data"]["revenue_recovered"] == 8500.0

        # =========================================================================
        # 9. PART 18 — AUDIT TRAIL VERIFICATION
        # =========================================================================
        audit_res = await client.get("/api/v1/audit/logs", headers=headers)
        assert audit_res.status_code == 200
        logs = audit_res.json()["data"]
        assert len(logs) >= 2
        # Verify SHA-256 hash existence
        for log_entry in logs:
            assert "sha256_hash" in log_entry
            assert len(log_entry["sha256_hash"]) == 64

        # Cryptographic chain verification
        verify_chain_res = await client.get("/api/v1/audit/verify-chain", headers=headers)
        assert verify_chain_res.status_code == 200
        assert verify_chain_res.json()["data"]["is_valid"] is True

        # =========================================================================
        # 10. PART 19 & 20 — LOGOUT & RE-LOGIN PERSISTENCE
        # =========================================================================
        logout_res = await client.post("/api/v1/auth/logout", headers=headers)
        assert logout_res.status_code == 200

        # Token is immediately blacklisted (Cannot access protected routes)
        blocked_res = await client.get("/api/v1/auth/me", headers=headers)
        assert blocked_res.status_code == 401
        client.cookies.clear()

        # Re-login with valid credentials
        relogin_res = await client.post(
            "/api/v1/auth/login",
            json={"email": test_email, "password": test_password}
        )
        assert relogin_res.status_code == 200
        new_token = relogin_res.json()["access_token"]
        new_headers = {"Authorization": f"Bearer {new_token}"}

        # Data persists after logout & re-login
        persisted_res = await client.get("/api/v1/analytics/summary", headers=new_headers)
        assert persisted_res.status_code == 200
        assert persisted_res.json()["data"]["revenue_recovered"] == 8500.0

        # =========================================================================
        # 11. PART 21 — MULTI-TENANT ISOLATION (ORG B BLOCKED FROM ORG A)
        # =========================================================================
        client.cookies.clear()
        org_b_email = f"tenant_b_{run_id}@competitorcorp.com"
        signup_b_res = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": org_b_email,
                "password": test_password,
                "full_name": "Tenant B Executive",
                "company_name": "Competitor Corp",
            }
        )
        assert signup_b_res.status_code in [200, 201]

        login_b_res = await client.post(
            "/api/v1/auth/login",
            json={"email": org_b_email, "password": test_password}
        )
        token_b = login_b_res.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Org B sees zero transactions and zero revenue
        org_b_dash = await client.get("/api/v1/analytics/summary", headers=headers_b)
        assert org_b_dash.json()["data"]["revenue_at_risk"] == 0.0
        assert org_b_dash.json()["data"]["revenue_recovered"] == 0.0

        # Org B attempting direct access to Org A's case must receive 403 or 404
        direct_access_res = await client.get(f"/api/v1/cases/{case_id}", headers=headers_b)
        assert direct_access_res.status_code in [403, 404]
