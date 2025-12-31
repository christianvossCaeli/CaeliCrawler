"""Admin API for FacetType management and review."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.database import get_session
from app.models import FacetType, FacetValue

router = APIRouter(prefix="/facet-types", tags=["admin-facet-types"])


# =============================================================================
# Schemas
# =============================================================================


class FacetTypeListItem(BaseModel):
    """FacetType list item for admin view."""

    id: UUID
    slug: str
    name: str
    name_plural: str
    description: str | None = None
    value_type: str
    icon: str
    color: str
    is_active: bool
    is_system: bool
    needs_review: bool
    facet_value_count: int = 0
    created_at: str

    class Config:
        from_attributes = True


class FacetTypeDetail(FacetTypeListItem):
    """Detailed FacetType for admin view."""

    value_schema: dict | None = None
    applicable_entity_type_slugs: list[str] = []
    ai_extraction_enabled: bool = True
    ai_extraction_prompt: str | None = None
    allows_entity_reference: bool = False
    target_entity_type_slugs: list[str] = []
    auto_create_entity: bool = False
    aggregation_method: str = "dedupe"
    deduplication_fields: list[str] = []
    is_time_based: bool = False
    time_field_path: str | None = None
    default_time_filter: str = "all"
    display_order: int = 0


class FacetTypeUpdate(BaseModel):
    """Schema for updating a FacetType."""

    name: str | None = None
    name_plural: str | None = None
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    is_active: bool | None = None
    needs_review: bool | None = None
    value_schema: dict | None = None
    applicable_entity_type_slugs: list[str] | None = None
    ai_extraction_enabled: bool | None = None
    ai_extraction_prompt: str | None = None
    allows_entity_reference: bool | None = None
    target_entity_type_slugs: list[str] | None = None
    auto_create_entity: bool | None = None
    display_order: int | None = None


class FacetTypeReviewAction(BaseModel):
    """Action for reviewing a FacetType."""

    action: str = Field(..., pattern="^(approve|reject|merge)$")
    merge_into_slug: str | None = None  # For merge action


class FacetTypeBulkReviewRequest(BaseModel):
    """Bulk review request."""

    facet_type_ids: list[UUID]
    action: str = Field(..., pattern="^(approve|reject)$")


class FacetTypeStats(BaseModel):
    """Statistics about FacetTypes."""

    total: int
    active: int
    needs_review: int
    system: int
    auto_created: int
    with_values: int


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/stats", response_model=FacetTypeStats)
async def get_facet_type_stats(
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_admin),
):
    """Get statistics about FacetTypes."""

    # Total count
    total = (await session.execute(
        select(func.count()).select_from(FacetType)
    )).scalar()

    # Active count
    active = (await session.execute(
        select(func.count()).select_from(FacetType).where(FacetType.is_active.is_(True))
    )).scalar()

    # Needs review count
    needs_review = (await session.execute(
        select(func.count()).select_from(FacetType).where(FacetType.needs_review.is_(True))
    )).scalar()

    # System count
    system = (await session.execute(
        select(func.count()).select_from(FacetType).where(FacetType.is_system.is_(True))
    )).scalar()

    # Auto-created (not system, not reviewed)
    auto_created = (await session.execute(
        select(func.count()).select_from(FacetType).where(
            FacetType.is_system.is_(False),
        )
    )).scalar()

    # With values
    with_values_subq = (
        select(FacetValue.facet_type_id)
        .distinct()
        .subquery()
    )
    with_values = (await session.execute(
        select(func.count()).select_from(FacetType).where(
            FacetType.id.in_(select(with_values_subq.c.facet_type_id))
        )
    )).scalar()

    return FacetTypeStats(
        total=total or 0,
        active=active or 0,
        needs_review=needs_review or 0,
        system=system or 0,
        auto_created=auto_created or 0,
        with_values=with_values or 0,
    )


@router.get("", response_model=list[FacetTypeListItem])
async def list_facet_types(
    needs_review: bool | None = Query(None, description="Filter by needs_review status"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    is_system: bool | None = Query(None, description="Filter by system status"),
    search: str | None = Query(None, description="Search in name, slug, description"),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_admin),
):
    """List all FacetTypes with optional filters."""

    # Base query with value count
    value_count_subq = (
        select(
            FacetValue.facet_type_id,
            func.count(FacetValue.id).label("count")
        )
        .group_by(FacetValue.facet_type_id)
        .subquery()
    )

    stmt = (
        select(
            FacetType,
            func.coalesce(value_count_subq.c.count, 0).label("value_count")
        )
        .outerjoin(value_count_subq, FacetType.id == value_count_subq.c.facet_type_id)
    )

    # Apply filters
    if needs_review is not None:
        stmt = stmt.where(FacetType.needs_review == needs_review)
    if is_active is not None:
        stmt = stmt.where(FacetType.is_active == is_active)
    if is_system is not None:
        stmt = stmt.where(FacetType.is_system == is_system)
    if search:
        search_filter = f"%{search}%"
        stmt = stmt.where(
            (FacetType.name.ilike(search_filter)) |
            (FacetType.slug.ilike(search_filter)) |
            (FacetType.description.ilike(search_filter))
        )

    # Order by needs_review first, then by name
    stmt = stmt.order_by(
        FacetType.needs_review.desc(),
        FacetType.display_order,
        FacetType.name
    )

    stmt = stmt.offset(offset).limit(limit)

    result = await session.execute(stmt)
    rows = result.all()

    return [
        FacetTypeListItem(
            id=ft.id,
            slug=ft.slug,
            name=ft.name,
            name_plural=ft.name_plural,
            description=ft.description,
            value_type=ft.value_type,
            icon=ft.icon,
            color=ft.color,
            is_active=ft.is_active,
            is_system=ft.is_system,
            needs_review=ft.needs_review,
            facet_value_count=value_count,
            created_at=ft.created_at.isoformat(),
        )
        for ft, value_count in rows
    ]


@router.get("/needs-review", response_model=list[FacetTypeListItem])
async def list_facet_types_needing_review(
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_admin),
):
    """List all FacetTypes that need admin review."""

    value_count_subq = (
        select(
            FacetValue.facet_type_id,
            func.count(FacetValue.id).label("count")
        )
        .group_by(FacetValue.facet_type_id)
        .subquery()
    )

    stmt = (
        select(
            FacetType,
            func.coalesce(value_count_subq.c.count, 0).label("value_count")
        )
        .outerjoin(value_count_subq, FacetType.id == value_count_subq.c.facet_type_id)
        .where(FacetType.needs_review.is_(True))
        .order_by(FacetType.created_at.desc())
    )

    result = await session.execute(stmt)
    rows = result.all()

    return [
        FacetTypeListItem(
            id=ft.id,
            slug=ft.slug,
            name=ft.name,
            name_plural=ft.name_plural,
            description=ft.description,
            value_type=ft.value_type,
            icon=ft.icon,
            color=ft.color,
            is_active=ft.is_active,
            is_system=ft.is_system,
            needs_review=ft.needs_review,
            facet_value_count=value_count,
            created_at=ft.created_at.isoformat(),
        )
        for ft, value_count in rows
    ]


@router.get("/{facet_type_id}", response_model=FacetTypeDetail)
async def get_facet_type(
    facet_type_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_admin),
):
    """Get detailed information about a FacetType."""

    value_count_subq = (
        select(func.count(FacetValue.id))
        .where(FacetValue.facet_type_id == facet_type_id)
        .scalar_subquery()
    )

    stmt = select(FacetType, value_count_subq.label("value_count")).where(
        FacetType.id == facet_type_id
    )

    result = await session.execute(stmt)
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="FacetType not found")

    ft, value_count = row

    return FacetTypeDetail(
        id=ft.id,
        slug=ft.slug,
        name=ft.name,
        name_plural=ft.name_plural,
        description=ft.description,
        value_type=ft.value_type,
        value_schema=ft.value_schema,
        icon=ft.icon,
        color=ft.color,
        is_active=ft.is_active,
        is_system=ft.is_system,
        needs_review=ft.needs_review,
        applicable_entity_type_slugs=ft.applicable_entity_type_slugs or [],
        ai_extraction_enabled=ft.ai_extraction_enabled,
        ai_extraction_prompt=ft.ai_extraction_prompt,
        allows_entity_reference=ft.allows_entity_reference,
        target_entity_type_slugs=ft.target_entity_type_slugs or [],
        auto_create_entity=ft.auto_create_entity,
        aggregation_method=ft.aggregation_method,
        deduplication_fields=ft.deduplication_fields or [],
        is_time_based=ft.is_time_based,
        time_field_path=ft.time_field_path,
        default_time_filter=ft.default_time_filter,
        display_order=ft.display_order,
        facet_value_count=value_count or 0,
        created_at=ft.created_at.isoformat(),
    )


@router.patch("/{facet_type_id}", response_model=FacetTypeDetail)
async def update_facet_type(
    facet_type_id: UUID,
    data: FacetTypeUpdate,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_admin),
):
    """Update a FacetType."""

    ft = await session.get(FacetType, facet_type_id)
    if not ft:
        raise HTTPException(status_code=404, detail="FacetType not found")

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(ft, key, value)

    await session.commit()
    await session.refresh(ft)

    # Get value count
    value_count = (await session.execute(
        select(func.count(FacetValue.id)).where(FacetValue.facet_type_id == facet_type_id)
    )).scalar() or 0

    return FacetTypeDetail(
        id=ft.id,
        slug=ft.slug,
        name=ft.name,
        name_plural=ft.name_plural,
        description=ft.description,
        value_type=ft.value_type,
        value_schema=ft.value_schema,
        icon=ft.icon,
        color=ft.color,
        is_active=ft.is_active,
        is_system=ft.is_system,
        needs_review=ft.needs_review,
        applicable_entity_type_slugs=ft.applicable_entity_type_slugs or [],
        ai_extraction_enabled=ft.ai_extraction_enabled,
        ai_extraction_prompt=ft.ai_extraction_prompt,
        allows_entity_reference=ft.allows_entity_reference,
        target_entity_type_slugs=ft.target_entity_type_slugs or [],
        auto_create_entity=ft.auto_create_entity,
        aggregation_method=ft.aggregation_method,
        deduplication_fields=ft.deduplication_fields or [],
        is_time_based=ft.is_time_based,
        time_field_path=ft.time_field_path,
        default_time_filter=ft.default_time_filter,
        display_order=ft.display_order,
        facet_value_count=value_count,
        created_at=ft.created_at.isoformat(),
    )


@router.post("/{facet_type_id}/review", response_model=FacetTypeDetail)
async def review_facet_type(
    facet_type_id: UUID,
    review: FacetTypeReviewAction,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_admin),
):
    """Review a FacetType (approve, reject, or merge)."""

    ft = await session.get(FacetType, facet_type_id)
    if not ft:
        raise HTTPException(status_code=404, detail="FacetType not found")

    if review.action == "approve":
        # Approve: Clear needs_review flag
        ft.needs_review = False
        await session.commit()

    elif review.action == "reject":
        # Reject: Deactivate and delete associated values
        ft.is_active = False
        ft.needs_review = False

        # Delete associated FacetValues
        await session.execute(
            FacetValue.__table__.delete().where(FacetValue.facet_type_id == facet_type_id)
        )
        await session.commit()

    elif review.action == "merge":
        # Merge into another FacetType
        if not review.merge_into_slug:
            raise HTTPException(
                status_code=400,
                detail="merge_into_slug is required for merge action"
            )

        # Find target FacetType
        target_result = await session.execute(
            select(FacetType).where(FacetType.slug == review.merge_into_slug)
        )
        target_ft = target_result.scalar_one_or_none()

        if not target_ft:
            raise HTTPException(
                status_code=404,
                detail=f"Target FacetType '{review.merge_into_slug}' not found"
            )

        # Update all FacetValues to point to target
        await session.execute(
            update(FacetValue)
            .where(FacetValue.facet_type_id == facet_type_id)
            .values(facet_type_id=target_ft.id)
        )

        # Deactivate source FacetType
        ft.is_active = False
        ft.needs_review = False
        await session.commit()

    await session.refresh(ft)

    # Get value count
    value_count = (await session.execute(
        select(func.count(FacetValue.id)).where(FacetValue.facet_type_id == facet_type_id)
    )).scalar() or 0

    return FacetTypeDetail(
        id=ft.id,
        slug=ft.slug,
        name=ft.name,
        name_plural=ft.name_plural,
        description=ft.description,
        value_type=ft.value_type,
        value_schema=ft.value_schema,
        icon=ft.icon,
        color=ft.color,
        is_active=ft.is_active,
        is_system=ft.is_system,
        needs_review=ft.needs_review,
        applicable_entity_type_slugs=ft.applicable_entity_type_slugs or [],
        ai_extraction_enabled=ft.ai_extraction_enabled,
        ai_extraction_prompt=ft.ai_extraction_prompt,
        allows_entity_reference=ft.allows_entity_reference,
        target_entity_type_slugs=ft.target_entity_type_slugs or [],
        auto_create_entity=ft.auto_create_entity,
        aggregation_method=ft.aggregation_method,
        deduplication_fields=ft.deduplication_fields or [],
        is_time_based=ft.is_time_based,
        time_field_path=ft.time_field_path,
        default_time_filter=ft.default_time_filter,
        display_order=ft.display_order,
        facet_value_count=value_count,
        created_at=ft.created_at.isoformat(),
    )


@router.post("/bulk-review")
async def bulk_review_facet_types(
    request: FacetTypeBulkReviewRequest,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_admin),
):
    """Bulk approve or reject multiple FacetTypes."""

    if request.action == "approve":
        await session.execute(
            update(FacetType)
            .where(FacetType.id.in_(request.facet_type_ids))
            .values(needs_review=False)
        )
    elif request.action == "reject":
        # Delete values first
        await session.execute(
            FacetValue.__table__.delete().where(
                FacetValue.facet_type_id.in_(request.facet_type_ids)
            )
        )
        # Deactivate FacetTypes
        await session.execute(
            update(FacetType)
            .where(FacetType.id.in_(request.facet_type_ids))
            .values(is_active=False, needs_review=False)
        )

    await session.commit()

    return {"status": "ok", "action": request.action, "count": len(request.facet_type_ids)}
