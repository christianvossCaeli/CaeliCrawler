"""Auto-Expand Service for Custom Summaries.

This module automatically suggests and adds new widgets when
new relevant data types or facets are discovered during execution.
"""

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CustomSummary,
    FacetType,
    SummaryWidget,
)
from app.models.summary_widget import SummaryWidgetType

logger = structlog.get_logger(__name__)


class WidgetSuggestion:
    """Represents a suggested widget to add."""

    def __init__(
        self,
        widget_type: SummaryWidgetType,
        title: str,
        subtitle: str | None = None,
        query_config: dict[str, Any] | None = None,
        reason: str = "",
        confidence: float = 0.5,
    ):
        self.widget_type = widget_type
        self.title = title
        self.subtitle = subtitle
        self.query_config = query_config or {}
        self.reason = reason
        self.confidence = confidence

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "widget_type": self.widget_type.value,
            "title": self.title,
            "subtitle": self.subtitle,
            "query_config": self.query_config,
            "reason": self.reason,
            "confidence": self.confidence,
        }


async def analyze_for_expansion(
    session: AsyncSession,
    summary: CustomSummary,
    execution_data: dict[str, Any],
) -> list[WidgetSuggestion]:
    """
    Analyze execution results to find expansion opportunities.

    Detects:
    1. New facet types not currently in any widget
    2. Related entity types with data
    3. Opportunities for additional visualization types

    Args:
        session: Database session
        summary: The summary being analyzed
        execution_data: The cached data from execution

    Returns:
        List of widget suggestions
    """
    suggestions: list[WidgetSuggestion] = []

    # Get current widget configurations
    current_facet_types = _get_current_facet_types(summary)
    _get_current_entity_types(summary)
    current_widget_types = _get_current_widget_types(summary)

    # Analyze data for new facet types
    new_facets = await _find_new_facet_types(
        session, execution_data, current_facet_types, summary
    )

    for facet_info in new_facets:
        suggestion = _create_facet_widget_suggestion(facet_info)
        if suggestion:
            suggestions.append(suggestion)

    # Check for visualization type opportunities
    viz_suggestions = _suggest_visualization_improvements(
        execution_data, current_widget_types, summary
    )
    suggestions.extend(viz_suggestions)

    # Sort by confidence
    suggestions.sort(key=lambda s: s.confidence, reverse=True)

    logger.info(
        "auto_expand_analysis_complete",
        summary_id=str(summary.id),
        suggestions_count=len(suggestions),
    )

    return suggestions


def _get_current_facet_types(summary: CustomSummary) -> set[str]:
    """Get all facet types currently used in widgets."""
    facet_types: set[str] = set()

    for widget in summary.widgets:
        config = widget.query_config or {}
        facet_list = config.get("facet_types", [])
        facet_types.update(facet_list)

    # Also check interpreted_config
    interpreted = summary.interpreted_config or {}
    facet_types.update(interpreted.get("facet_types", []))

    return facet_types


def _get_current_entity_types(summary: CustomSummary) -> set[str]:
    """Get all entity types currently used in widgets."""
    entity_types: set[str] = set()

    for widget in summary.widgets:
        config = widget.query_config or {}
        if config.get("entity_type"):
            entity_types.add(config["entity_type"])

    # Also check interpreted_config
    interpreted = summary.interpreted_config or {}
    if interpreted.get("primary_entity_type"):
        entity_types.add(interpreted["primary_entity_type"])

    return entity_types


def _get_current_widget_types(summary: CustomSummary) -> set[str]:
    """Get all widget types currently used."""
    return {w.widget_type.value for w in summary.widgets}


async def _find_new_facet_types(
    session: AsyncSession,
    execution_data: dict[str, Any],
    current_facets: set[str],
    summary: CustomSummary,
) -> list[dict[str, Any]]:
    """Find facet types in data that aren't in current widgets."""
    new_facets: list[dict[str, Any]] = []
    seen_facets: set[str] = set()

    # Iterate through widget data
    for _widget_key, widget_data in execution_data.items():
        if not isinstance(widget_data, dict):
            continue

        data_list = widget_data.get("data", [])
        for item in data_list:
            facets = item.get("facets", {})
            for facet_slug, facet_value in facets.items():
                if facet_slug in current_facets or facet_slug in seen_facets:
                    continue

                seen_facets.add(facet_slug)

                # Get facet type info from database
                result = await session.execute(
                    select(FacetType).where(FacetType.slug == facet_slug)
                )
                facet_type = result.scalar_one_or_none()

                if facet_type:
                    new_facets.append({
                        "slug": facet_slug,
                        "name": facet_type.name,
                        "data_type": facet_type.data_type,
                        "sample_value": facet_value.get("value") if isinstance(facet_value, dict) else facet_value,
                    })

    return new_facets


