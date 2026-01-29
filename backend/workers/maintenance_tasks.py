"""Celery tasks for database and system maintenance.

This module provides background tasks for:
- Cleaning up idle database connections
- Monitoring connection pool usage
- Logging connection statistics for alerting
- Entity and FacetType migration/reprocessing
"""

from datetime import UTC

import structlog

from workers.async_runner import run_async
from workers.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(name="workers.maintenance_tasks.cleanup_idle_connections")
def cleanup_idle_connections():
    """Clean up idle database connections.

    This task runs periodically (every 5 minutes) as a safety net to terminate
    connections that have been idle in a transaction for too long.

    PostgreSQL's idle_in_transaction_session_timeout is the primary protection,
    but this task provides an additional layer of defense and logging.
    """
    from app.database import cleanup_idle_connections as do_cleanup

    async def _cleanup():
        result = await do_cleanup()
        if result.get("terminated", 0) > 0:
            logger.warning(
                "idle_connections_cleaned",
                terminated=result["terminated"],
            )
        return result

    return run_async(_cleanup())


@celery_app.task(name="workers.maintenance_tasks.log_connection_stats")
def log_connection_stats():
    """Log current database connection statistics and update Prometheus metrics.

    This task runs periodically (every 15 minutes) to provide visibility
    into connection pool usage. The stats can be used for alerting when
    connection usage approaches the limit.

    Also updates Prometheus gauges for connection pool monitoring.
    """
    from app.database import get_celery_engine, get_connection_stats
    from app.monitoring.metrics import (
        db_connections_max,
        db_connections_total,
        update_db_pool_metrics,
    )

    async def _stats():
        stats = await get_connection_stats()

        # Update Prometheus metrics for PostgreSQL connection stats
        for state, count in stats.items():
            if state not in ("total_current", "max_connections", "error"):
                db_connections_total.labels(state=state).set(count)

        if "max_connections" in stats:
            db_connections_max.set(stats["max_connections"])

        # Update Celery pool metrics
        celery_engine = get_celery_engine()
        if celery_engine:
            update_db_pool_metrics(celery_engine, "celery")

        # Calculate usage percentage
        total = stats.get("total_current", 0)
        max_conn = stats.get("max_connections", 200)
        usage_pct = (total / max_conn * 100) if max_conn > 0 else 0

        # Log at different levels based on usage
        idle_in_transaction = stats.get("idle in transaction", 0)

        if usage_pct > 80 or idle_in_transaction > 10:
            logger.error(
                "connection_stats_critical",
                stats=stats,
                usage_percent=round(usage_pct, 1),
                idle_in_transaction=idle_in_transaction,
            )
        elif usage_pct > 50 or idle_in_transaction > 5:
            logger.warning(
                "connection_stats_elevated",
                stats=stats,
                usage_percent=round(usage_pct, 1),
                idle_in_transaction=idle_in_transaction,
            )
        else:
            logger.info(
                "connection_stats",
                total=total,
                max=max_conn,
                usage_percent=round(usage_pct, 1),
                idle=stats.get("idle", 0),
                active=stats.get("active", 0),
                idle_in_transaction=idle_in_transaction,
            )

        return stats

    return run_async(_stats())


@celery_app.task(name="workers.maintenance_tasks.force_cleanup_connections")
def force_cleanup_connections(max_idle_minutes: int = 2):
    """Force cleanup of idle connections with configurable threshold.

    This can be called manually via Celery to immediately clean up
    connections when issues are detected.

    Args:
        max_idle_minutes: Maximum minutes a connection can be idle before termination
    """
    from sqlalchemy import text

    from app.database import get_celery_session_context

    async def _force_cleanup():
        async with get_celery_session_context() as session:
            result = await session.execute(
                text("""
                    SELECT pg_terminate_backend(pid), pid, state,
                           EXTRACT(EPOCH FROM (clock_timestamp() - state_change))::int as idle_seconds
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                      AND pid != pg_backend_pid()
                      AND state IN ('idle', 'idle in transaction')
                      AND state_change < NOW() - make_interval(mins := :minutes)
                """),
                {"minutes": max_idle_minutes},
            )
            terminated = result.fetchall()

            if terminated:
                logger.warning(
                    "force_cleanup_completed",
                    terminated=len(terminated),
                    max_idle_minutes=max_idle_minutes,
                    connections=[{"pid": row[1], "state": row[2]} for row in terminated],
                )

            return {"terminated": len(terminated)}

    return run_async(_force_cleanup())


@celery_app.task(name="workers.maintenance_tasks.sync_azure_model_pricing")
def sync_azure_model_pricing():
    """Sync Azure OpenAI model pricing from Azure Retail Prices API.

    This task runs weekly (every Sunday at 3 AM) to keep Azure pricing data
    up-to-date. The Azure Retail Prices API is the only provider with a public
    pricing API. OpenAI and Anthropic prices must be updated manually.

    The task fetches all Azure OpenAI model prices and upserts them into the
    model_pricing table, updating existing entries and adding new ones.
    """
    from app.database import get_celery_session_context
    from services.model_pricing_service import ModelPricingService

    async def _sync():
        async with get_celery_session_context() as session:
            results = await ModelPricingService.sync_azure_prices(session)

            if results["errors"]:
                logger.warning(
                    "azure_pricing_sync_partial",
                    updated=results["updated"],
                    added=results["added"],
                    errors=results["errors"],
                )
            else:
                logger.info(
                    "azure_pricing_sync_complete",
                    updated=results["updated"],
                    added=results["added"],
                )

            return results

    return run_async(_sync())


