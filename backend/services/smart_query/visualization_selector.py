"""AI-powered visualization selection for Smart Query.

This module uses AI to automatically select the best visualization
format based on data characteristics and user intent.

Best Practices Applied:
- Single Responsibility: Each method handles one concern
- Dependency Injection: LLM client is obtained via LLMClientService
- Fail-Safe Defaults: Falls back to table visualization on errors
- Comprehensive Logging: All decisions are logged for debugging
- Caching: LRU cache for AI responses to reduce API calls
"""

import hashlib
import json
import time
from typing import TYPE_CHECKING, Any

import structlog

from app.core.cache import TTLCache
from app.models.llm_usage import LLMTaskType
from app.models.user_api_credentials import LLMPurpose
from app.schemas.visualization import (
    ChartAxis,
    ChartSeries,
    ColumnType,
    StatCard,
    VisualizationColumn,
    VisualizationConfig,
    VisualizationType,
)
from services.llm_client_service import LLMClientService
from services.llm_usage_tracker import record_llm_usage

from .utils import clean_json_response

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


# =============================================================================
# Constants
# =============================================================================

# Default chart colors (Caeli brand colors)
CHART_COLORS = {
    "primary": "#1976D2",
    "secondary": "#424242",
    "success": "#2E7D32",
    "warning": "#F57C00",
    "error": "#D32F2F",
    "info": "#0288D1",
    "caeli_primary": "#113634",
    "caeli_secondary": "#deeec6",
}

# Thresholds for automatic decisions
LARGE_DATASET_THRESHOLD = 100  # Above this, default to table
MAX_PIE_CHART_CATEGORIES = 8
MAX_BAR_CHART_CATEGORIES = 15
MIN_CLUSTERING_DATA_POINTS = 20

# Geo field detection patterns
GEO_FIELD_NAMES = frozenset(["latitude", "longitude", "lat", "lon", "lng", "geo", "coords", "coordinates"])

# Cache settings
AI_CACHE_SIZE = 128  # Max number of cached AI responses
AI_CACHE_ENABLED = True  # Can be disabled for testing


def _generate_cache_key(
    query: str,
    data_count: int,
    fields: tuple[str, ...],
    has_time: bool,
    has_geo: bool,
) -> str:
    """Generate a stable cache key from query characteristics.

    Args:
        query: Normalized user query
        data_count: Number of data items (bucketed)
        fields: Tuple of field names
        has_time: Whether data has time dimension
        has_geo: Whether data has geo information

    Returns:
        SHA256 hash as cache key
    """
    # Bucket data_count to improve cache hits (1, 2-5, 6-20, 21-100, 100+)
    if data_count <= 1:
        count_bucket = "single"
    elif data_count <= 5:
        count_bucket = "few"
    elif data_count <= 20:
        count_bucket = "medium"
    elif data_count <= 100:
        count_bucket = "large"
    else:
        count_bucket = "xlarge"

    # Normalize query: lowercase, strip, remove extra spaces
    normalized_query = " ".join(query.lower().split())

    # Create key components
    key_parts = [
        normalized_query,
        count_bucket,
        ",".join(sorted(fields[:10])),  # Limit to first 10 fields
        str(has_time),
        str(has_geo),
    ]

    key_string = "|".join(key_parts)
    return hashlib.sha256(key_string.encode()).hexdigest()[:32]


# In-memory cache for AI responses with TTL and max size
# TTL: 30 min, max 128 entries (visualization choices are context-dependent)
_ai_response_cache: TTLCache[dict[str, Any]] = TTLCache(default_ttl=1800, max_size=AI_CACHE_SIZE)


def invalidate_visualization_cache() -> None:
    """Invalidate visualization selection cache."""
    _ai_response_cache.clear()
    logger.info("Visualization cache invalidated")


# =============================================================================
# AI Prompt for Visualization Selection
# =============================================================================