def _create_facet_widget_suggestion(facet_info: dict[str, Any]) -> WidgetSuggestion | None:
    """Create a widget suggestion for a new facet type."""
    slug = facet_info["slug"]
    name = facet_info["name"]
    data_type = facet_info.get("data_type", "text")

    # Determine best widget type based on data type
    if data_type in ("number", "integer", "float"):
        return WidgetSuggestion(
            widget_type=SummaryWidgetType.STAT_CARD,
            title=f"{name} (Durchschnitt)",
            subtitle="Automatisch entdecktes Merkmal",
            query_config={
                "facet_types": [slug],
                "aggregate": "avg",
            },
            reason=f"Neues numerisches Merkmal '{name}' entdeckt",
            confidence=0.7,
        )
    elif data_type == "date":
        return WidgetSuggestion(
            widget_type=SummaryWidgetType.TIMELINE,
            title=f"Zeitverlauf: {name}",
            subtitle="Automatisch entdecktes Datum",
            query_config={
                "facet_types": [slug],
            },
            reason=f"Neues Datums-Merkmal '{name}' entdeckt",
            confidence=0.6,
        )
    elif data_type == "geo":
        return WidgetSuggestion(
            widget_type=SummaryWidgetType.MAP,
            title=f"Kartenansicht: {name}",
            subtitle="Geografische Daten",
            query_config={
                "facet_types": [slug],
            },
            reason=f"Neues Geo-Merkmal '{name}' entdeckt",
            confidence=0.8,
        )
    else:
        # Default: Add to table or create bar chart for categorization
        return WidgetSuggestion(
            widget_type=SummaryWidgetType.BAR_CHART,
            title=f"Verteilung: {name}",
            subtitle="Automatisch entdecktes Merkmal",
            query_config={
                "facet_types": [slug],
                "group_by": slug,
                "aggregate": "count",
            },
            reason=f"Neues Text-Merkmal '{name}' entdeckt",
            confidence=0.5,
        )


def _suggest_visualization_improvements(
    execution_data: dict[str, Any],
    current_widget_types: set[str],
    summary: CustomSummary,
) -> list[WidgetSuggestion]:
    """Suggest improved visualization types based on data characteristics."""
    suggestions: list[WidgetSuggestion] = []

    # Analyze data characteristics
    total_records = 0
    has_numeric_data = False
    has_date_data = False
    has_geo_data = False

    for widget_data in execution_data.values():
        if not isinstance(widget_data, dict):
            continue

        data_list = widget_data.get("data", [])
        total_records += len(data_list)

        for item in data_list:
            facets = item.get("facets", {})
            for facet_value in facets.values():
                if isinstance(facet_value, dict):
                    value = facet_value.get("value")
                    if isinstance(value, (int, float)):
                        has_numeric_data = True
                    elif isinstance(value, str) and _looks_like_date(value):
                        has_date_data = True
                    # Check for geo coordinates
                    if item.get("latitude") or item.get("longitude"):
                        has_geo_data = True

    # Suggest stat card if not present and we have numeric data
    if "stat_card" not in current_widget_types and has_numeric_data:
        suggestions.append(WidgetSuggestion(
            widget_type=SummaryWidgetType.STAT_CARD,
            title="Gesamtanzahl",
            subtitle=f"{total_records} Einträge",
            query_config={"aggregate": "count"},
            reason="Statistik-Karte für Übersicht hinzufügen",
            confidence=0.75,
        ))

    # Suggest map if geo data present
    if "map" not in current_widget_types and has_geo_data:
        suggestions.append(WidgetSuggestion(
            widget_type=SummaryWidgetType.MAP,
            title="Kartenübersicht",
            subtitle="Geografische Verteilung",
            query_config={},
            reason="Geografische Daten gefunden",
            confidence=0.85,
        ))

    # Suggest timeline if date data present
    if "timeline" not in current_widget_types and "calendar" not in current_widget_types and has_date_data:
        suggestions.append(WidgetSuggestion(
            widget_type=SummaryWidgetType.CALENDAR,
            title="Kalenderansicht",
            subtitle="Zeitliche Verteilung",
            query_config={},
            reason="Datums-Daten gefunden",
            confidence=0.7,
        ))

    return suggestions


def _looks_like_date(value: str) -> bool:
    """Check if a string looks like a date."""
    import re

    # Common date patterns
    patterns = [
        r"\d{4}-\d{2}-\d{2}",  # ISO format
        r"\d{1,2}\.\d{1,2}\.\d{4}",  # German format
        r"\d{1,2}/\d{1,2}/\d{4}",  # US format
    ]

    return any(re.match(pattern, str(value)) for pattern in patterns)


async def apply_expansion(
    session: AsyncSession,
    summary_id: UUID,
    suggestions: list[WidgetSuggestion],
    max_widgets: int = 3,
) -> list[SummaryWidget]:
    """
    Apply expansion suggestions by creating new widgets.

    Only creates widgets above a confidence threshold and respects
    the maximum widget limit.

    Args:
        session: Database session
        summary_id: Summary to expand
        suggestions: List of widget suggestions
        max_widgets: Maximum widgets to add at once

    Returns:
        List of created widgets
    """
    created_widgets: list[SummaryWidget] = []

    # Get summary
    result = await session.execute(
        select(CustomSummary).where(CustomSummary.id == summary_id)
    )
    summary = result.scalar_one_or_none()

    if not summary:
        return []

    # Get current widget count for positioning
    current_count = len(summary.widgets)

    # Filter by confidence threshold
    MIN_CONFIDENCE = 0.6
    valid_suggestions = [s for s in suggestions if s.confidence >= MIN_CONFIDENCE]

    # Apply limit
    to_apply = valid_suggestions[:max_widgets]

    for idx, suggestion in enumerate(to_apply):
        # Calculate position (simple grid layout)
        position_x = ((current_count + idx) % 4) * 1
        position_y = ((current_count + idx) // 4) * 2

        widget = SummaryWidget(
            summary_id=summary_id,
            widget_type=suggestion.widget_type,
            title=suggestion.title,
            subtitle=suggestion.subtitle,
            position_x=position_x,
            position_y=position_y,
            width=2,
            height=2,
            query_config=suggestion.query_config,
            visualization_config={},
            display_order=current_count + idx,
        )

        session.add(widget)
        created_widgets.append(widget)

        logger.info(
            "auto_expand_widget_created",
            summary_id=str(summary_id),
            widget_type=suggestion.widget_type.value,
            title=suggestion.title,
            reason=suggestion.reason,
        )

    if created_widgets:
        await session.commit()
        for widget in created_widgets:
            await session.refresh(widget)

    return created_widgets
