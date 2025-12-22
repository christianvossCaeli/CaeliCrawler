"""Service for managing facet value history (time-series data)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import structlog
from sqlalchemy import and_, delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Entity, FacetType, FacetValueHistory
from app.models.facet_value import FacetValueSourceType
from app.schemas.facet_value_history import (
    AggregatedDataPoint,
    AggregatedHistoryResponse,
    DateRange,
    EntityHistoryResponse,
    HistoryBulkImportResponse,
    HistoryDataPointCreate,
    HistoryDataPointResponse,
    HistoryStatistics,
    HistoryTrackConfig,
    HistoryTrackResponse,
)

logger = structlog.get_logger()


class FacetHistoryService:
    """Service for managing time-series facet data."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_data_point(
        self,
        entity_id: UUID,
        facet_type_id: UUID,
        recorded_at: datetime,
        value: float,
        track_key: str = "default",
        value_label: Optional[str] = None,
        annotations: Optional[Dict[str, Any]] = None,
        source_type: FacetValueSourceType = FacetValueSourceType.MANUAL,
        source_document_id: Optional[UUID] = None,
        source_url: Optional[str] = None,
        confidence_score: float = 1.0,
        ai_model_used: Optional[str] = None,
    ) -> FacetValueHistory:
        """
        Add a single data point to the history.

        Args:
            entity_id: The entity this data belongs to
            facet_type_id: The facet type (must be HISTORY type)
            recorded_at: When this value was recorded/measured
            value: The numeric value
            track_key: Track identifier for multi-track support
            value_label: Formatted value for display
            annotations: Additional metadata
            source_type: How this value was created
            source_document_id: Source document if applicable
            source_url: Source URL if applicable
            confidence_score: Confidence in the value (0-1)
            ai_model_used: AI model if extracted by AI

        Returns:
            The created FacetValueHistory object

        Raises:
            ValueError: If facet_type is not HISTORY type or entity doesn't exist
        """
        # Validate facet type
        facet_type = await self._get_facet_type(facet_type_id)
        if facet_type.value_type != "history":
            raise ValueError(
                f"FacetType '{facet_type.slug}' is not a HISTORY type"
            )

        # Validate entity exists
        entity = await self._get_entity(entity_id)
        if not entity:
            raise ValueError(f"Entity {entity_id} not found")

        # Create the data point
        data_point = FacetValueHistory(
            entity_id=entity_id,
            facet_type_id=facet_type_id,
            track_key=track_key,
            recorded_at=recorded_at,
            value=value,
            value_label=value_label,
            annotations=annotations or {},
            source_type=source_type,
            source_document_id=source_document_id,
            source_url=source_url,
            confidence_score=confidence_score,
            ai_model_used=ai_model_used,
        )

        self.session.add(data_point)
        await self.session.flush()

        logger.info(
            "history_data_point_created",
            entity_id=str(entity_id),
            facet_type=facet_type.slug,
            track_key=track_key,
            recorded_at=recorded_at.isoformat(),
            value=value,
        )

        return data_point

    async def add_data_points_bulk(
        self,
        entity_id: UUID,
        facet_type_id: UUID,
        data_points: List[HistoryDataPointCreate],
        skip_duplicates: bool = True,
    ) -> HistoryBulkImportResponse:
        """
        Bulk import multiple data points.

        Args:
            entity_id: The entity this data belongs to
            facet_type_id: The facet type
            data_points: List of data points to import
            skip_duplicates: Whether to skip existing data points

        Returns:
            Import statistics
        """
        # Validate
        facet_type = await self._get_facet_type(facet_type_id)
        if facet_type.value_type != "history":
            raise ValueError(f"FacetType '{facet_type.slug}' is not a HISTORY type")

        entity = await self._get_entity(entity_id)
        if not entity:
            raise ValueError(f"Entity {entity_id} not found")

        created = 0
        skipped = 0
        errors = []

        for dp in data_points:
            try:
                if skip_duplicates:
                    # Check if exists
                    existing = await self.session.execute(
                        select(FacetValueHistory.id).where(
                            FacetValueHistory.entity_id == entity_id,
                            FacetValueHistory.facet_type_id == facet_type_id,
                            FacetValueHistory.track_key == dp.track_key,
                            FacetValueHistory.recorded_at == dp.recorded_at,
                        )
                    )
                    if existing.scalar_one_or_none():
                        skipped += 1
                        continue

                data_point = FacetValueHistory(
                    entity_id=entity_id,
                    facet_type_id=facet_type_id,
                    track_key=dp.track_key,
                    recorded_at=dp.recorded_at,
                    value=dp.value,
                    value_label=dp.value_label,
                    annotations=dp.annotations,
                    source_type=dp.source_type,
                    source_url=dp.source_url,
                    confidence_score=dp.confidence_score,
                )
                self.session.add(data_point)
                created += 1

            except Exception as e:
                errors.append(f"Error at {dp.recorded_at}: {str(e)}")

        await self.session.flush()

        logger.info(
            "history_bulk_import_completed",
            entity_id=str(entity_id),
            facet_type=facet_type.slug,
            created=created,
            skipped=skipped,
            errors=len(errors),
        )

        return HistoryBulkImportResponse(
            created=created, skipped=skipped, errors=errors
        )

    async def get_history(
        self,
        entity_id: UUID,
        facet_type_id: UUID,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        track_keys: Optional[List[str]] = None,
        limit: int = 1000,
    ) -> EntityHistoryResponse:
        """
        Get history data for an entity+facet combination.

        Args:
            entity_id: Entity ID
            facet_type_id: Facet type ID
            from_date: Start date filter
            to_date: End date filter
            track_keys: Filter by specific tracks
            limit: Maximum number of points to return

        Returns:
            Complete history response with tracks and statistics
        """
        # Load entity and facet type
        entity = await self._get_entity(entity_id)
        facet_type = await self._get_facet_type(facet_type_id)

        # Build query
        query = (
            select(FacetValueHistory)
            .where(
                FacetValueHistory.entity_id == entity_id,
                FacetValueHistory.facet_type_id == facet_type_id,
            )
            .order_by(FacetValueHistory.recorded_at.asc())
            .limit(limit)
        )

        if from_date:
            query = query.where(FacetValueHistory.recorded_at >= from_date)
        if to_date:
            query = query.where(FacetValueHistory.recorded_at <= to_date)
        if track_keys:
            query = query.where(FacetValueHistory.track_key.in_(track_keys))

        result = await self.session.execute(query)
        data_points = result.scalars().all()

        # Parse track config from facet type schema
        track_configs = self._parse_track_configs(facet_type)

        # Group by track
        tracks_dict: Dict[str, List[FacetValueHistory]] = {}
        for dp in data_points:
            if dp.track_key not in tracks_dict:
                tracks_dict[dp.track_key] = []
            tracks_dict[dp.track_key].append(dp)

        # Build track responses
        tracks = []
        for track_key, points in tracks_dict.items():
            config = track_configs.get(
                track_key,
                HistoryTrackConfig(key=track_key, label=track_key, color="#1976D2"),
            )
            tracks.append(
                HistoryTrackResponse(
                    track_key=track_key,
                    label=config.label,
                    color=config.color,
                    style=config.style,
                    data_points=[
                        HistoryDataPointResponse.model_validate(p) for p in points
                    ],
                    point_count=len(points),
                )
            )

        # Calculate statistics
        all_points = list(data_points)
        statistics = self._calculate_statistics(all_points)

        # Date range
        date_range = DateRange()
        if all_points:
            date_range.from_date = min(p.recorded_at for p in all_points)
            date_range.to_date = max(p.recorded_at for p in all_points)

        # Extract unit info from schema
        schema = facet_type.value_schema or {}
        props = schema.get("properties", {})

        return EntityHistoryResponse(
            entity_id=entity_id,
            entity_name=entity.name,
            facet_type_id=facet_type_id,
            facet_type_slug=facet_type.slug,
            facet_type_name=facet_type.name,
            unit=props.get("unit", ""),
            unit_label=props.get("unit_label", ""),
            precision=props.get("precision", 2),
            tracks=tracks,
            date_range=date_range,
            statistics=statistics,
            total_points=len(all_points),
        )

    async def aggregate_history(
        self,
        entity_id: UUID,
        facet_type_id: UUID,
        interval: str = "month",
        method: str = "avg",
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        track_keys: Optional[List[str]] = None,
    ) -> AggregatedHistoryResponse:
        """
        Get aggregated history data.

        Args:
            entity_id: Entity ID
            facet_type_id: Facet type ID
            interval: Aggregation interval (day, week, month, quarter, year)
            method: Aggregation method (avg, sum, min, max)
            from_date: Start date filter
            to_date: End date filter
            track_keys: Filter by tracks

        Returns:
            Aggregated history response
        """
        # Map interval to PostgreSQL date_trunc format
        interval_map = {
            "day": "day",
            "week": "week",
            "month": "month",
            "quarter": "quarter",
            "year": "year",
        }
        pg_interval = interval_map.get(interval, "month")

        # Map method to SQL function
        agg_func_map = {
            "avg": func.avg,
            "sum": func.sum,
            "min": func.min,
            "max": func.max,
        }
        agg_func = agg_func_map.get(method, func.avg)

        # Build aggregation query
        interval_start = func.date_trunc(pg_interval, FacetValueHistory.recorded_at)

        query = (
            select(
                interval_start.label("interval_start"),
                FacetValueHistory.track_key,
                agg_func(FacetValueHistory.value).label("value"),
                func.count(FacetValueHistory.id).label("point_count"),
                func.min(FacetValueHistory.value).label("min_value"),
                func.max(FacetValueHistory.value).label("max_value"),
            )
            .where(
                FacetValueHistory.entity_id == entity_id,
                FacetValueHistory.facet_type_id == facet_type_id,
            )
            .group_by(interval_start, FacetValueHistory.track_key)
            .order_by(interval_start.asc())
        )

        if from_date:
            query = query.where(FacetValueHistory.recorded_at >= from_date)
        if to_date:
            query = query.where(FacetValueHistory.recorded_at <= to_date)
        if track_keys:
            query = query.where(FacetValueHistory.track_key.in_(track_keys))

        result = await self.session.execute(query)
        rows = result.all()

        # Build response
        data = []
        for row in rows:
            # Calculate interval end based on interval type
            interval_end = self._calculate_interval_end(row.interval_start, pg_interval)
            data.append(
                AggregatedDataPoint(
                    interval_start=row.interval_start,
                    interval_end=interval_end,
                    track_key=row.track_key,
                    value=float(row.value) if row.value else 0.0,
                    point_count=row.point_count,
                    min_value=float(row.min_value) if row.min_value else None,
                    max_value=float(row.max_value) if row.max_value else None,
                )
            )

        # Calculate actual date range from data
        date_range = DateRange()
        if data:
            date_range.from_date = min(d.interval_start for d in data)
            date_range.to_date = max(d.interval_end for d in data)

        return AggregatedHistoryResponse(
            entity_id=entity_id,
            facet_type_id=facet_type_id,
            interval=interval,
            method=method,
            data=data,
            date_range=date_range,
        )

    async def update_data_point(
        self,
        data_point_id: UUID,
        value: Optional[float] = None,
        value_label: Optional[str] = None,
        annotations: Optional[Dict[str, Any]] = None,
        human_verified: Optional[bool] = None,
        verified_by: Optional[str] = None,
    ) -> Optional[FacetValueHistory]:
        """Update a history data point."""
        result = await self.session.execute(
            select(FacetValueHistory).where(FacetValueHistory.id == data_point_id)
        )
        data_point = result.scalar_one_or_none()

        if not data_point:
            return None

        if value is not None:
            data_point.value = value
        if value_label is not None:
            data_point.value_label = value_label
        if annotations is not None:
            data_point.annotations = annotations
        if human_verified is not None:
            data_point.human_verified = human_verified
            if human_verified and verified_by:
                data_point.verified_by = verified_by
                data_point.verified_at = datetime.now(timezone.utc)

        await self.session.flush()
        return data_point

    async def delete_data_point(self, data_point_id: UUID) -> bool:
        """Delete a single data point."""
        result = await self.session.execute(
            delete(FacetValueHistory).where(FacetValueHistory.id == data_point_id)
        )
        return result.rowcount > 0

    async def delete_data_points(
        self,
        entity_id: UUID,
        facet_type_id: UUID,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        track_key: Optional[str] = None,
    ) -> int:
        """Delete multiple data points based on criteria."""
        conditions = [
            FacetValueHistory.entity_id == entity_id,
            FacetValueHistory.facet_type_id == facet_type_id,
        ]

        if from_date:
            conditions.append(FacetValueHistory.recorded_at >= from_date)
        if to_date:
            conditions.append(FacetValueHistory.recorded_at <= to_date)
        if track_key:
            conditions.append(FacetValueHistory.track_key == track_key)

        result = await self.session.execute(
            delete(FacetValueHistory).where(and_(*conditions))
        )
        return result.rowcount

    # =========================================================================
    # Private helper methods
    # =========================================================================

    async def _get_entity(self, entity_id: UUID) -> Optional[Entity]:
        """Get entity by ID."""
        result = await self.session.execute(
            select(Entity).where(Entity.id == entity_id)
        )
        return result.scalar_one_or_none()

    async def _get_facet_type(self, facet_type_id: UUID) -> FacetType:
        """Get facet type by ID, raise if not found."""
        result = await self.session.execute(
            select(FacetType).where(FacetType.id == facet_type_id)
        )
        facet_type = result.scalar_one_or_none()
        if not facet_type:
            raise ValueError(f"FacetType {facet_type_id} not found")
        return facet_type

    def _parse_track_configs(
        self, facet_type: FacetType
    ) -> Dict[str, HistoryTrackConfig]:
        """Parse track configurations from facet type schema."""
        schema = facet_type.value_schema or {}
        props = schema.get("properties", {})
        tracks_config = props.get("tracks", {})

        configs = {}
        for key, config in tracks_config.items():
            configs[key] = HistoryTrackConfig(
                key=key,
                label=config.get("label", key),
                color=config.get("color", "#1976D2"),
                style=config.get("style", "solid"),
            )

        # Always include default if not configured
        if "default" not in configs:
            configs["default"] = HistoryTrackConfig(
                key="default", label="Default", color="#1976D2"
            )

        return configs

    def _calculate_statistics(
        self, data_points: List[FacetValueHistory]
    ) -> HistoryStatistics:
        """Calculate statistics from data points."""
        if not data_points:
            return HistoryStatistics()

        values = [dp.value for dp in data_points]
        sorted_by_date = sorted(data_points, key=lambda x: x.recorded_at)

        oldest_value = sorted_by_date[0].value
        latest_value = sorted_by_date[-1].value

        # Calculate trend
        if len(sorted_by_date) >= 2:
            change_absolute = latest_value - oldest_value
            if oldest_value != 0:
                change_percent = (change_absolute / oldest_value) * 100
            else:
                change_percent = 0.0 if change_absolute == 0 else 100.0

            if change_percent > 1:
                trend = "up"
            elif change_percent < -1:
                trend = "down"
            else:
                trend = "stable"
        else:
            change_absolute = 0.0
            change_percent = 0.0
            trend = "stable"

        return HistoryStatistics(
            total_points=len(data_points),
            min_value=min(values),
            max_value=max(values),
            avg_value=sum(values) / len(values),
            latest_value=latest_value,
            oldest_value=oldest_value,
            trend=trend,
            change_percent=round(change_percent, 2),
            change_absolute=round(change_absolute, 2),
        )

    def _calculate_interval_end(
        self, interval_start: datetime, interval: str
    ) -> datetime:
        """Calculate interval end based on interval type."""
        from dateutil.relativedelta import relativedelta

        interval_deltas = {
            "day": relativedelta(days=1),
            "week": relativedelta(weeks=1),
            "month": relativedelta(months=1),
            "quarter": relativedelta(months=3),
            "year": relativedelta(years=1),
        }

        delta = interval_deltas.get(interval, relativedelta(months=1))
        return interval_start + delta
