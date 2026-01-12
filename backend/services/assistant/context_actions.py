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
    db: AsyncSession, message: str, context: AssistantContext, intent_data: dict[str, Any]
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
                success=False,
            ), []

        elif action == "create_facet":
            return await _handle_create_facet(db, entity_id, entity_name, action_data)

        elif action == "analyze_entity_data":
            return await _handle_analyze_entity_data(db, entity_id, entity_name, action_data)

        elif action == "show_entity_history":
            return await _handle_show_entity_history(db, entity_id, entity_name, action_data)

        elif action == "add_history_point":
            return await _handle_add_history_point(db, entity_id, entity_name, action_data)

        # Relation Actions
        elif action == "add_relation":
            return await _handle_add_relation(db, entity_id, entity_name, action_data)

        elif action == "remove_relation":
            return await _handle_remove_relation(db, entity_id, entity_name, action_data)

        # Widget Actions (for Summary Dashboards)
        elif action == "add_widget":
            return await _handle_add_widget(db, context, action_data)

        elif action == "remove_widget":
            return await _handle_remove_widget(db, context, action_data)

        elif action == "configure_widget":
            return await _handle_configure_widget(db, context, action_data)

        # Crawler Control Actions
        elif action == "pause_crawl":
            return await _handle_pause_crawl(db, context, action_data)

        elif action == "resume_crawl":
            return await _handle_resume_crawl(db, context, action_data)

        elif action == "cancel_crawl":
            return await _handle_cancel_crawl(db, context, action_data)

        # Category/Source Actions
        elif action == "start_category_crawl":
            return await _handle_start_category_crawl(db, context, action_data)

        elif action == "test_source_connection":
            return await _handle_test_source_connection(db, context, action_data)

        else:
            return ErrorResponseData(message=f"Unbekannte Aktion: {action}", error_code="unknown_action"), []

    except Exception as e:
        logger.error("context_action_error", action=action, error=str(e))
        return ErrorResponseData(message=f"Fehler bei der Ausführung: {str(e)}", error_code="context_action_error"), []


# =============================================================================
# PYSIS STATUS HANDLERS
# =============================================================================


async def _handle_show_pysis_status(
    service: PySisFacetService, entity_id: str, entity_name: str
) -> tuple[ContextActionResponse, list[SuggestedAction]]:
    """Show PySis status for current entity."""
    status = await service.get_pysis_status(UUID(entity_id))

    if not status.get("has_pysis"):
        return ContextActionResponse(
            message=f"**{entity_name}** hat keine verknüpften PySis-Prozesse.",
            action="show_pysis_status",
            entity_id=entity_id,
            entity_name=entity_name,
            success=True,
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
        success=True,
    ), [
        SuggestedAction(label="PySis analysieren", action="query", value="Analysiere PySis für Facets"),
        SuggestedAction(label="Facets anreichern", action="query", value="Reichere Facets mit PySis an"),
    ]


# =============================================================================
# ANALYZE PYSIS HANDLERS
# =============================================================================


async def _handle_analyze_pysis_preview(
    service: PySisFacetService, entity_id: str, entity_name: str
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
            success=False,
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
        success=True,
    ), [
        SuggestedAction(label="✅ Ja, analysieren", action="query", value="Ja, starte die PySis-Analyse"),
        SuggestedAction(label="❌ Abbrechen", action="query", value="Abbrechen"),
    ]


async def _handle_analyze_pysis_execute(
    service: PySisFacetService, entity_id: str, entity_name: str
) -> tuple[ContextActionResponse, list[SuggestedAction]]:
    """Execute PySis analysis for entity."""
    preview = await service.get_operation_preview(UUID(entity_id), "analyze")

    if not preview.get("can_execute"):
        return ContextActionResponse(
            message=preview.get("message", "Analyse nicht möglich"),
            action="analyze_pysis_execute",
            entity_id=entity_id,
            entity_name=entity_name,
            success=False,
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
        success=True,
    ), [
        SuggestedAction(label="Status prüfen", action="query", value="Zeige PySis-Status"),
    ]


# =============================================================================
# ENRICH FACETS HANDLERS
# =============================================================================


