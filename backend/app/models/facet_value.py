"""FacetValue model for storing facet instances."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.entity import Entity
    from app.models.facet_type import FacetType
    from app.models.category import Category
    from app.models.document import Document


class FacetValue(Base):
    """
    Concrete facet value instance for an entity.

    Stores extracted information (pain points, contacts, events, etc.)
    with metadata about source, confidence, and verification.
    """

    __tablename__ = "facet_values"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    facet_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("facet_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Category context in which this was extracted",
    )

    # Value
    value: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment="Structured value according to FacetType.value_schema",
    )
    text_representation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Text representation for search and display",
    )

    # Time-based fields
    event_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Date of the event/action (for time-based facets)",
    )
    valid_from: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this value becomes valid",
    )
    valid_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this value expires",
    )

    # Source tracking
    source_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Original URL where this was found",
    )

    # AI metadata
    confidence_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        index=True,
    )
    ai_model_used: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    # Human verification
    human_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    verified_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    human_corrections: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Manual corrections to the extracted value",
    )

    # Occurrence tracking
    occurrence_count: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="How often this value was found",
    )
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
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
    entity: Mapped["Entity"] = relationship(
        "Entity",
        back_populates="facet_values",
    )
    facet_type: Mapped["FacetType"] = relationship(
        "FacetType",
        back_populates="facet_values",
    )
    category: Mapped[Optional["Category"]] = relationship("Category")
    source_document: Mapped[Optional["Document"]] = relationship("Document")

    @property
    def final_value(self) -> Dict[str, Any]:
        """Get final value (with human corrections if available)."""
        if self.human_corrections:
            merged = self.value.copy()
            merged.update(self.human_corrections)
            return merged
        return self.value

    @property
    def is_future(self) -> bool:
        """Check if this is a future event."""
        if self.event_date:
            return self.event_date > datetime.now(self.event_date.tzinfo)
        return False

    @property
    def is_valid(self) -> bool:
        """Check if this value is currently valid (within valid_from/valid_until)."""
        now = datetime.now()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True

    def __repr__(self) -> str:
        return f"<FacetValue(id={self.id}, entity={self.entity_id}, type={self.facet_type_id})>"