@celery_app.task(name="workers.maintenance_tasks.seed_model_pricing")
def seed_model_pricing():
    """Seed default model pricing data if table is empty.

    This task should be called once during initial setup to populate the
    model_pricing table with default prices for OpenAI, Anthropic, and
    Azure OpenAI models.

    If pricing data already exists, this task does nothing.
    """
    from app.database import get_celery_session_context
    from services.model_pricing_service import ModelPricingService

    async def _seed():
        async with get_celery_session_context() as session:
            count = await ModelPricingService.seed_default_pricing(session)

            if count > 0:
                logger.info("model_pricing_seeded", count=count)
            else:
                logger.info("model_pricing_already_exists")

            return {"seeded": count}

    return run_async(_seed())


@celery_app.task(name="workers.maintenance_tasks.aggregate_llm_usage")
def aggregate_llm_usage():
    """Aggregate old LLM usage records into monthly summaries.

    This task runs monthly (1st of each month) to aggregate detailed
    usage records older than 90 days into monthly aggregates, reducing
    storage requirements while preserving historical data.
    """
    from datetime import datetime, timedelta
    from uuid import uuid4

    from sqlalchemy import delete, func, select
    from sqlalchemy.dialects.postgresql import insert

    from app.database import get_celery_session_context
    from app.models.llm_usage import LLMUsageMonthlyAggregate, LLMUsageRecord

    async def _aggregate():
        cutoff_date = datetime.now(UTC) - timedelta(days=90)

        async with get_celery_session_context() as session:
            # Get aggregated data from records older than 90 days
            stmt = (
                select(
                    func.to_char(LLMUsageRecord.created_at, "YYYY-MM").label("year_month"),
                    LLMUsageRecord.provider,
                    LLMUsageRecord.model,
                    LLMUsageRecord.task_type,
                    LLMUsageRecord.category_id,
                    func.count().label("request_count"),
                    func.sum(LLMUsageRecord.prompt_tokens).label("total_prompt_tokens"),
                    func.sum(LLMUsageRecord.completion_tokens).label("total_completion_tokens"),
                    func.sum(LLMUsageRecord.total_tokens).label("total_tokens"),
                    func.sum(LLMUsageRecord.estimated_cost_cents).label("total_cost_cents"),
                    func.sum(func.cast(LLMUsageRecord.is_error, "int")).label("error_count"),
                    func.avg(LLMUsageRecord.duration_ms).label("avg_duration_ms"),
                )
                .where(LLMUsageRecord.created_at < cutoff_date)
                .group_by(
                    func.to_char(LLMUsageRecord.created_at, "YYYY-MM"),
                    LLMUsageRecord.provider,
                    LLMUsageRecord.model,
                    LLMUsageRecord.task_type,
                    LLMUsageRecord.category_id,
                )
            )

            result = await session.execute(stmt)
            aggregates = result.fetchall()

            inserted_count = 0
            for row in aggregates:
                # Insert or update aggregate record
                values = {
                    "year_month": row.year_month,
                    "provider": row.provider,
                    "model": row.model,
                    "task_type": row.task_type,
                    "category_id": row.category_id,
                    "request_count": row.request_count,
                    "total_prompt_tokens": row.total_prompt_tokens or 0,
                    "total_completion_tokens": row.total_completion_tokens or 0,
                    "total_tokens": row.total_tokens or 0,
                    "total_cost_cents": row.total_cost_cents or 0,
                    "error_count": row.error_count or 0,
                    "avg_duration_ms": float(row.avg_duration_ms or 0),
                }

                stmt = insert(LLMUsageMonthlyAggregate).values(id=uuid4(), **values)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["year_month", "provider", "model", "task_type", "category_id"],
                    set_={
                        "request_count": stmt.excluded.request_count,
                        "total_prompt_tokens": stmt.excluded.total_prompt_tokens,
                        "total_completion_tokens": stmt.excluded.total_completion_tokens,
                        "total_tokens": stmt.excluded.total_tokens,
                        "total_cost_cents": stmt.excluded.total_cost_cents,
                        "error_count": stmt.excluded.error_count,
                        "avg_duration_ms": stmt.excluded.avg_duration_ms,
                    },
                )
                await session.execute(stmt)
                inserted_count += 1

            # Delete aggregated records
            if aggregates:
                delete_stmt = delete(LLMUsageRecord).where(LLMUsageRecord.created_at < cutoff_date)
                result = await session.execute(delete_stmt)
                deleted_count = result.rowcount

                await session.commit()

                logger.info(
                    "llm_usage_aggregated",
                    aggregates_created=inserted_count,
                    records_deleted=deleted_count,
                    cutoff_date=cutoff_date.isoformat(),
                )

                return {
                    "aggregates_created": inserted_count,
                    "records_deleted": deleted_count,
                }

            return {"aggregates_created": 0, "records_deleted": 0}

    return run_async(_aggregate())