async def _handle_enrich_facets_preview(
    service: PySisFacetService, entity_id: str, entity_name: str
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
            success=False,
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
        success=True,
    ), [
        SuggestedAction(label="✅ Ja, anreichern", action="query", value="Ja, starte die Facet-Anreicherung"),
        SuggestedAction(
            label="🔄 Mit Überschreiben", action="query", value="Ja, anreichern und bestehende überschreiben"
        ),
        SuggestedAction(label="❌ Abbrechen", action="query", value="Abbrechen"),
    ]


async def _handle_enrich_facets_execute(
    service: PySisFacetService, entity_id: str, entity_name: str, action_data: dict[str, Any]
) -> tuple[ContextActionResponse, list[SuggestedAction]]:
    """Execute facet enrichment for entity."""
    preview = await service.get_operation_preview(UUID(entity_id), "enrich")

    if not preview.get("can_execute"):
        return ContextActionResponse(
            message=preview.get("message", "Anreicherung nicht möglich"),
            action="enrich_facets_execute",
            entity_id=entity_id,
            entity_name=entity_name,
            success=False,
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
        success=True,
    ), [
        SuggestedAction(label="Status prüfen", action="query", value="Zeige PySis-Status"),
    ]


# =============================================================================
# CREATE FACET HANDLER
# =============================================================================


async def _handle_create_facet(
    db: AsyncSession, entity_id: str, entity_name: str, action_data: dict[str, Any]
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
            success=False,
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
            success=False,
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
            success=False,
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
        is_active=True,
    )
    db.add(facet_value)
    await db.flush()

    # Generate embedding for semantic similarity search
    from app.utils.similarity import generate_embedding

    embedding = await generate_embedding(description, session=db)
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
        success=True,
    ), [
        SuggestedAction(label="Weiteren hinzufügen", action="query", value=f"Füge weiteren {facet_type.name} hinzu"),
        SuggestedAction(label="Facets anzeigen", action="query", value="Zeige alle Facets"),
    ]


# =============================================================================
# ANALYZE ENTITY DATA HANDLER
# =============================================================================


async def _handle_analyze_entity_data(
    db: AsyncSession, entity_id: str, entity_name: str, action_data: dict[str, Any]
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
                success=False,
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
            task_id=str(task.id),
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
            success=False,
        ), []


# =============================================================================
# HISTORY HANDLERS
# =============================================================================


async def _handle_show_entity_history(
    db: AsyncSession, entity_id: str, entity_name: str, action_data: dict[str, Any]
) -> tuple[AssistantResponseData, list[SuggestedAction]]:
    """Display history data for entity."""
    from services.facet_history_service import FacetHistoryService

    facet_type_slug = action_data.get("facet_type_slug") if isinstance(action_data, dict) else None

    try:
        history_service = FacetHistoryService(db)

        if facet_type_slug:
            ft_result = await db.execute(select(FacetType).where(FacetType.slug == facet_type_slug))
            facet_type = ft_result.scalar_one_or_none()

            if not facet_type or facet_type.value_type.value != "history":
                return ContextActionResponse(
                    message=f"Facet-Typ '{facet_type_slug}' ist kein History-Typ.",
                    action="show_entity_history",
                    entity_id=entity_id,
                    entity_name=entity_name,
                    success=False,
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
                    success=True,
                ), [
                    SuggestedAction(
                        label="Datenpunkt hinzufügen",
                        action="query",
                        value=f"Füge Datenpunkt für {facet_type.name} hinzu",
                    ),
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
                preview={"history": history.model_dump() if hasattr(history, "model_dump") else None},
            ), [
                SuggestedAction(
                    label="Datenpunkt hinzufügen", action="query", value=f"Füge Datenpunkt für {facet_type.name} hinzu"
                ),
                SuggestedAction(label="Chart öffnen", action="navigate", value=f"entity/{entity_id}"),
            ]
        else:
            # List available history facet types
            ft_result = await db.execute(select(FacetType).where(FacetType.value_type == "history"))
            history_types = ft_result.scalars().all()

            if not history_types:
                return ContextActionResponse(
                    message="Es gibt noch keine Facet-Typen vom Typ 'History'. Erstelle zuerst einen History-Facet-Typ.",
                    action="show_entity_history",
                    entity_id=entity_id,
                    entity_name=entity_name,
                    success=False,
                ), [
                    SuggestedAction(
                        label="History-Facet erstellen",
                        action="query",
                        value="Erstelle History-Facet-Typ für Haushaltsvolumen",
                    ),
                ]

            msg = f"**Verfügbare History-Facets für {entity_name}:**\n\n"
            for ft in history_types:
                msg += f"- **{ft.name}** (`{ft.slug}`)\n"

            return ContextActionResponse(
                message=msg, action="show_entity_history", entity_id=entity_id, entity_name=entity_name, success=True
            ), [
                SuggestedAction(label=ft.name, action="query", value=f"Zeige {ft.name}-Verlauf")
                for ft in history_types[:3]
            ]

    except Exception as e:
        logger.error("show_entity_history_error", error=str(e))
        return ContextActionResponse(
            message=f"Fehler beim Laden der Verlaufsdaten: {str(e)}",
            action="show_entity_history",
            entity_id=entity_id,
            entity_name=entity_name,
            success=False,
        ), []


