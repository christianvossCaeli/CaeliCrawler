"""Pydantic models for AI Source Discovery Service."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SearchStrategy(BaseModel):
    """Von KI generierte Suchstrategie."""
    search_queries: List[str] = Field(..., description="3-5 Suchbegriffe")
    expected_data_type: str = Field(..., description="Art der Daten (sports_teams, municipalities, companies)")
    preferred_sources: List[str] = Field(default_factory=list, description="Priorisierte Quelltypen")
    entity_schema: Dict[str, str] = Field(default_factory=dict, description="Erwartete Felder pro Entität")
    base_tags: List[str] = Field(default_factory=list, description="Basis-Tags für alle Quellen")


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
    metadata: Dict[str, Any] = Field(default_factory=dict)
    extraction_method: str = "unknown"
    confidence: float = 0.5


class SourceWithTags(BaseModel):
    """Datenquelle mit generierten Tags."""
    name: str = Field(..., max_length=500)
    base_url: str = Field(..., max_length=2048)
    source_type: str = "WEBSITE"
    tags: List[str] = Field(default_factory=list, max_length=50)
    suggested_category_ids: List[UUID] = Field(default_factory=list, max_length=10)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class DiscoveryStats(BaseModel):
    """Statistiken über den Discovery-Prozess."""
    pages_searched: int = 0
    sources_extracted: int = 0
    sources_validated: int = 0
    duplicates_removed: int = 0


class DiscoveryResult(BaseModel):
    """Gesamtergebnis der KI-Discovery."""
    sources: List[SourceWithTags] = Field(default_factory=list)
    search_strategy: Optional[SearchStrategy] = None
    stats: DiscoveryStats = Field(default_factory=DiscoveryStats)
    warnings: List[str] = Field(default_factory=list)


class DiscoveryRequest(BaseModel):
    """Request für KI-Discovery Endpoint."""
    prompt: str = Field(..., min_length=3, max_length=1000, description="Natürlicher Prompt")
    max_results: int = Field(default=50, ge=1, le=200)
    search_depth: str = Field(default="standard", pattern="^(quick|standard|deep)$")
    include_category_suggestions: bool = Field(default=False)


class DiscoveryImportRequest(BaseModel):
    """Request zum Importieren der gefundenen Sources."""
    sources: List[SourceWithTags] = Field(..., min_length=1, max_length=100)
    category_ids: List[UUID] = Field(default_factory=list, max_length=20)
    override_tags: Dict[str, List[str]] = Field(default_factory=dict)
    skip_duplicates: bool = Field(default=True)


class CategorySuggestion(BaseModel):
    """Kategorie-Vorschlag von der KI."""
    category_id: Optional[UUID] = None  # None = neue Kategorie
    category_name: str
    category_slug: str
    confidence: float = 0.5
    is_new: bool = False
    matching_sources: int = 0
    suggested_purpose: Optional[str] = None


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
    expected_fields: List[str] = Field(default_factory=list)
    documentation_url: Optional[str] = None

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
    status_code: Optional[int] = None
    response_type: Optional[str] = None  # application/json, text/html, etc.
    item_count: Optional[int] = None  # Anzahl gefundener Items
    sample_data: Optional[List[Dict[str, Any]]] = None  # Erste 3 Items
    error_message: Optional[str] = None
    validation_time_ms: int = 0
    field_mapping: Dict[str, str] = Field(default_factory=dict)  # Erkanntes Mapping


class ValidatedAPISource(BaseModel):
    """Eine validierte API-Quelle mit extrahierten Daten."""
    api_suggestion: APISuggestion
    validation: APIValidationResult
    extracted_items: List[Dict[str, Any]] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class DiscoveryResultV2(BaseModel):
    """Erweitertes Discovery-Ergebnis mit KI-First Ansatz."""
    # Validierte API-Quellen (Priorität)
    api_sources: List[ValidatedAPISource] = Field(default_factory=list)
    # Fallback: Web-basierte Quellen (wie bisher)
    web_sources: List[SourceWithTags] = Field(default_factory=list)
    # Alle API-Vorschläge (auch gescheiterte)
    api_suggestions: List[APISuggestion] = Field(default_factory=list)
    api_validations: List[APIValidationResult] = Field(default_factory=list)
    # Suchstrategie und Stats
    search_strategy: Optional[SearchStrategy] = None
    stats: DiscoveryStats = Field(default_factory=DiscoveryStats)
    warnings: List[str] = Field(default_factory=list)
    # Flow-Info
    used_fallback: bool = False  # True wenn SERP-Fallback verwendet wurde
