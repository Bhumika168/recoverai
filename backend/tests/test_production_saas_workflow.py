import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models.recovery_case import CaseStatus


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_empty_organization_zero_dashboard_kpis():
    """
    Test A & O: New organization with zero transactions.
    Dashboard summary must cleanly return ₹0 and 0 active cases with zero fabricated numbers.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        uid = uuid.uuid4().hex[:6]
        signup = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": f"empty_org_{uid}@merchantsaas.io",
                "password": "Password123!",
                "full_name": "Empty Org Owner",
                "company_name": f"Empty Org {uid}",
            },
        )
        assert signup.status_code == 201
        token = signup.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Query analytics summary
        res = await client.get("/api/v1/analytics/summary", headers=headers)
        assert res.status_code == 200
        data = res.json()["data"]

        assert data["revenue_at_risk"] == 0
        assert data["revenue_recovered"] == 0
        assert data["recovery_rate_percentage"] == 0.0
        assert data["active_recovery_cases"] == 0
        assert data["recovered_cases"] == 0
        assert data["human_escalations"] == 0
        assert data["total_cases"] == 0
        assert data["transaction_summary"]["total"] == 0


@pytest.mark.asyncio
async def test_manual_transaction_end_to_end_recovery_workflow():
    """
    Test B, C, D, E, F, G:
    1. Create organization.
    2. Add failed transaction manually.
    3. Verify persistence and recovery case opening.
    4. Trigger single-transaction recovery POST /transactions/{id}/recover.
    5. Verify policy decision and state updates.
    6. Simulate settlement verification.
    7. Verify dashboard KPI updates from persisted records.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        uid = uuid.uuid4().hex[:6]
        signup = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": f"merchant_flow_{uid}@merchantsaas.io",
                "password": "Password123!",
                "full_name": "Merchant Flow User",
                "company_name": f"Flow Merchant {uid}",
            },
        )
        token = signup.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Add failed transaction (₹4,500 temporary network error)
        txn_payload = {
            "amount": 4500.0,
            "currency": "INR",
            "status": "FAILED",
            "payment_method": "upi",
            "customer_name": "Test Customer",
            "customer_email": "cust@example.com",
            "failure_code": "GATEWAY_TIMEOUT",
            "failure_reason": "Bank server timeout during UPI collect",
        }
        create_res = await client.post("/api/v1/transactions", json=txn_payload, headers=headers)
        assert create_res.status_code == 201
        txn_data = create_res.json()["data"]
        txn_id = txn_data["id"]
        assert txn_data["amount"] == 4500.0
        assert txn_data["status"] == "FAILED"

        # 2. Verify transaction is retrieved in list
        list_res = await client.get("/api/v1/transactions", headers=headers)
        assert list_res.status_code == 200
        txns = list_res.json()["data"]
        assert any(t["id"] == txn_id for t in txns)

        # 3. Verify single-transaction recovery trigger: POST /transactions/{txn_id}/recover
        recover_res = await client.post(f"/api/v1/transactions/{txn_id}/recover", headers=headers)
        assert recover_res.status_code == 200
        recover_data = recover_res.json()["data"]
        case_id = recover_data["case_id"]
        assert case_id is not None
        assert recover_data["amount_at_risk"] == 4500.0

        # 4. Check case detail and AI decision / deterministic policy evaluation
        case_res = await client.get(f"/api/v1/cases/{case_id}", headers=headers)
        assert case_res.status_code == 200
        case_detail = case_res.json()["data"]
        assert len(case_detail["ai_decisions"]) >= 1
        assert len(case_detail["actions"]) >= 1

        # Check KPI before verification
        kpi_res_1 = await client.get("/api/v1/analytics/summary", headers=headers)
        assert kpi_res_1.json()["data"]["revenue_at_risk"] == 4500.0
        assert kpi_res_1.json()["data"]["revenue_recovered"] == 0.0

        # 5. Simulate customer payment / settlement verification
        verify_res = await client.post(f"/api/v1/cases/{case_id}/verify-recovery", headers=headers)
        assert verify_res.status_code == 200
        assert verify_res.json()["data"]["status"] == CaseStatus.RECOVERED.value

        # 6. Check KPI after verification - revenue recovered must update dynamically
        kpi_res_2 = await client.get("/api/v1/analytics/summary", headers=headers)
        kpis_after = kpi_res_2.json()["data"]
        assert kpis_after["revenue_recovered"] == 4500.0
        assert kpis_after["recovery_rate_percentage"] == 100.0
        assert kpis_after["recovered_cases"] == 1


