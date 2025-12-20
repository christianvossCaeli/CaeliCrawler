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


class FeatureDisabledError(AppException):
    """Feature is disabled via feature flag."""

    def __init__(self, feature: str):
        super().__init__(
            message=f"Feature '{feature}' is currently disabled",
            status_code=403,
            detail=f"The feature '{feature}' is disabled. Enable it via the corresponding feature flag.",
            code="FEATURE_DISABLED",
        )


# =============================================================================
# Category-specific Exceptions
# =============================================================================


class CategoryValidationError(ValidationError):
    """Category-specific validation error with field context."""

    def __init__(self, field: str, message: str, value: Optional[str] = None):
        detail = f"Field '{field}': {message}"
        if value:
            detail += f" (received: '{value}')"
        super().__init__(
            message=f"Invalid {field}",
            detail=detail,
        )
        self.field = field
        self.code = "CATEGORY_VALIDATION_ERROR"


class InvalidRegexPatternError(CategoryValidationError):
    """Invalid regex pattern in URL filters."""

    def __init__(self, pattern: str, error: str):
        super().__init__(
            field="url_pattern",
            message=f"Invalid regex: {error}",
            value=pattern,
        )
        self.code = "INVALID_REGEX_PATTERN"


class InvalidCronExpressionError(CategoryValidationError):
    """Invalid cron expression for scheduling."""

    def __init__(self, expression: str, error: Optional[str] = None):
        message = "Invalid cron expression format"
        if error:
            message += f": {error}"
        super().__init__(
            field="schedule_cron",
            message=message,
            value=expression,
        )
        self.code = "INVALID_CRON_EXPRESSION"


class InvalidLanguageCodeError(CategoryValidationError):
    """Invalid ISO 639-1 language code."""

    def __init__(self, code: str):
        super().__init__(
            field="languages",
            message="Must be a 2-letter ISO 639-1 code (e.g., 'de', 'en')",
            value=code,
        )
        self.code = "INVALID_LANGUAGE_CODE"


class InvalidExtractionHandlerError(CategoryValidationError):
    """Invalid extraction handler type."""

    def __init__(self, handler: str, valid_handlers: tuple = ("default", "event")):
        super().__init__(
            field="extraction_handler",
            message=f"Must be one of: {', '.join(valid_handlers)}",
            value=handler,
        )
        self.code = "INVALID_EXTRACTION_HANDLER"


class CategoryNotFoundError(NotFoundError):
    """Category not found error with helpful suggestions."""

    def __init__(self, identifier: str, suggestion: Optional[str] = None):
        super().__init__("Category", identifier)
        if suggestion:
            self.detail += f". Did you mean: '{suggestion}'?"
        self.code = "CATEGORY_NOT_FOUND"


class CategoryDuplicateError(ConflictError):
    """Category already exists with same name or slug."""

    def __init__(self, field: str, value: str):
        super().__init__(
            message=f"Category with this {field} already exists",
            detail=f"A category with {field}='{value}' already exists. Please choose a different {field}.",
        )
        self.field = field
        self.code = "CATEGORY_DUPLICATE"
