"""Assistant Service - Response Formatting and Presentation.

This module handles formatting of various response types including:
- Help messages and documentation
- Navigation responses
- Summarization responses
- Image analysis responses
- Discussion/document analysis responses
- Facet management responses

Exports:
    - generate_help_response: Generate contextual help
    - handle_navigation: Handle navigation requests
    - handle_summarize: Generate entity or app summary
    - handle_image_analysis: Process image analysis requests
    - handle_discussion: Handle document/discussion analysis
    - handle_facet_management: Handle facet type management
"""

import base64
import time
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models import Entity, FacetType
from app.models.llm_usage import LLMProvider, LLMTaskType
from app.schemas.assistant import (
    SLASH_COMMANDS,
    AssistantContext,
    AssistantResponseData,
    DiscussionResponse,
    ErrorResponseData,
    HelpResponse,
    NavigationResponse,
    NavigationTarget,
    QueryResponse,
    QueryResultData,
    RedirectResponse,
    SuggestedAction,
    ViewMode,
)
from services.assistant.common import get_openai_client
from services.assistant.context_builder import (
    build_app_summary_context,
    build_entity_context,
    get_facet_counts_by_type,
)
from services.assistant.utils import format_entity_link
from services.llm_usage_tracker import record_llm_usage
from services.translations import Translator

logger = structlog.get_logger()


def generate_help_response(
    context: AssistantContext, intent_data: dict[str, Any], translator: Translator
) -> HelpResponse:
    """Generate contextual help response.

    Args:
        context: Application context
        intent_data: Optional help topic data
        translator: Translator instance

    Returns:
        HelpResponse with documentation
    """
    (intent_data or {}).get("help_topic", "")

    # Base help message
    msg = "**Hallo! Ich bin dein Assistent für CaeliCrawler.**\n\n"
    msg += "Ich kann dir helfen mit:\n"
    msg += "- **Suchen**: 'Zeige mir Pain Points von Gemeinden'\n"
    msg += "- **Navigation**: 'Geh zu Gummersbach'\n"
    msg += "- **Zusammenfassungen**: 'Fasse diese Entity zusammen'\n"
    msg += "- **Änderungen**: 'Ändere den Namen zu XY' (im Schreib-Modus)\n\n"

    # Context-specific help
    if context.view_mode == ViewMode.DETAIL and context.current_entity_name:
        msg += f"**Du bist gerade bei:** {context.current_entity_name}\n"
        msg += "Frag mich z.B. 'Was sind die Pain Points hier?' oder 'Zeig mir die Relationen'\n\n"

    # Slash commands
    msg += "**Slash Commands:**\n"
    for cmd in SLASH_COMMANDS:
        msg += f"- `/{cmd.command}` - {cmd.description}\n"

    help_topics = [
        {"title": "Suche", "description": "Wie suche ich nach Entities?"},
        {"title": "Schreib-Modus", "description": "Wie bearbeite ich Daten?"},
        {"title": "Navigation", "description": "Wie navigiere ich in der App?"},
    ]

    suggested_commands = ["/help", "/search", "/summary"]

    return HelpResponse(message=msg, help_topics=help_topics, suggested_commands=suggested_commands)


async def handle_navigation(db: AsyncSession, intent_data: dict[str, Any]) -> NavigationResponse:
    """Handle navigation requests.

    Args:
        db: Database session
        intent_data: Extracted navigation data

    Returns:
        NavigationResponse with target route
    """
    target_name = intent_data.get("target_entity", "")

    if not target_name:
        return NavigationResponse(
            message="Wohin möchtest du navigieren? Nenne mir einen Entity-Namen.",
            target=NavigationTarget(route="/entities"),
        )

    # Search for entity
    try:
        result = await db.execute(
            select(Entity)
            .options(selectinload(Entity.entity_type))
            .where(or_(Entity.name.ilike(f"%{target_name}%"), Entity.slug.ilike(f"%{target_name}%")))
            .limit(5)
        )
        entities = result.scalars().all()

        if not entities:
            return NavigationResponse(
                message=f"Keine Entity mit dem Namen '{target_name}' gefunden.",
                target=NavigationTarget(route=f"/entities?search={target_name}"),
            )

        entity = entities[0]
        type_slug = entity.entity_type.slug if entity.entity_type else "unknown"

        # Include entity link in message
        entity_link = format_entity_link(type_slug, entity.slug, entity.name)
        return NavigationResponse(
            message=f"Navigiere zu {entity_link}",
            target=NavigationTarget(
                route=f"/entities/{type_slug}/{entity.slug}",
                entity_type=type_slug,
                entity_slug=entity.slug,
                entity_name=entity.name,
            ),
        )

    except Exception as e:
        logger.error("navigation_error", error=str(e))
        return NavigationResponse(message=f"Fehler bei der Suche: {str(e)}", target=NavigationTarget(route="/entities"))


