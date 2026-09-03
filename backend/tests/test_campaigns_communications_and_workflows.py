import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db
from app.models.campaign import Campaign
from app.models.recovery_case import RecoveryCase, CaseStatus
from app.models.template import MessageTemplate
from app.models.communication import CommunicationLog, CustomerOptOut
from app.models.notification import MerchantNotification


@pytest.mark.asyncio
async def test_step11_complete_campaigns_communications_and_workflows():
    await init_db()
    sfx = uuid.uuid4().hex[:6]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. SETUP ORG ALPHA
        signup_a = await client.post(
            "/api/v1/auth/signup",
            json={
                "full_name": "Campaign Admin Alpha",
                "email": f"camp_admin_{sfx}@alpha.io",
                "password": "Password123!",
                "company_name": f"Alpha Global {sfx}",
            },
        )
        assert signup_a.status_code == 201
        token_a = signup_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}
        await client.patch("/api/v1/organization/current", json={"onboarding_completed": True}, headers=headers_a)

        # ======================================================================
        # TEST 1 — Create Campaign
        # ======================================================================
        create_camp_res = await client.post(
            "/api/v1/campaigns",
            json={
                "name": f"High Value Subscription Recovery {sfx}",
                "description": "Autonomous multi-channel recovery for failed recurring payments",
                "recovery_type": "SUBSCRIPTION",
                "target_segment": "RECURRING_SUB",
                "min_amount": 1000.0,
                "max_amount": 50000.0,
                "max_recovery_attempts": 3,
                "retry_delay_hours": 24,
                "channels": ["EMAIL", "WHATSAPP", "SMS"],
                "is_active": True,
            },
            headers=headers_a,
        )
        assert create_camp_res.status_code == 201
        camp_id = create_camp_res.json()["data"]["id"]
        assert camp_id is not None

        # ======================================================================
        # TEST 2 — List Campaigns Scoped to Org
        # ======================================================================
        list_camps = await client.get("/api/v1/campaigns", headers=headers_a)
        assert list_camps.status_code == 200
        camps_data = list_camps.json()["data"]
        matching_c = next((c for c in camps_data if c["id"] == camp_id), None)
        assert matching_c is not None
        assert matching_c["status"] == "ACTIVE"

        # ======================================================================
        # TEST 3 — Pause, Resume, Archive Campaign
        # ======================================================================
        pause_res = await client.post(f"/api/v1/campaigns/{camp_id}/pause", headers=headers_a)
        assert pause_res.status_code == 200
        assert pause_res.json()["data"]["status"] == "PAUSED"

        resume_res = await client.post(f"/api/v1/campaigns/{camp_id}/resume", headers=headers_a)
        assert resume_res.status_code == 200
        assert resume_res.json()["data"]["status"] == "ACTIVE"

        # ======================================================================
        # TEST 4 — Message Templates & Multi-Language Preview
        # ======================================================================
        # List default seeded templates
        templates_res = await client.get("/api/v1/templates", headers=headers_a)
        assert templates_res.status_code == 200
        templates_list = templates_res.json()["data"]
        assert len(templates_list) >= 3

        # Create custom Hinglish template
        custom_tmpl_res = await client.post(
            "/api/v1/templates",
            json={
                "name": "Custom Hinglish Cart Recovery",
                "channel": "WHATSAPP",
                "language": "HINGLISH",
                "body": "Hi {{customer_name}}, aapka {{currency}} {{amount}} ka order pending hai. Link: {{payment_link}}",
            },
            headers=headers_a,
        )
        assert custom_tmpl_res.status_code == 201
        tmpl_id = custom_tmpl_res.json()["data"]["id"]

        # Preview template
        preview_res = await client.post(
            "/api/v1/templates/preview",
            json={
                "body": "Hi {{customer_name}}, payment of {{currency}} {{amount}} to {{company_name}} failed. Link: {{payment_link}}",
                "subject": "Payment issue for {{company_name}}",
            },
            headers=headers_a,
        )
        assert preview_res.status_code == 200
        preview_data = preview_res.json()["data"]
        assert "Sarah Jenkins" in preview_data["rendered_body"]
        assert "8,500.00" in preview_data["rendered_body"]

        # ======================================================================
        # TEST 5 — Transaction -> Recovery Case -> Communication Dispatch
        # ======================================================================
        txn_res = await client.post(
            "/api/v1/transactions",
            json={
                "transaction_id": f"TXN_CAMP_{sfx}",
                "amount": 12500.0,
                "currency": "INR",
                "customer_email": f"camp_user_{sfx}@client.com",
                "payment_method": "CARD",
                "status": "FAILED",
                "failure_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
                "failure_reason": "Timeout during authorization",
            },
            headers=headers_a,
        )
        assert txn_res.status_code == 201
        txn_id = txn_res.json()["data"]["id"]

        # Get Recovery Case
        cases_res = await client.get("/api/v1/cases", headers=headers_a)
        case_item = next(c for c in cases_res.json()["data"] if c["transaction_id"] == txn_id)
        case_id = case_item["id"]

        # Dispatch automated communication step
        dispatch_res = await client.post(
            f"/api/v1/cases/{case_id}/dispatch-communication",
            json={"channel": "EMAIL", "template_id": tmpl_id},
            headers=headers_a,
        )
        assert dispatch_res.status_code == 200
        assert dispatch_res.json()["data"]["status"] == "success"

        # Verify CommunicationLog record created
        comms_res = await client.get(f"/api/v1/cases/{case_id}/communications", headers=headers_a)
        assert comms_res.status_code == 200
        comms_list = comms_res.json()["data"]
        assert len(comms_list) >= 1
        assert comms_list[0]["status"] == "DELIVERED"

        # ======================================================================
        # TEST 6 — Stop Condition (Frequency Cap: Max 3 Messages)
        # ======================================================================
        await client.post(f"/api/v1/cases/{case_id}/dispatch-communication", json={"channel": "EMAIL"}, headers=headers_a)
        await client.post(f"/api/v1/cases/{case_id}/dispatch-communication", json={"channel": "EMAIL"}, headers=headers_a)
        # 4th message should trigger stop condition EXHAUSTED
        stop_res = await client.post(f"/api/v1/cases/{case_id}/dispatch-communication", json={"channel": "EMAIL"}, headers=headers_a)
        assert stop_res.status_code == 200
        assert stop_res.json()["data"]["status"] == "stopped"
        assert stop_res.json()["data"]["reason"] == "MAX_ATTEMPTS_EXHAUSTED"

        # ======================================================================
        # TEST 7 — Customer Opt-Out Suppression
        # ======================================================================
        txn_opt_res = await client.post(
            "/api/v1/transactions",
            json={
                "transaction_id": f"TXN_OPTOUT_{sfx}",
                "amount": 4500.0,
                "currency": "INR",
                "customer_email": f"optout_user_{sfx}@client.com",
                "payment_method": "CARD",
                "status": "FAILED",
                "failure_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
                "failure_reason": "Timeout during authorization",
            },
            headers=headers_a,
        )
        case_opt_id = next(c["id"] for c in (await client.get("/api/v1/cases", headers=headers_a)).json()["data"] if c["transaction_id"] == f"TXN_OPTOUT_{sfx}")
        
        # Trigger opt-out
        opt_res = await client.post(f"/api/v1/cases/{case_opt_id}/opt-out", json={"reason": "UNSUBSCRIBE_CLICK"}, headers=headers_a)
        assert opt_res.status_code == 200
        assert opt_res.json()["data"]["status"] == "CANCELLED"

        # Subsequent communication attempt is blocked
        blocked_com = await client.post(f"/api/v1/cases/{case_opt_id}/dispatch-communication", json={"channel": "EMAIL"}, headers=headers_a)
        assert blocked_com.json()["data"]["status"] == "stopped"
        assert blocked_com.json()["data"]["reason"] == "CUSTOMER_OPTED_OUT"

        # ======================================================================
        # TEST 8 — Case Timeline Retrieval
        # ======================================================================
        timeline_res = await client.get(f"/api/v1/cases/{case_id}/timeline", headers=headers_a)
        assert timeline_res.status_code == 200
        timeline_events = timeline_res.json()["data"]
        assert len(timeline_events) >= 1
        assert any("MESSAGE_SENT" in e["event_type"] or "TRANSACTION" in e["event_type"] for e in timeline_events)

        # ======================================================================
        # TEST 9 — Merchant Notifications
        # ======================================================================
        notifs_res = await client.get("/api/v1/notifications", headers=headers_a)
        assert notifs_res.status_code == 200
        notifs_data = notifs_res.json()["data"]
        assert notifs_data["unread_count"] >= 1

        first_notif_id = notifs_data["notifications"][0]["id"]
        read_res = await client.patch(f"/api/v1/notifications/{first_notif_id}/read", headers=headers_a)
        assert read_res.status_code == 200

        mark_all_res = await client.post("/api/v1/notifications/mark-all-read", headers=headers_a)
        assert mark_all_res.status_code == 200

        # ======================================================================
        # TEST 10 — Multi-Tenant Isolation (Org Beta)
        # ======================================================================
        signup_b = await client.post(
            "/api/v1/auth/signup",
            json={
                "full_name": "Campaign Admin Beta",
                "email": f"camp_beta_{sfx}@beta.io",
                "password": "Password123!",
                "company_name": f"Beta Global {sfx}",
            },
        )
        assert signup_b.status_code == 201
        token_b = signup_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Beta cannot view Alpha's campaigns
        beta_camps = (await client.get("/api/v1/campaigns", headers=headers_b)).json()["data"]
        assert len(beta_camps) == 0

        # Beta cannot access Alpha's campaign detail (404)
        beta_camp_get = await client.get(f"/api/v1/campaigns/{camp_id}", headers=headers_b)
        assert beta_camp_get.status_code == 404

        # Beta cannot access Alpha's case timeline (404)
        beta_timeline_get = await client.get(f"/api/v1/cases/{case_id}/timeline", headers=headers_b)
        assert beta_timeline_get.status_code == 404
