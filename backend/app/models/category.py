"""Category model for organizing data sources."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.database import Base

if TYPE_CHECKING:
    from app.models.data_source import DataSource
    from app.models.api_export import ApiExport
    from app.models.entity_type import EntityType
    from app.models.user import User
    from app.models.category_entity_type import CategoryEntityType


class Category(Base):
    """
    Category for organizing data sources.

    Examples: "Gemeinden", "Landkreise", "Bundesländer"
    Each category defines what to search for and how to analyze found documents.
    """

    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    name_embedding: Mapped[Optional[List[float]]] = mapped_column(
        Vector(1536),
        nullable=True,
        comment="Embedding vector for semantic similarity search",
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Purpose defines what we're looking for (e.g., "Windkraft-Restriktionen")
    purpose: Mapped[str] = mapped_column(Text, nullable=False)

    # Search configuration
    search_terms: Mapped[List[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    document_types: Mapped[List[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )

    # URL filtering (applied to all sources in this category)
    url_include_patterns: Mapped[List[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        comment="Regex patterns - URLs must match at least one (if set)",
    )
    url_exclude_patterns: Mapped[List[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        comment="Regex patterns - URLs matching any will be skipped",
    )

    # Language configuration
    languages: Mapped[List[str]] = mapped_column(
        JSONB,
        default=lambda: ["de"],
        nullable=False,
        comment="Language codes (ISO 639-1) for this category, e.g. ['de', 'en']",
    )

    # AI extraction prompt template for this category
    ai_extraction_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Extraction handler: 'default' (entity_facet_service) or 'event' (event_extraction_service)
    extraction_handler: Mapped[str] = mapped_column(
        String(50),
        default="default",
        nullable=False,
        comment="Handler for processing extractions: 'default' or 'event'",
    )

    # Display configuration for results view
    display_fields: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Configuration for result display columns: {columns: [{key, label, type, width}]}",
    )

    # Entity reference extraction configuration
    entity_reference_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Config for entity reference extraction: {entity_types: ['territorial-entity', 'person']}",
    )

    # Scheduling (cron expression)
    schedule_cron: Mapped[str] = mapped_column(
        String(100),
        default="0 2 * * *",  # Daily at 2 AM
        nullable=False,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Ownership & Visibility
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who created this category",
    )
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who owns this category",
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="If true, visible to all users. If false, only visible to owner.",
    )

    # Target EntityType for extracted entities
    target_entity_type_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entity_types.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="EntityType for extracted entities (e.g., 'event-besuche-nrw')",
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
    # Legacy 1:N relationship (for backwards compatibility)
    data_sources: Mapped[List["DataSource"]] = relationship(
        "DataSource",
        back_populates="category",
        foreign_keys="DataSource.category_id",
        passive_deletes=True,
    )

    # N:M relationship via junction table
    sources: Mapped[List["DataSource"]] = relationship(
        "DataSource",
        secondary="data_source_categories",
        back_populates="categories",
        viewonly=True,
    )

    api_exports: Mapped[List["ApiExport"]] = relationship(
        "ApiExport",
        back_populates="category",
    )

    # Ownership relationships
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_id],
    )
    owner: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[owner_id],
    )

    # Target EntityType relationship (legacy 1:1 for backwards compatibility)
    target_entity_type: Mapped[Optional["EntityType"]] = relationship(
        "EntityType",
        foreign_keys=[target_entity_type_id],
    )

    # N:M relationship to EntityTypes via junction table (Multi-EntityType Support)
    entity_type_associations: Mapped[List["CategoryEntityType"]] = relationship(
        "CategoryEntityType",
        back_populates="category",
        cascade="all, delete-orphan",
        order_by="CategoryEntityType.extraction_order",
    )

    @property
    def entity_types(self) -> List["EntityType"]:
        """Get all associated EntityTypes in extraction order."""
        return [assoc.entity_type for assoc in self.entity_type_associations]

    @property
    def primary_entity_type(self) -> Optional["EntityType"]:
        """Get the primary EntityType for this category."""
        for assoc in self.entity_type_associations:
            if assoc.is_primary:
                return assoc.entity_type
        # Fallback to legacy target_entity_type
        return self.target_entity_type

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name='{self.name}')>"
