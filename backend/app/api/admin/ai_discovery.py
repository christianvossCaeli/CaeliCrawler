"""Admin API endpoints for AI-powered source discovery.

Allows users to find and import data sources using natural language prompts.
The AI searches the web, extracts relevant sources, and generates tags.

Security:
- Rate limited to prevent abuse (expensive LLM + web scraping operations)
- SSRF protection on URL validation
- Requires editor role
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.core.deps import require_editor
from app.core.rate_limit import check_rate_limit
from app.core.security_logging import security_logger
from app.models import Category, DataSource, DataSourceCategory, User, SourceType
from app.api.admin.sources import validate_crawler_url
from services.ai_source_discovery import (
    AISourceDiscoveryService,
    APISuggestion,
    APIValidationResult,
    DiscoveryRequest,
    DiscoveryResult,
    DiscoveryResultV2,
    SourceWithTags,
    ValidatedAPISource,
)

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================

class DiscoveryResponse(BaseModel):
    """Response from AI discovery endpoint."""
    sources: List[SourceWithTags]
    search_strategy: Optional[dict] = None
    stats: dict
    warnings: List[str]


class ImportResult(BaseModel):
    """Result of importing discovered sources."""
    imported: int
    skipped: int
    errors: List[dict]


class DiscoveryImportRequest(BaseModel):
    """Request to import discovered sources."""
    sources: List[SourceWithTags] = Field(..., min_length=1, max_length=100)
    category_ids: List[UUID] = Field(default_factory=list, max_length=20)
    skip_duplicates: bool = Field(default=True)


class DiscoveryRequestV2(BaseModel):
    """Request for KI-First discovery (V2)."""
    prompt: str = Field(..., min_length=3, max_length=1000)
    max_results: int = Field(default=50, ge=1, le=200)
    search_depth: str = Field(default="standard", pattern="^(quick|standard|deep)$")
    skip_api_discovery: bool = Field(
        default=False,
        description="Skip API discovery and go straight to SERP"
    )


class APISuggestionResponse(BaseModel):
    """API suggestion in response."""
    api_name: str
    base_url: str
    endpoint: str
    description: str
    api_type: str
    auth_required: bool
    confidence: float
    documentation_url: Optional[str] = None


class APIValidationResponse(BaseModel):
    """API validation result in response."""
    api_name: str
    is_valid: bool
    status_code: Optional[int] = None
    item_count: Optional[int] = None
    error_message: Optional[str] = None
    field_mapping: dict = Field(default_factory=dict)


class ValidatedAPISourceResponse(BaseModel):
    """Validated API source with extracted data."""
    api_name: str
    api_url: str
    api_type: str
    item_count: int
    sample_items: List[dict] = Field(default_factory=list, max_length=5)
    tags: List[str]
    field_mapping: dict


class DiscoveryResponseV2(BaseModel):
    """Response from KI-First discovery (V2)."""
    # API sources (primary)
    api_sources: List[ValidatedAPISourceResponse]
    # Web sources (fallback)
    web_sources: List[SourceWithTags]
    # All suggestions and validations for UI display
    api_suggestions: List[APISuggestionResponse]
    api_validations: List[APIValidationResponse]
    # Stats and metadata
    stats: dict
    warnings: List[str]
    used_fallback: bool


class APIDataImportRequest(BaseModel):
    """Request to import data from a validated API."""
    api_name: str
    api_url: str
    field_mapping: dict
    items: List[dict] = Field(..., min_length=1, max_length=1000)
    category_ids: List[UUID] = Field(default_factory=list, max_length=20)
    tags: List[str] = Field(default_factory=list)
    skip_duplicates: bool = Field(default=True)


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/discover", response_model=DiscoveryResponse)
async def discover_sources(
    request: DiscoveryRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor),
):
    """
    KI-gesteuerte Datenquellen-Entdeckung.

    Gibt einen natürlichen Prompt ein (z.B. "Alle Bundesliga-Vereine") und
    die KI sucht im Web nach passenden Datenquellen.

    Parameters:
    - **prompt**: Natürlicher Prompt zur Beschreibung der gewünschten Quellen
    - **max_results**: Maximale Anzahl zurückgegebener Quellen (default: 50)
    - **search_depth**: "quick" (3 Suchen), "standard" (5), "deep" (8)

    Returns:
    - **sources**: Liste gefundener Datenquellen mit Tags
    - **search_strategy**: Von KI generierte Suchstrategie
    - **stats**: Statistiken über den Discovery-Prozess

    Rate Limit: 10 requests per minute
    """
    # Rate limiting - expensive operation (LLM + web scraping)
    await check_rate_limit(http_request, "ai_discovery", identifier=str(user.id))

    service = AISourceDiscoveryService()

    result = await service.discover_sources(
        prompt=request.prompt,
        max_results=request.max_results,
        search_depth=request.search_depth,
    )

    return DiscoveryResponse(
        sources=result.sources,
        search_strategy=result.search_strategy.model_dump() if result.search_strategy else None,
        stats=result.stats.model_dump(),
        warnings=result.warnings,
    )


@router.post("/import", response_model=ImportResult)
async def import_discovered_sources(
    request: DiscoveryImportRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor),
):
    """
    Importiert die von KI entdeckten Datenquellen.

    Parameters:
    - **sources**: Liste der zu importierenden Sources (von /discover)
    - **category_ids**: Optional: Kategorien für die Zuordnung
    - **skip_duplicates**: Duplikate überspringen (default: true)

    Rate Limit: 20 requests per minute
    """
    # Rate limiting
    await check_rate_limit(http_request, "ai_discovery_import", identifier=str(user.id))
    # Verify categories exist
    categories = []
    for cat_id in request.category_ids:
        category = await session.get(Category, cat_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category '{cat_id}' not found",
            )
        categories.append(category)

    imported = 0
    skipped = 0
    errors = []

    for source in request.sources:
        try:
            # SSRF Protection
            is_safe, error_msg = validate_crawler_url(source.base_url)
            if not is_safe:
                security_logger.log_ssrf_blocked(
                    user_id=user.id,
                    url=source.base_url,
                    reason=error_msg,
                    ip_address=http_request.client.host if http_request.client else None,
                )
                errors.append({
                    "name": source.name,
                    "error": f"SSRF Protection: {error_msg}",
                })
                continue

            # Check for duplicate
            if request.skip_duplicates:
                existing = await session.execute(
                    select(DataSource).where(DataSource.base_url == source.base_url)
                )
                if existing.scalar():
                    skipped += 1
                    continue

            # Determine source type
            try:
                source_type = SourceType(source.source_type)
            except ValueError:
                source_type = SourceType.WEBSITE

            # Create DataSource
            data_source = DataSource(
                name=source.name,
                source_type=source_type,
                base_url=source.base_url,
                tags=source.tags,
                extra_data=source.metadata,
            )
            session.add(data_source)
            await session.flush()

            # Create category associations
            for idx, category in enumerate(categories):
                assoc = DataSourceCategory(
                    data_source_id=data_source.id,
                    category_id=category.id,
                    is_primary=(idx == 0),
                )
                session.add(assoc)

            imported += 1

        except Exception as e:
            errors.append({
                "name": source.name,
                "error": str(e),
            })

    await session.commit()

    return ImportResult(
        imported=imported,
        skipped=skipped,
        errors=errors,
    )


@router.get("/examples", response_model=List[dict])
async def get_discovery_examples(
    _: User = Depends(require_editor),
):
    """
    Gibt Beispiel-Prompts für die KI-Discovery zurück.
    """
    return [
        {
            "prompt": "Alle deutschen Bundesliga-Fußballvereine",
            "description": "Findet alle 18 Bundesliga-Clubs mit offiziellen Websites",
            "expected_tags": ["de", "bundesliga", "fußball", "sport", "verein"],
        },
        {
            "prompt": "Gemeinden in Sachsen",
            "description": "Findet sächsische Gemeinde-Websites",
            "expected_tags": ["de", "sachsen", "kommunal", "gemeinde"],
        },
        {
            "prompt": "Deutsche Universitäten",
            "description": "Findet Websites deutscher Hochschulen",
            "expected_tags": ["de", "bildung", "universität", "hochschule"],
        },
        {
            "prompt": "DAX-Unternehmen",
            "description": "Findet Websites der DAX-40 Konzerne",
            "expected_tags": ["de", "dax", "unternehmen", "börse"],
        },
        {
            "prompt": "Krankenhäuser in Bayern",
            "description": "Findet bayerische Krankenhaus-Websites",
            "expected_tags": ["de", "bayern", "gesundheit", "krankenhaus"],
        },
    ]


# =============================================================================
# V2 Endpoints (KI-First)
# =============================================================================

@router.post("/discover-v2", response_model=DiscoveryResponseV2)
async def discover_sources_v2(
    request: DiscoveryRequestV2,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor),
):
    """
    KI-First Datenquellen-Entdeckung (V2).

    Neuer Flow:
    1. KI generiert API-Vorschläge basierend auf Prompt
    2. API-Vorschläge werden validiert (HTTP-Test)
    3. Bei Erfolg: Daten direkt von API abrufen
    4. Bei Misserfolg: Fallback zu SERP-basierter Suche

    Parameters:
    - **prompt**: Natürlicher Prompt (z.B. "Alle Bundesliga-Vereine")
    - **max_results**: Maximale Anzahl Ergebnisse (default: 50)
    - **search_depth**: "quick", "standard", "deep"
    - **skip_api_discovery**: Direkt zu SERP gehen (überspringt KI-API-Vorschläge)

    Returns:
    - **api_sources**: Validierte APIs mit extrahierten Daten
    - **web_sources**: SERP-basierte Quellen (Fallback)
    - **api_suggestions**: Alle KI-Vorschläge
    - **api_validations**: Validierungsergebnisse
    - **used_fallback**: True wenn SERP-Fallback verwendet wurde

    Rate Limit: 10 requests per minute
    """
    # Rate limiting - expensive operation
    await check_rate_limit(http_request, "ai_discovery", identifier=str(user.id))

    service = AISourceDiscoveryService()

    result = await service.discover_sources_v2(
        prompt=request.prompt,
        max_results=request.max_results,
        search_depth=request.search_depth,
        skip_api_discovery=request.skip_api_discovery,
    )

    # Convert to response models
    api_sources_response = []
    for source in result.api_sources:
        api_sources_response.append(ValidatedAPISourceResponse(
            api_name=source.api_suggestion.api_name,
            api_url=source.api_suggestion.full_url,
            api_type=source.api_suggestion.api_type,
            item_count=len(source.extracted_items),
            sample_items=source.extracted_items[:5],
            tags=source.tags,
            field_mapping=source.validation.field_mapping,
        ))

    api_suggestions_response = [
        APISuggestionResponse(
            api_name=s.api_name,
            base_url=s.base_url,
            endpoint=s.endpoint,
            description=s.description,
            api_type=s.api_type,
            auth_required=s.auth_required,
            confidence=s.confidence,
            documentation_url=s.documentation_url,
        )
        for s in result.api_suggestions
    ]

    api_validations_response = [
        APIValidationResponse(
            api_name=v.suggestion.api_name,
            is_valid=v.is_valid,
            status_code=v.status_code,
            item_count=v.item_count,
            error_message=v.error_message,
            field_mapping=v.field_mapping,
        )
        for v in result.api_validations
    ]

    return DiscoveryResponseV2(
        api_sources=api_sources_response,
        web_sources=result.web_sources,
        api_suggestions=api_suggestions_response,
        api_validations=api_validations_response,
        stats=result.stats.model_dump(),
        warnings=result.warnings,
        used_fallback=result.used_fallback,
    )


@router.post("/import-api-data", response_model=ImportResult)
async def import_api_data(
    request: APIDataImportRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor),
):
    """
    Importiert Daten von einer validierten API als DataSources.

    Nimmt die extrahierten Items von einer API und erstellt DataSource-Einträge.

    Parameters:
    - **api_name**: Name der API (für Logging)
    - **api_url**: URL der API (für Referenz)
    - **field_mapping**: Feld-Mapping (z.B. {"teamName": "name"})
    - **items**: Die zu importierenden Items
    - **category_ids**: Kategorien für Zuordnung
    - **tags**: Tags für alle erstellten Sources
    - **skip_duplicates**: Duplikate überspringen

    Rate Limit: 20 requests per minute
    """
    await check_rate_limit(http_request, "ai_discovery_import", identifier=str(user.id))

    # Verify categories exist
    categories = []
    for cat_id in request.category_ids:
        category = await session.get(Category, cat_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category '{cat_id}' not found",
            )
        categories.append(category)

    imported = 0
    skipped = 0
    errors = []

    for item in request.items:
        try:
            # Get name from mapping
            name = None
            base_url = None

            for source_field, target_field in request.field_mapping.items():
                if target_field == "name" and source_field in item:
                    name = str(item[source_field])
                elif target_field == "base_url" and source_field in item:
                    base_url = str(item[source_field])

            # Fallback: try common field names
            if not name:
                name = item.get("name") or item.get("title") or item.get("label")
            if not base_url:
                base_url = item.get("website") or item.get("url") or item.get("homepage")

            if not name:
                errors.append({
                    "name": str(item)[:100],
                    "error": "Kein Name gefunden",
                })
                continue

            # Use API URL as base_url if no item URL
            if not base_url:
                base_url = request.api_url

            # SSRF Protection
            is_safe, error_msg = validate_crawler_url(base_url)
            if not is_safe:
                security_logger.log_ssrf_blocked(
                    user_id=user.id,
                    url=base_url,
                    reason=error_msg,
                    ip_address=http_request.client.host if http_request.client else None,
                )
                errors.append({
                    "name": name,
                    "error": f"SSRF Protection: {error_msg}",
                })
                continue

            # Check for duplicate
            if request.skip_duplicates and base_url:
                existing = await session.execute(
                    select(DataSource).where(DataSource.base_url == base_url)
                )
                if existing.scalar():
                    skipped += 1
                    continue

            # Create DataSource
            data_source = DataSource(
                name=name[:500],  # Limit name length
                source_type=SourceType.WEBSITE,
                base_url=base_url,
                tags=request.tags,
                extra_data={
                    "api_source": request.api_name,
                    "api_url": request.api_url,
                    **{k: v for k, v in item.items() if k not in request.field_mapping},
                },
            )
            session.add(data_source)
            await session.flush()

            # Create category associations
            for idx, category in enumerate(categories):
                assoc = DataSourceCategory(
                    data_source_id=data_source.id,
                    category_id=category.id,
                    is_primary=(idx == 0),
                )
                session.add(assoc)

            imported += 1

        except Exception as e:
            errors.append({
                "name": str(item.get("name", item))[:100],
                "error": str(e),
            })

    await session.commit()

    return ImportResult(
        imported=imported,
        skipped=skipped,
        errors=errors,
    )
