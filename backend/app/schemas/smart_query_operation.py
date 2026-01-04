"""Smart Query Operation schemas for API validation."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class OperationType(str, Enum):
    """Type of Smart Query operation."""

    START_CRAWL = "START_CRAWL"
    CREATE_CATEGORY_SETUP = "CREATE_CATEGORY_SETUP"
    CREATE_ENTITY = "CREATE_ENTITY"
    CREATE_ENTITY_TYPE = "CREATE_ENTITY_TYPE"
    CREATE_FACET = "CREATE_FACET"
    CREATE_RELATION = "CREATE_RELATION"
    FETCH_AND_CREATE_FROM_API = "FETCH_AND_CREATE_FROM_API"
    DISCOVER_SOURCES = "DISCOVER_SOURCES"
    COMBINED = "COMBINED"
    OTHER = "OTHER"


class SmartQueryOperationCreate(BaseModel):
    """Schema for creating a Smart Query operation record."""

    command_text: str = Field(..., min_length=1, max_length=5000)
    operation_type: OperationType = OperationType.OTHER
    interpretation: dict[str, Any] = Field(default_factory=dict)
    result_summary: dict[str, Any] = Field(default_factory=dict)
    display_name: str | None = Field(None, max_length=255)
    was_successful: bool = True


class SmartQueryOperationUpdate(BaseModel):
    """Schema for updating a Smart Query operation (e.g., toggle favorite, rename)."""

    is_favorite: bool | None = None
    display_name: str | None = Field(None, max_length=255)


class SmartQueryOperationResponse(BaseModel):
    """Schema for Smart Query operation response."""

    id: UUID
    user_id: UUID
    command_text: str
    command_hash: str
    operation_type: OperationType
    interpretation: dict[str, Any]
    result_summary: dict[str, Any]
    display_name: str | None
    is_favorite: bool
    execution_count: int
    was_successful: bool
    created_at: datetime
    last_executed_at: datetime

    model_config = {"from_attributes": True}


class SmartQueryOperationListResponse(BaseModel):
    """Schema for Smart Query operation list response."""

    items: list[SmartQueryOperationResponse]
    total: int
    page: int
    per_page: int
    pages: int


class SmartQueryFavoriteToggleResponse(BaseModel):
    """Schema for favorite toggle response."""

    id: UUID
    is_favorite: bool
    message: str


class SmartQueryExecuteResponse(BaseModel):
    """Schema for re-execute response."""

    operation_id: UUID
    success: bool
    message: str
    result: dict[str, Any] = Field(default_factory=dict)
