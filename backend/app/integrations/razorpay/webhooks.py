import hmac
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.config import settings
from app.logging_config import logger
from app.exceptions import RecoverAIException
from app.integrations.razorpay.models import RazorpayWebhookEvent
from app.models.customer import Customer
from app.models.transaction import Transaction, TransactionStatus, PaymentMethod
from app.models.payment_attempt import PaymentAttempt, AttemptStatus
from app.models.recovery_case import RecoveryCase, CaseStatus
from app.models.audit_log import AuditLog, calculate_hash


class RazorpayWebhookVerifier:
    """
    Official Razorpay HMAC SHA-256 signature verifier.
    """

    @staticmethod
    def verify_signature(
        raw_body: bytes,
        signature: str,
        secret: Optional[str] = None,
    ) -> bool:
        webhook_secret = secret or settings.RAZORPAY_WEBHOOK_SECRET
        if not webhook_secret:
            logger.warning("[RazorpayWebhook] Webhook secret is not configured; skipping verification in dev mode if empty")
            return True

        if not signature:
            logger.error("[RazorpayWebhook] Missing X-Razorpay-Signature header")
            return False

        try:
            expected_signature = hmac.new(
                key=webhook_secret.encode("utf-8"),
                msg=raw_body,
                digestmod=hashlib.sha256,
            ).hexdigest()

            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            logger.error(f"[RazorpayWebhook] Error calculating HMAC signature: {str(e)}")
            return False


