"""Summary Executor Service.

Executes custom summaries by running queries for each widget
and caching the results.
"""

import asyncio
import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    CustomSummary,
    Entity,
    EntityType,
    FacetType,
    FacetValue,
    SummaryExecution,
    SummaryWidget,
)
from app.models.summary_execution import ExecutionStatus

logger = structlog.get_logger(__name__)

# Whitelist of allowed filter keys to prevent injection attacks
ALLOWED_FILTER_KEYS = frozenset(
    {
        "admin_level_1",
        "country",
        "tags",
        "name",
        "is_active",
    }
)

# Whitelist of allowed sort fields to prevent injection attacks
ALLOWED_SORT_FIELDS = frozenset(
    {
        "name",
        "created_at",
        "updated_at",
        "entity_name",
        "entity_type",
        "admin_level_1",
        "country",
        "latitude",
        "longitude",
        # Core attributes (windparks, etc.)
        "status",
        "area_ha",
        "power_mw",
        "wea_count",
        "wind_speed_ms",
        # Facet-based sorting (dot notation validated separately)
        "facets.points",
        "facets.goals",
        "facets.population",
        "facets.area",
        "facets.founded",
        "facets.value",
    }
)

# Maximum limits for query execution to prevent resource exhaustion
MAX_QUERY_LIMIT = 1000  # Maximum entities per widget query
DEFAULT_QUERY_LIMIT = 100  # Default if not specified
MAX_FACET_VALUES_PER_QUERY = 5000  # Maximum facet values per query
MAX_CACHED_DATA_SIZE_BYTES = 10_000_000  # 10MB limit for cached data

# Query timeout settings (in seconds)
QUERY_TIMEOUT_SECONDS = 30  # Individual query timeout
WIDGET_EXECUTION_TIMEOUT_SECONDS = 60  # Total widget execution timeout


