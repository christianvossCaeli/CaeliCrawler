"""API endpoints for FacetValue management."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import AuditContext
from app.core.deps import require_editor
from app.core.exceptions import ConflictError, NotFoundError
from app.database import get_session
from app.models import (
    Entity,
    EntityType,
    FacetType,
    FacetValue,
)
from app.models.audit_log import AuditAction
from app.models.facet_value import FacetValueSourceType
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.facet_value import (
    FacetValueCreate,
    FacetValueListResponse,
    FacetValueResponse,
    FacetValueUpdate,
)
from app.utils.text import build_text_representation

router = APIRouter()


@router.get("/values", response_model=FacetValueListResponse)
async def list_facet_values(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    entity_id: UUID | None = Query(default=None),
    facet_type_id: UUID | None = Query(default=None),
    facet_type_slug: str | None = Query(default=None),
    category_id: UUID | None = Query(default=None),
    min_confidence: float = Query(default=0.0, ge=0, le=1),
    human_verified: bool | None = Query(default=None),
    search: str | None = Query(
        default=None,
        description="Search in text_representation",
        min_length=2,
    ),
    time_filter: str | None = Query(
        default=None,
        description="Time filter: 'future_only', 'past_only', or 'all'",
        pattern="^(future_only|past_only|all)$",
    ),
    is_active: bool | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """List facet values with filters and search."""
    query = select(FacetValue)

    if entity_id:
        query = query.where(FacetValue.entity_id == entity_id)
    if facet_type_id:
        query = query.where(FacetValue.facet_type_id == facet_type_id)
    elif facet_type_slug:
        subq = select(FacetType.id).where(FacetType.slug == facet_type_slug)
        query = query.where(FacetValue.facet_type_id.in_(subq))
    if category_id:
        query = query.where(FacetValue.category_id == category_id)
    if min_confidence > 0:
        query = query.where(FacetValue.confidence_score >= min_confidence)
    if human_verified is not None:
        query = query.where(FacetValue.human_verified.is_(human_verified))
    if is_active is not None:
        query = query.where(FacetValue.is_active.is_(is_active))
    if search:
        # Use PostgreSQL full-text search for better performance
        # Falls back to ILIKE if search_vector not populated
        search_query = func.plainto_tsquery("german", search)
        # Escape SQL wildcards in ILIKE fallback to prevent injection
        escaped_search = search.replace("%", r"\%").replace("_", r"\_")
        search_pattern = f"%{escaped_search}%"
        query = query.where(
            or_(
                FacetValue.search_vector.op("@@")(search_query),
                FacetValue.text_representation.ilike(search_pattern, escape="\\"),
            )
        )

    # Time-based filtering
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

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Sort: verified first, then by confidence (desc), then by created_at (desc)
    # Use selectinload for eager loading of relationships
    query = (
        query.options(
            selectinload(FacetValue.entity),
            selectinload(FacetValue.facet_type),
            selectinload(FacetValue.category),
            selectinload(FacetValue.source_document),
            selectinload(FacetValue.target_entity).selectinload(Entity.entity_type),
        )
        .order_by(FacetValue.human_verified.desc(), FacetValue.confidence_score.desc(), FacetValue.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await session.execute(query)
    values = result.scalars().all()

    # Build response items with enriched data from relationships
    items = []
    for fv in values:
        item = FacetValueResponse.model_validate(fv)
        item.entity_name = fv.entity.name if fv.entity else None
        item.facet_type_name = fv.facet_type.name if fv.facet_type else None
        item.facet_type_slug = fv.facet_type.slug if fv.facet_type else None
        item.category_name = fv.category.name if fv.category else None
        item.document_title = fv.source_document.title if fv.source_document else None
        item.document_url = fv.source_document.original_url if fv.source_document else None
        # Target entity info (for referenced entities like contacts -> person)
        if fv.target_entity:
            item.target_entity_name = fv.target_entity.name
            item.target_entity_slug = fv.target_entity.slug
            if fv.target_entity.entity_type:
                item.target_entity_type_slug = fv.target_entity.entity_type.slug
                item.target_entity_type_icon = fv.target_entity.entity_type.icon
                item.target_entity_type_color = fv.target_entity.entity_type.color
        items.append(item)

    return FacetValueListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
    )


@router.post("/values", response_model=FacetValueResponse, status_code=201)
async def create_facet_value(
    data: FacetValueCreate,
    request: Request,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
):
    """Create a new facet value. Requires Editor role."""
    # Verify entity exists
    entity = await session.get(Entity, data.entity_id)
    if not entity:
        raise NotFoundError("Entity", str(data.entity_id))

    # Verify facet type exists
    facet_type = await session.get(FacetType, data.facet_type_id)
    if not facet_type:
        raise NotFoundError("FacetType", str(data.facet_type_id))

    # Validate FacetType is applicable for this Entity's type
    if facet_type.applicable_entity_type_slugs:
        entity_type = await session.get(EntityType, entity.entity_type_id)
        entity_type_slug = entity_type.slug if entity_type else None
        if entity_type_slug and entity_type_slug not in facet_type.applicable_entity_type_slugs:
            raise ConflictError(
                "FacetType not applicable",
                detail=f"FacetType '{facet_type.name}' is not applicable for entity type '{entity_type_slug}'. "
                f"Applicable types: {', '.join(facet_type.applicable_entity_type_slugs)}",
            )

    # Use provided text_representation or generate from value
    text_repr = data.text_representation or build_text_representation(data.value)

    # Check for semantically similar FacetValues (AI-based)
    from app.utils.similarity import find_similar_facet_values

    similar_values = await find_similar_facet_values(
        session,
        entity_id=data.entity_id,
        facet_type_id=data.facet_type_id,
        text_representation=text_repr,
        threshold=0.85,
    )
    if similar_values:
        existing_fv, score, reason = similar_values[0]
        raise ConflictError(
            "Ähnlicher FacetValue existiert bereits",
            detail=f"{reason}. Bearbeiten Sie den bestehenden Wert statt einen neuen zu erstellen.",
        )

    # Validate target_entity_id if provided
    if data.target_entity_id:
        target_entity = await session.get(Entity, data.target_entity_id)
        if not target_entity:
            raise NotFoundError("Target Entity", str(data.target_entity_id))
        # Validate that target entity type is allowed for this facet type
        if facet_type.target_entity_type_slugs:
            target_entity_type = await session.get(EntityType, target_entity.entity_type_id)
            target_type_slug = target_entity_type.slug if target_entity_type else None
            if target_type_slug and target_type_slug not in facet_type.target_entity_type_slugs:
                raise ConflictError(
                    "Target entity type not allowed",
                    detail=f"Entity type '{target_type_slug}' is not allowed as target for facet type '{facet_type.name}'. "
                    f"Allowed types: {', '.join(facet_type.target_entity_type_slugs)}",
                )

    async with AuditContext(session, current_user, request) as audit:
        facet_value = FacetValue(
            entity_id=data.entity_id,
            facet_type_id=data.facet_type_id,
            category_id=data.category_id,
            value=data.value,
            text_representation=text_repr,
            event_date=data.event_date,
            valid_from=data.valid_from,
            valid_until=data.valid_until,
            source_type=FacetValueSourceType(data.source_type.value)
            if data.source_type
            else FacetValueSourceType.MANUAL,
            source_document_id=data.source_document_id,
            source_url=data.source_url,
            confidence_score=data.confidence_score,
            ai_model_used=data.ai_model_used,
            is_active=data.is_active,
            target_entity_id=data.target_entity_id,
        )
        session.add(facet_value)
        await session.flush()

        # Generate embedding for semantic similarity search
        from app.utils.similarity import generate_embedding

        embedding = await generate_embedding(text_repr)
        if embedding:
            facet_value.text_embedding = embedding

        audit.track_action(
            action=AuditAction.CREATE,
            entity_type="FacetValue",
            entity_id=facet_value.id,
            entity_name=f"{facet_type.name} for {entity.name}",
            changes={
                "entity_name": entity.name,
                "facet_type": facet_type.name,
                "text_representation": text_repr[:100] if text_repr else None,
                "source_type": data.source_type.value if data.source_type else "manual",
            },
        )

        await session.commit()
        await session.refresh(facet_value)

    item = FacetValueResponse.model_validate(facet_value)
    item.entity_name = entity.name
    item.facet_type_name = facet_type.name
    item.facet_type_slug = facet_type.slug

    return item


@router.get("/values/{facet_value_id}", response_model=FacetValueResponse)
async def get_facet_value(
    facet_value_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get a single facet value by ID."""
    # Eagerly load all relationships in a single query
    result = await session.execute(
        select(FacetValue)
        .options(
            selectinload(FacetValue.entity),
            selectinload(FacetValue.facet_type),
            selectinload(FacetValue.category),
            selectinload(FacetValue.source_document),
            selectinload(FacetValue.target_entity).selectinload(Entity.entity_type),
        )
        .where(FacetValue.id == facet_value_id)
    )
    fv = result.scalar()
    if not fv:
        raise NotFoundError("FacetValue", str(facet_value_id))

    response = FacetValueResponse.model_validate(fv)
    response.entity_name = fv.entity.name if fv.entity else None
    response.facet_type_name = fv.facet_type.name if fv.facet_type else None
    response.facet_type_slug = fv.facet_type.slug if fv.facet_type else None
    response.category_name = fv.category.name if fv.category else None
    response.document_title = fv.source_document.title if fv.source_document else None
    response.document_url = fv.source_document.original_url if fv.source_document else None
    # Target entity info (for referenced entities like contacts -> person)
    if fv.target_entity:
        response.target_entity_name = fv.target_entity.name
        response.target_entity_slug = fv.target_entity.slug
        if fv.target_entity.entity_type:
            response.target_entity_type_slug = fv.target_entity.entity_type.slug

    return response


