"""Celery tasks for asynchronous data exports."""

import asyncio
import csv
import io
import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from celery import shared_task

from workers.celery_app import celery_app
from workers.async_runner import run_async

logger = structlog.get_logger(__name__)

# Export directory for temporary files
EXPORT_DIR = os.environ.get("EXPORT_DIR", "/tmp/exports")


def ensure_export_dir():
    """Ensure export directory exists."""
    os.makedirs(EXPORT_DIR, exist_ok=True)


@celery_app.task(
    name="workers.export_tasks.async_entity_export",
    bind=True,
    max_retries=2,
    soft_time_limit=1800,  # 30 minutes soft limit
    time_limit=2100,  # 35 minutes hard limit
)
def async_entity_export(
    self,
    export_job_id: str,
    export_data: Dict[str, Any],
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a large entity export asynchronously.

    Args:
        export_job_id: UUID of the ExportJob record
        export_data: Export configuration (filters, format, etc.)
        user_id: Optional user ID for tracking

    Returns:
        Dict with export result including file path and record count
    """
    logger.info(
        "async_export_started",
        job_id=export_job_id,
        format=export_data.get("format"),
    )

    try:
        # Run the async export in an event loop
        result = run_async(_execute_async_export(
            export_job_id,
            export_data,
            progress_callback=lambda p, m: _update_progress(self, export_job_id, p, m),
        ))

        logger.info(
            "async_export_completed",
            job_id=export_job_id,
            record_count=result.get("record_count", 0),
        )

        return result

    except Exception as e:
        logger.error(
            "async_export_failed",
            job_id=export_job_id,
            error=str(e),
        )
        # Update job status to failed
        run_async(_mark_job_failed(export_job_id, str(e)))
        raise


def _update_progress(task, job_id: str, progress: int, message: str):
    """Update task progress metadata."""
    task.update_state(
        state="PROGRESS",
        meta={
            "progress": progress,
            "message": message,
            "job_id": job_id,
        }
    )


async def _mark_job_failed(job_id: str, error: str):
    """Mark export job as failed in database."""
    from app.database import get_celery_session
    from sqlalchemy import update
    from app.models.export_job import ExportJob

    async with get_celery_session() as session:
        await session.execute(
            update(ExportJob)
            .where(ExportJob.id == UUID(job_id))
            .values(
                status="failed",
                error_message=error,
                completed_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()


async def _execute_async_export(
    job_id: str,
    export_data: Dict[str, Any],
    progress_callback=None,
) -> Dict[str, Any]:
    """Execute the export query and write to file."""
    from app.database import get_celery_session
    from app.models import Entity, EntityType, FacetType, FacetValue
    from app.models.export_job import ExportJob
    from sqlalchemy import select, update, func
    from services.smart_query.geographic_utils import resolve_geographic_alias

    ensure_export_dir()

    export_format = export_data.get("format", "json").lower()
    query_filter = export_data.get("query_filter", {})
    include_facets = export_data.get("include_facets", True)
    filename = export_data.get("filename", f"export_{job_id}")

    entity_type_slug = query_filter.get("entity_type", "territorial_entity")
    location_filter = query_filter.get("location_filter")
    facet_type_slugs = query_filter.get("facet_types", [])
    position_keywords = query_filter.get("position_keywords", [])
    country = query_filter.get("country")

    async with get_celery_session() as session:
        # Update job status to processing
        await session.execute(
            update(ExportJob)
            .where(ExportJob.id == UUID(job_id))
            .values(status="processing", started_at=datetime.now(timezone.utc))
        )
        await session.commit()

        if progress_callback:
            progress_callback(5, "Export wird vorbereitet...")

        # Build entity query
        entity_query = select(Entity).where(Entity.is_active.is_(True))

        # Filter by entity type
        et_result = await session.execute(
            select(EntityType).where(EntityType.slug == entity_type_slug)
        )
        entity_type = et_result.scalar_one_or_none()
        if not entity_type:
            raise ValueError(f"Entity-Typ '{entity_type_slug}' nicht gefunden")

        entity_query = entity_query.where(Entity.entity_type_id == entity_type.id)

        # Filter by location
        if location_filter:
            resolved_location = resolve_geographic_alias(location_filter)
            entity_query = entity_query.where(Entity.admin_level_1 == resolved_location)

        # Filter by country
        if country:
            entity_query = entity_query.where(Entity.country == country)

        # Filter by position keywords
        if position_keywords and entity_type_slug == "person":
            from sqlalchemy import or_
            position_conditions = []
            for keyword in position_keywords:
                # Escape SQL wildcards to prevent injection
                safe_keyword = keyword.replace('%', '\\%').replace('_', '\\_')
                position_conditions.append(
                    Entity.core_attributes["position"].astext.ilike(f"%{safe_keyword}%", escape='\\')
                )
            if position_conditions:
                entity_query = entity_query.where(or_(*position_conditions))

        if progress_callback:
            progress_callback(10, "Zähle Datensätze...")

        # Count total records
        count_query = select(func.count()).select_from(entity_query.subquery())
        count_result = await session.execute(count_query)
        total_count = count_result.scalar() or 0

        # Update job with total count
        await session.execute(
            update(ExportJob)
            .where(ExportJob.id == UUID(job_id))
            .values(total_records=total_count)
        )
        await session.commit()

        if total_count == 0:
            # Complete with empty result
            await session.execute(
                update(ExportJob)
                .where(ExportJob.id == UUID(job_id))
                .values(
                    status="completed",
                    completed_at=datetime.now(timezone.utc),
                    processed_records=0,
                )
            )
            await session.commit()
            return {
                "success": True,
                "message": "Keine Entities für Export gefunden",
                "record_count": 0,
                "file_path": None,
            }

        if progress_callback:
            progress_callback(15, f"Lade {total_count} Datensätze...")

        # Load facet types for filtering
        facet_type_map = {}
        if facet_type_slugs and include_facets:
            for ft_slug in facet_type_slugs:
                ft_result = await session.execute(
                    select(FacetType).where(FacetType.slug == ft_slug)
                )
                ft = ft_result.scalar_one_or_none()
                if ft:
                    facet_type_map[ft_slug] = ft

        # Process in batches
        batch_size = 1000
        export_records = []
        processed = 0

        # Use streaming for large exports
        result = await session.execute(entity_query)
        entities = result.scalars().all()

        if progress_callback:
            progress_callback(30, "Lade Facetten...")

        # Bulk load facets
        entity_ids = [e.id for e in entities]
        facets_by_entity: Dict[UUID, List[Dict]] = {eid: [] for eid in entity_ids}

        if include_facets and entity_ids:
            facet_query = select(FacetValue).where(
                FacetValue.entity_id.in_(entity_ids),
                FacetValue.is_active.is_(True),
            )
            if facet_type_map:
                facet_type_ids = [ft.id for ft in facet_type_map.values()]
                facet_query = facet_query.where(FacetValue.facet_type_id.in_(facet_type_ids))

            fv_result = await session.execute(facet_query)
            for fv in fv_result.scalars().all():
                facets_by_entity[fv.entity_id].append({
                    "type": str(fv.facet_type_id),
                    "value": fv.value,
                    "text": fv.text_representation,
                    "date": fv.event_date.isoformat() if fv.event_date else None,
                })

        if progress_callback:
            progress_callback(50, "Formatiere Daten...")

        # Build export records
        for i, entity in enumerate(entities):
            record = {
                "id": str(entity.id),
                "name": entity.name,
                "slug": entity.slug,
                "entity_type": entity_type_slug,
                "country": entity.country,
                "admin_level_1": entity.admin_level_1,
                **{k: v for k, v in (entity.core_attributes or {}).items() if not k.startswith("_")},
            }

            if include_facets:
                record["facets"] = facets_by_entity.get(entity.id, [])
                record["facet_count"] = len(record["facets"])

            export_records.append(record)

            # Update progress every 500 records
            if progress_callback and (i + 1) % 500 == 0:
                progress = 50 + int((i / len(entities)) * 40)
                progress_callback(progress, f"Verarbeitet: {i + 1}/{len(entities)}")

        if progress_callback:
            progress_callback(90, "Schreibe Exportdatei...")

        # Write to file based on format
        if export_format == "json":
            file_path = os.path.join(EXPORT_DIR, f"{filename}.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(export_records, f, indent=2, ensure_ascii=False)

        elif export_format == "csv":
            file_path = os.path.join(EXPORT_DIR, f"{filename}.csv")
            with open(file_path, "w", encoding="utf-8", newline="") as f:
                if export_records:
                    # Flatten facets for CSV
                    flat_records = []
                    for record in export_records:
                        flat_record = {k: v for k, v in record.items() if k != "facets"}
                        if include_facets and record.get("facets"):
                            flat_record["facet_texts"] = "; ".join(
                                fac.get("text", "") for fac in record["facets"] if fac.get("text")
                            )
                        flat_records.append(flat_record)

                    fieldnames = list(flat_records[0].keys())
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(flat_records)

        elif export_format == "excel":
            try:
                import openpyxl
                from openpyxl import Workbook

                file_path = os.path.join(EXPORT_DIR, f"{filename}.xlsx")
                wb = Workbook()
                ws = wb.active
                ws.title = "Export"

                if export_records:
                    # Flatten facets for Excel
                    flat_records = []
                    for record in export_records:
                        flat_record = {k: v for k, v in record.items() if k != "facets"}
                        if include_facets and record.get("facets"):
                            flat_record["facet_texts"] = "; ".join(
                                fac.get("text", "") for fac in record["facets"] if fac.get("text")
                            )
                        flat_records.append(flat_record)

                    # Write header
                    headers = list(flat_records[0].keys())
                    ws.append(headers)

                    # Write data rows
                    for record in flat_records:
                        row = [record.get(h, "") for h in headers]
                        ws.append(row)

                    wb.save(file_path)
                else:
                    ws.append(["No data"])
                    wb.save(file_path)

            except ImportError:
                # Fall back to JSON if openpyxl not available
                file_path = os.path.join(EXPORT_DIR, f"{filename}.json")
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(export_records, f, indent=2, ensure_ascii=False)
                export_format = "json"

        else:
            raise ValueError(f"Unbekanntes Export-Format: {export_format}")

        # Get file size
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

        # Update job as completed
        await session.execute(
            update(ExportJob)
            .where(ExportJob.id == UUID(job_id))
            .values(
                status="completed",
                completed_at=datetime.now(timezone.utc),
                processed_records=len(export_records),
                file_path=file_path,
                file_size=file_size,
            )
        )
        await session.commit()

        if progress_callback:
            progress_callback(100, "Export abgeschlossen!")

        return {
            "success": True,
            "message": f"Export erstellt: {len(export_records)} Datensätze",
            "record_count": len(export_records),
            "file_path": file_path,
            "file_size": file_size,
            "format": export_format,
        }


@celery_app.task(name="workers.export_tasks.cleanup_old_exports")
def cleanup_old_exports(max_age_hours: int = 24):
    """Clean up export files older than max_age_hours."""
    import os
    from datetime import datetime, timedelta

    ensure_export_dir()

    cutoff = datetime.now() - timedelta(hours=max_age_hours)
    cleaned = 0

    for filename in os.listdir(EXPORT_DIR):
        file_path = os.path.join(EXPORT_DIR, filename)
        if os.path.isfile(file_path):
            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            if file_mtime < cutoff:
                try:
                    os.remove(file_path)
                    cleaned += 1
                except Exception as e:
                    logger.warning(f"Failed to clean up export file {file_path}: {e}")

    logger.info(f"Cleaned up {cleaned} old export files")
    return {"cleaned": cleaned}
