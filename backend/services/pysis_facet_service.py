"""
PySis-Facet Service - Einheitlicher Service für PySis-Facet-Operationen.

Dieser Service bietet eine einheitliche Schnittstelle für:
1. Analyse von PySis-Feldern zur Facet-Erstellung (analyze_for_facets)
2. Anreicherung bestehender Facets mit PySis-Daten (enrich_facets_from_pysis)
3. Status-Abfragen und Vorschauen

Kann von verschiedenen Stellen aufgerufen werden:
- Assistant (Chat mit Seitenkontext)
- Smart Query (Write-Befehle)
- API-Endpunkte (UI-Buttons)
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import AITask, AITaskStatus, AITaskType, Entity, FacetType, FacetValue
from app.models.pysis import PySisProcess, PySisProcessField

logger = structlog.get_logger()


class PySisFacetService:
    """Einheitlicher Service für PySis-Facet-Operationen."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze_for_facets(
        self,
        entity_id: UUID,
        process_id: UUID | None = None,
        include_empty: bool = False,
        min_confidence: float = 0.0,
    ) -> AITask:
        """
        Startet Celery-Task für PySis->Facets Analyse.

        Args:
            entity_id: UUID der Entity
            process_id: Optional - spezifischer PySis-Prozess (sonst alle Prozesse der Entity)
            include_empty: Auch leere Felder analysieren
            min_confidence: Minimale Konfidenz für Felder

        Returns:
            AITask für Progress-Tracking
        """
        from workers.ai_tasks import analyze_pysis_fields_for_facets

        # Validiere Entity existiert
        entity = await self.db.get(Entity, entity_id)
        if not entity:
            raise ValueError(f"Entity nicht gefunden: {entity_id}")

        # Finde PySis-Prozess
        if process_id:
            process = await self.db.get(PySisProcess, process_id)
            if not process:
                raise ValueError(f"PySis-Prozess nicht gefunden: {process_id}")
            if process.entity_id != entity_id:
                raise ValueError("PySis-Prozess gehört nicht zu dieser Entity")
        else:
            # Finde ersten Prozess der Entity
            result = await self.db.execute(
                select(PySisProcess)
                .where(PySisProcess.entity_id == entity_id)
                .limit(1)
            )
            process = result.scalar_one_or_none()
            if not process:
                raise ValueError(f"Keine PySis-Prozesse für Entity gefunden: {entity.name}")

        # Erstelle AITask für Tracking
        ai_task = AITask(
            task_type=AITaskType.PYSIS_TO_FACETS,
            status=AITaskStatus.PENDING,
            name=f"PySis-Facet-Analyse: {entity.name}",
            description="Analysiere PySis-Felder und erstelle Facets",
            process_id=process.id,
            started_at=datetime.now(UTC),
        )
        self.db.add(ai_task)
        await self.db.commit()
        await self.db.refresh(ai_task)

        # Starte Celery-Task mit Task-ID für Tracking
        analyze_pysis_fields_for_facets.delay(
            str(process.id),
            include_empty,
            min_confidence,
            str(ai_task.id),  # Pass task ID to avoid duplicate creation
        )

        logger.info(
            "Started analyze_for_facets task",
            entity_id=str(entity_id),
            process_id=str(process.id),
            task_id=str(ai_task.id),
        )

        return ai_task

    async def enrich_facets_from_pysis(
        self,
        entity_id: UUID,
        facet_type_id: UUID | None = None,
        overwrite: bool = False,
    ) -> AITask:
        """
        Startet Celery-Task für Facet-Erstellung/Anreicherung mit PySis-Daten.

        Intelligente Operation:
        - Keine FacetValues vorhanden → Erstellt neue aus PySis-Daten
        - FacetValues vorhanden → Aktualisiert bestehende

        Args:
            entity_id: UUID der Entity
            facet_type_id: Optional - nur diesen FacetType bearbeiten
            overwrite: Bestehende Werte überschreiben

        Returns:
            AITask für Progress-Tracking
        """
        from workers.ai_tasks import enrich_facet_values_from_pysis

        # Validiere Entity existiert
        entity = await self.db.get(Entity, entity_id)
        if not entity:
            raise ValueError(f"Entity nicht gefunden: {entity_id}")

        # Prüfe ob PySis-Prozesse existieren
        process_result = await self.db.execute(
            select(PySisProcess)
            .where(PySisProcess.entity_id == entity_id)
            .limit(1)
        )
        process = process_result.scalar_one_or_none()
        if not process:
            raise ValueError(f"Keine PySis-Prozesse für Entity gefunden: {entity.name}")

        # Zähle FacetValues die angereichert werden könnten
        facet_query = (
            select(func.count())
            .select_from(FacetValue)
            .where(FacetValue.entity_id == entity_id)
            .where(FacetValue.is_active.is_(True))
        )
        if facet_type_id:
            facet_query = facet_query.where(FacetValue.facet_type_id == facet_type_id)
        facet_count = await self.db.scalar(facet_query)

        # Wenn keine FacetValues existieren → Erstelle neue via Analyse
        if facet_count == 0:
            return await self.analyze_for_facets(entity_id, process.id)

        # Erstelle AITask für Tracking
        ai_task = AITask(
            task_type=AITaskType.PYSIS_TO_FACETS,
            status=AITaskStatus.PENDING,
            name=f"Facet-Anreicherung: {entity.name}",
            description=f"Reichere {facet_count} Facets mit PySis-Daten an",
            started_at=datetime.now(UTC),
            progress_total=facet_count,
        )
        self.db.add(ai_task)
        await self.db.commit()
        await self.db.refresh(ai_task)

        # Starte Celery-Task mit Task-ID für Tracking
        enrich_facet_values_from_pysis.delay(
            str(entity_id),
            str(facet_type_id) if facet_type_id else None,
            overwrite,
            str(ai_task.id),  # Pass task ID to avoid duplicate creation
        )

        logger.info(
            "Started enrich_facets_from_pysis task",
            entity_id=str(entity_id),
            facet_type_id=str(facet_type_id) if facet_type_id else None,
            task_id=str(ai_task.id),
            facet_count=facet_count,
        )

        return ai_task

    async def get_operation_preview(
        self,
        entity_id: UUID,
        operation: str,
    ) -> dict[str, Any]:
        """
        Zeigt Vorschau was bei einer Operation passieren würde.

        Args:
            entity_id: UUID der Entity
            operation: "analyze" oder "enrich"

        Returns:
            Dict mit Vorschau-Informationen
        """
        entity = await self.db.get(Entity, entity_id)
        if not entity:
            raise ValueError(f"Entity nicht gefunden: {entity_id}")

        # Lade PySis-Prozesse
        pysis_result = await self.db.execute(
            select(PySisProcess)
            .options(selectinload(PySisProcess.fields))
            .where(PySisProcess.entity_id == entity_id)
        )
        processes = pysis_result.scalars().all()

        if not processes:
            return {
                "can_execute": False,
                "message": "Keine PySis-Prozesse gefunden",
                "pysis_processes": 0,
                "pysis_fields": 0,
            }

        # Zähle Felder mit Werten
        total_fields = 0
        fields_with_values = 0
        for p in processes:
            for f in p.fields:
                total_fields += 1
                if f.current_value or f.pysis_value or f.ai_extracted_value:
                    fields_with_values += 1

        if operation == "analyze":
            # Lade aktive FacetTypes
            ft_result = await self.db.execute(
                select(FacetType)
                .where(FacetType.is_active.is_(True))
                .where(FacetType.ai_extraction_enabled.is_(True))
            )
            facet_types = ft_result.scalars().all()

            return {
                "can_execute": fields_with_values > 0 and len(facet_types) > 0,
                "message": f"{fields_with_values} Felder werden für {len(facet_types)} FacetTypes analysiert",
                "operation": "analyze_for_facets",
                "entity_name": entity.name,
                "pysis_processes": len(processes),
                "pysis_fields": total_fields,
                "fields_with_values": fields_with_values,
                "facet_types_count": len(facet_types),
                "facet_types": [{"slug": ft.slug, "name": ft.name} for ft in facet_types],
            }

        elif operation == "enrich":
            # Zähle bestehende FacetValues
            facet_count = await self.db.scalar(
                select(func.count())
                .select_from(FacetValue)
                .where(FacetValue.entity_id == entity_id)
                .where(FacetValue.is_active.is_(True))
            )

            # Lade aktive FacetTypes für neue Erstellung
            ft_result = await self.db.execute(
                select(FacetType)
                .where(FacetType.is_active.is_(True))
                .where(FacetType.ai_extraction_enabled.is_(True))
            )
            facet_types = ft_result.scalars().all()

            # Wenn keine FacetValues existieren → Zeige Erstellungs-Preview
            if facet_count == 0:
                return {
                    "can_execute": fields_with_values > 0 and len(facet_types) > 0,
                    "message": f"Keine FacetValues vorhanden. Es werden NEUE erstellt aus {fields_with_values} PySis-Feldern für {len(facet_types)} Facet-Typen.",
                    "operation": "enrich_facets",
                    "mode": "create",
                    "entity_name": entity.name,
                    "pysis_processes": len(processes),
                    "pysis_fields": total_fields,
                    "fields_with_values": fields_with_values,
                    "facet_values_count": 0,
                    "facet_types_count": len(facet_types),
                    "facet_types": [{"slug": ft.slug, "name": ft.name} for ft in facet_types],
                    "facets_by_type": [],
                }

            # Gruppiere nach FacetType
            facet_by_type = await self.db.execute(
                select(FacetType.slug, FacetType.name, func.count(FacetValue.id))
                .join(FacetValue, FacetType.id == FacetValue.facet_type_id)
                .where(FacetValue.entity_id == entity_id)
                .where(FacetValue.is_active.is_(True))
                .group_by(FacetType.slug, FacetType.name)
            )
            facet_counts = [
                {"slug": row[0], "name": row[1], "count": row[2]}
                for row in facet_by_type.all()
            ]

            return {
                "can_execute": fields_with_values > 0,
                "message": f"{facet_count} bestehende Facets werden mit {fields_with_values} PySis-Feldern aktualisiert",
                "operation": "enrich_facets",
                "mode": "update",
                "entity_name": entity.name,
                "pysis_processes": len(processes),
                "pysis_fields": total_fields,
                "fields_with_values": fields_with_values,
                "facet_values_count": facet_count,
                "facets_by_type": facet_counts,
            }

        else:
            raise ValueError(f"Unbekannte Operation: {operation}")

    async def get_pysis_status(
        self,
        entity_id: UUID,
    ) -> dict[str, Any]:
        """
        Zeigt den PySis-Status einer Entity.

        Args:
            entity_id: UUID der Entity

        Returns:
            Dict mit Status-Informationen
        """
        entity = await self.db.get(Entity, entity_id)
        if not entity:
            raise ValueError(f"Entity nicht gefunden: {entity_id}")

        # Lade PySis-Prozesse mit Feldern
        pysis_result = await self.db.execute(
            select(PySisProcess)
            .options(selectinload(PySisProcess.fields))
            .where(PySisProcess.entity_id == entity_id)
        )
        processes = pysis_result.scalars().all()

        if not processes:
            return {
                "has_pysis": False,
                "message": "Keine PySis-Prozesse verknüpft",
                "entity_name": entity.name,
            }

        # Sammle Status-Informationen
        process_info = []
        for p in processes:
            fields_summary = {
                "total": len(p.fields),
                "with_values": 0,
                "ai_enabled": 0,
                "needs_push": 0,
            }
            field_list = []

            for f in p.fields:
                value = f.current_value or f.pysis_value or f.ai_extracted_value
                if value:
                    fields_summary["with_values"] += 1
                if f.ai_extraction_enabled:
                    fields_summary["ai_enabled"] += 1
                if f.needs_push:
                    fields_summary["needs_push"] += 1

                field_list.append({
                    "name": f.internal_name,
                    "pysis_name": f.pysis_field_name,
                    "has_value": bool(value),
                    "value_preview": str(value)[:100] if value else None,
                    "source": f.value_source.value if f.value_source else None,
                    "ai_enabled": f.ai_extraction_enabled,
                    "confidence": f.confidence_score,
                })

            process_info.append({
                "id": str(p.id),
                "pysis_id": p.pysis_process_id,
                "name": p.name or p.entity_name,
                "status": p.sync_status.value if p.sync_status else "UNKNOWN",
                "last_sync": p.last_synced_at.isoformat() if p.last_synced_at else None,
                "fields_summary": fields_summary,
                "fields": field_list[:20],  # Limit für Übersicht
            })

        # Lade letzte AITasks
        task_result = await self.db.execute(
            select(AITask)
            .where(AITask.process_id.in_([p.id for p in processes]))
            .order_by(AITask.scheduled_at.desc())
            .limit(5)
        )
        recent_tasks = [
            {
                "id": str(t.id),
                "type": t.task_type.value,
                "status": t.status.value,
                "name": t.name,
                "scheduled_at": t.scheduled_at.isoformat() if t.scheduled_at else None,
                "fields_extracted": t.fields_extracted,
            }
            for t in task_result.scalars().all()
        ]

        return {
            "has_pysis": True,
            "entity_name": entity.name,
            "processes": process_info,
            "recent_tasks": recent_tasks,
            "total_processes": len(processes),
            "total_fields": sum(len(p.fields) for p in processes),
        }

    async def get_entity_pysis_summary(
        self,
        entity_id: UUID,
    ) -> dict[str, Any] | None:
        """
        Kurze Zusammenfassung für UI-Anzeige.

        Returns:
            Dict mit Zusammenfassung oder None wenn keine PySis-Daten
        """
        entity = await self.db.get(Entity, entity_id)
        if not entity:
            return None

        # Schnelle Zählung
        pysis_count = await self.db.scalar(
            select(func.count())
            .select_from(PySisProcess)
            .where(PySisProcess.entity_id == entity_id)
        )

        if pysis_count == 0:
            return None

        field_count = await self.db.scalar(
            select(func.count())
            .select_from(PySisProcessField)
            .join(PySisProcess, PySisProcessField.process_id == PySisProcess.id)
            .where(PySisProcess.entity_id == entity_id)
        )

        return {
            "has_pysis": True,
            "process_count": pysis_count,
            "field_count": field_count,
        }
