import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.config import settings
from app.logging_config import logger
from app.database import init_db
from app.exceptions import RecoverAIException
from app.api.health import router as health_router
from app.api.v1 import api_v1_router
from app.api.webhooks import router as webhooks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]")
    await init_db()
    try:
        from app.database import AsyncSessionLocal
        from app.services.seed_service import seed_database_if_empty
        async with AsyncSessionLocal() as session:
            await seed_database_if_empty(session)
    except Exception as e:
        logger.warning(f"[Startup Seed] Note: {str(e)}")
    yield
    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Autonomous, policy-guarded AI revenue recovery platform.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.rate_limiter import RateLimiterMiddleware

# Security Headers & Request Correlation
app.add_middleware(SecurityHeadersMiddleware)

# Rate Limiting
app.add_middleware(RateLimiterMiddleware, enabled=True)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request Logging Middleware
@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    start_time = time.time()
    path = request.url.path
    method = request.method
    
    try:
        response = await call_next(request)
        process_time_ms = round((time.time() - start_time) * 1000, 2)
        
        # Log all non-health requests or slow requests
        if path != "/health" or process_time_ms > 200:
            logger.info(f"{method} {path} - {response.status_code} ({process_time_ms}ms)")
            
        response.headers["X-Process-Time"] = f"{process_time_ms}ms"
        return response
    except Exception as exc:
        process_time_ms = round((time.time() - start_time) * 1000, 2)
        logger.error(f"{method} {path} FAILED after {process_time_ms}ms: {str(exc)}", exc_info=True)
        origin = request.headers.get("origin")
        allowed_origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]
        resp_origin = origin if (origin in allowed_origins or "*" in allowed_origins) else (allowed_origins[0] if allowed_origins else "*")
        headers = {
            "X-Process-Time": f"{process_time_ms}ms",
            "Access-Control-Allow-Origin": resp_origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "An internal server error occurred",
                "error": {
                    "error_code": "INTERNAL_SERVER_ERROR",
                    "detail": str(exc) if settings.DEBUG else "Please contact system administrator",
                },
            },
            headers=headers,
        )


# Exception Handlers
@app.exception_handler(RecoverAIException)
async def recoverai_exception_handler(request: Request, exc: RecoverAIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "detail": exc.detail,
            "error": {
                "error_code": exc.error_code,
                "extra": exc.extra,
            },
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    logger.warning(f"Validation error on {request.method} {request.url.path}: {errors}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Request validation failed",
            "error": {
                "error_code": "VALIDATION_ERROR",
                "details": errors,
            },
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "An internal server error occurred",
            "error": {
                "error_code": "INTERNAL_SERVER_ERROR",
                "detail": str(exc) if settings.DEBUG else "Please contact system administrator",
            },
        },
    )


# Include Routers
app.include_router(health_router)
app.include_router(api_v1_router)
app.include_router(webhooks_router)


@app.get("/")
async def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "description": "Autonomous AI-Powered Multi-Tenant Revenue Recovery Platform",
        "docs": "/docs",
        "health": "/health",
        "api_v1": "/api/v1",
    }
