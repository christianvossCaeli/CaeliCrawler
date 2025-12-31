"""FacetValue model for storing facet instances."""

import enum
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FacetValueSourceType(str, enum.Enum):
    """Source type for facet values - indicates how the value was created."""

    DOCUMENT = "DOCUMENT"  # Extracted from a crawled document via AI
    MANUAL = "MANUAL"  # Manually created by user via UI dialog
    PYSIS = "PYSIS"  # Generated from PySis analysis
    SMART_QUERY = "SMART_QUERY"  # Created via Smart Query write mode
    AI_ASSISTANT = "AI_ASSISTANT"  # Created via AI assistant chat
    IMPORT = "IMPORT"  # Imported from external data (CSV, API, etc.)
    ATTACHMENT = "ATTACHMENT"  # Extracted from user-uploaded attachment via AI

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.document import Document
    from app.models.entity import Entity
    from app.models.entity_attachment import EntityAttachment
    from app.models.facet_type import FacetType


class FacetValue(Base):
    """
    Concrete facet value instance for an entity.

    Stores extracted information (pain points, contacts, events, etc.)
    with metadata about source, confidence, and verification.
    """

    __tablename__ = "facet_values"

    # Composite indexes for frequently queried column combinations
    __table_args__ = (
        # For facet queries by entity and type
        Index("ix_facet_values_entity_type", "entity_id", "facet_type_id"),
        # For facet queries by entity and active status
        Index("ix_facet_values_entity_active", "entity_id", "is_active"),
        # For time-based facet queries
        Index("ix_facet_values_entity_event_date", "entity_id", "event_date"),
    )

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
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Category context in which this was extracted",
    )

    # Value
    value: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment="Structured value according to FacetType.value_schema",
    )
    text_representation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Text representation for search and display",
    )
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        nullable=True,
        comment="Full-text search vector (auto-generated from text_representation)",
    )
    text_embedding: Mapped[list[float] | None] = mapped_column(
        Vector(1536),
        nullable=True,
        comment="Embedding vector for semantic similarity search",
    )

    # Time-based fields
    event_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Date of the event/action (for time-based facets)",
    )
    valid_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this value becomes valid",
    )
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this value expires",
    )

    # Source tracking
    source_type: Mapped[FacetValueSourceType] = mapped_column(
        Enum(FacetValueSourceType),
        default=FacetValueSourceType.DOCUMENT,
        nullable=False,
        index=True,
        comment="How this value was created (document, manual, pysis, etc.)",
    )
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_attachment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entity_attachments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Source attachment for ATTACHMENT source type",
    )
    source_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Original URL where this was found",
    )

    # Entity reference (optional link to another entity, e.g., a Person for a contact facet)
    target_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional reference to another Entity (e.g., Person for contact facet)",
    )

    # AI metadata
    confidence_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        index=True,
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
        index=True,
    )
    verified_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    human_corrections: Mapped[dict[str, Any] | None] = mapped_column(
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
        foreign_keys=[entity_id],
    )
    facet_type: Mapped["FacetType"] = relationship(
        "FacetType",
        back_populates="facet_values",
    )
    category: Mapped[Optional["Category"]] = relationship("Category")
    source_document: Mapped[Optional["Document"]] = relationship("Document")
    source_attachment: Mapped[Optional["EntityAttachment"]] = relationship("EntityAttachment")
    target_entity: Mapped[Optional["Entity"]] = relationship(
        "Entity",
        foreign_keys=[target_entity_id],
        lazy="joined",
    )

    @property
    def final_value(self) -> dict[str, Any]:
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
        now = datetime.now(UTC)
        if self.valid_from and now < self.valid_from:
            return False
        return not (self.valid_until and now > self.valid_until)

    def __repr__(self) -> str:
        return f"<FacetValue(id={self.id}, entity={self.entity_id}, type={self.facet_type_id})>"
