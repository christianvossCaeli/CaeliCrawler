"""Crawl operations for Smart Query Service."""

from typing import Any, Dict, List, Set
from uuid import UUID

import structlog
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DataSource, DataSourceCategory, Category

logger = structlog.get_logger()


# Tag aliases for common geographic regions
TAG_ALIASES = {
    # German Bundesländer
    "nordrhein-westfalen": ["nrw", "nordrhein-westfalen"],
    "nrw": ["nrw", "nordrhein-westfalen"],
    "bayern": ["bayern", "by"],
    "baden-württemberg": ["baden-württemberg", "bw"],
    "niedersachsen": ["niedersachsen", "ni"],
    "hessen": ["hessen", "he"],
    "sachsen": ["sachsen", "sn"],
    "rheinland-pfalz": ["rheinland-pfalz", "rlp"],
    "berlin": ["berlin", "be"],
    "schleswig-holstein": ["schleswig-holstein", "sh"],
    "brandenburg": ["brandenburg", "bb"],
    "sachsen-anhalt": ["sachsen-anhalt", "st"],
    "thüringen": ["thüringen", "th"],
    "hamburg": ["hamburg", "hh"],
    "mecklenburg-vorpommern": ["mecklenburg-vorpommern", "mv"],
    "saarland": ["saarland", "sl"],
    "bremen": ["bremen", "hb"],
    # Countries
    "deutschland": ["deutschland", "de", "germany"],
    "österreich": ["österreich", "at", "austria"],
    "schweiz": ["schweiz", "ch", "switzerland"],
    # Source types
    "kommunal": ["kommunal", "gemeinde", "stadt", "kommune"],
    "landkreis": ["landkreis", "kreis"],
}


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
    limit: int = 100,
) -> List[DataSource]:
    """Find data sources matching crawl criteria."""
    filter_type = crawl_data.get("filter_type", "category")
    category_slug = crawl_data.get("category_slug")
    source_ids = crawl_data.get("source_ids", [])
    search = crawl_data.get("search")

    query = select(DataSource).where(DataSource.status != "ERROR")

    if source_ids:
        # Explicit source IDs
        query = query.where(DataSource.id.in_([UUID(sid) for sid in source_ids]))

    elif filter_type == "category" and category_slug:
        # Filter by category
        cat_result = await session.execute(
            select(Category).where(Category.slug == category_slug)
        )
        category = cat_result.scalar_one_or_none()
        if category:
            query = (
                query
                .join(DataSourceCategory, DataSource.id == DataSourceCategory.data_source_id)
                .where(DataSourceCategory.category_id == category.id)
            )

    elif filter_type == "search" and search:
        # Search by name
        query = query.where(DataSource.name.ilike(f"%{search}%"))

    result = await session.execute(query.limit(limit))
    return list(result.scalars().all())


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
