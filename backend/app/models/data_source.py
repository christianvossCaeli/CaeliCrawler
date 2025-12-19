"""DataSource model for defining crawl targets."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.crawl_job import CrawlJob
    from app.models.document import Document
    from app.models.change_log import ChangeLog
    from app.models.entity import Entity
    from app.models.data_source_category import DataSourceCategory


class SourceType(str, enum.Enum):
    """Type of data source."""

    WEBSITE = "WEBSITE"
    OPARL_API = "OPARL_API"
    RSS = "RSS"
    CUSTOM_API = "CUSTOM_API"


class SourceStatus(str, enum.Enum):
    """Status of a data source."""

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ERROR = "ERROR"


class DataSource(Base):
    """
    Data source configuration for crawling.

    Can be a website URL, OParl API endpoint, RSS feed, or custom API.
    """

    __tablename__ = "data_sources"
    __table_args__ = (
        UniqueConstraint("category_id", "base_url", name="uq_source_category_url"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Legacy category_id kept for backwards compatibility
    # New sources should use the N:M categories relationship instead
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Legacy primary category - use categories relationship for N:M",
    )
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="FK to entity (municipality/person/organization/event)",
    )

    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name="source_type"),
        nullable=False,
    )
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    api_endpoint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Location for clustering (legacy string fields, prefer location_id FK)
    country: Mapped[Optional[str]] = mapped_column(
        String(2),
        nullable=True,
        index=True,
        comment="ISO 3166-1 alpha-2 country code",
    )
    location_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Location name for result clustering (e.g., 'Münster')",
    )
    region: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Region for broader clustering (e.g., 'Münsterland')",
    )
    admin_level_1: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="State/Region/Bundesland (e.g., 'Nordrhein-Westfalen')",
    )

    # Configuration
    crawl_config: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    auth_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Crawl state
    last_crawl: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_change_detected: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # HTTP conditional request headers (for 304 Not Modified)
    last_modified_header: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="HTTP Last-Modified header from last crawl",
    )
    etag_header: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="HTTP ETag header from last crawl",
    )

    # Status
    status: Mapped[SourceStatus] = mapped_column(
        Enum(SourceStatus, name="source_status"),
        default=SourceStatus.PENDING,
        nullable=False,
        index=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Additional metadata (e.g., Bundesland, Einwohner, coordinates)
    extra_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    # Priority for crawling (higher = more important)
    priority: Mapped[int] = mapped_column(default=0, nullable=False)

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
    # Legacy 1:N relationship (kept for backwards compatibility)
    category: Mapped[Optional["Category"]] = relationship(
        "Category",
        back_populates="data_sources",
        foreign_keys=[category_id],
    )

    # N:M relationship via junction table
    categories: Mapped[List["Category"]] = relationship(
        "Category",
        secondary="data_source_categories",
        back_populates="sources",
        viewonly=True,
    )

    # Junction table entries (for direct access)
    category_links: Mapped[List["DataSourceCategory"]] = relationship(
        "DataSourceCategory",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    entity: Mapped[Optional["Entity"]] = relationship(
        "Entity",
        back_populates="data_sources",
    )
    crawl_jobs: Mapped[List["CrawlJob"]] = relationship(
        "CrawlJob",
        back_populates="source",
        cascade="all, delete-orphan",
    )
    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="source",
        cascade="all, delete-orphan",
    )
    change_logs: Mapped[List["ChangeLog"]] = relationship(
        "ChangeLog",
        back_populates="source",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<DataSource(id={self.id}, name='{self.name}', type={self.source_type})>"
