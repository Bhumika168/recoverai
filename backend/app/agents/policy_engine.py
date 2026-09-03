from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from app.models.transaction import Transaction
from app.models.recovery_case import RecoveryCase, CaseStatus
from app.models.recovery_action import RecoveryAction, ActionStatus
from app.agents.diagnostician import DiagnosisResult
from app.agents.decision_engine import DecisionRecommendation


@dataclass
class PolicyRuleEvaluation:
    rule_name: str
    passed: bool
    description: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyVerdict:
    approved: bool
    final_action: str  # delayed_retry, recovery_link, subscription_retry, customer_action_required, human_escalation, no_action
    requires_human_approval: bool
    case_status: CaseStatus
    evaluations: List[PolicyRuleEvaluation]
    rejection_reason: Optional[str] = None
    notes: str = ""


class PolicyEngine:
    """
    Deterministic Safety & Guardrail Engine.
    The LLM reasons and recommends; the Policy Engine controls and enforces non-negotiable hard bounds.
    """

    MAX_RETRY_ATTEMPTS = 3
    MIN_CONFIDENCE_THRESHOLD = 0.75
    HIGH_VALUE_THRESHOLD = 25000.0  # INR

    RETRY_ACTIONS = {"delayed_retry", "subscription_retry"}

    @classmethod
    def evaluate(
        cls,
        transaction: Transaction,
        recovery_case: RecoveryCase,
        diagnosis: DiagnosisResult,
        recommendation: DecisionRecommendation,
        existing_actions: Optional[List[RecoveryAction]] = None,
        max_retries: Optional[int] = None,
        high_value_limit: Optional[float] = None,
        min_confidence: Optional[float] = None,
    ) -> PolicyVerdict:
        max_retries_limit = max_retries or cls.MAX_RETRY_ATTEMPTS
        high_value_limit = high_value_limit or cls.HIGH_VALUE_THRESHOLD
        min_conf_threshold = min_confidence or cls.MIN_CONFIDENCE_THRESHOLD

        evaluations: List[PolicyRuleEvaluation] = []
        proposed_action = recommendation.action

        # -------------------------------------------------------------
        # Rule 1: Duplicate / Idempotency Protection
        # -------------------------------------------------------------
        has_duplicate = False
        if existing_actions:
            for act in existing_actions:
                if act.action_type.value.lower() == proposed_action.lower() and act.status in [
                    ActionStatus.SCHEDULED,
                    ActionStatus.EXECUTING,
                    ActionStatus.PENDING_APPROVAL,
                ]:
                    has_duplicate = True
                    break

        if has_duplicate:
            evaluations.append(
                PolicyRuleEvaluation(
                    rule_name="DUPLICATE_ACTION_PROTECTION",
                    passed=False,
                    description=f"Blocked duplicate action '{proposed_action}' already active or pending approval.",
                    details={"proposed_action": proposed_action},
                )
            )
            return PolicyVerdict(
                approved=False,
                final_action="no_action",
                requires_human_approval=False,
                case_status=recovery_case.status,
                evaluations=evaluations,
                rejection_reason="Duplicate action detected. An identical action is already in progress.",
                notes="Blocked duplicate execution to ensure idempotency.",
            )
        else:
            evaluations.append(
                PolicyRuleEvaluation(
                    rule_name="DUPLICATE_ACTION_PROTECTION",
                    passed=True,
                    description="No duplicate active action found.",
                )
            )

        # -------------------------------------------------------------
        # Rule 2: Hard Decline Suppression (Never Retry)
        # -------------------------------------------------------------
        if diagnosis.failure_category == "hard_decline":
            if proposed_action in cls.RETRY_ACTIONS:
                evaluations.append(
                    PolicyRuleEvaluation(
                        rule_name="NO_RETRY_AFTER_HARD_DECLINE",
                        passed=False,
                        description="Hard issuer decline detected. Automated retries strictly forbidden.",
                        details={"category": diagnosis.failure_category, "proposed": proposed_action},
                    )
                )
                # Overrule to customer action required or no action
                return PolicyVerdict(
                    approved=True,
                    final_action="customer_action_required",
                    requires_human_approval=False,
                    case_status=CaseStatus.UNRECOVERABLE,
                    evaluations=evaluations,
                    notes="Policy overruled retry recommendation to customer payment update due to hard decline.",
                )
            else:
                evaluations.append(
                    PolicyRuleEvaluation(
                        rule_name="NO_RETRY_AFTER_HARD_DECLINE",
                        passed=True,
                        description="Proposed action is not a card retry on hard decline.",
                    )
                )

        # -------------------------------------------------------------
        # Rule 3: Maximum Retry Attempt Limit
        # -------------------------------------------------------------
        current_retries = recovery_case.retry_count
        if proposed_action in cls.RETRY_ACTIONS:
            if current_retries >= max_retries_limit:
                evaluations.append(
                    PolicyRuleEvaluation(
                        rule_name="MAXIMUM_RETRY_LIMIT",
                        passed=False,
                        description=f"Attempt {current_retries} meets or exceeds maximum allowed retries ({max_retries_limit}).",
                        details={"current_retries": current_retries, "max_allowed": max_retries_limit},
                    )
                )
                return PolicyVerdict(
                    approved=False,
                    final_action="human_escalation",
                    requires_human_approval=True,
                    case_status=CaseStatus.ESCALATED,
                    evaluations=evaluations,
                    rejection_reason=f"Exceeded maximum automated retry count ({max_retries_limit}).",
                    notes="Automated retries halted. Escalated to merchant queue.",
                )
            else:
                evaluations.append(
                    PolicyRuleEvaluation(
                        rule_name="MAXIMUM_RETRY_LIMIT",
                        passed=True,
                        description=f"Retry attempt {current_retries + 1} is within allowed bound ({max_retries_limit}).",
                        details={"current_retries": current_retries, "max_allowed": max_retries_limit},
                    )
                )

        # -------------------------------------------------------------
        # Rule 4: Low Confidence Escalation
        # -------------------------------------------------------------
        if recommendation.confidence < min_conf_threshold:
            evaluations.append(
                PolicyRuleEvaluation(
                    rule_name="CONFIDENCE_THRESHOLD_CHECK",
                    passed=False,
                    description=f"AI diagnostic confidence {recommendation.confidence:.2f} is below minimum safe threshold {min_conf_threshold:.2f}.",
                    details={"confidence": recommendation.confidence, "threshold": min_conf_threshold},
                )
            )
            return PolicyVerdict(
                approved=False,
                final_action="human_escalation",
                requires_human_approval=True,
                case_status=CaseStatus.PENDING_APPROVAL,
                evaluations=evaluations,
                rejection_reason=f"Low confidence ({recommendation.confidence:.2f} < {min_conf_threshold:.2f}) requires human sign-off.",
                notes="Automated execution paused due to diagnostic ambiguity.",
            )
        else:
            evaluations.append(
                PolicyRuleEvaluation(
                    rule_name="CONFIDENCE_THRESHOLD_CHECK",
                    passed=True,
                    description=f"Confidence {recommendation.confidence:.2f} satisfies safe threshold {min_conf_threshold:.2f}.",
                )
            )

        # -------------------------------------------------------------
        # Rule 5: High-Value Uncertain Transaction Human Approval
        # -------------------------------------------------------------
        is_high_value = transaction.amount >= high_value_limit
        if is_high_value:
            evaluations.append(
                PolicyRuleEvaluation(
                    rule_name="HIGH_VALUE_TRANSACTION_GATE",
                    passed=False,
                    description=f"Transaction value ({transaction.amount:,.2f} {transaction.currency}) meets or exceeds high-value threshold ({high_value_limit:,.2f}). Human review mandatory.",
                    details={"amount": transaction.amount, "threshold": high_value_limit},
                )
            )
            return PolicyVerdict(
                approved=False,
                final_action=proposed_action,
                requires_human_approval=True,
                case_status=CaseStatus.PENDING_APPROVAL,
                evaluations=evaluations,
                rejection_reason=f"High transaction value (>= {high_value_limit:,.2f} INR) requires merchant confirmation.",
                notes="Action held in pending approval queue for one-click merchant clearance.",
            )
        else:
            evaluations.append(
                PolicyRuleEvaluation(
                    rule_name="HIGH_VALUE_TRANSACTION_GATE",
                    passed=True,
                    description=f"Transaction value ({transaction.amount:,.2f}) is within standard autonomous processing limit.",
                )
            )

        # All deterministic policies passed
        return PolicyVerdict(
            approved=True,
            final_action=proposed_action,
            requires_human_approval=False,
            case_status=CaseStatus.IN_PROGRESS,
            evaluations=evaluations,
            notes="All safety guardrails verified successfully. Automated execution cleared.",
        )


policy_engine = PolicyEngine()
