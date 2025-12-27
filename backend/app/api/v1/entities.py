"""API endpoints for Entity management."""

import json
import structlog
from typing import Any, Dict, List, Optional, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request

logger = structlog.get_logger(__name__)
from sqlalchemy import delete, func, select, text, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Entity, EntityType, FacetValue, EntityRelation
from app.models.document import Document
from app.models.data_source import DataSource
from app.models.user import User
from app.core.deps import get_current_user, require_editor
from app.core.audit import AuditContext
from app.models.audit_log import AuditAction
from app.utils.text import normalize_entity_name
from services.entity_matching_service import EntityMatchingService

# Import for external API data
try:
    from external_apis.models.sync_record import SyncRecord
    from app.models.api_configuration import APIConfiguration
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
    LocationFilterOptionsResponse,
    AttributeFilterOptionsResponse,
    FilterableAttribute,
    EntityDocumentsResponse,
    EntitySourcesResponse,
    EntityExternalDataResponse,
    GeoJSONFeatureCollection,
)
from app.schemas.common import MessageResponse
from app.core.exceptions import NotFoundError, ConflictError
from app.utils.text import create_slug as generate_slug

router = APIRouter()


@router.get("", response_model=EntityListResponse)
async def list_entities(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    per_page: Annotated[int, Query(ge=1, le=500, description="Items per page")] = 50,
    entity_type_id: Annotated[Optional[UUID], Query(description="Filter by entity type ID")] = None,
    entity_type_slug: Annotated[Optional[str], Query(description="Filter by entity type slug")] = None,
    parent_id: Annotated[Optional[UUID], Query(description="Filter by parent entity ID")] = None,
    hierarchy_level: Annotated[Optional[int], Query(description="Filter by hierarchy level")] = None,
    is_active: Annotated[Optional[bool], Query(description="Filter by active status")] = None,
    search: Annotated[Optional[str], Query(description="Search in entity name or external ID")] = None,
    country: Annotated[Optional[str], Query(description="Filter by country code (DE, GB, etc.)")] = None,
    admin_level_1: Annotated[Optional[str], Query(description="Filter by admin level 1 (Bundesland, Region)")] = None,
    admin_level_2: Annotated[Optional[str], Query(description="Filter by admin level 2 (Landkreis, District)")] = None,
    core_attr_filters: Annotated[Optional[str], Query(description="JSON-encoded core_attributes filters, e.g. {\"locality_type\": \"Stadt\"}")] = None,
    api_configuration_id: Annotated[Optional[UUID], Query(description="Filter by API configuration ID")] = None,
    has_facets: Annotated[Optional[bool], Query(description="Filter by whether entity has facet values")] = None,
    sort_by: Annotated[Optional[str], Query(description="Sort by field (name, hierarchy_path, facet_count, relation_count)")] = None,
    sort_order: Annotated[Optional[str], Query(description="Sort order (asc, desc)")] = "asc",
    session: AsyncSession = Depends(get_session),
) -> EntityListResponse:
    """List entities with filters."""
    from sqlalchemy.orm import selectinload

    # Eagerly load created_by and owner to avoid lazy loading in Pydantic validation
    query = select(Entity).options(
        selectinload(Entity.created_by),
        selectinload(Entity.owner),
    )

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

    # Filter by API configuration
    if api_configuration_id:
        query = query.where(Entity.api_configuration_id == api_configuration_id)

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
        # Use parameterized query pattern to prevent SQL injection
        search_pattern = f"%{search.replace('%', '\\%').replace('_', '\\_')}%"
        query = query.where(
            or_(
                Entity.name.ilike(search_pattern, escape='\\'),
                Entity.name_normalized.ilike(search_pattern, escape='\\'),
                Entity.external_id.ilike(search_pattern, escape='\\')
            )
        )

    # Filter by has_facets
    if has_facets is not None:
        entities_with_facets = (
            select(FacetValue.entity_id)
            .group_by(FacetValue.entity_id)
            .subquery()
        )
        if has_facets:
            # Only entities that have at least one facet value
            query = query.where(Entity.id.in_(select(entities_with_facets.c.entity_id)))
        else:
            # Only entities that have no facet values
            query = query.where(Entity.id.notin_(select(entities_with_facets.c.entity_id)))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Handle sorting
    sort_desc = sort_order and sort_order.lower() == "desc"

    # Sortable columns mapping
    sortable_columns = {
        "name": Entity.name,
        "hierarchy_path": Entity.hierarchy_path,
        "external_id": Entity.external_id,
        "created_at": Entity.created_at,
        "updated_at": Entity.updated_at,
    }

    # Handle sorting for computed fields (facet_count, relation_count)
    if sort_by == "facet_count":
        # Create subquery for facet counts
        facet_count_subq = (
            select(
                FacetValue.entity_id,
                func.count(FacetValue.id).label("facet_count")
            )
            .group_by(FacetValue.entity_id)
            .subquery()
        )
        query = query.outerjoin(facet_count_subq, Entity.id == facet_count_subq.c.entity_id)
        order_col = func.coalesce(facet_count_subq.c.facet_count, 0)
        if sort_desc:
            query = query.order_by(order_col.desc(), Entity.name)
        else:
            query = query.order_by(order_col, Entity.name)
    elif sort_by == "relation_count":
        # Create subquery for relation counts (source + target)
        source_count_subq = (
            select(
                EntityRelation.source_entity_id.label("entity_id"),
                func.count(EntityRelation.id).label("rel_count")
            )
            .group_by(EntityRelation.source_entity_id)
            .subquery()
        )
        target_count_subq = (
            select(
                EntityRelation.target_entity_id.label("entity_id"),
                func.count(EntityRelation.id).label("rel_count")
            )
            .group_by(EntityRelation.target_entity_id)
            .subquery()
        )
        query = query.outerjoin(source_count_subq, Entity.id == source_count_subq.c.entity_id)
        query = query.outerjoin(target_count_subq, Entity.id == target_count_subq.c.entity_id)
        total_rel_count = func.coalesce(source_count_subq.c.rel_count, 0) + func.coalesce(target_count_subq.c.rel_count, 0)
        if sort_desc:
            query = query.order_by(total_rel_count.desc(), Entity.name)
        else:
            query = query.order_by(total_rel_count, Entity.name)
    elif sort_by and sort_by in sortable_columns:
        order_col = sortable_columns[sort_by]
        if sort_desc:
            query = query.order_by(order_col.desc(), Entity.name)
        else:
            query = query.order_by(order_col, Entity.name)
    else:
        # Default sorting
        query = query.order_by(Entity.hierarchy_path, Entity.name)

    # Paginate
    query = query.offset((page - 1) * per_page).limit(per_page)
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

    # Initialize empty maps
    entity_types_map: dict = {}
    facet_counts_map: dict = {}
    relation_counts_map: dict = {}
    children_counts_map: dict = {}

    # Only run batch queries if there are entities
    if entity_ids:
        # Batch load EntityTypes (1 query instead of N)
        if entity_type_ids:
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
        for entity_id in entity_ids:
            relation_counts_map[entity_id] = source_counts.get(entity_id, 0) + target_counts.get(entity_id, 0)

        # Batch count children (1 query instead of N)
        children_counts_result = await session.execute(
            select(Entity.parent_id, func.count(Entity.id))
            .where(Entity.parent_id.in_(entity_ids))
            .group_by(Entity.parent_id)
        )
        children_counts_map = dict(children_counts_result.fetchall())

    # Batch load parent names (1 query instead of N)
    parent_ids = list(set(e.parent_id for e in entities if e.parent_id))
    parent_names_map: dict = {}
    if parent_ids:
        parent_result = await session.execute(
            select(Entity.id, Entity.name, Entity.slug)
            .where(Entity.id.in_(parent_ids))
        )
        for parent_id, parent_name, parent_slug in parent_result.fetchall():
            parent_names_map[parent_id] = {"name": parent_name, "slug": parent_slug}

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
        # Add parent name
        if entity.parent_id and entity.parent_id in parent_names_map:
            item.parent_name = parent_names_map[entity.parent_id]["name"]
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
    request: Request,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
) -> EntityResponse:
    """Create a new entity. Requires Editor role."""
    # Verify entity type exists
    entity_type = await session.get(EntityType, data.entity_type_id)
    if not entity_type:
        raise NotFoundError("EntityType", str(data.entity_type_id))

    # Generate slug if not provided
    slug = data.slug or generate_slug(data.name)

    # Use centralized normalization for consistent entity matching
    name_normalized = normalize_entity_name(data.name, country=data.country or "DE")

    # Check for duplicate within same entity type (using normalized name)
    existing = await session.execute(
        select(Entity).where(
            and_(
                Entity.entity_type_id == data.entity_type_id,
                Entity.is_active.is_(True),
                or_(
                    Entity.name_normalized == name_normalized,
                    Entity.slug == slug,
                    (Entity.external_id == data.external_id) if data.external_id else False
                )
            )
        )
    )
    existing_entity = existing.scalar()
    if existing_entity:
        raise ConflictError(
            "Entity already exists",
            detail=f"Entity '{existing_entity.name}' mit gleichem normalisierten Namen oder Slug existiert bereits",
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

    async with AuditContext(session, current_user, request) as audit:
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
        await session.flush()

        # Generate embedding for semantic similarity search
        from app.utils.similarity import generate_embedding
        embedding = await generate_embedding(entity.name)
        if embedding:
            entity.name_embedding = embedding

        audit.track_action(
            action=AuditAction.CREATE,
            entity_type="Entity",
            entity_id=entity.id,
            entity_name=entity.name,
            changes={
                "name": entity.name,
                "slug": entity.slug,
                "entity_type": entity_type.name,
                "country": entity.country,
                "external_id": entity.external_id,
                "parent_id": str(entity.parent_id) if entity.parent_id else None,
            },
        )

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

    # Load ALL entities of this type in a single query to avoid N+1
    all_entities_result = await session.execute(
        select(Entity).where(
            and_(
                Entity.entity_type_id == entity_type.id,
                Entity.is_active.is_(True)
            )
        ).order_by(Entity.name)
    )
    all_entities = list(all_entities_result.scalars().all())

    # Build lookup maps for efficient tree construction
    entities_by_id: Dict[UUID, Entity] = {e.id: e for e in all_entities}
    children_by_parent: Dict[Optional[UUID], List[Entity]] = {}

    for entity in all_entities:
        parent_key = entity.parent_id
        if parent_key not in children_by_parent:
            children_by_parent[parent_key] = []
        children_by_parent[parent_key].append(entity)

    def build_tree_from_cache(parent_id: Optional[UUID], depth: int) -> List[Dict[str, Any]]:
        """Build tree from cached entities - no database queries."""
        if depth > max_depth:
            return []

        children_entities = children_by_parent.get(parent_id, [])
        tree = []

        for entity in children_entities:
            children = build_tree_from_cache(entity.id, depth + 1)
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

    tree = build_tree_from_cache(root_id, 0)

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


@router.get("/filter-options/location", response_model=LocationFilterOptionsResponse)
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

    return LocationFilterOptionsResponse(
        countries=countries,
        admin_level_1=admin_level_1_values,
        admin_level_2=admin_level_2_values,
    )


@router.get("/filter-options/attributes", response_model=AttributeFilterOptionsResponse)
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
            filterable_attributes.append(FilterableAttribute(
                key=key,
                title=prop.get("title", key),
                description=prop.get("description"),
                type=attr_type,
                format=prop.get("format"),
            ))

    attribute_values = None

    # If specific attribute requested, get distinct values
    if attribute_key and attribute_key in properties:
        # Query distinct values from core_attributes JSONB
        # Use labeled column so ORDER BY matches SELECT DISTINCT exactly
        attr_value = Entity.core_attributes[attribute_key].astext.label("attr_value")
        values_query = (
            select(attr_value)
            .where(
                Entity.entity_type_id == entity_type.id,
                Entity.core_attributes[attribute_key].astext.isnot(None),
                Entity.core_attributes[attribute_key].astext != "",
            )
            .distinct()
            .order_by(attr_value)
            .limit(100)  # Limit to prevent huge lists
        )
        values_result = await session.execute(values_query)
        distinct_values = [row[0] for row in values_result.fetchall() if row[0]]
        attribute_values = {attribute_key: distinct_values}

    return AttributeFilterOptionsResponse(
        entity_type_slug=entity_type_slug,
        entity_type_name=entity_type.name,
        attributes=filterable_attributes,
        attribute_values=attribute_values,
    )


@router.get("/geojson", response_model=GeoJSONFeatureCollection)
async def get_entities_geojson(
    entity_type_slug: Optional[str] = Query(default=None, description="Filter by entity type slug"),
    country: Optional[str] = Query(default=None, description="Filter by country code"),
    admin_level_1: Optional[str] = Query(default=None, description="Filter by admin level 1"),
    admin_level_2: Optional[str] = Query(default=None, description="Filter by admin level 2"),
    search: Optional[str] = Query(default=None, description="Search in name"),
    include_geometry: bool = Query(default=True, description="Include polygon/boundary geometries"),
    limit: int = Query(default=50000, ge=1, le=100000, description="Max entities to return"),
    session: AsyncSession = Depends(get_session),
):
    """Get entities as GeoJSON FeatureCollection for map display.

    Returns entities with valid geo data:
    - Point geometry from latitude/longitude fields
    - Complex geometry (Polygon, MultiPolygon, etc.) from geometry field

    Optimized for large datasets - supports clustering for points.
    """
    # Build base query - entities with any geo data (lat/lng OR geometry)
    query = select(
        Entity.id,
        Entity.name,
        Entity.slug,
        Entity.latitude,
        Entity.longitude,
        Entity.geometry,
        Entity.entity_type_id,
        Entity.external_id,
        Entity.country,
        Entity.admin_level_1,
        Entity.admin_level_2,
    ).where(
        or_(
            and_(Entity.latitude.isnot(None), Entity.longitude.isnot(None)),
            Entity.geometry.isnot(None),
        ),
        Entity.is_active.is_(True),
    )

    # Apply filters
    if entity_type_slug:
        subq = select(EntityType.id).where(EntityType.slug == entity_type_slug)
        query = query.where(Entity.entity_type_id.in_(subq))

    if country:
        query = query.where(Entity.country == country.upper())

    if admin_level_1:
        query = query.where(Entity.admin_level_1 == admin_level_1)

    if admin_level_2:
        query = query.where(Entity.admin_level_2 == admin_level_2)

    if search:
        # Use parameterized query pattern to prevent SQL injection
        search_pattern = f"%{search.replace('%', '\\%').replace('_', '\\_')}%"
        query = query.where(Entity.name.ilike(search_pattern, escape='\\'))

    # Limit results
    query = query.limit(limit)

    result = await session.execute(query)
    rows = result.fetchall()

    # Count total without any geo data
    count_without_query = select(func.count()).select_from(Entity).where(
        and_(
            or_(Entity.latitude.is_(None), Entity.longitude.is_(None)),
            Entity.geometry.is_(None),
        ),
        Entity.is_active.is_(True),
    )
    if entity_type_slug:
        subq = select(EntityType.id).where(EntityType.slug == entity_type_slug)
        count_without_query = count_without_query.where(Entity.entity_type_id.in_(subq))
    total_without = (await session.execute(count_without_query)).scalar() or 0

    # Get entity type info for icons/colors
    entity_type_ids = list(set(row.entity_type_id for row in rows))
    entity_types_map = {}
    if entity_type_ids:
        et_result = await session.execute(
            select(EntityType).where(EntityType.id.in_(entity_type_ids))
        )
        entity_types_map = {et.id: et for et in et_result.scalars().all()}

    # Build GeoJSON features
    features = []
    for row in rows:
        et = entity_types_map.get(row.entity_type_id)

        # Determine geometry: use stored geometry if available, else create Point
        if include_geometry and row.geometry:
            geometry = row.geometry
        elif row.latitude is not None and row.longitude is not None:
            geometry = {
                "type": "Point",
                "coordinates": [row.longitude, row.latitude],
            }
        else:
            # Should not happen due to query filter, but skip just in case
            continue

        # Determine geometry type for frontend styling
        geometry_type = geometry.get("type", "Point") if isinstance(geometry, dict) else "Point"

        features.append({
            "type": "Feature",
            "geometry": geometry,
            "properties": {
                "id": str(row.id),
                "name": row.name,
                "slug": row.slug,
                "external_id": row.external_id,
                "entity_type_slug": et.slug if et else None,
                "entity_type_name": et.name if et else None,
                "icon": et.icon if et else "mdi-map-marker",
                "color": et.color if et else "#1976D2",
                "country": row.country,
                "admin_level_1": row.admin_level_1,
                "admin_level_2": row.admin_level_2,
                "geometry_type": geometry_type,
            },
        })

    return GeoJSONFeatureCollection(
        type="FeatureCollection",
        features=features,
        total_with_coords=len(features),
        total_without_coords=total_without,
    )


# ============================================================================
# Dynamic Entity Routes (MUST be AFTER static routes like /filter-options/*)
# ============================================================================


async def _build_entity_response(
    entity: Entity,
    entity_type: Optional[EntityType],
    session: AsyncSession,
) -> EntityResponse:
    """
    Build a complete EntityResponse with counts, parent info, and external source.

    This helper function centralizes the response building logic to avoid
    code duplication between get_entity and get_entity_by_slug endpoints.
    """
    from sqlalchemy.orm import selectinload

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
    parent_slug = None
    if entity.parent_id:
        parent = await session.get(Entity, entity.parent_id)
        if parent:
            parent_name = parent.name
            parent_slug = parent.slug

    # Get external source info (for API-imported entities)
    external_source_name = None
    if entity.api_configuration_id:
        from app.models.api_configuration import APIConfiguration
        api_result = await session.execute(
            select(APIConfiguration)
            .options(selectinload(APIConfiguration.data_source))
            .where(APIConfiguration.id == entity.api_configuration_id)
        )
        api_config = api_result.scalar_one_or_none()
        if api_config and api_config.data_source:
            external_source_name = api_config.data_source.name

    response = EntityResponse.model_validate(entity)
    response.entity_type_name = entity_type.name if entity_type else None
    response.entity_type_slug = entity_type.slug if entity_type else None
    response.parent_name = parent_name
    response.parent_slug = parent_slug
    response.facet_count = facet_count
    response.relation_count = relation_count
    response.children_count = children_count
    response.external_source_name = external_source_name

    return response


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
    return await _build_entity_response(entity, entity_type, session)


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

    return await _build_entity_response(entity, entity_type, session)


@router.get("/{entity_id}/children", response_model=EntityListResponse)
async def get_entity_children(
    entity_id: UUID,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """Get direct children of an entity."""
    from sqlalchemy.orm import selectinload

    entity = await session.get(Entity, entity_id)
    if not entity:
        raise NotFoundError("Entity", str(entity_id))

    # Eagerly load created_by and owner to avoid lazy loading
    query = select(Entity).options(
        selectinload(Entity.created_by),
        selectinload(Entity.owner),
    ).where(Entity.parent_id == entity_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Paginate
    query = query.order_by(Entity.name).offset((page - 1) * per_page).limit(per_page)
    result = await session.execute(query)
    children = result.scalars().all()

    # Batch load entity types to avoid N+1
    entity_type_ids = list(set(c.entity_type_id for c in children))
    entity_types_map = {}
    if entity_type_ids:
        entity_types_result = await session.execute(
            select(EntityType).where(EntityType.id.in_(entity_type_ids))
        )
        entity_types_map = {et.id: et for et in entity_types_result.scalars().all()}

    items = []
    for child in children:
        et = entity_types_map.get(child.entity_type_id)
        item = EntityResponse.model_validate(child)
        item.entity_type_name = et.name if et else None
        item.entity_type_slug = et.slug if et else None
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
    request: Request,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
):
    """Update an entity."""
    entity = await session.get(Entity, entity_id)
    if not entity:
        raise NotFoundError("Entity", str(entity_id))

    # Capture old state for audit
    old_data = {
        "name": entity.name,
        "slug": entity.slug,
        "country": entity.country,
        "is_active": entity.is_active,
        "parent_id": str(entity.parent_id) if entity.parent_id else None,
    }

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

    # If name changes, update normalized name and embedding
    if "name" in update_data:
        # Get country from update or existing entity for consistent normalization
        country = update_data.get("country", entity.country) or "DE"
        update_data["name_normalized"] = normalize_entity_name(update_data["name"], country=country)

        # Regenerate embedding for new name
        from app.utils.similarity import generate_embedding
        embedding = await generate_embedding(update_data["name"])
        if embedding:
            update_data["name_embedding"] = embedding

    async with AuditContext(session, current_user, request) as audit:
        for field, value in update_data.items():
            setattr(entity, field, value)

        # Capture new state
        new_data = {
            "name": entity.name,
            "slug": entity.slug,
            "country": entity.country,
            "is_active": entity.is_active,
            "parent_id": str(entity.parent_id) if entity.parent_id else None,
        }

        audit.track_update(entity, old_data, new_data)

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
    request: Request,
    force: bool = Query(default=False, description="Force delete with all facets and relations"),
    current_user: User = Depends(require_editor),
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

            # Audit log for cascade delete
            async with AuditContext(session, current_user, request) as audit:
                audit.track_action(
                    action=AuditAction.DELETE,
                    entity_type="Entity",
                    entity_id=entity_id,
                    entity_name=entity_name,
                    changes={
                        "deleted": True,
                        "force": True,
                        "cascade_deleted_entities": len(all_entity_ids),
                        "children_count": children_count,
                        "facet_count": facet_count,
                    },
                )
                await session.commit()
    else:
        # Simple delete without cascade
        async with AuditContext(session, current_user, request) as audit:
            audit.track_action(
                action=AuditAction.DELETE,
                entity_type="Entity",
                entity_id=entity_id,
                entity_name=entity_name,
                changes={
                    "deleted": True,
                    "force": False,
                },
            )
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


@router.get("/{entity_id}/sources")
async def get_entity_sources(
    entity_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get data sources linked to an entity.

    Finds DataSources via two paths:
    1. Direct link: entity_id in DataSource.extra_data->>'entity_ids' array
       OR legacy: DataSource.extra_data->>'entity_id' = entity_id
    2. Indirect: Entity -> FacetValues -> Documents -> DataSources

    Returns all unique DataSources for this entity.
    """
    from sqlalchemy import or_

    # Verify entity exists
    entity = await session.get(Entity, entity_id)
    if not entity:
        raise NotFoundError("Entity", str(entity_id))

    all_source_ids = set()
    direct_link_source_ids = set()

    # Path 1: Direct link via extra_data
    # Support both N:M (entity_ids array) and legacy (entity_id string)
    entity_id_str = str(entity_id)

    # Query for legacy entity_id (single value)
    legacy_query = (
        select(DataSource.id)
        .where(DataSource.extra_data["entity_id"].astext == entity_id_str)
    )
    legacy_result = await session.execute(legacy_query)
    for row in legacy_result.fetchall():
        all_source_ids.add(row[0])
        direct_link_source_ids.add(row[0])

    # Query for N:M entity_ids (array) - check if entity_id is in the array
    # Use JSONB contains operator
    array_query = (
        select(DataSource.id)
        .where(DataSource.extra_data["entity_ids"].contains([entity_id_str]))
    )
    array_result = await session.execute(array_query)
    for row in array_result.fetchall():
        all_source_ids.add(row[0])
        direct_link_source_ids.add(row[0])

    # Path 2: Via FacetValues -> Documents -> DataSources
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

    if document_ids:
        docs_query = (
            select(Document.source_id)
            .where(
                Document.id.in_(document_ids),
                Document.source_id.isnot(None)
            )
            .distinct()
        )
        docs_result = await session.execute(docs_query)
        for row in docs_result.fetchall():
            all_source_ids.add(row[0])

    if not all_source_ids:
        return {
            "entity_id": str(entity_id),
            "entity_name": entity.name,
            "sources": [],
            "total": 0,
        }

    # Load DataSources
    sources_query = select(DataSource).where(DataSource.id.in_(all_source_ids))
    sources_result = await session.execute(sources_query)
    sources = sources_result.scalars().all()

    # Count documents per source (only for sources that have documents)
    doc_counts_map = {}
    if document_ids:
        doc_counts_query = (
            select(Document.source_id, func.count(Document.id))
            .where(
                Document.id.in_(document_ids),
                Document.source_id.in_(all_source_ids)
            )
            .group_by(Document.source_id)
        )
        doc_counts_result = await session.execute(doc_counts_query)
        doc_counts_map = dict(doc_counts_result.fetchall())

    # Build response
    source_list = []
    for source in sources:
        # Check if this is a direct link (from direct_link_source_ids set)
        is_direct_link = source.id in direct_link_source_ids

        source_list.append({
            "id": str(source.id),
            "name": source.name,
            "base_url": source.base_url,
            "source_type": source.source_type,
            "status": source.status,
            "document_count": doc_counts_map.get(source.id, 0),
            "is_direct_link": is_direct_link,  # Mark directly linked sources (N:M)
            "last_crawl": source.last_crawl.isoformat() if source.last_crawl else None,
            "extra_data": source.extra_data,
            "crawl_config": source.crawl_config,
        })

    # Sort: directly linked sources first, then by document count
    source_list.sort(key=lambda x: (not x.get("is_direct_link", False), -x["document_count"]))

    return {
        "entity_id": str(entity_id),
        "entity_name": entity.name,
        "sources": source_list,
        "total": len(source_list),
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

    # Check if entity has an API configuration source
    if not entity.api_configuration_id:
        return {
            "entity_id": str(entity_id),
            "entity_name": entity.name,
            "has_external_data": False,
            "message": "Entity was not created from an external API",
        }

    # Get the APIConfiguration with eager-loaded data_source to avoid async lazy-loading
    from sqlalchemy.orm import selectinload
    config_result = await session.execute(
        select(APIConfiguration)
        .options(selectinload(APIConfiguration.data_source))
        .where(APIConfiguration.id == entity.api_configuration_id)
    )
    config = config_result.scalar_one_or_none()

    # Find the sync record for this entity
    sync_record_query = select(SyncRecord).where(SyncRecord.entity_id == entity_id)
    result = await session.execute(sync_record_query)
    sync_record = result.scalar()

    # Build external source info
    external_source = None
    if config:
        external_source = {
            "id": str(config.id),
            "name": config.data_source.name if config.data_source else None,
            "api_type": config.api_type,
            "api_base_url": config.get_full_url() if config else None,
        }

    if not sync_record:
        return {
            "entity_id": str(entity_id),
            "entity_name": entity.name,
            "has_external_data": False,
            "external_source": external_source,
            "message": "No sync record found for this entity",
        }

    return {
        "entity_id": str(entity_id),
        "entity_name": entity.name,
        "has_external_data": True,
        "external_source": external_source,
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