class RazorpayWebhookHandler:
    """
    Processes verified Razorpay webhook events, reconciles database states,
    and triggers autonomous recovery workflows on payment failures.
    """

    @classmethod
    async def process_event(
        cls,
        event_data: Dict[str, Any],
        db: AsyncSession,
    ) -> Dict[str, Any]:
        event_name = event_data.get("event")
        payload = event_data.get("payload", {})
        account_id = event_data.get("account_id", "acc_default")
        
        logger.info(f"[RazorpayWebhook] Received event: {event_name} (Account: {account_id})")

        # -------------------------------------------------------------
        # 1. Event: payment.failed
        # -------------------------------------------------------------
        if event_name == "payment.failed":
            payment_entity = payload.get("payment", {}).get("entity", {})
            return await cls._handle_payment_failed(payment_entity, db)

        # -------------------------------------------------------------
        # 2. Event: payment.captured / payment.authorized / order.paid
        # -------------------------------------------------------------
        elif event_name in ["payment.captured", "payment.authorized", "order.paid"]:
            payment_entity = payload.get("payment", {}).get("entity", {})
            order_entity = payload.get("order", {}).get("entity", {})
            return await cls._handle_payment_success(payment_entity, order_entity, db)

        # -------------------------------------------------------------
        # 3. Event: payment_link.paid
        # -------------------------------------------------------------
        elif event_name == "payment_link.paid":
            plink_entity = payload.get("payment_link", {}).get("entity", {})
            payment_entity = payload.get("payment", {}).get("entity", {})
            return await cls._handle_payment_link_paid(plink_entity, payment_entity, db)

        # Other events
        logger.info(f"[RazorpayWebhook] Acknowledged event {event_name} without state mutation.")
        return {"status": "ACKNOWLEDGED", "event": event_name}

    @classmethod
    async def _handle_payment_failed(
        cls,
        payment: Dict[str, Any],
        db: AsyncSession,
    ) -> Dict[str, Any]:
        rzp_payment_id = payment.get("id")
        rzp_order_id = payment.get("order_id")
        amount = payment.get("amount", 0) / 100.0  # Convert paise to major currency units (INR)
        currency = payment.get("currency", "INR")
        method_str = payment.get("method", "card").upper()
        email = payment.get("email") or "customer@example.com"
        contact = payment.get("contact")
        
        error_code = payment.get("error_code") or "GATEWAY_ERROR"
        error_desc = payment.get("error_description") or "Payment processing failed"
        error_source = payment.get("error_source") or "issuer"
        error_step = payment.get("error_step") or "payment_authorization"

        # Map payment method
        try:
            method_enum = PaymentMethod[method_str]
        except KeyError:
            method_enum = PaymentMethod.CARD

        # 1. Find or create Customer
        cust_res = await db.execute(select(Customer).where(Customer.email == email))
        customer = cust_res.scalar_one_or_none()
        if not customer:
            customer = Customer(
                email=email,
                phone=contact,
                name=email.split("@")[0].capitalize(),
            )
            db.add(customer)
            await db.flush()
            await db.refresh(customer)

        # 2. Check if transaction with this payment_id / order_id already exists (Idempotency)
        existing_txn = None
        if rzp_payment_id:
            txn_res = await db.execute(select(Transaction).where(Transaction.rzp_payment_id == rzp_payment_id))
            existing_txn = txn_res.scalar_one_or_none()

        if not existing_txn:
            txn = Transaction(
                customer_id=customer.id,
                amount=amount,
                currency=currency,
                status=TransactionStatus.FAILED,
                payment_method=method_enum,
                rzp_order_id=rzp_order_id,
                rzp_payment_id=rzp_payment_id,
                failure_code=error_code,
                failure_reason=error_desc,
                failure_source=error_source,
                error_step=error_step,
            )
            db.add(txn)
            await db.flush()
            await db.refresh(txn)

            attempt = PaymentAttempt(
                transaction_id=txn.id,
                attempt_number=1,
                rzp_payment_id=rzp_payment_id,
                status=AttemptStatus.FAILED,
                error_code=error_code,
                error_description=error_desc,
                gateway_response=payment,
            )
            db.add(attempt)
        else:
            txn = existing_txn
            txn.status = TransactionStatus.FAILED
            txn.failure_code = error_code
            txn.failure_reason = error_desc

        await db.flush()

        # 3. Trigger Autonomous Recovery Pipeline
        from app.agents.orchestrator import recover_transaction
        recovery_case = await recover_transaction(txn.id, db, actor="RAZORPAY_WEBHOOK")
        return {
            "status": "PROCESSED",
            "event": "payment.failed",
            "transaction_id": txn.id,
            "recovery_case_id": recovery_case.id,
            "case_status": recovery_case.status.value,
        }

    @classmethod
    async def _handle_payment_success(
        cls,
        payment: Dict[str, Any],
        order: Dict[str, Any],
        db: AsyncSession,
    ) -> Dict[str, Any]:
        rzp_payment_id = payment.get("id")
        rzp_order_id = payment.get("order_id") or order.get("id")
        amount = (payment.get("amount") or order.get("amount", 0)) / 100.0

        # Find matching transaction by rzp_payment_id or rzp_order_id
        txn = None
        if rzp_payment_id:
            txn_res = await db.execute(
                select(Transaction)
                .where(Transaction.rzp_payment_id == rzp_payment_id)
                .options(selectinload(Transaction.recovery_case))
            )
            txn = txn_res.scalar_one_or_none()

        if not txn and rzp_order_id:
            txn_res = await db.execute(
                select(Transaction)
                .where(Transaction.rzp_order_id == rzp_order_id)
                .options(selectinload(Transaction.recovery_case))
            )
            txn = txn_res.scalar_one_or_none()

        if txn:
            txn.status = TransactionStatus.CAPTURED
            if txn.recovery_case:
                case = txn.recovery_case
                case.status = CaseStatus.RECOVERED
                case.recovered_amount = amount or txn.amount
                case.recovered_at = datetime.now(timezone.utc)
                case.strategy_summary = f"[RECOVERED] Verified via Razorpay webhook ({rzp_payment_id or rzp_order_id})"
                
                # Append Audit Log
                latest_audit = (
                    await db.execute(select(AuditLog).order_by(desc(AuditLog.created_at)).limit(1))
                ).scalar_one_or_none()
                prev_hash = latest_audit.sha256_hash if latest_audit else "GENESIS_RECOVERAI"
                now_dt = datetime.now(timezone.utc)
                now_iso = now_dt.isoformat()

                audit_entry = AuditLog(
                    entity_name="RecoveryCase",
                    entity_id=case.id,
                    event_type="RECOVERY_VERIFIED",
                    actor="RAZORPAY_WEBHOOK",
                    state_before={"status": "IN_PROGRESS"},
                    state_after={"status": "RECOVERED", "recovered_amount": case.recovered_amount},
                    prev_hash=prev_hash,
                    sha256_hash=calculate_hash(
                        prev_hash, "RECOVERY_VERIFIED", "RecoveryCase", case.id, "RAZORPAY_WEBHOOK",
                        {"status": "RECOVERED", "recovered_amount": case.recovered_amount}, now_iso
                    ),
                    timestamp_iso=now_iso,
                    notes=f"Revenue recovered verified via payment webhook: {rzp_payment_id}",
                    created_at=now_dt,
                )
                db.add(audit_entry)

            await db.flush()
            return {"status": "RECOVERED", "transaction_id": txn.id, "recovered_amount": amount}

        return {"status": "ACKNOWLEDGED_NO_MATCH", "payment_id": rzp_payment_id}

    @classmethod
    async def _handle_payment_link_paid(
        cls,
        plink: Dict[str, Any],
        payment: Dict[str, Any],
        db: AsyncSession,
    ) -> Dict[str, Any]:
        plink_id = plink.get("id")
        amount = plink.get("amount", 0) / 100.0

        # Find RecoveryCase or Action associated with plink_id
        from app.models.recovery_action import RecoveryAction, ActionStatus
        act_res = await db.execute(
            select(RecoveryAction)
            .where(RecoveryAction.rzp_payment_link_id == plink_id)
            .options(selectinload(RecoveryAction.recovery_case).selectinload(RecoveryCase.transaction))
        )
        action = act_res.scalar_one_or_none()

        if action and action.recovery_case:
            action.status = ActionStatus.COMPLETED
            case = action.recovery_case
            case.status = CaseStatus.RECOVERED
            case.recovered_amount = amount or case.amount_at_risk
            case.recovered_at = datetime.now(timezone.utc)
            case.strategy_summary = f"[RECOVERED] Customer completed payment via Recovery Payment Link ({plink_id})"

            if case.transaction:
                case.transaction.status = TransactionStatus.RECOVERED

            # Append audit log
            latest_audit = (
                await db.execute(select(AuditLog).order_by(desc(AuditLog.created_at)).limit(1))
            ).scalar_one_or_none()
            prev_hash = latest_audit.sha256_hash if latest_audit else "GENESIS_RECOVERAI"
            now_dt = datetime.now(timezone.utc)
            now_iso = now_dt.isoformat()

            audit_entry = AuditLog(
                entity_name="RecoveryCase",
                entity_id=case.id,
                event_type="PAYMENT_LINK_PAID",
                actor="RAZORPAY_WEBHOOK",
                state_before={"status": "IN_PROGRESS"},
                state_after={"status": "RECOVERED", "recovered_amount": case.recovered_amount, "plink_id": plink_id},
                prev_hash=prev_hash,
                sha256_hash=calculate_hash(
                    prev_hash, "PAYMENT_LINK_PAID", "RecoveryCase", case.id, "RAZORPAY_WEBHOOK",
                    {"status": "RECOVERED", "recovered_amount": case.recovered_amount, "plink_id": plink_id}, now_iso
                ),
                timestamp_iso=now_iso,
                notes=f"Payment link paid: {plink_id} for amount {amount} INR",
                created_at=now_dt,
            )
            db.add(audit_entry)
            await db.flush()

            return {"status": "RECOVERED_VIA_LINK", "case_id": case.id, "plink_id": plink_id}

        return {"status": "ACKNOWLEDGED_LINK_NO_MATCH", "plink_id": plink_id}
