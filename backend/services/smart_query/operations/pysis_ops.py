"""PySis operations for Smart Query Service.

Operations:
- analyze_pysis: Analyze PySis data for an entity
- enrich_facets_from_pysis: Enrich facets with PySis data
- push_to_pysis: Push facet values to PySis
"""

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..entity_operations import find_entity_by_name
from .base import OperationResult, WriteOperation, register_operation

logger = structlog.get_logger()


@register_operation("analyze_pysis")
class AnalyzePySisOperation(WriteOperation):
    """Analyze PySis data for an entity and create facets."""

    def validate(self, command: dict[str, Any]) -> str | None:
        pysis_data = command.get("pysis_data", {})
        if not pysis_data.get("entity_id") and not pysis_data.get("entity_name"):
            return "Entity-ID oder Entity-Name erforderlich"
        return None

    async def execute(
        self,
        session: AsyncSession,
        command: dict[str, Any],
        user_id: UUID | None = None,
    ) -> OperationResult:
        from services.pysis_facet_service import PySisFacetService

        pysis_data = command.get("pysis_data", {})
        entity_id = pysis_data.get("entity_id")
        entity_name = pysis_data.get("entity_name")
        process_id = pysis_data.get("process_id")

        # Find entity by name if no ID provided
        if not entity_id and entity_name:
            entity = await find_entity_by_name(session, entity_name)
            if entity:
                entity_id = entity.id
            else:
                return OperationResult(
                    success=False,
                    message=f"Entity '{entity_name}' nicht gefunden",
                )

        try:
            service = PySisFacetService(session)
            task = await service.analyze_for_facets(
                entity_id=UUID(str(entity_id)) if isinstance(entity_id, str) else entity_id,
                process_id=UUID(str(process_id)) if process_id else None,
                include_empty=pysis_data.get("include_empty", False),
                min_confidence=pysis_data.get("min_confidence", 0.0),
            )
            return OperationResult(
                success=True,
                message="PySis-Analyse gestartet",
                data={"task_id": str(task.id)},
            )
        except ValueError as e:
            return OperationResult(success=False, message=str(e))
        except Exception as e:
            logger.error("PySis analyze failed", error=str(e))
            return OperationResult(success=False, message=f"Fehler: {str(e)}")


@register_operation("enrich_facets_from_pysis")
class EnrichFacetsFromPySisOperation(WriteOperation):
    """Enrich existing facets with PySis data."""

    def validate(self, command: dict[str, Any]) -> str | None:
        pysis_data = command.get("pysis_data", {})
        if not pysis_data.get("entity_id") and not pysis_data.get("entity_name"):
            return "Entity-ID oder Entity-Name erforderlich"
        return None

    async def execute(
        self,
        session: AsyncSession,
        command: dict[str, Any],
        user_id: UUID | None = None,
    ) -> OperationResult:
        from services.pysis_facet_service import PySisFacetService

        pysis_data = command.get("pysis_data", {})
        entity_id = pysis_data.get("entity_id")
        entity_name = pysis_data.get("entity_name")
        facet_type_id = pysis_data.get("facet_type_id")
        overwrite = pysis_data.get("overwrite", False)

        # Find entity by name if no ID provided
        if not entity_id and entity_name:
            entity = await find_entity_by_name(session, entity_name)
            if entity:
                entity_id = entity.id
            else:
                return OperationResult(
                    success=False,
                    message=f"Entity '{entity_name}' nicht gefunden",
                )

        try:
            service = PySisFacetService(session)
            task = await service.enrich_facets_from_pysis(
                entity_id=UUID(str(entity_id)) if isinstance(entity_id, str) else entity_id,
                facet_type_id=UUID(str(facet_type_id)) if facet_type_id else None,
                overwrite=overwrite,
            )
            return OperationResult(
                success=True,
                message="Facet-Anreicherung gestartet",
                data={"task_id": str(task.id)},
            )
        except ValueError as e:
            return OperationResult(success=False, message=str(e))
        except Exception as e:
            logger.error("PySis enrich failed", error=str(e))
            return OperationResult(success=False, message=f"Fehler: {str(e)}")


@register_operation("push_to_pysis")
class PushToPySisOperation(WriteOperation):
    """Push facet values to PySis."""

    def validate(self, command: dict[str, Any]) -> str | None:
        pysis_data = command.get("pysis_data", {})
        if not pysis_data.get("entity_id") and not pysis_data.get("entity_name"):
            return "Entity-ID oder Entity-Name erforderlich"
        return None

    async def execute(
        self,
        session: AsyncSession,
        command: dict[str, Any],
        user_id: UUID | None = None,
    ) -> OperationResult:
        from app.models import Entity
        from app.models.pysis import EntityPySisProcess
        from services.pysis_service import PySisService

        pysis_data = command.get("pysis_data", {})
        entity_name = pysis_data.get("entity_name")
        entity_id = pysis_data.get("entity_id")
        process_id = pysis_data.get("process_id")

        # Find entity
        entity = None
        if entity_id:
            entity = await session.get(Entity, UUID(str(entity_id)))
        elif entity_name:
            entity = await find_entity_by_name(session, entity_name)

        if not entity:
            return OperationResult(
                success=False,
                message=f"Entity nicht gefunden: {entity_name or entity_id}",
            )

        try:
            # Get PySis processes for entity
            process_query = select(EntityPySisProcess).where(
                EntityPySisProcess.entity_id == entity.id,
                EntityPySisProcess.is_active.is_(True),
            )
            if process_id:
                process_query = process_query.where(
                    EntityPySisProcess.pysis_process_id == process_id
                )

            process_result = await session.execute(process_query)
            processes = process_result.scalars().all()

            if not processes:
                return OperationResult(
                    success=False,
                    message=f"Keine aktiven PySis-Prozesse für '{entity.name}' gefunden",
                )

            service = PySisService()
            total_synced = 0

            for process in processes:
                try:
                    sync_result = await service.push_to_pysis(
                        process_id=str(process.pysis_process_id),
                        entity_id=entity.id,
                        session=session,
                    )
                    total_synced += sync_result.get("synced_count", 0)
                except Exception as e:
                    logger.warning(
                        "Push to single PySis process failed",
                        process_id=str(process.pysis_process_id),
                        error=str(e),
                    )

            logger.info(
                "PySis push completed via Smart Query",
                entity_id=str(entity.id),
                entity_name=entity.name,
                synced_fields=total_synced,
            )

            return OperationResult(
                success=True,
                message=f"PySis-Synchronisation für '{entity.name}' abgeschlossen: {total_synced} Felder synchronisiert",
                data={
                    "entity_name": entity.name,
                    "synced_fields": total_synced,
                },
            )

        except Exception as e:
            logger.error("PySis push failed", error=str(e), exc_info=True)
            return OperationResult(
                success=False,
                message=f"Fehler bei PySis-Synchronisation: {str(e)}",
            )
