"""API endpoints for Relation Type and Entity Relation management."""

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditContext
from app.core.deps import get_current_user_optional, require_editor
from app.core.exceptions import ConflictError, NotFoundError
from app.database import get_session
from app.models import (
    Entity,
    EntityRelation,
    EntityType,
    RelationType,
)
from app.models.audit_log import AuditAction
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.relation import (
    EntityRelationCreate,
    EntityRelationListResponse,
    EntityRelationResponse,
    EntityRelationsGraph,
    EntityRelationUpdate,
    RelationTypeCreate,
    RelationTypeListResponse,
    RelationTypeResponse,
    RelationTypeUpdate,
    generate_slug,
)

router = APIRouter()


# ============================================================================
# RelationType Endpoints
# ============================================================================


@router.get("/types", response_model=RelationTypeListResponse)
async def list_relation_types(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 50,
    is_active: Annotated[bool | None, Query(description="Filter by active status")] = None,
    source_entity_type_id: Annotated[UUID | None, Query(description="Filter by source entity type")] = None,
    target_entity_type_id: Annotated[UUID | None, Query(description="Filter by target entity type")] = None,
    search: Annotated[str | None, Query(description="Search in name or slug")] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user_optional),
) -> RelationTypeListResponse:
    """List all relation types with pagination."""
    query = select(RelationType)

    if is_active is not None:
        query = query.where(RelationType.is_active.is_(is_active))
    if source_entity_type_id:
        query = query.where(RelationType.source_entity_type_id == source_entity_type_id)
    if target_entity_type_id:
        query = query.where(RelationType.target_entity_type_id == target_entity_type_id)
    if search:
        # Escape SQL wildcards to prevent injection
        safe_search = search.replace('%', '\\%').replace('_', '\\_')
        query = query.where(
            RelationType.name.ilike(f"%{safe_search}%", escape='\\') |
            RelationType.slug.ilike(f"%{safe_search}%", escape='\\')
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Paginate
    query = query.order_by(RelationType.display_order, RelationType.name).offset((page - 1) * per_page).limit(per_page)
    result = await session.execute(query)
    relation_types = result.scalars().all()

    if not relation_types:
        return RelationTypeListResponse(
            items=[],
            total=total,
            page=page,
            per_page=per_page,
            pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
        )

    # Collect IDs for batch queries
    relation_type_ids = [rt.id for rt in relation_types]
    entity_type_ids = list(set(
        [rt.source_entity_type_id for rt in relation_types] +
        [rt.target_entity_type_id for rt in relation_types]
    ))

    # Batch load EntityTypes (1 query instead of 2N)
    entity_types_result = await session.execute(
        select(EntityType).where(EntityType.id.in_(entity_type_ids))
    )
    entity_types_map = {et.id: et for et in entity_types_result.scalars().all()}

    # Batch count relations (1 query instead of N)
    relation_counts_result = await session.execute(
        select(EntityRelation.relation_type_id, func.count(EntityRelation.id))
        .where(EntityRelation.relation_type_id.in_(relation_type_ids))
        .group_by(EntityRelation.relation_type_id)
    )
    relation_counts_map = dict(relation_counts_result.fetchall())

    # Build response items using pre-fetched data
    items = []
    for rt in relation_types:
        source_et = entity_types_map.get(rt.source_entity_type_id)
        target_et = entity_types_map.get(rt.target_entity_type_id)

        item = RelationTypeResponse.model_validate(rt)
        item.source_entity_type_name = source_et.name if source_et else None
        item.source_entity_type_slug = source_et.slug if source_et else None
        item.target_entity_type_name = target_et.name if target_et else None
        item.target_entity_type_slug = target_et.slug if target_et else None
        item.relation_count = relation_counts_map.get(rt.id, 0)
        items.append(item)

    return RelationTypeListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
    )


