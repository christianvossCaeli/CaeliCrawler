"""RelationType model for defining types of entity relationships."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.entity_type import EntityType
    from app.models.entity_relation import EntityRelation


class Cardinality(str, enum.Enum):
    """Cardinality of a relationship."""

    ONE_TO_ONE = "1:1"
    ONE_TO_MANY = "1:n"
    MANY_TO_ONE = "n:1"
    MANY_TO_MANY = "n:m"


class RelationType(Base):
    """
    Defines a type of relationship between entities.

    Examples:
    - Person works_for Organization
    - Person attends Event
    - Event located_in Municipality
    """

    __tablename__ = "relation_types"

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
        comment="URL-safe identifier (e.g., 'works_for', 'attends')",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Display name (e.g., 'arbeitet fuer')",
    )
    name_inverse: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Inverse display name (e.g., 'beschaeftigt')",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Entity type constraints
    source_entity_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entity_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Which entity type can be the source",
    )
    target_entity_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entity_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Which entity type can be the target",
    )

    # Cardinality
    cardinality: Mapped[str] = mapped_column(
        String(10),
        default=Cardinality.MANY_TO_MANY.value,
        nullable=False,
    )

    # Attribute schema for relationship properties
    attribute_schema: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment='Schema for relation attributes {"role": "string", "since": "date"}',
    )

    # UI Configuration
    icon: Mapped[str] = mapped_column(
        String(100),
        default="mdi-link",
        nullable=False,
    )
    color: Mapped[str] = mapped_column(
        String(20),
        default="#607D8B",
        nullable=False,
    )
    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
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
    source_entity_type: Mapped["EntityType"] = relationship(
        "EntityType",
        foreign_keys=[source_entity_type_id],
    )
    target_entity_type: Mapped["EntityType"] = relationship(
        "EntityType",
        foreign_keys=[target_entity_type_id],
    )
    relations: Mapped[List["EntityRelation"]] = relationship(
        "EntityRelation",
        back_populates="relation_type",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<RelationType(slug='{self.slug}', name='{self.name}')>"
