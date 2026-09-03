from typing import Any, Optional, Dict
from fastapi import HTTPException, status


class RecoverAIException(HTTPException):
    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str = "An unexpected error occurred",
        error_code: str = "INTERNAL_ERROR",
        extra: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code
        self.extra = extra or {}


class EntityNotFoundException(RecoverAIException):
    def __init__(self, entity_name: str, entity_id: Any):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity_name} with id '{entity_id}' was not found",
            error_code="NOT_FOUND",
            extra={"entity": entity_name, "id": str(entity_id)},
        )


class ValidationException(RecoverAIException):
    def __init__(self, detail: str, extra: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code="VALIDATION_ERROR",
            extra=extra,
        )


class PolicyViolationException(RecoverAIException):
    def __init__(self, rule_name: str, reason: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Safety Policy Violation [{rule_name}]: {reason}",
            error_code="POLICY_VIOLATION",
            extra={"rule": rule_name, "reason": reason},
        )