@router.post("/types", response_model=RelationTypeResponse, status_code=201)
async def create_relation_type(
    data: RelationTypeCreate,
    request: Request,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
) -> RelationTypeResponse:
    """Create a new relation type. Requires Editor role."""
    # Verify entity types exist
    source_et = await session.get(EntityType, data.source_entity_type_id)
    if not source_et:
        raise NotFoundError("Source EntityType", str(data.source_entity_type_id))

    target_et = await session.get(EntityType, data.target_entity_type_id)
    if not target_et:
        raise NotFoundError("Target EntityType", str(data.target_entity_type_id))

    # Generate slug if not provided
    slug = data.slug or generate_slug(data.name)

    # Check for exact duplicate
    existing = await session.execute(
        select(RelationType).where(
            (RelationType.name == data.name) | (RelationType.slug == slug)
        )
    )
    if existing.scalar():
        raise ConflictError(
            "Relation Type already exists",
            detail=f"A relation type with name '{data.name}' or slug '{slug}' already exists",
        )

    # Check for semantically similar RelationTypes (AI-based)
    from app.utils.similarity import find_similar_relation_types
    similar_matches = await find_similar_relation_types(
        session,
        name=data.name,
        name_inverse=data.name_inverse,
        source_entity_type_id=data.source_entity_type_id,
        target_entity_type_id=data.target_entity_type_id,
    )
    if similar_matches:
        match, score, reason = similar_matches[0]
        raise ConflictError(
            "Semantisch ähnlicher RelationType existiert bereits",
            detail=f"'{match.name}' ({match.slug}) - {reason}. Verwenden Sie diesen statt einen neuen zu erstellen.",
        )

    async with AuditContext(session, current_user, request) as audit:
        relation_type = RelationType(
            name=data.name,
            slug=slug,
            name_inverse=data.name_inverse,
            description=data.description,
            source_entity_type_id=data.source_entity_type_id,
            target_entity_type_id=data.target_entity_type_id,
            cardinality=data.cardinality,
            attribute_schema=data.attribute_schema,
            icon=data.icon,
            color=data.color,
            display_order=data.display_order,
            is_active=data.is_active,
            is_system=False,
        )
        session.add(relation_type)
        await session.flush()

        # Generate embeddings for semantic similarity search
        from app.utils.similarity import generate_embedding
        name_embedding = await generate_embedding(data.name)
        if name_embedding:
            relation_type.name_embedding = name_embedding
        if data.name_inverse:
            name_inverse_embedding = await generate_embedding(data.name_inverse)
            if name_inverse_embedding:
                relation_type.name_inverse_embedding = name_inverse_embedding

        audit.track_action(
            action=AuditAction.CREATE,
            entity_type="RelationType",
            entity_id=relation_type.id,
            entity_name=relation_type.name,
            changes={
                "name": relation_type.name,
                "slug": slug,
                "source_entity_type": source_et.name,
                "target_entity_type": target_et.name,
                "cardinality": data.cardinality,
            },
        )

        await session.commit()
        await session.refresh(relation_type)

    item = RelationTypeResponse.model_validate(relation_type)
    item.source_entity_type_name = source_et.name
    item.source_entity_type_slug = source_et.slug
    item.target_entity_type_name = target_et.name
    item.target_entity_type_slug = target_et.slug

    return item


@router.get("/types/{relation_type_id}", response_model=RelationTypeResponse)
async def get_relation_type(
    relation_type_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user_optional),
) -> RelationTypeResponse:
    """Get a single relation type by ID."""
    rt = await session.get(RelationType, relation_type_id)
    if not rt:
        raise NotFoundError("RelationType", str(relation_type_id))

    # Batch load both EntityTypes in a single query
    entity_type_ids = [rt.source_entity_type_id, rt.target_entity_type_id]
    entity_types_result = await session.execute(
        select(EntityType).where(EntityType.id.in_(entity_type_ids))
    )
    entity_types_map = {et.id: et for et in entity_types_result.scalars().all()}

    source_et = entity_types_map.get(rt.source_entity_type_id)
    target_et = entity_types_map.get(rt.target_entity_type_id)

    relation_count = (await session.execute(
        select(func.count()).where(EntityRelation.relation_type_id == rt.id)
    )).scalar()

    response = RelationTypeResponse.model_validate(rt)
    response.source_entity_type_name = source_et.name if source_et else None
    response.source_entity_type_slug = source_et.slug if source_et else None
    response.target_entity_type_name = target_et.name if target_et else None
    response.target_entity_type_slug = target_et.slug if target_et else None
    response.relation_count = relation_count

    return response


