from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, update
from app.database import get_db
from app.models.notification import MerchantNotification
from app.schemas.common import APIResponse
from app.exceptions import EntityNotFoundException
from app.api.deps import get_current_org_context

router = APIRouter(prefix="/notifications", tags=["Merchant Notifications"])


@router.get("", response_model=APIResponse[Dict[str, Any]])
async def list_notifications(
    limit: int = Query(50, ge=1, le=100),
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve merchant notifications and unread badge count."""
    org, _ = org_context

    query = (
        select(MerchantNotification)
        .where(MerchantNotification.organization_id == org.id)
        .order_by(desc(MerchantNotification.created_at))
        .limit(limit)
    )
    result = await db.execute(query)
    notifs = result.scalars().all()

    unread_count = sum(1 for n in notifs if not n.is_read)

    return APIResponse(
        message="Notifications retrieved",
        data={
            "unread_count": unread_count,
            "notifications": [
                {
                    "id": n.id,
                    "title": n.title,
                    "message": n.message,
                    "severity": n.severity,
                    "is_read": n.is_read,
                    "related_case_id": n.related_case_id,
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                }
                for n in notifs
            ],
        },
    )


@router.patch("/{notification_id}/read", response_model=APIResponse[Dict[str, Any]])
async def mark_notification_read(
    notification_id: str,
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """Mark a notification as read."""
    org, _ = org_context
    res = await db.execute(
        select(MerchantNotification).where(
            MerchantNotification.id == notification_id,
            MerchantNotification.organization_id == org.id,
        )
    )
    n = res.scalar_one_or_none()
    if not n:
        raise EntityNotFoundException(entity_name="Notification", entity_id=notification_id)

    n.is_read = True
    await db.commit()

    return APIResponse(message="Notification marked as read", data={"id": n.id, "is_read": True})


@router.post("/mark-all-read", response_model=APIResponse[Dict[str, Any]])
async def mark_all_read(
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications as read for current organization."""
    org, _ = org_context
    await db.execute(
        update(MerchantNotification)
        .where(MerchantNotification.organization_id == org.id)
        .values(is_read=True)
    )
    await db.commit()

    return APIResponse(message="All notifications marked as read", data={"marked": True})
