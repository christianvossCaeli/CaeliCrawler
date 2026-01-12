"""Assistant Service - Query Handling and Search Processing.

This module handles all query-related operations including:
- Database queries via SmartQueryService
- Context queries about current entity
- Query result formatting and suggestion generation
- Typo correction and fuzzy matching

Exports:
    - handle_query: Process database queries
    - handle_context_query: Process queries about current entity
    - suggest_corrections: Generate query corrections for no-results
"""

import re
import time
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_usage import LLMTaskType
from app.models.user_api_credentials import LLMPurpose
from app.schemas.assistant import (
    AssistantContext,
    QueryResponse,
    QueryResultData,
    SuggestedAction,
)
from services.assistant.common import AIServiceNotAvailableException
from services.assistant.context_builder import build_entity_context, prepare_entity_data_for_ai
from services.assistant.utils import format_entity_link
from services.llm_client_service import LLMClientService
from services.llm_usage_tracker import record_llm_usage
from services.smart_query import SmartQueryService
from services.smart_query.geographic_utils import (
    find_all_geo_suggestions,
    levenshtein_distance,
)
from services.translations import Translator

logger = structlog.get_logger()


async def handle_query(
    db: AsyncSession, message: str, context: AssistantContext, intent_data: dict[str, Any], translator: Translator
) -> tuple[QueryResponse, list[SuggestedAction]]:
    """Handle a database query intent using SmartQueryService.

    Args:
        db: Database session
        message: User message
        context: Application context
        intent_data: Extracted intent data
        translator: Translator instance

    Returns:
        Tuple of (QueryResponse, suggested_actions)
    """
    query_text = intent_data.get("query_text", message)
    smart_query_service = SmartQueryService(db)

    try:
        # Execute query
        result = await smart_query_service.smart_query(query_text, allow_write=False)

        # Check for errors
        if result.get("error"):
            return QueryResponse(
                message=result.get("message", translator.t("query_error", error="KI-Interpretation fehlgeschlagen")),
                data=QueryResultData(),
            ), []

        # Handle COUNT queries
        if result.get("query_type") == "count":
            msg = result.get("message", f"Gefunden: {result.get('total', 0)}")
            interpretation = result.get("query_interpretation", {})
            entity_type = interpretation.get("primary_entity_type", "Einträge")

            return QueryResponse(
                message=msg,
                data=QueryResultData(items=[], total=result.get("total", 0), query_interpretation=interpretation),
            ), [SuggestedAction(label=translator.t("show_list"), action="query", value=f"Liste alle {entity_type}")]

        items = result.get("items", [])
        total = result.get("total", len(items))

        # Handle empty results with suggestions
        if total == 0:
            corrections = await suggest_corrections(message, result.get("query_interpretation"))

            if corrections:
                suggestion_parts = []
                suggested_actions = []

                for correction in corrections:
                    suggestion_parts.append(correction["message"])
                    suggested_actions.append(
                        SuggestedAction(
                            label=correction["suggestion"], action="query", value=correction["corrected_query"]
                        )
                    )

                msg = translator.t("no_results") + "\n\n**Meinten Sie vielleicht:**\n"
                msg += "\n".join(f"- {s}" for s in suggestion_parts)

                return QueryResponse(
                    message=msg,
                    data=QueryResultData(
                        items=[],
                        total=0,
                        query_interpretation=result.get("query_interpretation"),
                        suggestions=corrections,
                    ),
                ), suggested_actions

            msg = translator.t("no_results")
        else:
            # Format success message with entity links
            msg = format_query_result_message(items, total, translator)

        # Build suggested actions
        suggested = build_query_suggestions(total, translator)

        return QueryResponse(
            message=msg,
            data=QueryResultData(
                items=items[:20],  # Limit for chat display
                total=total,
                grouping=result.get("grouping"),
                query_interpretation=result.get("query_interpretation"),
            ),
            follow_up_suggestions=[translator.t("show_more_details"), translator.t("filter_by_criteria")]
            if total > 0
            else [],
        ), suggested

    except Exception as e:
        logger.error("query_error", error=str(e))
        return QueryResponse(message=translator.t("query_error", error=str(e)), data=QueryResultData()), []


