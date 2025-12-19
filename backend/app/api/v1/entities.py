"""API endpoints for Entity management."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Entity, EntityType, FacetValue, EntityRelation
from app.schemas.entity import (
    EntityCreate,
    EntityUpdate,
    EntityResponse,
    EntityListResponse,
    EntityBrief,
    EntityHierarchy,
    generate_slug,
)
from app.schemas.common import MessageResponse
from app.core.exceptions import NotFoundError, ConflictError

router = APIRouter()


@router.get("", response_model=EntityListResponse)
async def list_entities(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=500),
    entity_type_id: Optional[UUID] = Query(default=None),
    entity_type_slug: Optional[str] = Query(default=None),
    parent_id: Optional[UUID] = Query(default=None),
    hierarchy_level: Optional[int] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    search: Optional[str] = Query(default=None),
    country: Optional[str] = Query(default=None, description="Filter by country code (DE, GB, etc.)"),
    admin_level_1: Optional[str] = Query(default=None, description="Filter by admin level 1 (Bundesland, Region)"),
    admin_level_2: Optional[str] = Query(default=None, description="Filter by admin level 2 (Landkreis, District)"),
    core_attr_filters: Optional[str] = Query(default=None, description="JSON-encoded core_attributes filters, e.g. {\"locality_type\": \"Stadt\"}"),
    session: AsyncSession = Depends(get_session),
):
    """List entities with filters."""
    query = select(Entity)

    # Filter by entity type (ID or slug)
    if entity_type_id:
        query = query.where(Entity.entity_type_id == entity_type_id)
    elif entity_type_slug:
        subq = select(EntityType.id).where(EntityType.slug == entity_type_slug)
        query = query.where(Entity.entity_type_id.in_(subq))

    if parent_id:
        query = query.where(Entity.parent_id == parent_id)
    if hierarchy_level is not None:
        query = query.where(Entity.hierarchy_level == hierarchy_level)
    if is_active is not None:
        query = query.where(Entity.is_active == is_active)
    if country:
        # Filter by indexed country column (with fallback to core_attributes for backwards compat)
        query = query.where(
            or_(
                Entity.country == country.upper(),
                Entity.core_attributes["country"].astext == country.upper()
            )
        )
    if admin_level_1:
        query = query.where(
            or_(
                Entity.admin_level_1 == admin_level_1,
                Entity.core_attributes["admin_level_1"].astext == admin_level_1
            )
        )
    if admin_level_2:
        query = query.where(
            or_(
                Entity.admin_level_2 == admin_level_2,
                Entity.core_attributes["admin_level_2"].astext == admin_level_2
            )
        )

    # Filter by core_attributes (dynamic schema-based filtering)
    if core_attr_filters:
        import json
        try:
            attr_filters = json.loads(core_attr_filters)
            for key, value in attr_filters.items():
                if value is not None and value != "":
                    query = query.where(
                        Entity.core_attributes[key].astext == str(value)
                    )
        except json.JSONDecodeError:
            pass  # Ignore invalid JSON

    if search:
        query = query.where(
            or_(
                Entity.name.ilike(f"%{search}%"),
                Entity.name_normalized.ilike(f"%{search}%"),
                Entity.external_id.ilike(f"%{search}%")
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Paginate
    query = query.order_by(Entity.hierarchy_path, Entity.name).offset((page - 1) * per_page).limit(per_page)
    result = await session.execute(query)
    entities = result.scalars().all()

    # Enrich with entity type info and counts
    items = []
    for entity in entities:
        entity_type = await session.get(EntityType, entity.entity_type_id)

        # Count facet values
        facet_count = (await session.execute(
            select(func.count()).where(FacetValue.entity_id == entity.id)
        )).scalar()

        # Count relations (as source or target)
        relation_count = (await session.execute(
            select(func.count()).where(
                or_(
                    EntityRelation.source_entity_id == entity.id,
                    EntityRelation.target_entity_id == entity.id
                )
            )
        )).scalar()

        # Count children
        children_count = (await session.execute(
            select(func.count()).where(Entity.parent_id == entity.id)
        )).scalar()

        item = EntityResponse.model_validate(entity)
        item.entity_type_name = entity_type.name if entity_type else None
        item.entity_type_slug = entity_type.slug if entity_type else None
        item.facet_count = facet_count
        item.relation_count = relation_count
        item.children_count = children_count
        items.append(item)

    return EntityListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
    )


@router.post("", response_model=EntityResponse, status_code=201)
async def create_entity(
    data: EntityCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new entity."""
    # Verify entity type exists
    entity_type = await session.get(EntityType, data.entity_type_id)
    if not entity_type:
        raise NotFoundError("EntityType", str(data.entity_type_id))

    # Generate slug if not provided
    slug = data.slug or generate_slug(data.name)

    # Check for duplicate within same entity type
    existing = await session.execute(
        select(Entity).where(
            and_(
                Entity.entity_type_id == data.entity_type_id,
                or_(
                    Entity.name == data.name,
                    Entity.slug == slug,
                    (Entity.external_id == data.external_id) if data.external_id else False
                )
            )
        )
    )
    if existing.scalar():
        raise ConflictError(
            "Entity already exists",
            detail=f"An entity with name '{data.name}' or slug '{slug}' already exists for this type",
        )

    # Handle parent relationship
    hierarchy_path = ""
    hierarchy_level = 0
    if data.parent_id:
        parent = await session.get(Entity, data.parent_id)
        if not parent:
            raise NotFoundError("Parent Entity", str(data.parent_id))
        hierarchy_path = f"{parent.hierarchy_path}/{slug}"
        hierarchy_level = parent.hierarchy_level + 1
    else:
        hierarchy_path = f"/{slug}"

    # Normalize name for search
    import unicodedata
    name_normalized = unicodedata.normalize("NFKD", data.name.lower())

    entity = Entity(
        entity_type_id=data.entity_type_id,
        name=data.name,
        name_normalized=name_normalized,
        slug=slug,
        external_id=data.external_id,
        parent_id=data.parent_id,
        hierarchy_path=hierarchy_path,
        hierarchy_level=hierarchy_level,
        country=data.country.upper() if data.country else None,
        admin_level_1=data.admin_level_1,
        admin_level_2=data.admin_level_2,
        core_attributes=data.core_attributes or {},
        latitude=data.latitude,
        longitude=data.longitude,
        is_active=data.is_active,
        owner_id=data.owner_id,
    )
    session.add(entity)
    await session.commit()
    await session.refresh(entity)

    item = EntityResponse.model_validate(entity)
    item.entity_type_name = entity_type.name
    item.entity_type_slug = entity_type.slug

    return item


