from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.models.organization import Organization
from app.models.transaction import Transaction, TransactionStatus
from app.models.customer import Customer
from app.models.payment_attempt import PaymentAttempt
from app.models.recovery_case import RecoveryCase, CaseStatus
from app.models.recovery_action import RecoveryAction, ActionStatus, ActionType
from app.models.ai_decision import AIDecision
from app.models.audit_log import AuditLog, calculate_hash
from app.agents.detector import detector
from app.agents.diagnostician import diagnostician
from app.agents.decision_engine import decision_engine
from app.agents.policy_engine import policy_engine
from app.agents.executor import executor
from app.agents.verifier import verifier
from app.exceptions import EntityNotFoundException
from app.logging_config import logger


class RecoveryOrchestrator:
    """
    Orchestrator Agent: Coordinates the complete autonomous recovery pipeline:
    Transaction -> Detector -> Diagnostician -> Decision Engine -> Policy Engine -> Executor -> Verifier -> Audit Log.
    """

    @classmethod
    async def recover_transaction(
        cls,
        transaction_id: str,
        db: AsyncSession,
        actor: str = "SYSTEM_AGENT",
        override_confidence: Optional[float] = None,
        simulated_immediate_success: bool = False,
    ) -> RecoveryCase:
        logger.info(f"[Orchestrator] Starting recovery workflow for transaction {transaction_id}")

        # 1. Fetch Transaction with full context
        query = (
            select(Transaction)
            .where(Transaction.id == transaction_id)
            .options(
                selectinload(Transaction.customer),
                selectinload(Transaction.payment_attempts),
                selectinload(Transaction.recovery_case).selectinload(RecoveryCase.actions),
            )
        )
        result = await db.execute(query)
        transaction = result.scalar_one_or_none()

        if not transaction:
            raise EntityNotFoundException("Transaction", transaction_id)

        # 2. Risk Detection
        detection = detector.detect(transaction)
        if not detection.is_recoverable_candidate:
            logger.info(f"[Detector] Transaction {transaction_id} not eligible: {detection.reason}")
            if transaction.recovery_case:
                return transaction.recovery_case
            raise ValueError(f"Transaction {transaction_id} is not eligible for recovery: {detection.reason}")

        # Ensure RecoveryCase exists
        recovery_case = transaction.recovery_case
        org_id = transaction.organization_id
        if not recovery_case:
            recovery_case = RecoveryCase(
                organization_id=org_id,
                transaction_id=transaction.id,
                customer_id=transaction.customer_id,
                status=CaseStatus.OPEN,
                amount_at_risk=transaction.amount,
                recovered_amount=0.0,
                recovery_score=50,
                risk_level=detection.priority,
                retry_count=len(transaction.payment_attempts) - 1 if transaction.payment_attempts else 0,
            )
            db.add(recovery_case)
            await db.flush()
            await db.refresh(recovery_case)

        # 3. AI Diagnosis
        diagnosis = diagnostician.diagnose(
            transaction=transaction,
            payment_attempts=transaction.payment_attempts,
            override_confidence=override_confidence,
        )
        logger.info(f"[Diagnostician] Category: {diagnosis.failure_category}, Confidence: {diagnosis.confidence:.2f}")

        # 4. Decision Engine
        recommendation = decision_engine.decide(
            transaction=transaction,
            diagnosis=diagnosis,
            override_confidence=override_confidence,
        )
        logger.info(f"[Decision Engine] Recommended: {recommendation.action}, Exp Prob: {recommendation.expected_recovery_probability:.2f}")

        # Record AI Decision in DB
        ai_decision_record = AIDecision(
            case_id=recovery_case.id,
            failure_category=diagnosis.failure_category,
            root_cause_explanation=diagnosis.root_cause,
            confidence_score=recommendation.confidence,
            recovery_probability=recommendation.expected_recovery_probability,
            reasoning_steps=[
                f"1. Ingested failure code: {transaction.failure_code or 'N/A'}",
                f"2. Classified into category: {diagnosis.failure_category}",
                f"3. Root cause: {diagnosis.root_cause}",
                f"4. Strategy evaluated: {recommendation.reason}",
            ],
            risk_factors=recommendation.risk_factors,
            recommended_action=recommendation.action,
            recommended_delay_minutes=recommendation.recommended_delay_minutes,
            recommended_channel=recommendation.recommended_channel,
            model_name="gemini-2.5-flash",
        )
        db.add(ai_decision_record)

        # 5. Deterministic Policy Engine Guardrails
        actions_query = await db.execute(select(RecoveryAction).where(RecoveryAction.case_id == recovery_case.id))
        existing_actions = actions_query.scalars().all()
        
        # Load organization custom guardrail settings
        org_query = await db.execute(select(Organization).where(Organization.id == org_id))
        org_obj = org_query.scalar_one_or_none()
        org_max_retries = org_obj.max_retries if org_obj else 3
        org_high_value_limit = org_obj.high_value_threshold if org_obj else 25000.0

        policy_verdict = policy_engine.evaluate(
            transaction=transaction,
            recovery_case=recovery_case,
            diagnosis=diagnosis,
            recommendation=recommendation,
            existing_actions=existing_actions,
            max_retries=org_max_retries,
            high_value_limit=org_high_value_limit,
        )
        logger.info(f"[Policy Engine] Approved: {policy_verdict.approved}, Action: {policy_verdict.final_action}, Approval Req: {policy_verdict.requires_human_approval}")

        # 6. Safe Executor
        execution = executor.execute(
            transaction=transaction,
            recovery_case=recovery_case,
            policy_verdict=policy_verdict,
            channel=recommendation.recommended_channel,
        )

        # 7. Verifier
        verification = verifier.verify(
            recovery_case=recovery_case,
            execution_result=execution,
            policy_verdict=policy_verdict,
            simulated_success=simulated_immediate_success,
        )

        # 8. Create RecoveryAction Record
        action_record = RecoveryAction(
            case_id=recovery_case.id,
            action_type=execution.action_type,
            status=execution.action_status,
            channel=execution.channel,
            idempotency_key=execution.idempotency_key,
            rzp_payment_link_id=execution.rzp_payment_link_id,
            rzp_short_url=execution.rzp_short_url,
            payload=execution.simulated_result,
            result={"verified": verification.is_recovered, "notes": verification.verification_notes},
            policy_passed="YES" if policy_verdict.approved else "NO",
            policy_rule_notes=policy_verdict.notes or policy_verdict.rejection_reason,
            executed_at=execution.timestamp if execution.action_status != ActionStatus.PENDING_APPROVAL else None,
        )
        db.add(action_record)

        # 9. Update RecoveryCase State & Metrics
        recovery_case.status = verification.new_case_status
        recovery_case.recovery_score = int(recommendation.expected_recovery_probability * 100)
        recovery_case.strategy_summary = f"[{policy_verdict.final_action.upper()}] {recommendation.reason}"
        recovery_case.requires_human_approval = "YES" if policy_verdict.requires_human_approval else "NO"
        recovery_case.approval_reason = policy_verdict.rejection_reason
        
        if execution.action_type.value == "DELAYED_RETRY" and execution.action_status in [ActionStatus.COMPLETED, ActionStatus.SCHEDULED]:
            recovery_case.retry_count += 1

        if verification.is_recovered:
            recovery_case.recovered_amount = verification.recovered_amount
            recovery_case.recovered_at = verification.verified_at
            transaction.status = TransactionStatus.RECOVERED

        await db.flush()
        await db.refresh(recovery_case)

        # 10. Append SHA-256 Chained Audit Log
        latest_audit = (
            await db.execute(select(AuditLog).order_by(desc(AuditLog.created_at)).limit(1))
        ).scalar_one_or_none()
        prev_hash = latest_audit.sha256_hash if latest_audit else "GENESIS_RECOVERAI"
        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()

        audit_state_after = {
            "case_id": recovery_case.id,
            "transaction_id": transaction.id,
            "status": recovery_case.status.value,
            "action_executed": execution.action_type.value,
            "policy_approved": policy_verdict.approved,
            "requires_human_approval": recovery_case.requires_human_approval,
            "recovered_amount": recovery_case.recovered_amount,
            "idempotency_key": execution.idempotency_key,
        }
        sha_hash = calculate_hash(
            prev_hash=prev_hash,
            event_type=f"RECOVERY_{execution.action_type.value}",
            entity_name="RecoveryCase",
            entity_id=recovery_case.id,
            actor=actor,
            state_after=audit_state_after,
            timestamp_iso=now_iso,
        )

        audit_entry = AuditLog(
            organization_id=org_id,
            entity_name="RecoveryCase",
            entity_id=recovery_case.id,
            event_type=f"RECOVERY_{execution.action_type.value}",
            actor=actor,
            state_before={"status": "OPEN"},
            state_after=audit_state_after,
            prev_hash=prev_hash,
            sha256_hash=sha_hash,
            timestamp_iso=now_iso,
            notes=f"Recovery pipeline executed: {execution.action_type.value} -> {recovery_case.status.value}",
            created_at=now_dt,
        )
        db.add(audit_entry)
        await db.flush()

        logger.info(f"[Orchestrator] Completed recovery for {transaction_id}. Final Case Status: {recovery_case.status.value}")
        return recovery_case


# Expose singleton service function
recover_transaction = RecoveryOrchestrator.recover_transaction
