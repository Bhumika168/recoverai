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
async def test_step15_production_deployment_and_readiness_suite():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # =========================================================================
        # 1. HEALTH & READINESS PROBES
        # =========================================================================
        health_resp = await client.get("/health")
        assert health_resp.status_code == 200
        health_data = health_resp.json()
        assert health_data["status"] in ["healthy", "ok"]
        assert "environment" in health_data

        # =========================================================================
        # 2. BRAND-NEW TENANT ISOLATION & ZERO-STATE METRICS
        # =========================================================================
        # Create a fresh test organization
        import uuid
        run_id = uuid.uuid4().hex[:8]
        user_email = f"tenant_admin_{run_id}@acme-enterprises.io"
        user_pwd = hash_password("SecureProdP@ssword2026!")

        async with AsyncSessionLocal() as db:
            org = Organization(
                name="Acme Global Inc",
                slug=f"acme-global-inc-{run_id}",
                industry="SaaS",
                currency="INR",
                auto_retry_enabled=True,
                max_retries=3,
                high_value_threshold=25000.0,
            )
            db.add(org)
            await db.flush()

            user = User(
                email=user_email,
                hashed_password=user_pwd,
                full_name="Acme Executive",
                is_active=True,
            )
            db.add(user)
            await db.flush()

            membership = OrganizationMembership(
                organization_id=org.id,
                user_id=user.id,
                role="OWNER",
            )
            db.add(membership)
            await db.commit()

            org_id = org.id
            user_id = user.id

        # Authenticate
        token = create_access_token({"sub": user_id, "email": user_email, "org_id": org_id})
        headers = {"Authorization": f"Bearer {token}"}
        client.cookies.set("recoverai_session", token)

        # 3. Verify Empty Dashboard Metrics (Calculated dynamically, NOT fabricated)
        dash_resp = await client.get("/api/v1/analytics/summary", headers=headers)
        assert dash_resp.status_code == 200
        dash_data = dash_resp.json()["data"]
        assert dash_data["transaction_summary"]["total"] == 0
        assert dash_data["transaction_summary"]["failed"] == 0
        assert dash_data["revenue_at_risk"] == 0.0
        assert dash_data["revenue_recovered"] == 0.0
        assert dash_data["recovery_rate_percentage"] == 0.0
        assert dash_data["active_recovery_cases"] == 0

        # 4. Verify Provider Connection Status Starts as "Not Connected"
        integ_resp = await client.get("/api/v1/integrations", headers=headers)
        assert integ_resp.status_code == 200
        connections = integ_resp.json()["data"]
        # None of the providers should falsely claim connected
        for conn in connections:
            assert conn["status"] in ["DISCONNECTED", "NOT_CONNECTED", "INACTIVE"]

        # =========================================================================
        # 5. INGEST A REAL FAILED TRANSACTION & OBSERVE DYNAMIC METRIC UPDATES
        # =========================================================================
        txn_create_resp = await client.post(
            "/api/v1/transactions",
            headers=headers,
            json={
                "customer_id": "cust_acme_001",
                "customer_name": "Rajesh Kumar",
                "customer_email": "rajesh.k@acme.com",
                "amount": 12500.0,
                "currency": "INR",
                "status": "FAILED",
                "transaction_type": "SUBSCRIPTION",
                "payment_method": "UPI",
                "failure_code": "INSUFFICIENT_FUNDS",
                "failure_reason": "Debit account has insufficient balance",
            },
        )
        assert txn_create_resp.status_code == 201
        created_txn = txn_create_resp.json()["data"]
        txn_id = created_txn["id"]

        # Re-fetch metrics: Revenue at risk should now reflect ₹12,500
        dash_resp2 = await client.get("/api/v1/analytics/summary", headers=headers)
        assert dash_resp2.status_code == 200
        dash_data2 = dash_resp2.json()["data"]
        assert dash_data2["transaction_summary"]["total"] == 1
        assert dash_data2["transaction_summary"]["failed"] == 1
        assert dash_data2["revenue_at_risk"] == 12500.0
        assert dash_data2["revenue_recovered"] == 0.0
        assert dash_data2["active_recovery_cases"] >= 1

        # =========================================================================
        # 6. VERIFY RECOVERY EXECUTION AND VERIFIED REVENUE ACCOUNTING
        # =========================================================================
        # List cases for this organization
        cases_resp = await client.get("/api/v1/cases", headers=headers)
        assert cases_resp.status_code == 200
        cases_list = cases_resp.json()["data"]
        assert len(cases_list) == 1
        case_id = cases_list[0]["id"]

        # Trigger recovery action
        action_resp = await client.post(
            f"/api/v1/cases/{case_id}/trigger-recovery",
            headers=headers,
        )
        assert action_resp.status_code in [200, 201]

        # Simulate verified recovery payment event
        async with AsyncSessionLocal() as db:
            txn_rec = await db.get(Transaction, txn_id)
            if txn_rec:
                txn_rec.status = TransactionStatus.CAPTURED
            case_rec = await db.get(RecoveryCase, case_id)
            if case_rec:
                case_rec.status = CaseStatus.RECOVERED
                case_rec.recovered_amount = 12500.0
            await db.commit()

        # Re-fetch metrics: Recovered revenue should now reflect ₹12,500 with 100% recovery rate
        dash_resp3 = await client.get("/api/v1/analytics/summary", headers=headers)
        assert dash_resp3.status_code == 200
        dash_data3 = dash_resp3.json()["data"]
        assert dash_data3["revenue_recovered"] == 12500.0
        assert dash_data3["recovery_rate_percentage"] == 100.0

        # =========================================================================
        # 7. CROSS-TENANT ISOLATION TEST (ORG B CANNOT SEE ORG A)
        # =========================================================================
        # Create Org B
        run_b = uuid.uuid4().hex[:8]
        user_b_email = f"admin_orgb_{run_b}@betacorp.io"
        async with AsyncSessionLocal() as db:
            org_b = Organization(
                name="Beta Software Corp",
                slug=f"beta-software-corp-{run_b}",
                industry="FinTech",
                currency="INR",
            )
            db.add(org_b)
            await db.flush()

            user_b = User(
                email=user_b_email,
                hashed_password=hash_password("PassSecure2026!"),
                full_name="Beta Admin",
                is_active=True,
            )
            db.add(user_b)
            await db.flush()

            membership_b = OrganizationMembership(
                organization_id=org_b.id,
                user_id=user_b.id,
                role="OWNER",
            )
            db.add(membership_b)
            await db.commit()

            org_b_id = org_b.id
            user_b_id = user_b.id

        token_b = create_access_token({"sub": user_b_id, "email": user_b_email, "org_id": org_b_id})
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Org B should see 0 transactions and 0 cases
        org_b_txns = await client.get("/api/v1/transactions", headers=headers_b)
        assert org_b_txns.status_code == 200
        assert len(org_b_txns.json()["data"]) == 0

        # Direct access to Org A's case must return 404 (Not Found / Isolated)
        direct_case_resp = await client.get(f"/api/v1/cases/{case_id}", headers=headers_b)
        assert direct_case_resp.status_code in [403, 404]

        # =========================================================================
        # 8. LOGOUT AND TOKEN REVOCATION
        # =========================================================================
        logout_resp = await client.post("/api/v1/auth/logout", headers=headers)
        assert logout_resp.status_code == 200

        # Trying to access protected route with revoked token must fail with 401
        revoked_check = await client.get("/api/v1/auth/me", headers=headers)
        assert revoked_check.status_code == 401