@router.get("/hierarchy/{entity_type_slug}")
async def get_entity_hierarchy(
    entity_type_slug: str,
    root_id: Optional[UUID] = Query(default=None, description="Start from this entity"),
    max_depth: int = Query(default=3, ge=1, le=10),
    session: AsyncSession = Depends(get_session),
) -> EntityHierarchy:
    """Get hierarchical tree of entities."""
    # Get entity type
    et_result = await session.execute(
        select(EntityType).where(EntityType.slug == entity_type_slug)
    )
    entity_type = et_result.scalar()
    if not entity_type:
        raise NotFoundError("EntityType", entity_type_slug)

    async def build_tree(parent_id: Optional[UUID], depth: int) -> List[Dict[str, Any]]:
        if depth > max_depth:
            return []

        query = select(Entity).where(
            and_(
                Entity.entity_type_id == entity_type.id,
                Entity.parent_id == parent_id if parent_id else Entity.parent_id.is_(None),
                Entity.is_active == True
            )
        ).order_by(Entity.name)

        result = await session.execute(query)
        entities = result.scalars().all()

        tree = []
        for entity in entities:
            children = await build_tree(entity.id, depth + 1)
            tree.append({
                "id": str(entity.id),
                "name": entity.name,
                "slug": entity.slug,
                "external_id": entity.external_id,
                "hierarchy_level": entity.hierarchy_level,
                "children": children,
                "children_count": len(children),
            })
        return tree

    tree = await build_tree(root_id, 0)

    return EntityHierarchy(
        entity_type_id=entity_type.id,
        entity_type_slug=entity_type.slug,
        entity_type_name=entity_type.name,
        root_id=root_id,
        tree=tree,
        total_nodes=sum(1 for _ in _count_nodes(tree)),
    )


