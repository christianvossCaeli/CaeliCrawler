"""Analysis statistics endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import (
    Entity,
    EntityRelation,
    EntityType,
    FacetType,
    FacetValue,
    RelationType,
)

router = APIRouter()


@router.get("/stats")
async def get_analysis_stats(
    entity_type_slug: str | None = Query(default=None),
    category_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """Get overall analysis statistics, optionally filtered by entity type."""
    # Get entity type ID if slug is provided
    entity_type_id = None
    if entity_type_slug:
        et_result = await session.execute(select(EntityType.id).where(EntityType.slug == entity_type_slug))
        entity_type_id = et_result.scalar()

    # Entity counts by type
    et_query = (
        select(EntityType.slug, EntityType.name, func.count(Entity.id).label("count"))
        .outerjoin(Entity, Entity.entity_type_id == EntityType.id)
        .group_by(EntityType.id)
    )

    et_result = await session.execute(et_query)
    entity_counts = {row.slug: {"name": row.name, "count": row.count} for row in et_result.fetchall()}

    # Facet value counts by type
    ft_query = select(FacetType.slug, FacetType.name, func.count(FacetValue.id).label("count")).outerjoin(
        FacetValue, FacetValue.facet_type_id == FacetType.id
    )

    if category_id:
        ft_query = ft_query.where(FacetValue.category_id == category_id)

    # Filter facets by entity type if specified
    if entity_type_id:
        ft_query = ft_query.join(Entity, FacetValue.entity_id == Entity.id).where(
            Entity.entity_type_id == entity_type_id
        )

    ft_query = ft_query.group_by(FacetType.id)
    ft_result = await session.execute(ft_query)
    facet_counts = {row.slug: {"name": row.name, "count": row.count} for row in ft_result.fetchall()}

    # Relation counts by type
    rt_query = (
        select(RelationType.slug, RelationType.name, func.count(EntityRelation.id).label("count"))
        .outerjoin(EntityRelation, EntityRelation.relation_type_id == RelationType.id)
        .group_by(RelationType.id)
    )

    rt_result = await session.execute(rt_query)
    relation_counts = {row.slug: {"name": row.name, "count": row.count} for row in rt_result.fetchall()}

    # Overall stats - filtered by entity type if specified
    if entity_type_id:
        # Filtered stats for specific entity type
        total_entities = (
            await session.execute(select(func.count(Entity.id)).where(Entity.entity_type_id == entity_type_id))
        ).scalar()

        # Facets for entities of this type
        total_facets = (
            await session.execute(
                select(func.count(FacetValue.id))
                .join(Entity, FacetValue.entity_id == Entity.id)
                .where(Entity.entity_type_id == entity_type_id)
            )
        ).scalar()

        # Relations where source OR target is of this entity type
        total_relations = (
            await session.execute(
                select(func.count(EntityRelation.id))
                .join(
                    Entity,
                    or_(EntityRelation.source_entity_id == Entity.id, EntityRelation.target_entity_id == Entity.id),
                )
                .where(Entity.entity_type_id == entity_type_id)
            )
        ).scalar()

        verified_facets = (
            await session.execute(
                select(func.count(FacetValue.id))
                .join(Entity, FacetValue.entity_id == Entity.id)
                .where(Entity.entity_type_id == entity_type_id, FacetValue.human_verified.is_(True))
            )
        ).scalar()

        # Hierarchy links for this entity type (entities with parent)
        total_hierarchy_links = (
            await session.execute(
                select(func.count(Entity.id)).where(
                    Entity.entity_type_id == entity_type_id, Entity.parent_id.isnot(None)
                )
            )
        ).scalar()
    else:
        # Global stats (no filter)
        total_entities = (await session.execute(select(func.count(Entity.id)))).scalar()
        total_facets = (await session.execute(select(func.count(FacetValue.id)))).scalar()
        total_relations = (await session.execute(select(func.count(EntityRelation.id)))).scalar()
        verified_facets = (
            await session.execute(select(func.count(FacetValue.id)).where(FacetValue.human_verified.is_(True)))
        ).scalar()
        total_hierarchy_links = (
            await session.execute(select(func.count(Entity.id)).where(Entity.parent_id.isnot(None)))
        ).scalar()

    # Total connections = explicit relations + hierarchy links
    total_connections = total_relations + total_hierarchy_links

    return {
        "overview": {
            "total_entities": total_entities,
            "total_facet_values": total_facets,
            "total_relations": total_relations,
            "total_hierarchy_links": total_hierarchy_links,
            "total_connections": total_connections,
            "verified_facet_values": verified_facets,
            "verification_rate": round(verified_facets / total_facets, 2) if total_facets > 0 else 0,
        },
        "by_entity_type": entity_counts,
        "by_facet_type": facet_counts,
        "by_relation_type": relation_counts,
    }
