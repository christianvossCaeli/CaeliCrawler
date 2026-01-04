"""
Security Headers Middleware.

Adds security-related HTTP headers to all responses.
Essential for production deployments.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all responses.

    Headers added:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security (HSTS) - only in production
    - Content-Security-Policy - basic policy
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: geolocation=(), camera=(), microphone=()
    """

    def __init__(self, app, enable_hsts: bool = False):
        super().__init__(app)
        self.enable_hsts = enable_hsts

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # XSS Protection (legacy, but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy (disable unnecessary browser features)
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=(), payment=()"

        # HSTS - Only enable in production with HTTPS
        if self.enable_hsts:
            # 1 year, include subdomains, preload ready
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # Content Security Policy
        # Note: 'unsafe-inline' for styles is needed for Vuetify/Vue.js
        # 'unsafe-eval' removed for better XSS protection (may need adjustment if Vue needs it)
        if self.enable_hsts:
            # Production: Stricter CSP
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "  # Removed unsafe-inline and unsafe-eval
                "style-src 'self' 'unsafe-inline'; "  # Vuetify needs unsafe-inline for styles
                "img-src 'self' data: https:; "
                "font-src 'self' data: https://fonts.gstatic.com; "
                "connect-src 'self' https:; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'; "
                "upgrade-insecure-requests;"
            )
        else:
            # Development: More permissive for hot-reload etc.
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' https: ws: wss:; "  # ws: for hot-reload
                "frame-ancestors 'none';"
            )

        return response


class TrustedHostMiddleware:
    """
    Middleware to validate Host header.

    Prevents Host header attacks in production.
    """

    def __init__(self, app, allowed_hosts: list[str]):
        self.app = app
        self.allowed_hosts = [h.lower() for h in allowed_hosts]
        # Always allow health checks without host validation
        self.health_paths = ["/health", "/healthz", "/ready"]

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # Skip validation for health check endpoints
        path = scope.get("path", "")
        if path in self.health_paths:
            await self.app(scope, receive, send)
            return

        # Get host from headers
        headers = dict(scope.get("headers", []))
        host_header = headers.get(b"host", b"").decode("latin-1").lower()

        # Remove port from host
        host = host_header.split(":")[0]

        # Check if host is allowed
        if "*" in self.allowed_hosts or host in self.allowed_hosts:
            await self.app(scope, receive, send)
            return

        # Host not allowed
        response = Response(
            content="Invalid host header",
            status_code=400,
            media_type="text/plain",
        )
        await response(scope, receive, send)
