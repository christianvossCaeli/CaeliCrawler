"""API endpoints for Entity management."""

import json
import unicodedata
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select, text, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Entity, EntityType, FacetValue, EntityRelation
from app.models.document import Document

# Import for external API data
try:
    from external_apis.models.sync_record import SyncRecord
    from external_apis.models.external_api_config import ExternalAPIConfig
    EXTERNAL_API_AVAILABLE = True
except ImportError:
    EXTERNAL_API_AVAILABLE = False
from app.schemas.entity import (
    EntityCreate,
    EntityUpdate,
    EntityResponse,
    EntityListResponse,
    EntityBrief,
    EntityHierarchy,
)
from app.schemas.common import MessageResponse
from app.core.exceptions import NotFoundError, ConflictError
from app.utils.text import create_slug as generate_slug

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
        query = query.where(Entity.is_active.is_(is_active))
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
        try:
            attr_filters = json.loads(core_attr_filters)
            if not isinstance(attr_filters, dict):
                raise ValueError("core_attr_filters must be a JSON object")
            for key, value in attr_filters.items():
                if value is not None and value != "":
                    query = query.where(
                        Entity.core_attributes[key].astext == str(value)
                    )
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid core_attr_filters parameter: {str(e)}"
            )

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

    if not entities:
        return EntityListResponse(
            items=[],
            total=total,
            page=page,
            per_page=per_page,
            pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
        )

    # Collect entity IDs for batch queries
    entity_ids = [e.id for e in entities]
    entity_type_ids = list(set(e.entity_type_id for e in entities))

    # Batch load EntityTypes (1 query instead of N)
    entity_types_result = await session.execute(
        select(EntityType).where(EntityType.id.in_(entity_type_ids))
    )
    entity_types_map = {et.id: et for et in entity_types_result.scalars().all()}

    # Batch count facet values (1 query instead of N)
    facet_counts_result = await session.execute(
        select(FacetValue.entity_id, func.count(FacetValue.id))
        .where(FacetValue.entity_id.in_(entity_ids))
        .group_by(FacetValue.entity_id)
    )
    facet_counts_map = dict(facet_counts_result.fetchall())

    # Batch count relations (1 query instead of N)
    # Count as source
    source_counts_result = await session.execute(
        select(EntityRelation.source_entity_id, func.count(EntityRelation.id))
        .where(EntityRelation.source_entity_id.in_(entity_ids))
        .group_by(EntityRelation.source_entity_id)
    )
    source_counts = dict(source_counts_result.fetchall())

    # Count as target
    target_counts_result = await session.execute(
        select(EntityRelation.target_entity_id, func.count(EntityRelation.id))
        .where(EntityRelation.target_entity_id.in_(entity_ids))
        .group_by(EntityRelation.target_entity_id)
    )
    target_counts = dict(target_counts_result.fetchall())

    # Merge relation counts
    relation_counts_map = {}
    for entity_id in entity_ids:
        relation_counts_map[entity_id] = source_counts.get(entity_id, 0) + target_counts.get(entity_id, 0)

    # Batch count children (1 query instead of N)
    children_counts_result = await session.execute(
        select(Entity.parent_id, func.count(Entity.id))
        .where(Entity.parent_id.in_(entity_ids))
        .group_by(Entity.parent_id)
    )
    children_counts_map = dict(children_counts_result.fetchall())

    # Build response items using pre-fetched data
    items = []
    for entity in entities:
        entity_type = entity_types_map.get(entity.entity_type_id)

        item = EntityResponse.model_validate(entity)
        item.entity_type_name = entity_type.name if entity_type else None
        item.entity_type_slug = entity_type.slug if entity_type else None
        item.facet_count = facet_counts_map.get(entity.id, 0)
        item.relation_count = relation_counts_map.get(entity.id, 0)
        item.children_count = children_counts_map.get(entity.id, 0)
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
                Entity.is_active.is_(True)
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


# ============================================================================
# Filter Options Endpoints (MUST be defined BEFORE dynamic /{entity_id} routes)
# ============================================================================


@router.get("/filter-options/location")
async def get_location_filter_options(
    country: Optional[str] = Query(default=None, description="Filter admin_level_1 options by country"),
    admin_level_1: Optional[str] = Query(default=None, description="Filter admin_level_2 options by admin_level_1"),
    session: AsyncSession = Depends(get_session),
):
    """Get available filter options for location fields (country, admin_level_1, admin_level_2)."""
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


