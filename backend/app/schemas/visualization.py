"""Schemas for Smart Query visualization responses.

This module defines the data structures for dynamic visualization
of query results. The KI selects the appropriate visualization type
based on data characteristics and user intent.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# =============================================================================
# Constants
# =============================================================================

VALID_SORT_ORDERS = ("asc", "desc")
VALID_AXIS_TYPES = ("category", "number", "time")
VALID_SERIES_TYPES = ("line", "bar", "area")
VALID_ALIGNMENTS = ("left", "center", "right")
VALID_TRENDS = ("up", "down", "stable")
VALID_SOURCE_TYPES = ("facet_history", "live_api", "internal")


class VisualizationType(str, Enum):
    """Supported visualization types."""
    TABLE = "table"              # Tabelle mit sortierbaren Spalten
    BAR_CHART = "bar_chart"      # Horizontales oder vertikales Balkendiagramm
    LINE_CHART = "line_chart"    # Liniendiagramm für Zeitverläufe
    PIE_CHART = "pie_chart"      # Kreisdiagramm für Anteile
    STAT_CARD = "stat_card"      # KPI-Karten (1-4 Werte)
    TEXT = "text"                # Fließtext-Antwort
    COMPARISON = "comparison"    # Side-by-side Vergleich von 2-3 Entities
    MAP = "map"                  # Kartenansicht (falls Geo-Daten)
    HEATMAP = "heatmap"          # Matrix-Darstellung


class ColumnType(str, Enum):
    """Column data types for tables."""
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    DATETIME = "datetime"
    CURRENCY = "currency"
    PERCENT = "percent"
    BOOLEAN = "boolean"
    LINK = "link"


class VisualizationColumn(BaseModel):
    """Column configuration for table visualization."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "key": "entity_name",
                "label": "Name",
                "type": "text",
                "sortable": True,
                "align": "left",
            }
        }
    )

    key: str = Field(..., description="Feld-Name im Datensatz", min_length=1)
    label: str = Field(..., description="Anzeigetext", min_length=1)
    type: ColumnType = Field(default=ColumnType.TEXT, description="Datentyp")
    format: str | None = Field(None, description="Format-String (z.B. '0.0' für Zahlen)")
    sortable: bool = Field(default=True, description="Spalte sortierbar")
    width: str | None = Field(None, description="Spaltenbreite (z.B. '100px', '20%')")
    align: Literal["left", "center", "right"] | None = Field(
        None, description="Ausrichtung: left, center, right"
    )


class ChartAxis(BaseModel):
    """Axis configuration for charts."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "key": "date",
                "label": "Datum",
                "type": "time",
            }
        }
    )

    key: str = Field(..., description="Feld-Name für Achsenwerte", min_length=1)
    label: str = Field(..., description="Achsenbeschriftung", min_length=1)
    type: Literal["category", "number", "time"] = Field(
        default="category", description="Achsentyp: category, number, time"
    )
    min: float | None = Field(None, description="Minimum Wert")
    max: float | None = Field(None, description="Maximum Wert")
    format: str | None = Field(None, description="Format für Labels")

    @model_validator(mode="after")
    def validate_min_max(self) -> "ChartAxis":
        """Ensure min is less than max if both are provided."""
        if self.min is not None and self.max is not None and self.min >= self.max:
            raise ValueError("min must be less than max")
        return self


class ChartSeries(BaseModel):
    """Data series configuration for charts."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "key": "points",
                "label": "Punkte",
                "color": "#1976D2",
                "type": "line",
            }
        }
    )

    key: str = Field(..., description="Feld-Name für Werte", min_length=1)
    label: str = Field(..., description="Legende", min_length=1)
    color: str = Field(default="#1976D2", description="Farbe (Hex)")
    type: Literal["line", "bar", "area"] = Field(
        default="line", description="Serientyp: line, bar, area"
    )
    stack: str | None = Field(None, description="Stack-Gruppe für gestapelte Charts")

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        """Validate that color is a valid hex color."""
        if not v.startswith("#") or len(v) not in (4, 7):
            raise ValueError("Color must be a valid hex color (e.g., #FFF or #FFFFFF)")
        return v


