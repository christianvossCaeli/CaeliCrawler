"""Custom exceptions for the application."""

from typing import Optional


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        detail: Optional[str] = None,
        code: Optional[str] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        self.code = code
        super().__init__(self.message)


class NotFoundError(AppException):
    """Resource not found error."""

    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} not found",
            status_code=404,
            detail=f"{resource} with identifier '{identifier}' does not exist",
            code="NOT_FOUND",
        )


class ConflictError(AppException):
    """Resource conflict error (e.g., duplicate)."""

    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=409,
            detail=detail,
            code="CONFLICT",
        )


class ValidationError(AppException):
    """Validation error."""

    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=422,
            detail=detail,
            code="VALIDATION_ERROR",
        )


class CrawlerError(AppException):
    """Crawler-related error."""

    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=500,
            detail=detail,
            code="CRAWLER_ERROR",
        )


class ExternalServiceError(AppException):
    """External service error (e.g., Azure OpenAI)."""

    def __init__(self, service: str, detail: Optional[str] = None):
        super().__init__(
            message=f"Error communicating with {service}",
            status_code=502,
            detail=detail,
            code="EXTERNAL_SERVICE_ERROR",
        )
