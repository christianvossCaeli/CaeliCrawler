"""Crawl operations for Smart Query Service."""

from typing import Any, Dict, List, Set
from uuid import UUID

import structlog
from sqlalchemy import select, or_, func, cast, Float
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DataSource, DataSourceCategory, Category, Entity
from services.smart_query.constants import TAG_ALIASES

logger = structlog.get_logger()


def expand_tag(tag: str) -> List[str]:
    """Expand a tag to include aliases."""
    tag_lower = tag.lower().strip()
    if tag_lower in TAG_ALIASES:
        return TAG_ALIASES[tag_lower]
    return [tag_lower]


async def find_matching_data_sources(
    session: AsyncSession,
    filter_criteria: Dict[str, Any],
    limit: int = 1000,
) -> List[DataSource]:
    """
    Find data sources matching filter criteria.

    Supports multiple strategies:
    1. By explicit category_slug/category_id
    2. By tags (e.g., ["nrw", "kommunal"])
    3. By related category keywords (finds categories matching keywords, then their sources)

    Args:
        session: Database session
        filter_criteria: Dict with optional keys:
            - category_slug: Exact category slug
            - category_id: Exact category ID
            - tags: List of tags to match (OR logic)
            - category_keywords: Keywords to search in category names/descriptions
            - admin_level_1: Geographic region (will be converted to tag search)
        limit: Maximum number of sources to return

    Returns:
        List of matching DataSources
    """
    category_slug = filter_criteria.get("category_slug")
    category_id = filter_criteria.get("category_id")
    tags = filter_criteria.get("tags", [])
    category_keywords = filter_criteria.get("category_keywords", [])
    admin_level_1 = filter_criteria.get("admin_level_1")

    # Convert admin_level_1 to tags
    if admin_level_1 and not tags:
        tags = expand_tag(admin_level_1)

    found_source_ids: Set[UUID] = set()
    all_sources: List[DataSource] = []

    logger.info(
        "Finding matching data sources",
        category_slug=category_slug,
        category_id=category_id,
        tags=tags,
        category_keywords=category_keywords,
        admin_level_1=admin_level_1,
    )

    # Strategy 1: Find by explicit category
    if category_slug or category_id:
        if category_slug:
            cat_result = await session.execute(
                select(Category).where(Category.slug == category_slug)
            )
            category = cat_result.scalar_one_or_none()
            if category:
                category_id = category.id

        if category_id:
            query = (
                select(DataSource)
                .join(DataSourceCategory, DataSource.id == DataSourceCategory.data_source_id)
                .where(DataSourceCategory.category_id == category_id)
            )
            result = await session.execute(query.limit(limit))
            for source in result.scalars().all():
                if source.id not in found_source_ids:
                    found_source_ids.add(source.id)
                    all_sources.append(source)

    # Strategy 2: Find by tags
    if tags:
        # Expand all tags to include aliases
        expanded_tags = []
        for tag in tags:
            expanded_tags.extend(expand_tag(tag))
        expanded_tags = list(set(expanded_tags))  # Remove duplicates

        # Use PostgreSQL JSONB overlap operator @>
        # Find sources where tags array contains any of the search tags
        tag_conditions = []
        for tag in expanded_tags:
            # Check if tag is in the JSONB array
            tag_conditions.append(
                DataSource.tags.contains([tag])
            )

        if tag_conditions:
            query = select(DataSource).where(or_(*tag_conditions))
            result = await session.execute(query.limit(limit))
            for source in result.scalars().all():
                if source.id not in found_source_ids:
                    found_source_ids.add(source.id)
                    all_sources.append(source)

    # Strategy 3: Find by category keywords (Option C - use existing categories)
    if category_keywords or (admin_level_1 and not all_sources):
        # Search for categories that match the keywords
        keywords = category_keywords or [admin_level_1]
        cat_conditions = []
        for keyword in keywords:
            cat_conditions.append(Category.name.ilike(f"%{keyword}%"))
            cat_conditions.append(Category.description.ilike(f"%{keyword}%"))
            cat_conditions.append(Category.purpose.ilike(f"%{keyword}%"))

        if cat_conditions:
            # Find matching categories
            cat_query = select(Category.id).where(or_(*cat_conditions))
            cat_result = await session.execute(cat_query)
            matching_category_ids = [row[0] for row in cat_result.fetchall()]

            if matching_category_ids:
                # Get sources from these categories
                query = (
                    select(DataSource)
                    .join(DataSourceCategory, DataSource.id == DataSourceCategory.data_source_id)
                    .where(DataSourceCategory.category_id.in_(matching_category_ids))
                )
                result = await session.execute(query.limit(limit))
                for source in result.scalars().all():
                    if source.id not in found_source_ids:
                        found_source_ids.add(source.id)
                        all_sources.append(source)

    logger.info(
        "Found matching data sources",
        count=len(all_sources),
        strategies_used={
            "by_category": bool(category_slug or category_id),
            "by_tags": bool(tags),
            "by_keywords": bool(category_keywords) or (bool(admin_level_1) and len(all_sources) == 0),
        },
    )

    return all_sources[:limit]


