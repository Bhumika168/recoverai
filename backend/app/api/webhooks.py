from fastapi import APIRouter, Request, Header, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.logging_config import logger
from app.integrations.razorpay.webhooks import RazorpayWebhookVerifier, RazorpayWebhookHandler
import json

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])


@router.post("/razorpay", status_code=status.HTTP_200_OK)
async def handle_razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None, alias="X-Razorpay-Signature"),
    db: AsyncSession = Depends(get_db),
):
    """
    Ingests official Razorpay Webhook Events.
    Verifies HMAC SHA-256 signature and triggers autonomous recovery or reconciliation workflows.
    """
    raw_body = await request.body()
    
    # 1. Verify HMAC SHA-256 signature
    is_valid = RazorpayWebhookVerifier.verify_signature(
        raw_body=raw_body,
        signature=x_razorpay_signature or "",
    )
    
    if not is_valid:
        logger.warning("[Webhook API] Webhook signature verification failed.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Razorpay webhook signature",
        )

    # 2. Parse event JSON payload
    try:
        event_data = json.loads(raw_body.decode("utf-8"))
    except Exception as e:
        logger.error(f"[Webhook API] Failed to parse webhook JSON: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Malformed JSON body",
        )

    # 3. Process the event
    result = await RazorpayWebhookHandler.process_event(event_data, db)
    return {
        "success": True,
        "message": "Webhook processed successfully",
        "result": result,
    }
