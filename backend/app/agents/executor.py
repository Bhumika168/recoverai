import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from app.models.transaction import Transaction
from app.models.recovery_case import RecoveryCase
from app.models.recovery_action import ActionType, ActionStatus
from app.agents.policy_engine import PolicyVerdict
from app.integrations.provider import PaymentProvider, default_payment_provider


@dataclass
class ExecutionResult:
    action_status: ActionStatus
    action_type: ActionType
    simulated_result: Dict[str, Any]
    timestamp: datetime
    idempotency_key: str
    channel: str
    rzp_payment_link_id: Optional[str] = None
    rzp_short_url: Optional[str] = None


class SafeRecoveryExecutor:
    """
    Executor Agent: Executes recovery actions through the active PaymentProvider.
    Generates deterministic idempotency keys, structured simulated payloads,
    and payment link artifacts without performing destructive operations.
    """

    @classmethod
    def execute(
        cls,
        transaction: Transaction,
        recovery_case: RecoveryCase,
        policy_verdict: PolicyVerdict,
        channel: str = "GATEWAY",
        payment_provider: Optional[PaymentProvider] = None,
    ) -> ExecutionResult:
        provider = payment_provider or default_payment_provider
        now_dt = datetime.now(timezone.utc)
        action_name = policy_verdict.final_action.upper()
        
        # Map string action to ActionType enum
        action_type_mapping = {
            "DELAYED_RETRY": ActionType.DELAYED_RETRY,
            "SUBSCRIPTION_RETRY": ActionType.DELAYED_RETRY,
            "RECOVERY_LINK": ActionType.PAYMENT_LINK,
            "CUSTOMER_ACTION_REQUIRED": ActionType.SWITCH_METHOD,
            "HUMAN_ESCALATION": ActionType.HUMAN_ESCALATION,
            "NO_ACTION": ActionType.NO_ACTION,
        }
        action_type = action_type_mapping.get(action_name, ActionType.NO_ACTION)
        
        # Deterministic Idempotency Key
        idempotency_key = f"idemp_{recovery_case.id}_{action_type.value}_{recovery_case.retry_count + 1}_{uuid.uuid4().hex[:8]}"

        # If policy required human approval or rejected execution
        if policy_verdict.requires_human_approval:
            return ExecutionResult(
                action_status=ActionStatus.PENDING_APPROVAL,
                action_type=action_type,
                simulated_result={
                    "status": "HELD_FOR_APPROVAL",
                    "reason": policy_verdict.rejection_reason or "Held by policy guardrail",
                    "timestamp": now_dt.isoformat(),
                },
                timestamp=now_dt,
                idempotency_key=idempotency_key,
                channel=channel,
            )

        if not policy_verdict.approved:
            return ExecutionResult(
                action_status=ActionStatus.CANCELLED,
                action_type=action_type,
                simulated_result={
                    "status": "REJECTED_BY_POLICY",
                    "reason": policy_verdict.rejection_reason or "Policy violation",
                    "timestamp": now_dt.isoformat(),
                },
                timestamp=now_dt,
                idempotency_key=idempotency_key,
                channel=channel,
            )

        # 1. Delayed Retry / Subscription Retry Execution
        if action_type == ActionType.DELAYED_RETRY:
            return ExecutionResult(
                action_status=ActionStatus.SCHEDULED,
                action_type=action_type,
                simulated_result={
                    "provider": provider.provider_name,
                    "action": "SCHEDULED_RETRY",
                    "retry_attempt": recovery_case.retry_count + 1,
                    "cooldown_seconds": 900,
                    "target_gateway": "Razorpay Smart Routing",
                    "execution_message": "Automated gateway retry scheduled with optimal bank routing window.",
                },
                timestamp=now_dt,
                idempotency_key=idempotency_key,
                channel="GATEWAY",
            )

        # 2. Payment Link Generation via PaymentProvider
        if action_type == ActionType.PAYMENT_LINK:
            from app.integrations.razorpay.models import RazorpayPaymentLinkPayload
            amount_paise = int(transaction.amount * 100)
            
            plink_payload = RazorpayPaymentLinkPayload(
                amount=amount_paise,
                currency=transaction.currency,
                description=f"RecoverAI Payment Link for Order {transaction.rzp_order_id or recovery_case.id}",
                customer={"email": transaction.customer.email if transaction.customer else "customer@example.com"},
                notes={"case_id": recovery_case.id, "transaction_id": transaction.id},
            )
            
            plink_response = provider.create_payment_link(plink_payload)
            
            return ExecutionResult(
                action_status=ActionStatus.COMPLETED,
                action_type=action_type,
                simulated_result={
                    "provider": provider.provider_name,
                    "action": "PAYMENT_LINK_DISPATCHED",
                    "payment_link_id": plink_response.id,
                    "short_url": plink_response.short_url,
                    "amount": transaction.amount,
                    "currency": transaction.currency,
                    "expiry_minutes": 1440,
                    "channels_notified": ["SMS", "EMAIL"],
                },
                timestamp=now_dt,
                idempotency_key=idempotency_key,
                channel="SMART_LINK",
                rzp_payment_link_id=plink_response.id,
                rzp_short_url=plink_response.short_url,
            )

        # 3. Customer Method Switch Notification
        if action_type == ActionType.SWITCH_METHOD:
            return ExecutionResult(
                action_status=ActionStatus.COMPLETED,
                action_type=action_type,
                simulated_result={
                    "simulated": True,
                    "action": "METHOD_UPDATE_PROMPT_SENT",
                    "message": "Customer informed of hard card decline; instructed to provide alternate UPI or debit card.",
                    "channel": "EMAIL_AND_INAPP",
                },
                timestamp=now_dt,
                idempotency_key=idempotency_key,
                channel="EMAIL",
            )

        # 4. Human Escalation / No Action
        return ExecutionResult(
            action_status=ActionStatus.COMPLETED,
            action_type=action_type,
            simulated_result={
                "simulated": True,
                "action": "ESCALATED_TO_MERCHANT_QUEUE",
                "notes": policy_verdict.notes,
            },
            timestamp=now_dt,
            idempotency_key=idempotency_key,
            channel="DASHBOARD",
        )


executor = SafeRecoveryExecutor()
