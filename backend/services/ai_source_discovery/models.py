"""Pydantic models for AI Source Discovery Service."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class SearchStrategy(BaseModel):
    """Von KI generierte Suchstrategie."""

    search_queries: list[str] = Field(..., description="3-5 Suchbegriffe")
    expected_data_type: str = Field(..., description="Art der Daten (sports_teams, municipalities, companies)")
    preferred_sources: list[str] = Field(default_factory=list, description="Priorisierte Quelltypen")
    entity_schema: dict[str, Any] = Field(
        default_factory=dict, description="Erwartete Felder pro Entität (kann verschachtelt sein)"
    )
    base_tags: list[str] = Field(default_factory=list, description="Basis-Tags für alle Quellen")
    # Intelligente Quellenbegrenzung durch KI
    expected_entity_count: int = Field(
        default=50, description="Erwartete Anzahl der Entitäten (z.B. 18 für Bundesliga-Vereine)"
    )
    recommended_max_sources: int = Field(
        default=50, description="Empfohlene maximale Quellenanzahl (ca. 1.5x expected_entity_count)"
    )
    reasoning: str = Field(default="", description="Begründung für die Quellenanzahl")


class SearchResult(BaseModel):
    """Einzelnes Web-Suchergebnis."""

    url: str
    title: str
    snippet: str = ""
    source_type: str = "unknown"  # wikipedia, api, html_table, json_ld
    confidence: float = 0.5


class ExtractedSource(BaseModel):
    """Aus Webseite extrahierte Datenquelle."""

    name: str
    base_url: str
    source_type: str = "WEBSITE"
    metadata: dict[str, Any] = Field(default_factory=dict)
    extraction_method: str = "unknown"
    confidence: float = 0.5


class SourceWithTags(BaseModel):
    """Datenquelle mit generierten Tags."""

    name: str = Field(..., max_length=500)
    base_url: str = Field(..., max_length=2048)
    source_type: str = "WEBSITE"
    tags: list[str] = Field(default_factory=list, max_length=50)
    suggested_category_ids: list[UUID] = Field(default_factory=list, max_length=10)
    metadata: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    @field_validator("name", mode="before")
    @classmethod
    def truncate_name(cls, v: str) -> str:
        """Truncate name to max 500 characters."""
        if isinstance(v, str) and len(v) > 500:
            return v[:497] + "..."
        return v


class DiscoveryStats(BaseModel):
    """Statistiken über den Discovery-Prozess."""

    pages_searched: int = 0
    sources_extracted: int = 0
    sources_validated: int = 0
    duplicates_removed: int = 0


class DiscoveryResult(BaseModel):
    """Gesamtergebnis der KI-Discovery."""

    sources: list[SourceWithTags] = Field(default_factory=list)
    search_strategy: SearchStrategy | None = None
    stats: DiscoveryStats = Field(default_factory=DiscoveryStats)
    warnings: list[str] = Field(default_factory=list)


class DiscoveryRequest(BaseModel):
    """Request für KI-Discovery Endpoint."""

    prompt: str = Field(..., min_length=3, max_length=1000, description="Natürlicher Prompt")
    max_results: int = Field(default=50, ge=1, le=200)
    search_depth: str = Field(default="standard", pattern="^(quick|standard|deep)$")
    include_category_suggestions: bool = Field(default=False)


class DiscoveryImportRequest(BaseModel):
    """Request zum Importieren der gefundenen Sources."""

    sources: list[SourceWithTags] = Field(..., min_length=1, max_length=100)
    category_ids: list[UUID] = Field(default_factory=list, max_length=20)
    override_tags: dict[str, list[str]] = Field(default_factory=dict)
    skip_duplicates: bool = Field(default=True)


class CategorySuggestion(BaseModel):
    """Kategorie-Vorschlag von der KI."""

    category_id: UUID | None = None  # None = neue Kategorie
    category_name: str
    category_slug: str
    confidence: float = 0.5
    is_new: bool = False
    matching_sources: int = 0
    suggested_purpose: str | None = None


# ============================================================
# KI-First API Discovery Models
# ============================================================


class APISuggestion(BaseModel):
    """Von KI generierter API-Vorschlag."""

    api_name: str = Field(..., description="Name der API")
    base_url: str = Field(..., description="Basis-URL der API")
    endpoint: str = Field(..., description="Konkreter Endpoint-Pfad")
    description: str = Field(default="", description="Beschreibung der API")
    api_type: str = Field(default="REST", pattern="^(REST|GRAPHQL|SPARQL|OPARL)$")
    auth_required: bool = Field(default=False)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    expected_fields: list[str] = Field(default_factory=list)
    documentation_url: str | None = None

    @property
    def full_url(self) -> str:
        """Kombiniert base_url und endpoint."""
        base = self.base_url.rstrip("/")
        endpoint = self.endpoint if self.endpoint.startswith("/") else f"/{self.endpoint}"
        return f"{base}{endpoint}"


class APIValidationResult(BaseModel):
    """Ergebnis der API-Validierung."""

    suggestion: APISuggestion
    is_valid: bool = False
    status_code: int | None = None
    response_type: str | None = None  # application/json, text/html, etc.
    item_count: int | None = None  # Anzahl gefundener Items
    sample_data: list[dict[str, Any]] | None = None  # Erste 3 Items
    error_message: str | None = None
    validation_time_ms: int = 0
    field_mapping: dict[str, str] = Field(default_factory=dict)  # Erkanntes Mapping


class ValidatedAPISource(BaseModel):
    """Eine validierte API-Quelle mit extrahierten Daten."""

    api_suggestion: APISuggestion
    validation: APIValidationResult
    extracted_items: list[dict[str, Any]] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class DiscoveryResultV2(BaseModel):
    """Erweitertes Discovery-Ergebnis mit KI-First Ansatz."""

    # Validierte API-Quellen (Priorität)
    api_sources: list[ValidatedAPISource] = Field(default_factory=list)
    # Fallback: Web-basierte Quellen (wie bisher)
    web_sources: list[SourceWithTags] = Field(default_factory=list)
    # Alle API-Vorschläge (auch gescheiterte)
    api_suggestions: list[APISuggestion] = Field(default_factory=list)
    api_validations: list[APIValidationResult] = Field(default_factory=list)
    # Suchstrategie und Stats
    search_strategy: SearchStrategy | None = None
    stats: DiscoveryStats = Field(default_factory=DiscoveryStats)
    warnings: list[str] = Field(default_factory=list)
    # Flow-Info
    used_fallback: bool = False  # True wenn SERP-Fallback verwendet wurde
    from_template: bool = False  # True wenn Vorlagen verwendet wurden
