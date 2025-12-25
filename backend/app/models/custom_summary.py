"""Custom Summary model for user-defined dashboard summaries.

Stores KI-generated dashboard configurations that can be automatically updated
via cron schedules or event triggers (crawl completion).
"""

import enum
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.category import Category
    from app.models.crawl_preset import CrawlPreset
    from app.models.summary_widget import SummaryWidget
    from app.models.summary_execution import SummaryExecution
    from app.models.summary_share import SummaryShare


class SummaryStatus(str, enum.Enum):
    """Status of a custom summary."""

    DRAFT = "draft"  # Still being configured
    ACTIVE = "active"  # Active and scheduled
    PAUSED = "paused"  # Temporarily paused
    ARCHIVED = "archived"  # Archived (soft delete)


class SummaryTriggerType(str, enum.Enum):
    """Trigger type for summary updates."""

    MANUAL = "manual"  # Only manual execution
    CRON = "cron"  # Cron-based schedule
    CRAWL_CATEGORY = "crawl_category"  # Triggered after category crawl completes
    CRAWL_PRESET = "crawl_preset"  # Triggered after preset crawl completes


class CustomSummary(Base):
    """
    User-defined summary/dashboard.

    Stores the definition of a KI-generated summary including:
    - Original prompt (for re-interpretation)
    - KI-interpreted configuration (entities, facets, filters)
    - Layout configuration (widget positions)
    - Update trigger settings (cron, events)
    """

    __tablename__ = "custom_summaries"

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
        comment="User-defined name for the summary",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional description",
    )

    # Original prompt (unchanged for re-interpretation)
    original_prompt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Original user prompt for KI interpretation",
    )

    # KI-interpreted configuration
    interpreted_config: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="KI-interpreted structure: theme, entities, facets, filters, time_scope",
    )
    # Example:
    # {
    #     "theme": "bundesliga_table",
    #     "primary_entity_type": "sports_team",
    #     "facet_types": ["points", "goals", "wins"],
    #     "filters": {"league": "1. Bundesliga", "season": "2024/2025"},
    #     "time_scope": "fixed",  # or "rolling"
    #     "time_range": {"start": "2024-07-01", "end": "2025-06-30"}
    # }

    # Layout configuration
    layout_config: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Widget layout and grid configuration",
    )
    # Example:
    # {
    #     "columns": 4,
    #     "row_height": 100
    # }

    # Status
    status: Mapped[SummaryStatus] = mapped_column(
        Enum(SummaryStatus, name="summary_status_enum"),
        nullable=False,
        default=SummaryStatus.DRAFT,
        index=True,
    )

    # Trigger configuration
    trigger_type: Mapped[SummaryTriggerType] = mapped_column(
        Enum(SummaryTriggerType, name="summary_trigger_type_enum"),
        nullable=False,
        default=SummaryTriggerType.MANUAL,
    )
    schedule_cron: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Cron expression for scheduled execution (like CrawlPreset)",
    )
    trigger_category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        comment="Category ID for crawl_category trigger",
    )
    trigger_preset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crawl_presets.id", ondelete="SET NULL"),
        nullable=True,
        comment="CrawlPreset ID for crawl_preset trigger",
    )

    # Scheduling
    schedule_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether scheduled/triggered execution is enabled",
    )
    next_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Next scheduled execution time",
    )

    # Semantic relevance check
    check_relevance: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="KI checks if update is meaningful before executing",
    )
    relevance_threshold: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.3,
        comment="Minimum relevance score for update (0-1)",
    )

    # Dynamic growth
    auto_expand: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Automatically include new relevant data",
    )

    # Statistics
    execution_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total number of executions",
    )
    last_executed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last execution timestamp",
    )
    last_data_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="Hash of last execution data for change detection",
    )

    # Favorite / Sorting
    is_favorite: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether this summary is marked as favorite",
    )
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Custom display order",
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
    user: Mapped["User"] = relationship(
        "User",
        back_populates="custom_summaries",
    )
    trigger_category: Mapped[Optional["Category"]] = relationship(
        "Category",
        foreign_keys=[trigger_category_id],
    )
    trigger_preset: Mapped[Optional["CrawlPreset"]] = relationship(
        "CrawlPreset",
        foreign_keys=[trigger_preset_id],
    )
    widgets: Mapped[List["SummaryWidget"]] = relationship(
        "SummaryWidget",
        back_populates="summary",
        cascade="all, delete-orphan",
        order_by="SummaryWidget.display_order",
    )
    executions: Mapped[List["SummaryExecution"]] = relationship(
        "SummaryExecution",
        back_populates="summary",
        cascade="all, delete-orphan",
        order_by="SummaryExecution.created_at.desc()",
    )
    shares: Mapped[List["SummaryShare"]] = relationship(
        "SummaryShare",
        back_populates="summary",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("ix_custom_summaries_user_status", "user_id", "status"),
        Index("ix_custom_summaries_next_run", "next_run_at", "schedule_enabled"),
        Index("ix_custom_summaries_trigger_category", "trigger_category_id"),
        Index("ix_custom_summaries_trigger_preset", "trigger_preset_id"),
        # Composite index for listing favorites sorted by update time
        Index("ix_custom_summaries_user_favorites", "user_id", "is_favorite", "updated_at"),
    )

    def __repr__(self) -> str:
        return f"<CustomSummary(id={self.id}, name='{self.name}', status={self.status})>"