async def _handle_add_history_point(
    db: AsyncSession, entity_id: str, entity_name: str, action_data: dict[str, Any]
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
            success=False,
        ), []

    if value is None:
        return ContextActionResponse(
            message="Bitte gib einen Wert an (z.B. 'Füge Haushaltsvolumen 5000000 hinzu').",
            action="add_history_point",
            entity_id=entity_id,
            entity_name=entity_name,
            success=False,
        ), []

    ft_result = await db.execute(select(FacetType).where(FacetType.slug == facet_type_slug))
    facet_type = ft_result.scalar_one_or_none()

    if not facet_type:
        return ContextActionResponse(
            message=f"Facet-Typ '{facet_type_slug}' nicht gefunden.",
            action="add_history_point",
            entity_id=entity_id,
            entity_name=entity_name,
            success=False,
        ), []

    if facet_type.value_type.value != "history":
        return ContextActionResponse(
            message=f"Facet-Typ '{facet_type.name}' ist kein History-Typ.",
            action="add_history_point",
            entity_id=entity_id,
            entity_name=entity_name,
            success=False,
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
            data_point_id=str(data_point.id),
        ), [
            SuggestedAction(label="Verlauf anzeigen", action="query", value=f"Zeige {facet_type.name}-Verlauf"),
            SuggestedAction(
                label="Weiteren hinzufügen", action="query", value=f"Füge weiteren {facet_type.name}-Datenpunkt hinzu"
            ),
        ]

    except Exception as e:
        logger.error("add_history_point_error", error=str(e))
        return ContextActionResponse(
            message=f"Fehler beim Hinzufügen des Datenpunkts: {str(e)}",
            action="add_history_point",
            entity_id=entity_id,
            entity_name=entity_name,
            success=False,
        ), []


# =============================================================================
# RELATION HANDLERS
# =============================================================================