@router.put("/values/{facet_value_id}", response_model=FacetValueResponse)
async def update_facet_value(
    facet_value_id: UUID,
    data: FacetValueUpdate,
    request: Request,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
):
    """Update a facet value."""
    fv = await session.get(FacetValue, facet_value_id)
    if not fv:
        raise NotFoundError("FacetValue", str(facet_value_id))

    async with AuditContext(session, current_user, request) as audit:
        # Update fields
        update_data = data.model_dump(exclude_unset=True)

        # Rebuild text representation if value changes
        if "value" in update_data:
            update_data["text_representation"] = build_text_representation(update_data["value"])

        # If text_representation changes, regenerate embedding
        if "text_representation" in update_data or "value" in update_data:
            from app.utils.similarity import generate_embedding

            text_repr = update_data.get("text_representation") or fv.text_representation
            embedding = await generate_embedding(text_repr)
            if embedding:
                update_data["text_embedding"] = embedding

        for field, value in update_data.items():
            setattr(fv, field, value)

        audit.track_action(
            action=AuditAction.UPDATE,
            entity_type="FacetValue",
            entity_id=fv.id,
            entity_name=fv.text_representation[:50] if fv.text_representation else str(fv.id),
            changes={"updated_fields": list(update_data.keys())},
        )

        await session.commit()
        await session.refresh(fv)

    # Enrich response with related entity info - eagerly load all relationships
    result = await session.execute(
        select(FacetValue)
        .options(
            selectinload(FacetValue.entity),
            selectinload(FacetValue.facet_type),
            selectinload(FacetValue.category),
            selectinload(FacetValue.source_document),
            selectinload(FacetValue.target_entity).selectinload(Entity.entity_type),
        )
        .where(FacetValue.id == fv.id)
    )
    fv = result.scalar()

    response = FacetValueResponse.model_validate(fv)
    response.entity_name = fv.entity.name if fv.entity else None
    response.facet_type_name = fv.facet_type.name if fv.facet_type else None
    response.facet_type_slug = fv.facet_type.slug if fv.facet_type else None
    response.category_name = fv.category.name if fv.category else None
    response.document_title = fv.source_document.title if fv.source_document else None
    response.document_url = fv.source_document.original_url if fv.source_document else None
    # Target entity info
    if fv.target_entity:
        response.target_entity_name = fv.target_entity.name
        response.target_entity_slug = fv.target_entity.slug
        if fv.target_entity.entity_type:
            response.target_entity_type_slug = fv.target_entity.entity_type.slug

    return response


