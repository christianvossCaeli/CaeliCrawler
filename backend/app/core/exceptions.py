"""Custom exceptions for the application."""


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        detail: str | None = None,
        code: str | None = None,
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

    def __init__(self, message: str, detail: str | None = None):
        super().__init__(
            message=message,
            status_code=409,
            detail=detail,
            code="CONFLICT",
        )


class ValidationError(AppException):
    """Validation error."""

    def __init__(self, message: str, detail: str | None = None):
        super().__init__(
            message=message,
            status_code=422,
            detail=detail,
            code="VALIDATION_ERROR",
        )


class CrawlerError(AppException):
    """Crawler-related error."""

    def __init__(self, message: str, detail: str | None = None):
        super().__init__(
            message=message,
            status_code=500,
            detail=detail,
            code="CRAWLER_ERROR",
        )


class ExternalServiceError(AppException):
    """External service error (e.g., Azure OpenAI)."""

    def __init__(self, service: str, detail: str | None = None):
        super().__init__(
            message=f"Error communicating with {service}",
            status_code=502,
            detail=detail,
            code="EXTERNAL_SERVICE_ERROR",
        )


class ConfigurationError(AppException):
    """Configuration is missing or invalid."""

    def __init__(self, detail: str):
        super().__init__(
            message="Configuration error",
            status_code=500,
            detail=detail,
            code="CONFIGURATION_ERROR",
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

    def __init__(self, field: str, message: str, value: str | None = None):
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

    def __init__(self, expression: str, error: str | None = None):
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

    def __init__(self, identifier: str, suggestion: str | None = None):
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


# =============================================================================
# HTTP Exception Wrappers (for consistent API responses)
# =============================================================================


class ForbiddenError(AppException):
    """Access forbidden (403) - user authenticated but lacks permission."""

    def __init__(self, message: str = "Access forbidden", detail: str | None = None):
        super().__init__(
            message=message,
            status_code=403,
            detail=detail or "You do not have permission to perform this action.",
            code="FORBIDDEN",
        )


class UnauthorizedError(AppException):
    """Unauthorized (401) - user not authenticated."""

    def __init__(self, message: str = "Authentication required", detail: str | None = None):
        super().__init__(
            message=message,
            status_code=401,
            detail=detail or "Please log in to access this resource.",
            code="UNAUTHORIZED",
        )


class BadRequestError(AppException):
    """Bad request (400) - invalid input."""

    def __init__(self, message: str, detail: str | None = None):
        super().__init__(
            message=message,
            status_code=400,
            detail=detail,
            code="BAD_REQUEST",
        )


class RateLimitError(AppException):
    """Rate limit exceeded (429)."""

    def __init__(self, retry_after: int | None = None):
        detail = "Please wait before making more requests."
        if retry_after:
            detail = f"Please wait {retry_after} seconds before retrying."
        super().__init__(
            message="Rate limit exceeded",
            status_code=429,
            detail=detail,
            code="RATE_LIMIT_EXCEEDED",
        )
        self.retry_after = retry_after


class ServiceUnavailableError(AppException):
    """Service unavailable (503) - temporary outage."""

    def __init__(self, service: str = "Service", retry_after: int | None = None):
        detail = f"{service} is temporarily unavailable. Please try again later."
        super().__init__(
            message=f"{service} unavailable",
            status_code=503,
            detail=detail,
            code="SERVICE_UNAVAILABLE",
        )
        self.retry_after = retry_after


# =============================================================================
# Smart Query Exceptions
# =============================================================================


class SmartQueryError(AppException):
    """Base exception for Smart Query errors."""

    def __init__(self, message: str, detail: str | None = None):
        super().__init__(
            message=message,
            status_code=400,
            detail=detail,
            code="SMART_QUERY_ERROR",
        )


class QueryValidationError(SmartQueryError):
    """Query validation failed (empty, too short, too long, etc.)."""

    def __init__(self, message: str, detail: str | None = None):
        super().__init__(message=message, detail=detail)
        self.code = "QUERY_VALIDATION_ERROR"


class SessionRequiredError(SmartQueryError):
    """Database session is required but not provided."""

    def __init__(self, operation: str = "query interpretation"):
        super().__init__(
            message=f"Database session required for {operation}",
            detail="A database session must be provided for this operation.",
        )
        self.code = "SESSION_REQUIRED"


class AIInterpretationError(ExternalServiceError):
    """AI interpretation failed."""

    def __init__(self, operation: str, detail: str | None = None):
        super().__init__(
            service="Azure OpenAI",
            detail=detail or f"KI-Service Fehler: {operation} fehlgeschlagen",
        )
        self.code = "AI_INTERPRETATION_ERROR"


class RelationDepthError(SmartQueryError):
    """Relation chain exceeds maximum allowed depth."""

    def __init__(self, max_depth: int):
        super().__init__(
            message=f"Relation chain exceeds maximum depth of {max_depth}",
            detail=f"Relations can only be followed up to {max_depth} levels deep.",
        )
        self.code = "RELATION_DEPTH_EXCEEDED"
