from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.models.template import MessageTemplate
from app.schemas.common import APIResponse
from app.exceptions import EntityNotFoundException, RecoverAIException
from app.api.deps import get_current_org_context, require_write_access
from app.notifications.provider import sanitize_and_render_template, DEFAULT_TEMPLATES

router = APIRouter(prefix="/templates", tags=["Message Templates"])


@router.get("", response_model=APIResponse[List[Dict[str, Any]]])
async def list_templates(
    channel: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """List message templates for the authenticated organization. Initializes default templates if none exist."""
    org, _ = org_context

    query = select(MessageTemplate).where(MessageTemplate.organization_id == org.id)
    if channel:
        query = query.where(MessageTemplate.channel == channel.upper())
    if language:
        query = query.where(MessageTemplate.language == language.upper())
    query = query.order_by(desc(MessageTemplate.created_at))

    result = await db.execute(query)
    templates = result.scalars().all()

    # Seed default templates for new org
    if len(templates) == 0:
        for dt in DEFAULT_TEMPLATES:
            new_t = MessageTemplate(
                organization_id=org.id,
                name=dt["name"],
                channel=dt["channel"],
                language=dt["language"],
                subject=dt.get("subject"),
                body=dt["body"],
                status="ACTIVE",
            )
            db.add(new_t)
        await db.commit()

        # Re-fetch
        result = await db.execute(query)
        templates = result.scalars().all()

    return APIResponse(
        message="Templates retrieved successfully",
        data=[
            {
                "id": t.id,
                "name": t.name,
                "channel": t.channel,
                "language": t.language,
                "subject": t.subject,
                "body": t.body,
                "status": t.status,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in templates
        ],
    )


@router.post("", response_model=APIResponse[Dict[str, Any]], status_code=status.HTTP_201_CREATED)
async def create_template(
    payload: Dict[str, Any],
    org_context: tuple = Depends(require_write_access),
    db: AsyncSession = Depends(get_db),
):
    """Create or update a custom message template."""
    org, _ = org_context

    name = payload.get("name", "").strip()
    body = payload.get("body", "").strip()
    channel = payload.get("channel", "EMAIL").upper()
    language = payload.get("language", "EN").upper()
    subject = payload.get("subject")

    if not name or not body:
        raise RecoverAIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template name and body are required.",
            error_code="INVALID_TEMPLATE",
        )

    tmpl = MessageTemplate(
        organization_id=org.id,
        name=name,
        channel=channel,
        language=language,
        subject=subject,
        body=body,
        status="ACTIVE",
    )
    db.add(tmpl)
    await db.commit()
    await db.refresh(tmpl)

    return APIResponse(
        message="Template created successfully",
        data={"id": tmpl.id, "name": tmpl.name, "channel": tmpl.channel},
    )


@router.post("/preview", response_model=APIResponse[Dict[str, Any]])
async def preview_template(
    payload: Dict[str, Any],
    org_context: tuple = Depends(get_current_org_context),
):
    """Safely render template preview with sample variable interpolation."""
    org, _ = org_context
    body = payload.get("body", "")
    subject = payload.get("subject", "")

    sample_vars = {
        "customer_name": "Sarah Jenkins",
        "amount": "8,500.00",
        "currency": "INR",
        "payment_method": "HDFC Credit Card",
        "payment_link": "https://pay.recoverai.io/p/case_demo_sample",
        "invoice_number": "INV-2026-089",
        "due_date": "Immediately",
        "company_name": org.name or "RecoverAI Enterprise",
    }

    rendered_subject = sanitize_and_render_template(subject, sample_vars) if subject else None
    rendered_body = sanitize_and_render_template(body, sample_vars)

    return APIResponse(
        message="Preview rendered",
        data={
            "rendered_subject": rendered_subject,
            "rendered_body": rendered_body,
            "variables_used": list(sample_vars.keys()),
        },
    )
