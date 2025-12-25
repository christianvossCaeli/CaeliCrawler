"""Assistant Service - KI-gestützter Chat-Assistent für die App.

This is the main orchestration layer for the assistant service.
It delegates to specialized modules for different concerns:
- common: Shared utilities and client initialization
- context_builder: Entity context and data collection
- query_handler: Query processing and search
- action_executor: Action execution and batch operations
- response_formatter: Response formatting and presentation
- context_actions: Context-aware entity actions

The service maintains backward compatibility with existing imports.
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import FacetType
from app.schemas.assistant import (
    AssistantChatResponse,
    AssistantContext,
    AssistantResponseData,
    ConversationMessage,
    ErrorResponseData,
    IntentType,
    SuggestedAction,
)
from app.utils.security import (
    SecurityConstants,
    sanitize_for_prompt,
    should_block_request,
    validate_message_length,
    log_security_event,
)
from services.assistant.common import get_openai_client
from services.assistant.action_executor import (
    execute_action,
    execute_batch_action,
    preview_inline_edit,
    handle_batch_action_intent,
)
from services.assistant.context_actions import handle_context_action
from services.assistant.query_handler import handle_query, handle_context_query
from services.assistant.response_formatter import (
    generate_help_response,
    handle_navigation,
    handle_summarize,
    handle_image_analysis,
    handle_discussion,
    suggest_smart_query_redirect,
)
from services.assistant.prompts import INTENT_CLASSIFICATION_PROMPT
from services.smart_query import SmartQueryService
from services.translations import Translator

logger = structlog.get_logger()


class AssistantService:
    """Service for the AI-powered chat assistant.

    This is the main orchestration layer that coordinates between specialized modules.
    """

    def __init__(self, db: AsyncSession):
        """Initialize the assistant service.

        Args:
            db: Database session
        """
        self.db = db
        self.smart_query_service = SmartQueryService(db)
        self._facet_types_cache = None

    async def _get_facet_types(self) -> List[FacetType]:
        """Get all active facet types (cached for session).

        Returns:
            List of active FacetType instances
        """
        if self._facet_types_cache is None:
            result = await self.db.execute(
                select(FacetType).where(FacetType.is_active.is_(True)).order_by(FacetType.display_order)
            )
            self._facet_types_cache = result.scalars().all()
        return self._facet_types_cache

    async def _get_facet_type_by_slug(self, slug: str) -> Optional[FacetType]:
        """Get a facet type by slug.

        Args:
            slug: Facet type slug

        Returns:
            FacetType instance or None
        """
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

        Returns:
            AssistantChatResponse with formatted response
        """
        # Initialize translator for this request
        self.tr = Translator(language)

        # === Security: Input validation and sanitization ===
        is_valid, error_msg = validate_message_length(
            message, SecurityConstants.MAX_MESSAGE_LENGTH
        )
        if not is_valid:
            return AssistantChatResponse(
                message=error_msg,
                response_data=ErrorResponseData(
                    message=error_msg,
                    error_code="message_too_long"
                ),
                suggested_actions=[],
            )

        # Sanitize input and check for injection patterns
        sanitization_result = sanitize_for_prompt(message)

        # Block requests with high-risk injection patterns
        if should_block_request(sanitization_result.risk_level):
            log_security_event(
                event_type="prompt_injection_blocked",
                risk_level=sanitization_result.risk_level,
                details={
                    "detected_risks": sanitization_result.detected_risks,
                    "message_preview": message[:100] if message else "",
                },
            )
            return AssistantChatResponse(
                message=self.tr.t("security_blocked") if hasattr(self.tr, 't') else
                    "Ihre Anfrage konnte aus Sicherheitsgründen nicht verarbeitet werden.",
                response_data=ErrorResponseData(
                    message="Sicherheitsprüfung fehlgeschlagen",
                    error_code="security_blocked"
                ),
                suggested_actions=[],
            )

        # Use sanitized message
        message = sanitization_result.sanitized_text

        # Handle image attachments with Vision API
        if attachments:
            image_attachments = [
                a for a in attachments
                if a.get("content_type", "").startswith("image/")
            ]
            if image_attachments:
                result = await handle_image_analysis(
                    message, context, image_attachments, language
                )
                return AssistantChatResponse(
                    success=result.get("success", False),
                    response=result.get("response"),
                    suggested_actions=result.get("suggested_actions", [])
                )

        try:
            # Check for slash commands first
            if message.startswith("/"):
                return await self._handle_slash_command(message, context)

            # Classify intent
            intent, intent_data = await self._classify_intent(message, context)
            logger.info("intent_classified", intent=intent, data=intent_data)

            # Route to appropriate handler
            response_data, suggested_actions = await self._route_intent(
                intent, message, context, intent_data, mode
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
        """Classify the user's intent using LLM.

        Args:
            message: User message
            context: Application context

        Returns:
            Tuple of (IntentType, extracted_data)

        Raises:
            ValueError: If Azure OpenAI not configured or classification fails
        """
        client = get_openai_client()
        if not client:
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

    async def _route_intent(
        self,
        intent: IntentType,
        message: str,
        context: AssistantContext,
        intent_data: Dict[str, Any],
        mode: str
    ) -> Tuple[AssistantResponseData, List[SuggestedAction]]:
        """Route intent to appropriate handler.

        Args:
            intent: Classified intent type
            message: User message
            context: Application context
            intent_data: Extracted intent data
            mode: Read or write mode

        Returns:
            Tuple of (response_data, suggested_actions)
        """
        if intent == IntentType.QUERY:
            return await handle_query(self.db, message, context, intent_data, self.tr)

        elif intent == IntentType.CONTEXT_QUERY:
            return await handle_context_query(self.db, message, context, intent_data, self.tr)

        elif intent == IntentType.INLINE_EDIT:
            if mode == "read":
                return ErrorResponseData(
                    message=self.tr.t("write_mode_required"),
                    error_code="write_mode_required"
                ), []
            return await preview_inline_edit(self.db, message, context, intent_data), []

        elif intent == IntentType.COMPLEX_WRITE:
            return suggest_smart_query_redirect(message, intent_data), []

        elif intent == IntentType.NAVIGATION:
            return await handle_navigation(self.db, intent_data), []

        elif intent == IntentType.SUMMARIZE:
            return await handle_summarize(self.db, context, self.tr)

        elif intent == IntentType.HELP:
            return generate_help_response(context, intent_data, self.tr), []

        elif intent == IntentType.BATCH_ACTION:
            if mode == "read":
                return ErrorResponseData(
                    message=self.tr.t("write_mode_required"),
                    error_code="write_mode_required"
                ), []
            return await handle_batch_action_intent(self.db, message, context, intent_data, self.tr)

        elif intent == IntentType.FACET_MANAGEMENT:
            return await self._handle_facet_management(message, context, intent_data, mode)

        elif intent == IntentType.CONTEXT_ACTION:
            if not context.current_entity_id:
                return ErrorResponseData(
                    message="Bitte navigiere zuerst zu einer Entity-Detailseite.",
                    error_code="no_entity_context"
                ), []

            # Check write mode for write actions
            context_action = intent_data.get("extracted_data", {}).get("context_action", "show_pysis_status")
            write_actions = ["analyze_pysis", "enrich_facets", "start_crawl", "create_facet", "analyze_entity_data"]

            if context_action in write_actions and mode == "read":
                return ErrorResponseData(
                    message=self.tr.t("write_mode_required"),
                    error_code="write_mode_required"
                ), []

            return await handle_context_action(self.db, message, context, intent_data)

        elif intent == IntentType.DISCUSSION:
            return await handle_discussion(message, context, intent_data)

        else:
            return ErrorResponseData(
                message=self.tr.t("unknown_intent"),
                error_code="unknown_intent"
            ), []

    async def _handle_slash_command(
        self,
        message: str,
        context: AssistantContext
    ) -> AssistantChatResponse:
        """Handle slash commands.

        Args:
            message: Slash command message
            context: Application context

        Returns:
            AssistantChatResponse
        """
        parts = message.split(maxsplit=1)
        command = parts[0][1:].lower()  # Remove leading /
        args = parts[1] if len(parts) > 1 else ""

        if command == "help":
            return AssistantChatResponse(
                success=True,
                response=generate_help_response(context, {"help_topic": args}, self.tr)
            )

        elif command == "search":
            if not args:
                return AssistantChatResponse(
                    success=True,
                    response=ErrorResponseData(
                        message="Bitte gib einen Suchbegriff an: /search <suchbegriff>"
                    )
                )
            response_data, suggested = await handle_query(
                self.db, args, context, {"query_text": args}, self.tr
            )
            return AssistantChatResponse(
                success=True,
                response=response_data,
                suggested_actions=suggested
            )

        elif command == "create":
            from services.assistant.response_formatter import suggest_smart_query_redirect
            return AssistantChatResponse(
                success=True,
                response=suggest_smart_query_redirect(args, {})
            )

        elif command == "summary":
            response_data, suggested = await handle_summarize(self.db, context, self.tr)
            return AssistantChatResponse(
                success=True,
                response=response_data,
                suggested_actions=suggested
            )

        elif command == "navigate":
            return AssistantChatResponse(
                success=True,
                response=await handle_navigation(self.db, {"target_entity": args})
            )

        else:
            return AssistantChatResponse(
                success=True,
                response=ErrorResponseData(
                    message=f"Unbekannter Befehl: /{command}. Nutze /help für verfügbare Befehle."
                )
            )

    async def _handle_facet_management(
        self,
        message: str,
        context: AssistantContext,
        intent_data: Dict[str, Any],
        mode: str
    ) -> Tuple[AssistantResponseData, List[SuggestedAction]]:
        """Handle facet management requests.

        Args:
            message: User message
            context: Application context
            intent_data: Extracted intent data
            mode: Read or write mode

        Returns:
            Tuple of (response_data, suggested_actions)
        """
        # Import here to avoid circular dependencies
        from services.assistant.facet_management import handle_facet_management_request

        # Check mode for write operations
        facet_action = intent_data.get("facet_action", "list_facet_types")
        if mode == "read" and facet_action in ["create_facet_type", "assign_facet_type"]:
            return ErrorResponseData(
                message=self.tr.t("write_mode_required"),
                error_code="write_mode_required"
            ), []

        return await handle_facet_management_request(
            self.db, message, context, intent_data, self.tr
        )

    # === Public API methods for backward compatibility ===

    async def execute_action(
        self,
        action: "ActionDetails",
        context: AssistantContext
    ) -> Dict[str, Any]:
        """Execute a confirmed action.

        Args:
            action: Action details to execute
            context: Application context

        Returns:
            Dict with success status and details
        """
        return await execute_action(self.db, action, context)

    async def execute_batch_action(
        self,
        action_type: str,
        target_filter: Dict[str, Any],
        action_data: Dict[str, Any],
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Execute a batch action on multiple entities.

        Args:
            action_type: Type of action (add_facet, update_field, etc.)
            target_filter: Filter for target entities
            action_data: Data for the action
            dry_run: If True, only preview changes

        Returns:
            Dict with success, affected_count, preview, batch_id
        """
        return await execute_batch_action(
            self.db, action_type, target_filter, action_data, dry_run
        )

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

        This is a simplified streaming implementation that wraps the main
        process_message method. For full streaming support, implement
        streaming in individual handlers.

        Args:
            message: The user's text message
            context: Current application context
            conversation_history: Previous messages
            mode: 'read' or 'write' mode
            language: Response language
            attachments: List of attachment dicts

        Yields:
            Dict chunks with type and data
        """
        # Initialize translator
        self.tr = Translator(language)

        try:
            # Send initial status
            yield {"type": "status", "message": self.tr.t("streaming_processing")}

            # Process message normally
            response = await self.process_message(
                message, context, conversation_history, mode, language, attachments
            )

            # Convert to streaming format
            yield {
                "type": "complete",
                "data": response.model_dump()
            }

        except Exception as e:
            logger.error("assistant_stream_error", error=str(e))
            yield {
                "type": "error",
                "message": self.tr.t("error_occurred", error=str(e))
            }
