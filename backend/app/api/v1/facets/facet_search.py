"""API endpoints for Facet Value Full-Text Search."""

import time
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models import (
    FacetType,
    FacetValue,
)
from app.schemas.facet_value import (
    FacetValueSearchResponse,
    FacetValueSearchResult,
)

router = APIRouter()


@router.get("/search", response_model=FacetValueSearchResponse)
async def search_facet_values(
    q: str = Query(..., min_length=2, description="Search query"),
    entity_id: UUID | None = Query(default=None, description="Filter by entity"),
    facet_type_slug: str | None = Query(default=None, description="Filter by facet type"),
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=20, ge=1, le=100, description="Results per page"),
    session: AsyncSession = Depends(get_session),
):
    """
    Full-text search across facet values with relevance ranking.

    Uses PostgreSQL full-text search (tsvector/tsquery) for efficient
    searching with German language support. Results are ranked by relevance.

    Features:
    - German language stemming and normalization
    - Relevance-based ranking
    - Highlighted search matches
    """
    start_time = time.time()

    # Build the search query with ts_rank for relevance scoring
    search_query = func.plainto_tsquery("german", q)

    # Build base query with ranking
    query = (
        select(
            FacetValue,
            func.ts_rank(FacetValue.search_vector, search_query).label("rank"),
            func.ts_headline(
                "german",
                FacetValue.text_representation,
                search_query,
                "StartSel=<mark>, StopSel=</mark>, MaxWords=50, MinWords=20",
            ).label("headline"),
        )
        .where(FacetValue.search_vector.op("@@")(search_query))
        .where(FacetValue.is_active.is_(True))
    )

    # Apply filters
    if entity_id:
        query = query.where(FacetValue.entity_id == entity_id)
    if facet_type_slug:
        subq = select(FacetType.id).where(FacetType.slug == facet_type_slug)
        query = query.where(FacetValue.facet_type_id.in_(subq))

    # Order by rank (highest first) with pagination
    query = query.order_by(func.ts_rank(FacetValue.search_vector, search_query).desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    # Execute with eager loading
    query = query.options(
        selectinload(FacetValue.entity),
        selectinload(FacetValue.facet_type),
    )

    result = await session.execute(query)
    rows = result.all()

    # Count total matches (without limit)
    count_query = (
        select(func.count())
        .select_from(FacetValue)
        .where(FacetValue.search_vector.op("@@")(search_query))
        .where(FacetValue.is_active.is_(True))
    )
    if entity_id:
        count_query = count_query.where(FacetValue.entity_id == entity_id)
    if facet_type_slug:
        subq = select(FacetType.id).where(FacetType.slug == facet_type_slug)
        count_query = count_query.where(FacetValue.facet_type_id.in_(subq))

    total = (await session.execute(count_query)).scalar() or 0

    # Build response
    items = []
    for row in rows:
        fv = row[0]
        rank = row[1] if row[1] else 0.0
        headline = row[2]

        items.append(
            FacetValueSearchResult(
                id=fv.id,
                entity_id=fv.entity_id,
                entity_name=fv.entity.name if fv.entity else "Unknown",
                facet_type_id=fv.facet_type_id,
                facet_type_slug=fv.facet_type.slug if fv.facet_type else "",
                facet_type_name=fv.facet_type.name if fv.facet_type else "",
                value=fv.value,
                text_representation=fv.text_representation,
                headline=headline,
                rank=round(rank, 4),
                confidence_score=fv.confidence_score,
                human_verified=fv.human_verified,
                source_type=fv.source_type.value if fv.source_type else "DOCUMENT",
                created_at=fv.created_at,
            )
        )

    search_time_ms = (time.time() - start_time) * 1000
    pages = (total + per_page - 1) // per_page if total > 0 else 1

    return FacetValueSearchResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
        query=q,
        search_time_ms=round(search_time_ms, 2),
    )
