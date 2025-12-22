"""Validation helpers for referential integrity checks."""

from typing import Any, Dict, List, Set, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def validate_entity_type_slugs(
    session: AsyncSession,
    slugs: List[str],
) -> Tuple[Set[str], Set[str]]:
    """Validate that entity type slugs exist in the database.

    Args:
        session: Database session
        slugs: List of entity type slugs to validate

    Returns:
        Tuple of (valid_slugs, invalid_slugs)
    """
    if not slugs:
        return set(), set()

    from app.models import EntityType

    result = await session.execute(
        select(EntityType.slug).where(EntityType.slug.in_(slugs))
    )
    valid_slugs = {row[0] for row in result.all()}
    invalid_slugs = set(slugs) - valid_slugs

    return valid_slugs, invalid_slugs


async def validate_facet_type_slugs(
    session: AsyncSession,
    slugs: List[str],
) -> Tuple[Set[str], Set[str]]:
    """Validate that facet type slugs exist in the database.

    Args:
        session: Database session
        slugs: List of facet type slugs to validate

    Returns:
        Tuple of (valid_slugs, invalid_slugs)
    """
    if not slugs:
        return set(), set()

    from app.models import FacetType

    result = await session.execute(
        select(FacetType.slug).where(FacetType.slug.in_(slugs))
    )
    valid_slugs = {row[0] for row in result.all()}
    invalid_slugs = set(slugs) - valid_slugs

    return valid_slugs, invalid_slugs


async def validate_facet_config_slugs(
    session: AsyncSession,
    facet_config: List[Dict[str, Any]],
) -> Tuple[Set[str], Set[str]]:
    """Validate facet_type_slug references in facet_config JSONB.

    Args:
        session: Database session
        facet_config: List of facet config dicts with 'facet_type_slug' keys

    Returns:
        Tuple of (valid_slugs, invalid_slugs)
    """
    slugs = [
        fc.get("facet_type_slug")
        for fc in facet_config
        if fc.get("facet_type_slug")
    ]
    return await validate_facet_type_slugs(session, slugs)


async def get_valid_entity_type_slugs(session: AsyncSession) -> Set[str]:
    """Get all valid entity type slugs from the database."""
    from app.models import EntityType

    result = await session.execute(select(EntityType.slug))
    return {row[0] for row in result.all()}


async def get_valid_facet_type_slugs(session: AsyncSession) -> Set[str]:
    """Get all valid facet type slugs from the database."""
    from app.models import FacetType

    result = await session.execute(select(FacetType.slug))
    return {row[0] for row in result.all()}
