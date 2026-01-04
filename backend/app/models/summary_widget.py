"""Summary Widget model for dashboard widgets.

Each widget represents a visualization component within a custom summary,
with its own query configuration and position in the grid layout.
"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.custom_summary import CustomSummary


class SummaryWidgetType(str, enum.Enum):
    """Types of dashboard widgets."""

    TABLE = "table"
    BAR_CHART = "bar_chart"
    LINE_CHART = "line_chart"
    PIE_CHART = "pie_chart"
    STAT_CARD = "stat_card"
    TEXT = "text"
    COMPARISON = "comparison"
    TIMELINE = "timeline"
    MAP = "map"
    CALENDAR = "calendar"


class SummaryWidget(Base):
    """
    Widget within a custom summary.

    Each widget has:
    - Type (table, chart, etc.)
    - Grid position (x, y, w, h)
    - Query configuration (which entities/facets to display)
    - Visualization configuration (styling, axes, columns)
    """

    __tablename__ = "summary_widgets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    summary_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("custom_summaries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Widget type - use values_callable to store lowercase values in DB
    widget_type: Mapped[SummaryWidgetType] = mapped_column(
        Enum(
            SummaryWidgetType,
            name="summary_widget_type_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )

    # Title and description
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Widget title displayed in header",
    )
    subtitle: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Optional subtitle or description",
    )

    # Grid position (for vue3-grid-layout)
    position_x: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="X position in grid (columns from left)",
    )
    position_y: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Y position in grid (rows from top)",
    )
    width: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=2,
        comment="Width in grid columns",
    )
    height: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=2,
        comment="Height in grid rows",
    )

    # Query configuration (which data to fetch)
    query_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Query configuration: entity_type, facets, filters, sort, limit",
    )
    # Example:
    # {
    #     "entity_type": "sports_team",
    #     "facet_types": ["points", "goals_for", "goals_against"],
    #     "filters": {"league": "1. Bundesliga"},
    #     "sort_by": "facets.points.value",
    #     "sort_order": "desc",
    #     "limit": 18,
    #     "aggregate": null,  # or "count", "sum", "avg"
    #     "group_by": null    # or field name
    # }

    # Visualization configuration (how to display)
    visualization_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Visualization config: columns, axes, colors, etc.",
    )
    # Example for table:
    # {
    #     "columns": [
    #         {"field": "name", "label": "Team", "sortable": true},
    #         {"field": "facets.points", "label": "Punkte", "sortable": true}
    #     ],
    #     "show_pagination": true,
    #     "rows_per_page": 10
    # }
    # Example for bar_chart:
    # {
    #     "x_axis": {"field": "name", "label": "Team"},
    #     "y_axis": {"field": "facets.points", "label": "Punkte"},
    #     "color": "#1976d2",
    #     "horizontal": false
    # }

    # Sort order within summary
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Order for widgets at same position",
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
    summary: Mapped["CustomSummary"] = relationship(
        "CustomSummary",
        back_populates="widgets",
    )

    # Indexes
    __table_args__ = (
        Index("ix_summary_widgets_summary_order", "summary_id", "display_order"),
    )

    def __repr__(self) -> str:
        return f"<SummaryWidget(id={self.id}, type={self.widget_type}, title='{self.title}')>"