@celery_app.task(name="workers.maintenance_tasks.check_llm_budgets")
def check_llm_budgets():
    """Check LLM budget limits and send alerts if thresholds are exceeded.

    This task runs daily (at 8 AM) to check all active budgets and send
    email notifications when warning or critical thresholds are reached.
    """
    from app.database import get_celery_session_context
    from services.llm_budget_service import LLMBudgetService

    async def _check():
        async with get_celery_session_context() as session:
            service = LLMBudgetService(session)
            alerts = await service.check_and_send_alerts()

            if alerts:
                logger.warning(
                    "llm_budget_alerts_sent",
                    alert_count=len(alerts),
                    alerts=[
                        {
                            "budget_id": str(a.budget_id),
                            "alert_type": a.alert_type,
                            "usage_percent": a.usage_percent,
                        }
                        for a in alerts
                    ],
                )

            return {"alerts_sent": len(alerts)}

    return run_async(_check())


@celery_app.task(name="workers.maintenance_tasks.migrate_entity_references", bind=True)
def migrate_entity_references(self, batch_size: int = 100, dry_run: bool = False):
    """Migrate existing ExtractedData records to link entities and create FacetValues.

    This task processes all ExtractedData records and:
    1. Extracts entity references from content for records without them
    2. Resolves entity_id for references without resolved entities
    3. Auto-creates EntityTypes and Entities as needed
    4. Creates FacetValues to link non-primary entities to primary entities

    Args:
        batch_size: Number of records to process per batch (default: 100)
        dry_run: If True, only count records without making changes

    Returns:
        Statistics about the migration
    """
    from uuid import UUID

    from sqlalchemy import func, select
    from sqlalchemy.orm import selectinload
    from sqlalchemy.orm.attributes import flag_modified

    from app.database import get_celery_session_context
    from app.models import ExtractedData
    from workers.ai_tasks.common import (
        DEFAULT_ARRAY_FIELD_MAPPINGS,
        DEFAULT_FIELD_MAPPINGS,
        DEFAULT_NESTED_FIELD_MAPPINGS,
        _create_entity_facet_value,
        _get_active_entity_type_slugs,
        _resolve_entity,
        _resolve_entity_smart,
    )

    def _get_nested_value(data: dict, path: str):
        """Get value from nested dict using dot notation path."""
        parts = path.split(".")
        current = data
        for part in parts:
            if not isinstance(current, dict):
                return None
            current = current.get(part)
            if current is None:
                return None
        return current

    async def _extract_entity_refs_from_content(session, content, category, active_entity_types):
        """Extract entity references from content using default mappings."""
        entity_refs = []
        primary_entity_id = None

        config = category.entity_reference_config or {} if category else {}
        # Use active entity types from DB, with optional category override
        entity_types = config.get("entity_types") or active_entity_types
        field_mappings = {**DEFAULT_FIELD_MAPPINGS, **config.get("field_mappings", {})}
        nested_field_mappings = {**DEFAULT_NESTED_FIELD_MAPPINGS, **config.get("nested_field_mappings", {})}
        array_field_mappings = {**DEFAULT_ARRAY_FIELD_MAPPINGS, **config.get("array_field_mappings", {})}

        primary_assigned_types = set()

        async def process_field_value(field_value, entity_type, source_field):
            """Process a field value and extract entity references."""
            nonlocal primary_entity_id

            if not field_value:
                return

            values = field_value if isinstance(field_value, list) else [field_value]

            for value in values:
                if not isinstance(value, str):
                    continue
                if value.lower() in ("", "unbekannt", "null", "none", "n/a"):
                    continue

                is_primary = entity_type not in primary_assigned_types
                role = "primary" if is_primary else "secondary"
                if is_primary:
                    primary_assigned_types.add(entity_type)

                entity_id = await _resolve_entity(session, entity_type, value)

                entity_refs.append(
                    {
                        "entity_type": entity_type,
                        "entity_name": value,
                        "entity_id": str(entity_id) if entity_id else None,
                        "role": role,
                        "confidence": 0.85,
                        "source_field": source_field,
                    }
                )

                if entity_id and not primary_entity_id:
                    primary_entity_id = entity_id

        # Process simple field mappings (top-level)
        for field_name, entity_type in field_mappings.items():
            if entity_type not in entity_types:
                continue
            field_value = content.get(field_name)
            await process_field_value(field_value, entity_type, field_name)

        # Process nested field mappings (dot notation paths)
        for field_path, entity_type in nested_field_mappings.items():
            if entity_type not in entity_types:
                continue
            field_value = _get_nested_value(content, field_path)
            await process_field_value(field_value, entity_type, field_path)

        # Process array field mappings
        for field_name, mapping in array_field_mappings.items():
            entity_type = mapping.get("entity_type")
            if not entity_type or entity_type not in entity_types:
                continue

            name_fields = mapping.get("name_fields", ["name"])
            role_field = mapping.get("role_field", "role")
            default_role = mapping.get("default_role", "secondary")

            field_values = content.get(field_name)
            if not isinstance(field_values, list):
                continue

            for item in field_values:
                name = None

                if isinstance(item, dict):
                    for nf in name_fields:
                        name = item.get(nf)
                        if name:
                            break
                    role = item.get(role_field, default_role)
                elif isinstance(item, str):
                    name = item
                    role = default_role
                else:
                    continue

                if not name or (isinstance(name, str) and name.lower() in ("", "unbekannt", "null")):
                    continue

                # Smart entity resolution: Search across all types and classify if needed
                entity_id, actual_entity_type = await _resolve_entity_smart(
                    session,
                    name,
                    allowed_types=None,  # Search all types
                    auto_create=True,
                    default_type=entity_type,  # Fallback to configured type
                )

                entity_refs.append(
                    {
                        "entity_type": actual_entity_type,
                        "entity_name": name,
                        "entity_id": str(entity_id) if entity_id else None,
                        "role": role,
                        "confidence": 0.7,
                        "source_field": field_name,
                    }
                )

        return entity_refs, primary_entity_id

    async def _create_facet_values_for_refs(session, entity_refs, primary_entity_id, document_id, category_id):
        """Create FacetValues for non-primary entity references."""
        facets_created = 0

        if not primary_entity_id:
            return facets_created

        for ref in entity_refs:
            # Skip primary entities - they get facets, not become targets
            if ref.get("role") == "primary":
                continue

            target_entity_id = ref.get("entity_id")
            if not target_entity_id:
                continue

            entity_type = ref.get("entity_type")
            entity_name = ref.get("entity_name")
            role = ref.get("role", "secondary")
            confidence = ref.get("confidence", 0.7)

            try:
                target_uuid = UUID(target_entity_id) if isinstance(target_entity_id, str) else target_entity_id
            except (ValueError, TypeError):
                continue

            facet_id = await _create_entity_facet_value(
                session=session,
                primary_entity_id=primary_entity_id,
                target_entity_id=target_uuid,
                target_entity_type_slug=entity_type,
                target_entity_name=entity_name,
                role=role,
                document_id=document_id,
                category_id=category_id,
                confidence_score=confidence,
            )

            if facet_id:
                facets_created += 1

        return facets_created

    async def _migrate():
        stats = {
            "total_processed": 0,
            "extracted_new": 0,
            "resolved_existing": 0,
            "facets_created": 0,
            "entities_created": 0,
            "entity_types_created": 0,
            "errors": 0,
        }

        async with get_celery_session_context() as session:
            # Get active entity types from DB
            active_entity_types = await _get_active_entity_type_slugs(session)
            logger.info("migrate_entity_references_entity_types", entity_types=active_entity_types)

            # Count total records
            count_stmt = select(func.count()).select_from(ExtractedData)
            total_count = (await session.execute(count_stmt)).scalar()

            if dry_run:
                # Count records needing migration
                needs_extraction_stmt = (
                    select(func.count())
                    .select_from(ExtractedData)
                    .where((ExtractedData.entity_references.is_(None)) | (ExtractedData.entity_references == []))
                )
                needs_extraction = (await session.execute(needs_extraction_stmt)).scalar()

                logger.info(
                    "migrate_entity_references_dry_run",
                    total_records=total_count,
                    needs_extraction=needs_extraction,
                )
                return {
                    "dry_run": True,
                    "total_records": total_count,
                    "needs_extraction": needs_extraction,
                }

            # Process in batches
            offset = 0
            while True:
                stmt = (
                    select(ExtractedData)
                    .options(selectinload(ExtractedData.category))
                    .order_by(ExtractedData.created_at)
                    .offset(offset)
                    .limit(batch_size)
                )
                result = await session.execute(stmt)
                records = result.scalars().all()

                if not records:
                    break

                for record in records:
                    try:
                        content = record.extracted_content or {}

                        # Case 1: No entity references - extract from content
                        if not record.entity_references:
                            entity_refs, primary_id = await _extract_entity_refs_from_content(
                                session, content, record.category, active_entity_types
                            )
                            if entity_refs:
                                record.entity_references = entity_refs
                                record.primary_entity_id = primary_id
                                stats["extracted_new"] += 1

                                # Create FacetValues for newly extracted refs
                                facets = await _create_facet_values_for_refs(
                                    session, entity_refs, primary_id, record.document_id, record.category_id
                                )
                                stats["facets_created"] += facets

                        # Case 2: Has entity references - resolve unlinked ones and create facets
                        elif isinstance(record.entity_references, list):
                            new_refs = []
                            refs_updated = False

                            for ref in record.entity_references:
                                if not isinstance(ref, dict):
                                    new_refs.append(ref)
                                    continue

                                # If already has entity_id, keep as is
                                if ref.get("entity_id"):
                                    new_refs.append(ref)
                                    continue

                                # Try to resolve entity using smart resolution
                                entity_type = ref.get("entity_type")
                                entity_name = ref.get("entity_name")

                                # Create a copy to ensure SQLAlchemy detects the change
                                new_ref = dict(ref)

                                if entity_name:
                                    entity_id, actual_type = await _resolve_entity_smart(
                                        session,
                                        entity_name,
                                        allowed_types=None,  # Search all types
                                        auto_create=False,  # Don't create, just find
                                        default_type=entity_type,
                                    )
                                    if entity_id:
                                        new_ref["entity_id"] = str(entity_id)
                                        new_ref["entity_type"] = actual_type  # Update type if different
                                        stats["resolved_existing"] += 1
                                        refs_updated = True

                                new_refs.append(new_ref)

                            if refs_updated:
                                record.entity_references = new_refs
                                # Explicitly mark JSONB column as modified to ensure SQLAlchemy tracks the change
                                flag_modified(record, "entity_references")

                                # Update primary_entity_id if not set
                                if not record.primary_entity_id:
                                    # First try to find explicit "primary" role
                                    for ref in new_refs:
                                        if ref.get("entity_id") and ref.get("role") == "primary":
                                            record.primary_entity_id = UUID(ref["entity_id"])
                                            break
                                    # Fallback: use first ref with entity_id (for legacy data with descriptive roles)
                                    if not record.primary_entity_id:
                                        for ref in new_refs:
                                            if ref.get("entity_id"):
                                                record.primary_entity_id = UUID(ref["entity_id"])
                                                break

                            # Also set primary_entity_id for records that weren't updated but are missing it
                            if not record.primary_entity_id and new_refs:
                                for ref in new_refs:
                                    if ref.get("entity_id"):
                                        record.primary_entity_id = UUID(ref["entity_id"])
                                        logger.debug(
                                            "Set primary_entity_id from existing ref",
                                            record_id=str(record.id),
                                            entity_id=ref["entity_id"],
                                        )
                                        break

                            # Create FacetValues for existing refs (even if not updated)
                            primary_id = record.primary_entity_id
                            if primary_id:
                                facets = await _create_facet_values_for_refs(
                                    session, new_refs, primary_id, record.document_id, record.category_id
                                )
                                stats["facets_created"] += facets

                        stats["total_processed"] += 1

                    except Exception as e:
                        logger.error(
                            "migrate_entity_reference_error",
                            record_id=str(record.id),
                            error=str(e),
                        )
                        stats["errors"] += 1

                # Commit batch
                await session.commit()

                # Update progress
                offset += batch_size
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "current": offset,
                        "total": total_count,
                        "percent": min(100, int(offset / total_count * 100)) if total_count else 100,
                    },
                )

                logger.info(
                    "migrate_entity_references_batch",
                    processed=offset,
                    total=total_count,
                    stats=stats,
                )

        logger.info("migrate_entity_references_complete", **stats)
        return stats

    return run_async(_migrate())


