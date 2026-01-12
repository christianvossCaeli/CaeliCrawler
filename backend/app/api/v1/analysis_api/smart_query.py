"""Smart Query endpoints - AI-powered natural language queries and commands."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_editor, require_llm_budget
from app.database import get_session
from app.models.user import User

from .helpers import build_preview

router = APIRouter()


# Rate limiter for AI-powered endpoints (expensive operations)
# Using user ID if available, otherwise IP address
def get_rate_limit_key(request: Request) -> str:
    """Get rate limit key - prefer user ID over IP for authenticated requests."""
    # Try to get user from request state (set by auth middleware)
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return f"user:{user.id}"
    return get_remote_address(request)


limiter = Limiter(key_func=get_rate_limit_key)


class ConversationMessage(BaseModel):
    """A single message in a conversation history."""

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class PageContext(BaseModel):
    """Page context for Plan Mode - enables context-aware responses."""

    current_route: str = Field(..., description="Current page route/path")
    view_mode: str = Field(default="unknown", description="Current view mode (dashboard, list, detail, summary, etc.)")
    available_features: list[str] = Field(default_factory=list, description="Features available on current page")
    entity_type: str | None = Field(default=None, description="Current entity type if applicable")
    entity_id: str | None = Field(default=None, description="Current entity ID if applicable")
    summary_id: str | None = Field(default=None, description="Current summary ID if applicable")
    widget_ids: list[str] = Field(default_factory=list, description="Widget IDs if on summary page")
    filter_state: dict | None = Field(default=None, description="Current filter state if applicable")


class SmartQueryRequest(BaseModel):
    """Request for smart query endpoint."""

    question: str = Field(..., min_length=1, max_length=10000, description="Natural language question or command")
    allow_write: bool = Field(default=False, description="Allow write operations (create entities, facets, relations)")
    mode: str | None = Field(default=None, description="Optional mode override: 'plan' for Plan Mode assistant")
    conversation_history: list[ConversationMessage] | None = Field(
        default=None, description="Conversation history for Plan Mode (list of previous messages)"
    )
    page_context: PageContext | None = Field(
        default=None, description="Current page context for context-aware Plan Mode responses"
    )


class SmartWriteRequest(BaseModel):
    """Request for smart write endpoint with preview support."""

    question: str = Field(..., min_length=3, max_length=2000, description="Natural language command")
    preview_only: bool = Field(default=True, description="If true, only return preview without executing")
    confirmed: bool = Field(default=False, description="If true and preview_only=false, execute the command")


@router.post("/smart-query")
@limiter.limit("30/minute")  # 30 AI queries per minute per user
async def smart_query_endpoint(
    request: Request,  # Required for slowapi
    query_request: SmartQueryRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_llm_budget),  # Budget check before LLM usage
):
    """
    Execute a natural language query or command against the Entity-Facet system.

    ## Modes:
    - **Read Mode** (default): Query data without modifications
    - **Write Mode** (allow_write=True): Create/modify data
    - **Plan Mode** (mode="plan"): Interactive assistant that helps formulate prompts

    ## Read Examples:
    - "Zeige mir auf welche künftige Events wichtige Entscheider-Personen von Gemeinden gehen"
    - "Welche Bürgermeister sprechen auf Windenergie-Konferenzen in den nächsten 3 Monaten?"
    - "Zeige mir alle Pain Points von Gemeinden in NRW"

    ## Write Examples (requires allow_write=True):
    - "Erstelle eine neue Person Max Müller, Bürgermeister"
    - "Füge einen Pain Point für Gummersbach hinzu: Bürgerbeschwerden wegen Lärmbelästigung"
    - "Verknüpfe Max Müller mit Gummersbach als Arbeitgeber"

    ## Plan Mode Examples (mode="plan"):
    - "Ich möchte Gemeinden finden die Probleme mit Windkraft haben"
    - "Wie kann ich Daten zu einer neuen Gemeinde anlegen?"
    - The assistant will guide you interactively to formulate the right prompt.

    The AI interprets the question/command and executes the appropriate action.
    """
    from services.smart_query import smart_query

    # Convert conversation history to the expected format
    conversation_history = None
    if query_request.conversation_history:
        conversation_history = [
            {"role": msg.role, "content": msg.content} for msg in query_request.conversation_history
        ]

    try:
        result = await smart_query(
            session,
            query_request.question,
            allow_write=query_request.allow_write,
            mode=query_request.mode,
            conversation_history=conversation_history,
        )
        return result
    except ValueError as e:
        # Convert validation errors to 422 Unprocessable Entity
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from None


class SmartQueryStreamRequest(BaseModel):
    """Request for streaming smart query (Plan Mode only)."""

    question: str = Field(..., min_length=1, max_length=10000, description="User's message")
    conversation_history: list[ConversationMessage] | None = Field(
        default=None, description="Conversation history for Plan Mode"
    )
    page_context: PageContext | None = Field(
        default=None, description="Current page context for context-aware responses"
    )


@router.post("/smart-query/stream")
@limiter.limit("20/minute")  # 20 streaming requests per minute (more expensive)
async def smart_query_stream_endpoint(
    request: Request,  # Required for slowapi
    stream_request: SmartQueryStreamRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_llm_budget),  # Budget check before LLM usage
):
    """
    Stream a Plan Mode query response using Server-Sent Events (SSE).

    This endpoint provides real-time streaming of the AI response for the Plan Mode.
    The response is sent as a stream of SSE events with the following types:
    - `start`: Signals the beginning of the stream
    - `chunk`: Contains a piece of the response text
    - `done`: Signals the end of the stream
    - `error`: Contains error information if something went wrong

    ## Example Event Format:
    ```
    data: {"event": "start"}

    data: {"event": "chunk", "data": "Hello, "}

    data: {"event": "chunk", "data": "I can help you"}

    data: {"event": "done"}
    ```

    ## Usage:
    Use EventSource or fetch with ReadableStream on the client side to consume the stream.
    """
    from services.smart_query import interpret_plan_query_stream

    # Convert conversation history to the expected format
    conversation_history = None
    if stream_request.conversation_history:
        conversation_history = [
            {"role": msg.role, "content": msg.content} for msg in stream_request.conversation_history
        ]

    # Convert page context to dict if provided
    page_context_dict = None
    if stream_request.page_context:
        page_context_dict = stream_request.page_context.model_dump()

    async def event_generator():
        async for event in interpret_plan_query_stream(
            question=stream_request.question,
            session=session,
            conversation_history=conversation_history,
            page_context=page_context_dict,
        ):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.post("/smart-write")
@limiter.limit("15/minute")  # 15 write operations per minute (most expensive)
async def smart_write_endpoint(
    request: Request,  # Required for slowapi
    write_request: SmartWriteRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """
    Execute a write command in natural language with preview support.

    **Workflow:**
    1. Send command with preview_only=True (default) → Get preview of what will be created
    2. Review the preview
    3. Send same command with preview_only=False, confirmed=True → Execute the command

    This endpoint is for:
    - Creating new entities (persons, municipalities, organizations, events)
    - Adding facets (pain points, positive signals, contacts)
    - Creating relations between entities
    - Creating category setups with automatic data source linking
    - Starting crawls for specific data sources

    Examples:
    - "Erstelle eine Person Hans Schmidt, Landrat von Oberberg"
    - "Füge einen Pain Point für Münster hinzu: Personalmangel in der IT-Abteilung"
    - "Neue Organisation: Caeli Wind GmbH, Windenergie-Entwickler"
    - "Verknüpfe Hans Schmidt mit Oberbergischer Kreis"
    - "Finde alle Events auf denen Entscheider aus NRW teilnehmen"
    - "Starte Crawls für alle Gummersbach Datenquellen"
    """
    from services.smart_query import execute_write_command, interpret_write_command

    # First, interpret the command (now uses dynamic prompt with DB data)
    command = await interpret_write_command(write_request.question, session)

    if not command or command.get("operation", "none") == "none":
        return {
            "success": False,
            "mode": "preview" if write_request.preview_only else "write",
            "message": "Keine Schreib-Operation erkannt. Bitte formulieren Sie das Kommando anders.",
            "interpretation": command,
            "original_question": write_request.question,
        }

    # Preview mode - just return the interpretation
    if write_request.preview_only:
        return {
            "success": True,
            "mode": "preview",
            "message": "Vorschau der geplanten Aktion",
            "interpretation": command,
            "preview": build_preview(command),
            "original_question": write_request.question,
        }

    # Execute mode - require confirmation
    if not write_request.confirmed:
        return {
            "success": False,
            "mode": "write",
            "message": "Bestätigung erforderlich. Setzen Sie confirmed=true um fortzufahren.",
            "interpretation": command,
            "preview": build_preview(command),
            "original_question": write_request.question,
        }

    # Execute the command with current user context
    result = await execute_write_command(session, command, current_user.id, original_question=write_request.question)
    result["original_question"] = write_request.question
    result["mode"] = "write"
    result["interpretation"] = command

    return result


class ValidatePromptRequest(BaseModel):
    """Request for validating a prompt before execution."""

    prompt: str = Field(..., min_length=3, max_length=2000, description="The prompt to validate")
    mode: str = Field(..., description="Target mode: 'read' or 'write'")


@router.post("/smart-query/validate")
@limiter.limit("60/minute")  # Higher limit for quick validation checks
async def validate_prompt_endpoint(
    request: Request,
    validate_request: ValidatePromptRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_llm_budget),  # Budget check before LLM usage
):
    """
    Validate a prompt before execution (smoke test / sanity check).

    This endpoint allows users to test prompts generated by Plan Mode
    before actually executing them. It performs interpretation without
    making any changes to the database.

    **Use Cases:**
    - Validate prompts from Plan Mode before transferring to Read/Write mode
    - Check if a prompt will be correctly interpreted
    - Preview the operations that would be performed

    Returns:
    - valid: Whether the prompt is syntactically valid
    - mode: The detected mode (read/write)
    - interpretation: The parsed query/command structure
    - preview: Human-readable description of what would happen
    - warnings: Any issues or suggestions
    """
    from services.smart_query import interpret_query, interpret_write_command

    prompt = validate_request.prompt.strip()
    target_mode = validate_request.mode.lower()

    result = {
        "valid": False,
        "mode": target_mode,
        "interpretation": None,
        "preview": None,
        "warnings": [],
        "original_prompt": prompt,
    }

    try:
        if target_mode == "write":
            # Validate as write command
            command = await interpret_write_command(prompt, session)

            if command and command.get("operation", "none") != "none":
                result["valid"] = True
                result["interpretation"] = command
                result["preview"] = _build_write_preview(command)
            else:
                result["warnings"].append(
                    "Keine gültige Schreib-Operation erkannt. "
                    "Versuche z.B. 'Erstelle...', 'Füge hinzu...', oder 'Verknüpfe...'."
                )

        else:  # read mode
            # Validate as read query
            query_params = await interpret_query(prompt, session=session)

            if query_params:
                result["valid"] = True
                result["interpretation"] = query_params
                result["preview"] = _build_read_preview(query_params)

                # Add warnings for potential issues
                if not query_params.get("entity_type"):
                    result["warnings"].append("Kein Entity-Typ erkannt. Die Abfrage könnte zu allgemein sein.")
            else:
                result["warnings"].append(
                    "Die Abfrage konnte nicht interpretiert werden. "
                    "Versuche spezifischer zu sein (z.B. 'Zeige mir alle Personen in Bayern')."
                )

    except ValueError as e:
        result["warnings"].append(f"Validierungsfehler: {str(e)}")
    except Exception as e:
        result["warnings"].append(f"Fehler bei der Interpretation: {str(e)}")

    return result


def _build_write_preview(command: dict) -> str:
    """Build a human-readable preview of a write command."""
    operation = command.get("operation", "unknown")
    previews = []

    if operation == "create_entity":
        entity_type = command.get("entity_type", "Entity")
        name = command.get("entity_data", {}).get("name", "Unbekannt")
        previews.append(f"Erstellt: {entity_type} '{name}'")

    elif operation == "create_facet":
        facet_type = command.get("facet_type", "Facet")
        entity = command.get("entity_identifier", "Entity")
        previews.append(f"Fügt hinzu: {facet_type} für '{entity}'")

    elif operation == "create_relation":
        rel_type = command.get("relation_type", "Relation")
        source = command.get("source_entity", "Quelle")
        target = command.get("target_entity", "Ziel")
        previews.append(f"Verknüpft: '{source}' --[{rel_type}]--> '{target}'")

    elif operation == "start_crawl":
        filters = command.get("filters", {})
        previews.append(f"Startet Crawl mit Filtern: {filters}")

    elif operation == "combined":
        ops = command.get("operations", [])
        previews.append(f"Kombinierte Operation mit {len(ops)} Aktionen")
        for i, op in enumerate(ops[:3], 1):  # Show first 3
            sub_preview = _build_write_preview(op)
            previews.append(f"  {i}. {sub_preview}")
        if len(ops) > 3:
            previews.append(f"  ... und {len(ops) - 3} weitere")

    else:
        previews.append(f"Operation: {operation}")

    return " | ".join(previews) if len(previews) == 1 else "\n".join(previews)


def _build_read_preview(query_params: dict) -> str:
    """Build a human-readable preview of a read query."""
    parts = []

    entity_type = query_params.get("entity_type", "Entities")
    parts.append(f"Sucht: {entity_type}")

    if query_params.get("filters"):
        filters = query_params["filters"]
        if filters.get("region"):
            parts.append(f"in {filters['region']}")
        if filters.get("position"):
            parts.append(f"mit Position '{filters['position']}'")

    if query_params.get("facet_types"):
        facets = ", ".join(query_params["facet_types"])
        parts.append(f"mit Facets: {facets}")

    if query_params.get("time_filter") == "future_only":
        parts.append("(nur zukünftige)")
    elif query_params.get("time_filter") == "past_only":
        parts.append("(nur vergangene)")

    if query_params.get("limit"):
        parts.append(f"(max. {query_params['limit']} Ergebnisse)")

    return " ".join(parts)


@router.get("/smart-query/examples")
async def get_smart_query_examples():
    """Get example queries for the smart query endpoint."""
    return {
        "read_examples": [
            {
                "question": "Zeige mir auf welche künftige Events wichtige Entscheider-Personen von Gemeinden gehen",
                "description": "Findet alle Personen mit Positionen wie Bürgermeister, Landrat etc. und deren zukünftige Event-Teilnahmen",
            },
            {
                "question": "Welche Bürgermeister sprechen auf Windenergie-Konferenzen?",
                "description": "Filtert nach Position 'Bürgermeister' und Event-Attendance Facets",
            },
            {
                "question": "Wo kann ich Entscheider aus Bayern in den nächsten 90 Tagen treffen?",
                "description": "Kombiniert Regions-Filter mit zukünftigen Events",
            },
            {
                "question": "Zeige mir alle Pain Points von Gemeinden",
                "description": "Listet alle Pain Point Facets gruppiert nach Gemeinde",
            },
        ],
        "write_examples": [
            {
                "question": "Erstelle eine neue Person Max Müller, Bürgermeister von Gummersbach",
                "description": "Erstellt eine Person-Entity mit Position 'Bürgermeister'",
            },
            {
                "question": "Füge einen Pain Point für Münster hinzu: Personalmangel in der IT",
                "description": "Erstellt einen Pain Point Facet für die Gemeinde Münster",
            },
            {
                "question": "Neue Organisation: Caeli Wind GmbH, Windenergie-Entwickler",
                "description": "Erstellt eine neue Organisation-Entity",
            },
            {
                "question": "Verknüpfe Max Müller mit Gummersbach als Arbeitgeber",
                "description": "Erstellt eine 'works_for' Relation zwischen Person und Gemeinde",
            },
        ],
        "supported_filters": {
            "time": ["künftig", "vergangen", "zukünftig", "in den nächsten X Tagen/Monaten"],
            "positions": ["Bürgermeister", "Landrat", "Dezernent", "Entscheider", "Amtsleiter"],
            "entity_types": ["Person", "Gemeinde", "Event", "Organisation"],
            "facet_types": ["Pain Points", "Positive Signale", "Event-Teilnahmen", "Kontakte"],
        },
        "write_operations": {
            "create_entity": ["Erstelle", "Neue/r/s", "Anlegen"],
            "create_facet": ["Füge hinzu", "Neuer Pain Point", "Neues Positive Signal"],
            "create_relation": ["Verknüpfe", "Verbinde", "arbeitet für", "ist Mitglied von"],
        },
    }