async def handle_summarize(
    db: AsyncSession, context: AssistantContext, translator: Translator
) -> tuple[QueryResponse, list[SuggestedAction]]:
    """Generate a summary of the current context.

    Args:
        db: Database session
        context: Application context
        translator: Translator instance

    Returns:
        Tuple of (QueryResponse, suggested_actions)
    """
    if not context.current_entity_id:
        # General app summary
        summary_data = await build_app_summary_context(db)

        msg = "**App-Übersicht:**\n"
        msg += f"- {summary_data['entity_count']} Entities\n"
        msg += f"- {summary_data['facet_count']} Facet-Werte"

        return QueryResponse(
            message=msg,
            data=QueryResultData(items=[], total=0),
            follow_up_suggestions=["Zeige alle Municipalities", "Zeige Pain Points"],
        ), []

    # Entity summary
    try:
        entity_id = UUID(context.current_entity_id)

        # Build entity context
        entity_context = await build_entity_context(
            db, entity_id, include_facets=True, include_pysis=False, include_relations=True
        )

        # Get facet counts
        facet_counts = await get_facet_counts_by_type(db, entity_id)

        msg = f"**Zusammenfassung: {entity_context['name']}**\n\n"
        msg += f"Typ: {entity_context['type']}\n\n"

        if facet_counts:
            msg += "**Facets:**\n"
            for ft_name, count in facet_counts.items():
                msg += f"- {ft_name}: {count}\n"

        relation_count = entity_context.get("relation_count", 0)
        msg += f"\n**Relationen:** {relation_count}"

        # Dynamic suggestions
        suggested = []

        # Get facet types for suggestions
        ft_result = await db.execute(
            select(FacetType).where(FacetType.is_active.is_(True)).order_by(FacetType.display_order).limit(2)
        )
        facet_types = ft_result.scalars().all()

        for ft in facet_types:
            suggested.append(
                SuggestedAction(
                    label=ft.name, action="query", value=f"{ft.name_plural or ft.name} von {entity_context['name']}"
                )
            )

        suggested.append(
            SuggestedAction(label="Relationen", action="query", value=f"Relationen von {entity_context['name']}")
        )

        return QueryResponse(
            message=msg,
            data=QueryResultData(
                items=[
                    {
                        "entity_id": str(entity_id),
                        "entity_name": entity_context["name"],
                        "facet_counts": facet_counts,
                        "relation_count": relation_count,
                    }
                ],
                total=1,
            ),
        ), suggested

    except Exception as e:
        logger.error("summarize_error", error=str(e))
        return QueryResponse(message=f"Fehler: {str(e)}", data=QueryResultData()), []


