"""Source Resolver Service for Custom Summaries.

This module resolves relevant data sources for a summary by analyzing:
1. Directly linked categories (trigger_category_id)
2. Directly linked presets (trigger_preset_id)
3. Entity types used in widgets -> mapped to categories
4. Entity types used in widgets -> mapped to API configurations
"""

from dataclasses import dataclass
from typing import List, Set, Union
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Category,
    CategoryEntityType,
    CrawlPreset,
    CustomSummary,
    DataSource,
    EntityType,
)
from app.models.data_source_category import DataSourceCategory
from app.models.api_configuration import APIConfiguration

logger = structlog.get_logger(__name__)


@dataclass
class ResolvedSources:
    """Container for resolved sources from different types."""
    data_sources: List[DataSource]
    external_apis: List[APIConfiguration]

    @property
    def total_count(self) -> int:
        return len(self.data_sources) + len(self.external_apis)

    @property
    def is_empty(self) -> bool:
        return self.total_count == 0

    def get_all_names(self) -> List[str]:
        """Get names of all sources."""
        names = []
        for ds in self.data_sources:
            names.append(ds.name or ds.url)
        for api in self.external_apis:
            api_name = api.data_source.name if api.data_source else f"API {str(api.id)[:8]}"
            names.append(f"API: {api_name}")
        return names


def extract_entity_types_from_summary(summary: CustomSummary) -> Set[str]:
    """
    Extract all entity type slugs from a summary's widgets and config.

    Args:
        summary: The CustomSummary to analyze

    Returns:
        Set of entity type slugs
    """
    entity_types: Set[str] = set()

    # From widgets
    for widget in summary.widgets:
        config = widget.query_config or {}
        if config.get("entity_type"):
            entity_types.add(config["entity_type"])

    # From interpreted_config
    interpreted = summary.interpreted_config or {}
    if interpreted.get("primary_entity_type"):
        entity_types.add(interpreted["primary_entity_type"])

    return entity_types


async def get_sources_for_category(
    session: AsyncSession,
    category_id: UUID,
) -> List[DataSource]:
    """
    Get all active data sources for a category.

    Args:
        session: Database session
        category_id: Category ID

    Returns:
        List of DataSource objects
    """
    result = await session.execute(
        select(DataSource)
        .join(DataSourceCategory, DataSource.id == DataSourceCategory.data_source_id)
        .where(
            DataSourceCategory.category_id == category_id,
            DataSource.is_active == True,
        )
    )
    return list(result.scalars().all())


async def get_sources_for_preset(
    session: AsyncSession,
    preset_id: UUID,
) -> List[DataSource]:
    """
    Get all data sources that match a preset's filter configuration.

    Args:
        session: Database session
        preset_id: CrawlPreset ID

    Returns:
        List of DataSource objects
    """
    preset = await session.get(CrawlPreset, preset_id)
    if not preset:
        return []

    filters = preset.filters or {}

    # Build base query
    query = select(DataSource).where(DataSource.is_active == True)

    # Apply category filter if present
    if filters.get("category_id"):
        query = query.join(
            DataSourceCategory, DataSource.id == DataSourceCategory.data_source_id
        ).where(DataSourceCategory.category_id == UUID(filters["category_id"]))

    # Apply additional filters
    if filters.get("source_type"):
        source_types = filters["source_type"]
        if isinstance(source_types, list):
            query = query.where(DataSource.source_type.in_(source_types))

    if filters.get("admin_level_1"):
        query = query.where(DataSource.admin_level_1 == filters["admin_level_1"])

    if filters.get("country"):
        query = query.where(DataSource.country == filters["country"])

    result = await session.execute(query)
    return list(result.scalars().all())


async def get_categories_for_entity_type(
    session: AsyncSession,
    entity_type_slug: str,
) -> List[Category]:
    """
    Get all categories that use a specific entity type.

    Args:
        session: Database session
        entity_type_slug: Entity type slug (e.g., "municipality")

    Returns:
        List of Category objects
    """
    # First, find the entity type by slug
    entity_type_result = await session.execute(
        select(EntityType).where(EntityType.slug == entity_type_slug)
    )
    entity_type = entity_type_result.scalar_one_or_none()

    if not entity_type:
        logger.warning(
            "entity_type_not_found",
            slug=entity_type_slug,
        )
        return []

    # Find categories that use this entity type
    result = await session.execute(
        select(Category)
        .join(CategoryEntityType, Category.id == CategoryEntityType.category_id)
        .where(
            CategoryEntityType.entity_type_id == entity_type.id,
            Category.is_active == True,
        )
    )
    return list(result.scalars().all())


