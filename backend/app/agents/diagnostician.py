from dataclasses import dataclass, field
from typing import List, Optional
from app.models.transaction import Transaction, PaymentMethod
from app.models.payment_attempt import PaymentAttempt


@dataclass
class DiagnosisResult:
    failure_category: str
    root_cause: str
    confidence: float  # 0.0 to 1.0
    risk_factors: List[str] = field(default_factory=list)
    suggested_focus: str = "GATEWAY"


class FailureDiagnostician:
    """
    Diagnostician Agent: Classifies transaction failures into specific categories:
    - temporary_failure
    - insufficient_funds
    - authentication_issue
    - expired_payment
    - checkout_abandonment
    - hard_decline
    - repeated_failure
    - unknown
    """

    HARD_DECLINE_CODES = {
        "CARD_STOLEN",
        "CARD_STOLEN_OR_LOST",
        "CARD_BLOCKED",
        "CARD_INACTIVE",
        "INVALID_CARD_NUMBER",
        "ACCOUNT_CLOSED",
        "FRAUD_SUSPECTED",
        "RESTRICTED_CARD",
        "CARD_RESTRICTED",
        "CARD_CANCELLED",
        "HARD_DECLINE",
        "DO_NOT_HONOR",
        "PICKUP_CARD",
    }

    TEMPORARY_FAILURE_CODES = {
        "BAD_REQUEST_PAYMENT_TIMED_OUT",
        "GATEWAY_ERROR",
        "ISSUER_DOWN",
        "NETWORK_ERROR",
        "NETWORK_TIMEOUT",
        "BANK_SYSTEM_ERROR",
        "BANK_TEMPORARY_OUTAGE",
        "PROCESSING_TIMEOUT",
        "SERVICE_UNAVAILABLE",
        "SWITCHING_SYSTEM_ERROR",
    }

    INSUFFICIENT_FUNDS_CODES = {
        "INSUFFICIENT_FUNDS",
        "NOT_ENOUGH_BALANCE",
        "LIMIT_EXCEEDED",
        "EXCEEDS_WITHDRAWAL_LIMIT",
        "INSUFFICIENT_CREDIT_LIMIT",
    }

    AUTH_ISSUE_CODES = {
        "AUTHENTICATION_FAILED",
        "OTP_EXPIRED",
        "3DS_TIMEOUT",
        "INCORRECT_OTP",
        "USER_DROPPED_OUT",
        "INCORRECT_PIN",
        "3D_SECURE_AUTH_FAILED",
    }

    EXPIRED_CODES = {
        "PAYMENT_EXPIRED",
        "EXPIRED_CARD",
        "CARD_INVALID_EXPIRY",
        "QR_EXPIRED",
        "SESSION_TIMEOUT",
        "LINK_EXPIRED",
        "ORDER_EXPIRED",
    }

    ABANDONMENT_CODES = {
        "CHECKOUT_ABANDONED",
        "CUSTOMER_ABORTED",
        "ABANDONED",
        "CART_ABANDONED",
        "WINDOW_CLOSED",
        "USER_CANCELLED",
    }

    @classmethod
    def diagnose(
        cls,
        transaction: Transaction,
        payment_attempts: Optional[List[PaymentAttempt]] = None,
        override_confidence: Optional[float] = None,
    ) -> DiagnosisResult:
        attempts_count = len(payment_attempts) if payment_attempts else 1
        
        # Check repeated failure condition
        if attempts_count >= 3:
            return DiagnosisResult(
                failure_category="repeated_failure",
                root_cause=f"Transaction has failed across {attempts_count} consecutive attempts. Systematic issue suspected.",
                confidence=override_confidence if override_confidence is not None else 0.95,
                risk_factors=[
                    f"Exceeded attempt threshold ({attempts_count} attempts)",
                    "Potential friction or payment method mismatch",
                ],
                suggested_focus="HUMAN_INTERVENTION",
            )

        code = (transaction.failure_code or "").upper().strip()
        reason = (transaction.failure_reason or "").lower()
        method = transaction.payment_method.value

        # 1. Hard Decline Check
        if code in cls.HARD_DECLINE_CODES or any(w in reason for w in ["stolen", "lost", "blocked card", "fraud", "closed account", "hard decline"]):
            return DiagnosisResult(
                failure_category="hard_decline",
                root_cause=f"Hard issuer decline ({code or 'DECLINED'}): Card/account is restricted or invalid.",
                confidence=override_confidence if override_confidence is not None else 0.99,
                risk_factors=[
                    "Issuer hard decline cannot be resolved via retry",
                    "Attempting further automated retries risks fraud penalties",
                ],
                suggested_focus="CUSTOMER_METHOD_SWITCH",
            )

        # 2. Temporary Failure Check
        if code in cls.TEMPORARY_FAILURE_CODES or any(w in reason for w in ["timeout", "timed out", "bank down", "network error", "gateway error", "unavailable"]):
            return DiagnosisResult(
                failure_category="temporary_failure",
                root_cause=f"Transient infrastructure issue: {transaction.failure_reason or 'Bank processing timeout'}",
                confidence=override_confidence if override_confidence is not None else 0.92,
                risk_factors=["Bank authorization latency", "Potential network congestion"],
                suggested_focus="DELAYED_RETRY",
            )

        # 3. Insufficient Funds
        if code in cls.INSUFFICIENT_FUNDS_CODES or any(w in reason for w in ["insufficient", "not enough balance", "limit exceeded"]):
            return DiagnosisResult(
                failure_category="insufficient_funds",
                root_cause=f"Insufficient balance or account limit exceeded on {method}.",
                confidence=override_confidence if override_confidence is not None else 0.88,
                risk_factors=["Account balance deficit", "High risk of immediate retry failure"],
                suggested_focus="SMART_NOTIFICATION_OR_ALTERNATIVE",
            )

        # 4. Authentication Issue
        if code in cls.AUTH_ISSUE_CODES or any(w in reason for w in ["otp", "auth", "3ds", "password", "pin", "verification"]):
            return DiagnosisResult(
                failure_category="authentication_issue",
                root_cause=f"Customer authentication failure (OTP/3DS) on {method}.",
                confidence=override_confidence if override_confidence is not None else 0.90,
                risk_factors=["User friction during 3DS challenge", "Device drop-off"],
                suggested_focus="PAYMENT_LINK_NOTIFICATION",
            )

        # 5. Expired Payment
        if code in cls.EXPIRED_CODES or any(w in reason for w in ["expired", "session time"]):
            return DiagnosisResult(
                failure_category="expired_payment",
                root_cause="Payment session or authorization window expired.",
                confidence=override_confidence if override_confidence is not None else 0.86,
                risk_factors=["Session latency", "Drop-off during gateway handoff"],
                suggested_focus="FRESH_PAYMENT_LINK",
            )

        # 6. Checkout Abandonment
        if code in cls.ABANDONMENT_CODES or transaction.status.value == "ABANDONED" or any(w in reason for w in ["abandoned", "cancelled by user"]):
            return DiagnosisResult(
                failure_category="checkout_abandonment",
                root_cause="Customer abandoned checkout flow prior to completing authentication.",
                confidence=override_confidence if override_confidence is not None else 0.85,
                risk_factors=["Cart intent at risk", "Drop-off prior to capture"],
                suggested_focus="RECOVERY_PAYMENT_LINK",
            )

        # 7. Unknown / Fallback
        return DiagnosisResult(
            failure_category="unknown",
            root_cause=f"Unclassified failure response: {transaction.failure_reason or code or 'Unknown error'}",
            confidence=override_confidence if override_confidence is not None else 0.55,
            risk_factors=["Unrecognized error pattern", "Requires heuristic or manual triage"],
            suggested_focus="ESCALATION_OR_LINK",
        )


diagnostician = FailureDiagnostician()
