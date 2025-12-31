"""EntityVersion model for diff-based versioning of all entities."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class EntityVersion(Base):
    """
    Stores version diffs for any entity.

    Uses diff-based storage to minimize space usage.
    Each record stores only the changes from the previous version.
    Every N versions (default: 10), a full snapshot is stored for
    efficient reconstruction.
    """

    __tablename__ = "entity_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Which entity this version belongs to
    entity_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Model name: Category, DataSource, Entity, etc.",
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    # Version info
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Sequential version number starting at 1",
    )

    # Diff storage (what changed from previous version)
    diff: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Changes from previous version: {field: {old: x, new: y}}",
    )

    # Optional full snapshot for efficient reconstruction
    snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Full entity state snapshot (stored every N versions)",
    )

    # Who made the change
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Denormalized email for when user is deleted",
    )

    # Change metadata
    change_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Optional description of why change was made",
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        lazy="selectin",
    )

    # Indexes for efficient queries
    __table_args__ = (
        # Index for fetching all versions of an entity
        Index("ix_entity_versions_entity", "entity_type", "entity_id"),
        # Index for finding latest version
        Index(
            "ix_entity_versions_entity_version",
            "entity_type",
            "entity_id",
            "version_number",
        ),
    )

    def __repr__(self) -> str:
        return f"<EntityVersion {self.entity_type}:{self.entity_id} v{self.version_number}>"