async def get_external_apis_for_entity_type(
    session: AsyncSession,
    entity_type_slug: str,
) -> List[APIConfiguration]:
    """
    Get all active API configurations that create entities of a given type.

    Args:
        session: Database session
        entity_type_slug: Entity type slug (e.g., "wind_project")

    Returns:
        List of APIConfiguration objects
    """
    result = await session.execute(
        select(APIConfiguration).where(
            APIConfiguration.entity_type_slug == entity_type_slug,
            APIConfiguration.is_active == True,
            APIConfiguration.sync_enabled == True,
        )
    )
    return list(result.scalars().all())


async def resolve_sources_for_summary(
    session: AsyncSession,
    summary: CustomSummary,
) -> List[DataSource]:
    """
    Resolve all relevant data sources for a summary.

    NOTE: This is the legacy function that only returns DataSources.
    Use resolve_all_sources_for_summary for full resolution including external APIs.

    Sources are resolved from:
    1. trigger_category_id -> All sources of this category
    2. trigger_preset_id -> Sources matching preset filters
    3. Widgets -> entity_types -> CategoryEntityType -> Categories -> Sources

    Args:
        session: Database session
        summary: The CustomSummary to resolve sources for

    Returns:
        List of unique DataSource objects
    """
    resolved = await resolve_all_sources_for_summary(session, summary)
    return resolved.data_sources


async def resolve_all_sources_for_summary(
    session: AsyncSession,
    summary: CustomSummary,
) -> ResolvedSources:
    """
    Resolve all relevant sources (DataSources and APIConfigurations) for a summary.

    Sources are resolved from:
    1. trigger_category_id -> All sources of this category
    2. trigger_preset_id -> Sources matching preset filters
    3. Widgets -> entity_types -> CategoryEntityType -> Categories -> Sources
    4. Widgets -> entity_types -> APIConfiguration (by entity_type_slug)

    Args:
        session: Database session
        summary: The CustomSummary to resolve sources for

    Returns:
        ResolvedSources containing both DataSources and APIConfigurations
    """
    source_ids: Set[UUID] = set()
    source_objects: dict[UUID, DataSource] = {}
    api_ids: Set[UUID] = set()
    api_objects: dict[UUID, APIConfiguration] = {}

    logger.info(
        "resolving_sources_for_summary",
        summary_id=str(summary.id),
        summary_name=summary.name,
    )

    # 1. Directly linked category
    if summary.trigger_category_id:
        category_sources = await get_sources_for_category(
            session, summary.trigger_category_id
        )
        for source in category_sources:
            source_ids.add(source.id)
            source_objects[source.id] = source

        logger.debug(
            "sources_from_trigger_category",
            category_id=str(summary.trigger_category_id),
            count=len(category_sources),
        )

    # 2. Directly linked preset
    if summary.trigger_preset_id:
        preset_sources = await get_sources_for_preset(session, summary.trigger_preset_id)
        for source in preset_sources:
            source_ids.add(source.id)
            source_objects[source.id] = source

        logger.debug(
            "sources_from_trigger_preset",
            preset_id=str(summary.trigger_preset_id),
            count=len(preset_sources),
        )

    # 3. Entity types from widgets
    entity_type_slugs = extract_entity_types_from_summary(summary)

    for slug in entity_type_slugs:
        # 3a. Categories -> DataSources
        categories = await get_categories_for_entity_type(session, slug)

        for category in categories:
            category_sources = await get_sources_for_category(session, category.id)
            for source in category_sources:
                source_ids.add(source.id)
                source_objects[source.id] = source

        # 3b. External APIs by entity_type_slug
        external_apis = await get_external_apis_for_entity_type(session, slug)
        for api in external_apis:
            api_ids.add(api.id)
            api_objects[api.id] = api

        logger.debug(
            "sources_from_entity_type",
            entity_type=slug,
            categories_count=len(categories),
            external_apis_count=len(external_apis),
        )

    data_sources = list(source_objects.values())
    external_apis = list(api_objects.values())

    logger.info(
        "source_resolution_complete",
        summary_id=str(summary.id),
        total_data_sources=len(data_sources),
        total_external_apis=len(external_apis),
        entity_types=list(entity_type_slugs),
    )

    return ResolvedSources(
        data_sources=data_sources,
        external_apis=external_apis,
    )


async def get_source_names(sources: List[DataSource]) -> List[str]:
    """
    Get human-readable names for a list of sources.

    Args:
        sources: List of DataSource objects

    Returns:
        List of source names
    """
    return [source.name or source.url for source in sources]
