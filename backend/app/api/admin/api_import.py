"""Admin API endpoints for external API import functionality.

This module provides endpoints for importing DataSources from external APIs
like Wikidata (SPARQL), OParl (council information systems), and custom REST APIs.

Features:
- Preview import results before execution
- AI-powered field mapping suggestions
- Support for multiple API types with templates
- Tag assignment based on API source
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.sources import validate_crawler_url
from app.core.audit import AuditContext
from app.core.deps import require_editor
from app.database import get_session
from app.models import Category, User
from app.models.audit_log import AuditAction

# =============================================================================
# Schemas
# =============================================================================


class ApiTemplate(BaseModel):
    """Template for a specific API type."""

    id: str
    name: str
    description: str
    api_type: str
    default_url: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    default_tags: list[str] = Field(default_factory=list)


class ApiImportPreviewRequest(BaseModel):
    """Request to preview an API import."""

    api_type: str = Field(..., description="API type: wikidata, oparl, govdata, custom")
    api_url: str = Field(..., description="API endpoint URL")
    params: dict[str, Any] = Field(default_factory=dict, description="API-specific parameters")
    sample_size: int = Field(default=10, ge=1, le=100, description="Number of preview items")


class ApiImportPreviewItem(BaseModel):
    """Single item in the import preview."""

    name: str
    base_url: str
    source_type: str = "WEBSITE"
    suggested_tags: list[str] = Field(default_factory=list)
    extra_data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class ApiImportPreviewResponse(BaseModel):
    """Response with preview of items to be imported."""

    items: list[ApiImportPreviewItem]
    total_available: int
    field_mapping: dict[str, str] = Field(default_factory=dict)
    suggested_tags: list[str] = Field(default_factory=list)


class ApiImportExecuteRequest(BaseModel):
    """Request to execute an API import."""

    api_type: str = Field(..., description="API type: wikidata, oparl, govdata, custom")
    api_url: str = Field(..., max_length=2048, description="API endpoint URL")
    params: dict[str, Any] = Field(default_factory=dict)
    category_ids: list[UUID] = Field(..., min_length=1, max_length=20, description="Categories to assign")
    default_tags: list[str] = Field(default_factory=list, max_length=50)
    field_mapping: dict[str, str] = Field(default_factory=dict, description="Field mapping from API to DataSource")
    skip_duplicates: bool = Field(default=True)
    max_items: int = Field(default=1000, ge=1, le=10000)


class ApiImportExecuteResponse(BaseModel):
    """Result of API import execution."""

    imported: int
    skipped: int
    errors: list[dict[str, str]]


# =============================================================================
# Templates
# =============================================================================

# Pre-defined templates for common API types
API_TEMPLATES: dict[str, ApiTemplate] = {
    "wikidata_de_gemeinden_nrw": ApiTemplate(
        id="wikidata_de_gemeinden_nrw",
        name="Wikidata: NRW Gemeinden",
        description="Deutsche Gemeinden in Nordrhein-Westfalen via Wikidata SPARQL",
        api_type="wikidata",
        default_url="https://query.wikidata.org/sparql",
        parameters={
            "sparql_query": """
SELECT DISTINCT ?item ?itemLabel ?website WHERE {
  ?item wdt:P31/wdt:P279* wd:Q262166 .  # Instance of municipality in Germany
  ?item wdt:P131* wd:Q1198 .             # Located in NRW
  OPTIONAL { ?item wdt:P856 ?website }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "de,en" }
}
LIMIT 500
""",
        },
        default_tags=["de", "nrw", "kommunal", "gemeinde"],
    ),
    "wikidata_de_gemeinden_bayern": ApiTemplate(
        id="wikidata_de_gemeinden_bayern",
        name="Wikidata: Bayern Gemeinden",
        description="Deutsche Gemeinden in Bayern via Wikidata SPARQL",
        api_type="wikidata",
        default_url="https://query.wikidata.org/sparql",
        parameters={
            "sparql_query": """
SELECT DISTINCT ?item ?itemLabel ?website WHERE {
  ?item wdt:P31/wdt:P279* wd:Q262166 .  # Instance of municipality in Germany
  ?item wdt:P131* wd:Q980 .              # Located in Bayern
  OPTIONAL { ?item wdt:P856 ?website }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "de,en" }
}
LIMIT 2500
""",
        },
        default_tags=["de", "bayern", "kommunal", "gemeinde"],
    ),
    "wikidata_at_gemeinden": ApiTemplate(
        id="wikidata_at_gemeinden",
        name="Wikidata: Österreichische Gemeinden",
        description="Gemeinden in Österreich via Wikidata SPARQL",
        api_type="wikidata",
        default_url="https://query.wikidata.org/sparql",
        parameters={
            "sparql_query": """
