"""Assistant Service - Context Action Handlers.

This module handles context-aware actions on entities, following a two-step process:
1. Preview: Shows what would happen and asks for confirmation
2. Execute: Performs the action after confirmation

Actions ending with '_execute' skip the preview and run immediately.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FacetType, FacetValue
from app.schemas.assistant import (
    AssistantContext,
    AssistantResponseData,
    ContextActionResponse,
    ErrorResponseData,
    SuggestedAction,
)
from services.pysis_facet_service import PySisFacetService

logger = structlog.get_logger()


async def handle_context_action(
    db: AsyncSession,
    message: str,
    context: AssistantContext,
    intent_data: dict[str, Any]
) -> tuple[AssistantResponseData, list[SuggestedAction]]:
    """Handle context-aware action on current entity.

    Args:
        db: Database session
        message: User message
        context: Current application context
        intent_data: Extracted intent data

    Returns:
        Tuple of (response_data, suggested_actions)
    """
    extracted = intent_data.get("extracted_data", {})
    action = extracted.get("context_action", "show_pysis_status")
    action_data = extracted.get("context_action_data", {})

    entity_id = context.current_entity_id
    entity_name = context.current_entity_name or "Entity"

    try:
        service = PySisFacetService(db)

        if action == "show_pysis_status":
            return await _handle_show_pysis_status(service, entity_id, entity_name)

        elif action == "analyze_pysis":
            return await _handle_analyze_pysis_preview(service, entity_id, entity_name)

        elif action == "analyze_pysis_execute":
            return await _handle_analyze_pysis_execute(service, entity_id, entity_name)

        elif action == "enrich_facets":
            return await _handle_enrich_facets_preview(service, entity_id, entity_name)

        elif action == "enrich_facets_execute":
            return await _handle_enrich_facets_execute(service, entity_id, entity_name, action_data)

        elif action == "start_crawl":
            return ContextActionResponse(
                message=f"Crawl für {entity_name} starten - Feature in Entwicklung.",
                action=action,
                entity_id=entity_id,
                entity_name=entity_name,
                success=False
            ), []

        elif action == "create_facet":
            return await _handle_create_facet(db, entity_id, entity_name, action_data)

        elif action == "analyze_entity_data":
            return await _handle_analyze_entity_data(db, entity_id, entity_name, action_data)

        elif action == "show_entity_history":
            return await _handle_show_entity_history(db, entity_id, entity_name, action_data)

        elif action == "add_history_point":
            return await _handle_add_history_point(db, entity_id, entity_name, action_data)

        else:
            return ErrorResponseData(
                message=f"Unbekannte Aktion: {action}",
                error_code="unknown_action"
            ), []

    except Exception as e:
        logger.error("context_action_error", action=action, error=str(e))
        return ErrorResponseData(
            message=f"Fehler bei der Ausführung: {str(e)}",
            error_code="context_action_error"
        ), []


# =============================================================================
# PYSIS STATUS HANDLERS
# =============================================================================

async def _handle_show_pysis_status(
    service: PySisFacetService,
    entity_id: str,
    entity_name: str
) -> tuple[ContextActionResponse, list[SuggestedAction]]:
    """Show PySis status for current entity."""
    status = await service.get_pysis_status(UUID(entity_id))

    if not status.get("has_pysis"):
        return ContextActionResponse(
            message=f"**{entity_name}** hat keine verknüpften PySis-Prozesse.",
            action="show_pysis_status",
            entity_id=entity_id,
            entity_name=entity_name,
            success=True
        ), []

    processes = status.get("processes", [])
    total_fields = status.get("total_fields", 0)
    msg = f"**PySis-Status für {entity_name}:**\n\n"
    msg += f"- {len(processes)} Prozess(e)\n"
    msg += f"- {total_fields} Felder\n"

    for p in processes[:3]:
        summary = p.get("fields_summary", {})
        msg += f"\n**{p.get('name', 'Prozess')}:** {summary.get('with_values', 0)}/{summary.get('total', 0)} Felder mit Werten"

    return ContextActionResponse(
        message=msg,
        action="show_pysis_status",
        entity_id=entity_id,
        entity_name=entity_name,
        status=status,
        success=True
    ), [
        SuggestedAction(label="PySis analysieren", action="query", value="Analysiere PySis für Facets"),
        SuggestedAction(label="Facets anreichern", action="query", value="Reichere Facets mit PySis an"),
    ]


# =============================================================================
# ANALYZE PYSIS HANDLERS
# =============================================================================

async def _handle_analyze_pysis_preview(
    service: PySisFacetService,
    entity_id: str,
    entity_name: str
) -> tuple[ContextActionResponse, list[SuggestedAction]]:
    """Preview PySis analysis for entity."""
    preview = await service.get_operation_preview(UUID(entity_id), "analyze")

    if not preview.get("can_execute"):
        return ContextActionResponse(
            message=f"**Analyse nicht möglich:**\n{preview.get('message', 'Keine Daten verfügbar')}",
            action="analyze_pysis",
            entity_id=entity_id,
            entity_name=entity_name,
            preview=preview,
            requires_confirmation=False,
            success=False
        ), []

    msg = f"**PySis-Analyse für {entity_name}**\n\n"
    msg += "📊 **Was wird analysiert:**\n"
    msg += f"- {preview.get('fields_with_values', 0)} PySis-Felder mit Werten\n"
    msg += f"- {preview.get('facet_types_count', 0)} Facet-Typen werden geprüft\n\n"

    facet_types = preview.get("facet_types", [])
    if facet_types:
        msg += "**Facet-Typen:**\n"
        for ft in facet_types[:5]:
            msg += f"- {ft.get('name')}\n"
        if len(facet_types) > 5:
            msg += f"- ... und {len(facet_types) - 5} weitere\n"

    msg += "\n⚠️ **Möchtest du die Analyse starten?**"

    return ContextActionResponse(
        message=msg,
        action="analyze_pysis",
        entity_id=entity_id,
        entity_name=entity_name,
        preview=preview,
        requires_confirmation=True,
        success=True
    ), [
        SuggestedAction(label="✅ Ja, analysieren", action="query", value="Ja, starte die PySis-Analyse"),
        SuggestedAction(label="❌ Abbrechen", action="query", value="Abbrechen"),
    ]


async def _handle_analyze_pysis_execute(
    service: PySisFacetService,
    entity_id: str,
    entity_name: str
) -> tuple[ContextActionResponse, list[SuggestedAction]]:
    """Execute PySis analysis for entity."""
    preview = await service.get_operation_preview(UUID(entity_id), "analyze")

    if not preview.get("can_execute"):
        return ContextActionResponse(
            message=preview.get("message", "Analyse nicht möglich"),
            action="analyze_pysis_execute",
            entity_id=entity_id,
            entity_name=entity_name,
            success=False
        ), []

    task = await service.analyze_for_facets(UUID(entity_id))

    msg = f"✅ **PySis-Analyse für {entity_name} gestartet!**\n\n"
    msg += f"- Task-ID: `{task.id}`\n"
    msg += f"- {preview.get('fields_with_values', 0)} Felder werden analysiert\n"
    msg += "\nDie Ergebnisse erscheinen in den Facets der Entity."

    return ContextActionResponse(
        message=msg,
        action="analyze_pysis_execute",
        entity_id=entity_id,
        entity_name=entity_name,
        task_id=str(task.id),
        preview=preview,
        success=True
    ), [
        SuggestedAction(label="Status prüfen", action="query", value="Zeige PySis-Status"),
    ]


# =============================================================================
# ENRICH FACETS HANDLERS
# =============================================================================

async def _handle_enrich_facets_preview(
    service: PySisFacetService,
    entity_id: str,
    entity_name: str
) -> tuple[ContextActionResponse, list[SuggestedAction]]:
    """Preview facet enrichment for entity."""
    preview = await service.get_operation_preview(UUID(entity_id), "enrich")

    if not preview.get("can_execute"):
        return ContextActionResponse(
            message=f"**Anreicherung nicht möglich:**\n{preview.get('message', 'Keine Daten verfügbar')}",
            action="enrich_facets",
            entity_id=entity_id,
            entity_name=entity_name,
            preview=preview,
            requires_confirmation=False,
            success=False
        ), []

    msg = f"**Facet-Anreicherung für {entity_name}**\n\n"
    msg += "📊 **Was wird angereichert:**\n"
    msg += f"- {preview.get('facet_values_count', 0)} bestehende Facets\n"
    msg += f"- mit {preview.get('fields_with_values', 0)} PySis-Feldern\n\n"

    facets_by_type = preview.get("facets_by_type", [])
    if facets_by_type:
        msg += "**Facets nach Typ:**\n"
        for ft in facets_by_type:
            msg += f"- {ft.get('name')}: {ft.get('count')} Einträge\n"

    msg += "\n⚠️ **Hinweis:** Bestehende Werte werden NICHT überschrieben.\n"
    msg += "\n**Möchtest du die Anreicherung starten?**"

    return ContextActionResponse(
        message=msg,
        action="enrich_facets",
        entity_id=entity_id,
        entity_name=entity_name,
        preview=preview,
        requires_confirmation=True,
        success=True
    ), [
        SuggestedAction(label="✅ Ja, anreichern", action="query", value="Ja, starte die Facet-Anreicherung"),
        SuggestedAction(label="🔄 Mit Überschreiben", action="query", value="Ja, anreichern und bestehende überschreiben"),
        SuggestedAction(label="❌ Abbrechen", action="query", value="Abbrechen"),
    ]


async def _handle_enrich_facets_execute(
    service: PySisFacetService,
    entity_id: str,
    entity_name: str,
    action_data: dict[str, Any]
) -> tuple[ContextActionResponse, list[SuggestedAction]]:
    """Execute facet enrichment for entity."""
    preview = await service.get_operation_preview(UUID(entity_id), "enrich")

    if not preview.get("can_execute"):
        return ContextActionResponse(
            message=preview.get("message", "Anreicherung nicht möglich"),
            action="enrich_facets_execute",
            entity_id=entity_id,
            entity_name=entity_name,
            success=False
        ), []

    overwrite = action_data.get("overwrite", False) if isinstance(action_data, dict) else False
    task = await service.enrich_facets_from_pysis(UUID(entity_id), overwrite=overwrite)

    msg = f"✅ **Facet-Anreicherung für {entity_name} gestartet!**\n\n"
    msg += f"- Task-ID: `{task.id}`\n"
    msg += f"- {preview.get('facet_values_count', 0)} Facets werden angereichert\n"
    if overwrite:
        msg += "- ⚠️ Bestehende Werte werden überschrieben\n"
    msg += "\nDie Ergebnisse erscheinen in den Facets der Entity."

    return ContextActionResponse(
        message=msg,
        action="enrich_facets_execute",
        entity_id=entity_id,
        entity_name=entity_name,
        task_id=str(task.id),
        preview=preview,
        success=True
    ), [
        SuggestedAction(label="Status prüfen", action="query", value="Zeige PySis-Status"),
    ]


# =============================================================================
# CREATE FACET HANDLER
# =============================================================================

async def _handle_create_facet(
    db: AsyncSession,
    entity_id: str,
    entity_name: str,
    action_data: dict[str, Any]
) -> tuple[AssistantResponseData, list[SuggestedAction]]:
    """Create a new facet value for entity."""
    facet_type_slug = action_data.get("facet_type") if isinstance(action_data, dict) else None
    description = action_data.get("description", "") if isinstance(action_data, dict) else ""
    severity = action_data.get("severity") if isinstance(action_data, dict) else None
    facet_sub_type = action_data.get("type") if isinstance(action_data, dict) else None

    if not facet_type_slug:
        return ContextActionResponse(
            message="Bitte gib einen Facet-Typ an (z.B. pain_point, positive_signal, contact).",
            action="create_facet",
            entity_id=entity_id,
            entity_name=entity_name,
            success=False
        ), [
            SuggestedAction(label="Pain Point", action="query", value="Füge Pain Point hinzu: "),
            SuggestedAction(label="Positive Signal", action="query", value="Füge Positive Signal hinzu: "),
            SuggestedAction(label="Kontakt", action="query", value="Füge Kontakt hinzu: "),
        ]

    if not description:
        return ContextActionResponse(
            message=f"Bitte beschreibe den {facet_type_slug} der hinzugefügt werden soll.",
            action="create_facet",
            entity_id=entity_id,
            entity_name=entity_name,
            success=False
        ), []

    # Find the facet type
    facet_type_result = await db.execute(
        select(FacetType).where(FacetType.slug == facet_type_slug, FacetType.is_active.is_(True))
    )
    facet_type = facet_type_result.scalar_one_or_none()

    if not facet_type:
        return ContextActionResponse(
            message=f"Facet-Typ '{facet_type_slug}' nicht gefunden. Verfügbare Typen: pain_point, positive_signal, contact, summary.",
            action="create_facet",
            entity_id=entity_id,
            entity_name=entity_name,
            success=False
        ), []

    # Build the value based on facet type
    value = {"description": description}
    if severity and facet_type_slug == "pain_point":
        value["severity"] = severity
    if facet_sub_type:
        value["type"] = facet_sub_type

    # Create the facet value
    from app.models.facet_value import FacetValueSourceType
    facet_value = FacetValue(
        entity_id=UUID(entity_id),
        facet_type_id=facet_type.id,
        value=value,
        text_representation=description,
        source_type=FacetValueSourceType.AI_ASSISTANT,
        confidence_score=1.0,
        human_verified=True,
        is_active=True
    )
    db.add(facet_value)
    await db.flush()

    # Generate embedding for semantic similarity search
    from app.utils.similarity import generate_embedding
    embedding = await generate_embedding(description)
    if embedding:
        facet_value.text_embedding = embedding

    await db.commit()
    await db.refresh(facet_value)

    msg = f"✅ **{facet_type.name} hinzugefügt!**\n\n"
    msg += f"- **Entity:** {entity_name}\n"
    msg += f"- **Beschreibung:** {description}\n"
    if severity:
        msg += f"- **Schweregrad:** {severity}\n"
    msg += "\nDer Facet-Wert wurde erfolgreich erstellt."

    return ContextActionResponse(
        message=msg,
        action="create_facet",
        entity_id=entity_id,
        entity_name=entity_name,
        facet_value_id=str(facet_value.id),
        success=True
    ), [
        SuggestedAction(label="Weiteren hinzufügen", action="query", value=f"Füge weiteren {facet_type.name} hinzu"),
        SuggestedAction(label="Facets anzeigen", action="query", value="Zeige alle Facets"),
    ]


# =============================================================================
# ANALYZE ENTITY DATA HANDLER
# =============================================================================

async def _handle_analyze_entity_data(
    db: AsyncSession,
    entity_id: str,
    entity_name: str,
    action_data: dict[str, Any]
) -> tuple[AssistantResponseData, list[SuggestedAction]]:
    """Extract facets from entity data (PySIS, relations, documents, extractions)."""
    from services.entity_data_facet_service import EntityDataFacetService

    source_types = []
    if isinstance(action_data, dict) and "source_types" in action_data:
        source_types = action_data.get("source_types", [])

    if not source_types:
        source_types = ["pysis", "relations", "documents", "extractions"]

    try:
        service = EntityDataFacetService(db)
        sources_info = await service.get_enrichment_sources(UUID(entity_id))

        available_sources = []
        if sources_info.get("pysis", {}).get("available") and "pysis" in source_types:
            available_sources.append("pysis")
        if sources_info.get("relations", {}).get("available") and "relations" in source_types:
            available_sources.append("relations")
        if sources_info.get("documents", {}).get("available") and "documents" in source_types:
            available_sources.append("documents")
        if sources_info.get("extractions", {}).get("available") and "extractions" in source_types:
            available_sources.append("extractions")

        if not available_sources:
            return ContextActionResponse(
                message=f"Keine Datenquellen für die Analyse von **{entity_name}** verfügbar.\n\n"
                        f"Verfügbare Quellen prüfen:\n"
                        f"- PySIS: {sources_info.get('pysis', {}).get('count', 0)} Felder\n"
                        f"- Relationen: {sources_info.get('relations', {}).get('count', 0)} Verknüpfungen\n"
                        f"- Dokumente: {sources_info.get('documents', {}).get('count', 0)} Dokumente\n"
                        f"- Extraktionen: {sources_info.get('extractions', {}).get('count', 0)} Einträge",
                action="analyze_entity_data",
                entity_id=entity_id,
                entity_name=entity_name,
                success=False
            ), []

        task = await service.start_analysis(
            entity_id=UUID(entity_id),
            source_types=available_sources,
        )

        sources_text = ", ".join(available_sources)
        return ContextActionResponse(
            message=f"**Facet-Analyse gestartet für {entity_name}**\n\n"
                    f"Analysiere: {sources_text}\n\n"
                    f"Die Analyse läuft im Hintergrund. "
                    f"Öffne die Entity-Seite, um den Fortschritt zu sehen und die Ergebnisse zu prüfen.\n\n"
                    f"Task-ID: `{task.id}`",
            action="analyze_entity_data",
            entity_id=entity_id,
            entity_name=entity_name,
            success=True,
            task_id=str(task.id)
        ), [
            SuggestedAction(label="Zur Entity", action="navigate", value=f"entity/{entity_id}"),
        ]

    except Exception as e:
        logger.error("analyze_entity_data_error", error=str(e))
        return ContextActionResponse(
            message=f"Fehler beim Starten der Analyse: {str(e)}",
            action="analyze_entity_data",
            entity_id=entity_id,
            entity_name=entity_name,
            success=False
        ), []


# =============================================================================
# HISTORY HANDLERS
# =============================================================================

async def _handle_show_entity_history(
    db: AsyncSession,
    entity_id: str,
    entity_name: str,
    action_data: dict[str, Any]
) -> tuple[AssistantResponseData, list[SuggestedAction]]:
    """Display history data for entity."""
    from services.facet_history_service import FacetHistoryService

    facet_type_slug = action_data.get("facet_type_slug") if isinstance(action_data, dict) else None

    try:
        history_service = FacetHistoryService(db)

        if facet_type_slug:
            ft_result = await db.execute(
                select(FacetType).where(FacetType.slug == facet_type_slug)
            )
            facet_type = ft_result.scalar_one_or_none()

            if not facet_type or facet_type.value_type.value != "history":
                return ContextActionResponse(
                    message=f"Facet-Typ '{facet_type_slug}' ist kein History-Typ.",
                    action="show_entity_history",
                    entity_id=entity_id,
                    entity_name=entity_name,
                    success=False
                ), []

            history = await history_service.get_history(
                entity_id=UUID(entity_id),
                facet_type_id=facet_type.id,
            )

            if not history.tracks:
                return ContextActionResponse(
                    message=f"Keine Verlaufsdaten für **{facet_type.name}** bei **{entity_name}** vorhanden.",
                    action="show_entity_history",
                    entity_id=entity_id,
                    entity_name=entity_name,
                    success=True
                ), [
                    SuggestedAction(label="Datenpunkt hinzufügen", action="query", value=f"Füge Datenpunkt für {facet_type.name} hinzu"),
                ]

            msg = f"**{facet_type.name}-Verlauf für {entity_name}**\n\n"
            stats = history.statistics
            if stats:
                trend_emoji = "📈" if stats.trend == "up" else ("📉" if stats.trend == "down" else "➡️")
                msg += f"- **Aktueller Wert:** {stats.latest_value} {history.unit_label or ''}\n"
                msg += f"- **Trend:** {trend_emoji} {'+' if stats.change_percent and stats.change_percent > 0 else ''}{stats.change_percent or 0:.1f}%\n"
                msg += f"- **Minimum:** {stats.min_value} | **Maximum:** {stats.max_value}\n"
                msg += f"- **Datenpunkte:** {stats.total_points}\n"

            return ContextActionResponse(
                message=msg,
                action="show_entity_history",
                entity_id=entity_id,
                entity_name=entity_name,
                success=True,
                preview={"history": history.model_dump() if hasattr(history, "model_dump") else None}
            ), [
                SuggestedAction(label="Datenpunkt hinzufügen", action="query", value=f"Füge Datenpunkt für {facet_type.name} hinzu"),
                SuggestedAction(label="Chart öffnen", action="navigate", value=f"entity/{entity_id}"),
            ]
        else:
            # List available history facet types
            ft_result = await db.execute(
                select(FacetType).where(FacetType.value_type == "history")
            )
            history_types = ft_result.scalars().all()

            if not history_types:
                return ContextActionResponse(
                    message="Es gibt noch keine Facet-Typen vom Typ 'History'. Erstelle zuerst einen History-Facet-Typ.",
                    action="show_entity_history",
                    entity_id=entity_id,
                    entity_name=entity_name,
                    success=False
                ), [
                    SuggestedAction(label="History-Facet erstellen", action="query", value="Erstelle History-Facet-Typ für Haushaltsvolumen"),
                ]

            msg = f"**Verfügbare History-Facets für {entity_name}:**\n\n"
            for ft in history_types:
                msg += f"- **{ft.name}** (`{ft.slug}`)\n"

            return ContextActionResponse(
                message=msg,
                action="show_entity_history",
                entity_id=entity_id,
                entity_name=entity_name,
                success=True
            ), [SuggestedAction(label=ft.name, action="query", value=f"Zeige {ft.name}-Verlauf") for ft in history_types[:3]]

    except Exception as e:
        logger.error("show_entity_history_error", error=str(e))
        return ContextActionResponse(
            message=f"Fehler beim Laden der Verlaufsdaten: {str(e)}",
            action="show_entity_history",
            entity_id=entity_id,
            entity_name=entity_name,
            success=False
        ), []


async def _handle_add_history_point(
    db: AsyncSession,
    entity_id: str,
    entity_name: str,
    action_data: dict[str, Any]
) -> tuple[AssistantResponseData, list[SuggestedAction]]:
    """Add a data point to a history facet."""
    from services.facet_history_service import FacetHistoryService

    facet_type_slug = action_data.get("facet_type_slug") if isinstance(action_data, dict) else None
    value = action_data.get("value") if isinstance(action_data, dict) else None
    recorded_at = action_data.get("recorded_at") if isinstance(action_data, dict) else None
    track_key = action_data.get("track_key", "default") if isinstance(action_data, dict) else "default"
    note = action_data.get("note") if isinstance(action_data, dict) else None

    if not facet_type_slug:
        return ContextActionResponse(
            message="Bitte gib einen History-Facet-Typ an (z.B. haushaltsvolumen, einwohnerzahl).",
            action="add_history_point",
            entity_id=entity_id,
            entity_name=entity_name,
            success=False
        ), []

    if value is None:
        return ContextActionResponse(
            message="Bitte gib einen Wert an (z.B. 'Füge Haushaltsvolumen 5000000 hinzu').",
            action="add_history_point",
            entity_id=entity_id,
            entity_name=entity_name,
            success=False
        ), []

    ft_result = await db.execute(
        select(FacetType).where(FacetType.slug == facet_type_slug)
    )
    facet_type = ft_result.scalar_one_or_none()

    if not facet_type:
        return ContextActionResponse(
            message=f"Facet-Typ '{facet_type_slug}' nicht gefunden.",
            action="add_history_point",
            entity_id=entity_id,
            entity_name=entity_name,
            success=False
        ), []

    if facet_type.value_type.value != "history":
        return ContextActionResponse(
            message=f"Facet-Typ '{facet_type.name}' ist kein History-Typ.",
            action="add_history_point",
            entity_id=entity_id,
            entity_name=entity_name,
            success=False
        ), []

    try:
        # Parse recorded_at
        if recorded_at:
            if isinstance(recorded_at, str):
                recorded_at = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
        else:
            recorded_at = datetime.utcnow()

        annotations = {}
        if note:
            annotations["note"] = note

        history_service = FacetHistoryService(db)
        data_point = await history_service.add_data_point(
            entity_id=UUID(entity_id),
            facet_type_id=facet_type.id,
            value=float(value),
            recorded_at=recorded_at,
            track_key=track_key,
            annotations=annotations,
            source_type="AI_ASSISTANT",
        )

        unit = ""
        if facet_type.value_schema and isinstance(facet_type.value_schema, dict):
            props = facet_type.value_schema.get("properties", {})
            unit = props.get("unit_label", props.get("unit", ""))

        msg = "✅ **Datenpunkt hinzugefügt!**\n\n"
        msg += f"- **Entity:** {entity_name}\n"
        msg += f"- **Facet-Typ:** {facet_type.name}\n"
        msg += f"- **Wert:** {value} {unit}\n"
        msg += f"- **Datum:** {recorded_at.strftime('%d.%m.%Y')}\n"
        if note:
            msg += f"- **Notiz:** {note}\n"

        return ContextActionResponse(
            message=msg,
            action="add_history_point",
            entity_id=entity_id,
            entity_name=entity_name,
            success=True,
            data_point_id=str(data_point.id)
        ), [
            SuggestedAction(label="Verlauf anzeigen", action="query", value=f"Zeige {facet_type.name}-Verlauf"),
            SuggestedAction(label="Weiteren hinzufügen", action="query", value=f"Füge weiteren {facet_type.name}-Datenpunkt hinzu"),
        ]

    except Exception as e:
        logger.error("add_history_point_error", error=str(e))
        return ContextActionResponse(
            message=f"Fehler beim Hinzufügen des Datenpunkts: {str(e)}",
            action="add_history_point",
            entity_id=entity_id,
            entity_name=entity_name,
            success=False
        ), []