VISUALIZATION_SELECTOR_PROMPT = """Analysiere die folgenden Daten und wähle das beste Visualisierungsformat.

## Datenübersicht
- Anzahl Datenpunkte: {count}
- Datenfelder: {fields}
- Hat Zeitdimension: {has_time}
- Hat Geo-Daten: {has_geo}
- Geo-Datenpunkte: {geo_count}
- Anzahl Kategorien/Entities: {category_count}
- Numerische Felder: {numeric_fields}
- User-Query: "{user_query}"

## Datensample (erste 3 Einträge):
```json
{data_sample}
```

## Verfügbare Visualisierungstypen:
- "table": Für Ranglisten, Vergleichstabellen, Listen mit mehreren Spalten
- "bar_chart": Für Kategorievergleiche (2-15 Kategorien, ein numerischer Wert pro Kategorie)
- "line_chart": Für Zeitverläufe und Trends (benötigt Zeitdimension)
- "pie_chart": Für Anteile und Prozentuale Verteilung (2-8 Kategorien)
- "stat_card": Für Einzelwerte, KPIs, Zählungen (1-4 Werte)
- "text": Für Zusammenfassungen oder wenn keine andere Visualisierung passt
- "comparison": Für direkten Vergleich von 2-3 Entities nebeneinander
- "map": Für geografische Daten auf einer interaktiven Karte

## Entscheidungslogik (Priorität beachten):
1. **map**: Wenn Geo-Daten vorhanden UND der User räumliche/geografische Informationen sehen möchte
   - Signale: Orte anzeigen, Standorte, wo liegt, auf der Karte, geografische Verteilung
   - Wichtig: Nur wenn has_geo=True und geo_count > 0
2. **line_chart**: Wenn Zeitdimension vorhanden UND Entwicklung/Verlauf gefragt
3. **comparison**: Bei explizitem Vergleich von 2-3 Entities
4. **stat_card**: Bei Einzelwert-Fragen oder wenn nur 1-3 KPIs relevant sind
5. **bar_chart**: Für Kategorienvergleich mit numerischen Werten
6. **pie_chart**: Für Anteile/Verteilung einer Gesamtmenge
7. **table**: Für strukturierte Daten, Ranglisten, oder wenn andere nicht passen

## Antwortformat (JSON):
{{
  "visualization_type": "table|bar_chart|line_chart|pie_chart|stat_card|text|comparison|map",
  "reasoning": "Kurze Begründung",
  "title": "Vorgeschlagener Titel",
  "subtitle": "Optional: Untertitel",
  "columns": [  // NUR für table
    {{"key": "feldname", "label": "Anzeigename", "type": "text|number|date"}}
  ],
  "sort_column": "feldname",  // NUR für table
  "sort_order": "asc|desc",   // NUR für table
  "x_axis": {{"key": "...", "label": "...", "type": "category|number|time"}},  // NUR für Charts
  "y_axis": {{"key": "...", "label": "...", "type": "number"}},  // NUR für Charts
  "series": [{{"key": "...", "label": "...", "color": "#..."}}],  // NUR für Charts
  "cards": [{{"label": "...", "value_key": "...", "unit": "..."}}]  // NUR für stat_card
}}

Antworte NUR mit validem JSON."""