SELECT DISTINCT ?item ?itemLabel ?website WHERE {
  ?item wdt:P31 wd:Q667509 .            # Instance of municipality in Austria
  OPTIONAL { ?item wdt:P856 ?website }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "de,en" }
}
LIMIT 2500
""",
        },
        default_tags=["at", "kommunal", "gemeinde"],
    ),
    "oparl_bodies": ApiTemplate(
        id="oparl_bodies",
        name="OParl: Alle Bodies",
        description="Alle registrierten OParl-Bodies (Ratsinformationssysteme)",
        api_type="oparl",
        default_url="https://oparl.org/api/bodies",
        parameters={},
        default_tags=["de", "oparl", "ratsinformation"],
    ),
}


# =============================================================================
# Router
# =============================================================================

router = APIRouter()


@router.get("/templates", response_model=list[ApiTemplate])
async def list_api_templates(
    _: User = Depends(require_editor),
):
    """
    List all available API import templates.

    Templates provide pre-configured queries for common data sources like:
    - Wikidata SPARQL queries for German/Austrian municipalities
    - OParl API for council information systems
    """
    return list(API_TEMPLATES.values())


@router.get("/templates/{template_id}", response_model=ApiTemplate)
async def get_api_template(
    template_id: str,
    _: User = Depends(require_editor),
):
    """Get a specific API import template by ID."""
    template = API_TEMPLATES.get(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found",
        )
    return template


@router.post("/preview", response_model=ApiImportPreviewResponse)
async def preview_api_import(
    request: ApiImportPreviewRequest,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """
    Preview what would be imported from an external API.

    This endpoint fetches a sample from the API and analyzes the response
    to suggest field mappings and tags.

    Supported API types:
    - `wikidata`: SPARQL endpoint (params.sparql_query required)
    - `oparl`: OParl API for council information
    - `custom`: Generic REST API (params.name_field, params.url_field)
    """
    from services.api_import.fetcher import fetch_api_preview

    try:
        items, total_available, field_mapping, suggested_tags = await fetch_api_preview(
            api_type=request.api_type,
            api_url=request.api_url,
            params=request.params,
            sample_size=request.sample_size,
        )

        return ApiImportPreviewResponse(
            items=items,
            total_available=total_available,
            field_mapping=field_mapping,
            suggested_tags=suggested_tags,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"API fetch failed: {str(e)}",
        ) from None


@router.post("/execute", response_model=ApiImportExecuteResponse)
async def execute_api_import(
    data: ApiImportExecuteRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """
    Execute an API import and create DataSources.

    Fetches all data from the API and creates DataSources with:
    - N:M category associations
    - Tags from API + default_tags
    - Field mapping applied
    """
    from app.models import DataSource, DataSourceCategory, SourceType
    from services.api_import.fetcher import fetch_all_from_api

    # Verify all categories exist
    categories = []
    for cat_id in data.category_ids:
        category = await session.get(Category, cat_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category '{cat_id}' not found",
            )
        categories.append(category)

    try:
        # Fetch all items from API
        items = await fetch_all_from_api(
            api_type=data.api_type,
            api_url=data.api_url,
            params=data.params,
            field_mapping=data.field_mapping,
            max_items=data.max_items,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"API fetch failed: {str(e)}",
        ) from None

    imported = 0
    skipped = 0
    errors = []

    for item in items:
        try:
            base_url = item.get("base_url") or item.get("website") or item.get("url")
            name = item.get("name") or item.get("label") or item.get("title")

            if not base_url:
                errors.append({"name": name or "Unknown", "error": "No URL found"})
                continue

            if not name:
                # Use domain as name if no name available
                from urllib.parse import urlparse

                name = urlparse(base_url).netloc

            # SSRF Protection
            is_safe, error_msg = validate_crawler_url(base_url)
            if not is_safe:
                errors.append({"url": base_url, "error": f"SSRF Protection: {error_msg}"})
                continue

            # Check for duplicate
            if data.skip_duplicates:
                existing = await session.execute(select(DataSource).where(DataSource.base_url == base_url))
                if existing.scalar():
                    skipped += 1
                    continue

            # Combine tags
            item_tags = item.get("tags", []) if isinstance(item.get("tags"), list) else []
            combined_tags = list(set(data.default_tags + item_tags))

            # Determine source type
            source_type_str = item.get("source_type", "WEBSITE")
            try:
                source_type = SourceType(source_type_str)
            except ValueError:
                source_type = SourceType.WEBSITE

            # Create DataSource
            source = DataSource(
                name=name,
                source_type=source_type,
                base_url=base_url,
                tags=combined_tags,
                extra_data=item.get("extra_data", {}),
            )
            session.add(source)
            await session.flush()

            # Create N:M category associations
            for idx, category in enumerate(categories):
                assoc = DataSourceCategory(
                    data_source_id=source.id,
                    category_id=category.id,
                    is_primary=(idx == 0),
                )
                session.add(assoc)

            imported += 1

        except Exception as e:
            errors.append(
                {
                    "name": item.get("name", "Unknown"),
                    "error": str(e),
                }
            )

    # Audit log for API import
    category_names = [c.name for c in categories]
    async with AuditContext(session, current_user, http_request) as audit:
        audit.track_action(
            action=AuditAction.IMPORT,
            entity_type="DataSource",
            entity_name=f"API Import ({data.api_type})",
            changes={
                "api_type": data.api_type,
                "api_url": data.api_url,
                "imported": imported,
                "skipped": skipped,
                "errors_count": len(errors),
                "categories": category_names,
                "default_tags": data.default_tags,
            },
        )
        await session.commit()

    return ApiImportExecuteResponse(
        imported=imported,
        skipped=skipped,
        errors=errors,
    )
