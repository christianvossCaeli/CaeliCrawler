"""
Middleware for handling internationalization based on request context.

Sets the locale for each request based on:
1. X-Language header (explicit override)
2. User preference (from JWT token)
3. Accept-Language header
4. Default locale (de)
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.i18n import set_locale, get_locale, SUPPORTED_LOCALES, DEFAULT_LOCALE


class I18nMiddleware(BaseHTTPMiddleware):
    """
    Middleware that sets the locale based on request headers or user preference.

    Priority order:
    1. X-Language header - explicit client override
    2. Accept-Language header - browser preference
    3. Default locale (de)

    Note: User preference from JWT is handled in the auth dependency,
    which runs after middleware but can override the locale if needed.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        locale = self._determine_locale(request)
        set_locale(locale)

        response = await call_next(request)

        # Add Content-Language header to response
        response.headers["Content-Language"] = get_locale()

        return response

    def _determine_locale(self, request: Request) -> str:
        """
        Determine the locale for this request.

        Args:
            request: The incoming request

        Returns:
            The locale code to use
        """
        # Priority 1: X-Language header (explicit override)
        x_language = request.headers.get("X-Language", "").lower()
        if x_language and x_language in SUPPORTED_LOCALES:
            return x_language

        # Priority 2: Parse Accept-Language header
        accept_language = request.headers.get("Accept-Language", "")
        for lang_entry in accept_language.split(","):
            # Handle entries like "de-DE;q=0.9" or "en"
            lang_code = lang_entry.split(";")[0].strip().split("-")[0].lower()
            if lang_code in SUPPORTED_LOCALES:
                return lang_code

        # Priority 3: Default locale
        return DEFAULT_LOCALE


def get_request_locale() -> str:
    """
    Get the current request's locale.

    This is a convenience function that can be used in route handlers
    to get the locale that was set by the middleware.

    Returns:
        Current locale code
    """
    return get_locale()
