import razorpay
from typing import Optional, Dict, Any
from app.config import settings
from app.logging_config import logger
from app.exceptions import RecoverAIException


def mask_secret(secret: Optional[str]) -> str:
    """Safely mask API secrets in logs."""
    if not secret:
        return "[NOT_SET]"
    if len(secret) <= 8:
        return "****"
    return f"{secret[:4]}...{secret[-4:]}"


class RazorpayClientWrapper:
    """
    Thread-safe official Razorpay SDK client wrapper.
    Ensures safe initialization, masked credential logging, and structured error handling.
    """

    def __init__(
        self,
        key_id: Optional[str] = None,
        key_secret: Optional[str] = None,
    ):
        self.key_id = key_id or settings.RAZORPAY_KEY_ID
        self.key_secret = key_secret or settings.RAZORPAY_KEY_SECRET
        self._client: Optional[razorpay.Client] = None

        if self.key_id and self.key_secret:
            logger.info(
                f"[RazorpayClient] Initializing Razorpay SDK with Key ID: {mask_secret(self.key_id)}"
            )
            self._client = razorpay.Client(auth=(self.key_id, self.key_secret))
        else:
            logger.warning("[RazorpayClient] Razorpay credentials not fully configured.")

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    @property
    def client(self) -> razorpay.Client:
        if not self._client:
            raise RecoverAIException(
                status_code=500,
                detail="Razorpay client is not configured with valid credentials",
                error_code="RAZORPAY_CONFIG_MISSING",
            )
        return self._client


# Global client instance
razorpay_client_wrapper = RazorpayClientWrapper()