class StatCard(BaseModel):
    """Single statistic card configuration."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "label": "Gesamtanzahl",
                "value": 42,
                "unit": "Entities",
                "trend": "up",
                "trend_value": "+5%",
                "icon": "mdi-chart-line",
            }
        }
    )

    label: str = Field(..., description="Beschriftung", min_length=1)
    value: Any = Field(..., description="Wert")
    unit: str | None = Field(None, description="Einheit")
    trend: Literal["up", "down", "stable"] | None = Field(
        None, description="Trend: up, down, stable"
    )
    trend_value: str | None = Field(None, description="Trend-Wert (z.B. '+5%')")
    icon: str | None = Field(None, description="Material Icon Name")
    color: str | None = Field(None, description="Farbe für den Wert")


class ComparisonEntity(BaseModel):
    """Entity data for comparison visualization."""
    entity_id: str
    entity_name: str
    facets: dict[str, Any] = Field(default_factory=dict)
    core_attributes: dict[str, Any] = Field(default_factory=dict)


class VisualizationConfig(BaseModel):
    """Complete visualization configuration."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "table",
                "title": "Bundesliga Tabelle",
                "subtitle": "Saison 2024/25",
                "columns": [
                    {"key": "position", "label": "Platz", "type": "number"},
                    {"key": "name", "label": "Verein", "type": "text"},
                ],
                "sort_column": "position",
                "sort_order": "asc",
            }
        }
    )

    type: VisualizationType = Field(..., description="Visualisierungstyp")
    title: str = Field(..., description="Titel", min_length=1)
    subtitle: str | None = Field(None, description="Untertitel")

    # Für Tabellen
    columns: list[VisualizationColumn] | None = Field(None, description="Spalten-Konfiguration")
    sort_column: str | None = Field(None, description="Standard-Sortier-Spalte")
    sort_order: Literal["asc", "desc"] | None = Field(None, description="Sortierung: asc, desc")

    # Für Charts
    x_axis: ChartAxis | None = Field(None, description="X-Achse")
    y_axis: ChartAxis | None = Field(None, description="Y-Achse")
    series: list[ChartSeries] | None = Field(None, description="Datenreihen")

    # Für Stat Cards
    cards: list[StatCard] | None = Field(None, description="KPI-Karten")

    # Für Text
    text_content: str | None = Field(None, description="Fließtext")

    # Für Comparison
    entities_to_compare: list[ComparisonEntity] | None = Field(None, description="Entities zum Vergleich")
    comparison_facets: list[str] | None = Field(None, description="Zu vergleichende Facets")

    @model_validator(mode="after")
    def validate_type_specific_fields(self) -> "VisualizationConfig":
        """Validate that required fields are present based on visualization type."""
        if self.type == VisualizationType.TABLE and not self.columns:
            # Allow empty columns - will use auto-detection in frontend
            pass
        elif self.type == VisualizationType.STAT_CARD and not self.cards:
            # Allow empty cards - will be built from data
            pass
        return self


