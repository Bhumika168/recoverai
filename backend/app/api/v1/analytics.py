from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
from app.database import get_db
from app.models.recovery_case import RecoveryCase, CaseStatus
from app.models.transaction import Transaction, TransactionStatus
from app.models.payment_attempt import PaymentAttempt, AttemptStatus
from app.models.ai_decision import AIDecision
from app.models.recovery_action import RecoveryAction
from app.models.audit_log import AuditLog
from app.models.organization import Organization
from app.models.integration import PaymentProviderConnection
from app.schemas.common import APIResponse
from app.api.deps import get_current_org_context

router = APIRouter(prefix="/analytics", tags=["Analytics & KPIs"])


def parse_date_range(
    range_param: Optional[str] = None,
    start_date_str: Optional[str] = None,
    end_date_str: Optional[str] = None,
) -> Optional[datetime]:
    """Computes cutoff datetime based on time range parameter."""
    now = datetime.now(timezone.utc)
    if not range_param or range_param.lower() in ["all", "all_time"]:
        return None
    if range_param.lower() == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif range_param.lower() in ["7d", "7_days"]:
        return now - timedelta(days=7)
    elif range_param.lower() in ["30d", "30_days"]:
        return now - timedelta(days=30)
    elif range_param.lower() in ["90d", "90_days"]:
        return now - timedelta(days=90)
    elif range_param.lower() == "custom" and start_date_str:
        try:
            return datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
        except Exception:
            return None
    return None


