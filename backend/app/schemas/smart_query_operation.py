"""Smart Query Operation schemas for API validation."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class OperationType(str, Enum):
    """Type of Smart Query operation."""

    START_CRAWL = "start_crawl"
    CREATE_CATEGORY_SETUP = "create_category_setup"
    CREATE_ENTITY = "create_entity"
    CREATE_ENTITY_TYPE = "create_entity_type"
    CREATE_FACET = "create_facet"
    CREATE_RELATION = "create_relation"
    FETCH_AND_CREATE_FROM_API = "fetch_and_create_from_api"
    DISCOVER_SOURCES = "discover_sources"
    COMBINED = "combined"
    OTHER = "other"


class SmartQueryOperationCreate(BaseModel):
    """Schema for creating a Smart Query operation record."""

    command_text: str = Field(..., min_length=1, max_length=5000)
    operation_type: OperationType = OperationType.OTHER
    interpretation: Dict[str, Any] = Field(default_factory=dict)
    result_summary: Dict[str, Any] = Field(default_factory=dict)
    display_name: Optional[str] = Field(None, max_length=255)
    was_successful: bool = True


class SmartQueryOperationUpdate(BaseModel):
    """Schema for updating a Smart Query operation (e.g., toggle favorite, rename)."""

    is_favorite: Optional[bool] = None
    display_name: Optional[str] = Field(None, max_length=255)


class SmartQueryOperationResponse(BaseModel):
    """Schema for Smart Query operation response."""

    id: UUID
    user_id: UUID
    command_text: str
    command_hash: str
    operation_type: OperationType
    interpretation: Dict[str, Any]
    result_summary: Dict[str, Any]
    display_name: Optional[str]
    is_favorite: bool
    execution_count: int
    was_successful: bool
    created_at: datetime
    last_executed_at: datetime

    model_config = {"from_attributes": True}


class SmartQueryOperationListResponse(BaseModel):
    """Schema for Smart Query operation list response."""

    items: List[SmartQueryOperationResponse]
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
    result: Dict[str, Any] = Field(default_factory=dict)