async def _handle_add_relation(
    db: AsyncSession, entity_id: str, entity_name: str, action_data: dict[str, Any]
) -> tuple[AssistantResponseData, list[SuggestedAction]]:
    """Add a relation to another entity."""
    from app.models import Entity, EntityRelation

    target_entity_id = action_data.get("target_entity_id") if isinstance(action_data, dict) else None
    target_entity_name = action_data.get("target_entity_name") if isinstance(action_data, dict) else None
    relation_type = action_data.get("relation_type", "related_to") if isinstance(action_data, dict) else "related_to"

    if not target_entity_id and not target_entity_name:
        return ContextActionResponse(
            message="Bitte gib die Ziel-Entity an (ID oder Name).",
            action="add_relation",
            entity_id=entity_id,
            entity_name=entity_name,
            success=False,
        ), []

    try:
        # Find target entity
        if target_entity_id:
            target_result = await db.execute(select(Entity).where(Entity.id == UUID(target_entity_id)))
            target = target_result.scalar_one_or_none()
        else:
            target_result = await db.execute(
                select(Entity).where(Entity.name.ilike(f"%{target_entity_name}%")).limit(1)
            )
            target = target_result.scalar_one_or_none()

        if not target:
            return ContextActionResponse(
                message=f"Ziel-Entity '{target_entity_name or target_entity_id}' nicht gefunden.",
                action="add_relation",
                entity_id=entity_id,
                entity_name=entity_name,
                success=False,
            ), []

        # Check if relation already exists
        existing = await db.execute(
            select(EntityRelation).where(
                EntityRelation.source_entity_id == UUID(entity_id),
                EntityRelation.target_entity_id == target.id,
                EntityRelation.relation_type == relation_type,
            )
        )
        if existing.scalar_one_or_none():
            return ContextActionResponse(
                message=f"Relation '{relation_type}' zu **{target.name}** existiert bereits.",
                action="add_relation",
                entity_id=entity_id,
                entity_name=entity_name,
                success=False,
            ), []

        # Create relation
        relation = EntityRelation(
            source_entity_id=UUID(entity_id),
            target_entity_id=target.id,
            relation_type=relation_type,
        )
        db.add(relation)
        await db.commit()

        msg = "✅ **Relation hinzugefügt!**\n\n"
        msg += f"- **Von:** {entity_name}\n"
        msg += f"- **Zu:** {target.name}\n"
        msg += f"- **Typ:** {relation_type}\n"

        return ContextActionResponse(
            message=msg, action="add_relation", entity_id=entity_id, entity_name=entity_name, success=True
        ), [
            SuggestedAction(label="Relationen anzeigen", action="query", value="Zeige alle Relationen"),
            SuggestedAction(label="Weitere hinzufügen", action="query", value="Füge weitere Relation hinzu"),
        ]

    except Exception as e:
        logger.error("add_relation_error", error=str(e))
        return ContextActionResponse(
            message=f"Fehler beim Hinzufügen der Relation: {str(e)}",
            action="add_relation",
            entity_id=entity_id,
            entity_name=entity_name,
            success=False,
        ), []


async def _handle_remove_relation(
    db: AsyncSession, entity_id: str, entity_name: str, action_data: dict[str, Any]
) -> tuple[AssistantResponseData, list[SuggestedAction]]:
    """Remove a relation to another entity."""
    from app.models import EntityRelation

    relation_id = action_data.get("relation_id") if isinstance(action_data, dict) else None
    target_entity_id = action_data.get("target_entity_id") if isinstance(action_data, dict) else None
    relation_type = action_data.get("relation_type") if isinstance(action_data, dict) else None

    if not relation_id and not target_entity_id:
        return ContextActionResponse(
            message="Bitte gib die Relation-ID oder die Ziel-Entity-ID an.",
            action="remove_relation",
            entity_id=entity_id,
            entity_name=entity_name,
            success=False,
        ), []

    try:
        if relation_id:
            relation_result = await db.execute(select(EntityRelation).where(EntityRelation.id == UUID(relation_id)))
            relation = relation_result.scalar_one_or_none()
        else:
            query = select(EntityRelation).where(
                EntityRelation.source_entity_id == UUID(entity_id),
                EntityRelation.target_entity_id == UUID(target_entity_id),
            )
            if relation_type:
                query = query.where(EntityRelation.relation_type == relation_type)
            relation_result = await db.execute(query.limit(1))
            relation = relation_result.scalar_one_or_none()

        if not relation:
            return ContextActionResponse(
                message="Relation nicht gefunden.",
                action="remove_relation",
                entity_id=entity_id,
                entity_name=entity_name,
                success=False,
            ), []

        await db.delete(relation)
        await db.commit()

        return ContextActionResponse(
            message="✅ **Relation entfernt!**\n\nDie Verknüpfung wurde erfolgreich gelöscht.",
            action="remove_relation",
            entity_id=entity_id,
            entity_name=entity_name,
            success=True,
        ), [
            SuggestedAction(label="Relationen anzeigen", action="query", value="Zeige alle Relationen"),
        ]

    except Exception as e:
        logger.error("remove_relation_error", error=str(e))
        return ContextActionResponse(
            message=f"Fehler beim Entfernen der Relation: {str(e)}",
            action="remove_relation",
            entity_id=entity_id,
            entity_name=entity_name,
            success=False,
        ), []


# =============================================================================
# WIDGET HANDLERS (Summary Dashboards)
# =============================================================================


