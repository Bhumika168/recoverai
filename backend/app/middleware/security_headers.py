import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Appends industry-standard production security headers and correlation request IDs.
    """

    async def dispatch(self, request: Request, call_next):
        # 1. Extract or assign X-Request-ID
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
        request.state.request_id = request_id

        # 2. Process downstream request
        response = await call_next(request)

        # 3. Add security headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        
        # In production HTTPS environments, enable HSTS
        # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
