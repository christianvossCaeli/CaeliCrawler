"""Assistant Service - KI-gestützter Chat-Assistent für die App."""

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

import structlog
from openai import AzureOpenAI
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models import (
    Entity,
    EntityType,
    FacetType,
    FacetValue,
    RelationType,
    EntityRelation,
)
from app.models.pysis import PySisProcess
from app.utils.validation import AssistantConstants, validate_uuid
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
    ContextActionResponse,
    SLASH_COMMANDS,
)
from services.smart_query import SmartQueryService
from services.smart_query.write_executor import execute_batch_operation
from services.smart_query.geographic_utils import (
    find_all_geo_suggestions,
    resolve_geographic_alias,
    GERMAN_STATE_ALIASES,
)
from services.pysis_facet_service import PySisFacetService
from services.translations import Translator

logger = structlog.get_logger()

# Azure OpenAI client
client = None
if settings.azure_openai_api_key:
    client = AzureOpenAI(
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        azure_endpoint=settings.azure_openai_endpoint,
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
9. FACET_MANAGEMENT - Benutzer will Facet-Typen erstellen, zuweisen oder verwalten (z.B. "Erstelle einen neuen Facet-Typ", "Welche Facets gibt es für Gemeinden?")
10. CONTEXT_ACTION - Benutzer will Aktion auf aktueller Entity ausführen (z.B. "Analysiere PySis", "Reichere Facets an", "Zeig PySis-Status", "Starte Crawl für diese Gemeinde")
11. SOURCE_MANAGEMENT - Benutzer will Datenquellen verwalten, Tags abfragen oder Quellen suchen/importieren (z.B. "Welche Tags gibt es?", "Zeige Quellen mit Tag nrw", "Finde Datenquellen für Bundesliga")

## Context Actions (für Intent CONTEXT_ACTION):
- show_pysis_status: PySis-Status anzeigen
- analyze_pysis: PySis-Analyse VORSCHAU anzeigen (noch nicht ausführen)
- analyze_pysis_execute: PySis-Analyse AUSFÜHREN (bei Bestätigung wie "Ja, starte", "Ja, analysieren")
- enrich_facets: Facet-Anreicherung aus PySis VORSCHAU anzeigen (noch nicht ausführen)
- enrich_facets_execute: Facet-Anreicherung aus PySis AUSFÜHREN (bei Bestätigung)
  - Mit overwrite=true wenn "überschreiben" erwähnt wird
- analyze_entity_data: Datenbasierte Facet-Analyse starten (z.B. "Analysiere die Verknüpfungen", "Schreibe Pain Points basierend auf den Relationen", "Reichere aus Dokumenten an")
  - Analysiert Relationen, Dokumente, Extraktionen und PySis-Daten
  - context_action_data kann enthalten: source_types (Liste: pysis, relations, documents, extractions)
- start_crawl: Crawl starten
- create_facet: Facet-Wert zur aktuellen Entity hinzufügen (z.B. "Füge Pain Point hinzu", "Neues Positive Signal")
  - context_action_data sollte enthalten: facet_type (pain_point|positive_signal|contact|summary), description, optional: severity, type

## Source Management Actions (für Intent SOURCE_MANAGEMENT):
- list_tags: Alle verfügbaren Tags anzeigen (z.B. "Welche Tags gibt es?", "Zeig alle Tags")
- list_sources_by_tag: Quellen nach Tag filtern (z.B. "Quellen mit Tag nrw", "Zeige kommunale Datenquellen")
  - source_action_data sollte enthalten: tags (Liste), match_mode (all|any)
- suggest_tags: Tags für einen Kontext vorschlagen (z.B. "Welche Tags passen zu Gemeinden in Bayern?")
  - source_action_data sollte enthalten: context (z.B. "Gemeinden Bayern")
- discover_sources: KI-gesteuerte Quellensuche (z.B. "Finde Datenquellen für Bundesliga-Vereine", "Suche Webseiten von Universitäten")
  - source_action_data sollte enthalten: prompt (Suchbegriff), search_depth (quick|standard|deep)

## DataSource Tags (Referenz):
Tags kategorisieren Datenquellen für effiziente Filterung und Kategorie-Zuordnung:
- Bundesländer: nrw, bayern, baden-wuerttemberg, hessen, niedersachsen, schleswig-holstein, etc.
- Länder: de (Deutschland), at (Österreich), ch (Schweiz)
- Typen: kommunal, landkreis, landesebene, oparl, ratsinformation
- Themen: windkraft, solar, bauen, verkehr, umwelt

WICHTIG bei Bestätigungen:
- "Ja, starte die PySis-Analyse" → context_action: "analyze_pysis_execute"
- "Ja, starte die Facet-Anreicherung" → context_action: "enrich_facets_execute"
- "Ja, anreichern und bestehende überschreiben" → context_action: "enrich_facets_execute", context_action_data: {{"overwrite": true}}
- "Ja, analysiere die Daten" / "Ja, extrahiere Facets" → context_action: "analyze_entity_data"
- "Abbrechen" → intent: "CONTEXT_QUERY" (einfach ignorieren)

WICHTIG für Entity-Daten-Analyse:
- Prompts wie "schreibe Pain Points anhand der Verknüpfungen" → context_action: "analyze_entity_data", source_types: ["relations"]
- "analysiere die Dokumente für neue Facets" → context_action: "analyze_entity_data", source_types: ["documents", "extractions"]
- "reichere Facets aus allen Daten an" → context_action: "analyze_entity_data" (alle Quellen)

## Slash Commands:
- /help - Hilfe anzeigen
- /search <query> - Suchen
- /create <type> <details> - Erstellen (→ COMPLEX_WRITE)
- /summary - Zusammenfassung (→ SUMMARIZE)
- /navigate <entity> - Navigation

Analysiere die Nachricht und gib JSON zurück:
{{
  "intent": "QUERY|CONTEXT_QUERY|INLINE_EDIT|COMPLEX_WRITE|NAVIGATION|SUMMARIZE|HELP|BATCH_ACTION|FACET_MANAGEMENT|CONTEXT_ACTION|SOURCE_MANAGEMENT",
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
    "target_entity_types": "optional: Liste von Entity-Typ-Slugs für Zuweisung",
    "context_action": "optional: analyze_pysis|enrich_facets|show_pysis_status|start_crawl|update_entity|create_facet|analyze_entity_data",
    "context_action_data": "optional: zusätzliche Parameter für die Aktion (z.B. source_types für analyze_entity_data)",
    "source_action": "optional: list_tags|list_sources_by_tag|suggest_tags|discover_sources",
    "source_action_data": "optional: Parameter für Source-Aktionen (z.B. tags, match_mode, context, prompt, search_depth)"
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
                select(FacetType).where(FacetType.is_active.is_(True)).order_by(FacetType.display_order)
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
        language: str = "de",
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> AssistantChatResponse:
        """Process a user message and return an appropriate response.

        Args:
            message: The user's text message
            context: Current application context (route, entity, view mode)
            conversation_history: Previous messages in the conversation
            mode: 'read' or 'write' mode
            language: Response language ('de' or 'en')
            attachments: List of attachment dicts with 'content' (bytes),
                        'content_type', 'filename', 'size'
        """
        # Initialize translator for this request
        self.tr = Translator(language)

        # Handle image attachments with Vision API
        if attachments:
            image_attachments = [
                a for a in attachments
                if a.get("content_type", "").startswith("image/")
            ]
            if image_attachments:
                return await self._handle_image_analysis(
                    message, context, image_attachments, language
                )

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
            elif intent == IntentType.CONTEXT_ACTION:
                # Context actions require an entity context
                if not context.current_entity_id:
                    response_data = ErrorResponseData(
                        message="Bitte navigiere zuerst zu einer Entity-Detailseite.",
                        error_code="no_entity_context"
                    )
                else:
                    context_action = intent_data.get("extracted_data", {}).get("context_action", "show_pysis_status")
                    write_actions = ["analyze_pysis", "enrich_facets", "start_crawl", "create_facet", "analyze_entity_data"]
                    if context_action in write_actions and mode == "read":
                        response_data = ErrorResponseData(
                            message=self.tr.t("write_mode_required"),
                            error_code="write_mode_required"
                        )
                    else:
                        response_data, suggested_actions = await self._handle_context_action(
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
            # No LLM available - return error
            logger.error("Azure OpenAI client not configured")
            raise ValueError("KI-Service nicht verfügbar. Bitte Azure OpenAI konfigurieren.")

        prompt = INTENT_CLASSIFICATION_PROMPT.format(
            current_route=context.current_route,
            entity_type=context.current_entity_type or "keine",
            entity_name=context.current_entity_name or "keine",
            view_mode=context.view_mode.value,
            message=message
        )

        try:
            response = client.chat.completions.create(
                model=settings.azure_openai_deployment_name,
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
            raise ValueError(f"KI-Klassifizierung fehlgeschlagen: {str(e)}")

    async def _handle_image_analysis(
        self,
        message: str,
        context: AssistantContext,
        images: List[Dict[str, Any]],
        language: str = "de"
    ) -> AssistantChatResponse:
        """
        Analyze images using the Vision API.

        Args:
            message: User's message/question about the image
            context: Current application context
            images: List of image dicts with 'content' (bytes), 'content_type', 'filename'
            language: Response language
        """
        import base64

        if not client:
            return AssistantChatResponse(
                success=False,
                response=ErrorResponseData(
                    message="KI-Service nicht verfügbar. Bitte Azure OpenAI konfigurieren.",
                    error_code="ai_not_configured"
                )
            )

        try:
            # Build the content array with text and images
            content = []

            # Add the user's text message
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
                    img_base64 = img_content  # Already base64

                content_type = img.get("content_type", "image/jpeg")
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{content_type};base64,{img_base64}",
                        "detail": "high"
                    }
                })

            # Make the API call with vision capabilities
            response = client.chat.completions.create(
                model=settings.azure_openai_deployment_name,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": content}
                ],
                temperature=0.3,
                max_tokens=2000
            )

            if not response.choices:
                raise ValueError("Leere Antwort vom AI-Service")

            analysis_result = response.choices[0].message.content

            # Collect attachment IDs for potential saving
            attachment_ids = [img.get("id") for img in images if img.get("id")]

            # Build response with analysis
            response_data = QueryResponse(
                type="image_analysis",
                message=analysis_result,
                data=QueryResultData(
                    items=[{
                        "attachment_ids": attachment_ids,
                        "entity_id": context.current_entity_id,
                    }] if attachment_ids and context.current_entity_id else [],
                    total=len(images),
                    query_interpretation={
                        "query": user_prompt,
                        "attachment_ids": attachment_ids,
                    }
                )
            )

            # Suggest follow-up actions
            suggested_actions = []
            if context.current_entity_id:
                # Add "Save as attachment" action if there are images to save
                if attachment_ids:
                    import json
                    suggested_actions.append(SuggestedAction(
                        label="Als Attachment speichern",
                        action="save_attachment",
                        value=json.dumps({
                            "entity_id": context.current_entity_id,
                            "attachment_ids": attachment_ids,
                        })
                    ))

                suggested_actions.append(SuggestedAction(
                    label="Als Pain Point speichern",
                    action="create_facet",
                    value="pain_point"
                ))
                suggested_actions.append(SuggestedAction(
                    label="Als Notiz speichern",
                    action="create_facet",
                    value="summary"
                ))

            return AssistantChatResponse(
                success=True,
                response=response_data,
                suggested_actions=suggested_actions
            )

        except Exception as e:
            logger.error("image_analysis_error", error=str(e))
            return AssistantChatResponse(
                success=False,
                response=ErrorResponseData(
                    message=f"Bildanalyse fehlgeschlagen: {str(e)}",
                    error_code="image_analysis_error"
                )
            )

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

    async def _suggest_corrections(
        self,
        message: str,
        query_interpretation: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate intelligent suggestions when a query returns no results.

        Uses fuzzy matching for geographic terms, entity names, and facet types
        to suggest corrections for potential typos or misunderstandings.

        Args:
            message: The original user message
            query_interpretation: The parsed query interpretation if available

        Returns:
            List of suggestion objects with 'type', 'original', 'suggestion', 'corrected_query'
        """
        suggestions = []

        # 1. Check for geographic typos in the message
        words = re.findall(r'\b\w+\b', message.lower())
        for word in words:
            # Skip very short words and common stop words
            if len(word) < 3 or word in {'in', 'an', 'am', 'im', 'von', 'aus', 'bei', 'mit', 'und', 'oder'}:
                continue

            geo_suggestions = find_all_geo_suggestions(word, threshold=2, max_suggestions=1)
            if geo_suggestions:
                alias, canonical, distance = geo_suggestions[0]
                # Only suggest if it's a reasonable match (not exact)
                if distance > 0:
                    corrected_query = message.replace(word, canonical)
                    suggestions.append({
                        "type": "geographic",
                        "original": word,
                        "suggestion": canonical,
                        "corrected_query": corrected_query,
                        "message": f"Meinten Sie '{canonical}'?",
                    })

        # 2. Check for entity type suggestions
        entity_type_aliases = {
            "person": ["personen", "leute", "menschen", "kontakte", "ansprechpartner"],
            "municipality": ["gemeinden", "städte", "kommunen", "ortschaften", "landkreise", "kreis"],
            "organization": ["organisationen", "unternehmen", "firmen", "vereine", "verbände"],
            "event": ["events", "veranstaltungen", "termine", "messen", "konferenzen"],
        }

        for word in words:
            for entity_type, aliases in entity_type_aliases.items():
                for alias in aliases:
                    # Check for close matches to entity types
                    from services.smart_query.geographic_utils import levenshtein_distance
                    if levenshtein_distance(word, alias) <= 2 and word != alias:
                        suggestions.append({
                            "type": "entity_type",
                            "original": word,
                            "suggestion": alias,
                            "corrected_query": message.replace(word, alias),
                            "message": f"Meinten Sie '{alias}'?",
                        })
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
            for facet_type, aliases in facet_aliases.items():
                for alias in aliases:
                    from services.smart_query.geographic_utils import levenshtein_distance
                    if levenshtein_distance(word, alias.replace(" ", "")) <= 2 and word != alias:
                        suggestions.append({
                            "type": "facet_type",
                            "original": word,
                            "suggestion": alias,
                            "corrected_query": message.replace(word, alias),
                            "message": f"Meinten Sie '{alias}'?",
                        })
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

            # Check if there was an error in interpretation
            if result.get("error"):
                return QueryResponse(
                    message=result.get("message", self.tr.t("query_error", error="KI-Interpretation fehlgeschlagen")),
                    data=QueryResultData()
                ), []

            # Handle COUNT queries - they return a message instead of items
            if result.get("query_type") == "count":
                msg = result.get("message", f"Gefunden: {result.get('total', 0)}")
                return QueryResponse(
                    message=msg,
                    data=QueryResultData(
                        items=[],
                        total=result.get("total", 0),
                        query_interpretation=result.get("query_interpretation")
                    )
                ), [
                    SuggestedAction(
                        label=self.tr.t("show_list"),
                        action="query",
                        value=f"Liste alle {result.get('query_interpretation', {}).get('primary_entity_type', 'Einträge')}"
                    )
                ]

            items = result.get("items", [])
            total = result.get("total", len(items))

            # Generate human-readable message with entity links
            if total == 0:
                # Try to get suggestions for the empty result
                corrections = await self._suggest_corrections(
                    message,
                    result.get("query_interpretation")
                )

                if corrections:
                    # Build suggestion message
                    suggestion_parts = []
                    suggested_actions = []

                    for correction in corrections:
                        suggestion_parts.append(correction["message"])
                        suggested_actions.append(SuggestedAction(
                            label=correction["suggestion"],
                            action="query",
                            value=correction["corrected_query"]
                        ))

                    msg = self.tr.t("no_results") + "\n\n**Meinten Sie vielleicht:**\n" + "\n".join(f"- {s}" for s in suggestion_parts)

                    return QueryResponse(
                        message=msg,
                        data=QueryResultData(
                            items=[],
                            total=0,
                            query_interpretation=result.get("query_interpretation"),
                            suggestions=corrections
                        )
                    ), suggested_actions

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
        """Handle a query about the current context/entity using AI."""
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

            # Collect all available data
            entity_data = {
                "name": entity.name,
                "type": entity.entity_type.name if entity.entity_type else "Unbekannt",
                "core_attributes": entity.core_attributes or {},
                "location": {
                    "country": entity.country,
                    "admin_level_1": entity.admin_level_1,
                    "admin_level_2": entity.admin_level_2,
                }
            }

            # Fetch facets
            facets_result = await self.db.execute(
                select(FacetValue)
                .options(selectinload(FacetValue.facet_type))
                .where(FacetValue.entity_id == entity_id)
                .where(FacetValue.is_active.is_(True))
                .order_by(FacetValue.created_at.desc())
                .limit(30)
            )
            facets = facets_result.scalars().all()

            facet_data = {}
            for fv in facets:
                ft_name = fv.facet_type.name if fv.facet_type else "Unbekannt"
                if ft_name not in facet_data:
                    facet_data[ft_name] = []
                facet_data[ft_name].append(fv.text_representation or str(fv.value)[:200])
            entity_data["facets"] = facet_data

            # Fetch PySis data if available
            pysis_result = await self.db.execute(
                select(PySisProcess)
                .where(PySisProcess.entity_id == entity_id)
                .limit(1)
            )
            pysis_process = pysis_result.scalar_one_or_none()

            pysis_data = {}
            if pysis_process and pysis_process.fields:
                for field in pysis_process.fields:
                    if field.current_value:
                        pysis_data[field.internal_name] = field.current_value[:500]
            entity_data["pysis_fields"] = pysis_data

            # Use AI to generate intelligent response (ALWAYS use AI)
            ai_response = await self._generate_context_response_with_ai(
                user_question=message,
                entity_data=entity_data
            )

            # Build items for response data
            items = [{
                "entity_id": str(entity.id),
                "entity_name": entity.name,
                "entity_type": entity.entity_type.slug if entity.entity_type else None,
                "core_attributes": entity.core_attributes or {},
                "facets": facet_data,
                "pysis_fields": pysis_data,
                "location": entity_data["location"]
            }]

            # Dynamic suggestions based on available data
            suggested = []
            if pysis_data:
                suggested.append(SuggestedAction(
                    label="PySis Details",
                    action="query",
                    value="Zeige mir alle PySis-Daten im Detail"
                ))
            if facet_data:
                for ft_name in list(facet_data.keys())[:2]:
                    suggested.append(SuggestedAction(
                        label=ft_name,
                        action="query",
                        value=f"Erzähl mir mehr über die {ft_name}"
                    ))
            suggested.append(SuggestedAction(
                label="Zusammenfassung",
                action="query",
                value="Gib mir eine kurze Zusammenfassung"
            ))

            return QueryResponse(
                message=ai_response,
                data=QueryResultData(items=items, total=1)
            ), suggested

        except Exception as e:
            logger.error("context_query_error", error=str(e))
            return QueryResponse(
                message=f"Fehler: {str(e)}",
                data=QueryResultData()
            ), []

    async def _generate_context_response_with_ai(
        self,
        user_question: str,
        entity_data: Dict[str, Any]
    ) -> str:
        """Use AI to generate an intelligent response about the entity."""
        if not client:
            raise ValueError("KI-Service nicht verfügbar. Bitte Azure OpenAI konfigurieren.")

        # Prepare data summary for AI
        data_summary = json.dumps(entity_data, ensure_ascii=False, indent=2, default=str)

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

        response = client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[
                {"role": "system", "content": "Du bist ein hilfreicher Assistent für ein CRM/Entity-Management-System im Bereich Windenergie."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        return response.choices[0].message.content

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
                        select(EntityType).where(EntityType.is_active.is_(True))
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
        """Use LLM to suggest new facet types based on context.

        Raises:
            ValueError: If Azure OpenAI is not configured
            RuntimeError: If LLM suggestion fails
        """
        if not client:
            raise ValueError("KI-Service nicht erreichbar: Azure OpenAI ist nicht konfiguriert")

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
                model=settings.azure_openai_deployment_name,
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
            raise RuntimeError(f"KI-Service Fehler: Facet-Vorschläge konnten nicht generiert werden - {str(e)}")

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
        """Execute a batch action on multiple entities.

        Uses the unified Smart Query batch executor.
        """
        try:
            # Convert target_filter to Smart Query format
            sq_target_filter = {
                "entity_type": target_filter.get("entity_type"),
            }

            # Handle location filter
            if "location" in target_filter:
                loc_filter = target_filter["location"]
                if isinstance(loc_filter, dict) and "admin_level_1" in loc_filter:
                    sq_target_filter["location_filter"] = loc_filter["admin_level_1"]

            # Handle additional filters
            additional = {}
            for key, value in target_filter.items():
                if key not in ("entity_type", "location"):
                    additional[key] = value
            if additional:
                sq_target_filter["additional_filters"] = additional

            # Convert action_data to Smart Query format
            sq_action_data = {
                "facet_type": action_data.get("facet_type"),
                "facet_value": action_data.get("value"),
                "field_name": action_data.get("field"),
                "field_value": action_data.get("value"),
                "relation_type": action_data.get("relation_type"),
                "relation_target": action_data.get("target"),
            }

            # Build batch_data for Smart Query executor
            batch_data = {
                "action_type": action_type,
                "target_filter": sq_target_filter,
                "action_data": sq_action_data,
            }

            # Execute via unified Smart Query executor
            result = await execute_batch_operation(self.db, batch_data, dry_run=dry_run)

            # Add batch_id for non-dry-run operations
            if not dry_run and result.get("success"):
                result["batch_id"] = str(uuid4())
            else:
                result["batch_id"] = None

            # Ensure preview is properly formatted
            preview = result.get("preview", [])
            if preview and isinstance(preview[0], dict):
                # Already in dict format from Smart Query
                result["preview"] = preview

            if not dry_run:
                await self.db.commit()

            return result

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
            except (json.JSONDecodeError, ValueError, TypeError):
                target_filter = {"entity_type": target_filter_raw}
        else:
            target_filter = target_filter_raw or {}

        if isinstance(action_data_raw, str):
            try:
                action_data = json.loads(action_data_raw)
            except (json.JSONDecodeError, ValueError, TypeError):
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

    async def _handle_context_action(
        self,
        message: str,
        context: AssistantContext,
        intent_data: Dict[str, Any]
    ) -> Tuple[AssistantResponseData, List[SuggestedAction]]:
        """Handle context-aware action on current entity.

        Actions follow a two-step process:
        1. Preview: Shows what would happen and asks for confirmation
        2. Execute: Performs the action after confirmation

        Actions ending with '_execute' skip the preview and run immediately.
        """
        extracted = intent_data.get("extracted_data", {})
        action = extracted.get("context_action", "show_pysis_status")
        action_data = extracted.get("context_action_data", {})

        entity_id = context.current_entity_id
        entity_name = context.current_entity_name or "Entity"

        try:
            service = PySisFacetService(self.db)

            if action == "show_pysis_status":
                # Show PySis status for current entity
                status = await service.get_pysis_status(UUID(entity_id))

                if not status.get("has_pysis"):
                    return ContextActionResponse(
                        message=f"**{entity_name}** hat keine verknüpften PySis-Prozesse.",
                        action=action,
                        entity_id=entity_id,
                        entity_name=entity_name,
                        success=True
                    ), []

                # Format status message
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
                    action=action,
                    entity_id=entity_id,
                    entity_name=entity_name,
                    status=status,
                    success=True
                ), [
                    SuggestedAction(label="PySis analysieren", action="query", value="Analysiere PySis für Facets"),
                    SuggestedAction(label="Facets anreichern", action="query", value="Reichere Facets mit PySis an"),
                ]

            # ==========================================
            # ANALYZE PYSIS - Preview (Step 1)
            # ==========================================
            elif action == "analyze_pysis":
                preview = await service.get_operation_preview(UUID(entity_id), "analyze")

                if not preview.get("can_execute"):
                    return ContextActionResponse(
                        message=f"**Analyse nicht möglich:**\n{preview.get('message', 'Keine Daten verfügbar')}",
                        action=action,
                        entity_id=entity_id,
                        entity_name=entity_name,
                        preview=preview,
                        requires_confirmation=False,
                        success=False
                    ), []

                # Build detailed preview message
                msg = f"**PySis-Analyse für {entity_name}**\n\n"
                msg += f"📊 **Was wird analysiert:**\n"
                msg += f"- {preview.get('fields_with_values', 0)} PySis-Felder mit Werten\n"
                msg += f"- {preview.get('facet_types_count', 0)} Facet-Typen werden geprüft\n\n"

                facet_types = preview.get("facet_types", [])
                if facet_types:
                    msg += f"**Facet-Typen:**\n"
                    for ft in facet_types[:5]:
                        msg += f"- {ft.get('name')}\n"
                    if len(facet_types) > 5:
                        msg += f"- ... und {len(facet_types) - 5} weitere\n"

                msg += f"\n⚠️ **Möchtest du die Analyse starten?**"

                return ContextActionResponse(
                    message=msg,
                    action=action,
                    entity_id=entity_id,
                    entity_name=entity_name,
                    preview=preview,
                    requires_confirmation=True,
                    success=True
                ), [
                    SuggestedAction(label="✅ Ja, analysieren", action="query", value="Ja, starte die PySis-Analyse"),
                    SuggestedAction(label="❌ Abbrechen", action="query", value="Abbrechen"),
                ]

            # ==========================================
            # ANALYZE PYSIS - Execute (Step 2)
            # ==========================================
            elif action == "analyze_pysis_execute":
                preview = await service.get_operation_preview(UUID(entity_id), "analyze")

                if not preview.get("can_execute"):
                    return ContextActionResponse(
                        message=preview.get("message", "Analyse nicht möglich"),
                        action=action,
                        entity_id=entity_id,
                        entity_name=entity_name,
                        success=False
                    ), []

                # Execute the analysis
                task = await service.analyze_for_facets(UUID(entity_id))

                msg = f"✅ **PySis-Analyse für {entity_name} gestartet!**\n\n"
                msg += f"- Task-ID: `{task.id}`\n"
                msg += f"- {preview.get('fields_with_values', 0)} Felder werden analysiert\n"
                msg += f"\nDie Ergebnisse erscheinen in den Facets der Entity."

                return ContextActionResponse(
                    message=msg,
                    action=action,
                    entity_id=entity_id,
                    entity_name=entity_name,
                    task_id=str(task.id),
                    preview=preview,
                    success=True
                ), [
                    SuggestedAction(label="Status prüfen", action="query", value="Zeige PySis-Status"),
                ]

            # ==========================================
            # ENRICH FACETS - Preview (Step 1)
            # ==========================================
            elif action == "enrich_facets":
                preview = await service.get_operation_preview(UUID(entity_id), "enrich")

                if not preview.get("can_execute"):
                    return ContextActionResponse(
                        message=f"**Anreicherung nicht möglich:**\n{preview.get('message', 'Keine Daten verfügbar')}",
                        action=action,
                        entity_id=entity_id,
                        entity_name=entity_name,
                        preview=preview,
                        requires_confirmation=False,
                        success=False
                    ), []

                # Build detailed preview message
                msg = f"**Facet-Anreicherung für {entity_name}**\n\n"
                msg += f"📊 **Was wird angereichert:**\n"
                msg += f"- {preview.get('facet_values_count', 0)} bestehende Facets\n"
                msg += f"- mit {preview.get('fields_with_values', 0)} PySis-Feldern\n\n"

                facets_by_type = preview.get("facets_by_type", [])
                if facets_by_type:
                    msg += f"**Facets nach Typ:**\n"
                    for ft in facets_by_type:
                        msg += f"- {ft.get('name')}: {ft.get('count')} Einträge\n"

                msg += f"\n⚠️ **Hinweis:** Bestehende Werte werden NICHT überschrieben.\n"
                msg += f"\n**Möchtest du die Anreicherung starten?**"

                return ContextActionResponse(
                    message=msg,
                    action=action,
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

            # ==========================================
            # ENRICH FACETS - Execute (Step 2)
            # ==========================================
            elif action == "enrich_facets_execute":
                preview = await service.get_operation_preview(UUID(entity_id), "enrich")

                if not preview.get("can_execute"):
                    return ContextActionResponse(
                        message=preview.get("message", "Anreicherung nicht möglich"),
                        action=action,
                        entity_id=entity_id,
                        entity_name=entity_name,
                        success=False
                    ), []

                # Check if overwrite was requested
                overwrite = action_data.get("overwrite", False) if isinstance(action_data, dict) else False

                # Execute the enrichment
                task = await service.enrich_facets_from_pysis(UUID(entity_id), overwrite=overwrite)

                msg = f"✅ **Facet-Anreicherung für {entity_name} gestartet!**\n\n"
                msg += f"- Task-ID: `{task.id}`\n"
                msg += f"- {preview.get('facet_values_count', 0)} Facets werden angereichert\n"
                if overwrite:
                    msg += f"- ⚠️ Bestehende Werte werden überschrieben\n"
                msg += f"\nDie Ergebnisse erscheinen in den Facets der Entity."

                return ContextActionResponse(
                    message=msg,
                    action=action,
                    entity_id=entity_id,
                    entity_name=entity_name,
                    task_id=str(task.id),
                    preview=preview,
                    success=True
                ), [
                    SuggestedAction(label="Status prüfen", action="query", value="Zeige PySis-Status"),
                ]

            elif action == "start_crawl":
                # Start crawl for current entity's data sources
                return ContextActionResponse(
                    message=f"Crawl für {entity_name} starten - Feature in Entwicklung.",
                    action=action,
                    entity_id=entity_id,
                    entity_name=entity_name,
                    success=False
                ), []

            # ==========================================
            # CREATE FACET - Add facet value to entity
            # ==========================================
            elif action == "create_facet":
                # Extract facet data from action_data
                facet_type_slug = action_data.get("facet_type") if isinstance(action_data, dict) else None
                description = action_data.get("description", "") if isinstance(action_data, dict) else ""
                severity = action_data.get("severity") if isinstance(action_data, dict) else None
                facet_sub_type = action_data.get("type") if isinstance(action_data, dict) else None

                if not facet_type_slug:
                    return ContextActionResponse(
                        message="Bitte gib einen Facet-Typ an (z.B. pain_point, positive_signal, contact).",
                        action=action,
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
                        action=action,
                        entity_id=entity_id,
                        entity_name=entity_name,
                        success=False
                    ), []

                # Find the facet type
                facet_type_result = await self.db.execute(
                    select(FacetType).where(FacetType.slug == facet_type_slug, FacetType.is_active.is_(True))
                )
                facet_type = facet_type_result.scalar_one_or_none()

                if not facet_type:
                    return ContextActionResponse(
                        message=f"Facet-Typ '{facet_type_slug}' nicht gefunden. Verfügbare Typen: pain_point, positive_signal, contact, summary.",
                        action=action,
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
                    confidence_score=1.0,  # Manual creation = full confidence
                    human_verified=True,
                    is_active=True
                )
                self.db.add(facet_value)
                await self.db.commit()
                await self.db.refresh(facet_value)

                msg = f"✅ **{facet_type.name} hinzugefügt!**\n\n"
                msg += f"- **Entity:** {entity_name}\n"
                msg += f"- **Beschreibung:** {description}\n"
                if severity:
                    msg += f"- **Schweregrad:** {severity}\n"
                msg += f"\nDer Facet-Wert wurde erfolgreich erstellt."

                return ContextActionResponse(
                    message=msg,
                    action=action,
                    entity_id=entity_id,
                    entity_name=entity_name,
                    facet_value_id=str(facet_value.id),
                    success=True
                ), [
                    SuggestedAction(label="Weiteren hinzufügen", action="query", value=f"Füge weiteren {facet_type.name} hinzu"),
                    SuggestedAction(label="Facets anzeigen", action="query", value="Zeige alle Facets"),
                ]

            # ==========================================
            # ANALYZE ENTITY DATA - Extract facets from entity data
            # ==========================================
            elif action == "analyze_entity_data":
                from services.entity_data_facet_service import EntityDataFacetService

                # Get source types from action_data
                source_types = []
                if isinstance(action_data, dict) and "source_types" in action_data:
                    source_types = action_data.get("source_types", [])

                # If no source types specified, use all available
                if not source_types:
                    source_types = ["pysis", "relations", "documents", "extractions"]

                try:
                    service = EntityDataFacetService(self.db)

                    # Get available sources first
                    sources_info = await service.get_enrichment_sources(UUID(entity_id))

                    # Filter to only available sources
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
                            action=action,
                            entity_id=entity_id,
                            entity_name=entity_name,
                            success=False
                        ), []

                    # Start the analysis task
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
                        action=action,
                        entity_id=entity_id,
                        entity_name=entity_name,
                        success=True,
                        task_id=str(task.id)
                    ), [
                        SuggestedAction(
                            label="Zur Entity",
                            action="navigate",
                            value=f"entity/{entity_id}"
                        ),
                    ]

                except Exception as e:
                    logger.error("analyze_entity_data_error", error=str(e))
                    return ContextActionResponse(
                        message=f"Fehler beim Starten der Analyse: {str(e)}",
                        action=action,
                        entity_id=entity_id,
                        entity_name=entity_name,
                        success=False
                    ), []

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

    async def process_message_stream(
        self,
        message: str,
        context: AssistantContext,
        conversation_history: List[ConversationMessage],
        mode: str = "read",
        language: str = "de",
        attachments: Optional[List[Dict[str, Any]]] = None
    ):
        """Process a user message and yield streaming response chunks.

        Args:
            message: The user's text message
            context: Current application context
            conversation_history: Previous messages
            mode: 'read' or 'write' mode
            language: Response language
            attachments: List of attachment dicts with image/document data
        """
        # Initialize translator for this request
        self.tr = Translator(language)

        try:
            # Handle image attachments
            if attachments:
                image_attachments = [
                    a for a in attachments
                    if a.get("content_type", "").startswith("image/")
                ]
                if image_attachments:
                    yield {"type": "status", "message": "Analysiere Bild..."}
                    response = await self._handle_image_analysis(
                        message, context, image_attachments, language
                    )
                    yield {
                        "type": "complete",
                        "data": response.model_dump()
                    }
                    return

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

            elif intent == IntentType.BATCH_ACTION:
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
                    yield {"type": "status", "message": "Berechne Batch-Vorschau..."}
                    response_data, suggested_actions = await self._handle_batch_action_intent(
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

            elif intent == IntentType.FACET_MANAGEMENT:
                if mode == "read":
                    facet_action = intent_data.get("facet_action", "list_facet_types")
                    if facet_action in ["create_facet_type", "assign_facet_type"]:
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
                        yield {"type": "status", "message": "Lade Facet-Typen..."}
                        response_data, suggested_actions = await self._handle_facet_management(
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
                else:
                    yield {"type": "status", "message": "Verarbeite Facet-Management..."}
                    response_data, suggested_actions = await self._handle_facet_management(
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

            elif intent == IntentType.CONTEXT_ACTION:
                if not context.current_entity_id:
                    yield {
                        "type": "complete",
                        "data": {
                            "success": True,
                            "response": {
                                "type": "error",
                                "message": "Bitte navigiere zuerst zu einer Entity-Detailseite.",
                                "error_code": "no_entity_context"
                            }
                        }
                    }
                else:
                    yield {"type": "status", "message": "Führe Aktion aus..."}
                    context_action = intent_data.get("extracted_data", {}).get("context_action", "show_pysis_status")
                    write_actions = ["analyze_pysis", "enrich_facets", "start_crawl", "create_facet", "analyze_entity_data"]
                    if context_action in write_actions and mode == "read":
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
                        response_data, suggested_actions = await self._handle_context_action(
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