async def _handle_add_widget(
    db: AsyncSession, context: AssistantContext, action_data: dict[str, Any]
) -> tuple[AssistantResponseData, list[SuggestedAction]]:
    """Add a widget to a summary dashboard."""
    from app.models import CustomSummary, SummaryWidget

    summary_id = context.page_data.get("summary_id") if context.page_data else None
    widget_type = action_data.get("widget_type") if isinstance(action_data, dict) else None
    title = action_data.get("title") if isinstance(action_data, dict) else None

    if not summary_id:
        return ErrorResponseData(
            message="Kein Summary-Dashboard im aktuellen Kontext gefunden.", error_code="no_summary_context"
        ), []

    if not widget_type:
        return ContextActionResponse(
            message="Bitte gib den Widget-Typ an (z.B. chart, table, stat, text).",
            action="add_widget",
            entity_id=None,
            entity_name=None,
            success=False,
        ), [
            SuggestedAction(label="Chart", action="query", value="Füge Chart-Widget hinzu"),
            SuggestedAction(label="Tabelle", action="query", value="Füge Tabellen-Widget hinzu"),
            SuggestedAction(label="Statistik", action="query", value="Füge Statistik-Widget hinzu"),
        ]

    try:
        summary_result = await db.execute(select(CustomSummary).where(CustomSummary.id == UUID(summary_id)))
        summary = summary_result.scalar_one_or_none()

        if not summary:
            return ErrorResponseData(message="Summary-Dashboard nicht gefunden.", error_code="summary_not_found"), []

        # Get next position
        widgets_result = await db.execute(select(SummaryWidget).where(SummaryWidget.summary_id == summary.id))
        existing_widgets = widgets_result.scalars().all()
        next_position = len(existing_widgets)

        widget = SummaryWidget(
            summary_id=summary.id,
            widget_type=widget_type,
            title=title or f"Neues {widget_type.title()}-Widget",
            position=next_position,
            config=action_data.get("config", {}),
        )
        db.add(widget)
        await db.commit()

        return ContextActionResponse(
            message=f"✅ **Widget hinzugefügt!**\n\n"
            f"- **Typ:** {widget_type}\n"
            f"- **Titel:** {widget.title}\n"
            f"- **Position:** {next_position + 1}\n\n"
            f"Das Widget kann jetzt konfiguriert werden.",
            action="add_widget",
            entity_id=None,
            entity_name=None,
            success=True,
        ), [
            SuggestedAction(label="Widget konfigurieren", action="query", value=f"Konfiguriere Widget {widget.title}"),
            SuggestedAction(label="Dashboard öffnen", action="navigate", value=f"summaries/{summary_id}"),
        ]

    except Exception as e:
        logger.error("add_widget_error", error=str(e))
        return ErrorResponseData(
            message=f"Fehler beim Hinzufügen des Widgets: {str(e)}", error_code="add_widget_error"
        ), []


async def _handle_remove_widget(
    db: AsyncSession, context: AssistantContext, action_data: dict[str, Any]
) -> tuple[AssistantResponseData, list[SuggestedAction]]:
    """Remove a widget from a summary dashboard."""
    from app.models import SummaryWidget

    widget_id = action_data.get("widget_id") if isinstance(action_data, dict) else None

    if not widget_id:
        return ErrorResponseData(message="Bitte gib die Widget-ID an.", error_code="missing_widget_id"), []

    try:
        widget_result = await db.execute(select(SummaryWidget).where(SummaryWidget.id == UUID(widget_id)))
        widget = widget_result.scalar_one_or_none()

        if not widget:
            return ErrorResponseData(message="Widget nicht gefunden.", error_code="widget_not_found"), []

        widget_title = widget.title
        await db.delete(widget)
        await db.commit()

        return ContextActionResponse(
            message=f"✅ **Widget '{widget_title}' entfernt!**",
            action="remove_widget",
            entity_id=None,
            entity_name=None,
            success=True,
        ), []

    except Exception as e:
        logger.error("remove_widget_error", error=str(e))
        return ErrorResponseData(
            message=f"Fehler beim Entfernen des Widgets: {str(e)}", error_code="remove_widget_error"
        ), []


