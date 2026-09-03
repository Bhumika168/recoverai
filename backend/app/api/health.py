import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.config import settings

router = APIRouter(tags=["Health"])

START_TIME = time.time()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(db: AsyncSession = Depends(get_db)):
    """System health endpoint checking application state and database connectivity."""
    db_status = "healthy"
    db_latency_ms = 0.0
    
    try:
        t0 = time.time()
        await db.execute(text("SELECT 1"))
        db_latency_ms = round((time.time() - t0) * 1000, 2)
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    is_healthy = "unhealthy" not in db_status
    return {
        "status": "healthy" if is_healthy else "degraded",
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "database": {
            "status": "healthy" if is_healthy else "unhealthy",
            "connected": is_healthy,
            "latency_ms": db_latency_ms,
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness_probe():
    """Lightweight liveness probe indicating the HTTP process is running."""
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/ready")
async def readiness_probe(response: Response, db: AsyncSession = Depends(get_db)):
    """
    Readiness probe verifying whether the application is ready to accept production traffic.
    Returns HTTP 200 when database is accessible, HTTP 503 otherwise.
    """
    try:
        t0 = time.time()
        await db.execute(text("SELECT 1"))
        latency_ms = round((time.time() - t0) * 1000, 2)
        return {
            "status": "ready",
            "database": "connected",
            "latency_ms": latency_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "database": "disconnected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
