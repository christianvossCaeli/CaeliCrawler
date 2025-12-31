"""EntityRelation model for storing relationships between entities."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.entity import Entity
    from app.models.relation_type import RelationType


class EntityRelation(Base):
    """
    Concrete relationship instance between two entities.

    Examples:
    - Person "Max Mueller" works_for Organization "Gemeinde Musterstadt"
    - Person "Max Mueller" attends Event "Husum Wind 2025"
    """

    __tablename__ = "entity_relations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    relation_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("relation_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationship attributes
    attributes: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment='Relation-specific attributes {"role": "Buergermeister", "since": "2020-01-01"}',
    )

    # Validity period
    valid_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this relationship starts",
    )
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this relationship ends",
    )

    # Source tracking
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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
    relation_type: Mapped["RelationType"] = relationship(
        "RelationType",
        back_populates="relations",
    )
    source_entity: Mapped["Entity"] = relationship(
        "Entity",
        back_populates="source_relations",
        foreign_keys=[source_entity_id],
    )
    target_entity: Mapped["Entity"] = relationship(
        "Entity",
        back_populates="target_relations",
        foreign_keys=[target_entity_id],
    )
    source_document: Mapped[Optional["Document"]] = relationship("Document")

    # Unique constraint and composite indexes
    __table_args__ = (
        UniqueConstraint(
            "relation_type_id",
            "source_entity_id",
            "target_entity_id",
            name="uq_entity_relation_type_source_target",
        ),
        # Composite indexes for frequently queried column combinations
        Index("ix_entity_relations_source_active", "source_entity_id", "is_active"),
        Index("ix_entity_relations_target_active", "target_entity_id", "is_active"),
        Index("ix_entity_relations_type_active", "relation_type_id", "is_active"),
    )

    @property
    def is_valid(self) -> bool:
        """Check if this relationship is currently valid based on validity period."""
        now = datetime.now(UTC)
        if self.valid_from and now < self.valid_from:
            return False
        return not (self.valid_until and now > self.valid_until)

    def __repr__(self) -> str:
        return f"<EntityRelation(id={self.id}, type={self.relation_type_id}, source={self.source_entity_id}, target={self.target_entity_id})>"