async def _handle_configure_widget(
    db: AsyncSession, context: AssistantContext, action_data: dict[str, Any]
) -> tuple[AssistantResponseData, list[SuggestedAction]]:
    """Configure a widget on a summary dashboard."""
    from app.models import SummaryWidget

    widget_id = action_data.get("widget_id") if isinstance(action_data, dict) else None
    config = action_data.get("config") if isinstance(action_data, dict) else None
    title = action_data.get("title") if isinstance(action_data, dict) else None

    if not widget_id:
        return ErrorResponseData(message="Bitte gib die Widget-ID an.", error_code="missing_widget_id"), []

    try:
        widget_result = await db.execute(select(SummaryWidget).where(SummaryWidget.id == UUID(widget_id)))
        widget = widget_result.scalar_one_or_none()

        if not widget:
            return ErrorResponseData(message="Widget nicht gefunden.", error_code="widget_not_found"), []

        if title:
            widget.title = title
        if config:
            widget.config = {**(widget.config or {}), **config}

        await db.commit()

        return ContextActionResponse(
            message=f"✅ **Widget '{widget.title}' konfiguriert!**\n\nDie Änderungen wurden gespeichert.",
            action="configure_widget",
            entity_id=None,
            entity_name=None,
            success=True,
        ), []

    except Exception as e:
        logger.error("configure_widget_error", error=str(e))
        return ErrorResponseData(
            message=f"Fehler beim Konfigurieren des Widgets: {str(e)}", error_code="configure_widget_error"
        ), []


# =============================================================================
# CRAWLER CONTROL HANDLERS
# =============================================================================


async def _handle_pause_crawl(
    db: AsyncSession, context: AssistantContext, action_data: dict[str, Any]
) -> tuple[AssistantResponseData, list[SuggestedAction]]:
    """Pause a running crawl job."""
    from app.models import CrawlJob, CrawlJobStatus

    job_id = action_data.get("job_id") if isinstance(action_data, dict) else None

    # Try to get from page context if not provided
    if not job_id and context.page_data:
        active_jobs = context.page_data.get("active_jobs", [])
        if active_jobs and len(active_jobs) > 0:
            job_id = active_jobs[0].get("job_id")

    if not job_id:
        return ErrorResponseData(
            message="Keine aktive Crawl-Job-ID gefunden. Bitte gib die Job-ID an.", error_code="missing_job_id"
        ), []

    try:
        job_result = await db.execute(select(CrawlJob).where(CrawlJob.id == UUID(job_id)))
        job = job_result.scalar_one_or_none()

        if not job:
            return ErrorResponseData(message="Crawl-Job nicht gefunden.", error_code="job_not_found"), []

        if job.status != CrawlJobStatus.RUNNING:
            return ContextActionResponse(
                message=f"Job ist nicht aktiv (Status: {job.status.value}).",
                action="pause_crawl",
                entity_id=None,
                entity_name=None,
                success=False,
            ), []

        job.status = CrawlJobStatus.PAUSED
        await db.commit()

        return ContextActionResponse(
            message=f"⏸️ **Crawl-Job pausiert!**\n\n"
            f"- **Job-ID:** `{job_id}`\n"
            f"- **Quelle:** {job.source_name or 'Unbekannt'}\n\n"
            f"Der Job kann mit 'Crawl fortsetzen' wieder gestartet werden.",
            action="pause_crawl",
            entity_id=None,
            entity_name=None,
            success=True,
        ), [
            SuggestedAction(label="Fortsetzen", action="query", value="Setze Crawl fort"),
            SuggestedAction(label="Abbrechen", action="query", value="Breche Crawl ab"),
        ]

    except Exception as e:
        logger.error("pause_crawl_error", error=str(e))
        return ErrorResponseData(message=f"Fehler beim Pausieren: {str(e)}", error_code="pause_crawl_error"), []


