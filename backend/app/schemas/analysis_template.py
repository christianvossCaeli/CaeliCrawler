"""AnalysisTemplate schemas for API validation."""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


def generate_slug(name: str) -> str:
    """Generate URL-friendly slug from name."""
    slug = name.lower()
    slug = re.sub(
        r"[äöüß]",
        lambda m: {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}[m.group()],
        slug,
    )
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug


class FacetConfig(BaseModel):
    """Configuration for a facet within an analysis template."""

    facet_type_slug: str = Field(..., description="Facet type slug")
    enabled: bool = Field(default=True, description="Whether this facet is enabled")
    display_order: int = Field(default=0, description="Display order")
    label: Optional[str] = Field(None, description="Custom label override")
    time_filter: Optional[str] = Field(None, description="Time filter: all, future_only, past_only")
    custom_prompt: Optional[str] = Field(None, description="Custom AI extraction prompt")


class AggregationConfig(BaseModel):
    """Configuration for aggregation in an analysis template."""

    group_by: str = Field(default="entity", description="Group results by: entity, facet_type, time")
    show_relations: List[str] = Field(default_factory=list, description="Relation type slugs to show")
    sort_by: str = Field(default="name", description="Sort results by")
    sort_order: str = Field(default="asc", description="Sort order: asc, desc")


class DisplayConfig(BaseModel):
    """Configuration for display in an analysis template."""

    columns: List[str] = Field(default_factory=list, description="Columns to show in list view")
    default_sort: str = Field(default="name", description="Default sort column")
    show_hierarchy: bool = Field(default=True, description="Show hierarchy navigation")
    show_map: bool = Field(default=False, description="Show map view")


class AnalysisTemplateBase(BaseModel):
    """Base analysis template schema with common fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Display name")
    description: Optional[str] = Field(None, description="Description")

    # Associations
    category_id: Optional[UUID] = Field(None, description="Category this template is for")
    primary_entity_type_id: UUID = Field(..., description="Primary entity type ID")

    # Configuration
    facet_config: List[FacetConfig] = Field(default_factory=list, description="Facet configurations")
    aggregation_config: AggregationConfig = Field(
        default_factory=AggregationConfig,
        description="Aggregation configuration",
    )
    display_config: DisplayConfig = Field(
        default_factory=DisplayConfig,
        description="Display configuration",
    )

    # AI configuration
    extraction_prompt_template: Optional[str] = Field(None, description="Combined AI prompt template")

    # Status
    is_default: bool = Field(default=False, description="Default template for this category")
    is_active: bool = Field(default=True, description="Whether template is active")
    display_order: int = Field(default=0, description="Order in UI lists")


class AnalysisTemplateCreate(AnalysisTemplateBase):
    """Schema for creating a new analysis template."""

    slug: Optional[str] = Field(None, description="URL-friendly slug (auto-generated if not provided)")

    @field_validator("slug", mode="before")
    @classmethod
    def generate_slug_if_empty(cls, v, info):
        if not v and "name" in info.data:
            return generate_slug(info.data["name"])
        return v


class AnalysisTemplateUpdate(BaseModel):
    """Schema for updating an analysis template."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category_id: Optional[UUID] = None
    primary_entity_type_id: Optional[UUID] = None
    facet_config: Optional[List[FacetConfig]] = None
    aggregation_config: Optional[AggregationConfig] = None
    display_config: Optional[DisplayConfig] = None
    extraction_prompt_template: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None


class AnalysisTemplateResponse(AnalysisTemplateBase):
    """Schema for analysis template response."""

    id: UUID
    slug: str
    is_system: bool
    created_at: datetime
    updated_at: datetime

    # Nested info
    category_name: Optional[str] = Field(None, description="Category name")
    primary_entity_type_name: Optional[str] = Field(None, description="Primary entity type name")
    primary_entity_type_slug: Optional[str] = Field(None, description="Primary entity type slug")

    model_config = {"from_attributes": True}


class AnalysisTemplateListResponse(BaseModel):
    """Schema for analysis template list response."""

    items: List[AnalysisTemplateResponse]
    total: int
