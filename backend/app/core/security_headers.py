"""
Security Headers Middleware.

Adds security-related HTTP headers to all responses.
Essential for production deployments.

CSP Strategy (2026 Best Practices):
- Production: Strict CSP without unsafe-inline for scripts
- Development: Permissive for hot-reload/debugging
- API responses: Restrictive default-src since APIs return JSON
- Nonce-based CSP prepared for future HTML serving
"""

import secrets
from contextvars import ContextVar

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

# Context variable for per-request nonce (for future nonce-based CSP)
_csp_nonce: ContextVar[str | None] = ContextVar("csp_nonce", default=None)


def generate_nonce() -> str:
    """Generate a cryptographically secure nonce for CSP.

    Returns a base64-encoded 16-byte random value.
    """
    return secrets.token_urlsafe(16)


def get_csp_nonce() -> str | None:
    """Get the CSP nonce for the current request.

    Use this in templates/HTML responses to inject nonce into script tags:
    <script nonce="{{ csp_nonce }}">...</script>
    """
    return _csp_nonce.get()


def set_csp_nonce(nonce: str) -> None:
    """Set the CSP nonce for the current request."""
    _csp_nonce.set(nonce)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds comprehensive security headers to all responses.

    Headers added:
    - X-Content-Type-Options: nosniff (prevent MIME sniffing)
    - X-Frame-Options: DENY (prevent clickjacking)
    - X-XSS-Protection: 0 (disabled - modern browsers use CSP instead)
    - Strict-Transport-Security (HSTS) - production only
    - Content-Security-Policy - strict policy
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: disable unnecessary browser features
    - Cross-Origin-* headers: isolation and protection
    """

    def __init__(
        self,
        app,
        enable_hsts: bool = False,
        csp_report_uri: str | None = None,
        csp_report_only: bool = False,
    ):
        """Initialize security headers middleware.

        Args:
            app: The ASGI application
            enable_hsts: Enable HSTS header (only for production with HTTPS)
            csp_report_uri: URI for CSP violation reports (optional)
            csp_report_only: Use Content-Security-Policy-Report-Only instead of enforcing
        """
        super().__init__(app)
        self.enable_hsts = enable_hsts
        self.csp_report_uri = csp_report_uri
        self.csp_report_only = csp_report_only

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Generate nonce for this request (prepared for future nonce-based CSP)
        nonce = generate_nonce()
        set_csp_nonce(nonce)

        response = await call_next(request)

        # === Standard Security Headers ===

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # XSS Protection: Disabled - modern browsers use CSP
        # Note: X-XSS-Protection: 1 can introduce vulnerabilities in some cases
        response.headers["X-XSS-Protection"] = "0"

        # Referrer Policy - don't leak URLs to third parties
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy (Feature Policy) - disable browser features we don't need
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "camera=(), "
            "microphone=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )

        # === Cross-Origin Headers ===

        # Cross-Origin-Opener-Policy: Prevent window.opener attacks
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"

        # Cross-Origin-Resource-Policy: Prevent cross-origin resource loading
        # 'same-site' allows same-site but blocks cross-site
        response.headers["Cross-Origin-Resource-Policy"] = "same-site"

        # === HSTS (Production Only) ===

        if self.enable_hsts:
            # 1 year, include subdomains, preload-ready
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # === Content Security Policy ===

        csp_header = "Content-Security-Policy-Report-Only" if self.csp_report_only else "Content-Security-Policy"

        if self.enable_hsts:
            # Production: Strict CSP
            # - script-src: 'self' only (no inline scripts)
            # - style-src: 'unsafe-inline' needed for Vuetify dynamic styles
            # - object-src: 'none' blocks plugins (Flash, Java, etc.)
            # - base-uri: 'self' prevents base tag hijacking
            # - form-action: 'self' prevents form submission to external sites
            csp_directives = [
                "default-src 'self'",
                "script-src 'self'",  # Strict: no inline scripts
                "style-src 'self' 'unsafe-inline'",  # Vuetify requires unsafe-inline for styles
                "img-src 'self' data: https: blob:",  # blob: for image processing
                "font-src 'self' data: https://fonts.gstatic.com",
                "connect-src 'self' https:",
                "media-src 'self'",
                "object-src 'none'",  # Block plugins
                "frame-src 'none'",  # No iframes
                "frame-ancestors 'none'",  # Can't be framed
                "base-uri 'self'",
                "form-action 'self'",
                "upgrade-insecure-requests",
                "block-all-mixed-content",
            ]
        else:
            # Development: Permissive for hot-reload and debugging
            csp_directives = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # Needed for Vite HMR
                "style-src 'self' 'unsafe-inline'",
                "img-src 'self' data: https: blob:",
                "font-src 'self' data:",
                "connect-src 'self' https: ws: wss:",  # ws: for Vite HMR
                "media-src 'self'",
                "object-src 'none'",
                "frame-src 'none'",
                "frame-ancestors 'none'",
            ]

        # Add report-uri if configured
        if self.csp_report_uri:
            csp_directives.append(f"report-uri {self.csp_report_uri}")

        response.headers[csp_header] = "; ".join(csp_directives)

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