@router.get("/types/by-slug/{slug}", response_model=RelationTypeResponse)
async def get_relation_type_by_slug(
    slug: str,
    session: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user_optional),
) -> RelationTypeResponse:
    """Get a single relation type by slug."""
    result = await session.execute(
        select(RelationType).where(RelationType.slug == slug)
    )
    rt = result.scalar()
    if not rt:
        raise NotFoundError("RelationType", slug)

    # Batch load both EntityTypes in a single query
    entity_type_ids = [rt.source_entity_type_id, rt.target_entity_type_id]
    entity_types_result = await session.execute(
        select(EntityType).where(EntityType.id.in_(entity_type_ids))
    )
    entity_types_map = {et.id: et for et in entity_types_result.scalars().all()}

    source_et = entity_types_map.get(rt.source_entity_type_id)
    target_et = entity_types_map.get(rt.target_entity_type_id)

    relation_count = (await session.execute(
        select(func.count()).where(EntityRelation.relation_type_id == rt.id)
    )).scalar()

    response = RelationTypeResponse.model_validate(rt)
    response.source_entity_type_name = source_et.name if source_et else None
    response.source_entity_type_slug = source_et.slug if source_et else None
    response.target_entity_type_name = target_et.name if target_et else None
    response.target_entity_type_slug = target_et.slug if target_et else None
    response.relation_count = relation_count

    return response


@router.put("/types/{relation_type_id}", response_model=RelationTypeResponse)
async def update_relation_type(
    relation_type_id: UUID,
    data: RelationTypeUpdate,
    request: Request,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
) -> RelationTypeResponse:
    """Update a relation type."""
    rt = await session.get(RelationType, relation_type_id)
    if not rt:
        raise NotFoundError("RelationType", str(relation_type_id))

    old_data = {"name": rt.name, "slug": rt.slug, "is_active": rt.is_active}

    async with AuditContext(session, current_user, request) as audit:
        # Update fields
        update_data = data.model_dump(exclude_unset=True)

        # If name changes, regenerate embedding
        if "name" in update_data:
            from app.utils.similarity import generate_embedding
            embedding = await generate_embedding(update_data["name"])
            if embedding:
                update_data["name_embedding"] = embedding

        # If name_inverse changes, regenerate embedding
        if "name_inverse" in update_data:
            from app.utils.similarity import generate_embedding
            embedding = await generate_embedding(update_data["name_inverse"])
            if embedding:
                update_data["name_inverse_embedding"] = embedding

        for field, value in update_data.items():
            setattr(rt, field, value)

        new_data = {"name": rt.name, "slug": rt.slug, "is_active": rt.is_active}
        audit.track_update(rt, old_data, new_data)

        await session.commit()
        await session.refresh(rt)

    return RelationTypeResponse.model_validate(rt)