def _count_nodes(tree: List[Dict]) -> int:
    """Count total nodes in tree."""
    for node in tree:
        yield 1
        yield from _count_nodes(node.get("children", []))


@router.get("/{entity_id}", response_model=EntityResponse)
async def get_entity(
    entity_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get a single entity by ID."""
    entity = await session.get(Entity, entity_id)
    if not entity:
        raise NotFoundError("Entity", str(entity_id))

    entity_type = await session.get(EntityType, entity.entity_type_id)

    # Count facet values
    facet_count = (await session.execute(
        select(func.count()).where(FacetValue.entity_id == entity.id)
    )).scalar()

    # Count relations
    relation_count = (await session.execute(
        select(func.count()).where(
            or_(
                EntityRelation.source_entity_id == entity.id,
                EntityRelation.target_entity_id == entity.id
            )
        )
    )).scalar()

    # Count children
    children_count = (await session.execute(
        select(func.count()).where(Entity.parent_id == entity.id)
    )).scalar()

    # Get parent info
    parent_name = None
    if entity.parent_id:
        parent = await session.get(Entity, entity.parent_id)
        parent_name = parent.name if parent else None

    response = EntityResponse.model_validate(entity)
    response.entity_type_name = entity_type.name if entity_type else None
    response.entity_type_slug = entity_type.slug if entity_type else None
    response.parent_name = parent_name
    response.facet_count = facet_count
    response.relation_count = relation_count
    response.children_count = children_count

    return response


@router.get("/by-slug/{entity_type_slug}/{entity_slug}", response_model=EntityResponse)
async def get_entity_by_slug(
    entity_type_slug: str,
    entity_slug: str,
    session: AsyncSession = Depends(get_session),
):
    """Get an entity by type slug and entity slug."""
    # First get entity type
    et_result = await session.execute(
        select(EntityType).where(EntityType.slug == entity_type_slug)
    )
    entity_type = et_result.scalar()
    if not entity_type:
        raise NotFoundError("EntityType", entity_type_slug)

    # Then get entity
    result = await session.execute(
        select(Entity).where(
            and_(
                Entity.entity_type_id == entity_type.id,
                Entity.slug == entity_slug
            )
        )
    )
    entity = result.scalar()
    if not entity:
        raise NotFoundError("Entity", f"{entity_type_slug}/{entity_slug}")

    # Get counts
    facet_count = (await session.execute(
        select(func.count()).where(FacetValue.entity_id == entity.id)
    )).scalar()

    relation_count = (await session.execute(
        select(func.count()).where(
            or_(
                EntityRelation.source_entity_id == entity.id,
                EntityRelation.target_entity_id == entity.id
            )
        )
    )).scalar()

    children_count = (await session.execute(
        select(func.count()).where(Entity.parent_id == entity.id)
    )).scalar()

    response = EntityResponse.model_validate(entity)
    response.entity_type_name = entity_type.name
    response.entity_type_slug = entity_type.slug
    response.facet_count = facet_count
    response.relation_count = relation_count
    response.children_count = children_count

    return response


@router.get("/{entity_id}/children", response_model=EntityListResponse)
async def get_entity_children(
    entity_id: UUID,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """Get direct children of an entity."""
    entity = await session.get(Entity, entity_id)
    if not entity:
        raise NotFoundError("Entity", str(entity_id))

    query = select(Entity).where(Entity.parent_id == entity_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Paginate
    query = query.order_by(Entity.name).offset((page - 1) * per_page).limit(per_page)
    result = await session.execute(query)
    children = result.scalars().all()

    entity_type = await session.get(EntityType, entity.entity_type_id)

    items = []
    for child in children:
        item = EntityResponse.model_validate(child)
        item.entity_type_name = entity_type.name if entity_type else None
        item.entity_type_slug = entity_type.slug if entity_type else None
        items.append(item)

    return EntityListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
    )


@router.put("/{entity_id}", response_model=EntityResponse)
async def update_entity(
    entity_id: UUID,
    data: EntityUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update an entity."""
    entity = await session.get(Entity, entity_id)
    if not entity:
        raise NotFoundError("Entity", str(entity_id))

    # Update fields
    update_data = data.model_dump(exclude_unset=True)

    # If name changes, update normalized name
    if "name" in update_data:
        import unicodedata
        update_data["name_normalized"] = unicodedata.normalize("NFKD", update_data["name"].lower())

    for field, value in update_data.items():
        setattr(entity, field, value)

    await session.commit()
    await session.refresh(entity)

    entity_type = await session.get(EntityType, entity.entity_type_id)

    response = EntityResponse.model_validate(entity)
    response.entity_type_name = entity_type.name if entity_type else None
    response.entity_type_slug = entity_type.slug if entity_type else None

    return response


@router.delete("/{entity_id}", response_model=MessageResponse)
async def delete_entity(
    entity_id: UUID,
    force: bool = Query(default=False, description="Force delete with all facets and relations"),
    session: AsyncSession = Depends(get_session),
):
    """Delete an entity."""
    entity = await session.get(Entity, entity_id)
    if not entity:
        raise NotFoundError("Entity", str(entity_id))

    # Check for children
    children_count = (await session.execute(
        select(func.count()).where(Entity.parent_id == entity.id)
    )).scalar()

    if children_count > 0 and not force:
        raise ConflictError(
            "Cannot delete entity with children",
            detail=f"Entity '{entity.name}' has {children_count} child entities. Use force=true to delete anyway.",
        )

    # Check for facets
    facet_count = (await session.execute(
        select(func.count()).where(FacetValue.entity_id == entity.id)
    )).scalar()

    if facet_count > 0 and not force:
        raise ConflictError(
            "Cannot delete entity with facets",
            detail=f"Entity '{entity.name}' has {facet_count} facet values. Use force=true to delete anyway.",
        )

    # If force, delete related data first
    if force:
        # Delete children recursively
        async def delete_children(parent_id: UUID):
            children_result = await session.execute(
                select(Entity).where(Entity.parent_id == parent_id)
            )
            children = children_result.scalars().all()
            for child in children:
                await delete_children(child.id)
                # Delete child's facets
                await session.execute(
                    select(FacetValue).where(FacetValue.entity_id == child.id)
                )
                await session.delete(child)

        await delete_children(entity.id)

        # Delete facets
        facets_result = await session.execute(
            select(FacetValue).where(FacetValue.entity_id == entity.id)
        )
        for facet in facets_result.scalars().all():
            await session.delete(facet)

        # Delete relations
        relations_result = await session.execute(
            select(EntityRelation).where(
                or_(
                    EntityRelation.source_entity_id == entity.id,
                    EntityRelation.target_entity_id == entity.id
                )
            )
        )
        for relation in relations_result.scalars().all():
            await session.delete(relation)

    await session.delete(entity)
    await session.commit()

    return MessageResponse(message=f"Entity '{entity.name}' deleted successfully")


@router.get("/{entity_id}/brief", response_model=EntityBrief)
async def get_entity_brief(
    entity_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get brief entity info (for references/dropdowns)."""
    entity = await session.get(Entity, entity_id)
    if not entity:
        raise NotFoundError("Entity", str(entity_id))

    entity_type = await session.get(EntityType, entity.entity_type_id)

    return EntityBrief(
        id=entity.id,
        name=entity.name,
        slug=entity.slug,
        entity_type_slug=entity_type.slug if entity_type else None,
        entity_type_name=entity_type.name if entity_type else None,
        hierarchy_path=entity.hierarchy_path,
    )


@router.get("/filter-options/location")
async def get_location_filter_options(
    country: Optional[str] = Query(default=None, description="Filter admin_level_1 options by country"),
    admin_level_1: Optional[str] = Query(default=None, description="Filter admin_level_2 options by admin_level_1"),
    session: AsyncSession = Depends(get_session),
):
    """Get available filter options for location fields (country, admin_level_1, admin_level_2).

    NOTE: This endpoint must be defined BEFORE the dynamic /{entity_id} routes."""

    # Get distinct countries
    countries_query = select(Entity.country).where(
        Entity.country.isnot(None)
    ).distinct().order_by(Entity.country)
    countries_result = await session.execute(countries_query)
    countries = [row[0] for row in countries_result.fetchall()]

    # Get distinct admin_level_1 values
    admin_level_1_query = select(Entity.admin_level_1).where(
        Entity.admin_level_1.isnot(None),
        Entity.admin_level_1 != ""
    )
    if country:
        admin_level_1_query = admin_level_1_query.where(Entity.country == country.upper())
    admin_level_1_query = admin_level_1_query.distinct().order_by(Entity.admin_level_1)
    admin_level_1_result = await session.execute(admin_level_1_query)
    admin_level_1_values = [row[0] for row in admin_level_1_result.fetchall()]

    # Get distinct admin_level_2 values
    admin_level_2_query = select(Entity.admin_level_2).where(
        Entity.admin_level_2.isnot(None),
        Entity.admin_level_2 != ""
    )
    if country:
        admin_level_2_query = admin_level_2_query.where(Entity.country == country.upper())
    if admin_level_1:
        admin_level_2_query = admin_level_2_query.where(Entity.admin_level_1 == admin_level_1)
    admin_level_2_query = admin_level_2_query.distinct().order_by(Entity.admin_level_2)
    admin_level_2_result = await session.execute(admin_level_2_query)
    admin_level_2_values = [row[0] for row in admin_level_2_result.fetchall()]

    return {
        "countries": countries,
        "admin_level_1": admin_level_1_values,
        "admin_level_2": admin_level_2_values,
    }


@router.get("/filter-options/attributes")
async def get_attribute_filter_options(
    entity_type_slug: str = Query(..., description="Entity type slug to get attribute options for"),
    attribute_key: Optional[str] = Query(default=None, description="Specific attribute key to get values for"),
    session: AsyncSession = Depends(get_session),
):
    """Get available filter options for core_attributes based on entity type schema.

    Returns the attribute schema properties and optionally distinct values for a specific attribute.

    NOTE: This endpoint must be defined BEFORE the dynamic /{entity_id} routes.
    """
    # Get entity type with schema
    et_result = await session.execute(
        select(EntityType).where(EntityType.slug == entity_type_slug)
    )
    entity_type = et_result.scalar()
    if not entity_type:
        raise NotFoundError("EntityType", entity_type_slug)

    # Get schema properties
    schema = entity_type.attribute_schema or {}
    properties = schema.get("properties", {})

    # Build response with filterable attributes
    filterable_attributes = []
    for key, prop in properties.items():
        attr_type = prop.get("type", "string")
        # Only include filterable types (strings, enums)
        if attr_type in ["string", "integer", "number"]:
            filterable_attributes.append({
                "key": key,
                "title": prop.get("title", key),
                "description": prop.get("description"),
                "type": attr_type,
                "format": prop.get("format"),
            })

    result = {
        "entity_type_slug": entity_type_slug,
        "entity_type_name": entity_type.name,
        "attributes": filterable_attributes,
    }

    # If specific attribute requested, get distinct values
    if attribute_key and attribute_key in properties:
        # Query distinct values from core_attributes JSONB
        values_query = (
            select(Entity.core_attributes[attribute_key].astext)
            .where(
                Entity.entity_type_id == entity_type.id,
                Entity.core_attributes[attribute_key].astext.isnot(None),
                Entity.core_attributes[attribute_key].astext != "",
            )
            .distinct()
            .order_by(Entity.core_attributes[attribute_key].astext)
            .limit(100)  # Limit to prevent huge lists
        )
        values_result = await session.execute(values_query)
        distinct_values = [row[0] for row in values_result.fetchall() if row[0]]
        result["attribute_values"] = {
            attribute_key: distinct_values
        }

    return result