@pytest.mark.asyncio
async def test_high_value_transaction_requires_human_approval():
    """
    Test I: Transaction > ₹25,000 must trigger Rule 5 (HIGH_VALUE_TRANSACTION_GATE),
    placing the recovery case into PENDING_APPROVAL / requires_human_approval="YES"
    and disallowing unapproved automatic execution.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        uid = uuid.uuid4().hex[:6]
        signup = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": f"hv_org_{uid}@merchantsaas.io",
                "password": "Password123!",
                "full_name": "High Value Merchant",
                "company_name": f"High Value Corp {uid}",
            },
        )
        token = signup.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create failed transaction > ₹25k
        txn_payload = {
            "amount": 75000.0,
            "currency": "INR",
            "status": "FAILED",
            "payment_method": "card",
            "customer_name": "Enterprise Buyer",
            "customer_email": "buyer@enterprise.corp",
            "failure_code": "INSUFFICIENT_FUNDS",
            "failure_reason": "Insufficient balance on enterprise debit card",
        }
        create_res = await client.post("/api/v1/transactions", json=txn_payload, headers=headers)
        assert create_res.status_code == 201
        txn_id = create_res.json()["data"]["id"]

        # Find case
        cases_res = await client.get("/api/v1/cases", headers=headers)
        cases = cases_res.json()["data"]
        hv_case = next(c for c in cases if c["transaction_id"] == txn_id)
        assert hv_case["status"] == CaseStatus.PENDING_APPROVAL.value
        assert hv_case["requires_human_approval"] == "YES"

        # Merchant approves the case
        approve_res = await client.post(f"/api/v1/cases/{hv_case['id']}/approve", headers=headers)
        assert approve_res.status_code == 200
        approved_case = approve_res.json()["data"]
        assert approved_case["requires_human_approval"] == "NO"
        assert approved_case["status"] == CaseStatus.IN_PROGRESS.value


@pytest.mark.asyncio
async def test_hard_decline_fraud_suppression():
    """
    Test J: Anti-fraud hard decline (e.g. CARD_STOLEN_OR_LOST) must trigger Rule 2
    and be strictly blocked from retries / unrecoverable.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        uid = uuid.uuid4().hex[:6]
        signup = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": f"fraud_org_{uid}@merchantsaas.io",
                "password": "Password123!",
                "full_name": "Fraud Test Merchant",
                "company_name": f"Security Org {uid}",
            },
        )
        token = signup.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        txn_payload = {
            "amount": 18000.0,
            "currency": "INR",
            "status": "FAILED",
            "payment_method": "card",
            "customer_name": "Suspect Actor",
            "customer_email": "fraud@badactor.net",
            "failure_code": "CARD_STOLEN_OR_LOST",
            "failure_reason": "Card reported lost or stolen by issuing institution",
        }
        create_res = await client.post("/api/v1/transactions", json=txn_payload, headers=headers)
        assert create_res.status_code == 201
        txn_id = create_res.json()["data"]["id"]

        cases_res = await client.get("/api/v1/cases", headers=headers)
        case = next(c for c in cases_res.json()["data"] if c["transaction_id"] == txn_id)
        assert case["status"] in [CaseStatus.UNRECOVERABLE.value, CaseStatus.BLOCKED.value]


