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
    DiscoveryRequest,
    DiscoveryResult,
    SourceWithTags,
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