async def handle_context_query(
    db: AsyncSession, message: str, context: AssistantContext, intent_data: dict[str, Any], translator: Translator
) -> tuple[QueryResponse, list[SuggestedAction]]:
    """Handle a query about the current entity using AI.

    Args:
        db: Database session
        message: User question
        context: Application context
        intent_data: Extracted intent data
        translator: Translator instance

    Returns:
        Tuple of (QueryResponse, suggested_actions)
    """
    if not context.current_entity_id:
        return QueryResponse(
            message="Du befindest dich aktuell nicht auf einer Entity-Detailseite.", data=QueryResultData()
        ), []

    try:
        # Validate UUID
        entity_id = UUID(context.current_entity_id)

        # Build entity context with all data
        entity_data = await build_entity_context(
            db, entity_id, include_facets=True, include_pysis=True, include_relations=True
        )

        # Use AI to generate intelligent response
        ai_response = await generate_context_response_with_ai(db, user_question=message, entity_data=entity_data)

        # Build items for response
        items = [
            {
                "entity_id": str(entity_id),
                "entity_name": entity_data["name"],
                "entity_type": entity_data["type_slug"],
                "core_attributes": entity_data.get("core_attributes", {}),
                "facets": entity_data.get("facets", {}),
                "pysis_fields": entity_data.get("pysis_fields", {}),
                "location": entity_data.get("location", {}),
            }
        ]

        # Build dynamic suggestions
        suggested = build_context_query_suggestions(entity_data, translator)

        return QueryResponse(message=ai_response, data=QueryResultData(items=items, total=1)), suggested

    except Exception as e:
        logger.error("context_query_error", error=str(e))
        return QueryResponse(message=f"Fehler: {str(e)}", data=QueryResultData()), []


async def generate_context_response_with_ai(
    db: AsyncSession, user_question: str, entity_data: dict[str, Any]
) -> str:
    """Use AI to generate an intelligent response about the entity.

    Args:
        db: Database session
        user_question: User's question
        entity_data: Entity context data

    Returns:
        AI-generated response text

    Raises:
        AIServiceNotAvailableException: If LLM not configured
    """
    llm_service = LLMClientService(db)
    client, config = await llm_service.get_system_client(LLMPurpose.ASSISTANT)
    if not client or not config:
        raise AIServiceNotAvailableException("KI-Service nicht verfügbar. Bitte LLM in Admin-Einstellungen konfigurieren.")

    model_name = llm_service.get_model_name(config)
    provider = llm_service.get_provider(config)

    # Prepare data summary
    data_summary = prepare_entity_data_for_ai(entity_data)

    prompt = f"""Du bist ein hilfreicher Assistent. Der Benutzer fragt nach Informationen über eine Entity.

## Entity-Daten:
{data_summary}

## Benutzer-Frage:
{user_question}

## Anweisungen:
- Beantworte die Frage basierend auf den verfügbaren Daten
- Sei prägnant aber informativ
- Hebe die wichtigsten/relevantesten Informationen hervor
- Wenn der Benutzer nach "wichtigen Infos" oder einer Zusammenfassung fragt, wähle die geschäftsrelevanten Daten aus:
  - Ansprechpartner/Zuständigkeit
  - Projektstatus/Phase
  - Anzahl WEA (Windenergieanlagen)
  - Flächeneigentümer
  - Wichtige Kontakte
  - Pain Points oder Herausforderungen
  - Positive Signale
- Ignoriere technische IDs (Hubspot.Id, etc.) außer der Benutzer fragt explizit danach
- Formatiere die Antwort mit Markdown (fett für wichtige Begriffe, Listen wenn sinnvoll)
- Antworte auf Deutsch
- Maximal 400 Wörter
"""

    start_time = time.time()
    response = await client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": "Du bist ein hilfreicher Assistent für ein CRM/Entity-Management-System im Bereich Windenergie.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=1000,
    )

    if response.usage:
        await record_llm_usage(
            provider=provider,
            model=model_name,
            task_type=LLMTaskType.CHAT,
            task_name="generate_context_response_with_ai",
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            duration_ms=int((time.time() - start_time) * 1000),
            is_error=False,
        )

    return response.choices[0].message.content


