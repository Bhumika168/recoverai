from dataclasses import dataclass, field
from typing import List, Optional
from app.models.transaction import Transaction, PaymentMethod
from app.agents.diagnostician import DiagnosisResult


@dataclass
class DecisionRecommendation:
    action: str  # delayed_retry, recovery_link, subscription_retry, customer_action_required, human_escalation, no_action
    confidence: float
    reason: str
    expected_recovery_probability: float
    recommended_delay_minutes: int = 0
    recommended_channel: str = "GATEWAY"
    risk_factors: List[str] = field(default_factory=list)


class DecisionEngine:
    """
    Decision Engine Agent: Evaluates the diagnosis, transaction metadata,
    and customer context to recommend the optimal revenue recovery action.
    """

    @staticmethod
    def decide(
        transaction: Transaction,
        diagnosis: DiagnosisResult,
        override_confidence: Optional[float] = None,
    ) -> DecisionRecommendation:
        category = diagnosis.failure_category
        confidence = override_confidence if override_confidence is not None else diagnosis.confidence
        is_subscription = transaction.payment_method == PaymentMethod.SUBSCRIPTION or (
            transaction.extra_metadata and transaction.extra_metadata.get("is_subscription")
        )

        # 1. Hard Decline: Never retry
        if category == "hard_decline":
            return DecisionRecommendation(
                action="customer_action_required",
                confidence=confidence,
                reason="Hard issuer decline detected. Automated retries are ineffective. Directing customer to update payment method.",
                expected_recovery_probability=0.35,
                recommended_delay_minutes=0,
                recommended_channel="EMAIL",
                risk_factors=diagnosis.risk_factors + ["Zero probability on card retry"],
            )

        # 2. Repeated Failure (3+ attempts): Escalate to human review
        if category == "repeated_failure":
            return DecisionRecommendation(
                action="human_escalation",
                confidence=confidence,
                reason="Transaction exceeded automated retry limit. Escalating to merchant support queue to prevent customer frustration.",
                expected_recovery_probability=0.40,
                recommended_delay_minutes=0,
                recommended_channel="DASHBOARD",
                risk_factors=diagnosis.risk_factors + ["Retry cap reached"],
            )

        # 3. Temporary Failure (Bank timeout / gateway glitch)
        if category == "temporary_failure":
            if is_subscription:
                return DecisionRecommendation(
                    action="subscription_retry",
                    confidence=confidence,
                    reason="Transient bank processing error on recurring charge. Scheduling smart retry window.",
                    expected_recovery_probability=0.88,
                    recommended_delay_minutes=30,
                    recommended_channel="GATEWAY",
                    risk_factors=diagnosis.risk_factors,
                )
            return DecisionRecommendation(
                action="delayed_retry",
                confidence=confidence,
                reason="Transient gateway/issuer timeout. Scheduled delayed retry after bank queue cooldown.",
                expected_recovery_probability=0.85,
                recommended_delay_minutes=15,
                recommended_channel="GATEWAY",
                risk_factors=diagnosis.risk_factors,
            )

        # 4. Checkout Abandonment or Authentication Issue
        if category in ["checkout_abandonment", "authentication_issue", "expired_payment"]:
            return DecisionRecommendation(
                action="recovery_link",
                confidence=confidence,
                reason="User drop-off or auth friction. Dispatched bounded personalized recovery payment link.",
                expected_recovery_probability=0.72,
                recommended_delay_minutes=5,
                recommended_channel="SMS_OR_WHATSAPP",
                risk_factors=diagnosis.risk_factors,
            )

        # 5. Insufficient Funds
        if category == "insufficient_funds":
            if is_subscription:
                return DecisionRecommendation(
                    action="subscription_retry",
                    confidence=confidence,
                    reason="Insufficient funds on subscription charge. Scheduling retry aligned with standard salary/replenishment cycle.",
                    expected_recovery_probability=0.65,
                    recommended_delay_minutes=1440,  # 24 hours
                    recommended_channel="GATEWAY",
                    risk_factors=diagnosis.risk_factors,
                )
            return DecisionRecommendation(
                action="recovery_link",
                confidence=confidence,
                reason="Insufficient balance on selected method. Providing alternative payment link with UPI/Card options.",
                expected_recovery_probability=0.60,
                recommended_delay_minutes=30,
                recommended_channel="SMS",
                risk_factors=diagnosis.risk_factors,
            )

        # 6. Low Confidence or Unknown Category
        if confidence < 0.75 or category == "unknown":
            return DecisionRecommendation(
                action="human_escalation",
                confidence=confidence,
                reason=f"Unclear failure pattern (confidence {confidence:.2f} < 0.75). Route for merchant manual review.",
                expected_recovery_probability=0.30,
                recommended_delay_minutes=0,
                recommended_channel="DASHBOARD",
                risk_factors=diagnosis.risk_factors + ["Low diagnostic confidence"],
            )

        return DecisionRecommendation(
            action="no_action",
            confidence=confidence,
            reason="No viable automated recovery pattern identified.",
            expected_recovery_probability=0.10,
            recommended_delay_minutes=0,
            recommended_channel="DASHBOARD",
            risk_factors=diagnosis.risk_factors,
        )


decision_engine = DecisionEngine()
