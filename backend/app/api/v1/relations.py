"""API endpoints for Relation Type and Entity Relation management."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import (
    RelationType, EntityRelation, Entity, EntityType, Document,
)
from app.schemas.relation import (
    RelationTypeCreate,
    RelationTypeUpdate,
    RelationTypeResponse,
    RelationTypeListResponse,
    EntityRelationCreate,
    EntityRelationUpdate,
    EntityRelationResponse,
    EntityRelationListResponse,
    EntityRelationsGraph,
    generate_slug,
)
from app.schemas.common import MessageResponse
from app.core.exceptions import NotFoundError, ConflictError

router = APIRouter()


# ============================================================================
# RelationType Endpoints
# ============================================================================


@router.get("/types", response_model=RelationTypeListResponse)
async def list_relation_types(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
    is_active: Optional[bool] = Query(default=None),
    source_entity_type_id: Optional[UUID] = Query(default=None),
    target_entity_type_id: Optional[UUID] = Query(default=None),
    search: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """List all relation types with pagination."""
    query = select(RelationType)

    if is_active is not None:
        query = query.where(RelationType.is_active == is_active)
    if source_entity_type_id:
        query = query.where(RelationType.source_entity_type_id == source_entity_type_id)
    if target_entity_type_id:
        query = query.where(RelationType.target_entity_type_id == target_entity_type_id)
    if search:
        query = query.where(
            RelationType.name.ilike(f"%{search}%") |
            RelationType.slug.ilike(f"%{search}%")
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Paginate
    query = query.order_by(RelationType.display_order, RelationType.name).offset((page - 1) * per_page).limit(per_page)
    result = await session.execute(query)
    relation_types = result.scalars().all()

    # Enrich with entity type names and counts
    items = []
    for rt in relation_types:
        source_et = await session.get(EntityType, rt.source_entity_type_id)
        target_et = await session.get(EntityType, rt.target_entity_type_id)

        relation_count = (await session.execute(
            select(func.count()).where(EntityRelation.relation_type_id == rt.id)
        )).scalar()

        item = RelationTypeResponse.model_validate(rt)
        item.source_entity_type_name = source_et.name if source_et else None
        item.source_entity_type_slug = source_et.slug if source_et else None
        item.target_entity_type_name = target_et.name if target_et else None
        item.target_entity_type_slug = target_et.slug if target_et else None
        item.relation_count = relation_count
        items.append(item)

    return RelationTypeListResponse(items=items, total=total)


@router.post("/types", response_model=RelationTypeResponse, status_code=201)
async def create_relation_type(
    data: RelationTypeCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new relation type."""
    # Verify entity types exist
    source_et = await session.get(EntityType, data.source_entity_type_id)
    if not source_et:
        raise NotFoundError("Source EntityType", str(data.source_entity_type_id))

    target_et = await session.get(EntityType, data.target_entity_type_id)
    if not target_et:
        raise NotFoundError("Target EntityType", str(data.target_entity_type_id))

    # Generate slug if not provided
    slug = data.slug or generate_slug(data.name)

    # Check for duplicate
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
):
    """Get a single relation type by ID."""
    rt = await session.get(RelationType, relation_type_id)
    if not rt:
        raise NotFoundError("RelationType", str(relation_type_id))

    source_et = await session.get(EntityType, rt.source_entity_type_id)
    target_et = await session.get(EntityType, rt.target_entity_type_id)

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
):
    """Get a single relation type by slug."""
    result = await session.execute(
        select(RelationType).where(RelationType.slug == slug)
    )
    rt = result.scalar()
    if not rt:
        raise NotFoundError("RelationType", slug)

    source_et = await session.get(EntityType, rt.source_entity_type_id)
    target_et = await session.get(EntityType, rt.target_entity_type_id)

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
    session: AsyncSession = Depends(get_session),
):
    """Update a relation type."""
    rt = await session.get(RelationType, relation_type_id)
    if not rt:
        raise NotFoundError("RelationType", str(relation_type_id))

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rt, field, value)

    await session.commit()
    await session.refresh(rt)

    return RelationTypeResponse.model_validate(rt)