async def suggest_corrections(message: str, query_interpretation: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Generate intelligent suggestions when a query returns no results.

    Uses fuzzy matching for geographic terms, entity names, and facet types.

    Args:
        message: Original user message
        query_interpretation: Parsed query interpretation if available

    Returns:
        List of suggestion objects with type, original, suggestion, corrected_query
    """
    suggestions = []

    # Extract words from message
    words = re.findall(r"\b\w+\b", message.lower())

    # 1. Check for geographic typos
    for word in words:
        # Skip very short words and common stop words
        if len(word) < 3 or word in {"in", "an", "am", "im", "von", "aus", "bei", "mit", "und", "oder"}:
            continue

        geo_suggestions = find_all_geo_suggestions(word, threshold=2, max_suggestions=1)
        if geo_suggestions:
            alias, canonical, distance = geo_suggestions[0]
            # Only suggest if it's a reasonable match (not exact)
            if distance > 0:
                corrected_query = message.replace(word, canonical)
                suggestions.append(
                    {
                        "type": "geographic",
                        "original": word,
                        "suggestion": canonical,
                        "corrected_query": corrected_query,
                        "message": f"Meinten Sie '{canonical}'?",
                    }
                )

    # 2. Check for entity type suggestions
    entity_type_aliases = {
        "person": ["personen", "leute", "menschen", "kontakte", "ansprechpartner"],
        "territorial_entity": ["gemeinden", "städte", "kommunen", "ortschaften", "landkreise", "kreis"],
        "organization": ["organisationen", "unternehmen", "firmen", "vereine", "verbände"],
        "event": ["events", "veranstaltungen", "termine", "messen", "konferenzen"],
    }

    for word in words:
        for _entity_type, aliases in entity_type_aliases.items():
            for alias in aliases:
                if levenshtein_distance(word, alias) <= 2 and word != alias:
                    suggestions.append(
                        {
                            "type": "entity_type",
                            "original": word,
                            "suggestion": alias,
                            "corrected_query": message.replace(word, alias),
                            "message": f"Meinten Sie '{alias}'?",
                        }
                    )
                    break

    # 3. Check for facet type suggestions
    facet_aliases = {
        "pain_point": ["pain point", "painpoint", "problem", "probleme", "herausforderung"],
        "positive_signal": ["positive signal", "chance", "potenzial", "signal"],
        "contact": ["kontakt", "kontakte", "ansprechpartner"],
        "event_attendance": ["teilnahme", "event teilnahme", "besuch"],
        "summary": ["zusammenfassung", "summary", "übersicht"],
    }

    for word in words:
        for _facet_type, aliases in facet_aliases.items():
            for alias in aliases:
                if levenshtein_distance(word, alias.replace(" ", "")) <= 2 and word != alias:
                    suggestions.append(
                        {
                            "type": "facet_type",
                            "original": word,
                            "suggestion": alias,
                            "corrected_query": message.replace(word, alias),
                            "message": f"Meinten Sie '{alias}'?",
                        }
                    )
                    break

    # Remove duplicates and limit
    seen = set()
    unique_suggestions = []
    for s in suggestions:
        key = (s["type"], s["original"], s["suggestion"])
        if key not in seen:
            seen.add(key)
            unique_suggestions.append(s)

    return unique_suggestions[:3]  # Limit to 3 suggestions


def format_query_result_message(items: list[dict[str, Any]], total: int, translator: Translator) -> str:
    """Format query results into a human-readable message.

    Args:
        items: Result items
        total: Total count
        translator: Translator instance

    Returns:
        Formatted message string
    """
    if total == 0:
        return translator.t("no_results")

    if total == 1:
        item = items[0]
        name = item.get("entity_name", item.get("name", "Entry"))
        entity_type = item.get("entity_type")
        entity_slug = item.get("entity_slug", item.get("slug"))

        if entity_type and entity_slug:
            entity_link = format_entity_link(entity_type, entity_slug, name)
            return translator.t("found_one", entity_link=entity_link)
        else:
            return translator.t("found_one_plain", name=name)

    # Multiple results - show first few with links
    entity_links = []
    for item in items[:3]:
        name = item.get("entity_name", item.get("name", ""))
        entity_type = item.get("entity_type")
        entity_slug = item.get("entity_slug", item.get("slug"))

        if entity_type and entity_slug and name:
            entity_links.append(format_entity_link(entity_type, entity_slug, name))

    if entity_links:
        remaining = total - len(entity_links)
        links_text = ", ".join(entity_links)
        if remaining > 0:
            return translator.t("found_many", total=total, links_text=links_text, remaining=remaining)
        else:
            return translator.t("found_many_no_remaining", total=total, links_text=links_text)

    return translator.t("found_count", total=total)


def build_query_suggestions(total: int, translator: Translator) -> list[SuggestedAction]:
    """Build suggested actions for query results.

    Args:
        total: Number of results
        translator: Translator instance

    Returns:
        List of suggested actions
    """
    suggestions = []

    if total > 0:
        suggestions.append(
            SuggestedAction(
                label=translator.t("show_details"),
                action="query",
                value="Show more details" if translator.language == "en" else "Zeig mir mehr Details",
            )
        )

    suggestions.append(SuggestedAction(label=translator.t("new_search"), action="query", value="/search "))

    return suggestions


def build_context_query_suggestions(entity_data: dict[str, Any], translator: Translator) -> list[SuggestedAction]:
    """Build suggested actions based on entity context data.

    Args:
        entity_data: Entity context dictionary
        translator: Translator instance

    Returns:
        List of suggested actions
    """
    suggested = []

    # PySIS suggestions
    pysis_data = entity_data.get("pysis_fields", {})
    if pysis_data:
        suggested.append(
            SuggestedAction(label="PySis Details", action="query", value="Zeige mir alle PySis-Daten im Detail")
        )

    # Facet suggestions
    facet_data = entity_data.get("facets", {})
    if facet_data:
        for ft_name in list(facet_data.keys())[:2]:
            suggested.append(
                SuggestedAction(label=ft_name, action="query", value=f"Erzähl mir mehr über die {ft_name}")
            )

    # Always add summary option
    suggested.append(
        SuggestedAction(label="Zusammenfassung", action="query", value="Gib mir eine kurze Zusammenfassung")
    )

    return suggested
