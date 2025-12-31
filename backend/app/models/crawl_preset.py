"""Crawl Preset model for saved crawl filter configurations.

Stores filter configurations for crawls that can be reused and optionally scheduled.
Unlike Smart Query History which saves AI-interpreted commands, presets store
the exact technical filter configuration for deterministic re-execution.
"""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PresetStatus(str, enum.Enum):
    """Status of a crawl preset."""

    ACTIVE = "active"
    ARCHIVED = "archived"


class CrawlPreset(Base):
    """
    Saved crawl filter configuration for deterministic re-execution.

    Presets store the exact filter configuration used for crawls, allowing
    users to quickly repeat crawls without AI interpretation variability.
    Optionally supports cron-based scheduling for automatic recurring crawls.
    """

    __tablename__ = "crawl_presets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Owner
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Basic info
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="User-defined name for the preset",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional description of what this preset does",
    )

    # Filter configuration (mirrors StartCrawlRequest filters)
    filters: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Filter configuration: category_id, tags, entity_type, admin_level_1, entity_filters, etc.",
    )

    # Scheduling
    schedule_cron: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Cron expression for scheduled execution, e.g., '0 6 * * 1' (Monday 6 AM)",
    )
    schedule_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether scheduled execution is enabled",
    )
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Next scheduled execution time",
    )

    # Statistics
    usage_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of times manually executed",
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last manual execution timestamp",
    )
    last_scheduled_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last scheduled execution timestamp",
    )

    # Meta
    is_favorite: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether this preset is marked as a favorite",
    )
    status: Mapped[PresetStatus] = mapped_column(
        Enum(PresetStatus, name="crawl_preset_status_enum"),
        nullable=False,
        default=PresetStatus.ACTIVE,
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
    user = relationship("User", foreign_keys=[user_id])

    def get_filter_summary(self) -> str:
        """Get a human-readable summary of the filter configuration."""
        parts = []

        if self.filters.get("category_id"):
            parts.append("Category Filter")

        if self.filters.get("tags"):
            tags = self.filters["tags"]
            if isinstance(tags, list):
                parts.append(f"Tags: {', '.join(tags[:3])}")
                if len(tags) > 3:
                    parts.append(f"+{len(tags) - 3}")

        if self.filters.get("entity_type"):
            parts.append(f"Type: {self.filters['entity_type']}")

        if self.filters.get("admin_level_1"):
            parts.append(f"Region: {self.filters['admin_level_1']}")

        if self.filters.get("limit"):
            parts.append(f"Limit: {self.filters['limit']}")

        return " | ".join(parts) if parts else "No filters"

    def __repr__(self) -> str:
        return f"<CrawlPreset(id={self.id}, name='{self.name}', user_id={self.user_id})>"