@router.get("/summary", response_model=APIResponse[Dict[str, Any]])
async def get_dashboard_summary(
    range: Optional[str] = Query("all", alias="range"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Computes real-time dynamic KPIs strictly scoped to the authenticated organization.
    No hardcoding. If empty, returns zeroes cleanly.
    """
    org, _ = org_context
    cutoff = parse_date_range(range, start_date, end_date)

    # 1. Fetch Cases for Organization
    case_query = select(RecoveryCase).where(RecoveryCase.organization_id == org.id)
    if cutoff:
        case_query = case_query.where(RecoveryCase.created_at >= cutoff)
    
    cases_res = await db.execute(case_query)
    cases = cases_res.scalars().all()

    # Active states
    ACTIVE_STATUSES = {
        CaseStatus.DETECTED,
        CaseStatus.DIAGNOSED,
        CaseStatus.POLICY_REVIEW,
        CaseStatus.APPROVED,
        CaseStatus.ACTION_SCHEDULED,
        CaseStatus.CUSTOMER_CONTACTED,
        CaseStatus.RETRY_PENDING,
        CaseStatus.PAYMENT_ATTEMPTED,
        CaseStatus.VERIFICATION,
        CaseStatus.OPEN,
        CaseStatus.IN_PROGRESS,
        CaseStatus.PENDING_APPROVAL,
    }

    # 2. Transaction Summary
    txn_query = select(Transaction).where(Transaction.organization_id == org.id)
    if cutoff:
        txn_query = txn_query.where(Transaction.created_at >= cutoff)
    
    txn_res = await db.execute(txn_query)
    txns = txn_res.scalars().all()

    total_txns = len(txns)
    successful_txns = len([t for t in txns if t.status in [TransactionStatus.CAPTURED, TransactionStatus.AUTHORIZED]])
    failed_txns = len([t for t in txns if t.status == TransactionStatus.FAILED])
    pending_txns = len([t for t in txns if t.status in [TransactionStatus.CREATED, TransactionStatus.ABANDONED]])
    recovered_txns = len([t for t in txns if t.status == TransactionStatus.RECOVERED])

    # Revenue At Risk: Eligible unrecovered revenue
    TERMINAL_NON_RISK = {CaseStatus.RECOVERED, CaseStatus.CANCELLED, CaseStatus.BLOCKED, CaseStatus.STOPPED}
    
    if cases:
        total_amount_at_risk = sum(c.amount_at_risk for c in cases if c.status not in TERMINAL_NON_RISK)
        eligible_revenue_total = sum(c.amount_at_risk for c in cases if c.status != CaseStatus.CANCELLED and c.status != CaseStatus.BLOCKED)
        total_revenue_recovered = sum(c.recovered_amount for c in cases if c.status == CaseStatus.RECOVERED)
        # Also check captured transactions linked to recovered cases
        recovered_txn_ids = {c.transaction_id for c in cases if c.status == CaseStatus.RECOVERED}
        captured_sum = sum(t.amount for t in txns if (t.id in recovered_txn_ids or t.status == TransactionStatus.CAPTURED) and any(c.transaction_id == t.id and c.status == CaseStatus.RECOVERED for c in cases))
        if captured_sum > total_revenue_recovered:
            total_revenue_recovered = captured_sum
    else:
        total_amount_at_risk = sum(t.amount for t in txns if t.status == TransactionStatus.FAILED)
        eligible_revenue_total = total_amount_at_risk
        total_revenue_recovered = 0.0
    
    active_cases = len([c for c in cases if c.status in ACTIVE_STATUSES])
    recovered_cases = len([c for c in cases if c.status == CaseStatus.RECOVERED])
    escalated_cases = len([
        c for c in cases 
        if c.status in [CaseStatus.ESCALATED, CaseStatus.PENDING_APPROVAL] or c.requires_human_approval == "YES"
    ])
    unrecoverable_count = len([c for c in cases if c.status in [CaseStatus.UNRECOVERABLE, CaseStatus.EXHAUSTED, CaseStatus.FAILED, CaseStatus.BLOCKED, CaseStatus.STOPPED]])

    # Recovery Rate %: Verified Recovered / Eligible At Risk * 100
    recovery_rate = (
        round((total_revenue_recovered / eligible_revenue_total * 100), 1)
        if eligible_revenue_total > 0
        else 0.0
    )

    # 3. Recovery Queue Summary
    queue_summary = {
        "awaiting_approval": len([c for c in cases if c.status == CaseStatus.PENDING_APPROVAL or c.requires_human_approval == "YES"]),
        "action_scheduled": len([c for c in cases if c.status in [CaseStatus.ACTION_SCHEDULED, CaseStatus.RETRY_PENDING]]),
        "in_progress": len([c for c in cases if c.status in [CaseStatus.IN_PROGRESS, CaseStatus.CUSTOMER_CONTACTED, CaseStatus.PAYMENT_ATTEMPTED]]),
        "escalated": len([c for c in cases if c.status == CaseStatus.ESCALATED]),
    }

    # 4. Average recovery time (hours) & average attempts
    recovered_with_time = [
        (c.recovered_at - c.created_at).total_seconds() / 3600.0
        for c in cases
        if c.status == CaseStatus.RECOVERED and c.recovered_at and c.created_at
    ]
    avg_recovery_time_hours = round(sum(recovered_with_time) / len(recovered_with_time), 1) if recovered_with_time else 0.0

    recovered_attempts = [c.retry_count for c in cases if c.status == CaseStatus.RECOVERED]
    avg_attempts_to_recovery = round(sum(recovered_attempts) / len(recovered_attempts), 1) if recovered_attempts else 0.0

    return APIResponse(
        message="Dashboard summary calculated successfully",
        data={
            "revenue_at_risk": total_amount_at_risk,
            "revenue_recovered": total_revenue_recovered,
            "recovery_rate_percentage": recovery_rate,
            "active_recovery_cases": active_cases,
            "recovered_cases": recovered_cases,
            "successful_recoveries": recovered_cases,
            "human_escalations": escalated_cases,
            "unrecoverable_count": unrecoverable_count,
            "total_cases": len(cases),
            "avg_recovery_score": round(sum(c.recovery_score for c in cases) / len(cases), 1) if cases else 0.0,
            "currency": org.currency or "INR",
            "organization_name": org.name,
            "environment": getattr(org, "environment", None) or "Production",
            "transaction_summary": {
                "total": total_txns,
                "successful": successful_txns,
                "failed": failed_txns,
                "pending": pending_txns,
                "recovered": recovered_txns,
            },
            "queue_summary": queue_summary,
            "performance": {
                "avg_recovery_time_hours": avg_recovery_time_hours,
                "avg_attempts_to_recovery": avg_attempts_to_recovery,
                "successful_recovery_attempts": recovered_cases,
                "failed_recovery_attempts": unrecoverable_count,
                "current_pipeline_amount": total_amount_at_risk,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@router.get("/revenue-trend", response_model=APIResponse[List[Dict[str, Any]]])
async def get_revenue_trend(
    range: Optional[str] = Query("30d", alias="range"),
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Computes time-series trend of Revenue at Risk vs Verified Recovered from DB records.
    Returns empty list if no historical data exists.
    """
    org, _ = org_context
    cutoff = parse_date_range(range)

    query = (
        select(RecoveryCase)
        .where(RecoveryCase.organization_id == org.id)
    )
    if cutoff:
        query = query.where(RecoveryCase.created_at >= cutoff)
    query = query.order_by(RecoveryCase.created_at)

    cases_res = await db.execute(query)
    cases = cases_res.scalars().all()

    if not cases:
        return APIResponse(message="No trend data", data=[])

    trend_points = []
    running_at_risk = 0.0
    running_recovered = 0.0

    for i, c in enumerate(cases):
        running_at_risk += c.amount_at_risk
        running_recovered += c.recovered_amount
        label = c.created_at.strftime("%b %d, %H:%M") if c.created_at else f"Point {i+1}"
        trend_points.append({
            "name": label,
            "at_risk": round(running_at_risk, 2),
            "recovered": round(running_recovered, 2),
            "case_amount": c.amount_at_risk,
            "status": c.status.value,
        })

    return APIResponse(
        message="Revenue trend retrieved",
        data=trend_points[-30:] if len(trend_points) > 30 else trend_points,
    )


@router.get("/failure-breakdown", response_model=APIResponse[List[Dict[str, Any]]])
async def get_failure_breakdown(
    range: Optional[str] = Query("all", alias="range"),
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns breakdown of revenue at risk and cases by failure/diagnosis category.
    """
    org, _ = org_context
    cutoff = parse_date_range(range)

    query = select(RecoveryCase).where(RecoveryCase.organization_id == org.id)
    if cutoff:
        query = query.where(RecoveryCase.created_at >= cutoff)
    
    cases_res = await db.execute(query)
    cases = cases_res.scalars().all()
    case_ids = [c.id for c in cases]

    category_colors = {
        "temporary_failure": "#D79A43",
        "insufficient_funds": "#E5A958",
        "authentication_issue": "#C48834",
        "checkout_abandonment": "#B37625",
        "hard_decline": "#E76F51",
        "repeated_failure": "#F4A261",
        "subscription_failure": "#20B89A",
        "expired_payment": "#8A6D47",
        "other": "#5A544C",
    }

    if not case_ids:
        return APIResponse(message="No failure data", data=[])

    decisions_res = await db.execute(
        select(AIDecision.failure_category, func.count(AIDecision.id))
        .where(AIDecision.case_id.in_(case_ids))
        .group_by(AIDecision.failure_category)
    )
    cat_rows = decisions_res.all()

    breakdown = []
    for cat, count in cat_rows:
        formatted_name = cat.replace("_", " ").title()
        breakdown.append({
            "category": cat,
            "name": formatted_name,
            "count": count,
            "color": category_colors.get(cat, "#D79A43"),
        })

    return APIResponse(message="Failure breakdown retrieved", data=breakdown)


@router.get("/recovery-funnel", response_model=APIResponse[List[Dict[str, Any]]])
async def get_recovery_funnel(
    range: Optional[str] = Query("all", alias="range"),
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Recovery Funnel: Revenue At Risk -> Eligible -> Actionable -> Attempted -> Verified Recovered.
    """
    org, _ = org_context
    cutoff = parse_date_range(range)

    query = select(RecoveryCase).where(RecoveryCase.organization_id == org.id)
    if cutoff:
        query = query.where(RecoveryCase.created_at >= cutoff)
    
    cases_res = await db.execute(query)
    cases = cases_res.scalars().all()
    case_ids = [c.id for c in cases]

    total_detected = len(cases)
    total_diagnosed = 0
    total_policy_passed = 0
    total_attempted = 0
    total_recovered = len([c for c in cases if c.status == CaseStatus.RECOVERED])

    if case_ids:
        total_diagnosed = (
            await db.execute(select(func.count(AIDecision.id)).where(AIDecision.case_id.in_(case_ids)))
        ).scalar() or 0
        total_policy_passed = (
            await db.execute(
                select(func.count(RecoveryAction.id))
                .where(RecoveryAction.case_id.in_(case_ids), RecoveryAction.policy_passed == "YES")
            )
        ).scalar() or 0
        total_attempted = (
            await db.execute(
                select(func.count(RecoveryAction.id))
                .where(RecoveryAction.case_id.in_(case_ids), RecoveryAction.status.in_(["EXECUTED", "SUCCESS", "PENDING_VERIFICATION"]))
            )
        ).scalar() or 0

    funnel = [
        {"stage": "Revenue At Risk", "count": total_detected, "fill": "#D79A43"},
        {"stage": "Eligible", "count": total_diagnosed, "fill": "#E5A958"},
        {"stage": "Actionable", "count": total_policy_passed, "fill": "#C48834"},
        {"stage": "Attempted", "count": total_attempted, "fill": "#B37625"},
        {"stage": "Verified Recovered", "count": total_recovered, "fill": "#20B89A"},
    ]

    return APIResponse(message="Recovery funnel retrieved", data=funnel)


@router.get("/recent-activity", response_model=APIResponse[List[Dict[str, Any]]])
async def get_recent_activity(
    limit: int = Query(10, ge=1, le=50),
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Live recent recovery activity feed from audit ledger records.
    Every single event originates from the database.
    """
    org, _ = org_context

    logs_res = await db.execute(
        select(AuditLog)
        .where(AuditLog.organization_id == org.id)
        .order_by(desc(AuditLog.created_at))
        .limit(limit)
    )
    logs = logs_res.scalars().all()

    activity_items = []
    for l in logs:
        activity_items.append({
            "id": l.id,
            "event_type": l.event_type,
            "actor": l.actor,
            "notes": l.notes,
            "timestamp": l.created_at.isoformat() if l.created_at else None,
            "state_after": l.state_after,
        })

    return APIResponse(message="Recent activity retrieved", data=activity_items)


@router.get("/top-opportunities", response_model=APIResponse[List[Dict[str, Any]]])
async def get_top_opportunities(
    limit: int = Query(5, ge=1, le=20),
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Highest-value actionable cases sorted by recovery priority.
    """
    org, _ = org_context

    # Unrecovered active cases ordered by amount at risk
    query = (
        select(RecoveryCase)
        .where(
            RecoveryCase.organization_id == org.id,
            RecoveryCase.status.not_in([CaseStatus.RECOVERED, CaseStatus.CANCELLED, CaseStatus.UNRECOVERABLE]),
        )
        .order_by(desc(RecoveryCase.amount_at_risk))
        .limit(limit)
    )
    cases_res = await db.execute(query)
    cases = cases_res.scalars().all()

    opportunities = []
    for c in cases:
        opportunities.append({
            "case_id": c.id,
            "transaction_id": c.transaction_id,
            "amount": c.amount_at_risk,
            "status": c.status.value,
            "recovery_score": c.recovery_score,
            "strategy": c.strategy_summary or "Autonomous Retry Sequence",
            "requires_approval": c.requires_human_approval == "YES" or c.status == CaseStatus.PENDING_APPROVAL,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    return APIResponse(message="Top opportunities retrieved", data=opportunities)


@router.get("/data-sources", response_model=APIResponse[Dict[str, Any]])
async def get_data_sources_status(
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Real status of connected payment providers and data sources.
    Never claims connected unless real DB record exists.
    """
    org, _ = org_context

    conns_res = await db.execute(
        select(PaymentProviderConnection).where(
            PaymentProviderConnection.organization_id == org.id,
            PaymentProviderConnection.status == "CONNECTED",
        )
    )
    connections = conns_res.scalars().all()

    # Check last transaction imported
    last_txn_res = await db.execute(
        select(Transaction)
        .where(Transaction.organization_id == org.id)
        .order_by(desc(Transaction.created_at))
        .limit(1)
    )
    last_txn = last_txn_res.scalar_one_or_none()

    return APIResponse(
        message="Data sources status retrieved",
        data={
            "payment_providers": {
                "connected": len(connections) > 0,
                "providers": [c.provider for c in connections],
            },
            "csv_import": {
                "available": True,
                "last_import_at": last_txn.created_at.isoformat() if last_txn else None,
            },
            "manual_entry": {
                "available": True,
            },
        },
    )


# Backward compatibility for existing frontend charts query
@router.get("/charts", response_model=APIResponse[Dict[str, Any]])
async def get_dashboard_charts(
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    trend_res = await get_revenue_trend(range="30d", org_context=org_context, db=db)
    breakdown_res = await get_failure_breakdown(range="all", org_context=org_context, db=db)
    funnel_res = await get_recovery_funnel(range="all", org_context=org_context, db=db)

    return APIResponse(
        message="Charts retrieved",
        data={
            "recovery_trend": trend_res.data,
            "failure_distribution": breakdown_res.data,
            "recovery_funnel": funnel_res.data,
            "action_distribution": [],
        },
    )
