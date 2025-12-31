"""Analysis report endpoints - overview and entity reports."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.database import get_session
from app.models import (
    AnalysisTemplate,
    DataSource,
    Document,
    Entity,
    EntityRelation,
    EntityType,
    FacetType,
    FacetValue,
    RelationType,
)

router = APIRouter()


def _deduplicate_values(values: list[dict], dedup_fields: list[str]) -> list[dict]:
    """Deduplicate values based on specified fields."""
    seen = {}

    for v in values:
        # Build key from dedup fields
        key_parts = []
        for field in dedup_fields:
            val = v.get("value", {})
            if isinstance(val, dict):
                key_parts.append(str(val.get(field, "")).lower().strip())
            else:
                key_parts.append(str(val).lower().strip())

        key = "|".join(key_parts)

        if key not in seen:
            seen[key] = {
                **v,
                "occurrences": 1,
                "sources": [v.get("document")] if v.get("document") else [],
            }
        else:
            seen[key]["occurrences"] += 1
            seen[key]["confidence"] = max(seen[key]["confidence"], v.get("confidence", 0))
            if v.get("verified"):
                seen[key]["verified"] = True
            if v.get("document") and v["document"] not in seen[key]["sources"]:
                seen[key]["sources"].append(v["document"])

    # Sort by occurrences then confidence
    result = list(seen.values())
    result.sort(key=lambda x: (x["occurrences"], x["confidence"]), reverse=True)

    return result


@router.get("/overview")
async def get_analysis_overview(
    template_id: UUID | None = Query(default=None),
    template_slug: str | None = Query(default=None),
    entity_type_slug: str | None = Query(default=None),
    category_id: UUID | None = Query(default=None),
    facet_types: list[str] | None = Query(default=None, description="Facet type slugs to include"),
    time_filter: str | None = Query(default=None, description="future_only, past_only, all"),
    min_confidence: float = Query(default=0.7, ge=0, le=1),
    min_facet_values: int = Query(default=1, ge=1),
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
):
    """
    Get analysis overview for entities.

    Returns a list of entities with aggregated facet counts and key metrics
    based on the selected template or parameters.
    """
    # Determine entity type
    entity_type = None
    template = None

    if template_id:
        template = await session.get(AnalysisTemplate, template_id)
        if not template:
            raise NotFoundError("AnalysisTemplate", str(template_id))
        entity_type = await session.get(EntityType, template.primary_entity_type_id)
    elif template_slug:
        t_result = await session.execute(
            select(AnalysisTemplate).where(AnalysisTemplate.slug == template_slug)
        )
        template = t_result.scalar()
        if template:
            entity_type = await session.get(EntityType, template.primary_entity_type_id)
    elif entity_type_slug:
        et_result = await session.execute(
            select(EntityType).where(EntityType.slug == entity_type_slug)
        )
        entity_type = et_result.scalar()

    if not entity_type:
        raise ConflictError(
            "No entity type specified",
            detail="Provide template_id, template_slug, or entity_type_slug",
        )

    # Determine which facet types to include
    facet_type_ids = []
    if facet_types:
        ft_result = await session.execute(
            select(FacetType).where(FacetType.slug.in_(facet_types))
        )
        facet_type_ids = [ft.id for ft in ft_result.scalars().all()]
    elif template and template.facet_config:
        enabled_slugs = [
            fc.get("facet_type_slug") or fc.get("facet_type")
            for fc in template.facet_config
            if fc.get("enabled", True)
        ]
        if enabled_slugs:
            ft_result = await session.execute(
                select(FacetType).where(FacetType.slug.in_(enabled_slugs))
            )
            facet_type_ids = [ft.id for ft in ft_result.scalars().all()]

    # Get all entities of this type
    entities_query = select(Entity).where(
        Entity.entity_type_id == entity_type.id,
        Entity.is_active.is_(True),
    )
    entities_result = await session.execute(entities_query)
    entities = entities_result.scalars().all()

    # Build overview data
    now = datetime.now(UTC)
    overview_items = []

    for entity in entities:
        # Base query for facet values
        fv_query = select(FacetValue).where(
            FacetValue.entity_id == entity.id,
            FacetValue.is_active.is_(True),
            FacetValue.confidence_score >= min_confidence,
        )

        if facet_type_ids:
            fv_query = fv_query.where(FacetValue.facet_type_id.in_(facet_type_ids))
        if category_id:
            fv_query = fv_query.where(FacetValue.category_id == category_id)

        # Apply time filter
        if time_filter == "future_only":
            fv_query = fv_query.where(
                or_(
                    FacetValue.event_date >= now,
                    FacetValue.valid_until >= now,
                    and_(FacetValue.event_date.is_(None), FacetValue.valid_until.is_(None))
                )
            )
        elif time_filter == "past_only":
            fv_query = fv_query.where(
                or_(
                    FacetValue.event_date < now,
                    FacetValue.valid_until < now
                )
            )

        fv_result = await session.execute(fv_query)
        facet_values = fv_result.scalars().all()

        if len(facet_values) < min_facet_values:
            continue

        # Group by facet type
        by_type: dict[UUID, list[FacetValue]] = {}
        for fv in facet_values:
            if fv.facet_type_id not in by_type:
                by_type[fv.facet_type_id] = []
            by_type[fv.facet_type_id].append(fv)

        facet_counts = {}
        total_verified = 0
        avg_confidence = sum(fv.confidence_score or 0 for fv in facet_values) / len(facet_values) if facet_values else 0

        for ft_id, fvs in by_type.items():
            ft = await session.get(FacetType, ft_id)
            if ft:
                facet_counts[ft.slug] = len(fvs)
                total_verified += sum(1 for fv in fvs if fv.human_verified)

        # Count relations
        relation_count = (await session.execute(
            select(func.count()).where(
                or_(
                    EntityRelation.source_entity_id == entity.id,
                    EntityRelation.target_entity_id == entity.id
                )
            )
        )).scalar()

        # Count data sources
        source_count = (await session.execute(
            select(func.count()).where(DataSource.entity_id == entity.id)
        )).scalar()

        latest_facet = max((fv.created_at for fv in facet_values), default=None)

        overview_items.append({
            "entity_id": str(entity.id),
            "entity_name": entity.name,
            "entity_slug": entity.slug,
            "external_id": entity.external_id,
            "hierarchy_path": entity.hierarchy_path,
            "latitude": entity.latitude,
            "longitude": entity.longitude,
            "total_facet_values": len(facet_values),
            "verified_count": total_verified,
            "avg_confidence": round(avg_confidence, 2),
            "facet_counts": facet_counts,
            "relation_count": relation_count,
            "source_count": source_count,
            "latest_facet_date": latest_facet.isoformat() if latest_facet else None,
        })

    # Sort by total facet values
    overview_items.sort(key=lambda x: x["total_facet_values"], reverse=True)
    overview_items = overview_items[:limit]

    return {
        "entity_type": {
            "id": str(entity_type.id),
            "slug": entity_type.slug,
            "name": entity_type.name,
            "name_plural": entity_type.name_plural,
        },
        "template": {
            "id": str(template.id),
            "slug": template.slug,
            "name": template.name,
        } if template else None,
        "filters": {
            "category_id": str(category_id) if category_id else None,
            "facet_types": facet_types,
            "time_filter": time_filter,
            "min_confidence": min_confidence,
        },
        "total_entities": len(overview_items),
        "entities": overview_items,
    }


@router.get("/report/{entity_id}")
async def get_entity_report(
    entity_id: UUID,
    template_id: UUID | None = Query(default=None),
    template_slug: str | None = Query(default=None),
    category_id: UUID | None = Query(default=None),
    time_filter: str | None = Query(default=None),
    min_confidence: float = Query(default=0.7, ge=0, le=1),
    session: AsyncSession = Depends(get_session),
):
    """
    Get detailed analysis report for a specific entity.

    Aggregates all facet values and relations, with deduplication and ranking.
    """
    entity = await session.get(Entity, entity_id)
    if not entity:
        raise NotFoundError("Entity", str(entity_id))

    entity_type = await session.get(EntityType, entity.entity_type_id)

    # Get template if specified
    template = None
    if template_id:
        template = await session.get(AnalysisTemplate, template_id)
    elif template_slug:
        t_result = await session.execute(
            select(AnalysisTemplate).where(AnalysisTemplate.slug == template_slug)
        )
        template = t_result.scalar()

    # Determine facet type configuration
    facet_config = {}
    if template and template.facet_config:
        for fc in template.facet_config:
            slug = fc.get("facet_type_slug") or fc.get("facet_type")
            if fc.get("enabled", True):
                facet_config[slug] = {
                    "label": fc.get("label"),
                    "display_order": fc.get("display_order", 0),
                    "time_filter": fc.get("time_filter"),
                }

    # Base query for facet values
    now = datetime.now(UTC)
    fv_query = select(FacetValue).where(
        FacetValue.entity_id == entity_id,
        FacetValue.is_active.is_(True),
        FacetValue.confidence_score >= min_confidence,
    )

    if category_id:
        fv_query = fv_query.where(FacetValue.category_id == category_id)

    # Apply time filter
    if time_filter == "future_only":
        fv_query = fv_query.where(
            or_(
                FacetValue.event_date >= now,
                FacetValue.valid_until >= now,
                and_(FacetValue.event_date.is_(None), FacetValue.valid_until.is_(None))
            )
        )
    elif time_filter == "past_only":
        fv_query = fv_query.where(
            or_(
                FacetValue.event_date < now,
                FacetValue.valid_until < now
            )
        )

    fv_result = await session.execute(fv_query)
    facet_values = fv_result.scalars().all()

    # Group facet values by type and aggregate
    facets_by_type: dict[str, dict[str, Any]] = {}

    for fv in facet_values:
        ft = await session.get(FacetType, fv.facet_type_id)
        if not ft:
            continue

        # Apply per-facet time filter from template
        if ft.slug in facet_config:
            ft_time_filter = facet_config[ft.slug].get("time_filter")
            if ft_time_filter == "future_only" and fv.event_date and fv.event_date < now or ft_time_filter == "past_only" and fv.event_date and fv.event_date >= now:
                continue

        if ft.slug not in facets_by_type:
            facets_by_type[ft.slug] = {
                "facet_type_id": str(ft.id),
                "facet_type_slug": ft.slug,
                "facet_type_name": facet_config.get(ft.slug, {}).get("label") or ft.name,
                "icon": ft.icon,
                "color": ft.color,
                "values": [],
                "aggregated": {},
            }

        # Get document info if available
        document = await session.get(Document, fv.source_document_id) if fv.source_document_id else None

        facets_by_type[ft.slug]["values"].append({
            "id": str(fv.id),
            "value": fv.value,
            "text": fv.text_representation,
            "event_date": fv.event_date.isoformat() if fv.event_date else None,
            "confidence": fv.confidence_score,
            "verified": fv.human_verified,
            "source_url": fv.source_url,
            "document": {
                "id": str(document.id),
                "title": document.title,
                "url": document.original_url,
            } if document else None,
            "occurrence_count": fv.occurrence_count,
            "first_seen": fv.first_seen.isoformat() if fv.first_seen else None,
            "last_seen": fv.last_seen.isoformat() if fv.last_seen else None,
        })

    # Aggregate and deduplicate per facet type
    for slug, data in facets_by_type.items():
        ft_result = await session.execute(
            select(FacetType).where(FacetType.slug == slug)
        )
        ft = ft_result.scalar()

        if ft and ft.deduplication_fields:
            # Deduplicate based on configured fields
            deduped = _deduplicate_values(data["values"], ft.deduplication_fields)
            data["aggregated"] = {
                "total": len(data["values"]),
                "unique": len(deduped),
                "verified": sum(1 for v in data["values"] if v.get("verified")),
                "avg_confidence": round(
                    sum(v.get("confidence", 0) for v in data["values"]) / len(data["values"]),
                    2
                ) if data["values"] else 0,
            }
            data["values"] = deduped
        else:
            # No deduplication, just sort by confidence
            data["values"].sort(key=lambda x: x.get("confidence", 0), reverse=True)
            data["aggregated"] = {
                "total": len(data["values"]),
                "verified": sum(1 for v in data["values"] if v.get("verified")),
                "avg_confidence": round(
                    sum(v.get("confidence", 0) for v in data["values"]) / len(data["values"]),
                    2
                ) if data["values"] else 0,
            }

    # Get relations
    relations = []
    rel_query = select(EntityRelation).where(
        or_(
            EntityRelation.source_entity_id == entity_id,
            EntityRelation.target_entity_id == entity_id
        ),
        EntityRelation.is_active.is_(True),
    )
    rel_result = await session.execute(rel_query)

    for rel in rel_result.scalars().all():
        rt = await session.get(RelationType, rel.relation_type_id)
        other_entity_id = rel.target_entity_id if rel.source_entity_id == entity_id else rel.source_entity_id
        other_entity = await session.get(Entity, other_entity_id)
        other_et = await session.get(EntityType, other_entity.entity_type_id) if other_entity else None

        is_outgoing = rel.source_entity_id == entity_id

        relations.append({
            "id": str(rel.id),
            "relation_type": rt.slug if rt else None,
            "relation_name": rt.name if is_outgoing else (rt.name_inverse if rt else None),
            "direction": "outgoing" if is_outgoing else "incoming",
            "related_entity": {
                "id": str(other_entity.id),
                "name": other_entity.name,
                "slug": other_entity.slug,
                "type": other_et.slug if other_et else None,
                "type_name": other_et.name if other_et else None,
            } if other_entity else None,
            "attributes": rel.attributes,
            "confidence": rel.confidence_score,
            "verified": rel.human_verified,
        })

    # Get data sources for this entity
    sources = []
    source_query = select(DataSource).where(DataSource.entity_id == entity_id)
    source_result = await session.execute(source_query)
    for src in source_result.scalars().all():
        sources.append({
            "id": str(src.id),
            "name": src.name,
            "url": src.url,
            "is_active": src.is_active,
        })

    # Calculate overview stats
    total_values = sum(len(d["values"]) for d in facets_by_type.values())
    verified_values = sum(d["aggregated"].get("verified", 0) for d in facets_by_type.values())

    return {
        "entity": {
            "id": str(entity.id),
            "name": entity.name,
            "slug": entity.slug,
            "external_id": entity.external_id,
            "hierarchy_path": entity.hierarchy_path,
            "core_attributes": entity.core_attributes,
            "latitude": entity.latitude,
            "longitude": entity.longitude,
        },
        "entity_type": {
            "id": str(entity_type.id),
            "slug": entity_type.slug,
            "name": entity_type.name,
        } if entity_type else None,
        "template": {
            "id": str(template.id),
            "slug": template.slug,
            "name": template.name,
        } if template else None,
        "overview": {
            "total_facet_values": total_values,
            "verified_values": verified_values,
            "facet_type_count": len(facets_by_type),
            "relation_count": len(relations),
            "source_count": len(sources),
        },
        "facets": facets_by_type,
        "relations": relations,
        "sources": sources,
    }