@celery_app.task(name="workers.maintenance_tasks.migrate_facet_value_entity_links", bind=True)
def migrate_facet_value_entity_links(self, batch_size: int = 100, dry_run: bool = False):
    """Link existing FacetValues to Entity records.

    This task processes FacetValues that:
    - Belong to FacetTypes with allows_entity_reference=True
    - Have no target_entity_id set

    For each such FacetValue, it:
    1. Extracts the entity name from value.name or text_representation
    2. Determines the target entity type from FacetType.target_entity_type_slugs
    3. Finds or creates a matching Entity
    4. Sets the target_entity_id

    Args:
        batch_size: Number of records to process per batch (default: 100)
        dry_run: If True, only count records without making changes

    Returns:
        Statistics about the migration
    """
    import re

    from sqlalchemy import func, select

    from app.database import get_celery_session_context
    from app.models import FacetType, FacetValue
    from workers.ai_tasks.common import _resolve_entity

    async def _migrate():
        stats = {
            "total_processed": 0,
            "linked_existing": 0,
            "created_new": 0,
            "skipped_no_name": 0,
            "skipped_no_type": 0,
            "errors": 0,
        }

        async with get_celery_session_context() as session:
            # Get FacetTypes that allow entity references
            ft_result = await session.execute(
                select(FacetType).where(
                    FacetType.is_active.is_(True),
                    FacetType.allows_entity_reference.is_(True),
                )
            )
            entity_ref_facet_types = {ft.id: ft for ft in ft_result.scalars().all()}

            if not entity_ref_facet_types:
                logger.info("migrate_facet_value_entity_links_no_facet_types")
                return stats

            # Count FacetValues needing migration
            count_stmt = (
                select(func.count())
                .select_from(FacetValue)
                .where(
                    FacetValue.facet_type_id.in_(entity_ref_facet_types.keys()),
                    FacetValue.target_entity_id.is_(None),
                )
            )
            total_count = (await session.execute(count_stmt)).scalar()

            logger.info(
                "migrate_facet_value_entity_links_start",
                total_to_process=total_count,
                facet_types=[ft.slug for ft in entity_ref_facet_types.values()],
            )

            if dry_run:
                return {
                    "dry_run": True,
                    "total_to_process": total_count,
                    "facet_types": [ft.slug for ft in entity_ref_facet_types.values()],
                }

            # Process in batches
            offset = 0
            while True:
                stmt = (
                    select(FacetValue)
                    .where(
                        FacetValue.facet_type_id.in_(entity_ref_facet_types.keys()),
                        FacetValue.target_entity_id.is_(None),
                    )
                    .order_by(FacetValue.created_at)
                    .offset(offset)
                    .limit(batch_size)
                )
                result = await session.execute(stmt)
                facet_values = result.scalars().all()

                if not facet_values:
                    break

                for fv in facet_values:
                    try:
                        facet_type = entity_ref_facet_types.get(fv.facet_type_id)
                        if not facet_type:
                            stats["skipped_no_type"] += 1
                            continue

                        # Extract name from value or text_representation
                        value = fv.value or {}
                        name = value.get("name")

                        if not name and fv.text_representation:
                            # Try to extract name from text like "Name (Role)"
                            match = re.match(r"^([^(]+)", fv.text_representation)
                            if match:
                                name = match.group(1).strip()

                        if not name:
                            stats["skipped_no_name"] += 1
                            continue

                        # Determine target entity type using intelligent classification
                        target_types = facet_type.target_entity_type_slugs or []
                        if not target_types:
                            stats["skipped_no_type"] += 1
                            continue

                        # Use EntityMatchingService to classify and resolve entity
                        from services.entity_matching_service import EntityMatchingService

                        matching_service = EntityMatchingService(session)
                        target_entity_type = matching_service._classify_entity_type(name, value, target_types)
                        if not target_entity_type:
                            # Fall back to first type if classification fails
                            target_entity_type = target_types[0]

                        # Find or create entity using _resolve_entity
                        entity_id = await _resolve_entity(session, target_entity_type, name)

                        if entity_id:
                            fv.target_entity_id = entity_id
                            # Check if entity was just created or already existed
                            # (We can't easily tell, so count as linked)
                            stats["linked_existing"] += 1
                        else:
                            stats["errors"] += 1

                        stats["total_processed"] += 1

                    except Exception as e:
                        logger.error(
                            "migrate_facet_value_entity_link_error",
                            facet_value_id=str(fv.id),
                            error=str(e),
                        )
                        stats["errors"] += 1

                # Commit batch
                await session.commit()

                # Update progress
                offset += batch_size
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "current": offset,
                        "total": total_count,
                        "percent": min(100, int(offset / total_count * 100)) if total_count else 100,
                    },
                )

                logger.info(
                    "migrate_facet_value_entity_links_batch",
                    processed=offset,
                    total=total_count,
                    stats=stats,
                )

        logger.info("migrate_facet_value_entity_links_complete", **stats)
        return stats

    return run_async(_migrate())


