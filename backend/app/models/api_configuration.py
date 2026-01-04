"""Unified API Configuration model.

This model combines the functionality of the former ExternalAPIConfig and APITemplate
into a single, unified configuration for external API integrations.

An APIConfiguration is always linked to a DataSource and defines:
- How to connect to the API (URL, auth, headers)
- What to import (entities, facets, or both)
- How to map API data to entities and facets
- Sync scheduling and lifecycle management
"""

from __future__ import annotations

import enum
import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.data_source import DataSource
    from app.models.entity import Entity
    from external_apis.models.sync_record import SyncRecord


class AuthType(str, enum.Enum):
    """Authentication types supported by external APIs."""

    NONE = "NONE"
    BASIC = "BASIC"
    BEARER = "BEARER"
    API_KEY = "API_KEY"
    OAUTH2 = "OAUTH2"


class ImportMode(str, enum.Enum):
    """Defines what the API sync imports/updates."""

    ENTITIES = "ENTITIES"  # Create/update entities from API data
    FACETS = "FACETS"  # Update facet values on existing entities
    BOTH = "BOTH"  # Create entities AND update facets


class APIType(str, enum.Enum):
    """Type of API protocol/format."""

    REST = "REST"
    GRAPHQL = "GRAPHQL"
    SPARQL = "SPARQL"
    OPARL = "OPARL"


class SyncStatus(str, enum.Enum):
    """Status of the last sync operation."""

    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    RUNNING = "RUNNING"


class APIConfiguration(Base):
    """Unified configuration for external API integration.

    This model stores all configuration needed to connect to an external API,
    map its data to entities and facets, and manage the sync lifecycle.

    Replaces the former ExternalAPIConfig and APITemplate models.
    """

    __tablename__ = "api_configurations"

    __table_args__ = (
        Index("ix_api_configurations_sync_due", "sync_enabled", "last_sync_at"),
        Index("ix_api_configurations_data_source", "data_source_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Required link to DataSource
    data_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # ==========================================================================
    # Connection Configuration
    # ==========================================================================

    api_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=APIType.REST.value,
        comment="API protocol type (rest, graphql, sparql, oparl)",
    )
    endpoint: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        default="",
        comment="API endpoint path (appended to DataSource.base_url)",
    )
    auth_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=AuthType.NONE.value,
    )
    auth_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Authentication config (env var references, not actual secrets)",
    )
    request_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Additional request config (headers, params, pagination)",
    )

    # ==========================================================================
    # Import Mode Configuration
    # ==========================================================================

    import_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ImportMode.ENTITIES.value,
        comment="What to import: entities, facets, or both",
    )

    # ==========================================================================
    # Entity Configuration (for import_mode: entities or both)
    # ==========================================================================

    entity_type_slug: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Target EntityType slug (e.g., wind_project)",
    )
    id_field: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="id",
        comment="API field containing unique identifier",
    )
    name_field: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="name",
        comment="API field containing entity name",
    )
    field_mappings: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Mapping from API fields to entity fields",
    )
    location_fields: Mapped[list[str]] = mapped_column(
        ARRAY(String(255)),
        nullable=False,
        default=list,
        comment="API fields containing location data",
    )

    # ==========================================================================
    # Facet Configuration (for import_mode: facets or both)
    # ==========================================================================

    facet_mappings: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Mapping from API fields to FacetTypes. Format: { 'api_field': { 'facet_type_slug': '...', 'is_history': true } }",
    )

    # ==========================================================================
    # Entity Matching (for facet updates on existing entities)
    # ==========================================================================

    entity_matching: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="How to match API records to entities. Format: { 'match_by': 'name|external_id', 'api_field': '...', 'entity_type_slug': '...' }",
    )

    # ==========================================================================
    # Sync Configuration
    # ==========================================================================

    sync_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    sync_interval_hours: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=24,
    )
    last_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_sync_status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    last_sync_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    last_sync_stats: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Statistics from last sync (records_fetched, entities_matched, facets_updated)",
    )
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Next scheduled sync execution time",
    )

    # ==========================================================================
    # Lifecycle Management
    # ==========================================================================

    mark_missing_inactive: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Mark entities as inactive if missing from API",
    )
    inactive_after_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=7,
        comment="Days after which missing entities are marked inactive",
    )

    # ==========================================================================
    # AI Features
    # ==========================================================================

    ai_linking_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Enable AI-based entity linking",
    )
    link_to_entity_types: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)),
        nullable=False,
        default=list,
        comment="Entity types to link imported entities to",
    )

    # ==========================================================================
    # KI-Discovery Features (from APITemplate)
    # ==========================================================================

    keywords: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Keywords for matching user prompts (KI-Discovery)",
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.8,
        comment="Confidence score (0.0-1.0) for KI-Discovery matching",
    )
    is_template: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether this is a reusable template",
    )
    documentation_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Link to API documentation",
    )

    # ==========================================================================
    # Status
    # ==========================================================================

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    # ==========================================================================
    # Timestamps
    # ==========================================================================

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

    # ==========================================================================
    # Relationships
    # ==========================================================================

    data_source: Mapped[DataSource] = relationship(
        "DataSource",
        back_populates="api_config",
    )

    # Entities created by this configuration
    managed_entities: Mapped[list[Entity]] = relationship(
        "Entity",
        back_populates="api_source",
        foreign_keys="Entity.api_configuration_id",
    )

    # Sync records for tracking individual API records
    sync_records: Mapped[list[SyncRecord]] = relationship(
        "SyncRecord",
        back_populates="api_configuration",
        cascade="all, delete-orphan",
    )

    # ==========================================================================
    # Methods
    # ==========================================================================

    def get_auth_token(self) -> str | None:
        """Get the authentication token from environment variable.

        The auth_config should contain a reference to an environment variable,
        not the actual secret. This method resolves that reference.

        Returns:
            The authentication token, or None if not configured.
        """
        if self.auth_type == AuthType.NONE.value:
            return None

        env_var = self.auth_config.get("token_env_var")
        if env_var:
            return os.environ.get(env_var)

        # For basic auth, might have separate username/password env vars
        username_var = self.auth_config.get("username_env_var")
        password_var = self.auth_config.get("password_env_var")
        if username_var and password_var:
            username = os.environ.get(username_var)
            password = os.environ.get(password_var)
            if username and password:
                import base64

                return base64.b64encode(f"{username}:{password}".encode()).decode()

        return None

    def get_full_url(self) -> str:
        """Get the full API URL by combining DataSource.base_url and endpoint.

        Returns:
            The complete API URL.
        """
        if not self.data_source:
            return self.endpoint

        base = self.data_source.base_url.rstrip("/")
        endpoint = self.endpoint.lstrip("/") if self.endpoint else ""
        return f"{base}/{endpoint}" if endpoint else base

    def is_due_for_sync(self) -> bool:
        """Check if this configuration is due for synchronization.

        Returns:
            True if sync should be performed, False otherwise.
        """
        if not self.sync_enabled or not self.is_active:
            return False

        if self.last_sync_at is None:
            return True

        now = datetime.now(UTC)
        next_sync = self.last_sync_at + timedelta(hours=self.sync_interval_hours)
        return now >= next_sync

    def matches_prompt(self, prompt: str) -> float:
        """Calculate match score for a user prompt (KI-Discovery).

        Args:
            prompt: The user's search prompt.

        Returns:
            A score between 0.0 and 1.0 based on keyword matches.
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
        return f"<APIConfiguration(id={self.id}, import_mode='{self.import_mode}', api_type='{self.api_type}')>"
