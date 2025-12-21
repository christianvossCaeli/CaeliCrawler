"""EntityType model for defining types of entities."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.entity import Entity
    from app.models.facet_type import FacetType
    from app.models.relation_type import RelationType
    from app.models.user import User
    from app.models.category_entity_type import CategoryEntityType


class EntityType(Base):
    """
    Defines a type of entity (e.g., Municipality, Person, Organization, Event).

    EntityTypes are the foundation of the flexible analysis system, allowing
    different kinds of entities to be tracked and analyzed.
    """

    __tablename__ = "entity_types"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Identification
    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="URL-safe identifier (e.g., 'municipality', 'person')",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Display name (e.g., 'Gemeinde', 'Person')",
    )
    name_plural: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Plural form (e.g., 'Gemeinden', 'Personen')",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # UI Configuration
    icon: Mapped[str] = mapped_column(
        String(100),
        default="mdi-help-circle",
        nullable=False,
        comment="Material Design Icon name",
    )
    color: Mapped[str] = mapped_column(
        String(20),
        default="#607D8B",
        nullable=False,
        comment="Hex color for UI",
    )
    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Order in UI lists",
    )

    # Capabilities
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Can serve as primary aggregation level in analysis",
    )
    supports_hierarchy: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Has hierarchical structure (like Location)",
    )
    hierarchy_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment='Hierarchy configuration {"levels": ["country", "admin_level_1", ...]}',
    )

    # Schema for entity attributes
    attribute_schema: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="JSON Schema defining core_attributes structure",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="System-defined type (cannot be deleted)",
    )

    # Ownership & Visibility
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who created this entity type",
    )
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who owns this entity type",
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="If true, visible to all users. If false, only visible to owner.",
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
    entities: Mapped[List["Entity"]] = relationship(
        "Entity",
        back_populates="entity_type",
        cascade="all, delete-orphan",
    )
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_id],
    )
    owner: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[owner_id],
    )

    # N:M relationship to Categories via junction table (Multi-EntityType Support)
    category_associations: Mapped[List["CategoryEntityType"]] = relationship(
        "CategoryEntityType",
        back_populates="entity_type",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<EntityType(slug='{self.slug}', name='{self.name}')>"