@celery_app.task(name="workers.maintenance_tasks.reclassify_entities", bind=True)
def reclassify_entities(self, batch_size: int = 100, dry_run: bool = True):
    """Reclassify entities using intelligent type detection.

    This task analyzes all entities and checks if they are correctly classified.
    Uses similarity-based classification to determine if an entity should be
    in a different EntityType (e.g., an organization mistakenly classified as person).

    The reclassification process:
    1. For each entity, uses classify_by_existing_entities() to find the best matching type
    2. If the classified type differs from the current type, the entity is migrated:
       - A new entity is created with the correct type
       - All FacetValues pointing to the old entity are updated
       - All entity_references in ExtractedData are updated
       - The old entity is deactivated

    Args:
        batch_size: Number of entities to process per batch (default: 100)
        dry_run: If True, only analyze and report without making changes (default: True)

    Returns:
        Statistics about the reclassification
    """

    from sqlalchemy import func, select, update
    from sqlalchemy.orm import selectinload

    from app.database import get_celery_session_context
    from app.models import Entity, EntityType, ExtractedData, FacetValue
    from workers.ai_tasks.common import classify_by_existing_entities

    async def _reclassify():
        stats = {
            "total_analyzed": 0,
            "needs_reclassification": 0,
            "reclassified": 0,
            "facets_updated": 0,
            "refs_updated": 0,
            "errors": 0,
            "reclassification_candidates": [],
        }

        async with get_celery_session_context() as session:
            # Get all entity types
            type_result = await session.execute(select(EntityType).where(EntityType.is_active.is_(True)))
            entity_types = {et.slug: et for et in type_result.scalars().all()}

            # Count total entities
            count_stmt = select(func.count()).select_from(Entity).where(Entity.is_active.is_(True))
            total_count = (await session.execute(count_stmt)).scalar()

            if dry_run:
                logger.info(
                    "reclassify_entities_dry_run_start",
                    total_entities=total_count,
                )

            # Process in batches
            offset = 0
            while True:
                stmt = (
                    select(Entity)
                    .options(selectinload(Entity.entity_type))
                    .where(Entity.is_active.is_(True))
                    .order_by(Entity.created_at)
                    .offset(offset)
                    .limit(batch_size)
                )
                result = await session.execute(stmt)
                entities = result.scalars().all()

                if not entities:
                    break

                for entity in entities:
                    try:
                        stats["total_analyzed"] += 1
                        current_type = entity.entity_type.slug

                        # Use smart classification to determine the best type
                        classified_type = await classify_by_existing_entities(
                            session,
                            entity.name,
                            allowed_types=None,  # Check all types
                            similarity_threshold=0.6,
                        )

                        # If no classification found, skip
                        if not classified_type:
                            continue

                        # If classified differently, mark for reclassification
                        if classified_type != current_type:
                            stats["needs_reclassification"] += 1
                            stats["reclassification_candidates"].append(
                                {
                                    "entity_id": str(entity.id),
                                    "entity_name": entity.name,
                                    "current_type": current_type,
                                    "suggested_type": classified_type,
                                }
                            )

                            if not dry_run:
                                # Get the target entity type
                                target_type = entity_types.get(classified_type)
                                if not target_type:
                                    continue

                                # Check if there's already an entity with this name in the target type
                                existing_stmt = select(Entity).where(
                                    Entity.entity_type_id == target_type.id,
                                    Entity.name == entity.name,
                                    Entity.is_active.is_(True),
                                )
                                existing_result = await session.execute(existing_stmt)
                                existing_entity = existing_result.scalar_one_or_none()

                                if existing_entity:
                                    # Merge: Point all references to the existing entity
                                    target_entity_id = existing_entity.id
                                else:
                                    # Create new entity with correct type
                                    new_entity = Entity(
                                        entity_type_id=target_type.id,
                                        name=entity.name,
                                        name_normalized=entity.name_normalized,
                                        slug=entity.slug,
                                        name_embedding=entity.name_embedding,
                                        core_attributes=entity.core_attributes or {},
                                        is_active=True,
                                    )
                                    session.add(new_entity)
                                    await session.flush()
                                    target_entity_id = new_entity.id

                                # Update FacetValues that reference the old entity
                                facet_update = (
                                    update(FacetValue)
                                    .where(FacetValue.target_entity_id == entity.id)
                                    .values(target_entity_id=target_entity_id)
                                )
                                facet_result = await session.execute(facet_update)
                                stats["facets_updated"] += facet_result.rowcount

                                # Update entity_references in ExtractedData
                                # This requires loading and modifying JSON
                                extracted_stmt = select(ExtractedData).where(
                                    ExtractedData.entity_references.isnot(None)
                                )
                                extracted_result = await session.execute(extracted_stmt)
                                for ed in extracted_result.scalars():
                                    if not ed.entity_references:
                                        continue
                                    updated = False
                                    for ref in ed.entity_references:
                                        if ref.get("entity_id") == str(entity.id):
                                            ref["entity_id"] = str(target_entity_id)
                                            ref["entity_type"] = classified_type
                                            updated = True
                                            stats["refs_updated"] += 1
                                    if updated:
                                        # Force JSONB update
                                        ed.entity_references = list(ed.entity_references)

                                # Deactivate old entity
                                entity.is_active = False
                                stats["reclassified"] += 1

                    except Exception as e:
                        logger.error(
                            "reclassify_entity_error",
                            entity_id=str(entity.id),
                            error=str(e),
                        )
                        stats["errors"] += 1

                # Commit batch
                if not dry_run:
                    await session.commit()

                # Update progress
                offset += batch_size
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "current": offset,
                        "total": total_count,
                        "percent": min(100, int(offset / total_count * 100)) if total_count else 100,
                    },
                )

                logger.info(
                    "reclassify_entities_batch",
                    processed=offset,
                    total=total_count,
                    needs_reclassification=stats["needs_reclassification"],
                )

        # Limit candidates list in output
        if len(stats["reclassification_candidates"]) > 50:
            stats["reclassification_candidates"] = stats["reclassification_candidates"][:50]
            stats["reclassification_candidates_truncated"] = True

        logger.info(
            "reclassify_entities_complete", **{k: v for k, v in stats.items() if k != "reclassification_candidates"}
        )
        return stats

    return run_async(_reclassify())