class SourceInfo(BaseModel):
    """Information about data source."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "internal",
                "last_updated": "2024-12-23T10:00:00Z",
                "data_freshness": "2 hours ago",
            }
        }
    )

    type: Literal["facet_history", "live_api", "internal"] = Field(
        ..., description="Quellentyp: facet_history, live_api, internal"
    )
    last_updated: datetime | None = Field(None, description="Letzte Aktualisierung")
    data_freshness: str | None = Field(None, description="Datenalter (menschenlesbar)")
    api_name: str | None = Field(None, description="API-Name falls extern")
    api_url: str | None = Field(None, description="API-URL falls extern")
    template_id: str | None = Field(None, description="API-Template ID falls genutzt")


class SuggestedAction(BaseModel):
    """Suggested follow-up action."""
    label: str = Field(..., description="Button-Text")
    action: str = Field(..., description="Action-Identifier")
    icon: str | None = Field(None, description="Material Icon")
    params: dict[str, Any] = Field(default_factory=dict, description="Action-Parameter")
    description: str | None = Field(None, description="Tooltip/Beschreibung")


class DataPoint(BaseModel):
    """Single data point in query results."""
    entity_id: str
    entity_name: str
    entity_type: str | None = None
    core_attributes: dict[str, Any] = Field(default_factory=dict)
    facets: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class QueryDataResponse(BaseModel):
    """Complete response for query_data operation."""
    success: bool = Field(..., description="Operation erfolgreich")
    error: str | None = Field(None, description="Fehlermeldung")

    # Datenquelle
    data_source: str = Field(default="internal", description="Quellentyp: internal, external_api")
    entity_type: str | None = Field(None, description="Entity-Typ Slug")

    # Rohdaten
    data: list[dict[str, Any]] = Field(default_factory=list, description="Abfrageergebnisse")
    total_count: int = Field(default=0, description="Gesamtanzahl")
    returned_count: int = Field(default=0, description="Zurückgegebene Anzahl")

    # Visualisierung
    visualization: VisualizationConfig | None = Field(None, description="Visualisierungs-Config")

    # Kontext
    explanation: str | None = Field(None, description="Erklärung der Daten")
    source_info: SourceInfo | None = Field(None, description="Quelleninformation")
    suggested_actions: list[SuggestedAction] = Field(default_factory=list, description="Vorgeschlagene Aktionen")


class QueryExternalResponse(BaseModel):
    """Complete response for query_external operation."""
    success: bool = Field(..., description="Operation erfolgreich")
    error: str | None = Field(None, description="Fehlermeldung")

    # API-Info
    data_source: str = Field(default="external_api")
    api_name: str | None = Field(None, description="API-Name")
    api_url: str | None = Field(None, description="API-URL")

    # Rohdaten (original from API)
    raw_data: list[dict[str, Any]] = Field(default_factory=list, description="Original API-Daten")

    # Formatierte Daten
    data: list[dict[str, Any]] = Field(default_factory=list, description="Formatierte Daten")
    total_count: int = Field(default=0, description="Gesamtanzahl")

    # Visualisierung
    visualization: VisualizationConfig | None = Field(None, description="Visualisierungs-Config")

    # Kontext
    explanation: str | None = Field(None, description="Erklärung der Daten")
    source_info: SourceInfo | None = Field(None, description="Quelleninformation")
    suggested_actions: list[SuggestedAction] = Field(default_factory=list, description="Vorgeschlagene Aktionen")


# =============================================================================
# Compound Query (UND-Abfragen)
# =============================================================================


class VisualizationWithData(BaseModel):
    """A single visualization block with its data (for compound queries)."""
    id: str = Field(..., description="Unique ID für Frontend-Key")
    title: str = Field(..., description="Titel für diesen Visualisierungsblock")
    visualization: VisualizationConfig | None = Field(None, description="Visualisierungs-Config")
    data: list[dict[str, Any]] = Field(default_factory=list, description="Daten für diese Visualisierung")
    source_info: SourceInfo | None = Field(None, description="Quelleninformation")
    explanation: str | None = Field(None, description="Erklärung für diesen Teil")


class SubQueryConfig(BaseModel):
    """Configuration for a sub-query in compound queries."""
    description: str = Field(..., description="Beschreibung der Sub-Query")
    query_config: dict[str, Any] = Field(..., description="Query-Konfiguration")
    visualization_hint: str | None = Field(None, description="Hinweis für Visualisierungstyp")


class CompoundQueryResponse(BaseModel):
    """Response for compound queries with multiple visualizations."""
    success: bool = Field(..., description="Operation erfolgreich")
    error: str | None = Field(None, description="Fehlermeldung")
    is_compound: bool = Field(default=True, description="Marker für Compound Query")
    visualizations: list[VisualizationWithData] = Field(default_factory=list, description="Liste der Visualisierungen")
    explanation: str | None = Field(None, description="Gesamterklärung")
    suggested_actions: list[SuggestedAction] = Field(default_factory=list, description="Vorgeschlagene Aktionen")


# =============================================================================
# Helper classes for query configuration
# =============================================================================


class TimeRangeConfig(BaseModel):
    """Time range configuration for history queries."""
    from_date: str | None = Field(None, alias="from", description="Start-Datum (ISO)")
    to_date: str | None = Field(None, alias="to", description="End-Datum (ISO)")
    latest_only: bool = Field(default=False, description="Nur letzten Wert pro Entity")

    model_config = {"populate_by_name": True}


class QueryFilters(BaseModel):
    """Filters for query_data operation."""
    tags: list[str] = Field(default_factory=list, description="Tags (AND)")
    admin_level_1: str | None = Field(None, description="Bundesland/Region")
    country: str | None = Field(None, description="Land (ISO 2)")
    core_attributes: dict[str, Any] = Field(default_factory=dict, description="Filter auf core_attributes")
    entity_names: list[str] = Field(default_factory=list, description="Spezifische Entity-Namen")
    entity_ids: list[str] = Field(default_factory=list, description="Spezifische Entity-IDs")


class QueryDataConfig(BaseModel):
    """Configuration for query_data operation."""
    entity_type: str = Field(..., description="Entity-Typ Slug")
    facet_types: list[str] = Field(default_factory=list, description="Facet-Typen abfragen")
    include_core_attributes: bool = Field(default=True, description="Core-Attribute einschließen")
    filters: QueryFilters = Field(default_factory=QueryFilters, description="Filter")
    time_range: TimeRangeConfig | None = Field(None, description="Zeitbereich für History")
    sort_by: str | None = Field(None, description="Sortieren nach (Facet-Slug oder 'name')")
    sort_order: str = Field(default="asc", description="Sortierung: asc, desc")
    limit: int = Field(default=100, ge=1, le=1000, description="Max. Ergebnisse")
    offset: int = Field(default=0, ge=0, description="Offset für Paginierung")


class QueryExternalConfig(BaseModel):
    """Configuration for query_external operation."""
    # Drei Optionen für API-Auswahl
    prompt: str | None = Field(None, description="Freitext für KI-API-Suche")
    api_configuration_id: str | None = Field(None, description="Spezifische API-Konfiguration")
    api_url: str | None = Field(None, description="Direkte API-URL")

    # Optionale Speicherung
    save_to_entities: bool = Field(default=False, description="Daten auch speichern")
    entity_type_for_save: str | None = Field(None, description="Entity-Typ für Speicherung")
    facet_mapping_for_save: dict[str, Any] = Field(default_factory=dict, description="Facet-Mapping für Speicherung")