# ============================================================================
# Dynamic Entity Routes (MUST be AFTER static routes like /filter-options/*)
# ============================================================================


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

    # Validate parent_id if being changed
    if "parent_id" in update_data and update_data["parent_id"] is not None:
        new_parent_id = update_data["parent_id"]

        # Check parent exists
        parent = await session.get(Entity, new_parent_id)
        if not parent:
            raise NotFoundError("Parent Entity", str(new_parent_id))

        # Check for circular reference: entity cannot be its own ancestor
        # Walk up the hierarchy from the new parent to check if we encounter ourselves
        current = parent
        while current is not None:
            if current.id == entity_id:
                raise ConflictError(
                    "Circular hierarchy detected",
                    detail="Cannot set parent that would create a circular reference"
                )
            if current.parent_id:
                current = await session.get(Entity, current.parent_id)
            else:
                break

        # Update hierarchy path and level based on new parent
        update_data["hierarchy_path"] = f"{parent.hierarchy_path}/{entity.slug}"
        update_data["hierarchy_level"] = parent.hierarchy_level + 1
    elif "parent_id" in update_data and update_data["parent_id"] is None:
        # Moving to root level
        update_data["hierarchy_path"] = f"/{entity.slug}"
        update_data["hierarchy_level"] = 0

    # If name changes, update normalized name
    if "name" in update_data:
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
    """Delete an entity.

    If force=True, deletes the entity along with all its children (recursively),
    facet values, and relations using efficient batch queries.
    """
    entity = await session.get(Entity, entity_id)
    if not entity:
        raise NotFoundError("Entity", str(entity_id))

    entity_name = entity.name

    # Check for children
    children_count = (await session.execute(
        select(func.count()).where(Entity.parent_id == entity.id)
    )).scalar()

    if children_count > 0 and not force:
        raise ConflictError(
            "Cannot delete entity with children",
            detail=f"Entity '{entity_name}' has {children_count} child entities. Use force=true to delete anyway.",
        )

    # Check for facets
    facet_count = (await session.execute(
        select(func.count()).where(FacetValue.entity_id == entity.id)
    )).scalar()

    if facet_count > 0 and not force:
        raise ConflictError(
            "Cannot delete entity with facets",
            detail=f"Entity '{entity_name}' has {facet_count} facet values. Use force=true to delete anyway.",
        )

    if force:
        # Use CTE to get all descendant entity IDs (including the root entity)
        # This is much more efficient than recursive Python calls
        hierarchy_cte = text("""
            WITH RECURSIVE entity_tree AS (
                -- Base case: the entity we want to delete
                SELECT id FROM entities WHERE id = :entity_id
                UNION ALL
                -- Recursive case: all children
                SELECT e.id FROM entities e
                INNER JOIN entity_tree et ON e.parent_id = et.id
            )
            SELECT id FROM entity_tree
        """)

        result = await session.execute(hierarchy_cte, {"entity_id": str(entity_id)})
        all_entity_ids = [row[0] for row in result.fetchall()]

        if all_entity_ids:
            # Batch delete all facet values for all entities in the hierarchy (1 query)
            await session.execute(
                delete(FacetValue).where(FacetValue.entity_id.in_(all_entity_ids))
            )

            # Batch delete all relations where any entity in hierarchy is source or target (1 query)
            await session.execute(
                delete(EntityRelation).where(
                    or_(
                        EntityRelation.source_entity_id.in_(all_entity_ids),
                        EntityRelation.target_entity_id.in_(all_entity_ids)
                    )
                )
            )

            # Delete entities from bottom up (children first) to respect FK constraints
            # We do this by deleting in reverse hierarchy order
            # First, set parent_id to NULL for all children to break the FK chain
            await session.execute(
                text("""
                    UPDATE entities SET parent_id = NULL
                    WHERE parent_id IN (
                        WITH RECURSIVE entity_tree AS (
                            SELECT id FROM entities WHERE id = :entity_id
                            UNION ALL
                            SELECT e.id FROM entities e
                            INNER JOIN entity_tree et ON e.parent_id = et.id
                        )
                        SELECT id FROM entity_tree
                    )
                """),
                {"entity_id": str(entity_id)}
            )

            # Now delete all entities in the hierarchy (1 query)
            await session.execute(
                delete(Entity).where(Entity.id.in_(all_entity_ids))
            )
    else:
        # Simple delete without cascade
        await session.delete(entity)

    await session.commit()

    return MessageResponse(message=f"Entity '{entity_name}' deleted successfully")


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


