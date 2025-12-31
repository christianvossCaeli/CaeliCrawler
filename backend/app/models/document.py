"""Document model for storing crawled documents."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.crawl_job import CrawlJob
    from app.models.data_source import DataSource
    from app.models.extracted_data import ExtractedData


class ProcessingStatus(str, enum.Enum):
    """Processing status of a document."""

    PENDING = "PENDING"
    DOWNLOADING = "DOWNLOADING"
    PROCESSING = "PROCESSING"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    FILTERED = "FILTERED"  # Skipped due to relevance filter (not wind-energy related)
    NEEDS_REVIEW = "NEEDS_REVIEW"  # No keywords found, manual review required


class Document(Base):
    """
    Crawled document record.

    Stores metadata and extracted text from PDFs, HTML pages, and other documents.
    """

    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("source_id", "file_hash", name="uq_document_source_hash"),
        Index("idx_documents_search", "search_vector", postgresql_using="gin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    crawl_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crawl_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Document info
    document_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # PDF, HTML, DOC, DOCX, etc.
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)

    # File storage
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )  # SHA256
    file_size: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Extracted content
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        nullable=True,
    )

    # Processing status
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, name="processing_status"),
        default=ProcessingStatus.PENDING,
        nullable=False,
        index=True,
    )
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    downloaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Document date (extracted from content or metadata)
    document_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Page-based analysis tracking
    page_analysis_status: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        default=None,
    )  # "pending", "partial", "complete", "needs_review"
    relevant_pages: Mapped[list[int] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
    )  # Pages with keyword matches (sorted by relevance score)
    analyzed_pages: Mapped[list[int] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
    )  # Pages already sent to LLM
    total_relevant_pages: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=None,
    )  # Total count of relevant pages (for UI hint)
    page_analysis_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )  # User-facing note (e.g., "15 weitere relevante Seiten verfügbar")

    # Relationships
    source: Mapped["DataSource"] = relationship(
        "DataSource",
        back_populates="documents",
    )
    category: Mapped["Category"] = relationship("Category")
    crawl_job: Mapped[Optional["CrawlJob"]] = relationship(
        "CrawlJob",
        back_populates="documents",
    )
    extracted_data: Mapped[list["ExtractedData"]] = relationship(
        "ExtractedData",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    @property
    def is_processed(self) -> bool:
        """Check if document has been processed."""
        return self.processing_status == ProcessingStatus.COMPLETED

    @property
    def file_extension(self) -> str:
        """Get file extension from document type."""
        return self.document_type.lower()

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, type={self.document_type}, status={self.processing_status})>"
