"""Assistant Service - Facet Management Handler.

This module handles facet type management operations including:
- Listing existing facet types
- Creating new facet types
- Assigning facet types to entity types
- AI-powered facet type suggestions

Exports:
    - handle_facet_management_request: Main handler for facet management
"""

import json
import re
import time
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import EntityType, FacetType
from app.models.llm_usage import LLMProvider, LLMTaskType
from app.schemas.assistant import (
    AssistantContext,
    AssistantResponseData,
    FacetManagementAction,
    FacetManagementResponse,
    FacetTypePreview,
    SuggestedAction,
)
from services.assistant.common import get_openai_client
from services.llm_usage_tracker import record_llm_usage
from services.translations import Translator

logger = structlog.get_logger()


async def handle_facet_management_request(
    db: AsyncSession, message: str, context: AssistantContext, intent_data: dict[str, Any], translator: Translator
) -> tuple[AssistantResponseData, list[SuggestedAction]]:
    """Handle facet type management requests.

    Args:
        db: Database session
        message: User message
        context: Application context
        intent_data: Extracted intent data
        translator: Translator instance

    Returns:
        Tuple of (FacetManagementResponse, suggested_actions)
    """
    facet_action = intent_data.get("facet_action", "list_facet_types")
    facet_name = intent_data.get("facet_name", "")
    facet_description = intent_data.get("facet_description", "")
    target_entity_types = intent_data.get("target_entity_types", [])

    # Convert string to list if needed
    if isinstance(target_entity_types, str):
        target_entity_types = [t.strip() for t in target_entity_types.split(",") if t.strip()]

    try:
        # Get all facet types
        facet_types = await _get_all_facet_types(db)

        if facet_action == "list_facet_types":
            return await _list_facet_types(facet_types, translator)

        elif facet_action == "create_facet_type":
            return await _preview_create_facet_type(db, facet_name, facet_description, target_entity_types, facet_types)

        elif facet_action == "assign_facet_type":
            return await _handle_assign_facet_type(db, target_entity_types)

        elif facet_action == "suggest_facet_types":
            return await _suggest_facet_types_with_llm(context.current_entity_type, facet_types, message)

        else:
            return FacetManagementResponse(
                message="Unbekannte Facet-Management Aktion.",
                action=FacetManagementAction.LIST_FACET_TYPES,
                requires_confirmation=False,
            ), []

    except Exception as e:
        logger.error("facet_management_error", error=str(e))
        return FacetManagementResponse(
            message=f"Fehler bei der Facet-Verwaltung: {str(e)}",
            action=FacetManagementAction.LIST_FACET_TYPES,
            requires_confirmation=False,
        ), []


async def _get_all_facet_types(db: AsyncSession) -> list[FacetType]:
    """Get all active facet types.

    Args:
        db: Database session

    Returns:
        List of FacetType instances
    """
    result = await db.execute(select(FacetType).where(FacetType.is_active.is_(True)).order_by(FacetType.display_order))
    return result.scalars().all()


async def _list_facet_types(
    facet_types: list[FacetType], translator: Translator
) -> tuple[FacetManagementResponse, list[SuggestedAction]]:
    """List all available facet types.

    Args:
        facet_types: List of FacetType instances
        translator: Translator instance

    Returns:
        Tuple of (response, suggested_actions)
    """
    facet_list = [
        {
            "slug": ft.slug,
            "name": ft.name,
            "name_plural": ft.name_plural,
            "description": ft.description,
            "icon": ft.icon,
            "color": ft.color,
            "value_type": ft.value_type,
            "applicable_entity_types": ft.applicable_entity_type_slugs or [],
            "ai_extraction_enabled": ft.ai_extraction_enabled,
        }
        for ft in facet_types
    ]

    msg = f"**{len(facet_list)} Facet-Typen verfügbar:**\n\n"
    for ft in facet_list[:10]:
        ft.get("icon", "mdi-tag")
        desc = ft.get("description", "Keine Beschreibung")[:50]
        msg += f"- **{ft['name']}** (`{ft['slug']}`): {desc}\n"

    return FacetManagementResponse(
        message=msg,
        action=FacetManagementAction.LIST_FACET_TYPES,
        existing_facet_types=facet_list,
        requires_confirmation=False,
    ), [
        SuggestedAction(label="Neuen Facet-Typ erstellen", action="query", value="Erstelle einen neuen Facet-Typ"),
        SuggestedAction(label="Facet zuweisen", action="query", value="Weise einen Facet-Typ zu"),
    ]