class VisualizationSelector:
    """AI-powered visualization selector for Smart Query results."""

    def __init__(self, session: "AsyncSession | None" = None):
        self.session = session

    async def select_visualization(
        self,
        data: list[dict[str, Any]],
        user_query: str,
        facet_types: list[str] | None = None,
        user_hint: str | None = None,
    ) -> VisualizationConfig:
        """
        Select the best visualization format for the given data.

        Args:
            data: Query result data
            user_query: Original user query for context
            facet_types: List of facet types in the data
            user_hint: Optional user override for visualization type

        Returns:
            VisualizationConfig with type and formatting details
        """
        # If user explicitly specifies a format, use that
        if user_hint:
            viz_type = self._parse_visualization_hint(user_hint)
            return self._build_config_for_type(viz_type, data, user_query)

        # Analyze data structure
        analysis = self._analyze_data(data, facet_types)

        # Quick decisions based on data characteristics (no AI needed)
        quick_decision = self._quick_select(analysis, user_query)
        if quick_decision:
            return self._build_config_for_type(quick_decision, data, user_query, analysis)

        # Use AI for more complex decisions
        try:
            ai_result = await self._ai_select(data, user_query, analysis)
            return self._build_config_from_ai(ai_result, data)
        except Exception as e:
            logger.warning("AI visualization selection failed, using fallback", error=str(e))
            # Fallback to table
            return self._build_config_for_type(VisualizationType.TABLE, data, user_query, analysis)

    def _analyze_data(
        self,
        data: list[dict[str, Any]],
        facet_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Analyze data structure for visualization selection."""
        if not data:
            return {
                "count": 0,
                "fields": [],
                "numeric_fields": [],
                "has_time": False,
                "has_geo": False,
                "category_count": 0,
            }

        # Get all fields from first item
        sample = data[0]
        fields = []
        numeric_fields = []
        time_fields = []
        has_geo = False

        def analyze_object(obj: dict, prefix: str = ""):
            nonlocal has_geo
            for key, value in obj.items():
                full_key = f"{prefix}{key}" if prefix else key

                # Check for geo data
                if key.lower() in ["latitude", "longitude", "lat", "lon", "lng"]:
                    if value is not None:
                        has_geo = True
                elif key.lower() == "geometry" and isinstance(value, dict):
                    if "type" in value and "coordinates" in value:
                        has_geo = True
                elif key.lower() == "coordinates" and isinstance(value, dict):  # noqa: SIM102
                    if "lat" in value or "lon" in value:
                        has_geo = True

                if isinstance(value, dict):
                    # Check if it's a facet with value/recorded_at
                    if "value" in value:
                        fields.append(full_key)
                        if isinstance(value.get("value"), (int, float)):
                            numeric_fields.append(full_key)
                        if "recorded_at" in value:
                            time_fields.append(full_key)
                    else:
                        analyze_object(value, f"{full_key}.")
                elif isinstance(value, (int, float)) and not isinstance(value, bool):
                    fields.append(full_key)
                    numeric_fields.append(full_key)
                elif isinstance(value, str):
                    fields.append(full_key)
                    # Check if it looks like a date/time
                    if any(x in key.lower() for x in ["date", "time", "recorded_at", "created", "updated"]):
                        time_fields.append(full_key)
                elif isinstance(value, list):
                    fields.append(full_key)

        analyze_object(sample)

        # Count items with geo data
        geo_count = 0
        for item in data:
            if self._has_geo_data(item):
                geo_count += 1

        return {
            "count": len(data),
            "fields": fields,
            "numeric_fields": numeric_fields,
            "time_fields": time_fields,
            "has_time": len(time_fields) > 0,
            "has_geo": has_geo,
            "geo_count": geo_count,
            "category_count": len(data),
            "facet_types": facet_types or [],
        }

    def _has_geo_data(self, item: dict[str, Any]) -> bool:
        """Check if an item has geographic data."""
        # Direct coordinates
        if item.get("latitude") is not None and item.get("longitude") is not None:
            return True
        if item.get("lat") is not None and item.get("lon") is not None:
            return True

        # Geometry object
        geometry = item.get("geometry")
        if isinstance(geometry, dict) and "type" in geometry and "coordinates" in geometry:
            return True

        # Nested coordinates
        coords = item.get("coordinates")
        return bool(isinstance(coords, dict) and ("lat" in coords or "lon" in coords))

    def _quick_select(
        self,
        analysis: dict[str, Any],
        user_query: str,
    ) -> VisualizationType | None:
        """
        Quick selection for trivial cases only.

        This method handles clear-cut cases where AI is unnecessary:
        - Empty datasets → TEXT (informational message)
        - Single result → STAT_CARD (KPI display)
        - Very large datasets → TABLE (performance)

        All complex decisions are delegated to AI for better context understanding
        and multilingual support. This ensures the AI can interpret user intent
        regardless of language (German, English, etc.).

        Args:
            analysis: Data analysis results from _analyze_data()
            user_query: Original user query (unused here but passed for consistency)

        Returns:
            VisualizationType if a quick decision can be made, None otherwise
        """
        count = analysis.get("count", 0)

        # Trivial case: empty result → show informational text
        if count == 0:
            return VisualizationType.TEXT

        # Trivial case: single result is always best as stat card
        if count == 1:
            return VisualizationType.STAT_CARD

        # Very large datasets default to table for performance
        # AI selection would be too slow and tables handle large data well
        if count > LARGE_DATASET_THRESHOLD:
            logger.debug(
                "Quick select: large dataset, defaulting to table",
                count=count,
                threshold=LARGE_DATASET_THRESHOLD,
            )
            return VisualizationType.TABLE

        # Everything else: let AI decide based on query context, data structure,
        # and visualization suitability (multilingual, context-aware)
        return None

    async def _ai_select(
        self,
        data: list[dict[str, Any]],
        user_query: str,
        analysis: dict[str, Any],
    ) -> dict[str, Any]:
        """Use AI to select visualization for complex cases.

        Includes caching to reduce API calls for similar queries.
        """
        # Generate cache key
        cache_key = None
        if AI_CACHE_ENABLED:
            cache_key = _generate_cache_key(
                query=user_query,
                data_count=analysis.get("count", 0),
                fields=tuple(analysis.get("fields", [])),
                has_time=analysis.get("has_time", False),
                has_geo=analysis.get("has_geo", False),
            )

            # Check cache
            cached = _ai_response_cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit for visualization selection", cache_key=cache_key[:8])
                return cached

        if not self.session:
            raise ValueError("Database session required for AI visualization selection")

        # Get LLM client
        llm_service = LLMClientService(self.session)
        client, config = await llm_service.get_system_client(LLMPurpose.DOCUMENT_ANALYSIS)
        if not client or not config:
            raise ValueError("No LLM credentials configured")

        model_name = llm_service.get_model_name(config)
        provider = llm_service.get_provider(config)

        # Build data sample
        sample_data = data[:3] if len(data) >= 3 else data
        data_sample = json.dumps(sample_data, indent=2, ensure_ascii=False, default=str)

        prompt = VISUALIZATION_SELECTOR_PROMPT.format(
            count=analysis.get("count", 0),
            fields=", ".join(analysis.get("fields", [])[:15]),
            has_time=analysis.get("has_time", False),
            has_geo=analysis.get("has_geo", False),
            geo_count=analysis.get("geo_count", 0),
            category_count=analysis.get("category_count", 0),
            numeric_fields=", ".join(analysis.get("numeric_fields", [])[:10]),
            user_query=user_query,
            data_sample=data_sample[:2000],  # Limit sample size
        )

        start_time = time.time()
        response = await client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1000,
        )

        if response.usage:
            await record_llm_usage(
                provider=provider,
                model=model_name,
                task_type=LLMTaskType.CHAT,
                task_name="_ai_select",
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                duration_ms=int((time.time() - start_time) * 1000),
                is_error=False,
            )

        content = response.choices[0].message.content.strip()
        content = clean_json_response(content)

        result = json.loads(content)

        logger.info(
            "AI selected visualization",
            type=result.get("visualization_type"),
            reasoning=result.get("reasoning"),
            cache_key=cache_key[:8] if cache_key else None,
        )

        # Store in cache (TTLCache handles size limit automatically)
        if AI_CACHE_ENABLED and cache_key:
            _ai_response_cache.set(cache_key, result)

        return result

    def _parse_visualization_hint(self, hint: str) -> VisualizationType:
        """Parse user hint to visualization type."""
        hint_lower = hint.lower()

        mapping = {
            "table": VisualizationType.TABLE,
            "tabelle": VisualizationType.TABLE,
            "bar": VisualizationType.BAR_CHART,
            "bar_chart": VisualizationType.BAR_CHART,
            "balken": VisualizationType.BAR_CHART,
            "line": VisualizationType.LINE_CHART,
            "line_chart": VisualizationType.LINE_CHART,
            "linie": VisualizationType.LINE_CHART,
            "pie": VisualizationType.PIE_CHART,
            "pie_chart": VisualizationType.PIE_CHART,
            "torte": VisualizationType.PIE_CHART,
            "stat": VisualizationType.STAT_CARD,
            "stat_card": VisualizationType.STAT_CARD,
            "kpi": VisualizationType.STAT_CARD,
            "text": VisualizationType.TEXT,
            "comparison": VisualizationType.COMPARISON,
            "vergleich": VisualizationType.COMPARISON,
            "map": VisualizationType.MAP,
            "karte": VisualizationType.MAP,
            "geo": VisualizationType.MAP,
        }

        for key, viz_type in mapping.items():
            if key in hint_lower:
                return viz_type

        return VisualizationType.TABLE  # Default

    def _build_config_for_type(
        self,
        viz_type: VisualizationType,
        data: list[dict[str, Any]],
        user_query: str,
        analysis: dict[str, Any] | None = None,
    ) -> VisualizationConfig:
        """Build visualization config for a specific type."""
        if analysis is None:
            analysis = self._analyze_data(data)

        title = self._generate_title(user_query, viz_type, len(data))

        if viz_type == VisualizationType.TABLE:
            return self._build_table_config(data, title, analysis)
        elif viz_type == VisualizationType.BAR_CHART:
            return self._build_bar_chart_config(data, title, analysis)
        elif viz_type == VisualizationType.LINE_CHART:
            return self._build_line_chart_config(data, title, analysis)
        elif viz_type == VisualizationType.PIE_CHART:
            return self._build_pie_chart_config(data, title, analysis)
        elif viz_type == VisualizationType.STAT_CARD:
            return self._build_stat_card_config(data, title, analysis)
        elif viz_type == VisualizationType.COMPARISON:
            return self._build_comparison_config(data, title, analysis)
        elif viz_type == VisualizationType.MAP:
            return self._build_map_config(data, title, analysis)
        else:
            return self._build_text_config(data, title, user_query)

    def _build_table_config(
        self,
        data: list[dict[str, Any]],
        title: str,
        analysis: dict[str, Any],
    ) -> VisualizationConfig:
        """Build table visualization config."""
        columns = []

        # Always include entity_name first if present
        if data and "entity_name" in data[0]:
            columns.append(
                VisualizationColumn(
                    key="entity_name",
                    label="Name",
                    type=ColumnType.TEXT,
                )
            )

        # Add numeric facet columns
        if data and "facets" in data[0]:
            facets = data[0].get("facets", {})
            for facet_key, facet_value in facets.items():
                if isinstance(facet_value, dict) and "value" in facet_value:
                    value = facet_value["value"]
                    col_type = ColumnType.NUMBER if isinstance(value, (int, float)) else ColumnType.TEXT
                    columns.append(
                        VisualizationColumn(
                            key=f"facets.{facet_key}.value",
                            label=facet_key.replace("-", " ").replace("_", " ").title(),
                            type=col_type,
                        )
                    )

        # Determine sort column
        sort_column = None
        numeric_fields = analysis.get("numeric_fields", [])
        if numeric_fields:
            for field in numeric_fields:
                if "position" in field.lower() or "platz" in field.lower():
                    sort_column = field
                    break
            if not sort_column:
                sort_column = numeric_fields[0]

        return VisualizationConfig(
            type=VisualizationType.TABLE,
            title=title,
            columns=columns if columns else None,
            sort_column=sort_column,
            sort_order="asc" if sort_column and "position" in sort_column.lower() else "desc",
        )

    def _build_bar_chart_config(
        self,
        data: list[dict[str, Any]],
        title: str,
        analysis: dict[str, Any],
    ) -> VisualizationConfig:
        """Build bar chart visualization config."""
        # Use entity_name as category (x-axis)
        x_axis = ChartAxis(
            key="entity_name",
            label="",
            type="category",
        )

        # Find first numeric field for y-axis
        y_key = "value"
        y_label = "Wert"

        if data and "facets" in data[0]:
            facets = data[0].get("facets", {})
            for facet_key, facet_value in facets.items():
                if isinstance(facet_value, dict) and isinstance(facet_value.get("value"), (int, float)):
                    y_key = f"facets.{facet_key}.value"
                    y_label = facet_key.replace("-", " ").replace("_", " ").title()
                    break

        y_axis = ChartAxis(
            key=y_key,
            label=y_label,
            type="number",
        )

        series = [
            ChartSeries(
                key=y_key,
                label=y_label,
                color=CHART_COLORS["primary"],
                type="bar",
            )
        ]

        return VisualizationConfig(
            type=VisualizationType.BAR_CHART,
            title=title,
            x_axis=x_axis,
            y_axis=y_axis,
            series=series,
        )

    def _build_line_chart_config(
        self,
        data: list[dict[str, Any]],
        title: str,
        analysis: dict[str, Any],
    ) -> VisualizationConfig:
        """Build line chart visualization config."""
        time_fields = analysis.get("time_fields", [])
        x_key = time_fields[0] if time_fields else "recorded_at"

        x_axis = ChartAxis(
            key=x_key,
            label="Zeit",
            type="time",
        )

        # Find numeric field for y-axis
        numeric_fields = analysis.get("numeric_fields", [])
        y_key = numeric_fields[0] if numeric_fields else "value"
        y_label = y_key.split(".")[-1].replace("-", " ").replace("_", " ").title()

        y_axis = ChartAxis(
            key=y_key,
            label=y_label,
            type="number",
        )

        series = [
            ChartSeries(
                key=y_key,
                label=y_label,
                color=CHART_COLORS["primary"],
                type="line",
            )
        ]

        return VisualizationConfig(
            type=VisualizationType.LINE_CHART,
            title=title,
            x_axis=x_axis,
            y_axis=y_axis,
            series=series,
        )

    def _build_pie_chart_config(
        self,
        data: list[dict[str, Any]],
        title: str,
        analysis: dict[str, Any],
    ) -> VisualizationConfig:
        """Build pie chart visualization config."""
        # Use entity_name as category
        x_axis = ChartAxis(
            key="entity_name",
            label="Kategorie",
            type="category",
        )

        # Find numeric field for values
        numeric_fields = analysis.get("numeric_fields", [])
        y_key = numeric_fields[0] if numeric_fields else "value"

        y_axis = ChartAxis(
            key=y_key,
            label="Wert",
            type="number",
        )

        return VisualizationConfig(
            type=VisualizationType.PIE_CHART,
            title=title,
            x_axis=x_axis,
            y_axis=y_axis,
        )

    def _build_stat_card_config(
        self,
        data: list[dict[str, Any]],
        title: str,
        analysis: dict[str, Any],
    ) -> VisualizationConfig:
        """Build stat card visualization config."""
        cards = []

        for item in data[:4]:  # Max 4 cards
            label = item.get("entity_name", "Wert")

            # Find first numeric value
            value = None
            unit = None

            if "facets" in item:
                for _facet_key, facet_value in item.get("facets", {}).items():
                    if isinstance(facet_value, dict) and "value" in facet_value:
                        value = facet_value["value"]
                        break

            if value is None and "core_attributes" in item:
                for _attr_key, attr_value in item.get("core_attributes", {}).items():
                    if isinstance(attr_value, (int, float)):
                        value = attr_value
                        break

            if value is not None:
                cards.append(
                    StatCard(
                        label=label,
                        value=value,
                        unit=unit,
                    )
                )

        return VisualizationConfig(
            type=VisualizationType.STAT_CARD,
            title=title,
            cards=cards if cards else None,
        )

    def _build_comparison_config(
        self,
        data: list[dict[str, Any]],
        title: str,
        analysis: dict[str, Any],
    ) -> VisualizationConfig:
        """Build comparison visualization config."""
        # Get list of facets to compare
        comparison_facets = []
        if data and "facets" in data[0]:
            comparison_facets = list(data[0].get("facets", {}).keys())

        return VisualizationConfig(
            type=VisualizationType.COMPARISON,
            title=title,
            comparison_facets=comparison_facets if comparison_facets else None,
        )

    def _build_map_config(
        self,
        data: list[dict[str, Any]],
        title: str,
        analysis: dict[str, Any],
    ) -> VisualizationConfig:
        """Build map visualization config."""
        geo_count = analysis.get("geo_count", 0)
        subtitle = f"{geo_count} Standorte" if geo_count > 0 else None

        return VisualizationConfig(
            type=VisualizationType.MAP,
            title=title,
            subtitle=subtitle,
        )

    def _build_text_config(
        self,
        data: list[dict[str, Any]],
        title: str,
        user_query: str,
    ) -> VisualizationConfig:
        """Build text visualization config."""
        if not data:
            text_content = "Keine Daten gefunden."
        elif len(data) == 1:
            item = data[0]
            name = item.get("entity_name", "Unbekannt")
            facets = item.get("facets", {})

            lines = [f"**{name}**"]
            for facet_key, facet_value in facets.items():
                if isinstance(facet_value, dict):
                    value = facet_value.get("value")
                    label = facet_key.replace("-", " ").replace("_", " ").title()
                    lines.append(f"- {label}: {value}")

            text_content = "\n".join(lines)
        else:
            text_content = f"{len(data)} Ergebnisse gefunden."

        return VisualizationConfig(
            type=VisualizationType.TEXT,
            title=title,
            text_content=text_content,
        )

    def _build_config_from_ai(
        self,
        ai_result: dict[str, Any],
        data: list[dict[str, Any]],
    ) -> VisualizationConfig:
        """Build visualization config from AI response."""
        viz_type_str = ai_result.get("visualization_type", "table")

        # Parse visualization type
        type_mapping = {
            "table": VisualizationType.TABLE,
            "bar_chart": VisualizationType.BAR_CHART,
            "line_chart": VisualizationType.LINE_CHART,
            "pie_chart": VisualizationType.PIE_CHART,
            "stat_card": VisualizationType.STAT_CARD,
            "text": VisualizationType.TEXT,
            "comparison": VisualizationType.COMPARISON,
            "map": VisualizationType.MAP,
        }
        viz_type = type_mapping.get(viz_type_str, VisualizationType.TABLE)

        # Build columns if provided
        columns = None
        if "columns" in ai_result and ai_result["columns"]:
            columns = []
            for col in ai_result["columns"]:
                col_type = ColumnType.TEXT
                if col.get("type") == "number":
                    col_type = ColumnType.NUMBER
                elif col.get("type") == "date":
                    col_type = ColumnType.DATE

                columns.append(
                    VisualizationColumn(
                        key=col.get("key", ""),
                        label=col.get("label", col.get("key", "")),
                        type=col_type,
                    )
                )

        # Build axes if provided
        x_axis = None
        y_axis = None
        if "x_axis" in ai_result and ai_result["x_axis"]:
            x = ai_result["x_axis"]
            x_axis = ChartAxis(
                key=x.get("key", ""),
                label=x.get("label", ""),
                type=x.get("type", "category"),
            )
        if "y_axis" in ai_result and ai_result["y_axis"]:
            y = ai_result["y_axis"]
            y_axis = ChartAxis(
                key=y.get("key", ""),
                label=y.get("label", ""),
                type=y.get("type", "number"),
            )

        # Build series if provided
        series = None
        if "series" in ai_result and ai_result["series"]:
            series = []
            for s in ai_result["series"]:
                series.append(
                    ChartSeries(
                        key=s.get("key", ""),
                        label=s.get("label", ""),
                        color=s.get("color", CHART_COLORS["primary"]),
                        type=s.get("type", "line"),
                    )
                )

        # Build stat cards if provided
        cards = None
        if "cards" in ai_result and ai_result["cards"]:
            cards = []
            for c in ai_result["cards"]:
                # Get value from data
                value = c.get("value")
                if value is None and data and c.get("value_key"):
                    value_key = c["value_key"]
                    for item in data:
                        if value_key in item:
                            value = item[value_key]
                            break
                        if "facets" in item and value_key in item["facets"]:
                            facet = item["facets"][value_key]
                            if isinstance(facet, dict):
                                value = facet.get("value")
                            break

                cards.append(
                    StatCard(
                        label=c.get("label", ""),
                        value=value,
                        unit=c.get("unit"),
                    )
                )

        return VisualizationConfig(
            type=viz_type,
            title=ai_result.get("title", "Ergebnis"),
            subtitle=ai_result.get("subtitle"),
            columns=columns,
            sort_column=ai_result.get("sort_column"),
            sort_order=ai_result.get("sort_order"),
            x_axis=x_axis,
            y_axis=y_axis,
            series=series,
            cards=cards,
        )

    def _generate_title(
        self,
        user_query: str,
        viz_type: VisualizationType,
        count: int,
    ) -> str:
        """Generate a title based on query and visualization type."""
        # Simple title extraction from query
        query_lower = user_query.lower()

        # Remove common question words
        for word in ["zeige", "show", "liste", "welche", "was", "wie", "mir", "die", "den", "das", "alle"]:
            query_lower = query_lower.replace(word, "")

        query_lower = query_lower.strip()

        if not query_lower:
            return f"Ergebnis ({count} Einträge)"

        # Capitalize first letter
        title = query_lower[0].upper() + query_lower[1:]

        # Limit length
        if len(title) > 50:
            title = title[:47] + "..."

        return title