async def handle_image_analysis(
    message: str, context: AssistantContext, images: list[dict[str, Any]], language: str = "de"
) -> dict[str, Any]:
    """Analyze images using the Vision API.

    Args:
        message: User's message/question about the image
        context: Application context
        images: List of image dicts with 'content', 'content_type', 'filename'
        language: Response language

    Returns:
        Response dict with analysis results
    """
    client = get_openai_client()
    if not client:
        return {
            "success": False,
            "response": ErrorResponseData(
                message="KI-Service nicht verfügbar. Bitte Azure OpenAI konfigurieren.", error_code="ai_not_configured"
            ),
        }

    try:
        # Build content array
        content = []

        # Add user's text message
        user_prompt = message.strip() if message.strip() else "Beschreibe was du auf diesem Bild siehst."

        if language == "de":
            system_instruction = (
                "Du bist ein hilfreicher Assistent für eine Entity-Management-App. "
                "Analysiere das Bild und beantworte die Frage des Benutzers auf Deutsch. "
                "Wenn relevant, extrahiere Daten die für die App nützlich sein könnten "
                "(z.B. Namen, Orte, Kontaktdaten, relevante Informationen)."
            )
        else:
            system_instruction = (
                "You are a helpful assistant for an entity management app. "
                "Analyze the image and answer the user's question in English. "
                "If relevant, extract data that could be useful for the app "
                "(e.g., names, locations, contact details, relevant information)."
            )

        content.append({"type": "text", "text": user_prompt})

        # Add images as base64
        for img in images:
            img_content = img.get("content")
            if isinstance(img_content, bytes):
                img_base64 = base64.b64encode(img_content).decode("utf-8")
            else:
                img_base64 = img_content

            content_type = img.get("content_type", "image/jpeg")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{content_type};base64,{img_base64}", "detail": "high"},
                }
            )

        # Make API call
        start_time = time.time()
        response = client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[{"role": "system", "content": system_instruction}, {"role": "user", "content": content}],
            temperature=0.3,
            max_tokens=2000,
        )

        if response.usage:
            await record_llm_usage(
                provider=LLMProvider.AZURE_OPENAI,
                model=settings.azure_openai_deployment_name,
                task_type=LLMTaskType.CHAT,
                task_name="handle_image_analysis",
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                duration_ms=int((time.time() - start_time) * 1000),
                is_error=False,
            )

        if not response.choices:
            raise ValueError("Leere Antwort vom AI-Service")

        analysis_result = response.choices[0].message.content

        # Build suggested actions
        suggested_actions = []
        if context.current_entity_id:
            suggested_actions.extend(
                [
                    SuggestedAction(label="Als Pain Point speichern", action="create_facet", value="pain_point"),
                    SuggestedAction(label="Als Notiz speichern", action="create_facet", value="summary"),
                ]
            )

        return {
            "success": True,
            "response": QueryResponse(
                type="image_analysis", message=analysis_result, data=QueryResultData(items=[], total=len(images))
            ),
            "suggested_actions": suggested_actions,
        }

    except Exception as e:
        logger.error("image_analysis_error", error=str(e))
        return {
            "success": False,
            "response": ErrorResponseData(
                message=f"Bildanalyse fehlgeschlagen: {str(e)}", error_code="image_analysis_error"
            ),
        }


async def handle_discussion(
    message: str, context: AssistantContext, intent_data: dict[str, Any]
) -> tuple[AssistantResponseData, list[SuggestedAction]]:
    """Handle discussion, document analysis, or general conversation.

    Args:
        message: User message
        context: Application context
        intent_data: Extracted intent data

    Returns:
        Tuple of (DiscussionResponse, suggested_actions)
    """
    client = get_openai_client()
    if not client:
        return ErrorResponseData(
            message="KI-Service nicht verfügbar für Diskussionen.", error_code="ai_not_available"
        ), []

    # Build context for AI
    app_context = f"""
Du bist ein hilfreicher Assistent in einer Entity-Management-App (CaeliCrawler).

Die App verwaltet:
- Entities (z.B. Gemeinden, Personen, Organisationen) mit verschiedenen Typen
- Facets (Eigenschaften wie Pain Points, Positive Signals, Kontakte, Haushaltsvolumen)
- Relations (Beziehungen zwischen Entities)
- Datenquellen für Crawler (Webseiten, APIs, SharePoint)
- Kategorien für die Datensammlung

Aktueller Kontext:
- Route: {context.current_route}
- Entity: {context.current_entity_name or "keine"} (Typ: {context.current_entity_type or "keine"})

Der Benutzer teilt ein Dokument, Anforderungen oder möchte diskutieren.
Analysiere den Text und gib eine hilfreiche Antwort. Wenn es um Features geht,
erkläre was bereits existiert und was noch implementiert werden müsste.
"""

    try:
        start_time = time.time()
        response = client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[{"role": "system", "content": app_context}, {"role": "user", "content": message}],
            temperature=0.7,
            max_tokens=2000,
        )

        if response.usage:
            await record_llm_usage(
                provider=LLMProvider.AZURE_OPENAI,
                model=settings.azure_openai_deployment_name,
                task_type=LLMTaskType.CHAT,
                task_name="handle_discussion",
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                duration_ms=int((time.time() - start_time) * 1000),
                is_error=False,
            )

        ai_response = response.choices[0].message.content

        # Extract key points and recommendations
        key_points, recommendations = extract_discussion_insights(ai_response)

        # Determine analysis type
        analysis_type = determine_analysis_type(message)

        # Build suggested actions
        suggested_actions = build_discussion_suggestions(message)

        return DiscussionResponse(
            message=ai_response,
            analysis_type=analysis_type,
            key_points=key_points[:5],
            recommendations=recommendations[:5],
        ), suggested_actions

    except Exception as e:
        logger.error("discussion_error", error=str(e))
        return ErrorResponseData(message=f"Fehler bei der Analyse: {str(e)}", error_code="discussion_error"), []


