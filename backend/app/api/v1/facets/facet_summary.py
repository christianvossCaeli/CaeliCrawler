"""API endpoints for Entity Facets Summary."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.database import get_session
from app.models import (
    Entity,
    EntityType,
    FacetType,
    FacetValue,
)
from app.schemas.facet_value import (
    EntityFacetsSummary,
    FacetValueAggregated,
    FacetValueListResponse,
    FacetValueResponse,
)

router = APIRouter()


@router.get("/entity/{entity_id}/referenced-by", response_model=FacetValueListResponse)
async def get_facets_referencing_entity(
    entity_id: UUID,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    facet_type_slug: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """
    Get all facet values that reference this entity as their target_entity.

    This shows where this entity is used/referenced, e.g., a Person entity
    being referenced in contact facets of other entities.
    """
    # Verify entity exists
    entity = await session.get(Entity, entity_id)
    if not entity:
        raise NotFoundError("Entity", str(entity_id))

    # Build query for facet values where target_entity_id = entity_id
    query = select(FacetValue).where(
        FacetValue.target_entity_id == entity_id,
        FacetValue.is_active.is_(True),
    )

    if facet_type_slug:
        subq = select(FacetType.id).where(FacetType.slug == facet_type_slug)
        query = query.where(FacetValue.facet_type_id.in_(subq))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Paginate with eager loading
    query = (
        query.options(
            selectinload(FacetValue.entity),
            selectinload(FacetValue.facet_type),
            selectinload(FacetValue.category),
            selectinload(FacetValue.source_document),
        )
        .order_by(FacetValue.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )

    result = await session.execute(query)
    values = result.scalars().all()

    # Build response items
    items = []
    for fv in values:
        item = FacetValueResponse.model_validate(fv)
        item.entity_name = fv.entity.name if fv.entity else None
        item.facet_type_name = fv.facet_type.name if fv.facet_type else None
        item.facet_type_slug = fv.facet_type.slug if fv.facet_type else None
        item.category_name = fv.category.name if fv.category else None
        item.document_title = fv.source_document.title if fv.source_document else None
        item.document_url = fv.source_document.original_url if fv.source_document else None
        # Target entity is the entity we're querying for
        item.target_entity_name = entity.name
        item.target_entity_slug = entity.slug
        items.append(item)

    return FacetValueListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
    )


@router.get("/entity/{entity_id}/summary", response_model=EntityFacetsSummary)
async def get_entity_facets_summary(
    entity_id: UUID,
    category_id: UUID | None = Query(default=None),
    time_filter: str | None = Query(
        default=None,
        description="Time filter: 'future_only', 'past_only', or 'all'",
        pattern="^(future_only|past_only|all)$",
    ),
    min_confidence: float = Query(default=0.0, ge=0, le=1),
    session: AsyncSession = Depends(get_session),
):
    """Get summary of all facets for an entity."""
    entity = await session.get(Entity, entity_id)
    if not entity:
        raise NotFoundError("Entity", str(entity_id))

    entity_type = await session.get(EntityType, entity.entity_type_id)
    entity_type_slug = entity_type.slug if entity_type else None

    # Build subquery for applicable facet types based on entity type
    # A FacetType is applicable if:
    # 1. applicable_entity_type_slugs is empty (applies to all entity types), OR
    # 2. applicable_entity_type_slugs contains the current entity's type slug
    if entity_type_slug:
        applicable_facet_types_subq = select(FacetType.id).where(
            or_(
                FacetType.applicable_entity_type_slugs == [],  # Empty = applies to all
                FacetType.applicable_entity_type_slugs.any(entity_type_slug),  # Contains this type
            )
        )
    else:
        # If entity has no type, only show facets that apply to all
        applicable_facet_types_subq = select(FacetType.id).where(FacetType.applicable_entity_type_slugs == [])

    # Base query for facet values - only include values from applicable facet types
    # Eager load target_entity and its entity_type for entity references (e.g., contacts -> person)
    # Also load source_document for document info display
    query = (
        select(FacetValue)
        .options(
            selectinload(FacetValue.target_entity).selectinload(Entity.entity_type),
            selectinload(FacetValue.source_document),
        )
        .where(
            FacetValue.entity_id == entity_id,
            FacetValue.is_active.is_(True),
            FacetValue.confidence_score >= min_confidence,
            FacetValue.facet_type_id.in_(applicable_facet_types_subq),
        )
    )

    if category_id:
        query = query.where(FacetValue.category_id == category_id)

    # Apply time filter
    now = datetime.now(UTC)
    if time_filter == "future_only":
        query = query.where(
            or_(
                FacetValue.event_date >= now,
                FacetValue.valid_until >= now,
                and_(FacetValue.event_date.is_(None), FacetValue.valid_until.is_(None)),
            )
        )
    elif time_filter == "past_only":
        query = query.where(or_(FacetValue.event_date < now, FacetValue.valid_until < now))

    result = await session.execute(query)
    values = result.scalars().all()

    # Group values by facet type
    by_facet_type: dict[UUID, list[FacetValue]] = {}
    for fv in values:
        if fv.facet_type_id not in by_facet_type:
            by_facet_type[fv.facet_type_id] = []
        by_facet_type[fv.facet_type_id].append(fv)

    # Load ALL applicable facet types for this entity type (including those without values)
    if entity_type_slug:
        applicable_types_query = (
            select(FacetType)
            .where(
                FacetType.is_active.is_(True),
                or_(
                    FacetType.applicable_entity_type_slugs == [],  # Empty = applies to all
                    FacetType.applicable_entity_type_slugs.any(entity_type_slug),  # Contains this type
                ),
            )
            .order_by(FacetType.display_order, FacetType.name)
        )
    else:
        applicable_types_query = (
            select(FacetType)
            .where(FacetType.is_active.is_(True), FacetType.applicable_entity_type_slugs == [])
            .order_by(FacetType.display_order, FacetType.name)
        )

    applicable_types_result = await session.execute(applicable_types_query)
    applicable_facet_types = applicable_types_result.scalars().all()

    # Build aggregated facets for ALL applicable types (even without values)
    facets_by_type = []
    total_values = 0
    verified_count = 0

    for facet_type in applicable_facet_types:
        type_values = by_facet_type.get(facet_type.id, [])

        if type_values:
            avg_confidence = sum(v.confidence_score or 0 for v in type_values) / len(type_values)
            type_verified_count = sum(1 for v in type_values if v.human_verified)
            latest_value = max((v.created_at for v in type_values), default=None)
            # Sort: verified first, then by confidence (desc), then by created_at (desc)
            sorted_values = sorted(
                type_values,
                key=lambda x: (
                    0 if x.human_verified else 1,  # Verified first
                    -(x.confidence_score or 0),  # Higher confidence first
                    -(x.created_at.timestamp() if x.created_at else 0),  # Newer first
                ),
            )
            sample_values = [
                {
                    "id": str(v.id),
                    "value": v.value,
                    "text_representation": v.text_representation,
                    "confidence_score": v.confidence_score,
                    "human_verified": v.human_verified,
                    "source_type": v.source_type.value if v.source_type else "DOCUMENT",
                    "source_url": v.source_url,
                    "created_at": v.created_at.isoformat() if v.created_at else None,
                    # Document source info
                    "source_document_id": str(v.source_document_id) if v.source_document_id else None,
                    "document_title": v.source_document.title if v.source_document else None,
                    "document_url": v.source_document.original_url if v.source_document else None,
                    # Target entity info for entity references (e.g., contacts -> person)
                    "target_entity_id": str(v.target_entity_id) if v.target_entity_id else None,
                    "target_entity_name": v.target_entity.name if v.target_entity else None,
                    "target_entity_slug": v.target_entity.slug if v.target_entity else None,
                    "target_entity_type_slug": v.target_entity.entity_type.slug
                    if v.target_entity and v.target_entity.entity_type
                    else None,
                }
                for v in sorted_values[:5]  # Show up to 5 samples
            ]
        else:
            avg_confidence = 0.0
            type_verified_count = 0
            latest_value = None
            sample_values = []

        facets_by_type.append(
            FacetValueAggregated(
                facet_type_id=facet_type.id,
                facet_type_slug=facet_type.slug,
                facet_type_name=facet_type.name,
                facet_type_icon=facet_type.icon,
                facet_type_color=facet_type.color,
                facet_type_value_type=facet_type.value_type.value
                if hasattr(facet_type.value_type, "value")
                else facet_type.value_type,
                value_schema=facet_type.value_schema,
                display_order=facet_type.display_order or 0,
                value_count=len(type_values),
                verified_count=type_verified_count,
                avg_confidence=round(avg_confidence, 2),
                latest_value=latest_value,
                sample_values=sample_values,
            )
        )

        total_values += len(type_values)
        verified_count += type_verified_count

    # Sort by display order
    facets_by_type.sort(key=lambda x: x.display_order)

    return EntityFacetsSummary(
        entity_id=entity.id,
        entity_name=entity.name,
        entity_type_slug=entity_type.slug if entity_type else None,
        total_facet_values=total_values,
        verified_count=verified_count,
        facet_type_count=len(facets_by_type),
        facets_by_type=facets_by_type,
    )
