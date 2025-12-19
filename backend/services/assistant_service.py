"""Assistant Service - KI-gestützter Chat-Assistent für die App."""

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

import structlog
from openai import AzureOpenAI
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Entity,
    EntityType,
    FacetType,
    FacetValue,
    RelationType,
    EntityRelation,
)
from app.schemas.assistant import (
    AssistantContext,
    AssistantChatResponse,
    AssistantResponseData,
    ConversationMessage,
    IntentType,
    ViewMode,
    QueryResponse,
    QueryResultData,
    ActionPreviewResponse,
    ActionDetails,
    ActionChange,
    NavigationResponse,
    NavigationTarget,
    RedirectResponse,
    HelpResponse,
    ErrorResponseData,
    SuggestedAction,
    BatchActionChatResponse,
    BatchActionPreview,
    FacetManagementResponse,
    FacetManagementAction,
    FacetTypePreview,
    SLASH_COMMANDS,
)
from services.smart_query import SmartQueryService
from services.translations import Translator

logger = structlog.get_logger()

# Azure OpenAI client
client = None
if os.getenv("AZURE_OPENAI_API_KEY"):
    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )


INTENT_CLASSIFICATION_PROMPT = """Du bist ein Intent-Classifier für einen Chat-Assistenten in einer Entity-Management-App.

## Kontext der aktuellen Seite:
- Route: {current_route}
- Entity-Typ: {entity_type}
- Entity-Name: {entity_name}
- View-Mode: {view_mode}

## Verfügbare Intents:
1. QUERY - Benutzer stellt eine Frage/Suche (z.B. "Zeige Pain Points", "Welche Events gibt es?")
2. CONTEXT_QUERY - Frage bezieht sich auf aktuelle Entity (z.B. "Was sind die Details?", "Zeig mir mehr")
3. INLINE_EDIT - Einfache Änderung an aktueller Entity (z.B. "Ändere den Namen zu X", "Setze Position auf Y")
4. COMPLEX_WRITE - Komplexe Erstellung (z.B. "Erstelle neue Category", "Lege neuen EntityType an")
5. NAVIGATION - Benutzer will zu einer anderen Seite (z.B. "Geh zu Gummersbach", "Zeig mir Max Mueller")
6. SUMMARIZE - Benutzer will Zusammenfassung (z.B. "Fasse zusammen", "Gib mir einen Überblick")
7. HELP - Benutzer braucht Hilfe (z.B. "Wie funktioniert das?", "Was kann ich hier tun?")
8. BATCH_ACTION - Benutzer will Massenoperation durchführen (z.B. "Füge allen Gemeinden in NRW Pain Point hinzu", "Aktualisiere alle Entities vom Typ X")
9. FACET_MANAGEMENT - Benutzer will Facet-Typen erstellen, zuweisen oder verwalten (z.B. "Erstelle einen neuen Facet-Typ", "Welche Facets gibt es für Gemeinden?", "Lege Attribute für diesen Entity-Typ fest", "Schlage mir passende Facets vor")

## Slash Commands:
- /help - Hilfe anzeigen
- /search <query> - Suchen
- /create <type> <details> - Erstellen (→ COMPLEX_WRITE)
- /summary - Zusammenfassung (→ SUMMARIZE)
- /navigate <entity> - Navigation

Analysiere die Nachricht und gib JSON zurück:
{{
  "intent": "QUERY|CONTEXT_QUERY|INLINE_EDIT|COMPLEX_WRITE|NAVIGATION|SUMMARIZE|HELP|BATCH_ACTION|FACET_MANAGEMENT",
  "confidence": 0.0-1.0,
  "extracted_data": {{
    "query_text": "optional: der Suchtext",
    "target_entity": "optional: Ziel-Entity Name",
    "target_type": "optional: entity type",
    "field_to_edit": "optional: welches Feld ändern",
    "new_value": "optional: neuer Wert",
    "help_topic": "optional: Hilfe-Thema",
    "batch_action_type": "optional: add_facet|update_field|add_relation|remove_facet",
    "batch_target_filter": "optional: Filter für Ziel-Entities (z.B. entity_type, location)",
    "batch_action_data": "optional: Daten für die Aktion (z.B. facet_type, value)",
    "facet_action": "optional: create_facet_type|assign_facet_type|list_facet_types|suggest_facet_types",
    "facet_name": "optional: Name des neuen Facet-Typs",
    "facet_description": "optional: Beschreibung",
    "target_entity_types": "optional: Liste von Entity-Typ-Slugs für Zuweisung"
  }},
  "reasoning": "Kurze Begründung"
}}

Benutzer-Nachricht: {message}
"""

RESPONSE_GENERATION_PROMPT = """Du bist ein freundlicher Assistent. Formuliere eine natürliche deutsche Antwort basierend auf den Daten.

Kontext:
- Aktuelle Seite: {context}
- Intent: {intent}
- Ergebnis-Daten: {data}

Regeln:
- Antworte auf Deutsch
- Sei prägnant aber hilfreich
- Nutze die konkreten Daten in deiner Antwort
- Bei vielen Ergebnissen, fasse zusammen
- Schlage Follow-up Fragen vor wenn sinnvoll

Generiere eine Antwort-Nachricht (max 200 Wörter):
"""


def format_entity_link(entity_type: str, slug: str, name: str) -> str:
    """Format an entity reference as a clickable link: [[type:slug:name]]."""
    return f"[[{entity_type}:{slug}:{name}]]"