async def _handle_resume_crawl(
    db: AsyncSession, context: AssistantContext, action_data: dict[str, Any]
) -> tuple[AssistantResponseData, list[SuggestedAction]]:
    """Resume a paused crawl job."""
    from app.models import CrawlJob, CrawlJobStatus

    job_id = action_data.get("job_id") if isinstance(action_data, dict) else None

    if not job_id and context.page_data:
        active_jobs = context.page_data.get("active_jobs", [])
        if active_jobs:
            for j in active_jobs:
                if j.get("status") == "paused":
                    job_id = j.get("job_id")
                    break

    if not job_id:
        return ErrorResponseData(message="Keine pausierte Crawl-Job-ID gefunden.", error_code="missing_job_id"), []

    try:
        job_result = await db.execute(select(CrawlJob).where(CrawlJob.id == UUID(job_id)))
        job = job_result.scalar_one_or_none()

        if not job:
            return ErrorResponseData(message="Crawl-Job nicht gefunden.", error_code="job_not_found"), []

        if job.status != CrawlJobStatus.PAUSED:
            return ContextActionResponse(
                message=f"Job ist nicht pausiert (Status: {job.status.value}).",
                action="resume_crawl",
                entity_id=None,
                entity_name=None,
                success=False,
            ), []

        job.status = CrawlJobStatus.RUNNING
        await db.commit()

        return ContextActionResponse(
            message=f"▶️ **Crawl-Job fortgesetzt!**\n\n"
            f"- **Job-ID:** `{job_id}`\n"
            f"- **Quelle:** {job.source_name or 'Unbekannt'}\n",
            action="resume_crawl",
            entity_id=None,
            entity_name=None,
            success=True,
        ), [
            SuggestedAction(label="Pausieren", action="query", value="Pausiere Crawl"),
        ]

    except Exception as e:
        logger.error("resume_crawl_error", error=str(e))
        return ErrorResponseData(message=f"Fehler beim Fortsetzen: {str(e)}", error_code="resume_crawl_error"), []


async def _handle_cancel_crawl(
    db: AsyncSession, context: AssistantContext, action_data: dict[str, Any]
) -> tuple[AssistantResponseData, list[SuggestedAction]]:
    """Cancel a crawl job."""
    from app.models import CrawlJob, CrawlJobStatus

    job_id = action_data.get("job_id") if isinstance(action_data, dict) else None

    if not job_id and context.page_data:
        active_jobs = context.page_data.get("active_jobs", [])
        if active_jobs and len(active_jobs) > 0:
            job_id = active_jobs[0].get("job_id")

    if not job_id:
        return ErrorResponseData(message="Keine Crawl-Job-ID gefunden.", error_code="missing_job_id"), []

    try:
        job_result = await db.execute(select(CrawlJob).where(CrawlJob.id == UUID(job_id)))
        job = job_result.scalar_one_or_none()

        if not job:
            return ErrorResponseData(message="Crawl-Job nicht gefunden.", error_code="job_not_found"), []

        if job.status in [CrawlJobStatus.COMPLETED, CrawlJobStatus.FAILED, CrawlJobStatus.CANCELLED]:
            return ContextActionResponse(
                message=f"Job ist bereits beendet (Status: {job.status.value}).",
                action="cancel_crawl",
                entity_id=None,
                entity_name=None,
                success=False,
            ), []

        job.status = CrawlJobStatus.CANCELLED
        await db.commit()

        return ContextActionResponse(
            message=f"🛑 **Crawl-Job abgebrochen!**\n\n"
            f"- **Job-ID:** `{job_id}`\n"
            f"- **Quelle:** {job.source_name or 'Unbekannt'}\n",
            action="cancel_crawl",
            entity_id=None,
            entity_name=None,
            success=True,
        ), []

    except Exception as e:
        logger.error("cancel_crawl_error", error=str(e))
        return ErrorResponseData(message=f"Fehler beim Abbrechen: {str(e)}", error_code="cancel_crawl_error"), []


# =============================================================================
# CATEGORY/SOURCE HANDLERS
# =============================================================================


