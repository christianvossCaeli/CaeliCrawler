"""Category schemas for API validation.

This module provides Pydantic schemas for Category CRUD operations with
comprehensive validation for:
- Regex patterns (URL filters)
- ISO 639-1 language codes
- Cron expressions (scheduling)
- Extraction handler types

Example usage:
    >>> from app.schemas.category import CategoryCreate
    >>> category = CategoryCreate(
    ...     name="Windkraft-Analyse",
    ...     purpose="Analysiere Windkraft-Dokumente in NRW",
    ...     languages=["de", "en"],
    ...     extraction_handler="default",
    ... )
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Set
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.utils.cron import normalize_cron_expression

# Valid extraction handlers
VALID_EXTRACTION_HANDLERS = ("default", "event")

# Known ISO 639-1 language codes
VALID_LANGUAGE_CODES: Set[str] = {
    "de", "en", "fr", "nl", "it", "es", "pl", "da", "pt", "sv",
    "no", "fi", "cs", "hu", "ro", "bg", "el", "tr", "ru", "uk",
    "ar", "zh", "ja", "ko"
}


def generate_slug(name: str) -> str:
    """Generate URL-friendly slug from name."""
    slug = name.lower()
    slug = re.sub(r"[äöüß]", lambda m: {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}[m.group()], slug)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug


def _validate_regex_patterns_impl(
    patterns: Optional[List[str]],
    allow_none: bool = False,
) -> Optional[List[str]]:
    """
    Shared implementation for regex pattern validation.

    Args:
        patterns: List of regex patterns to validate
        allow_none: If True, return None for None input (for update schemas)
                   If False, return empty list for None input (for create schemas)

    Returns:
        Validated list of patterns, None, or empty list based on allow_none
    """
    if patterns is None:
        return None if allow_none else []

    validated = []
    for pattern in patterns:
        if pattern:
            try:
                re.compile(pattern)
                validated.append(pattern)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern '{pattern}': {e}")
    return validated


def _validate_languages_impl(
    languages: Optional[List[str]],
    allow_none: bool = False,
) -> Optional[List[str]]:
    """
    Shared implementation for ISO 639-1 language code validation.

    Args:
        languages: List of language codes to validate
        allow_none: If True, return None for None/empty input (for update schemas)
                   If False, return ["de"] as default (for create schemas)

    Returns:
        Validated list of language codes

    Raises:
        ValueError: If any language code is not a valid 2-letter code
    """
    if languages is None:
        return None if allow_none else ["de"]

    validated = []
    for lang in languages:
        if lang:
            code = lang.lower().strip()
            if len(code) != 2:
                raise ValueError(
                    f"Invalid language code '{lang}': must be a 2-letter ISO 639-1 code"
                )
            # Accept valid codes and unknown 2-letter codes (for flexibility)
            validated.append(code)

    if not validated:
        return None if allow_none else ["de"]
    return validated


def _validate_cron_expression(cron: Optional[str]) -> Optional[str]:
    """
    Validate cron expression format.

    Supports standard 5-field cron format:
    - minute (0-59)
    - hour (0-23)
    - day of month (1-31)
    - month (1-12)
    - day of week (0-6, where 0 = Sunday)

    Also supports optional seconds as a 6th leading field:
    - second (0-59)

    Args:
        cron: Cron expression string (e.g., "0 2 * * *" for daily at 2 AM)

    Returns:
        Validated cron expression or None

    Raises:
        ValueError: If cron expression is invalid

    Examples:
        >>> _validate_cron_expression("0 2 * * *")  # Daily at 2 AM
        '0 2 * * *'
        >>> _validate_cron_expression("*/15 * * * *")  # Every 15 minutes
        '*/15 * * * *'
        >>> _validate_cron_expression("0 0 1 * *")  # Monthly on 1st at midnight
        '0 0 1 * *'
        >>> _validate_cron_expression("*/15 * * * * *")  # Every 15 seconds
        '*/15 * * * * *'
    """
    if cron is None:
        return None

    cron = cron.strip()
    if not cron:
        return None

    return normalize_cron_expression(cron)


class _CategoryFieldsMixin(BaseModel):
    """Shared fields for Category schemas (without validators)."""

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
    extraction_handler: Literal["default", "event"] = Field(
        default="default",
        description="Handler for processing extractions: 'default' (entity_facet_service) or 'event' (event_extraction_service)",
    )
    schedule_cron: str = Field(
        default="0 2 * * *",
        description="Cron expression for scheduled crawls (5 or 6 fields, seconds optional)",
    )
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

    # Display configuration for results view
    display_fields: Optional[Dict[str, Any]] = Field(
        None,
        description="Configuration for result display columns: {columns: [{key, label, type, width}]}",
    )

    # Entity reference extraction configuration
    entity_reference_config: Optional[Dict[str, Any]] = Field(
        None,
        description="Config for entity reference extraction: {entity_types: ['territorial-entity']}",
    )


class CategoryBase(_CategoryFieldsMixin):
    """Base category schema with common fields and validators for input."""

    @field_validator("url_include_patterns", "url_exclude_patterns", mode="before")
    @classmethod
    def validate_regex_patterns(cls, v: Optional[List[str]]) -> List[str]:
        """Validate that all patterns are valid regex expressions."""
        return _validate_regex_patterns_impl(v, allow_none=False)

    @field_validator("languages", mode="before")
    @classmethod
    def validate_languages(cls, v: Optional[List[str]]) -> List[str]:
        """Validate ISO 639-1 language codes."""
        return _validate_languages_impl(v, allow_none=False)

    @field_validator("schedule_cron", mode="before")
    @classmethod
    def validate_schedule_cron(cls, v: Optional[str]) -> str:
        """Validate cron expression format."""
        if v is None:
            return "0 2 * * *"  # Default: daily at 2 AM
        validated = _validate_cron_expression(v)
        return validated if validated else "0 2 * * *"


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
    extraction_handler: Optional[Literal["default", "event"]] = None
    schedule_cron: Optional[str] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None
    target_entity_type_id: Optional[UUID] = None
    display_fields: Optional[Dict[str, Any]] = None
    entity_reference_config: Optional[Dict[str, Any]] = None

    @field_validator("url_include_patterns", "url_exclude_patterns", mode="before")
    @classmethod
    def validate_regex_patterns(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate that all patterns are valid regex expressions."""
        return _validate_regex_patterns_impl(v, allow_none=True)

    @field_validator("languages", mode="before")
    @classmethod
    def validate_languages(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate ISO 639-1 language codes."""
        return _validate_languages_impl(v, allow_none=True)


class CategoryResponse(_CategoryFieldsMixin):
    """Schema for category response.

    Contains all category data plus computed fields like source_count and document_count.

    Note: Inherits from _CategoryFieldsMixin (without validators) to allow reading
    existing data that may contain invalid regex patterns.
    """

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

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "name": "Windkraft-Restriktionen NRW",
                    "slug": "windkraft-restriktionen-nrw",
                    "description": "Analyse kommunaler Windkraft-Entscheidungen in NRW",
                    "purpose": "Identifiziere Restriktionen und Hindernisse für Windkraftprojekte",
                    "search_terms": ["windkraft", "windenergie", "flächennutzungsplan"],
                    "document_types": ["html", "pdf"],
                    "url_include_patterns": [".*beschluss.*", ".*protokoll.*"],
                    "url_exclude_patterns": [".*archiv.*"],
                    "languages": ["de"],
                    "extraction_handler": "default",
                    "schedule_cron": "0 2 * * *",
                    "is_active": True,
                    "is_public": True,
                    "source_count": 42,
                    "document_count": 1337,
                    "created_at": "2025-01-15T10:30:00Z",
                    "updated_at": "2025-01-20T14:22:00Z",
                }
            ]
        },
    }


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


# =============================================================================
# AI Setup Preview Schemas
# =============================================================================


class EntityTypeSuggestion(BaseModel):
    """Suggested EntityType for AI setup - can be new or existing."""

    id: Optional[UUID] = Field(None, description="UUID if existing, None if new")
    name: str = Field(..., description="EntityType name")
    slug: str = Field(..., description="EntityType slug")
    name_plural: str = Field(..., description="Plural name")
    description: str = Field(..., description="Description")
    icon: str = Field(default="mdi-folder", description="Material Design icon")
    color: str = Field(default="#2196F3", description="Color hex code")
    attribute_schema: dict = Field(default_factory=dict, description="JSON schema for attributes")
    is_new: bool = Field(default=True, description="True if this would create a new EntityType")


class FacetTypeSuggestion(BaseModel):
    """Suggested FacetType for AI setup - can be new or existing."""

    id: Optional[UUID] = Field(None, description="UUID if existing, None if new")
    name: str = Field(..., description="FacetType name")
    slug: str = Field(..., description="FacetType slug")
    name_plural: str = Field(..., description="Plural name")
    description: str = Field(..., description="Description")
    value_type: str = Field(default="text", description="Value type (text, number, date, etc.)")
    value_schema: dict = Field(default_factory=dict, description="JSON schema for values")
    icon: str = Field(default="mdi-tag", description="Material Design icon")
    color: str = Field(default="#4CAF50", description="Color hex code")
    is_new: bool = Field(default=True, description="True if this would create a new FacetType")
    selected: bool = Field(default=True, description="Whether this facet type is selected for creation")


class CategoryAiSetupPreview(BaseModel):
    """
    Preview response for AI-generated category setup.

    Contains suggestions that the user can review and modify before saving.
    """

    # Suggested EntityType
    suggested_entity_type: EntityTypeSuggestion = Field(
        ..., description="Suggested EntityType configuration"
    )

    # List of existing EntityTypes user can choose instead
    existing_entity_types: List[EntityTypeSuggestion] = Field(
        default_factory=list,
        description="Existing EntityTypes that might be suitable",
    )

    # Suggested FacetTypes
    suggested_facet_types: List[FacetTypeSuggestion] = Field(
        default_factory=list,
        description="Suggested FacetTypes for this category",
    )

    # Existing FacetTypes that might be reusable
    existing_facet_types: List[FacetTypeSuggestion] = Field(
        default_factory=list,
        description="Existing FacetTypes that could be reused",
    )

    # Generated extraction prompt
    suggested_extraction_prompt: str = Field(
        ..., description="AI-generated extraction prompt"
    )

    # Generated search terms
    suggested_search_terms: List[str] = Field(
        default_factory=list,
        description="Suggested search terms",
    )

    # Generated URL patterns
    suggested_url_include_patterns: List[str] = Field(
        default_factory=list,
        description="Suggested URL include patterns",
    )
    suggested_url_exclude_patterns: List[str] = Field(
        default_factory=list,
        description="Suggested URL exclude patterns",
    )

    # Reasoning/explanation for suggestions
    reasoning: str = Field(
        default="",
        description="AI explanation for the suggestions",
    )


class CategoryAiSetupRequest(BaseModel):
    """Request for generating AI setup preview for a category."""

    name: str = Field(..., min_length=1, max_length=255, description="Category name")
    purpose: str = Field(..., min_length=1, description="Purpose/intent for this category")
    description: Optional[str] = Field(None, description="Optional additional description")


class CategoryCreateWithAiSetup(CategoryCreate):
    """
    Extended category creation schema that includes AI setup selections.

    This is used when the user has reviewed the AI preview and selected
    what EntityType/FacetTypes to create or reuse.
    """

    # EntityType selection
    create_new_entity_type: bool = Field(
        default=True,
        description="If true, create new EntityType from ai_entity_type_config",
    )
    use_existing_entity_type_id: Optional[UUID] = Field(
        None,
        description="If create_new_entity_type is false, use this existing EntityType",
    )
    ai_entity_type_config: Optional[EntityTypeSuggestion] = Field(
        None,
        description="EntityType config to create (if create_new_entity_type is true)",
    )

    # FacetTypes to create
    facet_types_to_create: List[FacetTypeSuggestion] = Field(
        default_factory=list,
        description="New FacetTypes to create and associate with the EntityType",
    )

    # Existing FacetTypes to associate
    facet_type_ids_to_associate: List[UUID] = Field(
        default_factory=list,
        description="Existing FacetType IDs to associate with the EntityType",
    )

    @model_validator(mode="after")
    def validate_entity_type_selection(self):
        """Ensure either new EntityType config or existing ID is provided."""
        if self.create_new_entity_type:
            if not self.ai_entity_type_config:
                raise ValueError(
                    "ai_entity_type_config required when create_new_entity_type is true"
                )
        else:
            if not self.use_existing_entity_type_id:
                raise ValueError(
                    "use_existing_entity_type_id required when create_new_entity_type is false"
                )
        return self