@router.delete("/types/{relation_type_id}", response_model=MessageResponse)
async def delete_relation_type(
    relation_type_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Delete a relation type."""
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

    await session.delete(rt)
    await session.commit()

    return MessageResponse(message=f"Relation type '{rt.name}' deleted successfully")


# ============================================================================
# EntityRelation Endpoints
# ============================================================================


@router.get("", response_model=EntityRelationListResponse)
async def list_entity_relations(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    relation_type_id: Optional[UUID] = Query(default=None),
    relation_type_slug: Optional[str] = Query(default=None),
    source_entity_id: Optional[UUID] = Query(default=None),
    target_entity_id: Optional[UUID] = Query(default=None),
    entity_id: Optional[UUID] = Query(default=None, description="Either source or target"),
    min_confidence: float = Query(default=0.0, ge=0, le=1),
    human_verified: Optional[bool] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
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
        query = query.where(EntityRelation.human_verified == human_verified)
    if is_active is not None:
        query = query.where(EntityRelation.is_active == is_active)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Paginate
    query = query.order_by(EntityRelation.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await session.execute(query)
    relations = result.scalars().all()

    # Enrich with related info
    items = []
    for rel in relations:
        rt = await session.get(RelationType, rel.relation_type_id)
        source = await session.get(Entity, rel.source_entity_id)
        target = await session.get(Entity, rel.target_entity_id)

        source_et = await session.get(EntityType, source.entity_type_id) if source else None
        target_et = await session.get(EntityType, target.entity_type_id) if target else None

        item = EntityRelationResponse.model_validate(rel)
        item.relation_type_slug = rt.slug if rt else None
        item.relation_type_name = rt.name if rt else None
        item.source_entity_name = source.name if source else None
        item.source_entity_type_slug = source_et.slug if source_et else None
        item.target_entity_name = target.name if target else None
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
    session: AsyncSession = Depends(get_session),
):
    """Create a new entity relation."""
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
            detail=f"A relation of this type already exists between these entities",
        )

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
    await session.commit()
    await session.refresh(relation)

    item = EntityRelationResponse.model_validate(relation)
    item.relation_type_slug = rt.slug
    item.relation_type_name = rt.name
    item.source_entity_name = source.name
    item.target_entity_name = target.name

    return item


@router.get("/{relation_id}", response_model=EntityRelationResponse)
async def get_entity_relation(
    relation_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get a single entity relation by ID."""
    rel = await session.get(EntityRelation, relation_id)
    if not rel:
        raise NotFoundError("EntityRelation", str(relation_id))

    rt = await session.get(RelationType, rel.relation_type_id)
    source = await session.get(Entity, rel.source_entity_id)
    target = await session.get(Entity, rel.target_entity_id)

    source_et = await session.get(EntityType, source.entity_type_id) if source else None
    target_et = await session.get(EntityType, target.entity_type_id) if target else None

    response = EntityRelationResponse.model_validate(rel)
    response.relation_type_slug = rt.slug if rt else None
    response.relation_type_name = rt.name if rt else None
    response.source_entity_name = source.name if source else None
    response.source_entity_type_slug = source_et.slug if source_et else None
    response.target_entity_name = target.name if target else None
    response.target_entity_type_slug = target_et.slug if target_et else None

    return response


@router.put("/{relation_id}", response_model=EntityRelationResponse)
async def update_entity_relation(
    relation_id: UUID,
    data: EntityRelationUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update an entity relation."""
    rel = await session.get(EntityRelation, relation_id)
    if not rel:
        raise NotFoundError("EntityRelation", str(relation_id))

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rel, field, value)

    await session.commit()
    await session.refresh(rel)

    return EntityRelationResponse.model_validate(rel)


@router.put("/{relation_id}/verify", response_model=EntityRelationResponse)
async def verify_entity_relation(
    relation_id: UUID,
    verified: bool = Query(default=True),
    verified_by: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """Verify an entity relation."""
    rel = await session.get(EntityRelation, relation_id)
    if not rel:
        raise NotFoundError("EntityRelation", str(relation_id))

    rel.human_verified = verified
    rel.verified_by = verified_by
    rel.verified_at = datetime.utcnow()

    await session.commit()
    await session.refresh(rel)

    return EntityRelationResponse.model_validate(rel)


@router.delete("/{relation_id}", response_model=MessageResponse)
async def delete_entity_relation(
    relation_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Delete an entity relation."""
    rel = await session.get(EntityRelation, relation_id)
    if not rel:
        raise NotFoundError("EntityRelation", str(relation_id))

    await session.delete(rel)
    await session.commit()

    return MessageResponse(message="Entity relation deleted successfully")


# ============================================================================
# Graph Endpoints
# ============================================================================


@router.get("/graph/{entity_id}", response_model=EntityRelationsGraph)
async def get_entity_relations_graph(
    entity_id: UUID,
    depth: int = Query(default=1, ge=1, le=3),
    relation_type_slugs: Optional[List[str]] = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """Get a graph of entity relations centered on the given entity."""
    entity = await session.get(Entity, entity_id)
    if not entity:
        raise NotFoundError("Entity", str(entity_id))

    visited_entities: set = set()
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    async def explore(ent_id: UUID, current_depth: int):
        if current_depth > depth or ent_id in visited_entities:
            return

        visited_entities.add(ent_id)
        ent = await session.get(Entity, ent_id)
        if not ent:
            return

        ent_type = await session.get(EntityType, ent.entity_type_id)

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

        # Find outgoing relations
        outgoing_query = select(EntityRelation).where(
            EntityRelation.source_entity_id == ent_id,
            EntityRelation.is_active == True,
        )
        if relation_type_slugs:
            subq = select(RelationType.id).where(RelationType.slug.in_(relation_type_slugs))
            outgoing_query = outgoing_query.where(EntityRelation.relation_type_id.in_(subq))

        outgoing_result = await session.execute(outgoing_query)
        for rel in outgoing_result.scalars().all():
            rt = await session.get(RelationType, rel.relation_type_id)
            edges.append({
                "id": str(rel.id),
                "source": str(rel.source_entity_id),
                "target": str(rel.target_entity_id),
                "type": rt.slug if rt else None,
                "type_name": rt.name if rt else None,
                "color": rt.color if rt else None,
                "attributes": rel.attributes,
            })
            await explore(rel.target_entity_id, current_depth + 1)

        # Find incoming relations
        incoming_query = select(EntityRelation).where(
            EntityRelation.target_entity_id == ent_id,
            EntityRelation.is_active == True,
        )
        if relation_type_slugs:
            subq = select(RelationType.id).where(RelationType.slug.in_(relation_type_slugs))
            incoming_query = incoming_query.where(EntityRelation.relation_type_id.in_(subq))

        incoming_result = await session.execute(incoming_query)
        for rel in incoming_result.scalars().all():
            rt = await session.get(RelationType, rel.relation_type_id)
            edges.append({
                "id": str(rel.id),
                "source": str(rel.source_entity_id),
                "target": str(rel.target_entity_id),
                "type": rt.slug if rt else None,
                "type_name": rt.name_inverse if rt else None,  # Use inverse name for incoming
                "color": rt.color if rt else None,
                "attributes": rel.attributes,
            })
            await explore(rel.source_entity_id, current_depth + 1)

    await explore(entity_id, 0)

    # Deduplicate edges
    seen_edges = set()
    unique_edges = []
    for edge in edges:
        edge_key = edge["id"]
        if edge_key not in seen_edges:
            seen_edges.add(edge_key)
            unique_edges.append(edge)

    return EntityRelationsGraph(nodes=nodes, edges=unique_edges)
