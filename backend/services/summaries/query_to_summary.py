"""Service to create Custom Summaries from Smart Query results.

This module enables creating dashboard summaries directly from
Smart Query Plan Mode results, bridging the gap between ad-hoc queries
and persistent dashboards.
"""

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CustomSummary, SummaryWidget
from app.models.custom_summary import SummaryStatus, SummaryTriggerType
from app.models.summary_widget import SummaryWidgetType

logger = structlog.get_logger(__name__)


# Mapping from VisualizationType to SummaryWidgetType
VISUALIZATION_TO_WIDGET_TYPE = {
    "table": SummaryWidgetType.TABLE,
    "bar_chart": SummaryWidgetType.BAR_CHART,
    "line_chart": SummaryWidgetType.LINE_CHART,
    "pie_chart": SummaryWidgetType.PIE_CHART,
    "stat_card": SummaryWidgetType.STAT_CARD,
    "text": SummaryWidgetType.TEXT,
    "comparison": SummaryWidgetType.COMPARISON,
    "map": SummaryWidgetType.MAP,
    "timeline": SummaryWidgetType.TIMELINE,
    "calendar": SummaryWidgetType.CALENDAR,
}


async def create_summary_from_smart_query(
    session: AsyncSession,
    user_id: UUID,
    query_text: str,
    query_result: dict[str, Any],
    name: str | None = None,
    description: str | None = None,
) -> CustomSummary:
    """
    Create a Custom Summary from a Smart Query result.

    This function takes the result of a Smart Query (including data and
    visualization config) and creates a persistent Summary with widgets.

    Args:
        session: Database session
        user_id: Owner's user ID
        query_text: Original Smart Query text (becomes the prompt)
        query_result: Smart Query response containing:
            - data: List of result items
            - visualization: VisualizationConfig
            - interpretation: Query interpretation details
        name: Optional custom name (auto-generated if not provided)
        description: Optional description

    Returns:
        Created CustomSummary with widgets

    Example:
        ```python
        result = await smart_query(session, "Zeige alle Vereine mit Einwohnerzahl")
        summary = await create_summary_from_smart_query(
            session=session,
            user_id=user.id,
            query_text="Zeige alle Vereine mit Einwohnerzahl",
            query_result=result,
            name="Vereinsübersicht",
        )
        ```
    """
    # Extract visualization config
    visualization = query_result.get("visualization", {})
    data = query_result.get("data", [])
    interpretation = query_result.get("interpretation", {})

    # Generate name from query if not provided
    if not name:
        name = _generate_name_from_query(query_text)

    # Build interpreted config from query interpretation
    interpreted_config = _build_interpreted_config(interpretation, query_result)

    # Create the summary
    summary = CustomSummary(
        user_id=user_id,
        name=name,
        description=description,
        original_prompt=query_text,
        interpreted_config=interpreted_config,
        layout_config={"columns": 4, "row_height": 150},
        status=SummaryStatus.ACTIVE,
        trigger_type=SummaryTriggerType.MANUAL,
        schedule_enabled=False,
        check_relevance=True,
        relevance_threshold=0.3,
        auto_expand=False,
        is_favorite=False,
    )
    session.add(summary)
    await session.flush()

    # Create widget from visualization
    widget = _create_widget_from_visualization(
        summary_id=summary.id,
        visualization=visualization,
        query_text=query_text,
        data=data,
        interpretation=interpretation,
    )
    session.add(widget)

    await session.commit()
    await session.refresh(summary)

    logger.info(
        "summary_created_from_smart_query",
        summary_id=str(summary.id),
        user_id=str(user_id),
        query_text=query_text[:100],
        widget_type=widget.widget_type.value,
    )

    return summary


def _generate_name_from_query(query_text: str) -> str:
    """Generate a summary name from the query text."""
    # Remove common question words
    cleaned = query_text.lower()
    for word in ["zeige", "show", "liste", "welche", "was", "wie", "mir", "die", "den", "das", "alle", "bitte"]:
        cleaned = cleaned.replace(word, "")

    cleaned = " ".join(cleaned.split())  # Normalize whitespace
    cleaned = cleaned.strip()

    if not cleaned:
        return "Smart Query Zusammenfassung"

    # Capitalize and limit length
    name = cleaned[0].upper() + cleaned[1:]
    if len(name) > 100:
        name = name[:97] + "..."

    return name


def _build_interpreted_config(
    interpretation: dict[str, Any],
    query_result: dict[str, Any],
) -> dict[str, Any]:
    """Build interpreted_config from Smart Query interpretation."""
    config = {
        "source": "smart_query",
        "theme": interpretation.get("intent", "custom_query"),
        "primary_entity_type": interpretation.get("entity_type"),
        "facet_types": interpretation.get("facet_types", []),
        "filters": interpretation.get("filters", {}),
        "time_scope": "dynamic",  # Smart Query results are dynamic by default
    }

    # Add original query metadata
    config["original_query"] = {
        "text": query_result.get("query_text", ""),
        "intent": interpretation.get("intent"),
        "confidence": interpretation.get("confidence", 1.0),
    }

    return config