async def find_sources_for_crawl(
    session: AsyncSession,
    crawl_data: Dict[str, Any],
    limit: int = 1000,
) -> List[DataSource]:
    """Find data sources matching crawl criteria.

    Supports multiple filter strategies that can be combined:

    1. source_ids: Explicit list of DataSource IDs
    2. category_slug: Filter by category
    3. search: Name search
    4. tags: Filter by tags (entity_type, region, etc.) - uses AND logic
    5. entity_type: Filter by entity type tag (e.g., "territorial-entity", "windpark")
    6. admin_level_1: Filter by region/Bundesland (e.g., "Bayern", "NRW")
    7. entity_filters: Advanced entity-based filtering

    Multiple filters are combined with AND logic.

    Examples:
        # All sources in Bayern
        {"admin_level_1": "Bayern"}

        # All Gemeinden in Bayern
        {"admin_level_1": "Bayern", "tags": ["kommunal"]}

        # All territorial entities in NRW for a specific category
        {"entity_type": "territorial-entity", "admin_level_1": "NRW",
         "category_slug": "kommunale-news-windenergie"}
    """
    source_ids = crawl_data.get("source_ids", [])
    category_slug = crawl_data.get("category_slug")
    search = crawl_data.get("search")

    # New generic filters
    tags = crawl_data.get("tags", [])
    entity_type = crawl_data.get("entity_type")
    admin_level_1 = crawl_data.get("admin_level_1")
    entity_filters = crawl_data.get("entity_filters", {})

    # Build base query
    query = select(DataSource).where(DataSource.status != "ERROR")
    conditions = []

    # Strategy 1: Explicit source IDs (highest priority, returns immediately)
    if source_ids:
        query = query.where(DataSource.id.in_([UUID(sid) for sid in source_ids]))
        result = await session.execute(query.limit(limit))
        return list(result.scalars().all())

    # Strategy 2: Category filter
    if category_slug:
        cat_result = await session.execute(
            select(Category).where(Category.slug == category_slug)
        )
        category = cat_result.scalar_one_or_none()
        if category:
            # Need to join with category table
            query = (
                query
                .join(DataSourceCategory, DataSource.id == DataSourceCategory.data_source_id)
                .where(DataSourceCategory.category_id == category.id)
            )

    # Strategy 3: Name search
    if search:
        conditions.append(DataSource.name.ilike(f"%{search}%"))

    # Strategy 4: Entity type filter (tag-based)
    if entity_type:
        entity_type_slug = entity_type.lower().replace(" ", "-")
        conditions.append(DataSource.tags.contains([entity_type_slug]))

    # Strategy 5: Admin level 1 / Region filter
    if admin_level_1:
        # Expand to include aliases (e.g., "Bayern" -> ["bayern", "by"])
        region_tags = expand_tag(admin_level_1)
        # Any of the region tags must match
        region_conditions = [DataSource.tags.contains([tag]) for tag in region_tags]
        if region_conditions:
            conditions.append(or_(*region_conditions))

    # Strategy 6: Additional tags (AND logic - all must be present)
    if tags:
        for tag in tags:
            expanded = expand_tag(tag)
            # For each tag group, any alias can match
            tag_conditions = [DataSource.tags.contains([t]) for t in expanded]
            if tag_conditions:
                conditions.append(or_(*tag_conditions))

    # Strategy 7: Advanced entity filters (via Entity join)
    entity_id_filter = None
    if entity_filters:
        # Build entity query for filtering
        entity_conditions = []

        # Filter by parent entity name (for hierarchical filtering)
        parent_name = entity_filters.get("parent_name")
        if parent_name:
            # Find parent entity first
            parent_query = select(Entity.id).where(
                Entity.name.ilike(f"%{parent_name}%")
            )
            parent_result = await session.execute(parent_query)
            parent_ids = [row[0] for row in parent_result.fetchall()]
            if parent_ids:
                entity_conditions.append(Entity.parent_id.in_(parent_ids))

        # Filter by hierarchy level
        hierarchy_level = entity_filters.get("hierarchy_level")
        if hierarchy_level is not None:
            entity_conditions.append(Entity.hierarchy_level == hierarchy_level)

        # Filter by core_attributes (e.g., population, area)
        core_attr_filters = entity_filters.get("core_attributes", {})
        for attr_name, attr_filter in core_attr_filters.items():
            # Support operators: lt, lte, gt, gte, eq
            json_path = Entity.core_attributes[attr_name].astext
            if isinstance(attr_filter, dict):
                for op, value in attr_filter.items():
                    if op == "lt":
                        entity_conditions.append(cast(json_path, Float) < value)
                    elif op == "lte":
                        entity_conditions.append(cast(json_path, Float) <= value)
                    elif op == "gt":
                        entity_conditions.append(cast(json_path, Float) > value)
                    elif op == "gte":
                        entity_conditions.append(cast(json_path, Float) >= value)
                    elif op == "eq":
                        entity_conditions.append(cast(json_path, Float) == value)
            else:
                # Direct value = equality
                entity_conditions.append(cast(json_path, Float) == attr_filter)

        # If we have entity conditions, get matching entity IDs
        if entity_conditions:
            entity_query = select(Entity.id).where(*entity_conditions)
            entity_result = await session.execute(entity_query)
            matching_entity_ids = [str(row[0]) for row in entity_result.fetchall()]

            if matching_entity_ids:
                entity_id_filter = matching_entity_ids
                logger.info(f"Entity filter matched {len(matching_entity_ids)} entities")
            else:
                # No matching entities = no results
                logger.info("Entity filter matched 0 entities")
                return []

    # Apply entity_id filter via extra_data JSONB
    if entity_id_filter:
        # Filter DataSources where extra_data->>'entity_id' is in our list
        entity_id_conditions = [
            DataSource.extra_data["entity_id"].astext == eid
            for eid in entity_id_filter[:1000]  # Limit to prevent huge OR
        ]
        if entity_id_conditions:
            conditions.append(or_(*entity_id_conditions))

    # Apply all conditions
    if conditions:
        query = query.where(*conditions)

    logger.info(
        "Finding sources for crawl",
        category_slug=category_slug,
        entity_type=entity_type,
        admin_level_1=admin_level_1,
        tags=tags,
        search=search,
        entity_filters=entity_filters,
    )

    result = await session.execute(query.limit(limit))
    sources = list(result.scalars().all())

    logger.info(f"Found {len(sources)} sources matching criteria")

    return sources


