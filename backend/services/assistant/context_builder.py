"""Assistant Service - Context Building Logic.

This module handles building rich context data for AI processing, including:
- Entity data collection with facets and relations
- PySIS process data enrichment
- Location and attribute data aggregation

Exports:
    - build_entity_context: Build complete entity context
    - build_facet_summary: Summarize facets by type
    - build_pysis_context: Extract PySIS data for entity
"""

import json
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Entity,
    EntityRelation,
    FacetType,
    FacetValue,
)
from app.models.pysis import PySisProcess

logger = structlog.get_logger()


async def build_entity_context(
    db: AsyncSession,
    entity_id: UUID,
    include_facets: bool = True,
    include_pysis: bool = True,
    include_relations: bool = False,
    facet_limit: int = 30
) -> Dict[str, Any]:
    """Build comprehensive context data for an entity.

    Args:
        db: Database session
        entity_id: Entity UUID
        include_facets: Include facet values
        include_pysis: Include PySIS data
        include_relations: Include relation count
        facet_limit: Maximum number of facets to load

    Returns:
        Dict with complete entity context

    Raises:
        ValueError: If entity not found
    """
    # Load entity
    entity_result = await db.execute(
        select(Entity)
        .options(selectinload(Entity.entity_type))
        .where(Entity.id == entity_id)
    )
    entity = entity_result.scalar_one_or_none()

    if not entity:
        raise ValueError(f"Entity {entity_id} not found")

    # Build base context
    context = {
        "id": str(entity.id),
        "name": entity.name,
        "slug": entity.slug,
        "type": entity.entity_type.name if entity.entity_type else "Unbekannt",
        "type_slug": entity.entity_type.slug if entity.entity_type else None,
        "core_attributes": entity.core_attributes or {},
        "location": {
            "country": entity.country,
            "admin_level_1": entity.admin_level_1,
            "admin_level_2": entity.admin_level_2,
        }
    }

    # Include facets if requested
    if include_facets:
        facet_data = await build_facet_summary(db, entity_id, limit=facet_limit)
        context["facets"] = facet_data

    # Include PySIS data if requested
    if include_pysis:
        pysis_data = await build_pysis_context(db, entity_id)
        context["pysis_fields"] = pysis_data

    # Include relation count if requested
    if include_relations:
        relation_count = await count_entity_relations(db, entity_id)
        context["relation_count"] = relation_count

    return context


async def build_facet_summary(
    db: AsyncSession,
    entity_id: UUID,
    limit: int = 30
) -> Dict[str, List[str]]:
    """Build a summary of facets grouped by type.

    Args:
        db: Database session
        entity_id: Entity UUID
        limit: Maximum facets to load

    Returns:
        Dict mapping facet type names to lists of text representations
    """
    # Fetch facets
    facets_result = await db.execute(
        select(FacetValue)
        .options(selectinload(FacetValue.facet_type))
        .where(FacetValue.entity_id == entity_id)
        .where(FacetValue.is_active.is_(True))
        .order_by(FacetValue.created_at.desc())
        .limit(limit)
    )
    facets = facets_result.scalars().all()

    # Group by facet type
    facet_data = {}
    for fv in facets:
        ft_name = fv.facet_type.name if fv.facet_type else "Unbekannt"
        if ft_name not in facet_data:
            facet_data[ft_name] = []

        # Use text representation or truncated value
        text = fv.text_representation or str(fv.value)[:200]
        facet_data[ft_name].append(text)

    return facet_data


async def build_pysis_context(
    db: AsyncSession,
    entity_id: UUID,
    max_field_length: int = 500
) -> Dict[str, str]:
    """Extract PySIS field data for entity.

    Args:
        db: Database session
        entity_id: Entity UUID
        max_field_length: Maximum length for field values

    Returns:
        Dict mapping field internal names to current values
    """
    # Fetch PySIS process
    pysis_result = await db.execute(
        select(PySisProcess)
        .where(PySisProcess.entity_id == entity_id)
        .limit(1)
    )
    pysis_process = pysis_result.scalar_one_or_none()

    pysis_data = {}
    if pysis_process and pysis_process.fields:
        for field in pysis_process.fields:
            if field.current_value:
                # Truncate long values
                value = str(field.current_value)[:max_field_length]
                pysis_data[field.internal_name] = value

    return pysis_data


async def count_entity_relations(
    db: AsyncSession,
    entity_id: UUID
) -> int:
    """Count relations for an entity.

    Args:
        db: Database session
        entity_id: Entity UUID

    Returns:
        Number of relations (both source and target)
    """
    count = await db.scalar(
        select(func.count(EntityRelation.id))
        .where(
            or_(
                EntityRelation.source_entity_id == entity_id,
                EntityRelation.target_entity_id == entity_id
            )
        )
    )
    return count or 0


async def get_facet_counts_by_type(
    db: AsyncSession,
    entity_id: UUID
) -> Dict[str, int]:
    """Get facet counts grouped by type.

    Args:
        db: Database session
        entity_id: Entity UUID

    Returns:
        Dict mapping facet type names to counts
    """
    facet_counts = await db.execute(
        select(FacetType.name, func.count(FacetValue.id))
        .join(FacetValue, FacetType.id == FacetValue.facet_type_id)
        .where(FacetValue.entity_id == entity_id)
        .where(FacetValue.is_active.is_(True))
        .group_by(FacetType.name)
    )

    return dict(facet_counts.all())


async def build_app_summary_context(db: AsyncSession) -> Dict[str, Any]:
    """Build high-level app summary statistics.

    Args:
        db: Database session

    Returns:
        Dict with app-level statistics
    """
    entity_count = await db.scalar(select(func.count(Entity.id)))
    facet_count = await db.scalar(select(func.count(FacetValue.id)))

    return {
        "entity_count": entity_count or 0,
        "facet_count": facet_count or 0,
    }


async def build_entity_summary_for_prompt(
    db: AsyncSession,
    entity_id: UUID
) -> str:
    """Build a text summary of entity for use in AI prompts.

    Args:
        db: Database session
        entity_id: Entity UUID

    Returns:
        Formatted text summary
    """
    context = await build_entity_context(
        db, entity_id,
        include_facets=True,
        include_pysis=True,
        include_relations=True
    )

    # Format as text
    lines = [
        f"Name: {context['name']}",
        f"Typ: {context['type']}",
    ]

    # Add location if available
    location = context.get("location", {})
    if location.get("country"):
        lines.append(f"Land: {location['country']}")
    if location.get("admin_level_1"):
        lines.append(f"Region: {location['admin_level_1']}")

    # Add facet summary
    facets = context.get("facets", {})
    if facets:
        lines.append("\nFacets:")
        for ft_name, values in facets.items():
            lines.append(f"  - {ft_name}: {len(values)} Einträge")

    # Add PySIS summary
    pysis_fields = context.get("pysis_fields", {})
    if pysis_fields:
        lines.append(f"\nPySIS: {len(pysis_fields)} Felder mit Werten")

    # Add relations
    relation_count = context.get("relation_count", 0)
    if relation_count > 0:
        lines.append(f"\nRelationen: {relation_count}")

    return "\n".join(lines)


def prepare_entity_data_for_ai(entity_data: Dict[str, Any]) -> str:
    """Prepare entity data as JSON string for AI processing.

    Args:
        entity_data: Entity context dict

    Returns:
        JSON formatted string
    """
    return json.dumps(entity_data, ensure_ascii=False, indent=2, default=str)