async def _preview_create_facet_type(
    db: AsyncSession,
    facet_name: str,
    facet_description: str,
    target_entity_types: list[str],
    existing_facet_types: list[FacetType],
) -> tuple[FacetManagementResponse, list[SuggestedAction]]:
    """Preview facet type creation.

    Args:
        db: Database session
        facet_name: Name for new facet type
        facet_description: Description
        target_entity_types: List of entity type slugs
        existing_facet_types: Existing facet types for slug validation

    Returns:
        Tuple of (response, suggested_actions)
    """
    if not facet_name:
        return FacetManagementResponse(
            message="Bitte gib einen Namen für den neuen Facet-Typ an.",
            action=FacetManagementAction.CREATE_FACET_TYPE,
            requires_confirmation=False,
        ), []

    # Generate slug from name
    slug = re.sub(r"[^a-z0-9_]", "_", facet_name.lower())
    slug = re.sub(r"_+", "_", slug).strip("_")

    # Check if slug already exists
    for ft in existing_facet_types:
        if ft.slug == slug:
            return FacetManagementResponse(
                message=f"Ein Facet-Typ mit dem Slug '{slug}' existiert bereits. Bitte wähle einen anderen Namen.",
                action=FacetManagementAction.CREATE_FACET_TYPE,
                requires_confirmation=False,
            ), []

    preview = FacetTypePreview(
        name=facet_name,
        name_plural=f"{facet_name}s" if not facet_name.endswith("s") else facet_name,
        slug=slug,
        description=facet_description or f"Automatisch erstellter Facet-Typ: {facet_name}",
        applicable_entity_type_slugs=target_entity_types,
        ai_extraction_enabled=True,
        ai_extraction_prompt=f"Extrahiere Informationen zum Thema '{facet_name}' aus dem Dokument.",
    )

    entity_types_text = ", ".join(target_entity_types) if target_entity_types else "Alle"

    return FacetManagementResponse(
        message=f"Soll ich den Facet-Typ **{facet_name}** erstellen?\n\n"
        f"- Slug: `{slug}`\n"
        f"- Beschreibung: {preview.description}\n"
        f"- Für Entity-Typen: {entity_types_text}",
        action=FacetManagementAction.CREATE_FACET_TYPE,
        facet_type_preview=preview,
        target_entity_types=target_entity_types,
        requires_confirmation=True,
    ), []


async def _handle_assign_facet_type(
    db: AsyncSession, target_entity_types: list[str]
) -> tuple[FacetManagementResponse, list[SuggestedAction]]:
    """Handle facet type assignment to entity types.

    Args:
        db: Database session
        target_entity_types: List of entity type slugs

    Returns:
        Tuple of (response, suggested_actions)
    """
    if not target_entity_types:
        # Get available entity types
        et_result = await db.execute(select(EntityType).where(EntityType.is_active.is_(True)))
        entity_types = et_result.scalars().all()

        msg = "Welchem Entity-Typ soll der Facet-Typ zugewiesen werden?\n\n"
        for et in entity_types:
            msg += f"- `{et.slug}`: {et.name}\n"

        return FacetManagementResponse(
            message=msg, action=FacetManagementAction.ASSIGN_FACET_TYPE, requires_confirmation=False
        ), []

    return FacetManagementResponse(
        message=f"Facet-Typ würde den Entity-Typen {', '.join(target_entity_types)} zugewiesen.",
        action=FacetManagementAction.ASSIGN_FACET_TYPE,
        target_entity_types=target_entity_types,
        requires_confirmation=True,
    ), []


async def _suggest_facet_types_with_llm(
    current_entity_type: str, existing_facet_types: list[FacetType], user_message: str
) -> tuple[FacetManagementResponse, list[SuggestedAction]]:
    """Use LLM to suggest new facet types based on context.

    Args:
        current_entity_type: Current entity type slug
        existing_facet_types: Existing facet types
        user_message: User message for context

    Returns:
        Tuple of (response, suggested_actions)

    Raises:
        ValueError: If Azure OpenAI not configured
    """
    client = get_openai_client()
    if not client:
        raise ValueError("KI-Service nicht erreichbar: Azure OpenAI ist nicht konfiguriert")

    existing_slugs = [ft.slug for ft in existing_facet_types]

    prompt = f"""Basierend auf dem Kontext, schlage neue Facet-Typen vor, die noch nicht existieren.

Entity-Typ: {current_entity_type or "Allgemein"}
Existierende Facet-Typen: {", ".join(existing_slugs)}
Benutzeranfrage: {user_message}

Gib JSON zurück mit max. 3 Vorschlägen:
{{
  "suggestions": [
    {{"name": "Facet-Name", "description": "Kurze Beschreibung", "slug": "facet_slug"}}
  ]
}}

Regeln:
- Keine Duplikate zu existierenden Facet-Typen
- Passend zum Entity-Typ
- Praktisch nutzbar für KI-Extraktion
"""

    try:
        start_time = time.time()
        response = client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[
                {"role": "system", "content": "Du bist ein Datenmodellierungs-Experte. Antworte nur mit JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=500,
            response_format={"type": "json_object"},
        )

        if response.usage:
            await record_llm_usage(
                provider=LLMProvider.AZURE_OPENAI,
                model=settings.azure_openai_deployment_name,
                task_type=LLMTaskType.CHAT,
                task_name="_suggest_facet_types_with_llm",
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                duration_ms=int((time.time() - start_time) * 1000),
                is_error=False,
            )

        result = json.loads(response.choices[0].message.content)
        suggestions = result.get("suggestions", [])

        if suggestions:
            msg = "**Vorgeschlagene Facet-Typen:**\n\n"
            for s in suggestions:
                msg += f"- **{s['name']}**: {s['description']}\n"

            return FacetManagementResponse(
                message=msg,
                action=FacetManagementAction.SUGGEST_FACET_TYPES,
                existing_facet_types=suggestions,
                auto_suggested=True,
                requires_confirmation=False,
            ), [
                SuggestedAction(
                    label=f"'{s['name']}' erstellen", action="query", value=f"Erstelle Facet-Typ {s['name']}"
                )
                for s in suggestions[:3]
            ]

        return FacetManagementResponse(
            message="Keine neuen Facet-Typen vorgeschlagen. Die existierenden Typen scheinen bereits gut abzudecken.",
            action=FacetManagementAction.SUGGEST_FACET_TYPES,
            requires_confirmation=False,
        ), []

    except Exception as e:
        logger.error("facet_suggestion_error", error=str(e))
        raise RuntimeError(f"KI-Service Fehler: Facet-Vorschläge konnten nicht generiert werden - {str(e)}") from None