@celery_app.task(name="workers.maintenance_tasks.reprocess_extractions_for_facets", bind=True)
def reprocess_extractions_for_facets(
    self,
    batch_size: int = 50,
    skip_existing_facets: bool = True,
    category_slug: str | None = None,
):
    """
    Reprocess all ExtractedData to create FacetValues using the generic converter.

    This task iterates over all ExtractedData and applies the new generic
    `convert_extraction_to_facets` function which:
    - Dynamically creates FacetTypes for unknown fields
    - Creates FacetValues for all extracted data
    - Handles complex nested structures like `flaechenausweisung`

    Args:
        batch_size: Number of extractions to process per batch (default: 50)
        skip_existing_facets: Skip extractions that already have facet values (default: True)
        category_slug: Optional - only process extractions from this category

    Returns:
        Statistics about the reprocessing
    """

    from sqlalchemy import func, select
    from sqlalchemy.orm import selectinload

    from app.database import get_celery_session_context
    from app.models import Category, DataSource, ExtractedData, FacetType, FacetValue
    from services.entity_facet_service import convert_extraction_to_facets

    async def _reprocess():
        stats = {
            "total_processed": 0,
            "facets_created": 0,
            "facet_types_created": 0,
            "skipped_no_content": 0,
            "skipped_existing": 0,
            "errors": 0,
            "facet_counts_by_type": {},
        }

        # Track newly created FacetTypes
        initial_facet_types = set()

        async with get_celery_session_context() as session:
            # Get initial FacetType count
            ft_count_stmt = select(func.count()).select_from(FacetType)
            (await session.execute(ft_count_stmt)).scalar()

            # Get initial FacetType slugs
            ft_stmt = select(FacetType.slug)
            ft_result = await session.execute(ft_stmt)
            initial_facet_types = {row[0] for row in ft_result.fetchall()}

            # Build base query
            stmt = (
                select(ExtractedData)
                .options(selectinload(ExtractedData.category))
                .where(ExtractedData.extracted_content.isnot(None))
            )

            # Filter by category if specified
            if category_slug:
                category_stmt = select(Category.id).where(Category.slug == category_slug)
                category_result = await session.execute(category_stmt)
                category_id = category_result.scalar_one_or_none()
                if category_id:
                    stmt = stmt.where(ExtractedData.category_id == category_id)

            stmt = stmt.order_by(ExtractedData.created_at)

            # Count total
            count_stmt = (
                select(func.count()).select_from(ExtractedData).where(ExtractedData.extracted_content.isnot(None))
            )
            if category_slug and category_id:
                count_stmt = count_stmt.where(ExtractedData.category_id == category_id)
            total_count = (await session.execute(count_stmt)).scalar()

            logger.info(
                "reprocess_extractions_start",
                total_extractions=total_count,
                category_slug=category_slug,
                skip_existing=skip_existing_facets,
            )

            # Process in batches
            offset = 0
            while True:
                batch_stmt = stmt.offset(offset).limit(batch_size)
                result = await session.execute(batch_stmt)
                extractions = result.scalars().all()

                if not extractions:
                    break

                # Extract all needed data upfront to avoid lazy loading issues
                # after any session rollback
                extraction_data = []
                for extraction in extractions:
                    extraction_data.append(
                        {
                            "id": extraction.id,
                            "document_id": extraction.document_id,
                            "category_id": extraction.category_id,
                            "extracted_content": extraction.extracted_content,
                            "entity_references": getattr(extraction, "entity_references", []),
                        }
                    )

                for data in extraction_data:
                    extraction_id = data["id"]
                    document_id = data["document_id"]
                    extracted_content = data["extracted_content"]

                    try:
                        # Skip if no content
                        if not extracted_content:
                            stats["skipped_no_content"] += 1
                            continue

                        # Skip if already has facet values (optional)
                        if skip_existing_facets:
                            fv_check = await session.execute(
                                select(func.count())
                                .select_from(FacetValue)
                                .where(FacetValue.source_document_id == document_id)
                            )
                            if fv_check.scalar() > 0:
                                stats["skipped_existing"] += 1
                                continue

                        # Re-fetch the extraction for processing (fresh ORM object)
                        extraction = await session.get(ExtractedData, extraction_id)
                        if not extraction:
                            continue

                        # Get data source if available
                        source = None
                        if document_id:
                            from app.models import Document

                            doc = await session.get(Document, document_id)
                            if doc and doc.source_id:
                                source = await session.get(DataSource, doc.source_id)

                        # Run the generic converter
                        counts = await convert_extraction_to_facets(
                            session,
                            extraction,
                            source,
                        )

                        stats["total_processed"] += 1

                        for facet_slug, count in counts.items():
                            stats["facets_created"] += count
                            if facet_slug not in stats["facet_counts_by_type"]:
                                stats["facet_counts_by_type"][facet_slug] = 0
                            stats["facet_counts_by_type"][facet_slug] += count

                    except Exception as e:
                        logger.error(
                            "reprocess_extraction_error",
                            extraction_id=str(extraction_id),
                            error=str(e),
                        )
                        stats["errors"] += 1
                        # Begin new transaction after error
                        await session.rollback()

                # Commit batch
                await session.commit()

                # Update progress
                offset += batch_size
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "current": offset,
                        "total": total_count,
                        "percent": min(100, int(offset / total_count * 100)) if total_count else 100,
                        "facets_created": stats["facets_created"],
                    },
                )

                logger.info(
                    "reprocess_extractions_batch",
                    processed=offset,
                    total=total_count,
                    facets_created=stats["facets_created"],
                )

            # Count newly created FacetTypes
            ft_result = await session.execute(select(FacetType.slug))
            final_facet_types = {row[0] for row in ft_result.fetchall()}
            new_facet_types = final_facet_types - initial_facet_types
            stats["facet_types_created"] = len(new_facet_types)
            stats["new_facet_type_slugs"] = list(new_facet_types)

        logger.info("reprocess_extractions_complete", **stats)
        return stats

    return run_async(_reprocess())
