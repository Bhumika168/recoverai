from typing import Dict, Any, Optional
from app.integrations.razorpay.client import razorpay_client_wrapper
from app.integrations.razorpay.models import (
    RazorpayOrderPayload,
    RazorpayOrderResponse,
    RazorpayPaymentResponse,
    RazorpayPaymentLinkPayload,
    RazorpayPaymentLinkResponse,
    RazorpayCustomerPayload,
    RazorpayCustomerResponse,
)
from app.logging_config import logger
from app.exceptions import RecoverAIException


class RazorpayPaymentService:
    """
    Service for executing official Razorpay API operations in Test Mode / Live Mode.
    Follows official Razorpay API specs for Orders, Payments, Payment Links, and Customers.
    """

    def __init__(self, wrapper=None):
        self.wrapper = wrapper or razorpay_client_wrapper

    def create_order(self, payload: RazorpayOrderPayload) -> RazorpayOrderResponse:
        """Create an order via Razorpay Orders API: POST /v1/orders"""
        try:
            logger.info(f"[Razorpay API] Creating Order for amount {payload.amount} {payload.currency}")
            data = payload.model_dump(exclude_none=True)
            res = self.wrapper.client.order.create(data=data)
            logger.info(f"[Razorpay API] Order created successfully: {res.get('id')}")
            return RazorpayOrderResponse.model_validate(res)
        except Exception as e:
            logger.error(f"[Razorpay API] Order creation failed: {str(e)}", exc_info=True)
            raise RecoverAIException(
                status_code=502,
                detail=f"Razorpay Order creation error: {str(e)}",
                error_code="RAZORPAY_ORDER_ERROR",
            )

    def fetch_payment(self, payment_id: str) -> RazorpayPaymentResponse:
        """Fetch payment details via Razorpay Payments API: GET /v1/payments/{payment_id}"""
        try:
            logger.info(f"[Razorpay API] Fetching payment details for: {payment_id}")
            res = self.wrapper.client.payment.fetch(payment_id)
            logger.info(f"[Razorpay API] Fetched payment {payment_id}: status={res.get('status')}")
            return RazorpayPaymentResponse.model_validate(res)
        except Exception as e:
            logger.error(f"[Razorpay API] Fetch payment failed for {payment_id}: {str(e)}", exc_info=True)
            raise RecoverAIException(
                status_code=502,
                detail=f"Razorpay Payment fetch error: {str(e)}",
                error_code="RAZORPAY_PAYMENT_ERROR",
            )

    def create_payment_link(self, payload: RazorpayPaymentLinkPayload) -> RazorpayPaymentLinkResponse:
        """Create a standard Razorpay Payment Link: POST /v1/payment_links"""
        try:
            logger.info(
                f"[Razorpay API] Creating Payment Link for {payload.amount} {payload.currency} (Desc: {payload.description})"
            )
            data = payload.model_dump(exclude_none=True)
            res = self.wrapper.client.payment_link.create(data=data)
            logger.info(f"[Razorpay API] Created Payment Link {res.get('id')} -> {res.get('short_url')}")
            return RazorpayPaymentLinkResponse.model_validate(res)
        except Exception as e:
            logger.error(f"[Razorpay API] Create payment link failed: {str(e)}", exc_info=True)
            raise RecoverAIException(
                status_code=502,
                detail=f"Razorpay Payment Link creation error: {str(e)}",
                error_code="RAZORPAY_PAYMENT_LINK_ERROR",
            )

    def fetch_payment_link(self, link_id: str) -> RazorpayPaymentLinkResponse:
        """Fetch Payment Link details: GET /v1/payment_links/{link_id}"""
        try:
            logger.info(f"[Razorpay API] Fetching Payment Link details for: {link_id}")
            res = self.wrapper.client.payment_link.fetch(link_id)
            return RazorpayPaymentLinkResponse.model_validate(res)
        except Exception as e:
            logger.error(f"[Razorpay API] Fetch payment link failed for {link_id}: {str(e)}", exc_info=True)
            raise RecoverAIException(
                status_code=502,
                detail=f"Razorpay Payment Link fetch error: {str(e)}",
                error_code="RAZORPAY_PAYMENT_LINK_ERROR",
            )

    def create_customer(self, payload: RazorpayCustomerPayload) -> RazorpayCustomerResponse:
        """Create a Customer via Razorpay Customers API: POST /v1/customers"""
        try:
            logger.info(f"[Razorpay API] Creating Customer with email: {payload.email}")
            data = payload.model_dump(exclude_none=True)
            res = self.wrapper.client.customer.create(data=data)
            logger.info(f"[Razorpay API] Created Customer: {res.get('id')}")
            return RazorpayCustomerResponse.model_validate(res)
        except Exception as e:
            logger.error(f"[Razorpay API] Customer creation failed: {str(e)}", exc_info=True)
            raise RecoverAIException(
                status_code=502,
                detail=f"Razorpay Customer creation error: {str(e)}",
                error_code="RAZORPAY_CUSTOMER_ERROR",
            )


razorpay_payment_service = RazorpayPaymentService()
