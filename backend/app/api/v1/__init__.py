from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.customers import router as customers_router
from app.api.v1.transactions import router as transactions_router
from app.api.v1.cases import router as cases_router
from app.api.v1.audit import router as audit_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.organization import router as organization_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.campaigns import router as campaigns_router
from app.api.v1.templates import router as templates_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.customer_recovery import router as customer_recovery_router
from app.api.v1.demo import router as demo_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth_router)
api_v1_router.include_router(organization_router)
api_v1_router.include_router(integrations_router)
api_v1_router.include_router(campaigns_router)
api_v1_router.include_router(templates_router)
api_v1_router.include_router(notifications_router)
api_v1_router.include_router(customer_recovery_router)
api_v1_router.include_router(customers_router)
api_v1_router.include_router(transactions_router)
api_v1_router.include_router(cases_router)
api_v1_router.include_router(audit_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(demo_router)

__all__ = ["api_v1_router"]
