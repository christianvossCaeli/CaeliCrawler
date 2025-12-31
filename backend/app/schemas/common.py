"""Common schemas used across the application."""

from typing import Any, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Pagination parameters."""

    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


class PaginatedResponse[T](BaseModel):
    """Generic paginated response."""

    items: list[T]
    total: int
    page: int
    per_page: int
    pages: int

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        per_page: int,
    ) -> "PaginatedResponse[T]":
        pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
        )


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str
    success: bool = True
    data: Any | None = None


class ErrorResponse(BaseModel):
    """Standard error response for API errors.

    Used for 4xx and 5xx responses across all endpoints.

    Attributes:
        error: Human-readable error message
        detail: Additional context or troubleshooting information
        code: Machine-readable error code for programmatic handling
    """

    error: str = Field(..., description="Human-readable error message")
    detail: str | None = Field(None, description="Additional error details")
    code: str | None = Field(None, description="Machine-readable error code")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": "Category not found",
                    "detail": "Category with identifier 'abc123' does not exist",
                    "code": "NOT_FOUND",
                },
                {
                    "error": "Invalid regex pattern",
                    "detail": "Field 'url_pattern': Invalid regex: unbalanced parenthesis",
                    "code": "VALIDATION_ERROR",
                },
            ]
        }
    }


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str
    database: str = "connected"
    redis: str = "connected"
