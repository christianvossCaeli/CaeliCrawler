"""Category schemas for API validation."""

import re
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


def generate_slug(name: str) -> str:
    """Generate URL-friendly slug from name."""
    slug = name.lower()
    slug = re.sub(r"[äöüß]", lambda m: {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}[m.group()], slug)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug


class CategoryBase(BaseModel):
    """Base category schema with common fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Category name")
    description: Optional[str] = Field(None, description="Category description")
    purpose: str = Field(..., min_length=1, description="Purpose of this category (e.g., 'Windkraft-Restriktionen analysieren')")
    search_terms: List[str] = Field(default_factory=list, description="Search terms for this category")
    document_types: List[str] = Field(default_factory=list, description="Document types to search for")

    # URL filtering (applied to all sources in this category)
    url_include_patterns: List[str] = Field(
        default_factory=list,
        description="Regex patterns - URLs must match at least one (if set)",
    )
    url_exclude_patterns: List[str] = Field(
        default_factory=list,
        description="Regex patterns - URLs matching any will be skipped",
    )

    # Language configuration
    languages: List[str] = Field(
        default_factory=lambda: ["de"],
        description="Language codes (ISO 639-1) for this category, e.g. ['de', 'en']",
    )

    ai_extraction_prompt: Optional[str] = Field(None, description="Custom AI extraction prompt")
    extraction_handler: str = Field(
        default="default",
        description="Handler for processing extractions: 'default' (entity_facet_service) or 'event' (event_extraction_service)",
    )
    schedule_cron: str = Field(default="0 2 * * *", description="Cron expression for scheduled crawls")
    is_active: bool = Field(default=True, description="Whether category is active")

    # Visibility
    is_public: bool = Field(
        default=False,
        description="If true, visible to all users. If false, only visible to owner.",
    )

    # Target EntityType for extracted entities
    target_entity_type_id: Optional[UUID] = Field(
        None,
        description="EntityType for extracted entities (e.g., 'event-besuche-nrw')",
    )


class CategoryCreate(CategoryBase):
    """Schema for creating a new category."""

    slug: Optional[str] = Field(None, description="URL-friendly slug (auto-generated if not provided)")

    @field_validator("slug", mode="before")
    @classmethod
    def generate_slug_if_empty(cls, v, info):
        if not v and "name" in info.data:
            return generate_slug(info.data["name"])
        return v


class CategoryUpdate(BaseModel):
    """Schema for updating a category."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    purpose: Optional[str] = None
    search_terms: Optional[List[str]] = None
    document_types: Optional[List[str]] = None
    url_include_patterns: Optional[List[str]] = None
    url_exclude_patterns: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    ai_extraction_prompt: Optional[str] = None
    extraction_handler: Optional[str] = None
    schedule_cron: Optional[str] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None
    target_entity_type_id: Optional[UUID] = None


class CategoryResponse(CategoryBase):
    """Schema for category response."""

    id: UUID
    slug: str
    created_at: datetime
    updated_at: datetime

    # Ownership
    created_by_id: Optional[UUID] = Field(None, description="User who created this category")
    owner_id: Optional[UUID] = Field(None, description="User who owns this category")

    # Computed fields
    source_count: int = Field(default=0, description="Number of data sources")
    document_count: int = Field(default=0, description="Number of documents")

    model_config = {"from_attributes": True}


class CategoryListResponse(BaseModel):
    """Schema for category list response."""

    items: List[CategoryResponse]
    total: int
    page: int
    per_page: int
    pages: int


class CategoryStats(BaseModel):
    """Statistics for a category."""

    id: UUID
    name: str
    source_count: int
    document_count: int
    extracted_count: int
    last_crawl: Optional[datetime]
    active_jobs: int