@router.put("/values/{facet_value_id}/verify", response_model=FacetValueResponse)
async def verify_facet_value(
    facet_value_id: UUID,
    verified: bool = Query(default=True),
    verified_by: str | None = Query(default=None),
    corrections: dict[str, Any] | None = None,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
):
    """Verify a facet value and optionally apply corrections."""
    fv = await session.get(FacetValue, facet_value_id)
    if not fv:
        raise NotFoundError("FacetValue", str(facet_value_id))

    fv.human_verified = verified
    fv.verified_by = verified_by
    fv.verified_at = datetime.now(UTC)

    if corrections:
        fv.human_corrections = corrections

    await session.commit()
    await session.refresh(fv)

    # Enrich response with related entity info - eagerly load all relationships
    result = await session.execute(
        select(FacetValue)
        .options(
            selectinload(FacetValue.entity),
            selectinload(FacetValue.facet_type),
            selectinload(FacetValue.category),
            selectinload(FacetValue.source_document),
        )
        .where(FacetValue.id == fv.id)
    )
    fv = result.scalar()

    response = FacetValueResponse.model_validate(fv)
    response.entity_name = fv.entity.name if fv.entity else None
    response.facet_type_name = fv.facet_type.name if fv.facet_type else None
    response.facet_type_slug = fv.facet_type.slug if fv.facet_type else None
    response.category_name = fv.category.name if fv.category else None
    response.document_title = fv.source_document.title if fv.source_document else None
    response.document_url = fv.source_document.original_url if fv.source_document else None

    return response


@router.delete("/values/{facet_value_id}", response_model=MessageResponse)
async def delete_facet_value(
    facet_value_id: UUID,
    request: Request,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
):
    """Delete a facet value. Requires Editor role."""
    fv = await session.get(FacetValue, facet_value_id)
    if not fv:
        raise NotFoundError("FacetValue", str(facet_value_id))

    fv_name = fv.text_representation[:50] if fv.text_representation else str(facet_value_id)

    async with AuditContext(session, current_user, request) as audit:
        audit.track_action(
            action=AuditAction.DELETE,
            entity_type="FacetValue",
            entity_id=facet_value_id,
            entity_name=fv_name,
            changes={"deleted": True},
        )

        await session.delete(fv)
        await session.commit()

    return MessageResponse(message="Facet value deleted successfully")