@router.delete("/types/{relation_type_id}", response_model=MessageResponse)
async def delete_relation_type(
    relation_type_id: UUID,
    request: Request,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """Delete a relation type. Requires Editor role."""
    rt = await session.get(RelationType, relation_type_id)
    if not rt:
        raise NotFoundError("RelationType", str(relation_type_id))

    if rt.is_system:
        raise ConflictError(
            "Cannot delete system relation type",
            detail=f"Relation type '{rt.name}' is a system type and cannot be deleted",
        )

    # Check for existing relations
    relation_count = (await session.execute(
        select(func.count()).where(EntityRelation.relation_type_id == rt.id)
    )).scalar()

    if relation_count > 0:
        raise ConflictError(
            "Cannot delete relation type with existing relations",
            detail=f"Relation type '{rt.name}' has {relation_count} relations. Delete them first.",
        )

    rt_name = rt.name

    async with AuditContext(session, current_user, request) as audit:
        audit.track_action(
            action=AuditAction.DELETE,
            entity_type="RelationType",
            entity_id=relation_type_id,
            entity_name=rt_name,
            changes={"deleted": True, "name": rt_name, "slug": rt.slug},
        )
        await session.delete(rt)
        await session.commit()

    return MessageResponse(message=f"Relation type '{rt_name}' deleted successfully")


# ============================================================================
# EntityRelation Endpoints
# ============================================================================


@router.get("", response_model=EntityRelationListResponse)
async def list_entity_relations(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    per_page: Annotated[int, Query(ge=1, le=200, description="Items per page")] = 50,
    relation_type_id: Annotated[UUID | None, Query(description="Filter by relation type ID")] = None,
    relation_type_slug: Annotated[str | None, Query(description="Filter by relation type slug")] = None,
    source_entity_id: Annotated[UUID | None, Query(description="Filter by source entity")] = None,
    target_entity_id: Annotated[UUID | None, Query(description="Filter by target entity")] = None,
    entity_id: Annotated[UUID | None, Query(description="Either source or target")] = None,
    min_confidence: Annotated[float, Query(ge=0, le=1, description="Minimum confidence score")] = 0.0,
    human_verified: Annotated[bool | None, Query(description="Filter by verification status")] = None,
    is_active: Annotated[bool | None, Query(description="Filter by active status")] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user_optional),
) -> EntityRelationListResponse:
    """List entity relations with filters."""
    query = select(EntityRelation)

    if relation_type_id:
        query = query.where(EntityRelation.relation_type_id == relation_type_id)
    elif relation_type_slug:
        subq = select(RelationType.id).where(RelationType.slug == relation_type_slug)
        query = query.where(EntityRelation.relation_type_id.in_(subq))

    if source_entity_id:
        query = query.where(EntityRelation.source_entity_id == source_entity_id)
    if target_entity_id:
        query = query.where(EntityRelation.target_entity_id == target_entity_id)
    if entity_id:
        query = query.where(
            or_(
                EntityRelation.source_entity_id == entity_id,
                EntityRelation.target_entity_id == entity_id
            )
        )

    if min_confidence > 0:
        query = query.where(EntityRelation.confidence_score >= min_confidence)
    if human_verified is not None:
        query = query.where(EntityRelation.human_verified.is_(human_verified))
    if is_active is not None:
        query = query.where(EntityRelation.is_active.is_(is_active))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Paginate
    query = query.order_by(EntityRelation.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await session.execute(query)
    relations = result.scalars().all()

    # Batch load related data to avoid N+1 queries
    if not relations:
        return EntityRelationListResponse(
            items=[],
            total=total,
            page=page,
            per_page=per_page,
            pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
        )

    # Collect all IDs for batch loading
    relation_type_ids = list({rel.relation_type_id for rel in relations})
    entity_ids = list(set(
        [rel.source_entity_id for rel in relations] +
        [rel.target_entity_id for rel in relations]
    ))

    # Batch load RelationTypes (1 query instead of N)
    rt_result = await session.execute(
        select(RelationType).where(RelationType.id.in_(relation_type_ids))
    )
    relation_types_map = {rt.id: rt for rt in rt_result.scalars().all()}

    # Batch load Entities (1 query instead of 2N)
    entities_result = await session.execute(
        select(Entity).where(Entity.id.in_(entity_ids))
    )
    entities_map = {e.id: e for e in entities_result.scalars().all()}

    # Collect EntityType IDs from loaded entities
    entity_type_ids = list({
        e.entity_type_id for e in entities_map.values() if e.entity_type_id
    })

    # Batch load EntityTypes (1 query instead of 2N)
    et_result = await session.execute(
        select(EntityType).where(EntityType.id.in_(entity_type_ids))
    )
    entity_types_map = {et.id: et for et in et_result.scalars().all()}

    # Build response items using pre-fetched data
    items = []
    for rel in relations:
        rt = relation_types_map.get(rel.relation_type_id)
        source = entities_map.get(rel.source_entity_id)
        target = entities_map.get(rel.target_entity_id)

        source_et = entity_types_map.get(source.entity_type_id) if source else None
        target_et = entity_types_map.get(target.entity_type_id) if target else None

        item = EntityRelationResponse.model_validate(rel)
        item.relation_type_slug = rt.slug if rt else None
        item.relation_type_name = rt.name if rt else None
        item.source_entity_name = source.name if source else None
        item.source_entity_slug = source.slug if source else None
        item.source_entity_type_slug = source_et.slug if source_et else None
        item.target_entity_name = target.name if target else None
        item.target_entity_slug = target.slug if target else None
        item.target_entity_type_slug = target_et.slug if target_et else None
        items.append(item)

    return EntityRelationListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
    )


