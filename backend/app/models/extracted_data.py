"""ExtractedData model for AI-extracted information."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

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
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.category import Category
    from app.models.entity import Entity


class ExtractedData(Base):
    """
    AI-extracted structured data from documents.

    Stores the results of AI analysis, including confidence scores
    and human verification status.
    """

    __tablename__ = "extracted_data"
    __table_args__ = (
        Index("ix_extracted_data_search_vector", "search_vector", postgresql_using="gin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Extraction type (e.g., "windkraft_analyse", "bebauungsplan")
    extraction_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    # Extracted structured content
    extracted_content: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    search_vector: Mapped[Optional[str]] = mapped_column(
        TSVECTOR,
        nullable=True,
    )

    # AI metadata
    confidence_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )  # 0.0 - 1.0
    ai_model_used: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    ai_prompt_version: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    raw_ai_response: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    tokens_used: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Human verification
    human_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    human_corrections: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )
    verified_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relevance score for this category's purpose
    relevance_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )  # 0.0 - 1.0

    # Entity references - AI-extracted entity references
    entity_references: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
        comment="AI-extracted entity references: [{entity_type, entity_name, entity_id, role, confidence}]",
    )

    # Primary entity link (resolved from entity_references)
    primary_entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Primary entity referenced in this extraction",
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
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="extracted_data",
    )
    category: Mapped["Category"] = relationship("Category")
    primary_entity: Mapped[Optional["Entity"]] = relationship(
        "Entity",
        foreign_keys=[primary_entity_id],
    )

    @property
    def is_high_confidence(self) -> bool:
        """Check if extraction has high confidence (>= 0.8)."""
        return self.confidence_score is not None and self.confidence_score >= 0.8

    @property
    def final_content(self) -> Dict[str, Any]:
        """Get final content (with human corrections if available)."""
        if self.human_corrections:
            merged = self.extracted_content.copy()
            merged.update(self.human_corrections)
            return merged
        return self.extracted_content

    def __repr__(self) -> str:
        return f"<ExtractedData(id={self.id}, type={self.extraction_type}, confidence={self.confidence_score})>"