@router.get("/{entity_id}/documents")
async def get_entity_documents(
    entity_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get documents linked to an entity via facet values.

    Returns all documents that are sources for facet values of this entity.
    """
    # Verify entity exists
    entity = await session.get(Entity, entity_id)
    if not entity:
        raise NotFoundError("Entity", str(entity_id))

    # Get distinct source_document_ids from all FacetValues for this entity
    source_doc_query = (
        select(FacetValue.source_document_id)
        .where(
            FacetValue.entity_id == entity_id,
            FacetValue.source_document_id.isnot(None)
        )
        .distinct()
    )
    result = await session.execute(source_doc_query)
    document_ids = [row[0] for row in result.fetchall()]

    if not document_ids:
        return {
            "entity_id": str(entity_id),
            "entity_name": entity.name,
            "documents": [],
            "total": 0,
        }

    # Load documents
    docs_query = select(Document).where(Document.id.in_(document_ids))
    docs_result = await session.execute(docs_query)
    documents = docs_result.scalars().all()

    # Count facet values per document
    facet_counts_query = (
        select(FacetValue.source_document_id, func.count(FacetValue.id))
        .where(
            FacetValue.entity_id == entity_id,
            FacetValue.source_document_id.in_(document_ids)
        )
        .group_by(FacetValue.source_document_id)
    )
    facet_counts_result = await session.execute(facet_counts_query)
    facet_counts_map = dict(facet_counts_result.fetchall())

    # Build response
    document_list = []
    for doc in documents:
        document_list.append({
            "id": str(doc.id),
            "title": doc.title,
            "url": doc.source_url,
            "source_type": doc.source_type,
            "processing_status": doc.processing_status,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "facet_count": facet_counts_map.get(doc.id, 0),
        })

    return {
        "entity_id": str(entity_id),
        "entity_name": entity.name,
        "documents": document_list,
        "total": len(document_list),
    }


@router.get("/{entity_id}/external-data")
async def get_entity_external_data(
    entity_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get raw external API data for an entity.

    Returns the raw API response data from the external API that created this entity,
    along with information about the sync source.
    """
    if not EXTERNAL_API_AVAILABLE:
        return {
            "entity_id": str(entity_id),
            "has_external_data": False,
            "message": "External API module not available",
        }

    # Verify entity exists
    entity = await session.get(Entity, entity_id)
    if not entity:
        raise NotFoundError("Entity", str(entity_id))

    # Check if entity has an external source
    if not entity.external_source_id:
        return {
            "entity_id": str(entity_id),
            "entity_name": entity.name,
            "has_external_data": False,
            "message": "Entity was not created from an external API",
        }

    # Get the ExternalAPIConfig
    config = await session.get(ExternalAPIConfig, entity.external_source_id)

    # Find the sync record for this entity
    sync_record_query = select(SyncRecord).where(SyncRecord.entity_id == entity_id)
    result = await session.execute(sync_record_query)
    sync_record = result.scalar()

    if not sync_record:
        return {
            "entity_id": str(entity_id),
            "entity_name": entity.name,
            "has_external_data": False,
            "external_source": {
                "id": str(config.id) if config else None,
                "name": config.name if config else None,
                "api_type": config.api_type if config else None,
            },
            "message": "No sync record found for this entity",
        }

    return {
        "entity_id": str(entity_id),
        "entity_name": entity.name,
        "has_external_data": True,
        "external_source": {
            "id": str(config.id) if config else None,
            "name": config.name if config else None,
            "api_type": config.api_type if config else None,
            "api_base_url": config.api_base_url if config else None,
        },
        "sync_record": {
            "id": str(sync_record.id),
            "external_id": sync_record.external_id,
            "sync_status": sync_record.sync_status,
            "first_seen_at": sync_record.first_seen_at.isoformat() if sync_record.first_seen_at else None,
            "last_seen_at": sync_record.last_seen_at.isoformat() if sync_record.last_seen_at else None,
            "last_modified_at": sync_record.last_modified_at.isoformat() if sync_record.last_modified_at else None,
        },
        "raw_data": sync_record.raw_data,
    }