def extract_discussion_insights(ai_response: str) -> tuple[list[str], list[str]]:
    """Extract key points and recommendations from AI response.

    Args:
        ai_response: AI-generated response text

    Returns:
        Tuple of (key_points, recommendations)
    """
    key_points = []
    recommendations = []

    lines = ai_response.split("\n")
    in_key_points = False
    in_recommendations = False

    for line in lines:
        line_lower = line.lower().strip()

        if "kernpunkte" in line_lower or "key points" in line_lower or "hauptpunkte" in line_lower:
            in_key_points = True
            in_recommendations = False
            continue
        elif "empfehlung" in line_lower or "recommendation" in line_lower or "nächste schritte" in line_lower:
            in_recommendations = True
            in_key_points = False
            continue
        elif line.startswith("#"):
            in_key_points = False
            in_recommendations = False

        if in_key_points and line.strip().startswith(("-", "•", "*", "1", "2", "3", "4", "5")):
            key_points.append(line.strip().lstrip("-•* 0123456789."))
        elif in_recommendations and line.strip().startswith(("-", "•", "*", "1", "2", "3", "4", "5")):
            recommendations.append(line.strip().lstrip("-•* 0123456789."))

    return key_points, recommendations


def determine_analysis_type(message: str) -> str:
    """Determine the type of analysis from message content.

    Args:
        message: User message

    Returns:
        Analysis type string
    """
    message_lower = message.lower()

    if "anforderung" in message_lower or "requirement" in message_lower:
        return "requirements"
    elif "plan" in message_lower or "vorgehen" in message_lower:
        return "planning"
    elif len(message) > 500:
        return "document"

    return "general"


def build_discussion_suggestions(message: str) -> list[SuggestedAction]:
    """Build suggested actions based on discussion content.

    Args:
        message: User message

    Returns:
        List of suggested actions
    """
    suggestions = []
    message_lower = message.lower()

    if "crawler" in message_lower or "datenquelle" in message_lower:
        suggestions.append(SuggestedAction(label="Datenquellen anzeigen", action="navigate", value="/admin/sources"))

    if "kategorie" in message_lower or "category" in message_lower:
        suggestions.append(SuggestedAction(label="Kategorien verwalten", action="navigate", value="/admin/categories"))

    if "smart query" in message_lower or "plan modus" in message_lower:
        suggestions.append(SuggestedAction(label="Smart Query öffnen", action="navigate", value="/smart-query"))

    return suggestions


def suggest_smart_query_redirect(message: str, intent_data: dict[str, Any]) -> RedirectResponse:
    """Suggest redirecting to Smart Query for complex writes.

    Args:
        message: User message
        intent_data: Intent data

    Returns:
        RedirectResponse
    """
    return RedirectResponse(
        message="Für diese komplexe Operation nutze bitte die Smart Query Seite. Ich leite dich weiter.",
        prefilled_query=message,
        write_mode=True,
    )
