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
from typing import List, Literal, Optional, Set
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

# Valid extraction handlers
VALID_EXTRACTION_HANDLERS = ("default", "event")

# Cron expression regex pattern (5 or 6 fields)
CRON_PATTERN = re.compile(
    r"^(\*|([0-9]|[1-5][0-9])(-([0-9]|[1-5][0-9]))?(,([0-9]|[1-5][0-9])(-([0-9]|[1-5][0-9]))?)*(/[0-9]+)?)\s+"  # minute
    r"(\*|([0-9]|1[0-9]|2[0-3])(-([0-9]|1[0-9]|2[0-3]))?(,([0-9]|1[0-9]|2[0-3])(-([0-9]|1[0-9]|2[0-3]))?)*(/[0-9]+)?)\s+"  # hour
    r"(\*|([1-9]|[12][0-9]|3[01])(-([1-9]|[12][0-9]|3[01]))?(,([1-9]|[12][0-9]|3[01])(-([1-9]|[12][0-9]|3[01]))?)*(/[0-9]+)?)\s+"  # day of month
    r"(\*|([1-9]|1[0-2])(-([1-9]|1[0-2]))?(,([1-9]|1[0-2])(-([1-9]|1[0-2]))?)*(/[0-9]+)?)\s+"  # month
    r"(\*|([0-6])(-([0-6]))?(,([0-6])(-([0-6]))?)*(/[0-9]+)?)$"  # day of week
)

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
    """
    if cron is None:
        return None

    cron = cron.strip()
    if not cron:
        return None

    # Check field count (should be 5)
    fields = cron.split()
    if len(fields) != 5:
        raise ValueError(
            f"Invalid cron expression: expected 5 fields (minute hour day month weekday), got {len(fields)}"
        )

    # Validate with regex pattern
    if not CRON_PATTERN.match(cron):
        raise ValueError(
            f"Invalid cron expression format. Examples: '0 2 * * *' (daily at 2 AM), "
            f"'*/15 * * * *' (every 15 min), '0 0 * * 0' (weekly on Sunday)"
        )

    return cron


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
    extraction_handler: Literal["default", "event"] = Field(
        default="default",
        description="Handler for processing extractions: 'default' (entity_facet_service) or 'event' (event_extraction_service)",
    )
    schedule_cron: str = Field(default="0 2 * * *", description="Cron expression for scheduled crawls")
    is_active: bool = Field(default=True, description="Whether category is active")

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
    extraction_handler: Optional[Literal["default", "event"]] = None
    schedule_cron: Optional[str] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None
    target_entity_type_id: Optional[UUID] = None

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


class CategoryResponse(CategoryBase):
    """Schema for category response.

    Contains all category data plus computed fields like source_count and document_count.
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
