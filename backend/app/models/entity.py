"""Entity model for generic entity instances."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

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
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.data_source import DataSource
    from app.models.entity_attachment import EntityAttachment
    from app.models.entity_relation import EntityRelation
    from app.models.entity_type import EntityType
    from app.models.facet_value import FacetValue
    from app.models.reminder import Reminder
    from app.models.user import User
    from external_apis.models.external_api_config import ExternalAPIConfig


class Entity(Base):
    """
    Generic entity instance (Municipality, Person, Organization, Event, etc.).

    Replaces the hardcoded Location model with a flexible entity system
    that can represent any type of entity.
    """

    __tablename__ = "entities"

    # Composite indexes for frequently queried column combinations
    __table_args__ = (
        # For list queries filtering by type and active status
        Index("ix_entities_type_active", "entity_type_id", "is_active"),
        # For entity lookup by normalized name within a type
        Index("ix_entities_type_name_normalized", "entity_type_id", "name_normalized"),
        # For hierarchy queries
        Index("ix_entities_hierarchy_path", "hierarchy_path"),
        # For user's entities queries
        Index("ix_entities_owner_active", "owner_id", "is_active"),
        # For location-based filtering
        Index("ix_entities_country_admin1", "country", "admin_level_1"),
        Index("ix_entities_admin1_admin2", "admin_level_1", "admin_level_2"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    entity_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entity_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Identification
    name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
        comment="Primary name",
    )
    name_normalized: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
        comment="Normalized name for search (lowercase, no special chars)",
    )
    slug: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
        comment="URL-safe identifier",
    )
    external_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="External reference (AGS, UUID, etc.)",
    )

    # Hierarchy (for hierarchical entity types)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Parent entity (self-referencing)",
    )
    hierarchy_path: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        index=True,
        comment="Materialized path: /DE/Bayern/Muenchen",
    )
    hierarchy_level: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="0=root, 1=level1, etc.",
    )

    # Location fields for efficient filtering
    country: Mapped[Optional[str]] = mapped_column(
        String(2),
        nullable=True,
        index=True,
        comment="ISO 3166-1 alpha-2 country code (DE, GB, etc.)",
    )
    admin_level_1: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="First-level admin division (Bundesland, Region, State)",
    )
    admin_level_2: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Second-level admin division (Landkreis, District)",
    )

    # Core attributes (type-specific)
    core_attributes: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Type-specific attributes (population, area_km2, email, etc.)",
    )

    # Geo-coordinates (optional)
    latitude: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    longitude: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    # Ownership (optional user association)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who created this entity",
    )
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who owns/is responsible for this entity",
    )

    # External API sync tracking
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this entity was last seen in external API sync",
    )
    external_source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("external_api_configs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="ExternalAPIConfig that created/manages this entity",
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
    entity_type: Mapped["EntityType"] = relationship(
        "EntityType",
        back_populates="entities",
    )
    parent: Mapped[Optional["Entity"]] = relationship(
        "Entity",
        remote_side="Entity.id",
        back_populates="children",
        foreign_keys=[parent_id],
    )
    children: Mapped[List["Entity"]] = relationship(
        "Entity",
        back_populates="parent",
        foreign_keys=[parent_id],
    )
    facet_values: Mapped[List["FacetValue"]] = relationship(
        "FacetValue",
        back_populates="entity",
        cascade="all, delete-orphan",
    )
    # Relations where this entity is the source
    source_relations: Mapped[List["EntityRelation"]] = relationship(
        "EntityRelation",
        back_populates="source_entity",
        foreign_keys="EntityRelation.source_entity_id",
        cascade="all, delete-orphan",
    )
    # Relations where this entity is the target
    target_relations: Mapped[List["EntityRelation"]] = relationship(
        "EntityRelation",
        back_populates="target_entity",
        foreign_keys="EntityRelation.target_entity_id",
        cascade="all, delete-orphan",
    )
    # Data sources linked to this entity
    data_sources: Mapped[List["DataSource"]] = relationship(
        "DataSource",
        back_populates="entity",
        passive_deletes=True,  # Let DB handle SET NULL on delete
    )
    # User who created this entity
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_id],
    )
    # User who owns this entity
    owner: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[owner_id],
    )
    # Reminders linked to this entity
    reminders: Mapped[List["Reminder"]] = relationship(
        "Reminder",
        back_populates="entity",
        cascade="all, delete-orphan",
    )
    # File attachments linked to this entity
    attachments: Mapped[List["EntityAttachment"]] = relationship(
        "EntityAttachment",
        back_populates="entity",
        cascade="all, delete-orphan",
        order_by="EntityAttachment.created_at.desc()",
    )
    # External API source that manages this entity
    external_source: Mapped[Optional["ExternalAPIConfig"]] = relationship(
        "ExternalAPIConfig",
        back_populates="managed_entities",
        foreign_keys=[external_source_id],
    )

    @property
    def display_name(self) -> str:
        """Get display name with hierarchy context if available."""
        if self.hierarchy_path:
            parts = self.hierarchy_path.strip("/").split("/")
            if len(parts) > 1:
                return f"{self.name} ({parts[-2]})"
        return self.name

    def __repr__(self) -> str:
        return f"<Entity(id={self.id}, name='{self.name}', type={self.entity_type_id})>"
