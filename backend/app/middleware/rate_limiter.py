import os
import sys
import time
from typing import Dict, List
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.config import settings


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Sliding window in-memory rate limiter.
    Provides endpoint-specific protection against brute-force attacks, token enumeration, and DoS.
    """

    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
        self._requests: Dict[str, List[float]] = {}
        
        # Endpoint-specific rate limits: (max_requests, window_seconds)
        self.AUTH_LIMIT = (20, 60)         # 20 reqs / min for login/signup/reset
        self.RECOVERY_LIMIT = (40, 60)     # 40 reqs / min for public recovery links
        self.GENERAL_LIMIT = (300, 60)     # 300 reqs / min for standard authenticated APIs

    def _get_client_identifier(self, request: Request) -> str:
        """Extract client IP from proxy headers or direct connection."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        client = request.client
        return client.host if client else "127.0.0.1"

    def _get_rate_limit(self, path: str) -> tuple[int, int]:
        """Determine rate limit based on endpoint sensitivity."""
        if any(auth_path in path for auth_path in ["/auth/login", "/auth/signup", "/auth/forgot-password", "/auth/reset-password"]):
            return self.AUTH_LIMIT
        if "/recover/" in path:
            return self.RECOVERY_LIMIT
        return self.GENERAL_LIMIT

    async def dispatch(self, request: Request, call_next):
        if not self.enabled or request.method == "OPTIONS":
            return await call_next(request)

        # In automated test runner, bypass unless explicitly testing rate limits
        is_testing = "PYTEST_CURRENT_TEST" in os.environ or "pytest" in sys.modules
        if is_testing and request.headers.get("X-Test-Rate-Limit") != "enforce":
            return await call_next(request)

        path = request.url.path
        # Skip static or health check routes
        if path in ["/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)

        client_ip = self._get_client_identifier(request)
        max_requests, window_seconds = self._get_rate_limit(path)
        
        # Key grouped by client_ip and path category
        path_category = "auth" if "/auth/" in path else ("recover" if "/recover" in path else "api")
        rate_key = f"{client_ip}:{path_category}"
        now = time.time()
        cutoff = now - window_seconds

        # Prune old timestamps
        timestamps = self._requests.get(rate_key, [])
        valid_timestamps = [t for t in timestamps if t > cutoff]

        if len(valid_timestamps) >= max_requests:
            retry_after = int(window_seconds - (now - valid_timestamps[0])) + 1
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "message": "Too many requests. Please slow down and try again later.",
                    "error_code": "RATE_LIMIT_EXCEEDED",
                },
                headers={
                    "Retry-After": str(max(1, retry_after)),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                },
            )

        valid_timestamps.append(now)
        self._requests[rate_key] = valid_timestamps

        response = await call_next(request)
        
        # Add rate limit headers to response
        remaining = max(0, max_requests - len(valid_timestamps))
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
