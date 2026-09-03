from dataclasses import dataclass
from typing import Optional
from app.models.transaction import Transaction, TransactionStatus


@dataclass
class DetectionResult:
    is_recoverable_candidate: bool
    priority: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    reason: str
    amount_at_risk: float


class RiskDetector:
    """
    Detector Agent: Evaluates whether a transaction represents an active
    revenue risk that is viable for recovery workflows.
    """

    @staticmethod
    def detect(transaction: Transaction) -> DetectionResult:
        # Non-failed or already successfully captured transactions are not recovery candidates
        if transaction.status in [TransactionStatus.CAPTURED, TransactionStatus.RECOVERED]:
            return DetectionResult(
                is_recoverable_candidate=False,
                priority="LOW",
                reason=f"Transaction is already in successful status: {transaction.status.value}",
                amount_at_risk=0.0,
            )

        if transaction.status not in [TransactionStatus.FAILED, TransactionStatus.ABANDONED]:
            return DetectionResult(
                is_recoverable_candidate=False,
                priority="LOW",
                reason=f"Transaction status {transaction.status.value} does not warrant recovery triage",
                amount_at_risk=0.0,
            )

        # Determine priority based on amount
        amount = transaction.amount
        if amount >= 50000.0:
            priority = "CRITICAL"
        elif amount >= 20000.0:
            priority = "HIGH"
        elif amount >= 5000.0:
            priority = "MEDIUM"
        else:
            priority = "LOW"

        return DetectionResult(
            is_recoverable_candidate=True,
            priority=priority,
            reason=f"Failed transaction ({transaction.failure_code or 'UNKNOWN'}) representing {amount} {transaction.currency} at risk",
            amount_at_risk=amount,
        )


detector = RiskDetector()