@router.post("", response_model=EntityRelationResponse, status_code=201)
async def create_entity_relation(
    data: EntityRelationCreate,
    request: Request,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
) -> EntityRelationResponse:
    """Create a new entity relation. Requires Editor role."""
    # Verify entities exist
    source = await session.get(Entity, data.source_entity_id)
    if not source:
        raise NotFoundError("Source Entity", str(data.source_entity_id))

    target = await session.get(Entity, data.target_entity_id)
    if not target:
        raise NotFoundError("Target Entity", str(data.target_entity_id))

    # Verify relation type exists
    rt = await session.get(RelationType, data.relation_type_id)
    if not rt:
        raise NotFoundError("RelationType", str(data.relation_type_id))

    # Validate entity types match relation type constraints
    if source.entity_type_id != rt.source_entity_type_id:
        source_et = await session.get(EntityType, rt.source_entity_type_id)
        raise ConflictError(
            "Invalid source entity type",
            detail=f"Relation type '{rt.name}' requires source entity of type '{source_et.name if source_et else 'Unknown'}'",
        )

    if target.entity_type_id != rt.target_entity_type_id:
        target_et = await session.get(EntityType, rt.target_entity_type_id)
        raise ConflictError(
            "Invalid target entity type",
            detail=f"Relation type '{rt.name}' requires target entity of type '{target_et.name if target_et else 'Unknown'}'",
        )

    # Check for duplicate
    existing = await session.execute(
        select(EntityRelation).where(
            and_(
                EntityRelation.relation_type_id == data.relation_type_id,
                EntityRelation.source_entity_id == data.source_entity_id,
                EntityRelation.target_entity_id == data.target_entity_id,
            )
        )
    )
    if existing.scalar():
        raise ConflictError(
            "Relation already exists",
            detail="A relation of this type already exists between these entities",
        )

    async with AuditContext(session, current_user, request) as audit:
        relation = EntityRelation(
            relation_type_id=data.relation_type_id,
            source_entity_id=data.source_entity_id,
            target_entity_id=data.target_entity_id,
            attributes=data.attributes or {},
            valid_from=data.valid_from,
            valid_until=data.valid_until,
            source_document_id=data.source_document_id,
            source_url=data.source_url,
            confidence_score=data.confidence_score,
            ai_model_used=data.ai_model_used,
            is_active=data.is_active,
        )
        session.add(relation)
        await session.flush()

        audit.track_action(
            action=AuditAction.CREATE,
            entity_type="EntityRelation",
            entity_id=relation.id,
            entity_name=f"{source.name} -> {target.name}",
            changes={
                "relation_type": rt.name,
                "source_entity": source.name,
                "target_entity": target.name,
            },
        )

        await session.commit()
        await session.refresh(relation)

    # Batch load entity types
    entity_type_ids = []
    if source.entity_type_id:
        entity_type_ids.append(source.entity_type_id)
    if target.entity_type_id:
        entity_type_ids.append(target.entity_type_id)

    entity_types_map = {}
    if entity_type_ids:
        entity_types_result = await session.execute(
            select(EntityType).where(EntityType.id.in_(entity_type_ids))
        )
        entity_types_map = {et.id: et for et in entity_types_result.scalars().all()}

    source_et = entity_types_map.get(source.entity_type_id) if source.entity_type_id else None
    target_et = entity_types_map.get(target.entity_type_id) if target.entity_type_id else None

    item = EntityRelationResponse.model_validate(relation)
    item.relation_type_slug = rt.slug
    item.relation_type_name = rt.name
    item.source_entity_name = source.name
    item.source_entity_slug = source.slug
    item.source_entity_type_slug = source_et.slug if source_et else None
    item.target_entity_name = target.name
    item.target_entity_slug = target.slug
    item.target_entity_type_slug = target_et.slug if target_et else None

    return item


