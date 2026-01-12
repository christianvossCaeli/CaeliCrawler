"""
EntityDataFacetService - Service for AI-based facet enrichment from entity data.

This service analyzes various data sources linked to an entity (relations,
documents, extractions, PySIS) and suggests new facet values or updates
to existing ones.

Key features:
1. Preview-based workflow: No direct writes, shows changes for approval
2. Multi-source analysis: Relations, Documents, Extractions, PySIS
3. Deduplication: Checks existing facets to avoid duplicates
4. Confidence scoring: AI provides confidence scores for suggestions
"""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    AITask,
    AITaskStatus,
    AITaskType,
    DataSource,
    Document,
    Entity,
    EntityRelation,
    ExtractedData,
    FacetType,
    FacetValue,
)
from app.models.entity_attachment import AttachmentAnalysisStatus, EntityAttachment
from app.models.facet_value import FacetValueSourceType
from app.models.pysis import PySisProcess, PySisProcessField

logger = structlog.get_logger()


class EntityDataFacetService:
    """Service for analyzing entity data and creating facet value suggestions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_enrichment_sources(self, entity_id: UUID) -> dict[str, Any]:
        """
        Get all available data sources for an entity with counts and timestamps.

        Returns:
            Dict with information about each data source type:
            - pysis: PySIS process data
            - relations: Entity relations
            - documents: Crawled documents
            - extractions: AI-extracted data
            - existing_facets: Count of existing facet values
        """
        entity = await self.db.get(Entity, entity_id)
        if not entity:
            raise ValueError(f"Entity nicht gefunden: {entity_id}")

        # PySIS data
        pysis_result = await self.db.execute(
            select(
                func.count(PySisProcessField.id).label("field_count"),
                func.max(PySisProcess.updated_at).label("last_updated"),
            )
            .join(PySisProcess, PySisProcessField.process_id == PySisProcess.id)
            .where(PySisProcess.entity_id == entity_id)
        )
        pysis_row = pysis_result.first()
        pysis_count = pysis_row.field_count if pysis_row else 0
        pysis_last_updated = pysis_row.last_updated if pysis_row else None

        # Relations (both as source and target)
        relations_result = await self.db.execute(
            select(
                func.count(EntityRelation.id).label("count"),
                func.max(EntityRelation.updated_at).label("last_updated"),
            ).where(
                and_(
                    EntityRelation.is_active.is_(True),
                    (EntityRelation.source_entity_id == entity_id) | (EntityRelation.target_entity_id == entity_id),
                )
            )
        )
        relations_row = relations_result.first()
        relations_count = relations_row.count if relations_row else 0
        relations_last_updated = relations_row.last_updated if relations_row else None

        # Documents via DataSource
        documents_result = await self.db.execute(
            select(
                func.count(Document.id).label("count"),
                func.max(Document.processed_at).label("last_updated"),
            )
            .join(DataSource, Document.source_id == DataSource.id)
            .where(
                and_(
                    DataSource.entity_id == entity_id,
                    Document.processing_status == "COMPLETED",
                )
            )
        )
        documents_row = documents_result.first()
        documents_count = documents_row.count if documents_row else 0
        documents_last_updated = documents_row.last_updated if documents_row else None

        # Extractions via Documents
        extractions_result = await self.db.execute(
            select(
                func.count(ExtractedData.id).label("count"),
                func.max(ExtractedData.created_at).label("last_updated"),
            )
            .join(Document, ExtractedData.document_id == Document.id)
            .join(DataSource, Document.source_id == DataSource.id)
            .where(DataSource.entity_id == entity_id)
        )
        extractions_row = extractions_result.first()
        extractions_count = extractions_row.count if extractions_row else 0
        extractions_last_updated = extractions_row.last_updated if extractions_row else None

        # Attachments with completed analysis
        attachments_result = await self.db.execute(
            select(
                func.count(EntityAttachment.id).label("count"),
                func.max(EntityAttachment.analyzed_at).label("last_analyzed"),
            ).where(
                and_(
                    EntityAttachment.entity_id == entity_id,
                    EntityAttachment.analysis_status == AttachmentAnalysisStatus.COMPLETED,
                )
            )
        )
        attachments_row = attachments_result.first()
        attachments_count = attachments_row.count if attachments_row else 0
        attachments_last_updated = attachments_row.last_analyzed if attachments_row else None

        # Existing facet values
        facets_count = await self.db.scalar(
            select(func.count())
            .select_from(FacetValue)
            .where(
                and_(
                    FacetValue.entity_id == entity_id,
                    FacetValue.is_active.is_(True),
                )
            )
        )

        return {
            "entity_id": str(entity_id),
            "entity_name": entity.name,
            "pysis": {
                "available": pysis_count > 0,
                "count": pysis_count,
                "last_updated": (pysis_last_updated.isoformat() if pysis_last_updated else None),
                "label": "PySIS-Daten",
            },
            "relations": {
                "available": relations_count > 0,
                "count": relations_count,
                "last_updated": (relations_last_updated.isoformat() if relations_last_updated else None),
                "label": "Verknüpfungen",
            },
            "documents": {
                "available": documents_count > 0,
                "count": documents_count,
                "last_updated": (documents_last_updated.isoformat() if documents_last_updated else None),
                "label": "Dokumente",
            },
            "extractions": {
                "available": extractions_count > 0,
                "count": extractions_count,
                "last_updated": (extractions_last_updated.isoformat() if extractions_last_updated else None),
                "label": "AI-Extraktionen",
            },
            "attachments": {
                "available": attachments_count > 0,
                "count": attachments_count,
                "last_updated": (attachments_last_updated.isoformat() if attachments_last_updated else None),
                "label": "Anhänge",
            },
            "existing_facets": facets_count or 0,
        }

    async def start_analysis(
        self,
        entity_id: UUID,
        source_types: list[str],
        target_facet_types: list[str] | None = None,
    ) -> AITask:
        """
        Start an AI analysis task for facet enrichment.

        This creates an AITask and triggers the Celery worker. The worker will:
        1. Collect data from selected sources
        2. Analyze with AI
        3. Store preview in AITask.result_data

        Args:
            entity_id: Entity to analyze
            source_types: List of source types to include (pysis, relations, documents, extractions)
            target_facet_types: Optional list of facet type slugs to generate

        Returns:
            AITask for progress tracking
        """
        from workers.ai_tasks import analyze_entity_data_for_facets

        entity = await self.db.get(Entity, entity_id)
        if not entity:
            raise ValueError(f"Entity nicht gefunden: {entity_id}")

        # Validate source types
        valid_sources = {"pysis", "relations", "documents", "extractions", "attachments"}
        invalid_sources = set(source_types) - valid_sources
        if invalid_sources:
            raise ValueError(f"Ungültige Datenquellen: {invalid_sources}")

        # Get available facet types if not specified
        if not target_facet_types:
            ft_result = await self.db.execute(
                select(FacetType.slug).where(
                    and_(
                        FacetType.is_active.is_(True),
                        FacetType.ai_extraction_enabled.is_(True),
                    )
                )
            )
            target_facet_types = [row[0] for row in ft_result.all()]

        if not target_facet_types:
            raise ValueError("Keine aktiven Facet-Typen für AI-Extraktion gefunden")

        # Create AI task
        ai_task = AITask(
            task_type=AITaskType.ENTITY_DATA_ANALYSIS,
            status=AITaskStatus.PENDING,
            name=f"Facet-Anreicherung: {entity.name}",
            description=f"Analysiere Daten aus {', '.join(source_types)} für Facet-Vorschläge",
            entity_id=entity_id,
            started_at=datetime.now(UTC),
            result_data={
                "source_types": source_types,
                "target_facet_types": target_facet_types,
            },
        )
        self.db.add(ai_task)
        await self.db.commit()
        await self.db.refresh(ai_task)

        # Start Celery task
        analyze_entity_data_for_facets.delay(
            str(entity_id),
            source_types,
            target_facet_types,
            str(ai_task.id),
        )

        logger.info(
            "Started entity data analysis task",
            entity_id=str(entity_id),
            task_id=str(ai_task.id),
            source_types=source_types,
        )

        return ai_task

    async def get_analysis_preview(self, task_id: UUID) -> dict[str, Any]:
        """
        Get the preview of proposed changes from a completed analysis task.

        Returns:
            Dict with:
            - status: Task status
            - new_facets: List of proposed new facet values
            - updates: List of proposed updates to existing facets
            - error: Error message if failed
        """
        task = await self.db.get(AITask, task_id)
        if not task:
            raise ValueError(f"Task nicht gefunden: {task_id}")

        if task.status == AITaskStatus.PENDING:
            return {
                "status": "pending",
                "message": "Analyse noch nicht gestartet",
            }
        elif task.status == AITaskStatus.RUNNING:
            return {
                "status": "running",
                "message": "Analyse läuft...",
                "progress_current": task.progress_current,
                "progress_total": task.progress_total,
            }
        elif task.status == AITaskStatus.FAILED:
            return {
                "status": "failed",
                "message": task.error_message or "Unbekannter Fehler",
            }
        elif task.status == AITaskStatus.CANCELLED:
            return {
                "status": "cancelled",
                "message": "Analyse abgebrochen",
            }

        # Task completed - return preview data
        result_data = task.result_data or {}
        return {
            "status": "completed",
            "task_id": str(task.id),
            "entity_id": str(task.entity_id) if task.entity_id else None,
            "new_facets": result_data.get("new_facets", []),
            "updates": result_data.get("updates", []),
            "source_types": result_data.get("source_types", []),
            "analysis_summary": result_data.get("analysis_summary", {}),
        }

    async def apply_changes(
        self,
        task_id: UUID,
        accepted_new_facets: list[int],
        accepted_updates: list[str],
    ) -> dict[str, Any]:
        """
        Apply selected changes from the analysis preview.

        Args:
            task_id: The analysis task ID
            accepted_new_facets: List of indices of accepted new facets
            accepted_updates: List of facet_value_ids of accepted updates

        Returns:
            Dict with created/updated counts
        """
        task = await self.db.get(AITask, task_id)
        if not task:
            raise ValueError(f"Task nicht gefunden: {task_id}")

        if task.status != AITaskStatus.COMPLETED:
            raise ValueError(f"Task ist nicht abgeschlossen: {task.status}")

        result_data = task.result_data or {}
        new_facets = result_data.get("new_facets", [])
        updates = result_data.get("updates", [])

        created_count = 0
        updated_count = 0
        errors = []

        # Create new facets
        for idx in accepted_new_facets:
            if idx < 0 or idx >= len(new_facets):
                errors.append(f"Ungültiger Index für neuen Facet: {idx}")
                continue

            facet_data = new_facets[idx]
            try:
                await self._create_facet_from_preview(facet_data, task.entity_id)
                created_count += 1
            except Exception as e:
                errors.append(f"Fehler bei Facet {idx}: {str(e)}")
                logger.warning(
                    "Failed to create facet from preview",
                    idx=idx,
                    error=str(e),
                )

        # Apply updates
        for facet_value_id in accepted_updates:
            update_data = next(
                (u for u in updates if u.get("facet_value_id") == facet_value_id),
                None,
            )
            if not update_data:
                errors.append(f"Update nicht gefunden: {facet_value_id}")
                continue

            try:
                await self._apply_update_from_preview(update_data)
                updated_count += 1
            except Exception as e:
                errors.append(f"Fehler bei Update {facet_value_id}: {str(e)}")
                logger.warning(
                    "Failed to apply update from preview",
                    facet_value_id=facet_value_id,
                    error=str(e),
                )

        await self.db.commit()

        logger.info(
            "Applied changes from analysis preview",
            task_id=str(task_id),
            created=created_count,
            updated=updated_count,
            errors=len(errors),
        )

        return {
            "created": created_count,
            "updated": updated_count,
            "errors": errors if errors else None,
        }

    async def _create_facet_from_preview(self, facet_data: dict[str, Any], entity_id: UUID) -> FacetValue:
        """Create a new facet value from preview data."""
        # Get facet type
        facet_type = await self.db.execute(select(FacetType).where(FacetType.slug == facet_data.get("facet_type")))
        facet_type = facet_type.scalar_one_or_none()
        if not facet_type:
            raise ValueError(f"FacetType nicht gefunden: {facet_data.get('facet_type')}")

        text_repr = facet_data.get("text", "")[:2000]

        facet_value = FacetValue(
            entity_id=entity_id,
            facet_type_id=facet_type.id,
            value=facet_data.get("value", {}),
            text_representation=text_repr,
            confidence_score=facet_data.get("confidence", 0.5),
            source_type=FacetValueSourceType.AI_ASSISTANT,
            ai_model_used=facet_data.get("ai_model"),
        )
        self.db.add(facet_value)
        await self.db.flush()

        # Generate embedding for semantic similarity search
        from app.utils.similarity import generate_embedding

        embedding = await generate_embedding(text_repr, session=self.db)
        if embedding:
            facet_value.text_embedding = embedding

        return facet_value

    async def _apply_update_from_preview(self, update_data: dict[str, Any]) -> None:
        """Apply an update to an existing facet value."""
        facet_value_id = UUID(update_data.get("facet_value_id"))
        facet_value = await self.db.get(FacetValue, facet_value_id)
        if not facet_value:
            raise ValueError(f"FacetValue nicht gefunden: {facet_value_id}")

        proposed_value = update_data.get("proposed_value", {})
        changed_fields = update_data.get("changes", [])

        # Merge only changed fields
        current_value = facet_value.value or {}
        for field in changed_fields:
            if field in proposed_value:
                current_value[field] = proposed_value[field]

        facet_value.value = current_value

        # Update text representation if provided
        if "text" in update_data:
            facet_value.text_representation = update_data["text"][:2000]

        facet_value.updated_at = datetime.now(UTC)
        await self.db.flush()


# =============================================================================
# Helper Functions for Data Collection (used by Celery worker)
# =============================================================================


async def collect_entity_data(
    db: AsyncSession,
    entity_id: UUID,
    source_types: list[str],
) -> dict[str, Any]:
    """
    Collect all relevant data for an entity from specified sources.

    This is called by the Celery worker to gather data for AI analysis.
    """
    entity = await db.get(Entity, entity_id)
    if not entity:
        raise ValueError(f"Entity nicht gefunden: {entity_id}")

    collected_data = {
        "entity": {
            "id": str(entity.id),
            "name": entity.name,
            "type": entity.entity_type_id,
            "core_attributes": entity.core_attributes,
        },
        "sources": {},
    }

    if "relations" in source_types:
        collected_data["sources"]["relations"] = await _collect_relations(db, entity_id)

    if "documents" in source_types:
        collected_data["sources"]["documents"] = await _collect_documents(db, entity_id)

    if "extractions" in source_types:
        collected_data["sources"]["extractions"] = await _collect_extractions(db, entity_id)

    if "pysis" in source_types:
        collected_data["sources"]["pysis"] = await _collect_pysis(db, entity_id)

    if "attachments" in source_types:
        collected_data["sources"]["attachments"] = await _collect_attachments(db, entity_id)

    return collected_data


async def _collect_relations(db: AsyncSession, entity_id: UUID) -> list[dict[str, Any]]:
    """Collect relations where entity is source or target."""
    # Source relations (this entity -> other)
    source_result = await db.execute(
        select(EntityRelation)
        .options(
            selectinload(EntityRelation.relation_type),
            selectinload(EntityRelation.target_entity).selectinload(Entity.facet_values),
        )
        .where(
            and_(
                EntityRelation.source_entity_id == entity_id,
                EntityRelation.is_active.is_(True),
            )
        )
    )
    source_relations = source_result.scalars().all()

    # Target relations (other -> this entity)
    target_result = await db.execute(
        select(EntityRelation)
        .options(
            selectinload(EntityRelation.relation_type),
            selectinload(EntityRelation.source_entity).selectinload(Entity.facet_values),
        )
        .where(
            and_(
                EntityRelation.target_entity_id == entity_id,
                EntityRelation.is_active.is_(True),
            )
        )
    )
    target_relations = target_result.scalars().all()

    relations_data = []

    for rel in source_relations:
        target = rel.target_entity
        relations_data.append(
            {
                "direction": "outgoing",
                "relation_type": rel.relation_type.slug if rel.relation_type else None,
                "relation_name": rel.relation_type.name if rel.relation_type else None,
                "attributes": rel.attributes,
                "related_entity": {
                    "id": str(target.id),
                    "name": target.name,
                    "facets": [
                        {
                            "type": fv.facet_type_id,
                            "value": fv.value,
                            "text": fv.text_representation,
                        }
                        for fv in (target.facet_values or [])
                        if fv.is_active
                    ][:20],  # Limit for context size
                },
                "confidence": rel.confidence_score,
                "valid_from": rel.valid_from.isoformat() if rel.valid_from else None,
                "valid_until": rel.valid_until.isoformat() if rel.valid_until else None,
            }
        )

    for rel in target_relations:
        source = rel.source_entity
        relations_data.append(
            {
                "direction": "incoming",
                "relation_type": rel.relation_type.slug if rel.relation_type else None,
                "relation_name": rel.relation_type.name if rel.relation_type else None,
                "attributes": rel.attributes,
                "related_entity": {
                    "id": str(source.id),
                    "name": source.name,
                    "facets": [
                        {
                            "type": fv.facet_type_id,
                            "value": fv.value,
                            "text": fv.text_representation,
                        }
                        for fv in (source.facet_values or [])
                        if fv.is_active
                    ][:20],
                },
                "confidence": rel.confidence_score,
                "valid_from": rel.valid_from.isoformat() if rel.valid_from else None,
                "valid_until": rel.valid_until.isoformat() if rel.valid_until else None,
            }
        )

    return relations_data


async def _collect_documents(db: AsyncSession, entity_id: UUID) -> list[dict[str, Any]]:
    """Collect documents linked to entity via DataSource."""
    result = await db.execute(
        select(Document)
        .join(DataSource, Document.source_id == DataSource.id)
        .where(
            and_(
                DataSource.entity_id == entity_id,
                Document.processing_status == "COMPLETED",
            )
        )
        .order_by(Document.processed_at.desc())
        .limit(50)  # Limit for context size
    )
    documents = result.scalars().all()

    return [
        {
            "id": str(doc.id),
            "title": doc.title,
            "url": doc.original_url,
            "type": doc.document_type,
            "date": doc.document_date.isoformat() if doc.document_date else None,
            "text_preview": (doc.raw_text or "")[:2000],  # First 2000 chars
        }
        for doc in documents
    ]


async def _collect_extractions(db: AsyncSession, entity_id: UUID) -> list[dict[str, Any]]:
    """Collect AI extractions from documents."""
    result = await db.execute(
        select(ExtractedData)
        .join(Document, ExtractedData.document_id == Document.id)
        .join(DataSource, Document.source_id == DataSource.id)
        .where(DataSource.entity_id == entity_id)
        .order_by(ExtractedData.created_at.desc())
        .limit(50)
    )
    extractions = result.scalars().all()

    return [
        {
            "id": str(ext.id),
            "type": ext.extraction_type,
            "content": ext.final_content,
            "confidence": ext.confidence_score,
            "created_at": ext.created_at.isoformat(),
        }
        for ext in extractions
    ]


async def _collect_pysis(db: AsyncSession, entity_id: UUID) -> list[dict[str, Any]]:
    """Collect PySIS process fields."""
    result = await db.execute(
        select(PySisProcess).options(selectinload(PySisProcess.fields)).where(PySisProcess.entity_id == entity_id)
    )
    processes = result.scalars().all()

    pysis_data = []
    for process in processes:
        fields_data = []
        for field in process.fields:
            value = field.current_value or field.pysis_value or field.ai_extracted_value
            if value:
                fields_data.append(
                    {
                        "name": field.internal_name,
                        "pysis_name": field.pysis_field_name,
                        "value": value,
                        "source": field.value_source.value if field.value_source else None,
                        "confidence": field.confidence_score,
                    }
                )

        if fields_data:
            pysis_data.append(
                {
                    "process_id": str(process.id),
                    "name": process.name or process.entity_name,
                    "pysis_id": process.pysis_process_id,
                    "fields": fields_data,
                }
            )

    return pysis_data


async def _collect_attachments(db: AsyncSession, entity_id: UUID) -> list[dict[str, Any]]:
    """Collect analyzed attachments with their AI analysis results."""
    result = await db.execute(
        select(EntityAttachment)
        .where(
            and_(
                EntityAttachment.entity_id == entity_id,
                EntityAttachment.analysis_status == AttachmentAnalysisStatus.COMPLETED,
            )
        )
        .order_by(EntityAttachment.analyzed_at.desc())
        .limit(20)  # Limit for context size
    )
    attachments = result.scalars().all()

    attachments_data = []
    for att in attachments:
        if not att.analysis_result:
            continue

        data = {
            "id": str(att.id),
            "filename": att.filename,
            "content_type": att.content_type,
            "is_image": att.is_image,
            "is_pdf": att.is_pdf,
            "analyzed_at": att.analyzed_at.isoformat() if att.analyzed_at else None,
            "description": att.analysis_result.get("description", ""),
            "detected_text": att.analysis_result.get("detected_text", []),
            "entities": att.analysis_result.get("entities", {}),
            "facet_suggestions": att.analysis_result.get("facet_suggestions", []),
        }

        # Include document type for PDFs
        if att.is_pdf and "document_type" in att.analysis_result:
            data["document_type"] = att.analysis_result["document_type"]

        # Include key findings if available
        if "key_findings" in att.analysis_result:
            data["key_findings"] = att.analysis_result["key_findings"]

        attachments_data.append(data)

    return attachments_data


async def get_existing_facets(db: AsyncSession, entity_id: UUID) -> list[dict[str, Any]]:
    """Get existing facet values for duplicate checking."""
    result = await db.execute(
        select(FacetValue)
        .options(selectinload(FacetValue.facet_type))
        .where(
            and_(
                FacetValue.entity_id == entity_id,
                FacetValue.is_active.is_(True),
            )
        )
    )
    facets = result.scalars().all()

    return [
        {
            "id": str(fv.id),
            "facet_type": fv.facet_type.slug if fv.facet_type else None,
            "facet_type_name": fv.facet_type.name if fv.facet_type else None,
            "value": fv.value,
            "text": fv.text_representation,
            "confidence": fv.confidence_score,
            "source_type": fv.source_type.value if fv.source_type else None,
        }
        for fv in facets
    ]


def compute_value_hash(value: dict[str, Any]) -> str:
    """Compute a hash for deduplication."""
    normalized = json.dumps(value, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(normalized.encode()).hexdigest()[:16]  # noqa: S324
