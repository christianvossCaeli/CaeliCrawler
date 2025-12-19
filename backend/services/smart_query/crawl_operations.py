"""Crawl operations for Smart Query Service."""

from typing import Any, Dict, List
from uuid import UUID

import structlog
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DataSource, DataSourceCategory, Category, Entity
from .geographic_utils import resolve_geographic_alias

logger = structlog.get_logger()


async def find_matching_data_sources(
    session: AsyncSession,
    geographic_filter: Dict[str, Any],
    limit: int = 1000,
) -> List[DataSource]:
    """Find data sources matching geographic criteria."""
    admin_level_1 = geographic_filter.get("admin_level_1")
    admin_level_1_alias = geographic_filter.get("admin_level_1_alias")
    country = geographic_filter.get("country", "DE")

    if not admin_level_1 and admin_level_1_alias:
        admin_level_1 = resolve_geographic_alias(admin_level_1_alias)
    elif admin_level_1:
        admin_level_1 = resolve_geographic_alias(admin_level_1)

    if not admin_level_1:
        logger.warning("No admin_level_1 filter provided")
        return []

    logger.info(
        "Finding matching data sources",
        admin_level_1=admin_level_1,
        country=country,
    )

    # Strategy 1: Direct match on DataSource.admin_level_1
    direct_query = select(DataSource).where(
        DataSource.admin_level_1 == admin_level_1,
    )
    if country:
        direct_query = direct_query.where(DataSource.country == country)

    direct_result = await session.execute(direct_query.limit(limit))
    direct_matches = list(direct_result.scalars().all())

    # Strategy 2: Fallback via Entity relationship
    entity_query = (
        select(DataSource)
        .join(Entity, DataSource.entity_id == Entity.id)
        .where(Entity.admin_level_1 == admin_level_1)
    )
    if country:
        entity_query = entity_query.where(Entity.country == country)

    entity_result = await session.execute(entity_query.limit(limit))
    entity_matches = list(entity_result.scalars().all())

    # Combine and deduplicate
    all_sources = {ds.id: ds for ds in direct_matches + entity_matches}

    logger.info(
        "Found matching data sources",
        direct_count=len(direct_matches),
        entity_count=len(entity_matches),
        total_unique=len(all_sources),
    )

    return list(all_sources.values())


async def find_sources_for_crawl(
    session: AsyncSession,
    crawl_data: Dict[str, Any],
    limit: int = 100,
) -> List[DataSource]:
    """Find data sources matching crawl criteria."""
    filter_type = crawl_data.get("filter_type", "location")
    location_name = crawl_data.get("location_name")
    admin_level_1 = crawl_data.get("admin_level_1")
    category_slug = crawl_data.get("category_slug")
    source_ids = crawl_data.get("source_ids", [])

    query = select(DataSource).where(DataSource.status != "ERROR")

    if source_ids:
        # Explicit source IDs
        query = query.where(DataSource.id.in_([UUID(sid) for sid in source_ids]))

    elif filter_type == "location" and location_name:
        # Filter by location_name (e.g., "Gummersbach")
        query = query.where(
            or_(
                DataSource.location_name.ilike(f"%{location_name}%"),
                DataSource.name.ilike(f"%{location_name}%"),
            )
        )

    elif filter_type == "location" and admin_level_1:
        # Filter by admin_level_1 (e.g., "Nordrhein-Westfalen")
        resolved = resolve_geographic_alias(admin_level_1)
        query = query.where(DataSource.admin_level_1 == resolved)

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

    elif filter_type == "entity_name":
        # Filter by linked entity name
        entity_name = location_name or crawl_data.get("entity_name")
        if entity_name:
            query = (
                query
                .join(Entity, DataSource.entity_id == Entity.id)
                .where(Entity.name.ilike(f"%{entity_name}%"))
            )

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