def _create_widget_from_visualization(
    summary_id: UUID,
    visualization: dict[str, Any],
    query_text: str,
    data: list[dict[str, Any]],
    interpretation: dict[str, Any],
) -> SummaryWidget:
    """Create a SummaryWidget from Smart Query visualization config."""
    # Get visualization type
    viz_type_str = visualization.get("type", "table")
    widget_type = VISUALIZATION_TO_WIDGET_TYPE.get(viz_type_str, SummaryWidgetType.TABLE)

    # Build query config from interpretation
    query_config = {
        "entity_type": interpretation.get("entity_type"),
        "facet_types": interpretation.get("facet_types", []),
        "filters": interpretation.get("filters", {}),
        "limit": 100,
        "smart_query_text": query_text,  # Store original query for re-execution
    }

    # Add sort config if available
    if visualization.get("sort_column"):
        query_config["sort_by"] = visualization["sort_column"]
        query_config["sort_order"] = visualization.get("sort_order", "desc")

    # Build visualization config
    viz_config = {}

    # Copy relevant visualization settings
    if visualization.get("columns"):
        viz_config["columns"] = visualization["columns"]

    if visualization.get("x_axis"):
        viz_config["x_axis"] = visualization["x_axis"]

    if visualization.get("y_axis"):
        viz_config["y_axis"] = visualization["y_axis"]

    if visualization.get("series"):
        viz_config["series"] = visualization["series"]

    if visualization.get("cards"):
        viz_config["cards"] = visualization["cards"]

    if visualization.get("text_content"):
        viz_config["text_content"] = visualization["text_content"]

    # Determine widget size based on type
    width, height = _get_widget_size(widget_type, len(data))

    return SummaryWidget(
        summary_id=summary_id,
        widget_type=widget_type,
        title=visualization.get("title", "Smart Query Ergebnis"),
        subtitle=visualization.get("subtitle"),
        position_x=0,
        position_y=0,
        width=width,
        height=height,
        query_config=query_config,
        visualization_config=viz_config,
        display_order=0,
    )


def _get_widget_size(widget_type: SummaryWidgetType, data_count: int) -> tuple[int, int]:
    """Determine appropriate widget size based on type and data."""
    # (width, height) in grid units

    if widget_type == SummaryWidgetType.STAT_CARD:
        return (1, 1)  # Small card

    if widget_type == SummaryWidgetType.TEXT:
        return (2, 1)  # Wide but short

    if widget_type in (SummaryWidgetType.PIE_CHART,):
        return (2, 2)  # Square

    if widget_type in (SummaryWidgetType.BAR_CHART, SummaryWidgetType.LINE_CHART):
        return (3, 2)  # Wide chart

    if widget_type == SummaryWidgetType.MAP:
        return (4, 3)  # Full width, tall

    if widget_type == SummaryWidgetType.CALENDAR:
        return (4, 3)  # Full width, tall

    if widget_type == SummaryWidgetType.TABLE:
        # Table size depends on data amount
        if data_count <= 5:
            return (2, 2)
        elif data_count <= 15:
            return (3, 2)
        else:
            return (4, 3)  # Full width for large tables

    # Default
    return (2, 2)


async def add_smart_query_to_existing_summary(
    session: AsyncSession,
    summary_id: UUID,
    user_id: UUID,
    query_text: str,
    query_result: dict[str, Any],
) -> SummaryWidget:
    """
    Add a Smart Query result as a new widget to an existing summary.

    This enables building up complex dashboards from multiple queries.

    Args:
        session: Database session
        summary_id: Target summary ID
        user_id: User ID (for ownership verification)
        query_text: Smart Query text
        query_result: Smart Query response

    Returns:
        Created SummaryWidget

    Raises:
        ValueError: If summary not found or not owned by user
    """
    # Verify ownership
    summary = await session.get(CustomSummary, summary_id)
    if not summary or summary.user_id != user_id:
        raise ValueError(f"Summary {summary_id} not found or access denied")

    visualization = query_result.get("visualization", {})
    data = query_result.get("data", [])
    interpretation = query_result.get("interpretation", {})

    # Get current widget count for positioning
    from sqlalchemy import func, select

    result = await session.execute(
        select(func.count(SummaryWidget.id), func.max(SummaryWidget.display_order)).where(
            SummaryWidget.summary_id == summary_id
        )
    )
    row = result.one()
    widget_count = row[0] or 0
    max_order = row[1] or 0

    # Calculate position (simple grid layout)
    position_x = (widget_count % 2) * 2  # 0 or 2
    position_y = (widget_count // 2) * 2  # 0, 2, 4, ...

    # Create widget
    widget = _create_widget_from_visualization(
        summary_id=summary_id,
        visualization=visualization,
        query_text=query_text,
        data=data,
        interpretation=interpretation,
    )

    # Adjust position
    widget.position_x = position_x
    widget.position_y = position_y
    widget.display_order = max_order + 1

    session.add(widget)
    await session.commit()
    await session.refresh(widget)

    logger.info(
        "widget_added_from_smart_query",
        summary_id=str(summary_id),
        widget_id=str(widget.id),
        query_text=query_text[:100],
    )

    return widget
