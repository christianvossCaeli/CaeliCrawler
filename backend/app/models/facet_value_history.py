"""FacetValueHistory model for storing time-series data points."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.facet_value import FacetValueSourceType

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.entity import Entity
    from app.models.facet_type import FacetType


class FacetValueHistory(Base):
    """
    Time-series data point for HISTORY facet types.

    Stores individual data points with timestamps for tracking values
    over time (e.g., stock prices, population counts, budget data).
    Supports multiple tracks per entity+facet combination.
    """

    __tablename__ = "facet_value_history"

    # Composite indexes for frequently queried column combinations
    __table_args__ = (
        # For queries by entity and facet type
        Index("ix_fvh_entity_type", "entity_id", "facet_type_id"),
        # For queries including track
        Index("ix_fvh_entity_type_track", "entity_id", "facet_type_id", "track_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Entity and FacetType references
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

    # Track identification for multi-track support
    track_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="default",
        comment="Track identifier (e.g., 'actual', 'forecast', 'budget')",
    )

    # The actual data point
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="When this value was recorded/measured",
    )
    value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="The numeric value",
    )
    value_label: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Formatted value for display (e.g., '1.234,56 EUR')",
    )
    annotations: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Additional metadata (notes, trend, etc.)",
    )

    # Source tracking
    source_type: Mapped[FacetValueSourceType] = mapped_column(
        default=FacetValueSourceType.MANUAL,
        nullable=False,
        index=True,
        comment="How this value was created",
    )
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Original URL where this was found",
    )

    # AI metadata
    confidence_score: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        nullable=False,
        comment="Confidence score (0-1)",
    )
    ai_model_used: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Human verification
    human_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    verified_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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
    entity: Mapped["Entity"] = relationship("Entity")
    facet_type: Mapped["FacetType"] = relationship("FacetType")
    source_document: Mapped[Optional["Document"]] = relationship("Document")

    def __repr__(self) -> str:
        return (
            f"<FacetValueHistory(id={self.id}, entity={self.entity_id}, "
            f"track={self.track_key}, recorded_at={self.recorded_at}, value={self.value})>"
        )
