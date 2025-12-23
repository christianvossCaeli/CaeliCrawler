"""API Template model for saved API discovery configurations.

Stores validated API configurations that can be reused for future discoveries.
Templates can be created automatically (from successful KI-First discoveries)
or manually by administrators.
"""

import enum
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class APIType(str, enum.Enum):
    """Type of API."""

    REST = "REST"
    GRAPHQL = "GRAPHQL"
    SPARQL = "SPARQL"
    OPARL = "OPARL"


class TemplateStatus(str, enum.Enum):
    """Status of an API template."""

    ACTIVE = "ACTIVE"  # Template is active and usable
    INACTIVE = "INACTIVE"  # Disabled by user
    FAILED = "FAILED"  # Last validation failed
    PENDING = "PENDING"  # Awaiting validation


class APITemplate(Base):
    """
    Saved API template for KI-First discovery.

    Templates are created when:
    1. A KI-generated API suggestion is successfully validated
    2. An admin manually creates a template

    Templates allow quick reuse of known working APIs without
    needing to regenerate via KI each time.
    """

    __tablename__ = "api_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Basic info
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Human-readable name for the template",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Description of what this API provides",
    )

    # API configuration
    api_type: Mapped[APIType] = mapped_column(
        Enum(APIType, name="api_type_enum"),
        nullable=False,
        default=APIType.REST,
    )
    base_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Base URL of the API",
    )
    endpoint: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="API endpoint path",
    )
    documentation_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Link to API documentation",
    )

    # Authentication
    auth_required: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    auth_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Authentication configuration (type, header name, etc.)",
    )

    # Field mapping (for Entity fields)
    field_mapping: Mapped[Dict[str, str]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Mapping from API fields to standard fields (e.g., teamName -> name)",
    )

    # Facet mapping (for scheduled API-to-Facet sync)
    facet_mapping: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Mapping from API fields to Facet types. Format: { 'api_field': { 'facet_type_slug': '...', 'is_history': true } }",
    )

    # Entity matching configuration (for Facet sync)
    entity_matching: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="How to match API records to entities. Format: { 'match_by': 'name|external_id', 'api_field': 'teamName', 'entity_type_slug': '...' }",
    )

    # Keywords for matching user prompts
    keywords: Mapped[List[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        comment="Keywords to match against user prompts (e.g., bundesliga, fußball)",
    )

    # Default tags to apply to imported sources
    default_tags: Mapped[List[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        comment="Tags automatically applied to sources from this API",
    )

    # Status and validation
    status: Mapped[TemplateStatus] = mapped_column(
        Enum(TemplateStatus, name="template_status_enum"),
        default=TemplateStatus.PENDING,
        nullable=False,
        index=True,
    )
    last_validated: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last successful validation timestamp",
    )
    last_validation_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message from last failed validation",
    )
    validation_item_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of items found in last validation",
    )

    # Scheduling for API-to-Facet sync
    schedule_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether scheduled syncing is enabled",
    )
    schedule_cron: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Cron expression for scheduled sync (e.g., '0 6 * * 1' = Monday 6 AM)",
    )
    next_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Next scheduled sync execution time",
    )
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last successful facet sync timestamp",
    )
    last_sync_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Status of last sync: 'success', 'partial', 'failed'",
    )
    last_sync_stats: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Statistics from last sync (records_fetched, entities_matched, facets_updated)",
    )

    # Usage tracking
    usage_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of times this template was used",
    )
    last_used: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Confidence score (from KI or manual rating)
    confidence: Mapped[float] = mapped_column(
        Float,
        default=0.8,
        nullable=False,
        comment="Confidence score (0.0-1.0)",
    )

    # Source of template
    source: Mapped[str] = mapped_column(
        String(50),
        default="manual",
        nullable=False,
        comment="How template was created: 'ai_generated' or 'manual'",
    )

    # Who created it (optional)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])

    @property
    def full_url(self) -> str:
        """Get full API URL."""
        base = self.base_url.rstrip("/")
        endpoint = self.endpoint if self.endpoint.startswith("/") else f"/{self.endpoint}"
        return f"{base}{endpoint}"

    def matches_prompt(self, prompt: str) -> float:
        """
        Calculate match score for a user prompt.

        Returns a score 0.0-1.0 based on keyword matches.
        """
        if not self.keywords:
            return 0.0

        prompt_lower = prompt.lower()
        matches = sum(1 for kw in self.keywords if kw.lower() in prompt_lower)

        if matches == 0:
            return 0.0

        # Score based on percentage of keywords matched
        return min(1.0, matches / len(self.keywords) * 1.5)

    def __repr__(self) -> str:
        return f"<APITemplate(id={self.id}, name='{self.name}', api_type={self.api_type})>"
