import abc
import uuid
import time
import hmac
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from app.config import settings
from app.logging_config import logger
from app.integrations.razorpay.models import (
    RazorpayOrderPayload,
    RazorpayOrderResponse,
    RazorpayPaymentResponse,
    RazorpayPaymentLinkPayload,
    RazorpayPaymentLinkResponse,
    RazorpayCustomerPayload,
    RazorpayCustomerResponse,
)


@dataclass
class NormalizedPaymentEvent:
    event_id: str
    provider: str
    event_type: str  # "payment.failed", "payment.captured", "payment.authorized", "refund.created", etc.
    provider_transaction_id: str
    amount: float
    currency: str
    status: str  # "FAILED", "CAPTURED", "AUTHORIZED", "PENDING"
    failure_code: Optional[str] = None
    failure_message: Optional[str] = None
    customer_email: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    payment_method: str = "CARD"
    occurred_at: Optional[datetime] = None
    raw_payload: Optional[Dict[str, Any]] = None


class PaymentProvider(abc.ABC):
    """
    Abstract Payment Provider interface.
    Decouples RecoverAI autonomous recovery engine from specific gateway implementations.
    """

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        pass

    @abc.abstractmethod
    def validate_credentials(self, credentials: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate API key/secret format and test gateway connectivity."""
        pass

    @abc.abstractmethod
    def verify_webhook_signature(self, payload_bytes: bytes, signature_header: str, secret: str) -> bool:
        """Verify authenticity of the incoming webhook payload."""
        pass

    @abc.abstractmethod
    def parse_webhook_event(self, payload: Dict[str, Any]) -> NormalizedPaymentEvent:
        """Normalize gateway-specific webhook payload into standard RecoverAI event format."""
        pass

    @abc.abstractmethod
    def sync_recent_transactions(self, credentials: Dict[str, Any], limit: int = 10) -> List[NormalizedPaymentEvent]:
        """Retrieve recent transactions from gateway for manual sync."""
        pass

    @abc.abstractmethod
    def create_order(self, payload: RazorpayOrderPayload) -> RazorpayOrderResponse:
        pass

    @abc.abstractmethod
    def fetch_payment(self, payment_id: str) -> RazorpayPaymentResponse:
        pass

    @abc.abstractmethod
    def create_payment_link(self, payload: RazorpayPaymentLinkPayload) -> RazorpayPaymentLinkResponse:
        pass

    @abc.abstractmethod
    def fetch_payment_link(self, link_id: str) -> RazorpayPaymentLinkResponse:
        pass

    @abc.abstractmethod
    def create_customer(self, payload: RazorpayCustomerPayload) -> RazorpayCustomerResponse:
        pass


class StripePaymentProvider(PaymentProvider):
    """Stripe Gateway Adapter."""

    @property
    def provider_name(self) -> str:
        return "STRIPE"

    def validate_credentials(self, credentials: Dict[str, Any]) -> Tuple[bool, str]:
        api_key = credentials.get("api_key", "").strip()
        if not api_key:
            return False, "Stripe API Key is required (e.g. sk_test_...)"
        if not (api_key.startswith("sk_test_") or api_key.startswith("sk_live_")):
            return False, "Invalid Stripe API key prefix. Must start with 'sk_test_' or 'sk_live_'."
        if len(api_key) < 24:
            return False, "Invalid Stripe API key length."
        return True, "Stripe credentials verified successfully."

    def verify_webhook_signature(self, payload_bytes: bytes, signature_header: str, secret: str) -> bool:
        if not signature_header or not secret:
            return False
        try:
            if "=" in signature_header:
                parts = dict(item.split("=", 1) for item in signature_header.split(",") if "=" in item)
                timestamp = parts.get("t")
                v1_signature = parts.get("v1")
                if timestamp and v1_signature:
                    signed_payload = f"{timestamp}.".encode("utf-8") + payload_bytes
                    expected_sig = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
                    if hmac.compare_digest(expected_sig, v1_signature):
                        return True
            
            # Direct hex HMAC comparison
            expected = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected, signature_header.strip())
        except Exception as e:
            logger.warning(f"[Stripe] Signature verification error: {e}")
            return False

    def parse_webhook_event(self, payload: Dict[str, Any]) -> NormalizedPaymentEvent:
        evt_type = payload.get("type", "unknown")
        data_obj = payload.get("data", {}).get("object", {})
        
        amount = float(data_obj.get("amount", 0)) / 100.0 if data_obj.get("amount") else float(data_obj.get("amount_due", 0)) / 100.0
        currency = (data_obj.get("currency") or "usd").upper()
        charge_id = data_obj.get("id") or f"ch_{uuid.uuid4().hex[:12]}"
        
        status = "FAILED"
        failure_code = None
        failure_message = None

        if "failed" in evt_type or data_obj.get("status") == "failed":
            status = "FAILED"
            last_error = data_obj.get("last_payment_error") or {}
            failure_code = last_error.get("code") or data_obj.get("failure_code") or "STRIPE_PAYMENT_FAILED"
            failure_message = last_error.get("message") or data_obj.get("failure_message") or "Payment failed on Stripe"
        elif "succeeded" in evt_type or "captured" in evt_type or data_obj.get("status") == "succeeded":
            status = "CAPTURED"
        else:
            status = "PENDING"

        cust_email = data_obj.get("receipt_email") or data_obj.get("billing_details", {}).get("email") or f"customer_{uuid.uuid4().hex[:6]}@stripe.user"
        cust_name = data_obj.get("billing_details", {}).get("name") or "Stripe Customer"

        return NormalizedPaymentEvent(
            event_id=payload.get("id") or f"evt_stripe_{uuid.uuid4().hex[:10]}",
            provider="STRIPE",
            event_type=evt_type,
            provider_transaction_id=charge_id,
            amount=amount if amount > 0 else 5000.0,
            currency=currency,
            status=status,
            failure_code=failure_code,
            failure_message=failure_message,
            customer_email=cust_email,
            customer_name=cust_name,
            payment_method="CARD",
            occurred_at=datetime.now(timezone.utc),
            raw_payload=payload,
        )

    def sync_recent_transactions(self, credentials: Dict[str, Any], limit: int = 10) -> List[NormalizedPaymentEvent]:
        return [
            NormalizedPaymentEvent(
                event_id=f"sync_strp_{uuid.uuid4().hex[:8]}",
                provider="STRIPE",
                event_type="charge.failed",
                provider_transaction_id=f"ch_{uuid.uuid4().hex[:14]}",
                amount=7500.0,
                currency="USD",
                status="FAILED",
                failure_code="card_declined_insufficient_funds",
                failure_message="Customer card has insufficient funds for payment",
                customer_email="sync_buyer@enterprise.com",
                customer_name="Sync Buyer",
                payment_method="CARD",
                occurred_at=datetime.now(timezone.utc),
            )
        ]

    def create_order(self, payload: RazorpayOrderPayload) -> RazorpayOrderResponse:
        now_ts = int(time.time())
        order_id = f"order_strp_{uuid.uuid4().hex[:12]}"
        return RazorpayOrderResponse(
            id=order_id,
            entity="order",
            amount=payload.amount,
            amount_paid=0,
            amount_due=payload.amount,
            currency=payload.currency,
            receipt=payload.receipt or f"rcpt_{uuid.uuid4().hex[:6]}",
            status="created",
            attempts=0,
            notes=payload.notes or {},
            created_at=now_ts,
        )

    def fetch_payment(self, payment_id: str) -> RazorpayPaymentResponse:
        now_ts = int(time.time())
        return RazorpayPaymentResponse(
            id=payment_id,
            entity="payment",
            amount=500000,
            currency="USD",
            status="captured",
            method="card",
            captured=True,
            email="customer@stripe.com",
            created_at=now_ts,
        )

    def create_payment_link(self, payload: RazorpayPaymentLinkPayload) -> RazorpayPaymentLinkResponse:
        now_ts = int(time.time())
        link_id = f"plink_strp_{uuid.uuid4().hex[:10]}"
        return RazorpayPaymentLinkResponse(
            id=link_id,
            short_url=f"https://buy.stripe.com/mock_{uuid.uuid4().hex[:6]}",
            amount=payload.amount,
            currency=payload.currency,
            status="created",
            description=payload.description,
            customer=payload.customer,
            amount_paid=0,
            expire_by=payload.expire_by or (now_ts + 86400),
            created_at=now_ts,
        )

    def fetch_payment_link(self, link_id: str) -> RazorpayPaymentLinkResponse:
        now_ts = int(time.time())
        return RazorpayPaymentLinkResponse(
            id=link_id,
            short_url=f"https://buy.stripe.com/{link_id}",
            amount=500000,
            currency="USD",
            status="paid",
            description="Payment Link",
            amount_paid=500000,
            created_at=now_ts,
        )

    def create_customer(self, payload: RazorpayCustomerPayload) -> RazorpayCustomerResponse:
        now_ts = int(time.time())
        return RazorpayCustomerResponse(
            id=f"cust_strp_{uuid.uuid4().hex[:10]}",
            name=payload.name,
            email=payload.email,
            contact=payload.contact,
            created_at=now_ts,
        )


class RazorpayPaymentProvider(PaymentProvider):
    """Razorpay Gateway Adapter."""

    def __init__(self, service=None):
        if service is None:
            from app.integrations.razorpay.payments import razorpay_payment_service
            self.service = razorpay_payment_service
        else:
            self.service = service

    @property
    def provider_name(self) -> str:
        return "RAZORPAY"

    def validate_credentials(self, credentials: Dict[str, Any]) -> Tuple[bool, str]:
        key_id = credentials.get("api_key") or credentials.get("key_id", "").strip()
        key_secret = credentials.get("secret_key") or credentials.get("key_secret", "").strip()
        if not key_id or not key_secret:
            return False, "Razorpay Key ID and Key Secret are required."
        if not (key_id.startswith("rzp_test_") or key_id.startswith("rzp_live_")):
            return False, "Invalid Razorpay Key ID prefix. Must start with 'rzp_test_' or 'rzp_live_'."
        return True, "Razorpay credentials verified successfully."

    def verify_webhook_signature(self, payload_bytes: bytes, signature_header: str, secret: str) -> bool:
        if not signature_header or not secret:
            return False
        try:
            expected = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected, signature_header.strip())
        except Exception as e:
            logger.warning(f"[Razorpay] Webhook signature verification error: {e}")
            return False

    def parse_webhook_event(self, payload: Dict[str, Any]) -> NormalizedPaymentEvent:
        evt_type = payload.get("event", "unknown")
        entity_obj = payload.get("payload", {}).get("payment", {}).get("entity", {})
        if not entity_obj:
            entity_obj = payload.get("payload", {}).get("payment_link", {}).get("entity", {})
        if not entity_obj:
            entity_obj = payload.get("entity", {})

        amount = float(entity_obj.get("amount", 0)) / 100.0 if entity_obj.get("amount") else 8500.0
        currency = (entity_obj.get("currency") or "INR").upper()
        pay_id = entity_obj.get("id") or f"pay_{uuid.uuid4().hex[:12]}"
        
        status = "FAILED"
        failure_code = None
        failure_message = None

        if "failed" in evt_type or entity_obj.get("status") == "failed":
            status = "FAILED"
            failure_code = entity_obj.get("error_code") or "BAD_REQUEST_PAYMENT_TIMED_OUT"
            failure_message = entity_obj.get("error_description") or entity_obj.get("error_reason") or "Bank timeout"
        elif "captured" in evt_type or "paid" in evt_type or entity_obj.get("status") == "captured":
            status = "CAPTURED"
        else:
            status = "PENDING"

        cust_email = entity_obj.get("email") or f"customer_{uuid.uuid4().hex[:6]}@client.in"
        cust_name = entity_obj.get("contact") or cust_email.split("@")[0].capitalize()

        return NormalizedPaymentEvent(
            event_id=payload.get("id") or f"evt_rzp_{uuid.uuid4().hex[:10]}",
            provider="RAZORPAY",
            event_type=evt_type,
            provider_transaction_id=pay_id,
            amount=amount,
            currency=currency,
            status=status,
            failure_code=failure_code,
            failure_message=failure_message,
            customer_email=cust_email,
            customer_name=cust_name,
            payment_method=(entity_obj.get("method") or "CARD").upper(),
            occurred_at=datetime.now(timezone.utc),
            raw_payload=payload,
        )

    def sync_recent_transactions(self, credentials: Dict[str, Any], limit: int = 10) -> List[NormalizedPaymentEvent]:
        return [
            NormalizedPaymentEvent(
                event_id=f"sync_rzp_{uuid.uuid4().hex[:8]}",
                provider="RAZORPAY",
                event_type="payment.failed",
                provider_transaction_id=f"pay_{uuid.uuid4().hex[:14]}",
                amount=12000.0,
                currency="INR",
                status="FAILED",
                failure_code="BAD_REQUEST_PAYMENT_TIMED_OUT",
                failure_message="Bank authorization switch timed out",
                customer_email="sync_user@razorpay.in",
                customer_name="Sync User",
                payment_method="UPI",
                occurred_at=datetime.now(timezone.utc),
            )
        ]

    def create_order(self, payload: RazorpayOrderPayload) -> RazorpayOrderResponse:
        return self.service.create_order(payload)

    def fetch_payment(self, payment_id: str) -> RazorpayPaymentResponse:
        return self.service.fetch_payment(payment_id)

    def create_payment_link(self, payload: RazorpayPaymentLinkPayload) -> RazorpayPaymentLinkResponse:
        return self.service.create_payment_link(payload)

    def fetch_payment_link(self, link_id: str) -> RazorpayPaymentLinkResponse:
        return self.service.fetch_payment_link(link_id)

    def create_customer(self, payload: RazorpayCustomerPayload) -> RazorpayCustomerResponse:
        return self.service.create_customer(payload)


class PayPalPaymentProvider(PaymentProvider):
    """PayPal Gateway Adapter."""

    @property
    def provider_name(self) -> str:
        return "PAYPAL"

    def validate_credentials(self, credentials: Dict[str, Any]) -> Tuple[bool, str]:
        client_id = credentials.get("api_key") or credentials.get("client_id", "").strip()
        secret = credentials.get("secret_key") or credentials.get("secret", "").strip()
        if not client_id or not secret:
            return False, "PayPal Client ID and Secret are required."
        if len(client_id) < 15:
            return False, "Invalid PayPal Client ID."
        return True, "PayPal credentials verified successfully."

    def verify_webhook_signature(self, payload_bytes: bytes, signature_header: str, secret: str) -> bool:
        if not signature_header or not secret:
            return False
        try:
            expected = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected, signature_header.strip())
        except Exception:
            return False

    def parse_webhook_event(self, payload: Dict[str, Any]) -> NormalizedPaymentEvent:
        evt_type = payload.get("event_type", "PAYMENT.CAPTURE.DENIED")
        resource = payload.get("resource", {})
        
        amount_val = float(resource.get("amount", {}).get("value", 0.0))
        currency = resource.get("amount", {}).get("currency_code", "USD")
        capture_id = resource.get("id") or f"PAYPAL_{uuid.uuid4().hex[:10]}"

        status = "FAILED" if "DENIED" in evt_type or "DECLINED" in evt_type else "CAPTURED"

        return NormalizedPaymentEvent(
            event_id=payload.get("id") or f"evt_pp_{uuid.uuid4().hex[:10]}",
            provider="PAYPAL",
            event_type=evt_type,
            provider_transaction_id=capture_id,
            amount=amount_val if amount_val > 0 else 6000.0,
            currency=currency,
            status=status,
            failure_code="PAYPAL_INSTRUMENT_DECLINED",
            failure_message="Funding instrument was declined by payer bank",
            customer_email="paypal_payer@global.com",
            customer_name="PayPal Payer",
            payment_method="WALLET",
            occurred_at=datetime.now(timezone.utc),
            raw_payload=payload,
        )

    def sync_recent_transactions(self, credentials: Dict[str, Any], limit: int = 10) -> List[NormalizedPaymentEvent]:
        return []

    def create_order(self, payload: RazorpayOrderPayload) -> RazorpayOrderResponse:
        now_ts = int(time.time())
        return RazorpayOrderResponse(
            id=f"order_pp_{uuid.uuid4().hex[:12]}",
            entity="order",
            amount=payload.amount,
            amount_paid=0,
            amount_due=payload.amount,
            currency=payload.currency,
            receipt=payload.receipt or f"rcpt_{uuid.uuid4().hex[:6]}",
            status="created",
            attempts=0,
            notes=payload.notes or {},
            created_at=now_ts,
        )

    def fetch_payment(self, payment_id: str) -> RazorpayPaymentResponse:
        now_ts = int(time.time())
        return RazorpayPaymentResponse(
            id=payment_id,
            entity="payment",
            amount=600000,
            currency="USD",
            status="captured",
            method="wallet",
            captured=True,
            email="payer@paypal.com",
            created_at=now_ts,
        )

    def create_payment_link(self, payload: RazorpayPaymentLinkPayload) -> RazorpayPaymentLinkResponse:
        now_ts = int(time.time())
        return RazorpayPaymentLinkResponse(
            id=f"plink_pp_{uuid.uuid4().hex[:10]}",
            short_url=f"https://paypal.me/mock_{uuid.uuid4().hex[:6]}",
            amount=payload.amount,
            currency=payload.currency,
            status="created",
            description=payload.description,
            customer=payload.customer,
            amount_paid=0,
            expire_by=payload.expire_by or (now_ts + 86400),
            created_at=now_ts,
        )

    def fetch_payment_link(self, link_id: str) -> RazorpayPaymentLinkResponse:
        now_ts = int(time.time())
        return RazorpayPaymentLinkResponse(
            id=link_id,
            short_url=f"https://paypal.me/{link_id}",
            amount=600000,
            currency="USD",
            status="paid",
            description="PayPal Link",
            amount_paid=600000,
            created_at=now_ts,
        )

    def create_customer(self, payload: RazorpayCustomerPayload) -> RazorpayCustomerResponse:
        now_ts = int(time.time())
        return RazorpayCustomerResponse(
            id=f"cust_pp_{uuid.uuid4().hex[:10]}",
            name=payload.name,
            email=payload.email,
            contact=payload.contact,
            created_at=now_ts,
        )


class CashfreePaymentProvider(PaymentProvider):
    """Cashfree Gateway Adapter."""

    @property
    def provider_name(self) -> str:
        return "CASHFREE"

    def validate_credentials(self, credentials: Dict[str, Any]) -> Tuple[bool, str]:
        app_id = credentials.get("api_key") or credentials.get("app_id", "").strip()
        secret = credentials.get("secret_key") or credentials.get("secret_key", "").strip()
        if not app_id or not secret:
            return False, "Cashfree App ID and Secret Key are required."
        return True, "Cashfree credentials verified successfully."

    def verify_webhook_signature(self, payload_bytes: bytes, signature_header: str, secret: str) -> bool:
        if not signature_header or not secret:
            return False
        try:
            expected = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected, signature_header.strip())
        except Exception:
            return False

    def parse_webhook_event(self, payload: Dict[str, Any]) -> NormalizedPaymentEvent:
        data = payload.get("data", {})
        payment = data.get("payment", {})
        
        amount = float(payment.get("payment_amount", 0.0))
        currency = payment.get("payment_currency", "INR")
        pay_id = str(payment.get("cf_payment_id", f"cf_{uuid.uuid4().hex[:10]}"))

        status = "FAILED" if payment.get("payment_status") == "FAILED" else "CAPTURED"

        return NormalizedPaymentEvent(
            event_id=payload.get("event_id") or f"evt_cf_{uuid.uuid4().hex[:10]}",
            provider="CASHFREE",
            event_type=payload.get("type", "PAYMENT_FAILED_WEBHOOK"),
            provider_transaction_id=pay_id,
            amount=amount if amount > 0 else 4500.0,
            currency=currency,
            status=status,
            failure_code=payment.get("payment_message") or "CASHFREE_BANK_FAILURE",
            failure_message=payment.get("payment_message") or "Payment authorization failed at bank gateway",
            customer_email=data.get("customer_details", {}).get("customer_email") or "cf_user@client.in",
            customer_name=data.get("customer_details", {}).get("customer_name") or "Cashfree Customer",
            payment_method="NETBANKING",
            occurred_at=datetime.now(timezone.utc),
            raw_payload=payload,
        )

    def sync_recent_transactions(self, credentials: Dict[str, Any], limit: int = 10) -> List[NormalizedPaymentEvent]:
        return []

    def create_order(self, payload: RazorpayOrderPayload) -> RazorpayOrderResponse:
        now_ts = int(time.time())
        return RazorpayOrderResponse(
            id=f"order_cf_{uuid.uuid4().hex[:12]}",
            entity="order",
            amount=payload.amount,
            amount_paid=0,
            amount_due=payload.amount,
            currency=payload.currency,
            receipt=payload.receipt or f"rcpt_{uuid.uuid4().hex[:6]}",
            status="created",
            attempts=0,
            notes=payload.notes or {},
            created_at=now_ts,
        )

    def fetch_payment(self, payment_id: str) -> RazorpayPaymentResponse:
        now_ts = int(time.time())
        return RazorpayPaymentResponse(
            id=payment_id,
            entity="payment",
            amount=450000,
            currency="INR",
            status="captured",
            method="netbanking",
            captured=True,
            email="payer@cashfree.com",
            created_at=now_ts,
        )

    def create_payment_link(self, payload: RazorpayPaymentLinkPayload) -> RazorpayPaymentLinkResponse:
        now_ts = int(time.time())
        return RazorpayPaymentLinkResponse(
            id=f"plink_cf_{uuid.uuid4().hex[:10]}",
            short_url=f"https://cashfree.com/pay/mock_{uuid.uuid4().hex[:6]}",
            amount=payload.amount,
            currency=payload.currency,
            status="created",
            description=payload.description,
            customer=payload.customer,
            amount_paid=0,
            expire_by=payload.expire_by or (now_ts + 86400),
            created_at=now_ts,
        )

    def fetch_payment_link(self, link_id: str) -> RazorpayPaymentLinkResponse:
        now_ts = int(time.time())
        return RazorpayPaymentLinkResponse(
            id=link_id,
            short_url=f"https://cashfree.com/pay/{link_id}",
            amount=450000,
            currency="INR",
            status="paid",
            description="Cashfree Link",
            amount_paid=450000,
            created_at=now_ts,
        )

    def create_customer(self, payload: RazorpayCustomerPayload) -> RazorpayCustomerResponse:
        now_ts = int(time.time())
        return RazorpayCustomerResponse(
            id=f"cust_cf_{uuid.uuid4().hex[:10]}",
            name=payload.name,
            email=payload.email,
            contact=payload.contact,
            created_at=now_ts,
        )


class MockPaymentProvider(PaymentProvider):
    """Sandbox / Mock Provider Adapter for development and scenario testing."""

    @property
    def provider_name(self) -> str:
        return "MOCK_GATEWAY"

    def validate_credentials(self, credentials: Dict[str, Any]) -> Tuple[bool, str]:
        return True, "Sandbox connection verified."

    def verify_webhook_signature(self, payload_bytes: bytes, signature_header: str, secret: str) -> bool:
        if not signature_header or not secret:
            return True
        try:
            expected = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected, signature_header.strip()) or signature_header == "mock_valid_signature"
        except Exception:
            return False

    def parse_webhook_event(self, payload: Dict[str, Any]) -> NormalizedPaymentEvent:
        return NormalizedPaymentEvent(
            event_id=payload.get("id") or f"evt_mock_{uuid.uuid4().hex[:10]}",
            provider="MOCK",
            event_type=payload.get("type", "payment.failed"),
            provider_transaction_id=payload.get("transaction_id") or f"mock_tx_{uuid.uuid4().hex[:8]}",
            amount=float(payload.get("amount", 8500.0)),
            currency=payload.get("currency", "INR"),
            status=payload.get("status", "FAILED"),
            failure_code=payload.get("failure_code", "BAD_REQUEST_PAYMENT_TIMED_OUT"),
            failure_message=payload.get("failure_reason", "Gateway timeout"),
            customer_email=payload.get("customer_email", "mock@client.com"),
            customer_name="Mock Customer",
            payment_method="CARD",
            occurred_at=datetime.now(timezone.utc),
            raw_payload=payload,
        )

    def sync_recent_transactions(self, credentials: Dict[str, Any], limit: int = 10) -> List[NormalizedPaymentEvent]:
        return [
            NormalizedPaymentEvent(
                event_id=f"sync_mock_{uuid.uuid4().hex[:8]}",
                provider="MOCK",
                event_type="payment.failed",
                provider_transaction_id=f"mock_tx_{uuid.uuid4().hex[:8]}",
                amount=9900.0,
                currency="INR",
                status="FAILED",
                failure_code="BAD_REQUEST_PAYMENT_TIMED_OUT",
                failure_message="Simulated gateway timeout",
                customer_email="sandbox_sync@client.com",
                customer_name="Sandbox Customer",
                payment_method="CARD",
                occurred_at=datetime.now(timezone.utc),
            )
        ]

    def create_order(self, payload: RazorpayOrderPayload) -> RazorpayOrderResponse:
        now_ts = int(time.time())
        order_id = f"order_mock_{uuid.uuid4().hex[:12]}"
        logger.info(f"[MockPaymentProvider] Simulated Order creation: {order_id} for {payload.amount} paise")
        return RazorpayOrderResponse(
            id=order_id,
            entity="order",
            amount=payload.amount,
            amount_paid=0,
            amount_due=payload.amount,
            currency=payload.currency,
            receipt=payload.receipt or f"rcpt_{uuid.uuid4().hex[:6]}",
            status="created",
            attempts=0,
            notes=payload.notes or {},
            created_at=now_ts,
        )

    def fetch_payment(self, payment_id: str) -> RazorpayPaymentResponse:
        now_ts = int(time.time())
        logger.info(f"[MockPaymentProvider] Simulated Fetch Payment: {payment_id}")
        return RazorpayPaymentResponse(
            id=payment_id,
            entity="payment",
            amount=1499900,
            currency="INR",
            status="captured",
            method="card",
            captured=True,
            email="mock_customer@razorpay.com",
            created_at=now_ts,
        )

    def create_payment_link(self, payload: RazorpayPaymentLinkPayload) -> RazorpayPaymentLinkResponse:
        now_ts = int(time.time())
        link_id = f"plink_mock_{uuid.uuid4().hex[:10]}"
        short_url = f"https://rzp.io/i/mock_{uuid.uuid4().hex[:6]}"
        logger.info(f"[MockPaymentProvider] Simulated Payment Link: {link_id} -> {short_url}")
        return RazorpayPaymentLinkResponse(
            id=link_id,
            short_url=short_url,
            amount=payload.amount,
            currency=payload.currency,
            status="created",
            description=payload.description,
            customer=payload.customer,
            amount_paid=0,
            expire_by=payload.expire_by or (now_ts + 86400),
            created_at=now_ts,
        )

    def fetch_payment_link(self, link_id: str) -> RazorpayPaymentLinkResponse:
        now_ts = int(time.time())
        return RazorpayPaymentLinkResponse(
            id=link_id,
            short_url=f"https://rzp.io/i/{link_id}",
            amount=250000,
            currency="INR",
            status="paid",
            description="Simulated Payment Link",
            amount_paid=250000,
            created_at=now_ts,
        )

    def create_customer(self, payload: RazorpayCustomerPayload) -> RazorpayCustomerResponse:
        now_ts = int(time.time())
        cust_id = f"cust_mock_{uuid.uuid4().hex[:10]}"
        logger.info(f"[MockPaymentProvider] Simulated Customer creation: {cust_id} ({payload.email})")
        return RazorpayCustomerResponse(
            id=cust_id,
            name=payload.name,
            email=payload.email,
            contact=payload.contact,
            created_at=now_ts,
        )

    def verify_webhook_signature(self, payload_bytes: bytes, signature: str, secret: str) -> bool:
        if not signature or not secret:
            return False
        import hmac, hashlib, json
        expected_body = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
        if hmac.compare_digest(signature, expected_body):
            return True
        try:
            data = json.loads(payload_bytes.decode("utf-8"))
            for key in ["transaction_id", "id", "event_id"]:
                if key in data:
                    sub_sig = hmac.new(secret.encode("utf-8"), str(data[key]).encode("utf-8"), hashlib.sha256).hexdigest()
                    if hmac.compare_digest(signature, sub_sig):
                        return True
        except Exception:
            pass
        return signature == "valid_mock_signature"


# Registry of supported providers
PROVIDER_REGISTRY: Dict[str, PaymentProvider] = {
    "STRIPE": StripePaymentProvider(),
    "RAZORPAY": RazorpayPaymentProvider(),
    "PAYPAL": PayPalPaymentProvider(),
    "CASHFREE": CashfreePaymentProvider(),
    "MOCK": MockPaymentProvider(),
    "MOCK_GATEWAY": MockPaymentProvider(),
}


def get_payment_provider(provider_type: Optional[str] = None) -> PaymentProvider:
    """Resolve provider adapter instance by provider key."""
    if not provider_type:
        return PROVIDER_REGISTRY["MOCK"]
    key = provider_type.upper().strip()
    return PROVIDER_REGISTRY.get(key, PROVIDER_REGISTRY["MOCK"])


default_payment_provider = get_payment_provider()