async def _handle_start_category_crawl(
    db: AsyncSession, context: AssistantContext, action_data: dict[str, Any]
) -> tuple[AssistantResponseData, list[SuggestedAction]]:
    """Start a crawl for all sources in a category."""
    from app.models import Category, Source
    from workers.crawl_tasks import start_crawl_for_source

    category_id = action_data.get("category_id") if isinstance(action_data, dict) else None

    if not category_id and context.page_data:
        category_id = context.page_data.get("category_id")

    if not category_id:
        return ErrorResponseData(
            message="Keine Kategorie-ID gefunden. Bitte gib die Kategorie an.", error_code="missing_category_id"
        ), []

    try:
        category_result = await db.execute(select(Category).where(Category.id == UUID(category_id)))
        category = category_result.scalar_one_or_none()

        if not category:
            return ErrorResponseData(message="Kategorie nicht gefunden.", error_code="category_not_found"), []

        # Count active sources
        sources_result = await db.execute(
            select(Source).where(Source.category_id == category.id, Source.status == "ACTIVE")
        )
        sources = sources_result.scalars().all()

        if not sources:
            return ContextActionResponse(
                message=f"Keine aktiven Quellen in Kategorie **{category.name}** gefunden.",
                action="start_category_crawl",
                entity_id=None,
                entity_name=None,
                success=False,
            ), []

        # Start crawl tasks
        started_count = 0
        for source in sources[:50]:  # Limit to 50 sources at once
            try:
                start_crawl_for_source.delay(str(source.id))
                started_count += 1
            except Exception as task_error:
                logger.warning("Failed to start crawl task", source_id=str(source.id), error=str(task_error))

        msg = f"🚀 **Crawl für Kategorie '{category.name}' gestartet!**\n\n"
        msg += f"- **Gestartete Crawls:** {started_count}\n"
        msg += f"- **Quellen gesamt:** {len(sources)}\n"
        if len(sources) > 50:
            msg += "\n⚠️ Nur die ersten 50 Quellen wurden gestartet."

        return ContextActionResponse(
            message=msg, action="start_category_crawl", entity_id=None, entity_name=None, success=True
        ), [
            SuggestedAction(label="Crawler-Status", action="navigate", value="crawler"),
        ]

    except Exception as e:
        logger.error("start_category_crawl_error", error=str(e))
        return ErrorResponseData(
            message=f"Fehler beim Starten der Crawls: {str(e)}", error_code="start_category_crawl_error"
        ), []


async def _handle_test_source_connection(
    db: AsyncSession, context: AssistantContext, action_data: dict[str, Any]
) -> tuple[AssistantResponseData, list[SuggestedAction]]:
    """Test the connection to a source."""
    import httpx

    from app.models import Source

    source_id = action_data.get("source_id") if isinstance(action_data, dict) else None

    if not source_id and context.page_data:
        source_id = context.page_data.get("source_id")

    if not source_id:
        return ErrorResponseData(
            message="Keine Quellen-ID gefunden. Bitte gib die Quelle an.", error_code="missing_source_id"
        ), []

    try:
        source_result = await db.execute(select(Source).where(Source.id == UUID(source_id)))
        source = source_result.scalar_one_or_none()

        if not source:
            return ErrorResponseData(message="Quelle nicht gefunden.", error_code="source_not_found"), []

        # Test connection
        url = source.url
        success = False
        status_code = None
        error_msg = None
        response_time_ms = None

        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                import time

                start = time.time()
                response = await client.get(url)
                response_time_ms = int((time.time() - start) * 1000)
                status_code = response.status_code
                success = 200 <= status_code < 400
        except httpx.TimeoutException:
            error_msg = "Timeout nach 10 Sekunden"
        except httpx.RequestError as e:
            error_msg = str(e)

        if success:
            msg = "✅ **Verbindung erfolgreich!**\n\n"
            msg += f"- **Quelle:** {source.name}\n"
            msg += f"- **URL:** {url}\n"
            msg += f"- **Status:** {status_code}\n"
            msg += f"- **Antwortzeit:** {response_time_ms}ms\n"
        else:
            msg = "❌ **Verbindung fehlgeschlagen!**\n\n"
            msg += f"- **Quelle:** {source.name}\n"
            msg += f"- **URL:** {url}\n"
            if status_code:
                msg += f"- **Status:** {status_code}\n"
            if error_msg:
                msg += f"- **Fehler:** {error_msg}\n"

        return ContextActionResponse(
            message=msg,
            action="test_source_connection",
            entity_id=None,
            entity_name=None,
            success=success,
            preview={"status_code": status_code, "response_time_ms": response_time_ms, "error": error_msg},
        ), [
            SuggestedAction(label="Crawl starten", action="query", value=f"Starte Crawl für {source.name}"),
        ] if success else []

    except Exception as e:
        logger.error("test_source_connection_error", error=str(e))
        return ErrorResponseData(
            message=f"Fehler beim Testen der Verbindung: {str(e)}", error_code="test_source_connection_error"
        ), []
