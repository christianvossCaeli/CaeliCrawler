"""Query execution for Smart Query Service."""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict
from uuid import UUID

import structlog
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Entity,
    EntityType,
    FacetType,
    FacetValue,
    RelationType,
    EntityRelation,
)

logger = structlog.get_logger()


async def execute_smart_query(
    session: AsyncSession,
    query_params: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute the interpreted query against the Entity-Facet system."""

    results = {
        "items": [],
        "total": 0,
        "query_interpretation": query_params,
    }

    primary_type = query_params.get("primary_entity_type", "person")
    facet_types = query_params.get("facet_types", [])
    time_filter = query_params.get("time_filter", "all")
    filters = query_params.get("filters", {})
    grouping = query_params.get("result_grouping", "flat")

    # Get entity type
    entity_type_result = await session.execute(
        select(EntityType).where(EntityType.slug == primary_type)
    )
    entity_type = entity_type_result.scalar_one_or_none()
    if not entity_type:
        return results

    # Get facet types
    facet_type_map = {}
    for ft_slug in facet_types:
        ft_result = await session.execute(
            select(FacetType).where(FacetType.slug == ft_slug)
        )
        ft = ft_result.scalar_one_or_none()
        if ft:
            facet_type_map[ft_slug] = ft

    # Build base entity query
    entity_query = select(Entity).where(
        Entity.entity_type_id == entity_type.id,
        Entity.is_active == True,
    )

    # Apply position filters for persons
    position_keywords = filters.get("position_keywords", [])
    if position_keywords and primary_type == "person":
        position_conditions = []
        for keyword in position_keywords:
            position_conditions.append(
                Entity.core_attributes["position"].astext.ilike(f"%{keyword}%")
            )
        if position_conditions:
            entity_query = entity_query.where(or_(*position_conditions))

    # Apply location/name filters
    location_keywords = filters.get("location_keywords", [])
    if location_keywords:
        location_conditions = []
        for keyword in location_keywords:
            location_conditions.append(Entity.name.ilike(f"%{keyword}%"))
        if location_conditions:
            entity_query = entity_query.where(or_(*location_conditions))

    # If specific facet types are requested, first find entities that have those facets
    if facet_type_map and not location_keywords:
        # Get entity IDs that have the requested facet types
        facet_type_ids = [ft.id for ft in facet_type_map.values()]
        entity_ids_with_facets_result = await session.execute(
            select(FacetValue.entity_id)
            .distinct()
            .where(FacetValue.facet_type_id.in_(facet_type_ids))
            .where(FacetValue.is_active == True)
            .limit(500)
        )
        entity_ids_with_facets = [row[0] for row in entity_ids_with_facets_result.fetchall()]

        if entity_ids_with_facets:
            entity_query = entity_query.where(Entity.id.in_(entity_ids_with_facets))

    # Execute entity query
    entity_result = await session.execute(entity_query.limit(500))
    entities = entity_result.scalars().all()

    if not entities:
        return results

    # Calculate time boundaries
    now = datetime.utcnow()
    days_ahead = filters.get("date_range_days", 90)
    future_cutoff = now + timedelta(days=days_ahead)

    # Get relation types for enrichment
    works_for_result = await session.execute(
        select(RelationType).where(RelationType.slug == "works_for")
    )
    works_for_type = works_for_result.scalar_one_or_none()

    # ==========================================================================
    # BULK LOADING - Avoid N+1 queries by loading all data upfront
    # ==========================================================================
    entity_ids = [e.id for e in entities]
    facet_type_ids = [ft.id for ft in facet_type_map.values()]

    # Bulk load all FacetValues for all entities and facet types
    facet_values_by_entity_and_type: Dict[UUID, Dict[UUID, list[FacetValue]]] = defaultdict(
        lambda: defaultdict(list)
    )
    if facet_type_ids:
        fv_bulk_query = select(FacetValue).where(
            FacetValue.entity_id.in_(entity_ids),
            FacetValue.facet_type_id.in_(facet_type_ids),
            FacetValue.is_active == True,
        )
        # Apply time filter to bulk query
        if time_filter == "future_only":
            fv_bulk_query = fv_bulk_query.where(
                or_(
                    FacetValue.event_date >= now,
                    FacetValue.event_date.is_(None)
                )
            )
        elif time_filter == "past_only":
            fv_bulk_query = fv_bulk_query.where(
                FacetValue.event_date < now
            )
        fv_bulk_result = await session.execute(fv_bulk_query)
        for fv in fv_bulk_result.scalars().all():
            facet_values_by_entity_and_type[fv.entity_id][fv.facet_type_id].append(fv)

    # Bulk load all EntityRelations for works_for type
    relations_by_entity: Dict[UUID, EntityRelation] = {}
    target_entity_ids: set = set()
    if works_for_type:
        rel_bulk_result = await session.execute(
            select(EntityRelation).where(
                EntityRelation.source_entity_id.in_(entity_ids),
                EntityRelation.relation_type_id == works_for_type.id,
            )
        )
        for rel in rel_bulk_result.scalars().all():
            relations_by_entity[rel.source_entity_id] = rel
            target_entity_ids.add(rel.target_entity_id)

    # Bulk load all target entities (municipalities)
    target_entities_by_id: Dict[UUID, Entity] = {}
    if target_entity_ids:
        target_result = await session.execute(
            select(Entity).where(Entity.id.in_(target_entity_ids))
        )
        for target in target_result.scalars().all():
            target_entities_by_id[target.id] = target

    # Create reverse mapping from facet_type_id to slug
    facet_type_id_to_slug = {ft.id: slug for slug, ft in facet_type_map.items()}

    # ==========================================================================
    # Process each entity using pre-loaded data
    # ==========================================================================
    items = []
    events_map = {}  # For grouping by event

    for entity in entities:
        entity_data = {
            "entity_id": str(entity.id),
            "entity_name": entity.name,
            "entity_slug": entity.slug,
            "entity_type": primary_type,
            "attributes": entity.core_attributes,
            "facets": {},
            "relations": {},
        }

        # Get pre-loaded facet values for this entity
        for ft_slug, ft in facet_type_map.items():
            facet_values = facet_values_by_entity_and_type[entity.id][ft.id]

            entity_data["facets"][ft_slug] = [
                {
                    "id": str(fv.id),
                    "value": fv.value,
                    "text": fv.text_representation,
                    "event_date": fv.event_date.isoformat() if fv.event_date else None,
                    "confidence": fv.confidence_score,
                }
                for fv in facet_values
            ]

            # For event grouping
            if grouping == "by_event" and ft_slug == "event_attendance":
                for fv in facet_values:
                    event_name = fv.value.get("event_name", "Unknown")
                    event_date = fv.value.get("event_date", "")
                    event_key = f"{event_name}_{event_date}"

                    if event_key not in events_map:
                        events_map[event_key] = {
                            "event_name": event_name,
                            "event_date": event_date,
                            "event_location": fv.value.get("event_location"),
                            "attendees": [],
                        }

                    # Get municipality from pre-loaded data
                    municipality_info = None
                    rel = relations_by_entity.get(entity.id)
                    if rel:
                        muni = target_entities_by_id.get(rel.target_entity_id)
                        if muni:
                            municipality_info = {
                                "id": str(muni.id),
                                "name": muni.name,
                            }

                    events_map[event_key]["attendees"].append({
                        "person_id": str(entity.id),
                        "person_name": entity.name,
                        "position": entity.core_attributes.get("position"),
                        "municipality": municipality_info,
                        "role": fv.value.get("role"),
                        "topic": fv.value.get("topic"),
                    })

        # Get relations from pre-loaded data
        if works_for_type and primary_type == "person":
            rel = relations_by_entity.get(entity.id)
            if rel:
                target = target_entities_by_id.get(rel.target_entity_id)
                if target:
                    entity_data["relations"]["works_for"] = {
                        "entity_id": str(target.id),
                        "entity_name": target.name,
                        "attributes": rel.attributes,
                    }

        # Only include if has relevant facets
        has_relevant_facets = any(
            len(fvs) > 0 for fvs in entity_data["facets"].values()
        )
        if has_relevant_facets or not facet_types:
            items.append(entity_data)

    # Return based on grouping
    if grouping == "by_event" and events_map:
        events_list = list(events_map.values())
        events_list.sort(key=lambda x: x.get("event_date") or "9999")
        results["items"] = events_list
        results["total"] = len(events_list)
        results["grouping"] = "by_event"
    else:
        results["items"] = items
        results["total"] = len(items)
        results["grouping"] = grouping

    return results
