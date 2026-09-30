"""Security headers middleware for FastAPI."""

from __future__ import annotations

from typing import cast

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security-related HTTP response headers."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = cast(Response, await call_next(request))
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Clickjacking protection
        response.headers["X-Frame-Options"] = "DENY"
        # XSS protection (legacy but harmless)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Content Security Policy (API-focused; adjust for frontend serving)
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        # HSTS (force HTTPS for 1 year, include subdomains)
        if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