class SummaryExecutor:
    """
    Executes custom summaries and caches results.

    The executor:
    1. Loads the summary with all widgets
    2. Executes queries for each widget
    3. Optionally checks relevance (if enabled)
    4. Caches results in SummaryExecution
    5. Updates summary statistics
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def execute_summary(
        self,
        summary_id: UUID,
        triggered_by: str = "manual",
        trigger_details: dict[str, Any] | None = None,
        force: bool = False,
    ) -> SummaryExecution:
        """
        Execute a summary and cache the results.

        Args:
            summary_id: ID of the summary to execute
            triggered_by: Who/what triggered (manual, cron, crawl_event, api)
            trigger_details: Additional context (e.g., crawl_job_id)
            force: Skip relevance check and force execution

        Returns:
            SummaryExecution with results

        Raises:
            ValueError: If summary not found
        """
        # Check for concurrent execution - if another execution is running, skip
        running_exec = await self.session.execute(
            select(SummaryExecution)
            .where(
                SummaryExecution.summary_id == summary_id,
                SummaryExecution.status == ExecutionStatus.RUNNING,
            )
            .limit(1)
        )
        if running_exec.scalar_one_or_none():
            logger.info(
                "summary_execution_skipped_concurrent",
                summary_id=str(summary_id),
                reason="Another execution is already running",
            )
            # Return a placeholder execution indicating skip
            skipped_execution = SummaryExecution(
                summary_id=summary_id,
                status=ExecutionStatus.SKIPPED,
                triggered_by=triggered_by,
                trigger_details=trigger_details,
                relevance_reason="Übersprungen: Eine andere Ausführung läuft bereits",
                completed_at=datetime.now(UTC),
            )
            self.session.add(skipped_execution)
            await self.session.commit()
            return skipped_execution

        # Load summary with widgets using FOR UPDATE to prevent concurrent modifications
        result = await self.session.execute(
            select(CustomSummary)
            .options(selectinload(CustomSummary.widgets))
            .where(CustomSummary.id == summary_id)
            .with_for_update(skip_locked=True)
        )
        summary = result.scalar_one_or_none()

        if not summary:
            # Could be locked by another execution or not found
            # Check if it exists at all
            exists_result = await self.session.execute(select(CustomSummary.id).where(CustomSummary.id == summary_id))
            if exists_result.scalar_one_or_none():
                logger.info(
                    "summary_execution_skipped_locked",
                    summary_id=str(summary_id),
                    reason="Summary is locked by another transaction",
                )
                skipped_execution = SummaryExecution(
                    summary_id=summary_id,
                    status=ExecutionStatus.SKIPPED,
                    triggered_by=triggered_by,
                    trigger_details=trigger_details,
                    relevance_reason="Übersprungen: Summary ist durch eine andere Transaktion gesperrt",
                    completed_at=datetime.now(UTC),
                )
                self.session.add(skipped_execution)
                await self.session.commit()
                return skipped_execution
            raise ValueError(f"Summary {summary_id} not found")

        # Create execution record
        execution = SummaryExecution(
            summary_id=summary_id,
            status=ExecutionStatus.RUNNING,
            triggered_by=triggered_by,
            trigger_details=trigger_details,
            started_at=datetime.now(UTC),
        )
        self.session.add(execution)
        await self.session.flush()

        try:
            # Execute queries for all widgets
            cached_data: dict[str, Any] = {}

            for widget in summary.widgets:
                widget_key = f"widget_{widget.id}"
                try:
                    # Execute with timeout to prevent long-running queries
                    widget_data = await asyncio.wait_for(
                        self._execute_widget_query(widget),
                        timeout=WIDGET_EXECUTION_TIMEOUT_SECONDS,
                    )
                    cached_data[widget_key] = widget_data
                except TimeoutError:
                    logger.warning(
                        "widget_query_timeout",
                        widget_id=str(widget.id),
                        timeout_seconds=WIDGET_EXECUTION_TIMEOUT_SECONDS,
                    )
                    cached_data[widget_key] = {
                        "data": [],
                        "total": 0,
                        "error": f"Query timeout after {WIDGET_EXECUTION_TIMEOUT_SECONDS}s",
                        "timeout": True,
                    }
                except Exception as e:
                    logger.warning(
                        "widget_query_failed",
                        widget_id=str(widget.id),
                        error=str(e),
                    )
                    cached_data[widget_key] = {
                        "data": [],
                        "total": 0,
                        "error": str(e),
                    }

            # Check cached_data size to prevent memory/storage issues
            cached_data_size = len(json.dumps(cached_data, default=str).encode("utf-8"))
            if cached_data_size > MAX_CACHED_DATA_SIZE_BYTES:
                logger.warning(
                    "cached_data_size_exceeded",
                    summary_id=str(summary_id),
                    size_bytes=cached_data_size,
                    max_bytes=MAX_CACHED_DATA_SIZE_BYTES,
                )
                # Truncate data for oversized widgets
                cached_data = self._truncate_cached_data(cached_data, MAX_CACHED_DATA_SIZE_BYTES)

            # Calculate data hash for change detection
            data_hash = self._calculate_data_hash(cached_data)

            # Check for changes (only if there was a previous execution)
            # First execution has no "changes" because there's nothing to compare to
            has_changes = summary.last_data_hash is not None and summary.last_data_hash != data_hash

            # Relevance check (if enabled and not forced)
            if summary.check_relevance and not force and has_changes:
                relevance = await self._check_relevance(summary, cached_data, data_hash)

                if not relevance["should_update"]:
                    execution.status = ExecutionStatus.SKIPPED
                    execution.relevance_score = relevance["score"]
                    execution.relevance_reason = relevance["reason"]
                    execution.data_hash = data_hash
                    execution.has_changes = False
                    execution.completed_at = datetime.now(UTC)
                    execution.duration_ms = self._calculate_duration(execution)
                    await self.session.commit()

                    logger.info(
                        "summary_execution_skipped",
                        summary_id=str(summary_id),
                        reason=relevance["reason"],
                    )
                    return execution

                execution.relevance_score = relevance["score"]
                execution.relevance_reason = relevance["reason"]

            # Store results
            execution.cached_data = cached_data
            execution.data_hash = data_hash
            execution.has_changes = has_changes
            execution.status = ExecutionStatus.COMPLETED
            execution.completed_at = datetime.now(UTC)
            execution.duration_ms = self._calculate_duration(execution)

            # Update summary statistics atomically using SQL UPDATE
            # This prevents race conditions with concurrent executions
            await self.session.execute(
                update(CustomSummary)
                .where(CustomSummary.id == summary_id)
                .values(
                    last_executed_at=execution.completed_at,
                    execution_count=CustomSummary.execution_count + 1,
                    last_data_hash=data_hash,
                )
            )

            # Auto-expand: Detect and add new relevant widgets
            expansion_suggestions = []
            if summary.auto_expand and has_changes:
                expansion_suggestions = await self._check_auto_expand(summary, cached_data)
                if expansion_suggestions:
                    execution.expansion_suggestions = [s.to_dict() for s in expansion_suggestions]

            await self.session.commit()

            logger.info(
                "summary_execution_completed",
                summary_id=str(summary_id),
                execution_id=str(execution.id),
                duration_ms=execution.duration_ms,
                has_changes=has_changes,
            )

            return execution

        except TimeoutError:
            # Timeout errors - mark as failed, don't retry
            await self.session.rollback()
            execution.status = ExecutionStatus.FAILED
            execution.error_message = "Execution timeout - query took too long"
            execution.completed_at = datetime.now(UTC)
            execution.duration_ms = self._calculate_duration(execution)
            await self._safe_commit(summary_id)
            logger.error(
                "summary_execution_timeout",
                summary_id=str(summary_id),
                error="Execution timeout",
            )
            raise

        except (ConnectionError, OSError) as e:
            # Network/connection errors - worth retrying
            await self.session.rollback()
            execution.status = ExecutionStatus.FAILED
            execution.error_message = f"Connection error: {str(e)}"
            execution.completed_at = datetime.now(UTC)
            execution.duration_ms = self._calculate_duration(execution)
            await self._safe_commit(summary_id)
            logger.error(
                "summary_execution_connection_error",
                summary_id=str(summary_id),
                error=str(e),
            )
            raise

        except ValueError as e:
            # Validation errors - don't retry
            await self.session.rollback()
            execution.status = ExecutionStatus.FAILED
            execution.error_message = f"Validation error: {str(e)}"
            execution.completed_at = datetime.now(UTC)
            execution.duration_ms = self._calculate_duration(execution)
            await self._safe_commit(summary_id)
            logger.error(
                "summary_execution_validation_error",
                summary_id=str(summary_id),
                error=str(e),
            )
            raise

        except Exception as e:
            # Generic errors - log with full context
            await self.session.rollback()
            execution.status = ExecutionStatus.FAILED
            execution.error_message = f"{type(e).__name__}: {str(e)}"
            execution.completed_at = datetime.now(UTC)
            execution.duration_ms = self._calculate_duration(execution)
            await self._safe_commit(summary_id)
            logger.exception(
                "summary_execution_failed",
                summary_id=str(summary_id),
                error_type=type(e).__name__,
                error=str(e),
            )
            raise

    async def _safe_commit(self, summary_id: UUID) -> None:
        """Safely commit, rolling back on failure."""
        try:
            await self.session.commit()
        except Exception as commit_error:
            logger.error(
                "failed_to_save_execution_error",
                summary_id=str(summary_id),
                commit_error=str(commit_error),
            )
            await self.session.rollback()

    async def _execute_widget_query(
        self,
        widget: SummaryWidget,
    ) -> dict[str, Any]:
        """
        Execute query for a single widget.

        Uses the widget's query_config to fetch data from Entity-Facet system.

        Args:
            widget: The widget to execute

        Returns:
            Dict with data, total, and query_time_ms
        """
        import time

        start_time = time.time()
        query_config = widget.query_config

        entity_type_slug = query_config.get("entity_type")
        facet_types = query_config.get("facet_types", [])
        filters = query_config.get("filters", {})
        sort_by = query_config.get("sort_by")
        sort_order = query_config.get("sort_order", "desc")
        # Enforce query limit to prevent resource exhaustion
        requested_limit = query_config.get("limit", DEFAULT_QUERY_LIMIT)
        limit = min(requested_limit, MAX_QUERY_LIMIT) if requested_limit else DEFAULT_QUERY_LIMIT
        aggregate = query_config.get("aggregate")
        query_config.get("group_by")

        # Handle aggregation queries
        if aggregate == "count" and not facet_types:
            count = await self._count_entities(entity_type_slug, filters)
            query_time = int((time.time() - start_time) * 1000)
            return {
                "data": [{"value": count}],
                "total": 1,
                "query_time_ms": query_time,
            }

        # Get entity type
        entity_type = await self._get_entity_type(entity_type_slug)
        if not entity_type:
            return {"data": [], "total": 0, "error": f"Entity type '{entity_type_slug}' not found"}

        # Build entity query
        query = select(Entity).where(
            Entity.entity_type_id == entity_type.id,
            Entity.is_active,
        )

        # Apply filters
        query = self._apply_filters(query, filters)

        # Execute query
        result = await self.session.execute(query)
        entities = result.scalars().all()

        if not entities:
            query_time = int((time.time() - start_time) * 1000)
            return {"data": [], "total": 0, "query_time_ms": query_time}

        # Load facet values
        entity_ids = [e.id for e in entities]
        facet_data = await self._load_facet_values(entity_ids, facet_types)

        # Load parent entities for coordinates fallback
        parent_ids = [e.parent_id for e in entities if e.parent_id and e.latitude is None]
        parent_coords = {}
        if parent_ids:
            parent_result = await self.session.execute(select(Entity).where(Entity.id.in_(parent_ids)))
            for parent in parent_result.scalars():
                if parent.latitude is not None and parent.longitude is not None:
                    parent_coords[parent.id] = (float(parent.latitude), float(parent.longitude))

        # Build result data
        data = []
        for entity in entities:
            entity_data = {
                "entity_id": str(entity.id),
                "name": entity.name,
            }

            # Add core attributes (contains most of the entity data like status, area, power, etc.)
            if entity.core_attributes:
                entity_data.update(entity.core_attributes)

            # Add location attributes
            if entity.admin_level_1:
                entity_data["admin_level_1"] = entity.admin_level_1
            if entity.country:
                entity_data["country"] = entity.country

            # Use own coordinates, or fallback to parent coordinates
            if entity.latitude is not None and entity.longitude is not None:
                entity_data["latitude"] = float(entity.latitude)
                entity_data["longitude"] = float(entity.longitude)
            elif entity.parent_id and entity.parent_id in parent_coords:
                lat, lng = parent_coords[entity.parent_id]
                entity_data["latitude"] = lat
                entity_data["longitude"] = lng
                entity_data["coords_from_parent"] = True  # Flag to indicate fallback

            # Add facet values
            entity_data["facets"] = facet_data.get(entity.id, {})

            data.append(entity_data)

        # Apply sorting (with strict whitelist validation)
        if sort_by:
            # Validate sort_by against whitelist to prevent injection
            # For facet fields, validate the full path is in whitelist
            is_valid_sort = sort_by in ALLOWED_SORT_FIELDS

            # Also allow facet.{slug}.value pattern with slug validation
            if not is_valid_sort and sort_by.startswith("facets."):
                parts = sort_by.split(".")
                # Must be facets.{slug}.value format
                if len(parts) == 3 and parts[2] == "value":
                    facet_slug = parts[1]
                    # Validate facet slug: alphanumeric, hyphens, underscores only
                    if facet_slug.replace("-", "").replace("_", "").isalnum():
                        is_valid_sort = True

            if is_valid_sort:
                data = self._sort_data(data, sort_by, sort_order)
            else:
                logger.warning("invalid_sort_field_ignored", sort_by=sort_by)

        # Apply limit
        total = len(data)
        if limit and limit < total:
            data = data[:limit]

        query_time = int((time.time() - start_time) * 1000)

        return {
            "data": data,
            "total": total,
            "query_time_ms": query_time,
        }

    async def _get_entity_type(self, slug: str) -> EntityType | None:
        """Get entity type by slug."""
        result = await self.session.execute(select(EntityType).where(EntityType.slug == slug))
        return result.scalar_one_or_none()

    async def _count_entities(
        self,
        entity_type_slug: str,
        filters: dict[str, Any],
    ) -> int:
        """Count entities matching filters."""
        from sqlalchemy import func

        entity_type = await self._get_entity_type(entity_type_slug)
        if not entity_type:
            return 0

        query = select(func.count(Entity.id)).where(
            Entity.entity_type_id == entity_type.id,
            Entity.is_active,
        )
        query = self._apply_filters(query, filters)

        result = await self.session.execute(query)
        return result.scalar() or 0

    def _apply_filters(self, query, filters: dict[str, Any]):
        """Apply filters to entity query.

        Only whitelisted filter keys are applied to prevent injection.
        Unknown keys are logged and ignored.
        """
        if not filters:
            return query

        # Filter out unknown keys
        unknown_keys = set(filters.keys()) - ALLOWED_FILTER_KEYS
        if unknown_keys:
            logger.warning(
                "unknown_filter_keys_ignored",
                unknown_keys=list(unknown_keys),
                allowed_keys=list(ALLOWED_FILTER_KEYS),
            )

        if filters.get("admin_level_1"):
            query = query.where(Entity.admin_level_1 == filters["admin_level_1"])

        if filters.get("country"):
            query = query.where(Entity.country == filters["country"])

        if filters.get("tags"):
            # Tags are stored as array, check for overlap
            tags = filters["tags"]
            if isinstance(tags, list):
                query = query.where(Entity.tags.overlap(tags))

        if filters.get("name"):
            # Partial match on name - escape LIKE wildcards to prevent LIKE injection
            name_filter = filters["name"]
            if isinstance(name_filter, str) and len(name_filter) <= 255:
                # Escape LIKE special characters
                safe_name = name_filter.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                query = query.where(Entity.name.ilike(f"%{safe_name}%", escape="\\"))

        return query

    async def _load_facet_values(
        self,
        entity_ids: list[UUID],
        facet_type_slugs: list[str],
    ) -> dict[UUID, dict[str, Any]]:
        """Load facet values for entities."""
        if not entity_ids or not facet_type_slugs:
            return {}

        # Get facet types
        ft_result = await self.session.execute(select(FacetType).where(FacetType.slug.in_(facet_type_slugs)))
        facet_types = {ft.id: ft for ft in ft_result.scalars().all()}

        if not facet_types:
            return {}

        # Get facet values with limit to prevent resource exhaustion
        fv_result = await self.session.execute(
            select(FacetValue)
            .where(
                FacetValue.entity_id.in_(entity_ids),
                FacetValue.facet_type_id.in_(facet_types.keys()),
            )
            .limit(MAX_FACET_VALUES_PER_QUERY)
        )
        facet_values = fv_result.scalars().all()

        # Warn if limit was hit
        if len(facet_values) >= MAX_FACET_VALUES_PER_QUERY:
            logger.warning(
                "facet_values_limit_reached",
                entity_count=len(entity_ids),
                facet_types=facet_type_slugs,
                limit=MAX_FACET_VALUES_PER_QUERY,
            )

        # Build result dict
        result: dict[UUID, dict[str, Any]] = {}
        for fv in facet_values:
            if fv.entity_id not in result:
                result[fv.entity_id] = {}

            ft = facet_types.get(fv.facet_type_id)
            if ft:
                result[fv.entity_id][ft.slug] = {
                    "value": fv.value,
                    "confidence": fv.confidence,
                    "source_type": fv.source_type.value if fv.source_type else None,
                }

        return result

    def _sort_data(
        self,
        data: list[dict[str, Any]],
        sort_by: str,
        sort_order: str,
    ) -> list[dict[str, Any]]:
        """Sort data by field."""
        reverse = sort_order == "desc"

        def get_sort_value(item: dict[str, Any]) -> Any:
            if sort_by.startswith("facets."):
                facet_key = sort_by.replace("facets.", "")
                facet_data = item.get("facets", {}).get(facet_key, {})
                value = facet_data.get("value")
                # Handle numeric values in JSONB
                if isinstance(value, (int, float)):
                    return value
                return 0
            return item.get(sort_by, "")

        return sorted(data, key=get_sort_value, reverse=reverse)

    def _truncate_cached_data(
        self,
        cached_data: dict[str, Any],
        max_size_bytes: int,
    ) -> dict[str, Any]:
        """
        Truncate cached data to fit within size limit.

        Progressively reduces data in each widget until the total size
        is below the limit.

        Args:
            cached_data: The original cached data
            max_size_bytes: Maximum allowed size in bytes

        Returns:
            Truncated cached data
        """

        # Calculate current size
        def get_size(data: dict[str, Any]) -> int:
            return len(json.dumps(data, default=str).encode("utf-8"))

        current_size = get_size(cached_data)
        if current_size <= max_size_bytes:
            return cached_data

        # Sort widgets by data size (largest first)
        widget_sizes = []
        for key, widget_data in cached_data.items():
            if isinstance(widget_data, dict) and "data" in widget_data:
                widget_size = get_size(widget_data)
                widget_sizes.append((key, widget_size, widget_data))

        widget_sizes.sort(key=lambda x: x[1], reverse=True)

        # Progressively truncate largest widgets
        truncated_data = dict(cached_data)
        for key, _, widget_data in widget_sizes:
            if get_size(truncated_data) <= max_size_bytes:
                break

            if isinstance(widget_data, dict) and "data" in widget_data:
                data_list = widget_data.get("data", [])
                if isinstance(data_list, list) and len(data_list) > 10:
                    # Truncate to 50% or minimum 10 items
                    new_length = max(len(data_list) // 2, 10)
                    truncated_data[key] = {
                        **widget_data,
                        "data": data_list[:new_length],
                        "total": widget_data.get("total", len(data_list)),
                        "truncated": True,
                        "truncated_from": len(data_list),
                    }

        # Final check - if still too large, truncate more aggressively
        if get_size(truncated_data) > max_size_bytes:
            for key, _, _widget_data in widget_sizes:
                if isinstance(truncated_data.get(key), dict):
                    data_list = truncated_data[key].get("data", [])
                    if isinstance(data_list, list) and len(data_list) > 10:
                        truncated_data[key]["data"] = data_list[:10]
                        truncated_data[key]["truncated"] = True

        logger.info(
            "cached_data_truncated",
            original_size=current_size,
            truncated_size=get_size(truncated_data),
        )

        return truncated_data

    def _calculate_data_hash(self, data: dict[str, Any]) -> str:
        """Calculate SHA256 hash of data for change detection.

        Excludes non-deterministic fields like query_time_ms that change
        on every execution even when the actual data is the same.
        """

        def consistent_json_encoder(obj: Any) -> Any:
            """Encode objects consistently for deterministic hashing."""
            from datetime import date, datetime
            from decimal import Decimal
            from uuid import UUID

            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            elif isinstance(obj, UUID):
                return str(obj)
            elif isinstance(obj, Decimal):
                return float(obj)
            elif hasattr(obj, "__dict__"):
                return str(type(obj).__name__)
            return str(obj)

        def remove_non_deterministic_fields(obj: Any) -> Any:
            """Remove fields that change on every execution."""
            if isinstance(obj, dict):
                return {
                    k: remove_non_deterministic_fields(v)
                    for k, v in obj.items()
                    if k not in ("query_time_ms", "executed_at", "cached_at")
                }
            elif isinstance(obj, list):
                return [remove_non_deterministic_fields(item) for item in obj]
            return obj

        # Remove non-deterministic fields before hashing
        cleaned_data = remove_non_deterministic_fields(data)

        # Sort keys for deterministic hashing
        json_str = json.dumps(cleaned_data, sort_keys=True, default=consistent_json_encoder)
        return hashlib.sha256(json_str.encode()).hexdigest()

    def _calculate_duration(self, execution: SummaryExecution) -> int:
        """Calculate execution duration in milliseconds."""
        if execution.started_at and execution.completed_at:
            delta = execution.completed_at - execution.started_at
            return int(delta.total_seconds() * 1000)
        return 0

    async def _check_relevance(
        self,
        summary: CustomSummary,
        new_data: dict[str, Any],
        data_hash: str,
    ) -> dict[str, Any]:
        """
        Check if update is relevant using semantic analysis.

        Uses the relevance_checker module for multi-level analysis:
        1. Hash comparison (fast)
        2. Record-level change counting
        3. AI-based semantic analysis (if enabled)

        Args:
            summary: The summary being executed
            new_data: The new cached data
            data_hash: Hash of new data

        Returns:
            Dict with score, reason, and should_update
        """
        from services.summaries.relevance_checker import check_relevance

        # Quick hash check first
        if summary.last_data_hash == data_hash:
            return {
                "score": 0.0,
                "reason": "Keine Datenänderungen seit letzter Ausführung",
                "should_update": False,
            }

        # Get previous execution data for comparison
        old_data = {}
        if summary.last_executed_at:
            prev_exec_result = await self.session.execute(
                select(SummaryExecution)
                .where(
                    SummaryExecution.summary_id == summary.id,
                    SummaryExecution.status == ExecutionStatus.COMPLETED,
                )
                .order_by(SummaryExecution.created_at.desc())
                .limit(1)
            )
            prev_execution = prev_exec_result.scalar_one_or_none()
            if prev_execution and prev_execution.cached_data:
                old_data = prev_execution.cached_data

        # Build summary context for AI analysis
        summary_context = {
            "name": summary.name,
            "prompt": summary.original_prompt,
            "theme": summary.interpreted_config.get("theme", {}),
        }

        # Run relevance check
        result = await check_relevance(
            summary_context=summary_context,
            old_data=old_data,
            new_data=new_data,
            threshold=summary.relevance_threshold,
            use_ai=summary.check_relevance,  # Use AI if relevance checking is enabled
            session=self.session,
        )

        return result.to_dict()

    async def _check_auto_expand(
        self,
        summary: CustomSummary,
        cached_data: dict[str, Any],
    ) -> list:
        """
        Check for auto-expand opportunities and return suggestions.

        Uses the auto_expand service to analyze execution data and
        find new relevant facets or visualization opportunities.

        Args:
            summary: The summary being executed
            cached_data: The execution data

        Returns:
            List of WidgetSuggestion objects
        """
        from services.summaries.auto_expand import analyze_for_expansion

        try:
            suggestions = await analyze_for_expansion(
                session=self.session,
                summary=summary,
                execution_data=cached_data,
            )
            return suggestions
        except Exception as e:
            logger.warning(
                "auto_expand_check_failed",
                summary_id=str(summary.id),
                error=str(e),
            )
            return []

    async def get_latest_execution(
        self,
        summary_id: UUID,
        completed_only: bool = True,
    ) -> SummaryExecution | None:
        """
        Get the latest execution for a summary.

        Args:
            summary_id: ID of the summary
            completed_only: Only return completed executions

        Returns:
            Latest SummaryExecution or None
        """
        query = select(SummaryExecution).where(SummaryExecution.summary_id == summary_id)

        if completed_only:
            query = query.where(SummaryExecution.status == ExecutionStatus.COMPLETED)

        query = query.order_by(SummaryExecution.created_at.desc()).limit(1)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()
