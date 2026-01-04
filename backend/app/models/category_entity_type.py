"""CategoryEntityType model for N:M relationship between Category and EntityType."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.entity_type import EntityType


class CategoryEntityType(Base):
    """
    Junction table for N:M relationship between Category and EntityType.

    Enables categories to extract and manage multiple EntityTypes,
    with configuration for how each type should be extracted and related.

    Example:
        Category "Events in NRW" can have:
        - Person (primary=False, order=1) - attendees
        - Event (primary=True, order=0) - main entity type
        - Municipality (primary=False, order=2) - locations

    The relation_config defines how entities should be related:
        [
            {"from_type": "person", "to_type": "event", "relation": "attends"},
            {"from_type": "event", "to_type": "municipality", "relation": "located_in"}
        ]
    """

    __tablename__ = "category_entity_types"

    __table_args__ = (UniqueConstraint("category_id", "entity_type_id", name="uq_category_entity_type"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    entity_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entity_types.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="If true, this is the main EntityType for analysis aggregation",
    )

    extraction_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Order in which entity types are extracted (0 = first)",
    )

    extraction_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Configuration for how to extract this entity type from documents",
    )

    relation_config: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        comment="Defines relations to create between this type and others",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    category: Mapped["Category"] = relationship(
        "Category",
        back_populates="entity_type_associations",
    )

    entity_type: Mapped["EntityType"] = relationship(
        "EntityType",
        back_populates="category_associations",
    )

    def __repr__(self) -> str:
        return f"<CategoryEntityType(category_id={self.category_id}, entity_type_id={self.entity_type_id}, is_primary={self.is_primary})>"