class AssistantService:
    """Service for the AI-powered chat assistant."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.smart_query_service = SmartQueryService(db)
        self._facet_types_cache = None

    async def _get_facet_types(self) -> List[FacetType]:
        """Get all active facet types (cached for session)."""
        if self._facet_types_cache is None:
            result = await self.db.execute(
                select(FacetType).where(FacetType.is_active == True).order_by(FacetType.display_order)
            )
            self._facet_types_cache = result.scalars().all()
        return self._facet_types_cache

    async def _get_facet_type_by_slug(self, slug: str) -> Optional[FacetType]:
        """Get a facet type by slug."""
        facet_types = await self._get_facet_types()
        for ft in facet_types:
            if ft.slug == slug:
                return ft
        return None

    async def process_message(
        self,
        message: str,
        context: AssistantContext,
        conversation_history: List[ConversationMessage],
        mode: str = "read",
        language: str = "de"
    ) -> AssistantChatResponse:
        """Process a user message and return an appropriate response."""
        # Initialize translator for this request
        self.tr = Translator(language)

        try:
            # Check for slash commands first
            if message.startswith("/"):
                return await self._handle_slash_command(message, context)

            # Classify intent
            intent, intent_data = await self._classify_intent(message, context)
            logger.info("intent_classified", intent=intent, data=intent_data)

            # Handle based on intent
            response_data: AssistantResponseData
            suggested_actions: List[SuggestedAction] = []

            if intent == IntentType.QUERY:
                response_data, suggested_actions = await self._handle_query(
                    message, context, intent_data
                )
            elif intent == IntentType.CONTEXT_QUERY:
                response_data, suggested_actions = await self._handle_context_query(
                    message, context, intent_data
                )
            elif intent == IntentType.INLINE_EDIT:
                if mode == "read":
                    # In read mode, suggest switching to write mode
                    response_data = ErrorResponseData(
                        message=self.tr.t("write_mode_required"),
                        error_code="write_mode_required"
                    )
                else:
                    response_data = await self._handle_inline_edit(
                        message, context, intent_data
                    )
            elif intent == IntentType.COMPLEX_WRITE:
                response_data = self._suggest_smart_query_redirect(message, intent_data)
            elif intent == IntentType.NAVIGATION:
                response_data = await self._handle_navigation(intent_data)
            elif intent == IntentType.SUMMARIZE:
                response_data, suggested_actions = await self._handle_summarize(context)
            elif intent == IntentType.HELP:
                response_data = self._generate_help(context, intent_data)
            elif intent == IntentType.BATCH_ACTION:
                if mode == "read":
                    # In read mode, suggest switching to write mode
                    response_data = ErrorResponseData(
                        message=self.tr.t("write_mode_required"),
                        error_code="write_mode_required"
                    )
                else:
                    response_data, suggested_actions = await self._handle_batch_action_intent(
                        message, context, intent_data
                    )
            elif intent == IntentType.FACET_MANAGEMENT:
                if mode == "read":
                    # In read mode, only allow listing facet types
                    facet_action = intent_data.get("facet_action", "list_facet_types")
                    if facet_action in ["create_facet_type", "assign_facet_type"]:
                        response_data = ErrorResponseData(
                            message=self.tr.t("write_mode_required"),
                            error_code="write_mode_required"
                        )
                    else:
                        response_data, suggested_actions = await self._handle_facet_management(
                            message, context, intent_data
                        )
                else:
                    response_data, suggested_actions = await self._handle_facet_management(
                        message, context, intent_data
                    )
            else:
                response_data = ErrorResponseData(
                    message=self.tr.t("unknown_intent"),
                    error_code="unknown_intent"
                )

            return AssistantChatResponse(
                success=True,
                response=response_data,
                suggested_actions=suggested_actions
            )

        except Exception as e:
            logger.error("assistant_error", error=str(e))
            return AssistantChatResponse(
                success=False,
                response=ErrorResponseData(
                    message=self.tr.t("error_occurred", error=str(e)),
                    error_code="internal_error"
                )
            )

    async def _classify_intent(
        self,
        message: str,
        context: AssistantContext
    ) -> Tuple[IntentType, Dict[str, Any]]:
        """Classify the user's intent using LLM."""
        if not client:
            # Fallback classification without LLM
            return self._fallback_intent_classification(message, context)

        prompt = INTENT_CLASSIFICATION_PROMPT.format(
            current_route=context.current_route,
            entity_type=context.current_entity_type or "keine",
            entity_name=context.current_entity_name or "keine",
            view_mode=context.view_mode.value,
            message=message
        )

        try:
            response = client.chat.completions.create(
                model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": "Du bist ein Intent-Classifier. Antworte nur mit JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            intent_str = result.get("intent", "QUERY").upper()
            intent = IntentType(intent_str.lower())
            extracted_data = result.get("extracted_data", {})

            return intent, extracted_data

        except Exception as e:
            logger.error("intent_classification_error", error=str(e))
            return self._fallback_intent_classification(message, context)

    def _fallback_intent_classification(
        self,
        message: str,
        context: AssistantContext
    ) -> Tuple[IntentType, Dict[str, Any]]:
        """Fallback intent classification without LLM."""
        message_lower = message.lower()

        # Help patterns
        if any(w in message_lower for w in ["hilfe", "help", "wie ", "was kann", "anleitung"]):
            return IntentType.HELP, {}

        # Navigation patterns
        if any(w in message_lower for w in ["geh zu", "zeig mir ", "navigier", "öffne"]):
            # Try to extract entity name
            for pattern in [r"geh zu (.+)", r"zeig mir (.+)", r"öffne (.+)"]:
                match = re.search(pattern, message_lower)
                if match:
                    return IntentType.NAVIGATION, {"target_entity": match.group(1).strip()}
            return IntentType.NAVIGATION, {}

        # Edit patterns
        if any(w in message_lower for w in ["ändere", "setze", "aktualisiere", "update"]):
            return IntentType.INLINE_EDIT, {}

        # Complex write patterns
        if any(w in message_lower for w in ["erstelle", "create", "neu anlegen", "hinzufügen"]):
            return IntentType.COMPLEX_WRITE, {}

        # Summary patterns
        if any(w in message_lower for w in ["zusammenfassung", "summary", "überblick", "fasse zusammen"]):
            return IntentType.SUMMARIZE, {}

        # Context query (if on entity detail page)
        if context.current_entity_id and any(w in message_lower for w in ["hier", "diese", "dieser", "details", "mehr"]):
            return IntentType.CONTEXT_QUERY, {}

        # Default to query
        return IntentType.QUERY, {"query_text": message}

    async def _handle_slash_command(
        self,
        message: str,
        context: AssistantContext
    ) -> AssistantChatResponse:
        """Handle slash commands."""
        parts = message.split(maxsplit=1)
        command = parts[0][1:].lower()  # Remove leading /
        args = parts[1] if len(parts) > 1 else ""

        if command == "help":
            return AssistantChatResponse(
                success=True,
                response=self._generate_help(context, {"help_topic": args})
            )

        elif command == "search":
            if not args:
                return AssistantChatResponse(
                    success=True,
                    response=ErrorResponseData(
                        message="Bitte gib einen Suchbegriff an: /search <suchbegriff>"
                    )
                )
            response_data, suggested = await self._handle_query(
                args, context, {"query_text": args}
            )
            return AssistantChatResponse(
                success=True,
                response=response_data,
                suggested_actions=suggested
            )

        elif command == "create":
            return AssistantChatResponse(
                success=True,
                response=RedirectResponse(
                    message=f"Für die Erstellung nutze bitte die Smart Query Seite im Schreib-Modus.",
                    prefilled_query=args,
                    write_mode=True
                )
            )

        elif command == "summary":
            response_data, suggested = await self._handle_summarize(context)
            return AssistantChatResponse(
                success=True,
                response=response_data,
                suggested_actions=suggested
            )

        elif command == "navigate":
            return AssistantChatResponse(
                success=True,
                response=await self._handle_navigation({"target_entity": args})
            )

        else:
            return AssistantChatResponse(
                success=True,
                response=ErrorResponseData(
                    message=f"Unbekannter Befehl: /{command}. Nutze /help für verfügbare Befehle."
                )
            )

    async def _handle_query(
        self,
        message: str,
        context: AssistantContext,
        intent_data: Dict[str, Any]
    ) -> Tuple[QueryResponse, List[SuggestedAction]]:
        """Handle a query intent using SmartQueryService."""
        query_text = intent_data.get("query_text", message)

        try:
            # Use SmartQueryService for the query
            result = await self.smart_query_service.smart_query(query_text, allow_write=False)

            items = result.get("items", [])
            total = result.get("total", len(items))

            # Generate human-readable message with entity links
            if total == 0:
                msg = self.tr.t("no_results")
            elif total == 1:
                item = items[0]
                name = item.get("entity_name", item.get("name", "Entry"))
                entity_type = item.get("entity_type")
                entity_slug = item.get("entity_slug", item.get("slug"))
                if entity_type and entity_slug:
                    entity_link = format_entity_link(entity_type, entity_slug, name)
                    msg = self.tr.t("found_one", entity_link=entity_link)
                else:
                    msg = self.tr.t("found_one_plain", name=name)
            else:
                # Include first few results as entity links
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
                        msg = self.tr.t("found_many", total=total, links_text=links_text, remaining=remaining)
                    else:
                        msg = self.tr.t("found_many_no_remaining", total=total, links_text=links_text)
                else:
                    msg = self.tr.t("found_count", total=total)

            # Suggested follow-ups
            suggested = []
            if total > 0:
                suggested.append(SuggestedAction(
                    label=self.tr.t("show_details"),
                    action="query",
                    value="Show more details" if self.tr.language == "en" else "Zeig mir mehr Details"
                ))
            suggested.append(SuggestedAction(
                label=self.tr.t("new_search"),
                action="query",
                value="/search "
            ))

            return QueryResponse(
                message=msg,
                data=QueryResultData(
                    items=items[:20],  # Limit for chat display
                    total=total,
                    grouping=result.get("grouping"),
                    query_interpretation=result.get("query_interpretation")
                ),
                follow_up_suggestions=[
                    self.tr.t("show_more_details"),
                    self.tr.t("filter_by_criteria")
                ] if total > 0 else []
            ), suggested

        except Exception as e:
            logger.error("query_error", error=str(e))
            return QueryResponse(
                message=self.tr.t("query_error", error=str(e)),
                data=QueryResultData()
            ), []

    async def _handle_context_query(
        self,
        message: str,
        context: AssistantContext,
        intent_data: Dict[str, Any]
    ) -> Tuple[QueryResponse, List[SuggestedAction]]:
        """Handle a query about the current context/entity."""
        if not context.current_entity_id:
            return QueryResponse(
                message="Du befindest dich aktuell nicht auf einer Entity-Detailseite.",
                data=QueryResultData()
            ), []

        try:
            # Validate and fetch entity with facets
            try:
                entity_id = UUID(context.current_entity_id)
            except (ValueError, TypeError, AttributeError):
                return QueryResponse(
                    message="Ungueltige Entity-ID.",
                    data=QueryResultData()
                ), []

            entity_result = await self.db.execute(
                select(Entity)
                .options(selectinload(Entity.entity_type))
                .where(Entity.id == entity_id)
            )
            entity = entity_result.scalar_one_or_none()

            if not entity:
                return QueryResponse(
                    message="Entity nicht gefunden.",
                    data=QueryResultData()
                ), []

            # Fetch facets
            facets_result = await self.db.execute(
                select(FacetValue)
                .options(selectinload(FacetValue.facet_type))
                .where(FacetValue.entity_id == entity_id)
                .order_by(FacetValue.created_at.desc())
                .limit(20)
            )
            facets = facets_result.scalars().all()

            # Format response
            facet_summary = {}
            for fv in facets:
                ft_name = fv.facet_type.name if fv.facet_type else "Unbekannt"
                if ft_name not in facet_summary:
                    facet_summary[ft_name] = []
                facet_summary[ft_name].append(fv.text_representation or str(fv.value)[:100])

            # Format entity name as clickable link
            type_slug = entity.entity_type.slug if entity.entity_type else None
            type_name = entity.entity_type.name if entity.entity_type else 'Unbekannt'
            if type_slug and entity.slug:
                entity_link = format_entity_link(type_slug, entity.slug, entity.name)
                msg = f"**{entity_link}** ({type_name})\n\n"
            else:
                msg = f"**{entity.name}** ({type_name})\n\n"

            for ft_name, values in facet_summary.items():
                msg += f"**{ft_name}:** {len(values)} Einträge\n"

            items = [{
                "entity_id": str(entity.id),
                "entity_name": entity.name,
                "entity_type": entity.entity_type.slug if entity.entity_type else None,
                "facets": facet_summary
            }]

            # Dynamic suggestions based on available facet types
            facet_types = await self._get_facet_types()
            suggested = []
            for ft in facet_types[:3]:  # First 3 facet types as suggestions
                suggested.append(SuggestedAction(
                    label=ft.name,
                    action="query",
                    value=f"Zeige {ft.name_plural or ft.name} von {entity.name}"
                ))
            suggested.append(SuggestedAction(label="Zusammenfassung", action="query", value="/summary"))

            return QueryResponse(
                message=msg,
                data=QueryResultData(items=items, total=1)
            ), suggested

        except Exception as e:
            logger.error("context_query_error", error=str(e))
            return QueryResponse(
                message=f"Fehler: {str(e)}",
                data=QueryResultData()
            ), []

    async def _handle_inline_edit(
        self,
        message: str,
        context: AssistantContext,
        intent_data: Dict[str, Any]
    ) -> ActionPreviewResponse:
        """Handle inline edit requests - return preview for confirmation."""
        if not context.current_entity_id:
            return ActionPreviewResponse(
                message="Keine Entity ausgewählt. Navigiere zuerst zu einer Entity-Detailseite.",
                action=ActionDetails(type="none"),
                requires_confirmation=False
            )

        field = intent_data.get("field_to_edit", "name")
        new_value = intent_data.get("new_value", "")

        if not new_value:
            return ActionPreviewResponse(
                message="Ich konnte den neuen Wert nicht erkennen. Bitte formuliere um, z.B. 'Ändere den Namen zu Neuer Name'",
                action=ActionDetails(type="none"),
                requires_confirmation=False
            )

        # Get current entity
        try:
            # Validate UUID format
            try:
                entity_id = UUID(context.current_entity_id)
            except (ValueError, TypeError, AttributeError) as uuid_err:
                logger.warning("invalid_entity_id", entity_id=context.current_entity_id, error=str(uuid_err))
                return ActionPreviewResponse(
                    message="Ungueltige Entity-ID. Bitte navigiere zuerst zu einer Entity-Detailseite.",
                    action=ActionDetails(type="none"),
                    requires_confirmation=False
                )

            result = await self.db.execute(
                select(Entity).where(Entity.id == entity_id)
            )
            entity = result.scalar_one_or_none()

            if not entity:
                return ActionPreviewResponse(
                    message="Entity nicht gefunden.",
                    action=ActionDetails(type="none"),
                    requires_confirmation=False
                )

            # Determine the field and current value
            current_value = getattr(entity, field, None)
            if current_value is None and field == "name":
                current_value = entity.name

            return ActionPreviewResponse(
                message=f"Soll ich '{field}' von '{current_value}' zu '{new_value}' ändern?",
                action=ActionDetails(
                    type="update_entity",
                    target_id=str(entity.id),
                    target_name=entity.name,
                    target_type=context.current_entity_type,
                    changes={
                        field: ActionChange(
                            field=field,
                            from_value=current_value,
                            to_value=new_value
                        )
                    }
                ),
                requires_confirmation=True
            )

        except Exception as e:
            logger.error("inline_edit_error", error=str(e))
            return ActionPreviewResponse(
                message=f"Fehler: {str(e)}",
                action=ActionDetails(type="none"),
                requires_confirmation=False
            )

    def _suggest_smart_query_redirect(
        self,
        message: str,
        intent_data: Dict[str, Any]
    ) -> RedirectResponse:
        """Suggest redirecting to Smart Query for complex writes."""
        return RedirectResponse(
            message="Für diese komplexe Operation nutze bitte die Smart Query Seite. Ich leite dich weiter.",
            prefilled_query=message,
            write_mode=True
        )

    async def _handle_navigation(
        self,
        intent_data: Dict[str, Any]
    ) -> NavigationResponse:
        """Handle navigation requests."""
        target_name = intent_data.get("target_entity", "")

        if not target_name:
            return NavigationResponse(
                message="Wohin möchtest du navigieren? Nenne mir einen Entity-Namen.",
                target=NavigationTarget(route="/entities")
            )

        # Search for entity
        try:
            result = await self.db.execute(
                select(Entity)
                .options(selectinload(Entity.entity_type))
                .where(
                    or_(
                        Entity.name.ilike(f"%{target_name}%"),
                        Entity.slug.ilike(f"%{target_name}%")
                    )
                )
                .limit(5)
            )
            entities = result.scalars().all()

            if not entities:
                return NavigationResponse(
                    message=f"Keine Entity mit dem Namen '{target_name}' gefunden.",
                    target=NavigationTarget(route=f"/entities?search={target_name}")
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
                    entity_name=entity.name
                )
            )

        except Exception as e:
            logger.error("navigation_error", error=str(e))
            return NavigationResponse(
                message=f"Fehler bei der Suche: {str(e)}",
                target=NavigationTarget(route="/entities")
            )

    async def _handle_summarize(
        self,
        context: AssistantContext
    ) -> Tuple[QueryResponse, List[SuggestedAction]]:
        """Generate a summary of the current context."""
        if not context.current_entity_id:
            # General app summary
            entity_count = await self.db.scalar(select(func.count(Entity.id)))
            facet_count = await self.db.scalar(select(func.count(FacetValue.id)))

            msg = f"**App-Übersicht:**\n- {entity_count or 0} Entities\n- {facet_count or 0} Facet-Werte"

            return QueryResponse(
                message=msg,
                data=QueryResultData(items=[], total=0),
                follow_up_suggestions=["Zeige alle Municipalities", "Zeige Pain Points"]
            ), []

        # Entity summary
        try:
            # Validate UUID
            try:
                entity_id = UUID(context.current_entity_id)
            except (ValueError, TypeError, AttributeError):
                return QueryResponse(
                    message="Ungueltige Entity-ID.",
                    data=QueryResultData()
                ), []

            # Get entity with related data
            entity_result = await self.db.execute(
                select(Entity)
                .options(selectinload(Entity.entity_type))
                .where(Entity.id == entity_id)
            )
            entity = entity_result.scalar_one_or_none()

            if not entity:
                return QueryResponse(
                    message="Entity nicht gefunden.",
                    data=QueryResultData()
                ), []

            # Count facets by type
            facet_counts = await self.db.execute(
                select(FacetType.name, func.count(FacetValue.id))
                .join(FacetValue, FacetType.id == FacetValue.facet_type_id)
                .where(FacetValue.entity_id == entity_id)
                .group_by(FacetType.name)
            )
            counts = dict(facet_counts.all())

            # Count relations
            relation_count = await self.db.scalar(
                select(func.count(EntityRelation.id))
                .where(
                    or_(
                        EntityRelation.source_entity_id == entity_id,
                        EntityRelation.target_entity_id == entity_id
                    )
                )
            )

            msg = f"**Zusammenfassung: {entity.name}**\n\n"
            msg += f"Typ: {entity.entity_type.name if entity.entity_type else 'Unbekannt'}\n\n"

            if counts:
                msg += "**Facets:**\n"
                for ft_name, count in counts.items():
                    msg += f"- {ft_name}: {count}\n"

            msg += f"\n**Relationen:** {relation_count or 0}"

            # Dynamic suggestions based on available facet types
            facet_types = await self._get_facet_types()
            suggested = []
            for ft in facet_types[:2]:  # First 2 facet types as suggestions
                suggested.append(SuggestedAction(
                    label=ft.name,
                    action="query",
                    value=f"{ft.name_plural or ft.name} von {entity.name}"
                ))
            suggested.append(SuggestedAction(label="Relationen", action="query", value=f"Relationen von {entity.name}"))

            return QueryResponse(
                message=msg,
                data=QueryResultData(
                    items=[{
                        "entity_id": str(entity.id),
                        "entity_name": entity.name,
                        "facet_counts": counts,
                        "relation_count": relation_count
                    }],
                    total=1
                )
            ), suggested

        except Exception as e:
            logger.error("summarize_error", error=str(e))
            return QueryResponse(
                message=f"Fehler: {str(e)}",
                data=QueryResultData()
            ), []

    def _generate_help(
        self,
        context: AssistantContext,
        intent_data: Dict[str, Any] = None
    ) -> HelpResponse:
        """Generate contextual help."""
        help_topic = (intent_data or {}).get("help_topic", "")

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

        return HelpResponse(
            message=msg,
            help_topics=help_topics,
            suggested_commands=suggested_commands
        )

    async def _handle_facet_management(
        self,
        message: str,
        context: AssistantContext,
        intent_data: Dict[str, Any]
    ) -> Tuple[FacetManagementResponse, List[SuggestedAction]]:
        """Handle facet type management requests."""
        facet_action = intent_data.get("facet_action", "list_facet_types")
        facet_name = intent_data.get("facet_name", "")
        facet_description = intent_data.get("facet_description", "")
        target_entity_types = intent_data.get("target_entity_types", [])

        # Convert string to list if needed
        if isinstance(target_entity_types, str):
            target_entity_types = [t.strip() for t in target_entity_types.split(",") if t.strip()]

        try:
            facet_types = await self._get_facet_types()

            if facet_action == "list_facet_types":
                # List all available facet types
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
                    icon = ft.get("icon", "mdi-tag")
                    msg += f"- **{ft['name']}** (`{ft['slug']}`): {ft.get('description', 'Keine Beschreibung')[:50]}\n"

                return FacetManagementResponse(
                    message=msg,
                    action=FacetManagementAction.LIST_FACET_TYPES,
                    existing_facet_types=facet_list,
                    requires_confirmation=False
                ), [
                    SuggestedAction(label="Neuen Facet-Typ erstellen", action="query", value="Erstelle einen neuen Facet-Typ"),
                    SuggestedAction(label="Facet zuweisen", action="query", value="Weise einen Facet-Typ zu"),
                ]

            elif facet_action == "create_facet_type":
                # Preview facet type creation
                if not facet_name:
                    return FacetManagementResponse(
                        message="Bitte gib einen Namen für den neuen Facet-Typ an.",
                        action=FacetManagementAction.CREATE_FACET_TYPE,
                        requires_confirmation=False
                    ), []

                # Generate slug from name
                import re
                slug = re.sub(r'[^a-z0-9_]', '_', facet_name.lower())
                slug = re.sub(r'_+', '_', slug).strip('_')

                # Check if slug already exists
                existing = await self._get_facet_type_by_slug(slug)
                if existing:
                    return FacetManagementResponse(
                        message=f"Ein Facet-Typ mit dem Slug '{slug}' existiert bereits. Bitte wähle einen anderen Namen.",
                        action=FacetManagementAction.CREATE_FACET_TYPE,
                        requires_confirmation=False
                    ), []

                preview = FacetTypePreview(
                    name=facet_name,
                    name_plural=f"{facet_name}s" if not facet_name.endswith("s") else facet_name,
                    slug=slug,
                    description=facet_description or f"Automatisch erstellter Facet-Typ: {facet_name}",
                    applicable_entity_type_slugs=target_entity_types,
                    ai_extraction_enabled=True,
                    ai_extraction_prompt=f"Extrahiere Informationen zum Thema '{facet_name}' aus dem Dokument."
                )

                return FacetManagementResponse(
                    message=f"Soll ich den Facet-Typ **{facet_name}** erstellen?\n\n"
                            f"- Slug: `{slug}`\n"
                            f"- Beschreibung: {preview.description}\n"
                            f"- Für Entity-Typen: {', '.join(target_entity_types) if target_entity_types else 'Alle'}",
                    action=FacetManagementAction.CREATE_FACET_TYPE,
                    facet_type_preview=preview,
                    target_entity_types=target_entity_types,
                    requires_confirmation=True
                ), []

            elif facet_action == "assign_facet_type":
                # Assign facet type to entity types
                if not target_entity_types:
                    # Get available entity types
                    et_result = await self.db.execute(
                        select(EntityType).where(EntityType.is_active == True)
                    )
                    entity_types = et_result.scalars().all()

                    msg = "Welchem Entity-Typ soll der Facet-Typ zugewiesen werden?\n\n"
                    for et in entity_types:
                        msg += f"- `{et.slug}`: {et.name}\n"

                    return FacetManagementResponse(
                        message=msg,
                        action=FacetManagementAction.ASSIGN_FACET_TYPE,
                        requires_confirmation=False
                    ), []

                return FacetManagementResponse(
                    message=f"Facet-Typ würde den Entity-Typen {', '.join(target_entity_types)} zugewiesen.",
                    action=FacetManagementAction.ASSIGN_FACET_TYPE,
                    target_entity_types=target_entity_types,
                    requires_confirmation=True
                ), []

            elif facet_action == "suggest_facet_types":
                # Use LLM to suggest appropriate facet types based on context
                current_entity_type = context.current_entity_type
                existing_slugs = [ft.slug for ft in facet_types]

                suggestions = await self._suggest_facet_types_with_llm(
                    current_entity_type, existing_slugs, message
                )

                if suggestions:
                    msg = "**Vorgeschlagene Facet-Typen:**\n\n"
                    for s in suggestions:
                        msg += f"- **{s['name']}**: {s['description']}\n"

                    return FacetManagementResponse(
                        message=msg,
                        action=FacetManagementAction.SUGGEST_FACET_TYPES,
                        existing_facet_types=suggestions,
                        auto_suggested=True,
                        requires_confirmation=False
                    ), [
                        SuggestedAction(
                            label=f"'{s['name']}' erstellen",
                            action="query",
                            value=f"Erstelle Facet-Typ {s['name']}"
                        )
                        for s in suggestions[:3]
                    ]

                return FacetManagementResponse(
                    message="Keine neuen Facet-Typen vorgeschlagen. Die existierenden Typen scheinen bereits gut abzudecken.",
                    action=FacetManagementAction.SUGGEST_FACET_TYPES,
                    requires_confirmation=False
                ), []

            else:
                return FacetManagementResponse(
                    message="Unbekannte Facet-Management Aktion.",
                    action=FacetManagementAction.LIST_FACET_TYPES,
                    requires_confirmation=False
                ), []

        except Exception as e:
            logger.error("facet_management_error", error=str(e))
            return FacetManagementResponse(
                message=f"Fehler bei der Facet-Verwaltung: {str(e)}",
                action=FacetManagementAction.LIST_FACET_TYPES,
                requires_confirmation=False
            ), []

    async def _suggest_facet_types_with_llm(
        self,
        entity_type: Optional[str],
        existing_slugs: List[str],
        user_message: str
    ) -> List[Dict[str, str]]:
        """Use LLM to suggest new facet types based on context."""
        if not client:
            # Fallback suggestions without LLM
            return []

        prompt = f"""Basierend auf dem Kontext, schlage neue Facet-Typen vor, die noch nicht existieren.

Entity-Typ: {entity_type or 'Allgemein'}
Existierende Facet-Typen: {', '.join(existing_slugs)}
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
            response = client.chat.completions.create(
                model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": "Du bist ein Datenmodellierungs-Experte. Antworte nur mit JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return result.get("suggestions", [])

        except Exception as e:
            logger.error("facet_suggestion_error", error=str(e))
            return []

    async def execute_action(
        self,
        action: ActionDetails,
        context: AssistantContext
    ) -> Dict[str, Any]:
        """Execute a confirmed action."""
        if action.type == "update_entity":
            try:
                entity_id = UUID(action.target_id)
                result = await self.db.execute(
                    select(Entity).where(Entity.id == entity_id)
                )
                entity = result.scalar_one_or_none()

                if not entity:
                    return {"success": False, "message": "Entity nicht gefunden"}

                # Apply changes
                for field, change in action.changes.items():
                    if hasattr(entity, field):
                        setattr(entity, field, change.to_value)

                await self.db.commit()

                return {
                    "success": True,
                    "message": f"'{entity.name}' wurde aktualisiert.",
                    "affected_entity_id": str(entity.id),
                    "affected_entity_name": entity.name,
                    "refresh_required": True
                }

            except Exception as e:
                await self.db.rollback()
                logger.error("execute_action_error", error=str(e))
                return {"success": False, "message": f"Fehler: {str(e)}"}

        return {"success": False, "message": f"Unbekannte Aktion: {action.type}"}

    async def execute_batch_action(
        self,
        action_type: str,
        target_filter: Dict[str, Any],
        action_data: Dict[str, Any],
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Execute a batch action on multiple entities."""
        from app.schemas.assistant import BatchActionPreview

        try:
            # Build the query based on filters
            query = select(Entity)

            # Apply entity type filter
            if "entity_type" in target_filter:
                entity_type_slug = target_filter["entity_type"]
                type_result = await self.db.execute(
                    select(EntityType).where(EntityType.slug == entity_type_slug)
                )
                entity_type = type_result.scalar_one_or_none()
                if entity_type:
                    query = query.where(Entity.type_id == entity_type.id)

            # Apply location filter
            if "location" in target_filter:
                loc_filter = target_filter["location"]
                if isinstance(loc_filter, dict):
                    # Handle nested location filters
                    for key, value in loc_filter.items():
                        if key == "admin_level_1":
                            # Filter by state/region
                            query = query.where(
                                Entity.location["admin_level_1"].astext == value
                            )

            # Execute query to get affected entities
            result = await self.db.execute(query)
            entities = result.scalars().all()

            # Create preview (first 10)
            preview = [
                BatchActionPreview(
                    entity_id=str(e.id),
                    entity_name=e.name,
                    entity_type=e.type.slug if e.type else "unknown"
                )
                for e in entities[:10]
            ]

            affected_count = len(entities)

            if dry_run:
                # Return preview only
                action_desc = {
                    "add_facet": f"Facet '{action_data.get('facet_type')}' hinzufügen",
                    "update_field": f"Feld '{action_data.get('field')}' aktualisieren",
                    "add_relation": f"Relation '{action_data.get('relation_type')}' hinzufügen",
                    "remove_facet": f"Facet '{action_data.get('facet_type')}' entfernen",
                }.get(action_type, action_type)

                return {
                    "success": True,
                    "affected_count": affected_count,
                    "preview": [p.model_dump() for p in preview],
                    "batch_id": None,
                    "message": f"{action_desc} für {affected_count} Entities"
                }

            # Execute the batch action
            batch_id = str(uuid4())
            processed = 0
            errors = []

            for entity in entities:
                try:
                    if action_type == "add_facet":
                        # Add facet to entity
                        facet_type = action_data.get("facet_type")
                        facet_value = action_data.get("value")
                        if facet_type and facet_value:
                            new_facet = EntityFacet(
                                entity_id=entity.id,
                                facet_type=facet_type,
                                value=facet_value,
                                source="batch_action"
                            )
                            self.db.add(new_facet)

                    elif action_type == "update_field":
                        # Update entity field
                        field = action_data.get("field")
                        value = action_data.get("value")
                        if field and hasattr(entity, field):
                            setattr(entity, field, value)

                    processed += 1

                except Exception as e:
                    errors.append({
                        "entity_id": str(entity.id),
                        "entity_name": entity.name,
                        "error": str(e)
                    })

            await self.db.commit()

            return {
                "success": True,
                "affected_count": processed,
                "preview": [p.model_dump() for p in preview],
                "batch_id": batch_id,
                "message": f"{processed} von {affected_count} Entities aktualisiert"
            }

        except Exception as e:
            await self.db.rollback()
            logger.error("batch_action_error", error=str(e))
            return {
                "success": False,
                "affected_count": 0,
                "preview": [],
                "batch_id": None,
                "message": f"Fehler: {str(e)}"
            }

    async def _handle_batch_action_intent(
        self,
        message: str,
        context: AssistantContext,
        intent_data: Dict[str, Any]
    ) -> Tuple[AssistantResponseData, List[SuggestedAction]]:
        """Handle a batch action intent from chat."""
        extracted = intent_data.get("extracted_data", {})

        # Try to parse batch action parameters from the intent data
        action_type = extracted.get("batch_action_type", "add_facet")
        target_filter_raw = extracted.get("batch_target_filter", {})
        action_data_raw = extracted.get("batch_action_data", {})

        # Convert string representations to dicts if needed
        if isinstance(target_filter_raw, str):
            try:
                target_filter = json.loads(target_filter_raw)
            except:
                target_filter = {"entity_type": target_filter_raw}
        else:
            target_filter = target_filter_raw or {}

        if isinstance(action_data_raw, str):
            try:
                action_data = json.loads(action_data_raw)
            except:
                action_data = {"value": action_data_raw}
        else:
            action_data = action_data_raw or {}

        # If we don't have enough info, return an error asking for more details
        if not target_filter:
            return ErrorResponseData(
                message=self.tr.t(
                    "batch_missing_filter",
                    default="Bitte gib an, welche Entities bearbeitet werden sollen (z.B. 'alle Gemeinden in NRW')."
                ),
                error_code="missing_filter"
            ), []

        # Execute dry run to get preview
        try:
            result = await self.execute_batch_action(
                action_type=action_type,
                target_filter=target_filter,
                action_data=action_data,
                dry_run=True
            )

            if not result.get("success"):
                return ErrorResponseData(
                    message=result.get("message", "Fehler bei der Batch-Vorschau"),
                    error_code="batch_preview_error"
                ), []

            affected_count = result.get("affected_count", 0)
            preview = result.get("preview", [])

            if affected_count == 0:
                return QueryResponse(
                    message=self.tr.t(
                        "batch_no_matches",
                        default="Keine passenden Entities für die Batch-Operation gefunden."
                    ),
                    data=QueryResultData(items=[], total=0)
                ), []

            # Return batch preview response
            return BatchActionChatResponse(
                message=self.tr.t(
                    "batch_preview_message",
                    count=affected_count,
                    default=f"{affected_count} Entities würden bearbeitet werden."
                ),
                affected_count=affected_count,
                preview=[
                    BatchActionPreview(
                        entity_id=p.get("entity_id", ""),
                        entity_name=p.get("entity_name", ""),
                        entity_type=p.get("entity_type", "")
                    )
                    for p in preview
                ],
                action_type=action_type,
                action_data=action_data,
                target_filter=target_filter,
                requires_confirmation=True
            ), []

        except Exception as e:
            logger.error("batch_intent_error", error=str(e))
            return ErrorResponseData(
                message=f"Fehler bei der Batch-Verarbeitung: {str(e)}",
                error_code="batch_error"
            ), []

    async def process_message_stream(
        self,
        message: str,
        context: AssistantContext,
        conversation_history: List[ConversationMessage],
        mode: str = "read",
        language: str = "de"
    ):
        """Process a user message and yield streaming response chunks."""
        # Initialize translator for this request
        self.tr = Translator(language)

        try:
            # Send initial status
            yield {"type": "status", "message": self.tr.t("streaming_processing")}

            # Check for slash commands first
            if message.startswith("/"):
                response = await self._handle_slash_command(message, context)
                yield {
                    "type": "complete",
                    "data": response.model_dump()
                }
                return

            # Classify intent
            yield {"type": "status", "message": self.tr.t("streaming_analyzing")}
            intent, intent_data = await self._classify_intent(message, context)
            yield {"type": "intent", "intent": intent.value}
            logger.info("intent_classified", intent=intent, data=intent_data)

            # Handle based on intent with streaming
            if intent == IntentType.QUERY:
                yield {"type": "status", "message": self.tr.t("streaming_searching")}
                async for chunk in self._handle_query_stream(message, context, intent_data):
                    yield chunk

            elif intent == IntentType.CONTEXT_QUERY:
                yield {"type": "status", "message": self.tr.t("streaming_searching")}
                response_data, suggested_actions = await self._handle_context_query(
                    message, context, intent_data
                )
                yield {
                    "type": "complete",
                    "data": {
                        "success": True,
                        "response": response_data.model_dump() if hasattr(response_data, 'model_dump') else response_data,
                        "suggested_actions": [s.model_dump() for s in suggested_actions]
                    }
                }

            elif intent == IntentType.INLINE_EDIT:
                if mode == "read":
                    yield {
                        "type": "complete",
                        "data": {
                            "success": True,
                            "response": {
                                "type": "error",
                                "message": self.tr.t("write_mode_required"),
                                "error_code": "write_mode_required"
                            }
                        }
                    }
                else:
                    response_data = await self._handle_inline_edit(message, context, intent_data)
                    yield {
                        "type": "complete",
                        "data": {
                            "success": True,
                            "response": response_data.model_dump()
                        }
                    }

            elif intent == IntentType.COMPLEX_WRITE:
                response_data = self._suggest_smart_query_redirect(message, intent_data)
                yield {
                    "type": "complete",
                    "data": {
                        "success": True,
                        "response": response_data.model_dump()
                    }
                }

            elif intent == IntentType.NAVIGATION:
                yield {"type": "status", "message": self.tr.t("streaming_searching")}
                response_data = await self._handle_navigation(intent_data)
                yield {
                    "type": "complete",
                    "data": {
                        "success": True,
                        "response": response_data.model_dump()
                    }
                }

            elif intent == IntentType.SUMMARIZE:
                yield {"type": "status", "message": self.tr.t("streaming_generating")}
                response_data, suggested_actions = await self._handle_summarize(context)
                yield {
                    "type": "complete",
                    "data": {
                        "success": True,
                        "response": response_data.model_dump(),
                        "suggested_actions": [s.model_dump() for s in suggested_actions]
                    }
                }

            elif intent == IntentType.HELP:
                response_data = self._generate_help(context, intent_data)
                yield {
                    "type": "complete",
                    "data": {
                        "success": True,
                        "response": response_data.model_dump()
                    }
                }

            else:
                yield {
                    "type": "complete",
                    "data": {
                        "success": True,
                        "response": {
                            "type": "error",
                            "message": self.tr.t("unknown_intent"),
                            "error_code": "unknown_intent"
                        }
                    }
                }

        except Exception as e:
            logger.error("assistant_stream_error", error=str(e))
            yield {
                "type": "error",
                "message": self.tr.t("error_occurred", error=str(e))
            }

    async def _handle_query_stream(
        self,
        message: str,
        context: AssistantContext,
        intent_data: Dict[str, Any]
    ):
        """Handle a query intent with streaming results."""
        query_text = intent_data.get("query_text", message)

        try:
            # Use SmartQueryService for the query
            result = await self.smart_query_service.smart_query(query_text, allow_write=False)

            items = result.get("items", [])
            total = result.get("total", len(items))

            # Stream items one by one (first 20)
            for i, item in enumerate(items[:20]):
                yield {
                    "type": "item",
                    "index": i,
                    "data": item
                }

            # Generate human-readable message with entity links
            if total == 0:
                msg = self.tr.t("no_results")
            elif total == 1:
                item = items[0]
                name = item.get("entity_name", item.get("name", "Entry"))
                entity_type = item.get("entity_type")
                entity_slug = item.get("entity_slug", item.get("slug"))
                if entity_type and entity_slug:
                    entity_link = format_entity_link(entity_type, entity_slug, name)
                    msg = self.tr.t("found_one", entity_link=entity_link)
                else:
                    msg = self.tr.t("found_one_plain", name=name)
            else:
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
                        msg = self.tr.t("found_many", total=total, links_text=links_text, remaining=remaining)
                    else:
                        msg = self.tr.t("found_many_no_remaining", total=total, links_text=links_text)
                else:
                    msg = self.tr.t("found_count", total=total)

            # Suggested follow-ups
            suggested = []
            if total > 0:
                suggested.append({
                    "label": self.tr.t("show_details"),
                    "action": "query",
                    "value": "Show more details" if self.tr.language == "en" else "Zeig mir mehr Details"
                })
            suggested.append({
                "label": self.tr.t("new_search"),
                "action": "query",
                "value": "/search "
            })

            # Final complete message
            yield {
                "type": "complete",
                "data": {
                    "success": True,
                    "response": {
                        "type": "query_result",
                        "message": msg,
                        "data": {
                            "items": items[:20],
                            "total": total,
                            "grouping": result.get("grouping"),
                            "query_interpretation": result.get("query_interpretation")
                        },
                        "follow_up_suggestions": [
                            self.tr.t("show_more_details"),
                            self.tr.t("filter_by_criteria")
                        ] if total > 0 else []
                    },
                    "suggested_actions": suggested
                }
            }

        except Exception as e:
            logger.error("query_stream_error", error=str(e))
            yield {
                "type": "error",
                "message": self.tr.t("query_error", error=str(e))
            }