@pytest.mark.asyncio
async def test_csv_import_workflow_creates_real_recoverable_records():
    """
    Test L: CSV import creates persisted organization-owned transactions,
    opens recovery cases, and updates dashboard metrics.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        uid = uuid.uuid4().hex[:6]
        signup = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": f"csv_org_{uid}@merchantsaas.io",
                "password": "Password123!",
                "full_name": "CSV Ingest Merchant",
                "company_name": f"CSV Merchant {uid}",
            },
        )
        token = signup.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Import CSV rows
        import_payload = [
            {
                "transaction_id": f"CSV-TXN-{uid}-001",
                "amount": 3200.0,
                "currency": "INR",
                "status": "FAILED",
                "payment_method": "card",
                "customer_email": "csv1@customer.com",
                "customer_name": "CSV User 1",
                "failure_code": "INSUFFICIENT_FUNDS",
                "failure_reason": "Card balance insufficient",
                "timestamp": "2026-09-05T12:00:00Z",
            },
            {
                "transaction_id": f"CSV-TXN-{uid}-002",
                "amount": 8900.0,
                "currency": "INR",
                "status": "FAILED",
                "payment_method": "upi",
                "customer_email": "csv2@customer.com",
                "customer_name": "CSV User 2",
                "failure_code": "UPI_MPIN_TIMEOUT",
                "failure_reason": "Customer did not enter MPIN within window",
                "timestamp": "2026-09-05T12:05:00Z",
            },
        ]
        import_res = await client.post(
            "/api/v1/transactions/import-csv",
            json={"rows": import_payload},
            headers=headers,
        )
        assert import_res.status_code == 200
        summary = import_res.json()["data"]
        assert summary["imported_count"] == 2
        assert summary["failed_recoveries_triggered"] == 2
        assert summary["skipped_count"] == 0

        # Verify transactions appear in transactions list
        txns_res = await client.get("/api/v1/transactions", headers=headers)
        assert txns_res.status_code == 200
        txns = txns_res.json()["data"]
        csv_ids = {f"CSV-TXN-{uid}-001", f"CSV-TXN-{uid}-002"}
        assert sum(1 for t in txns if t["transaction_id"] in csv_ids or t["id"] in csv_ids) == 2

        # Verify cases opened and revenue at risk calculated
        kpis_res = await client.get("/api/v1/analytics/summary", headers=headers)
        kpis = kpis_res.json()["data"]
        assert kpis["revenue_at_risk"] == 12100.0  # 3200 + 8900
        assert kpis["total_cases"] >= 2


@pytest.mark.asyncio
async def test_tenant_isolation_org_isolation():
    """
    Test M: Organization A cannot read or recover transactions/cases belonging to Organization B.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Org A
        uid_a = uuid.uuid4().hex[:6]
        signup_a = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": f"org_a_{uid_a}@tenanta.com",
                "password": "Password123!",
                "full_name": "Owner A",
                "company_name": f"Corp A {uid_a}",
            },
        )
        token_a = signup_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Org B
        uid_b = uuid.uuid4().hex[:6]
        signup_b = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": f"org_b_{uid_b}@tenantb.com",
                "password": "Password123!",
                "full_name": "Owner B",
                "company_name": f"Corp B {uid_b}",
            },
        )
        token_b = signup_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Org A creates a transaction
        txn_res_a = await client.post(
            "/api/v1/transactions",
            json={
                "amount": 5000.0,
                "currency": "INR",
                "status": "FAILED",
                "payment_method": "card",
                "customer_email": "private@org-a.com",
                "failure_code": "NETWORK_ERROR",
                "failure_reason": "Org A private transaction failure",
            },
            headers=headers_a,
        )
        assert txn_res_a.status_code == 201
        txn_id_a = txn_res_a.json()["data"]["id"]

        # Org B attempts to read Org A transaction -> 404
        read_b = await client.get(f"/api/v1/transactions/{txn_id_a}", headers=headers_b)
        assert read_b.status_code == 404

        # Org B attempts to recover Org A transaction -> 404
        recover_b = await client.post(f"/api/v1/transactions/{txn_id_a}/recover", headers=headers_b)
        assert recover_b.status_code == 404