@router.get("/{relation_id}", response_model=EntityRelationResponse)
async def get_entity_relation(
    relation_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user_optional),
) -> EntityRelationResponse:
    """Get a single entity relation by ID."""
    rel = await session.get(EntityRelation, relation_id)
    if not rel:
        raise NotFoundError("EntityRelation", str(relation_id))

    # Batch load all related objects in parallel queries
    rt_result = await session.execute(
        select(RelationType).where(RelationType.id == rel.relation_type_id)
    )
    rt = rt_result.scalar()

    # Batch load entities
    entity_ids = [rel.source_entity_id, rel.target_entity_id]
    entities_result = await session.execute(
        select(Entity).where(Entity.id.in_(entity_ids))
    )
    entities_map = {e.id: e for e in entities_result.scalars().all()}
    source = entities_map.get(rel.source_entity_id)
    target = entities_map.get(rel.target_entity_id)

    # Batch load entity types
    entity_type_ids = []
    if source and source.entity_type_id:
        entity_type_ids.append(source.entity_type_id)
    if target and target.entity_type_id:
        entity_type_ids.append(target.entity_type_id)

    entity_types_map = {}
    if entity_type_ids:
        entity_types_result = await session.execute(
            select(EntityType).where(EntityType.id.in_(entity_type_ids))
        )
        entity_types_map = {et.id: et for et in entity_types_result.scalars().all()}

    source_et = entity_types_map.get(source.entity_type_id) if source else None
    target_et = entity_types_map.get(target.entity_type_id) if target else None

    response = EntityRelationResponse.model_validate(rel)
    response.relation_type_slug = rt.slug if rt else None
    response.relation_type_name = rt.name if rt else None
    response.source_entity_name = source.name if source else None
    response.source_entity_slug = source.slug if source else None
    response.source_entity_type_slug = source_et.slug if source_et else None
    response.target_entity_name = target.name if target else None
    response.target_entity_slug = target.slug if target else None
    response.target_entity_type_slug = target_et.slug if target_et else None

    return response


@router.put("/{relation_id}", response_model=EntityRelationResponse)
async def update_entity_relation(
    relation_id: UUID,
    data: EntityRelationUpdate,
    request: Request,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
) -> EntityRelationResponse:
    """Update an entity relation."""
    rel = await session.get(EntityRelation, relation_id)
    if not rel:
        raise NotFoundError("EntityRelation", str(relation_id))

    async with AuditContext(session, current_user, request) as audit:
        # Update fields
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(rel, field, value)

        audit.track_action(
            action=AuditAction.UPDATE,
            entity_type="EntityRelation",
            entity_id=rel.id,
            changes={"updated_fields": list(update_data.keys())},
        )

        await session.commit()
        await session.refresh(rel)

    return EntityRelationResponse.model_validate(rel)


@router.put("/{relation_id}/verify", response_model=EntityRelationResponse)
async def verify_entity_relation(
    relation_id: UUID,
    verified: Annotated[bool, Query(description="Mark as verified or unverified")] = True,
    verified_by: Annotated[str | None, Query(description="Name of verifier")] = None,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
) -> EntityRelationResponse:
    """Verify an entity relation."""
    rel = await session.get(EntityRelation, relation_id)
    if not rel:
        raise NotFoundError("EntityRelation", str(relation_id))

    rel.human_verified = verified
    rel.verified_by = verified_by
    rel.verified_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(rel)

    return EntityRelationResponse.model_validate(rel)


