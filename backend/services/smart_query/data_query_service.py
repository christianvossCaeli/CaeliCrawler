"""Data Query Service for Smart Query.

This service handles data retrieval from the Entity-Facet system,
including FacetValueHistory for time-series data.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from sqlalchemy import select, and_, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Entity, EntityType, FacetType, FacetValue, FacetValueHistory
from app.schemas.visualization import (
    QueryDataResponse,
    QueryDataConfig,
    VisualizationConfig,
    VisualizationType,
    VisualizationColumn,
    ColumnType,
    SourceInfo,
    SuggestedAction,
    StatCard,
)

logger = structlog.get_logger()


class DataQueryService:
    """Service for querying entity and facet data."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def query_data(
        self,
        config: QueryDataConfig,
        user_query: Optional[str] = None,
    ) -> QueryDataResponse:
        """
        Query entities with their facet values.

        This is the main entry point for the query_data operation.
        It retrieves entities of a specific type with their associated
        facet values (either latest or history).

        Args:
            config: Query configuration
            user_query: Original user query for context

        Returns:
            QueryDataResponse with data and visualization config
        """
        try:
            # 1. Get entity type
            entity_type = await self._get_entity_type(config.entity_type)
            if not entity_type:
                return QueryDataResponse(
                    success=False,
                    error=f"Entity-Typ '{config.entity_type}' nicht gefunden",
                    data_source="internal",
                )

            # 2. Get facet types
            facet_type_map = await self._get_facet_types(config.facet_types)

            # 3. Build and execute entity query
            entities = await self._query_entities(entity_type, config)

            if not entities:
                return QueryDataResponse(
                    success=True,
                    data_source="internal",
                    entity_type=config.entity_type,
                    data=[],
                    total_count=0,
                    returned_count=0,
                    explanation=f"Keine {entity_type.name_plural or entity_type.name} gefunden",
                )

            # 4. Load facet values for entities
            entity_ids = [e.id for e in entities]
            facet_data = await self._load_facet_data(
                entity_ids=entity_ids,
                facet_type_map=facet_type_map,
                time_range=config.time_range,
            )

            # 5. Build result data
            data = []
            for entity in entities:
                entity_data = {
                    "entity_id": str(entity.id),
                    "entity_name": entity.name,
                    "entity_type": config.entity_type,
                }

                if config.include_core_attributes:
                    entity_data["core_attributes"] = entity.core_attributes or {}
                    entity_data["admin_level_1"] = entity.admin_level_1
                    entity_data["country"] = entity.country
                    entity_data["tags"] = entity.tags or []

                # Add facet values
                entity_data["facets"] = facet_data.get(entity.id, {})

                data.append(entity_data)

            # 6. Apply sorting
            data = self._sort_data(data, config.sort_by, config.sort_order, facet_type_map)

            # 7. Determine last update time
            last_updated = self._get_last_update_time(facet_data)

            # 8. Build response
            return QueryDataResponse(
                success=True,
                data_source="internal",
                entity_type=config.entity_type,
                data=data,
                total_count=len(data),
                returned_count=len(data),
                source_info=SourceInfo(
                    type="facet_history" if config.time_range else "internal",
                    last_updated=last_updated,
                    data_freshness=self._format_freshness(last_updated) if last_updated else None,
                ),
                suggested_actions=self._build_suggested_actions(config, facet_type_map),
            )

        except Exception as e:
            logger.error("query_data_failed", error=str(e), config=config.model_dump())
            return QueryDataResponse(
                success=False,
                error=f"Abfrage fehlgeschlagen: {str(e)}",
                data_source="internal",
            )

    async def query_facet_history(
        self,
        entity_type_slug: str,
        facet_type_slug: str,
        entity_ids: Optional[List[UUID]] = None,
        entity_names: Optional[List[str]] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit_per_entity: int = 100,
    ) -> Dict[str, Any]:
        """
        Query history data for a specific facet type.

        Args:
            entity_type_slug: Entity type to query
            facet_type_slug: Facet type to query history for
            entity_ids: Optional list of specific entity IDs
            entity_names: Optional list of entity names
            from_date: Start of time range
            to_date: End of time range
            limit_per_entity: Max history points per entity

        Returns:
            Dictionary with entities and their history data
        """
        # Get facet type
        ft_result = await self.session.execute(
            select(FacetType).where(FacetType.slug == facet_type_slug)
        )
        facet_type = ft_result.scalar_one_or_none()

        if not facet_type:
            return {"error": f"FacetType '{facet_type_slug}' nicht gefunden", "data": []}

        if facet_type.value_type != "history":
            return {"error": f"FacetType '{facet_type_slug}' ist kein History-Typ", "data": []}

        # Get entity type
        et_result = await self.session.execute(
            select(EntityType).where(EntityType.slug == entity_type_slug)
        )
        entity_type = et_result.scalar_one_or_none()

        if not entity_type:
            return {"error": f"EntityType '{entity_type_slug}' nicht gefunden", "data": []}

        # Build entity query
        entity_query = select(Entity).where(
            Entity.entity_type_id == entity_type.id,
            Entity.is_active.is_(True),
        )

        if entity_ids:
            entity_query = entity_query.where(Entity.id.in_(entity_ids))
        if entity_names:
            entity_query = entity_query.where(Entity.name.in_(entity_names))

        entity_result = await self.session.execute(entity_query)
        entities = entity_result.scalars().all()

        if not entities:
            return {"data": [], "total_entities": 0}

        # Query history for all entities
        entity_id_list = [e.id for e in entities]

        history_query = (
            select(FacetValueHistory)
            .where(
                FacetValueHistory.entity_id.in_(entity_id_list),
                FacetValueHistory.facet_type_id == facet_type.id,
            )
            .order_by(FacetValueHistory.recorded_at.desc())
        )

        if from_date:
            history_query = history_query.where(FacetValueHistory.recorded_at >= from_date)
        if to_date:
            history_query = history_query.where(FacetValueHistory.recorded_at <= to_date)

        history_result = await self.session.execute(history_query)
        history_points = history_result.scalars().all()

        # Group by entity
        entity_map = {e.id: e for e in entities}
        history_by_entity: Dict[UUID, List[Dict[str, Any]]] = {}

        for hp in history_points:
            if hp.entity_id not in history_by_entity:
                history_by_entity[hp.entity_id] = []

            if len(history_by_entity[hp.entity_id]) < limit_per_entity:
                history_by_entity[hp.entity_id].append({
                    "id": str(hp.id),
                    "recorded_at": hp.recorded_at.isoformat() if hp.recorded_at else None,
                    "value": hp.value,
                    "value_label": hp.value_label,
                    "track_key": hp.track_key,
                    "annotations": hp.annotations,
                })

        # Build result
        data = []
        for entity_id, history in history_by_entity.items():
            entity = entity_map.get(entity_id)
            if entity:
                data.append({
                    "entity_id": str(entity_id),
                    "entity_name": entity.name,
                    "history": history,
                    "point_count": len(history),
                })

        return {
            "data": data,
            "total_entities": len(data),
            "facet_type": facet_type_slug,
            "entity_type": entity_type_slug,
        }

    async def get_latest_facet_values(
        self,
        entity_type_slug: str,
        facet_type_slugs: List[str],
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get the latest facet value for each entity.

        For history facets, returns the most recent value.
        For regular facets, returns the current value.
        """
        # Get entity type
        et_result = await self.session.execute(
            select(EntityType).where(EntityType.slug == entity_type_slug)
        )
        entity_type = et_result.scalar_one_or_none()

        if not entity_type:
            return []

        # Build entity query
        entity_conditions = [
            Entity.entity_type_id == entity_type.id,
            Entity.is_active.is_(True),
        ]

        if filters:
            if filters.get("admin_level_1"):
                entity_conditions.append(Entity.admin_level_1 == filters["admin_level_1"])
            if filters.get("country"):
                entity_conditions.append(Entity.country == filters["country"])
            if filters.get("tags"):
                for tag in filters["tags"]:
                    entity_conditions.append(Entity.tags.contains([tag]))

        entity_query = select(Entity).where(*entity_conditions).limit(limit)
        entity_result = await self.session.execute(entity_query)
        entities = entity_result.scalars().all()

        if not entities:
            return []

        # Get facet types - bulk load instead of N+1 queries
        ft_result = await self.session.execute(
            select(FacetType).where(FacetType.slug.in_(facet_type_slugs))
        )
        facet_types = {ft.slug: ft for ft in ft_result.scalars().all()}

        entity_ids = [e.id for e in entities]

        # Separate history and regular facet types
        history_facet_types = {slug: ft for slug, ft in facet_types.items() if ft.value_type == "history"}
        regular_facet_types = {slug: ft for slug, ft in facet_types.items() if ft.value_type != "history"}

        # Bulk load latest history values using window function
        history_by_entity: Dict[UUID, Dict[str, Any]] = {eid: {} for eid in entity_ids}
        if history_facet_types:
            history_ft_ids = [ft.id for ft in history_facet_types.values()]
            history_subquery = (
                select(
                    FacetValueHistory.entity_id,
                    FacetValueHistory.facet_type_id,
                    FacetValueHistory.value,
                    FacetValueHistory.value_label,
                    FacetValueHistory.recorded_at,
                    func.row_number().over(
                        partition_by=[FacetValueHistory.entity_id, FacetValueHistory.facet_type_id],
                        order_by=FacetValueHistory.recorded_at.desc()
                    ).label("rn")
                )
                .where(
                    FacetValueHistory.entity_id.in_(entity_ids),
                    FacetValueHistory.facet_type_id.in_(history_ft_ids),
                )
            ).subquery()

            history_query = select(history_subquery).where(history_subquery.c.rn == 1)
            history_result = await self.session.execute(history_query)

            # Build lookup: facet_type_id -> slug
            ft_id_to_slug = {ft.id: slug for slug, ft in history_facet_types.items()}

            for row in history_result.all():
                ft_slug = ft_id_to_slug.get(row.facet_type_id)
                if ft_slug:
                    history_by_entity[row.entity_id][ft_slug] = {
                        "value": row.value,
                        "value_label": row.value_label,
                        "recorded_at": row.recorded_at.isoformat() if row.recorded_at else None,
                    }

        # Bulk load regular facet values
        facets_by_entity: Dict[UUID, Dict[str, Any]] = {eid: {} for eid in entity_ids}
        if regular_facet_types:
            regular_ft_ids = [ft.id for ft in regular_facet_types.values()]
            fv_result = await self.session.execute(
                select(FacetValue)
                .where(
                    FacetValue.entity_id.in_(entity_ids),
                    FacetValue.facet_type_id.in_(regular_ft_ids),
                    FacetValue.is_active.is_(True),
                )
            )

            # Build lookup: facet_type_id -> slug
            ft_id_to_slug = {ft.id: slug for slug, ft in regular_facet_types.items()}

            for fv in fv_result.scalars().all():
                ft_slug = ft_id_to_slug.get(fv.facet_type_id)
                if ft_slug and ft_slug not in facets_by_entity[fv.entity_id]:
                    # Only keep first (in case of multiple values)
                    facets_by_entity[fv.entity_id][ft_slug] = {
                        "value": fv.value,
                        "text": fv.text_representation,
                    }

        # Build results using pre-loaded data
        results = []
        for entity in entities:
            entity_data = {
                "entity_id": str(entity.id),
                "entity_name": entity.name,
                "facets": {},
            }

            # Add history facets
            entity_data["facets"].update(history_by_entity.get(entity.id, {}))

            # Add regular facets
            entity_data["facets"].update(facets_by_entity.get(entity.id, {}))

            results.append(entity_data)

        return results

    # =========================================================================
    # Private helper methods
    # =========================================================================

    async def _get_entity_type(self, slug: str) -> Optional[EntityType]:
        """Get entity type by slug."""
        result = await self.session.execute(
            select(EntityType).where(EntityType.slug == slug)
        )
        return result.scalar_one_or_none()

    async def _get_facet_types(self, slugs: List[str]) -> Dict[str, FacetType]:
        """Get facet types by slugs."""
        if not slugs:
            return {}

        result = await self.session.execute(
            select(FacetType).where(FacetType.slug.in_(slugs))
        )
        return {ft.slug: ft for ft in result.scalars().all()}

    async def _query_entities(
        self,
        entity_type: EntityType,
        config: QueryDataConfig,
    ) -> List[Entity]:
        """Query entities based on configuration."""
        conditions = [
            Entity.entity_type_id == entity_type.id,
            Entity.is_active.is_(True),
        ]

        filters = config.filters

        # Apply filters
        if filters.admin_level_1:
            conditions.append(Entity.admin_level_1 == filters.admin_level_1)

        if filters.country:
            conditions.append(Entity.country == filters.country)

        if filters.tags:
            for tag in filters.tags:
                conditions.append(Entity.tags.contains([tag]))

        if filters.entity_names:
            conditions.append(Entity.name.in_(filters.entity_names))

        if filters.entity_ids:
            uuid_ids = [UUID(eid) for eid in filters.entity_ids]
            conditions.append(Entity.id.in_(uuid_ids))

        # Build query
        query = select(Entity).where(*conditions)

        # Apply offset and limit
        query = query.offset(config.offset).limit(config.limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def _load_facet_data(
        self,
        entity_ids: List[UUID],
        facet_type_map: Dict[str, FacetType],
        time_range: Optional[Any] = None,
    ) -> Dict[UUID, Dict[str, Any]]:
        """Load facet data for entities."""
        facet_data: Dict[UUID, Dict[str, Any]] = {eid: {} for eid in entity_ids}

        for ft_slug, ft in facet_type_map.items():
            if ft.value_type == "history":
                # Load history facets
                await self._load_history_facets(
                    facet_data, entity_ids, ft, ft_slug, time_range
                )
            else:
                # Load regular facets
                await self._load_regular_facets(
                    facet_data, entity_ids, ft, ft_slug
                )

        return facet_data

    async def _load_history_facets(
        self,
        facet_data: Dict[UUID, Dict[str, Any]],
        entity_ids: List[UUID],
        facet_type: FacetType,
        facet_slug: str,
        time_range: Optional[Any] = None,
    ) -> None:
        """Load history facet values."""
        latest_only = time_range and hasattr(time_range, 'latest_only') and time_range.latest_only

        if latest_only:
            # Get only latest value per entity using window function
            subquery = (
                select(
                    FacetValueHistory.entity_id,
                    FacetValueHistory.value,
                    FacetValueHistory.value_label,
                    FacetValueHistory.recorded_at,
                    FacetValueHistory.track_key,
                    func.row_number().over(
                        partition_by=FacetValueHistory.entity_id,
                        order_by=FacetValueHistory.recorded_at.desc()
                    ).label("rn")
                )
                .where(
                    FacetValueHistory.entity_id.in_(entity_ids),
                    FacetValueHistory.facet_type_id == facet_type.id,
                )
            ).subquery()

            query = select(subquery).where(subquery.c.rn == 1)
            result = await self.session.execute(query)

            for row in result.all():
                entity_id = row.entity_id
                facet_data[entity_id][facet_slug] = {
                    "value": row.value,
                    "value_label": row.value_label,
                    "recorded_at": row.recorded_at.isoformat() if row.recorded_at else None,
                    "track_key": row.track_key,
                }
        else:
            # Get all history within range
            query = (
                select(FacetValueHistory)
                .where(
                    FacetValueHistory.entity_id.in_(entity_ids),
                    FacetValueHistory.facet_type_id == facet_type.id,
                )
                .order_by(FacetValueHistory.recorded_at.desc())
            )

            if time_range:
                if hasattr(time_range, 'from_date') and time_range.from_date:
                    from_dt = datetime.fromisoformat(time_range.from_date)
                    query = query.where(FacetValueHistory.recorded_at >= from_dt)
                if hasattr(time_range, 'to_date') and time_range.to_date:
                    to_dt = datetime.fromisoformat(time_range.to_date)
                    query = query.where(FacetValueHistory.recorded_at <= to_dt)

            result = await self.session.execute(query)

            for hp in result.scalars().all():
                if facet_slug not in facet_data[hp.entity_id]:
                    facet_data[hp.entity_id][facet_slug] = []

                if isinstance(facet_data[hp.entity_id][facet_slug], list):
                    facet_data[hp.entity_id][facet_slug].append({
                        "value": hp.value,
                        "value_label": hp.value_label,
                        "recorded_at": hp.recorded_at.isoformat() if hp.recorded_at else None,
                        "track_key": hp.track_key,
                    })

    async def _load_regular_facets(
        self,
        facet_data: Dict[UUID, Dict[str, Any]],
        entity_ids: List[UUID],
        facet_type: FacetType,
        facet_slug: str,
    ) -> None:
        """Load regular (non-history) facet values."""
        query = select(FacetValue).where(
            FacetValue.entity_id.in_(entity_ids),
            FacetValue.facet_type_id == facet_type.id,
            FacetValue.is_active.is_(True),
        )

        result = await self.session.execute(query)

        for fv in result.scalars().all():
            facet_data[fv.entity_id][facet_slug] = {
                "value": fv.value,
                "text": fv.text_representation,
            }

    def _sort_data(
        self,
        data: List[Dict[str, Any]],
        sort_by: Optional[str],
        sort_order: str,
        facet_type_map: Dict[str, FacetType],
    ) -> List[Dict[str, Any]]:
        """Sort query results."""
        if not sort_by:
            return data

        reverse = sort_order.lower() == "desc"

        def get_sort_key(item: Dict[str, Any]) -> Any:
            if sort_by == "name":
                return item.get("entity_name", "")

            # Check facets
            facets = item.get("facets", {})
            if sort_by in facets:
                facet_value = facets[sort_by]
                if isinstance(facet_value, dict):
                    return facet_value.get("value", 0) or 0
                return facet_value or 0

            # Check core_attributes
            attrs = item.get("core_attributes", {})
            return attrs.get(sort_by, 0) or 0

        try:
            return sorted(data, key=get_sort_key, reverse=reverse)
        except Exception:
            return data

    def _get_last_update_time(
        self,
        facet_data: Dict[UUID, Dict[str, Any]],
    ) -> Optional[datetime]:
        """Get the most recent update time from facet data."""
        latest = None

        for entity_facets in facet_data.values():
            for facet_value in entity_facets.values():
                if isinstance(facet_value, dict):
                    recorded_at = facet_value.get("recorded_at")
                    if recorded_at:
                        dt = datetime.fromisoformat(recorded_at)
                        if latest is None or dt > latest:
                            latest = dt

        return latest

    def _format_freshness(self, dt: datetime) -> str:
        """Format time difference in human-readable form."""
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        diff = now - dt

        if diff.days > 0:
            return f"{diff.days} Tag(e) alt"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} Stunde(n) alt"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} Minute(n) alt"
        else:
            return "Gerade aktualisiert"

    def _build_suggested_actions(
        self,
        config: QueryDataConfig,
        facet_type_map: Dict[str, FacetType],
    ) -> List[SuggestedAction]:
        """Build suggested follow-up actions."""
        actions = []

        # Always suggest export
        actions.append(SuggestedAction(
            label="Als CSV exportieren",
            action="export_csv",
            icon="mdi-download",
            params={
                "entity_type": config.entity_type,
                "facet_types": config.facet_types,
            },
        ))

        # Check if any history facets - suggest sync setup
        has_history_facets = any(
            ft.value_type == "history" for ft in facet_type_map.values()
        )

        if has_history_facets:
            actions.append(SuggestedAction(
                label="Automatisch aktualisieren",
                action="setup_api_sync",
                icon="mdi-sync",
                params={
                    "entity_type": config.entity_type,
                    "facet_types": config.facet_types,
                },
                description="Richte automatische API-Synchronisation ein",
            ))

        # Suggest visualization change
        actions.append(SuggestedAction(
            label="Visualisierung ändern",
            action="change_visualization",
            icon="mdi-chart-bar",
            params={},
        ))

        return actions
