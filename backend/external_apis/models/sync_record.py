"""SyncRecord model for tracking external API record sync state."""

import enum
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.api_configuration import APIConfiguration
    from app.models.entity import Entity


class RecordStatus(str, enum.Enum):
    """Status of a sync record."""

    ACTIVE = "active"
    """Record is present in the API and synced."""

    UPDATED = "updated"
    """Record was updated in the last sync."""

    MISSING = "missing"
    """Record was not found in the API (temporarily missing)."""

    ARCHIVED = "archived"
    """Record has been missing for extended period and is archived."""


class SyncRecord(Base):
    """Track individual record sync state and history.

    Each SyncRecord represents one record from an external API.
    It tracks when the record was first/last seen, detects changes
    via content hash, and manages the lifecycle of missing records.
    """

    __tablename__ = "sync_records"

    __table_args__ = (
        UniqueConstraint(
            "api_configuration_id",
            "external_id",
            name="uq_sync_record_config_external_id",
        ),
        Index(
            "ix_sync_records_missing",
            "api_configuration_id",
            "sync_status",
            "missing_since",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Foreign Keys
    api_configuration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("api_configurations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # External Identification
    external_id: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
        comment="ID from the external API",
    )

    # Sync State
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    last_modified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Modification timestamp from API (if available)",
    )
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SHA256 hash for change detection",
    )

    # Status
    sync_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=RecordStatus.ACTIVE.value,
        index=True,
    )
    missing_since: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the record was first not found in API",
    )

    # Raw Data Cache
    raw_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Last fetched data from API",
    )

    # Entity Linking Results
    linked_entity_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)),
        nullable=False,
        default=list,
        comment="IDs of entities linked via entity linking service",
    )
    linking_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Metadata about entity linking (confidence, method, etc.)",
    )

    # Error Tracking
    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    error_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
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
    api_configuration: Mapped["APIConfiguration"] = relationship(
        "APIConfiguration",
        back_populates="sync_records",
    )
    entity: Mapped[Optional["Entity"]] = relationship(
        "Entity",
        foreign_keys=[entity_id],
    )

    def mark_seen(self, content_hash: str, raw_data: dict[str, Any]) -> bool:
        """Mark this record as seen in the current sync.

        Args:
            content_hash: New content hash.
            raw_data: New raw data from API.

        Returns:
            True if the record was updated (content changed), False otherwise.
        """

        was_updated = self.content_hash != content_hash
        self.last_seen_at = datetime.now(UTC)
        self.content_hash = content_hash
        self.raw_data = raw_data
        self.sync_status = RecordStatus.UPDATED.value if was_updated else RecordStatus.ACTIVE.value
        self.missing_since = None
        self.last_error = None
        return was_updated

    def mark_missing(self) -> None:
        """Mark this record as missing from the API."""

        if self.sync_status != RecordStatus.MISSING.value:
            self.missing_since = datetime.now(UTC)
        self.sync_status = RecordStatus.MISSING.value

    def mark_archived(self) -> None:
        """Mark this record as archived (extended absence)."""
        self.sync_status = RecordStatus.ARCHIVED.value

    def __repr__(self) -> str:
        return f"<SyncRecord(id={self.id}, external_id='{self.external_id}', status='{self.sync_status}')>"
