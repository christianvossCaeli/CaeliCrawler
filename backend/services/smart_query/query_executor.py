"""Query execution for Smart Query Service."""

from collections import defaultdict
from datetime import datetime, timezone, date
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from sqlalchemy import select, or_, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Entity,
    EntityType,
    FacetType,
    FacetValue,
    RelationType,
    EntityRelation,
)
from .relation_resolver import (
    RelationResolver,
    parse_relation_chain_from_query,
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

    query_type = query_params.get("query_type", "list")
    primary_type = query_params.get("primary_entity_type", "person")
    facet_types = query_params.get("facet_types", [])
    negative_facet_types = query_params.get("negative_facet_types", [])
    facet_operator = query_params.get("facet_operator", "OR").upper()  # AND or OR
    time_filter = query_params.get("time_filter", "all")
    date_range = query_params.get("date_range", {})
    filters = query_params.get("filters", {})
    negative_locations = filters.get("negative_locations", [])
    logical_operator = filters.get("logical_operator", "OR").upper()  # For location filters
    grouping = query_params.get("result_grouping", "flat")

    # Multi-hop relation chain parameters
    relation_chain = parse_relation_chain_from_query(query_params)
    target_facets_at_chain_end = query_params.get("target_facets_at_chain_end", [])
    negative_facets_at_chain_end = query_params.get("negative_facets_at_chain_end", [])

    # Parse date_range if provided
    date_start: Optional[datetime] = None
    date_end: Optional[datetime] = None
    if date_range:
        start_str = date_range.get("start")
        end_str = date_range.get("end")
        if start_str and isinstance(start_str, str) and len(start_str) == 10:
            try:
                date_start = datetime.strptime(start_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        if end_str and isinstance(end_str, str) and len(end_str) == 10:
            try:
                # End of day for end date
                date_end = datetime.strptime(end_str, "%Y-%m-%d").replace(
                    hour=23, minute=59, second=59, tzinfo=timezone.utc
                )
            except ValueError:
                pass

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

    # Build base entity query conditions
    base_conditions = [
        Entity.entity_type_id == entity_type.id,
        Entity.is_active.is_(True),
    ]

    # Apply country filter
    country = filters.get("country")
    if country:
        base_conditions.append(Entity.country == country)

    # Apply admin_level_1 filter (Bundesland) - supports single value or array
    admin_level_1 = filters.get("admin_level_1")
    if admin_level_1:
        if isinstance(admin_level_1, list):
            # Multiple locations - use OR (or AND based on logical_operator, but AND doesn't make sense for locations)
            base_conditions.append(Entity.admin_level_1.in_(admin_level_1))
        else:
            base_conditions.append(Entity.admin_level_1 == admin_level_1)

    # Apply negative location filter (NOT IN)
    if negative_locations:
        if isinstance(negative_locations, list) and negative_locations:
            base_conditions.append(~Entity.admin_level_1.in_(negative_locations))
        elif isinstance(negative_locations, str):
            base_conditions.append(Entity.admin_level_1 != negative_locations)

    # Apply position filters for persons
    position_keywords = filters.get("position_keywords", [])
    if position_keywords and primary_type == "person":
        position_conditions = []
        for keyword in position_keywords:
            position_conditions.append(
                Entity.core_attributes["position"].astext.ilike(f"%{keyword}%")
            )
        if position_conditions:
            base_conditions.append(or_(*position_conditions))

    # Apply location/name filters
    # NOTE: Only use location_keywords if admin_level_1 is NOT set
    # (to avoid filtering by name when it's actually a region filter)
    location_keywords = filters.get("location_keywords", [])
    if location_keywords and not admin_level_1 and not country:
        location_conditions = []
        for keyword in location_keywords:
            location_conditions.append(Entity.name.ilike(f"%{keyword}%"))
        if location_conditions:
            base_conditions.append(or_(*location_conditions))

    # If specific facet types are requested, first find entities that have those facets
    facet_entity_ids = None
    negative_facet_entity_ids = None

    # Handle negative facet types first (entities to EXCLUDE)
    if negative_facet_types:
        # Load negative facet types
        neg_facet_type_map = {}
        for ft_slug in negative_facet_types:
            ft_result = await session.execute(
                select(FacetType).where(FacetType.slug == ft_slug)
            )
            ft = ft_result.scalar_one_or_none()
            if ft:
                neg_facet_type_map[ft_slug] = ft

        if neg_facet_type_map:
            neg_facet_type_ids = [ft.id for ft in neg_facet_type_map.values()]
            # Get entities that have ANY of the negative facet types (to exclude them)
            neg_entity_ids_result = await session.execute(
                select(FacetValue.entity_id)
                .distinct()
                .where(FacetValue.facet_type_id.in_(neg_facet_type_ids))
                .where(FacetValue.is_active.is_(True))
            )
            negative_facet_entity_ids = set(row[0] for row in neg_entity_ids_result.fetchall())

    # Only skip facet filtering if we're doing a name-based search (not region-based)
    name_search_active = location_keywords and not admin_level_1 and not country
    if facet_type_map and not name_search_active:
        facet_type_ids = [ft.id for ft in facet_type_map.values()]

        if facet_operator == "AND" and len(facet_type_ids) > 1:
            # AND: Entity must have ALL requested facet types
            # Use a subquery that counts distinct facet types per entity
            from sqlalchemy import literal_column

            # Get entities that have ALL the requested facet types
            subquery = (
                select(FacetValue.entity_id)
                .where(FacetValue.facet_type_id.in_(facet_type_ids))
                .where(FacetValue.is_active.is_(True))
                .group_by(FacetValue.entity_id)
                .having(func.count(func.distinct(FacetValue.facet_type_id)) == len(facet_type_ids))
            )
            entity_ids_with_facets_result = await session.execute(subquery)
            facet_entity_ids = [row[0] for row in entity_ids_with_facets_result.fetchall()]
        else:
            # OR (default): Entity must have at least one of the requested facet types
            entity_ids_with_facets_result = await session.execute(
                select(FacetValue.entity_id)
                .distinct()
                .where(FacetValue.facet_type_id.in_(facet_type_ids))
                .where(FacetValue.is_active.is_(True))
            )
            facet_entity_ids = [row[0] for row in entity_ids_with_facets_result.fetchall()]

        # Apply negative facet filter (exclude entities with negative facets)
        if negative_facet_entity_ids and facet_entity_ids is not None:
            facet_entity_ids = [eid for eid in facet_entity_ids if eid not in negative_facet_entity_ids]

    # Apply negative facet filter even if no positive facets requested
    if negative_facet_entity_ids and facet_entity_ids is None:
        # Need to exclude entities with negative facets from all entities
        # This means we need to use NOT IN condition
        pass  # Will be handled by the query conditions below

    # ==========================================================================
    # MULTI-HOP RELATION RESOLUTION
    # ==========================================================================
    multi_hop_entity_ids: Optional[List[UUID]] = None

    if relation_chain:
        logger.info(
            "Processing multi-hop relation query",
            primary_type=primary_type,
            chain_length=len(relation_chain),
            target_facets=target_facets_at_chain_end,
        )

        resolver = RelationResolver(session)

        # Resolve entities through the relation chain
        multi_hop_entity_ids = await resolver.resolve_entities_with_related_facets(
            primary_entity_type_slug=primary_type,
            relation_chain=relation_chain,
            target_facet_types=target_facets_at_chain_end,
            negative_facet_types=negative_facets_at_chain_end,
            base_filters=filters,
        )

        if not multi_hop_entity_ids:
            logger.debug("Multi-hop resolution returned no matching entities")
            results["message"] = "Keine Entities gefunden, die den Multi-Hop-Kriterien entsprechen"
            return results

        logger.info(
            "Multi-hop resolution complete",
            matching_entities=len(multi_hop_entity_ids),
        )

    # Build entity query
    entity_query = select(Entity).where(*base_conditions)

    # Handle negative facets when no positive facets are specified
    if negative_facet_entity_ids and facet_entity_ids is None and not facet_type_map:
        # Exclude entities that have the negative facet types
        entity_query = entity_query.where(~Entity.id.in_(list(negative_facet_entity_ids)))

    if facet_entity_ids is not None:
        if facet_entity_ids:
            entity_query = entity_query.where(Entity.id.in_(facet_entity_ids))
        else:
            # No entities with those facets - return empty result
            return results

    # Apply multi-hop relation filter if resolved
    if multi_hop_entity_ids is not None:
        entity_query = entity_query.where(Entity.id.in_(multi_hop_entity_ids))

    # Handle COUNT queries - just return the count, no items
    if query_type == "count":
        count_conditions = list(base_conditions)

        # Build the count query with all filters
        count_subquery = select(Entity).where(*count_conditions)

        if facet_entity_ids is not None and facet_entity_ids:
            count_subquery = count_subquery.where(Entity.id.in_(facet_entity_ids))

        if multi_hop_entity_ids is not None:
            count_subquery = count_subquery.where(Entity.id.in_(multi_hop_entity_ids))

        if negative_facet_entity_ids and facet_entity_ids is None and not facet_type_map:
            count_subquery = count_subquery.where(~Entity.id.in_(list(negative_facet_entity_ids)))

        count_query = select(func.count()).select_from(count_subquery.subquery())
        total_count = (await session.execute(count_query)).scalar() or 0
        results["total"] = total_count
        results["query_type"] = "count"
        results["message"] = f"Es gibt {total_count} {entity_type.name_plural or entity_type.name}"
        location_parts = []
        if admin_level_1:
            location_parts.append(admin_level_1)
        if country:
            country_names = {"DE": "Deutschland", "AT": "Österreich", "CH": "Schweiz", "GB": "Großbritannien"}
            location_parts.append(country_names.get(country, country))
        if location_parts:
            results["message"] += f" in {', '.join(location_parts)}"
        return results

    # Handle AGGREGATE queries - statistical operations
    if query_type == "aggregate":
        aggregate_config = query_params.get("aggregate", {})
        agg_function = aggregate_config.get("function", "COUNT").upper()
        agg_target = aggregate_config.get("target", "entity_count")
        agg_facet_type = aggregate_config.get("facet_type")
        group_by = aggregate_config.get("group_by")

        aggregate_results = await _execute_aggregate_query(
            session=session,
            entity_type=entity_type,
            base_conditions=base_conditions,
            facet_entity_ids=facet_entity_ids,
            negative_facet_entity_ids=negative_facet_entity_ids,
            multi_hop_entity_ids=multi_hop_entity_ids,
            agg_function=agg_function,
            agg_target=agg_target,
            agg_facet_type=agg_facet_type,
            group_by=group_by,
            filters=filters,
        )

        results["query_type"] = "aggregate"
        results["aggregate_function"] = agg_function
        results["aggregate_target"] = agg_target
        results["group_by"] = group_by
        results["items"] = aggregate_results["items"]
        results["total"] = aggregate_results["total"]
        results["message"] = aggregate_results["message"]
        return results

    # Execute entity query for list queries (with reasonable limit)
    entity_result = await session.execute(entity_query.limit(1000))
    entities = entity_result.scalars().all()

    if not entities:
        return results

    # Calculate time boundary (use timezone-aware UTC)
    now = datetime.now(timezone.utc)

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
            FacetValue.is_active.is_(True),
        )
        # Apply date range filter (takes precedence over time_filter)
        if date_start and date_end:
            # Full date range: start <= event_date <= end
            fv_bulk_query = fv_bulk_query.where(
                and_(
                    FacetValue.event_date >= date_start,
                    FacetValue.event_date <= date_end
                )
            )
        elif date_start:
            # Only start date: event_date >= start
            fv_bulk_query = fv_bulk_query.where(
                FacetValue.event_date >= date_start
            )
        elif date_end:
            # Only end date: event_date <= end
            fv_bulk_query = fv_bulk_query.where(
                FacetValue.event_date <= date_end
            )
        # Fallback to time_filter if no date_range specified
        elif time_filter == "future_only":
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
                    "source_type": fv.source_type.value if fv.source_type else None,
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


async def _execute_aggregate_query(
    session: AsyncSession,
    entity_type: EntityType,
    base_conditions: list,
    facet_entity_ids: Optional[list],
    negative_facet_entity_ids: Optional[set],
    multi_hop_entity_ids: Optional[List[UUID]],
    agg_function: str,
    agg_target: str,
    agg_facet_type: Optional[str],
    group_by: Optional[str],
    filters: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute an aggregate query with optional GROUP BY.

    Supports:
    - COUNT: Count entities or facets
    - SUM: Sum of facet counts per entity
    - AVG: Average facet count per entity
    - MIN: Minimum facet count
    - MAX: Maximum facet count

    Group by options:
    - entity_type: Group by entity type
    - admin_level_1: Group by Bundesland/region
    - country: Group by country
    - facet_type: Group by facet type
    """
    results = {
        "items": [],
        "total": 0,
        "message": "",
    }

    # Map aggregate function names to SQLAlchemy functions
    agg_functions = {
        "COUNT": func.count,
        "SUM": func.sum,
        "AVG": func.avg,
        "MIN": func.min,
        "MAX": func.max,
    }

    if agg_function not in agg_functions:
        results["message"] = f"Unbekannte Aggregatfunktion: {agg_function}"
        return results

    sql_func = agg_functions[agg_function]

    # Build the base entity subquery with conditions
    entity_subquery = select(Entity.id).where(*base_conditions)
    if facet_entity_ids is not None:
        entity_subquery = entity_subquery.where(Entity.id.in_(facet_entity_ids))
    if negative_facet_entity_ids:
        entity_subquery = entity_subquery.where(~Entity.id.in_(list(negative_facet_entity_ids)))
    if multi_hop_entity_ids is not None:
        entity_subquery = entity_subquery.where(Entity.id.in_(multi_hop_entity_ids))

    # Handle different aggregate targets
    if agg_target == "entity_count":
        # Simple entity count, optionally grouped
        if group_by == "admin_level_1":
            query = (
                select(
                    Entity.admin_level_1.label("group_key"),
                    sql_func(Entity.id).label("value")
                )
                .where(*base_conditions)
                .group_by(Entity.admin_level_1)
                .order_by(sql_func(Entity.id).desc())
            )
            if facet_entity_ids is not None:
                query = query.where(Entity.id.in_(facet_entity_ids))
            if negative_facet_entity_ids:
                query = query.where(~Entity.id.in_(list(negative_facet_entity_ids)))
            if multi_hop_entity_ids is not None:
                query = query.where(Entity.id.in_(multi_hop_entity_ids))

            result = await session.execute(query)
            rows = result.fetchall()

            items = [
                {"group": row.group_key or "Unbekannt", "value": row.value}
                for row in rows
            ]
            results["items"] = items
            results["total"] = len(items)
            results["message"] = f"{agg_function} von {entity_type.name_plural or entity_type.name} gruppiert nach Bundesland"

        elif group_by == "country":
            query = (
                select(
                    Entity.country.label("group_key"),
                    sql_func(Entity.id).label("value")
                )
                .where(*base_conditions)
                .group_by(Entity.country)
                .order_by(sql_func(Entity.id).desc())
            )
            if facet_entity_ids is not None:
                query = query.where(Entity.id.in_(facet_entity_ids))
            if negative_facet_entity_ids:
                query = query.where(~Entity.id.in_(list(negative_facet_entity_ids)))
            if multi_hop_entity_ids is not None:
                query = query.where(Entity.id.in_(multi_hop_entity_ids))

            result = await session.execute(query)
            rows = result.fetchall()

            country_names = {"DE": "Deutschland", "AT": "Österreich", "CH": "Schweiz", "GB": "Großbritannien"}
            items = [
                {"group": country_names.get(row.group_key, row.group_key) or "Unbekannt", "value": row.value}
                for row in rows
            ]
            results["items"] = items
            results["total"] = len(items)
            results["message"] = f"{agg_function} von {entity_type.name_plural or entity_type.name} gruppiert nach Land"

        elif group_by == "entity_type":
            # Need to join with EntityType
            query = (
                select(
                    EntityType.name.label("group_key"),
                    sql_func(Entity.id).label("value")
                )
                .join(EntityType, Entity.entity_type_id == EntityType.id)
                .where(Entity.is_active.is_(True))
                .group_by(EntityType.name)
                .order_by(sql_func(Entity.id).desc())
            )

            result = await session.execute(query)
            rows = result.fetchall()

            items = [
                {"group": row.group_key or "Unbekannt", "value": row.value}
                for row in rows
            ]
            results["items"] = items
            results["total"] = len(items)
            results["message"] = f"{agg_function} von Entities gruppiert nach Entity-Typ"

        else:
            # No grouping - simple count
            count_query = select(sql_func(Entity.id)).where(*base_conditions)
            if facet_entity_ids is not None:
                count_query = count_query.where(Entity.id.in_(facet_entity_ids))
            if negative_facet_entity_ids:
                count_query = count_query.where(~Entity.id.in_(list(negative_facet_entity_ids)))
            if multi_hop_entity_ids is not None:
                count_query = count_query.where(Entity.id.in_(multi_hop_entity_ids))

            result = await session.execute(count_query)
            total = result.scalar() or 0

            results["items"] = [{"value": total}]
            results["total"] = 1
            results["message"] = f"{agg_function}: {total} {entity_type.name_plural or entity_type.name}"

    elif agg_target == "facet_count":
        # Aggregate over facet counts per entity
        if not agg_facet_type:
            results["message"] = "Für Facet-Aggregationen muss ein Facet-Typ angegeben werden"
            return results

        # Get the facet type
        ft_result = await session.execute(
            select(FacetType).where(FacetType.slug == agg_facet_type)
        )
        facet_type = ft_result.scalar_one_or_none()
        if not facet_type:
            results["message"] = f"Facet-Typ '{agg_facet_type}' nicht gefunden"
            return results

        # Build subquery for facet counts per entity
        facet_count_subquery = (
            select(
                FacetValue.entity_id,
                func.count(FacetValue.id).label("facet_count")
            )
            .where(
                FacetValue.facet_type_id == facet_type.id,
                FacetValue.is_active.is_(True),
                FacetValue.entity_id.in_(entity_subquery)
            )
            .group_by(FacetValue.entity_id)
            .subquery()
        )

        if group_by == "admin_level_1":
            # Group by region with facet counts
            query = (
                select(
                    Entity.admin_level_1.label("group_key"),
                    sql_func(facet_count_subquery.c.facet_count).label("value")
                )
                .join(facet_count_subquery, Entity.id == facet_count_subquery.c.entity_id)
                .where(*base_conditions)
                .group_by(Entity.admin_level_1)
                .order_by(sql_func(facet_count_subquery.c.facet_count).desc())
            )

            result = await session.execute(query)
            rows = result.fetchall()

            items = [
                {"group": row.group_key or "Unbekannt", "value": float(row.value) if row.value else 0}
                for row in rows
            ]
            results["items"] = items
            results["total"] = len(items)
            results["message"] = f"{agg_function} von {facet_type.name} pro {entity_type.name} gruppiert nach Bundesland"

        elif group_by == "entity_type":
            # Group by entity type with facet counts
            query = (
                select(
                    EntityType.name.label("group_key"),
                    sql_func(facet_count_subquery.c.facet_count).label("value")
                )
                .join(facet_count_subquery, Entity.id == facet_count_subquery.c.entity_id)
                .join(EntityType, Entity.entity_type_id == EntityType.id)
                .where(Entity.is_active.is_(True))
                .group_by(EntityType.name)
                .order_by(sql_func(facet_count_subquery.c.facet_count).desc())
            )

            result = await session.execute(query)
            rows = result.fetchall()

            items = [
                {"group": row.group_key or "Unbekannt", "value": float(row.value) if row.value else 0}
                for row in rows
            ]
            results["items"] = items
            results["total"] = len(items)
            results["message"] = f"{agg_function} von {facet_type.name} gruppiert nach Entity-Typ"

        else:
            # No grouping - aggregate over all entities
            if agg_function == "COUNT":
                # Count total facets
                count_query = (
                    select(func.count(FacetValue.id))
                    .where(
                        FacetValue.facet_type_id == facet_type.id,
                        FacetValue.is_active.is_(True),
                        FacetValue.entity_id.in_(entity_subquery)
                    )
                )
                result = await session.execute(count_query)
                total = result.scalar() or 0
                results["items"] = [{"value": total}]
                results["total"] = 1
                results["message"] = f"Insgesamt {total} {facet_type.name}"
            else:
                # AVG, SUM, MIN, MAX over facet counts
                agg_query = (
                    select(sql_func(facet_count_subquery.c.facet_count))
                )
                result = await session.execute(agg_query)
                value = result.scalar()

                if value is not None:
                    formatted_value = round(float(value), 2) if agg_function == "AVG" else int(value)
                else:
                    formatted_value = 0

                function_labels = {
                    "AVG": "Durchschnitt",
                    "SUM": "Summe",
                    "MIN": "Minimum",
                    "MAX": "Maximum",
                }

                results["items"] = [{"value": formatted_value}]
                results["total"] = 1
                results["message"] = f"{function_labels.get(agg_function, agg_function)}: {formatted_value} {facet_type.name} pro {entity_type.name}"

    return results