async def start_crawl_jobs(
    session: AsyncSession,
    sources: List[DataSource],
    force: bool = False,
) -> List[str]:
    """Start crawl jobs for a list of data sources.

    Args:
        session: Database session
        sources: List of DataSource objects to crawl
        force: If True, force crawl even if recently crawled

    Returns:
        List of created job IDs
    """
    from workers.crawl_tasks import create_crawl_job

    job_ids: List[str] = []

    for source in sources:
        # Get all categories for this source
        cat_result = await session.execute(
            select(DataSourceCategory.category_id)
            .where(DataSourceCategory.data_source_id == source.id)
        )
        category_ids = [row[0] for row in cat_result.fetchall()]

        # Also include legacy category_id if set
        if source.category_id and source.category_id not in category_ids:
            category_ids.append(source.category_id)

        if not category_ids:
            logger.warning(
                "Source has no categories, skipping",
                source_id=str(source.id),
                source_name=source.name,
            )
            continue

        # Create crawl job for each category
        for cat_id in category_ids:
            try:
                task = create_crawl_job.delay(str(source.id), str(cat_id))
                job_ids.append(str(task.id))
            except Exception as e:
                logger.error(
                    "Failed to create crawl job",
                    source_id=str(source.id),
                    category_id=str(cat_id),
                    error=str(e),
                )

    return job_ids


async def execute_crawl_command(
    session: AsyncSession,
    crawl_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute START_CRAWL operation - starts crawls for matching sources."""
    from workers.crawl_tasks import create_crawl_job

    result = {
        "success": False,
        "message": "",
        "job_count": 0,
        "source_count": 0,
        "sources": [],
        "warnings": [],
    }

    try:
        # Find matching sources
        sources = await find_sources_for_crawl(session, crawl_data)

        if not sources:
            result["message"] = "Keine passenden DataSources gefunden"
            return result

        result["source_count"] = len(sources)

        # Get categories for each source
        include_all_categories = crawl_data.get("include_all_categories", True)
        job_count = 0

        for source in sources:
            # Get all categories for this source
            if include_all_categories:
                cat_result = await session.execute(
                    select(DataSourceCategory.category_id)
                    .where(DataSourceCategory.data_source_id == source.id)
                )
                category_ids = [row[0] for row in cat_result.fetchall()]

                # Also include legacy category_id if set
                if source.category_id and source.category_id not in category_ids:
                    category_ids.append(source.category_id)
            else:
                # Only primary category
                category_ids = [source.category_id] if source.category_id else []

            if not category_ids:
                result["warnings"].append(f"Source '{source.name}' hat keine Kategorie")
                continue

            # Create crawl job for each category
            for cat_id in category_ids:
                try:
                    create_crawl_job.delay(str(source.id), str(cat_id))
                    job_count += 1
                except Exception as e:
                    logger.error(
                        "Failed to create crawl job",
                        source_id=str(source.id),
                        category_id=str(cat_id),
                        error=str(e),
                    )

            result["sources"].append({
                "id": str(source.id),
                "name": source.name,
                "category_count": len(category_ids),
            })

        result["success"] = True
        result["job_count"] = job_count
        result["message"] = f"{job_count} Crawl-Jobs für {len(sources)} Sources erstellt"

        return result

    except Exception as e:
        logger.error("Crawl command failed", error=str(e), exc_info=True)
        result["message"] = f"Fehler: {str(e)}"
        return result