@router.delete("/{relation_id}", response_model=MessageResponse)
async def delete_entity_relation(
    relation_id: UUID,
    request: Request,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """Delete an entity relation. Requires Editor role."""
    rel = await session.get(EntityRelation, relation_id)
    if not rel:
        raise NotFoundError("EntityRelation", str(relation_id))

    async with AuditContext(session, current_user, request) as audit:
        audit.track_action(
            action=AuditAction.DELETE,
            entity_type="EntityRelation",
            entity_id=relation_id,
            changes={"deleted": True},
        )
        await session.delete(rel)
        await session.commit()

    return MessageResponse(message="Entity relation deleted successfully")


# ============================================================================
# Graph Endpoints
# ============================================================================


@router.get("/graph/{entity_id}", response_model=EntityRelationsGraph)
async def get_entity_relations_graph(
    entity_id: UUID,
    depth: Annotated[int, Query(ge=1, le=3, description="Graph traversal depth (1-3)")] = 1,
    relation_type_slugs: Annotated[list[str] | None, Query(description="Filter by relation type slugs")] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user_optional),
) -> EntityRelationsGraph:
    """Get a graph of entity relations centered on the given entity."""
    entity = await session.get(Entity, entity_id)
    if not entity:
        raise NotFoundError("Entity", str(entity_id))

    # Pre-load all RelationTypes and EntityTypes to avoid N+1 queries
    relation_types_result = await session.execute(select(RelationType))
    relation_types_map: dict[UUID, RelationType] = {
        rt.id: rt for rt in relation_types_result.scalars().all()
    }

    entity_types_result = await session.execute(select(EntityType))
    entity_types_map: dict[UUID, EntityType] = {
        et.id: et for et in entity_types_result.scalars().all()
    }

    # Build filter for relation type slugs if provided
    allowed_relation_type_ids: set | None = None
    if relation_type_slugs:
        allowed_relation_type_ids = {
            rt.id for rt in relation_types_map.values()
            if rt.slug in relation_type_slugs
        }

    # Cache for loaded entities
    entities_cache: dict[UUID, Entity] = {entity_id: entity}
    visited_entities: set = set()
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen_edges: set = set()

    # Collect entity IDs to explore at each depth level
    current_level_ids = {entity_id}

    for current_depth in range(depth + 1):
        if not current_level_ids:
            break

        next_level_ids: set = set()

        # Batch load entities not yet cached
        entities_to_load = current_level_ids - set(entities_cache.keys())
        if entities_to_load:
            ents_result = await session.execute(
                select(Entity).where(Entity.id.in_(entities_to_load))
            )
            for ent in ents_result.scalars().all():
                entities_cache[ent.id] = ent

        # Process entities at current depth
        for ent_id in current_level_ids:
            if ent_id in visited_entities:
                continue
            visited_entities.add(ent_id)

            ent = entities_cache.get(ent_id)
            if not ent:
                continue

            ent_type = entity_types_map.get(ent.entity_type_id)

            nodes.append({
                "id": str(ent.id),
                "name": ent.name,
                "slug": ent.slug,
                "type": ent_type.slug if ent_type else None,
                "type_name": ent_type.name if ent_type else None,
                "icon": ent_type.icon if ent_type else None,
                "color": ent_type.color if ent_type else None,
                "depth": current_depth,
            })

        # Batch load all relations for current level entities
        if current_depth < depth:
            # Outgoing relations
            outgoing_query = select(EntityRelation).where(
                EntityRelation.source_entity_id.in_(current_level_ids),
                EntityRelation.is_active.is_(True),
            )
            if allowed_relation_type_ids is not None:
                outgoing_query = outgoing_query.where(
                    EntityRelation.relation_type_id.in_(allowed_relation_type_ids)
                )

            outgoing_result = await session.execute(outgoing_query)
            for rel in outgoing_result.scalars().all():
                if rel.id not in seen_edges:
                    seen_edges.add(rel.id)
                    rt = relation_types_map.get(rel.relation_type_id)
                    edges.append({
                        "id": str(rel.id),
                        "source": str(rel.source_entity_id),
                        "target": str(rel.target_entity_id),
                        "type": rt.slug if rt else None,
                        "type_name": rt.name if rt else None,
                        "color": rt.color if rt else None,
                        "attributes": rel.attributes,
                    })
                    if rel.target_entity_id not in visited_entities:
                        next_level_ids.add(rel.target_entity_id)

            # Incoming relations
            incoming_query = select(EntityRelation).where(
                EntityRelation.target_entity_id.in_(current_level_ids),
                EntityRelation.is_active.is_(True),
            )
            if allowed_relation_type_ids is not None:
                incoming_query = incoming_query.where(
                    EntityRelation.relation_type_id.in_(allowed_relation_type_ids)
                )

            incoming_result = await session.execute(incoming_query)
            for rel in incoming_result.scalars().all():
                if rel.id not in seen_edges:
                    seen_edges.add(rel.id)
                    rt = relation_types_map.get(rel.relation_type_id)
                    edges.append({
                        "id": str(rel.id),
                        "source": str(rel.source_entity_id),
                        "target": str(rel.target_entity_id),
                        "type": rt.slug if rt else None,
                        "type_name": rt.name_inverse if rt else None,
                        "color": rt.color if rt else None,
                        "attributes": rel.attributes,
                    })
                    if rel.source_entity_id not in visited_entities:
                        next_level_ids.add(rel.source_entity_id)

        current_level_ids = next_level_ids

    return EntityRelationsGraph(nodes=nodes, edges=edges)
