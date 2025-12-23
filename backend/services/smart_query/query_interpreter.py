"""Query interpretation for Smart Query Service - AI-powered NLP query parsing."""

import asyncio
import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
import structlog
from openai import AzureOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from .prompts import build_dynamic_write_prompt, build_compound_query_prompt, build_plan_mode_prompt
from .utils import clean_json_response

logger = structlog.get_logger()

# =============================================================================
# TTL Cache for Database Types
# =============================================================================

# Cache configuration
TYPES_CACHE_TTL_SECONDS = 300  # 5 minutes


class TypesCache:
    """Simple TTL cache for entity types, facet types, etc.

    This cache reduces database queries when building prompts for
    AI interpretation, especially useful for Plan Mode which may
    make multiple queries in quick succession.
    """

    def __init__(self, ttl_seconds: int = TYPES_CACHE_TTL_SECONDS):
        self.ttl_seconds = ttl_seconds
        self._facet_entity_cache: Optional[Tuple[List[Dict], List[Dict]]] = None
        self._facet_entity_timestamp: float = 0
        self._all_types_cache: Optional[Tuple[List[Dict], List[Dict], List[Dict], List[Dict]]] = None
        self._all_types_timestamp: float = 0

    def get_facet_entity_types(self) -> Optional[Tuple[List[Dict], List[Dict]]]:
        """Get cached facet and entity types if not expired."""
        if self._facet_entity_cache is None:
            return None
        if time.time() - self._facet_entity_timestamp > self.ttl_seconds:
            self._facet_entity_cache = None
            return None
        return self._facet_entity_cache

    def set_facet_entity_types(self, data: Tuple[List[Dict], List[Dict]]) -> None:
        """Cache facet and entity types."""
        self._facet_entity_cache = data
        self._facet_entity_timestamp = time.time()

    def get_all_types(self) -> Optional[Tuple[List[Dict], List[Dict], List[Dict], List[Dict]]]:
        """Get cached all types (entity, facet, relation, category) if not expired."""
        if self._all_types_cache is None:
            return None
        if time.time() - self._all_types_timestamp > self.ttl_seconds:
            self._all_types_cache = None
            return None
        return self._all_types_cache

    def set_all_types(self, data: Tuple[List[Dict], List[Dict], List[Dict], List[Dict]]) -> None:
        """Cache all types."""
        self._all_types_cache = data
        self._all_types_timestamp = time.time()

    def invalidate(self) -> None:
        """Invalidate all caches."""
        self._facet_entity_cache = None
        self._all_types_cache = None
        logger.debug("Types cache invalidated")


# Global cache instance
_types_cache = TypesCache()


def invalidate_types_cache() -> None:
    """Invalidate the types cache.

    Call this when entity types, facet types, relation types,
    or categories are created, updated, or deleted.
    """
    _types_cache.invalidate()

# =============================================================================
# Constants
# =============================================================================

# Azure OpenAI client - initialized lazily
_client = None

# AI Model Parameters
AI_TEMPERATURE_LOW = 0.1  # For precise, deterministic responses
AI_TEMPERATURE_MEDIUM = 0.2  # For creative but still consistent responses

# Token limits for different operations
MAX_TOKENS_QUERY = 1000
MAX_TOKENS_WRITE = 2000
MAX_TOKENS_COMPOUND = 1500

# Query validation limits
MAX_QUERY_LENGTH = 2000  # Maximum characters in a query
MIN_QUERY_LENGTH = 3  # Minimum characters in a query

# Plan Mode Token limits
MAX_TOKENS_PLAN_MODE = 2000

# Streaming Timeout Configuration
STREAMING_CONNECT_TIMEOUT = 10.0  # 10 seconds to establish connection
STREAMING_READ_TIMEOUT = 30.0  # 30 seconds between chunks
STREAMING_TOTAL_TIMEOUT = 120.0  # 120 seconds total for streaming

# SSE Event Types
SSE_EVENT_START = "start"
SSE_EVENT_CHUNK = "chunk"
SSE_EVENT_DONE = "done"
SSE_EVENT_ERROR = "error"


# =============================================================================
# Prompt Injection Sanitization
# =============================================================================

# Patterns that could be used for prompt injection attacks
PROMPT_INJECTION_PATTERNS = [
    # OpenAI/ChatGPT control tokens
    "<|im_start|>",
    "<|im_end|>",
    "<|endoftext|>",
    "<|system|>",
    "<|user|>",
    "<|assistant|>",

    # Anthropic/Claude control tokens
    "\n\nHuman:",
    "\n\nAssistant:",
    "[INST]",
    "[/INST]",
    "<<SYS>>",
    "<</SYS>>",

    # Common role injection attempts
    "system:",
    "System:",
    "SYSTEM:",
    "Human:",
    "HUMAN:",
    "Assistant:",
    "ASSISTANT:",
    "user:",
    "User:",
    "USER:",

    # Instruction override attempts (case variations handled separately)
    "ignore previous instructions",
    "ignore all previous",
    "forget your instructions",
    "disregard previous",
    "override system",
    "new instructions:",
    "actual instructions:",
    "real instructions:",
    "true instructions:",

    # Role-play injection
    "you are now",
    "pretend you are",
    "act as if",
    "from now on you",
    "simulate being",
    "roleplay as",
    "behave like",

    # Delimiter injection
    "---BEGIN SYSTEM---",
    "---END SYSTEM---",
    "###SYSTEM###",
    "===SYSTEM===",
    "[SYSTEM]",
    "[/SYSTEM]",
    "```system",
    "```instruction",
]

# Regex patterns for more complex injection attempts
PROMPT_INJECTION_REGEX_PATTERNS = [
    # XML-style tags that could confuse the model
    re.compile(r"<\s*system\s*>", re.IGNORECASE),
    re.compile(r"<\s*/\s*system\s*>", re.IGNORECASE),
    re.compile(r"<\s*instruction\s*>", re.IGNORECASE),
    re.compile(r"<\s*/\s*instruction\s*>", re.IGNORECASE),
    re.compile(r"<\s*prompt\s*>", re.IGNORECASE),
    re.compile(r"<\s*/\s*prompt\s*>", re.IGNORECASE),

    # Unicode escape sequences that could bypass filters
    re.compile(r"\\u[0-9a-fA-F]{4}"),  # \u0048 etc.
    re.compile(r"&#x?[0-9a-fA-F]+;"),  # HTML entities

    # Base64 encoded content (potential hidden instructions)
    re.compile(r"[A-Za-z0-9+/]{50,}={0,2}"),  # Long base64 strings

    # Excessive whitespace manipulation
    re.compile(r"\n{5,}"),  # More than 4 consecutive newlines
    re.compile(r" {10,}"),  # More than 9 consecutive spaces
]


def sanitize_user_input(content: str, max_length: int = MAX_QUERY_LENGTH) -> str:
    """Sanitize user input to prevent prompt injection attacks.

    This function removes or neutralizes patterns that could be used to:
    - Override system instructions
    - Inject new roles or personas
    - Bypass safety guidelines
    - Manipulate the AI's behavior

    Args:
        content: The user input to sanitize
        max_length: Maximum allowed length (truncated if exceeded)

    Returns:
        Sanitized content string
    """
    if not content:
        return ""

    # Step 1: Truncate to max length
    if len(content) > max_length:
        content = content[:max_length]
        logger.warning("User input truncated", original_length=len(content), max_length=max_length)

    # Step 2: Remove exact pattern matches (case-sensitive first)
    for pattern in PROMPT_INJECTION_PATTERNS:
        content = content.replace(pattern, "")

    # Step 3: Case-insensitive removal of dangerous patterns
    dangerous_phrases = [
        "ignore previous",
        "ignore all",
        "forget your",
        "disregard",
        "override",
        "new instruction",
        "actual instruction",
        "real instruction",
        "true instruction",
    ]
    content_lower = content.lower()
    for phrase in dangerous_phrases:
        # Find and remove case-insensitively while preserving surrounding text
        idx = content_lower.find(phrase)
        while idx != -1:
            content = content[:idx] + content[idx + len(phrase):]
            content_lower = content.lower()
            idx = content_lower.find(phrase)

    # Step 4: Apply regex patterns
    for regex in PROMPT_INJECTION_REGEX_PATTERNS:
        content = regex.sub("", content)

    # Step 5: Normalize whitespace (but preserve intentional formatting)
    content = re.sub(r"\n{3,}", "\n\n", content)  # Max 2 consecutive newlines
    content = re.sub(r" {3,}", "  ", content)  # Max 2 consecutive spaces

    # Step 6: Strip and clean
    content = content.strip()

    return content


def sanitize_conversation_messages(
    messages: List[Dict[str, str]],
    max_messages: int = 20,
) -> List[Dict[str, str]]:
    """Sanitize a list of conversation messages.

    Args:
        messages: List of {"role": "user"|"assistant", "content": "..."} dicts
        max_messages: Maximum number of messages to keep

    Returns:
        Sanitized list of messages
    """
    if not messages:
        return []

    # Limit number of messages (keep first and last n-1)
    if len(messages) > max_messages:
        messages = [messages[0]] + messages[-(max_messages - 1):]
        logger.info("Conversation history truncated", kept=max_messages)

    sanitized = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        # Validate role
        if role not in ("user", "assistant"):
            role = "user"

        # Sanitize content
        sanitized_content = sanitize_user_input(content)

        if sanitized_content:  # Only keep non-empty messages
            sanitized.append({
                "role": role,
                "content": sanitized_content,
            })

    return sanitized


async def call_claude_for_plan_mode_stream(
    system_prompt: str,
    messages: List[Dict[str, str]],
    max_tokens: int = MAX_TOKENS_PLAN_MODE,
):
    """Call Claude Opus for Plan Mode with streaming response.

    Yields SSE-formatted events as the response is generated.

    Args:
        system_prompt: The system prompt with Smart Query documentation
        messages: Conversation history as list of {"role": "user"|"assistant", "content": "..."}
        max_tokens: Maximum tokens in response

    Yields:
        SSE-formatted strings: data: {"event": "...", "data": "..."}
    """
    import json as json_module

    if not settings.anthropic_api_endpoint or not settings.anthropic_api_key:
        logger.warning("Claude API not configured for streaming")
        yield f"data: {json_module.dumps({'event': SSE_EVENT_ERROR, 'data': 'Claude API not configured'})}\n\n"
        return

    # Sanitize and limit conversation history using comprehensive sanitization
    sanitized_messages = sanitize_conversation_messages(messages)

    if not sanitized_messages:
        yield f"data: {json_module.dumps({'event': SSE_EVENT_ERROR, 'data': 'No valid messages'})}\n\n"
        return

    # Signal start of streaming
    yield f"data: {json_module.dumps({'event': SSE_EVENT_START})}\n\n"

    # Track streaming state for partial content handling
    streaming_started = False
    last_chunk_time = time.monotonic()

    # Configure granular timeouts:
    # - connect: time to establish connection
    # - read: time to wait for each chunk (important for streaming)
    # - pool: time to wait for connection from pool
    timeout_config = httpx.Timeout(
        connect=STREAMING_CONNECT_TIMEOUT,
        read=STREAMING_READ_TIMEOUT,
        write=10.0,
        pool=5.0,
    )

    try:
        async with httpx.AsyncClient(timeout=timeout_config) as client:
            async with client.stream(
                "POST",
                settings.anthropic_api_endpoint,
                headers={
                    "api-key": settings.anthropic_api_key,
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": settings.anthropic_model,
                    "max_tokens": max_tokens,
                    "system": system_prompt,
                    "messages": sanitized_messages,
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()
                streaming_started = True

                async for line in response.aiter_lines():
                    # Check total streaming timeout
                    elapsed = time.monotonic() - last_chunk_time
                    if elapsed > STREAMING_TOTAL_TIMEOUT:
                        logger.warning(
                            "Streaming total timeout exceeded",
                            elapsed=elapsed,
                            max_timeout=STREAMING_TOTAL_TIMEOUT,
                        )
                        yield f"data: {json_module.dumps({'event': SSE_EVENT_ERROR, 'data': 'Streaming timeout exceeded'})}\n\n"
                        return

                    if not line:
                        continue

                    # Update last chunk time on any data
                    last_chunk_time = time.monotonic()

                    # Parse SSE from Anthropic API
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break

                        try:
                            data = json_module.loads(data_str)
                            event_type = data.get("type", "")

                            # Handle content_block_delta events (actual text)
                            if event_type == "content_block_delta":
                                delta = data.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    text = delta.get("text", "")
                                    if text:
                                        yield f"data: {json_module.dumps({'event': SSE_EVENT_CHUNK, 'data': text})}\n\n"

                            # Handle message_stop event
                            elif event_type == "message_stop":
                                break

                        except json_module.JSONDecodeError:
                            continue

        # Signal completion
        yield f"data: {json_module.dumps({'event': SSE_EVENT_DONE})}\n\n"

    except httpx.ConnectTimeout:
        logger.error("Claude API connection timeout")
        yield f"data: {json_module.dumps({'event': SSE_EVENT_ERROR, 'data': 'Connection timeout - server unreachable'})}\n\n"
    except httpx.ReadTimeout:
        logger.error("Claude API read timeout during streaming")
        # Yield partial timeout event - frontend can decide to keep partial content
        yield f"data: {json_module.dumps({'event': SSE_EVENT_ERROR, 'data': 'Read timeout - response incomplete', 'partial': streaming_started})}\n\n"
    except httpx.TimeoutException:
        logger.error("Claude API streaming request timed out")
        yield f"data: {json_module.dumps({'event': SSE_EVENT_ERROR, 'data': 'Request timed out', 'partial': streaming_started})}\n\n"
    except httpx.HTTPStatusError as e:
        logger.error("Claude API HTTP error during streaming", status_code=e.response.status_code)
        yield f"data: {json_module.dumps({'event': SSE_EVENT_ERROR, 'data': f'HTTP error: {e.response.status_code}'})}\n\n"
    except Exception as e:
        logger.error("Claude API streaming error", error=str(e), exc_info=True)
        yield f"data: {json_module.dumps({'event': SSE_EVENT_ERROR, 'data': str(e), 'partial': streaming_started})}\n\n"


async def call_claude_for_plan_mode(
    system_prompt: str,
    messages: List[Dict[str, str]],
    max_tokens: int = MAX_TOKENS_PLAN_MODE,
) -> Optional[str]:
    """Call Claude Opus for Plan Mode with conversation history.

    Uses the Azure-hosted Anthropic endpoint configured in settings.

    Args:
        system_prompt: The system prompt with Smart Query documentation
        messages: Conversation history as list of {"role": "user"|"assistant", "content": "..."}
        max_tokens: Maximum tokens in response

    Returns:
        Response content or None on error
    """
    if not settings.anthropic_api_endpoint or not settings.anthropic_api_key:
        logger.warning("Claude API not configured, falling back to OpenAI")
        return None

    # Sanitize and limit conversation history using comprehensive sanitization
    sanitized_messages = sanitize_conversation_messages(messages)

    if not sanitized_messages:
        logger.warning("No valid messages after sanitization")
        return None

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                settings.anthropic_api_endpoint,
                headers={
                    "api-key": settings.anthropic_api_key,
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": settings.anthropic_model,
                    "max_tokens": max_tokens,
                    "system": system_prompt,
                    "messages": sanitized_messages,
                },
            )
            response.raise_for_status()
            data = response.json()

            # Extract content from Claude response
            if "content" in data and len(data["content"]) > 0:
                return data["content"][0].get("text", "")

            logger.warning("Claude API returned empty content")
            return None

    except httpx.TimeoutException:
        logger.error("Claude API request timed out after 120 seconds")
        return None
    except httpx.HTTPStatusError as e:
        logger.error(
            "Claude API HTTP error",
            status_code=e.response.status_code,
            detail=e.response.text[:500] if e.response.text else None,
        )
        return None
    except httpx.HTTPError as e:
        logger.error("Claude API request failed", error=str(e))
        return None
    except Exception as e:
        logger.error("Claude API unexpected error", error=str(e), exc_info=True)
        return None


def get_openai_client() -> AzureOpenAI:
    """Get or create the Azure OpenAI client.

    Raises:
        ValueError: If Azure OpenAI is not configured
    """
    global _client
    if _client is None:
        if not settings.azure_openai_api_key:
            raise ValueError("KI-Service nicht erreichbar: Azure OpenAI ist nicht konfiguriert")
        _client = AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint,
        )
    return _client


def build_dynamic_query_prompt(facet_types: List[Dict[str, Any]], entity_types: List[Dict[str, Any]], query: str = "") -> str:
    """Build the query interpretation prompt dynamically with current facet and entity types."""
    from datetime import date

    today = date.today().isoformat()

    # Build facet types section
    facet_lines = []
    for ft in facet_types:
        desc = ft.get("description") or f"{ft['name']}"
        time_note = " (hat time_filter!)" if ft.get("is_time_based") else ""
        facet_lines.append(f"- {ft['slug']}: {desc}{time_note}")
    facet_section = "\n".join(facet_lines) if facet_lines else "- (keine Facet-Typen definiert)"

    # Build entity types section
    entity_lines = []
    for et in entity_types:
        desc = et.get("description") or et["name"]
        entity_lines.append(f"- {et['slug']}: {desc}")
    entity_section = "\n".join(entity_lines) if entity_lines else "- (keine Entity-Typen definiert)"

    return f"""Du bist ein Query-Interpreter für ein Entity-Facet-System.

## Verfügbare Entity Types:
{entity_section}

## Verfügbare Facet Types:
{facet_section}

## Verfügbare Relation Types:
- works_for: Person arbeitet für Municipality
- attends: Person nimmt teil an Event
- located_in: Event findet statt in Municipality
- member_of: Person ist Mitglied von Organization

## Multi-Hop Relationen (WICHTIG für komplexe Abfragen!):
Verwende `relation_chain` für Abfragen über mehrere Beziehungsebenen:

### Beispiele:
1. "Personen, deren Gemeinden Pain Points haben"
   → primary_entity_type: "person"
   → relation_chain: [{{"type": "works_for", "direction": "source"}}]
   → target_facets_at_chain_end: ["pain_point"]

2. "Events bei denen Bürgermeister teilnehmen"
   → primary_entity_type: "event"
   → relation_chain: [{{"type": "attends", "direction": "target", "position_filter": ["Bürgermeister"]}}]

3. "Gebietskörperschaften mit Mitarbeitern die Events besucht haben"
   → primary_entity_type: "territorial_entity"
   → relation_chain: [
       {{"type": "works_for", "direction": "target"}},
       {{"type": "attends", "direction": "source"}}
     ]
   → target_facets_at_chain_end: ["event_attendance"]

4. "Personen deren Gemeinden in NRW Pain Points aber keine positive Signale haben"
   → primary_entity_type: "person"
   → relation_chain: [{{"type": "works_for", "direction": "source", "location_filter": "Nordrhein-Westfalen"}}]
   → target_facets_at_chain_end: ["pain_point"]
   → negative_facets_at_chain_end: ["positive_signal"]

### direction-Werte:
- "source": Folge Relation von source_entity → target_entity
- "target": Folge Relation von target_entity → source_entity

### Optional pro Hop:
- facet_filter: Nur Entities mit diesem Facet einbeziehen
- negative_facet_filter: Entities mit diesem Facet ausschließen
- position_filter: Nach Position filtern (bei Personen)
- location_filter: Nach Region filtern

Trigger-Phrasen für Multi-Hop:
- "deren Gemeinden", "dessen Organisation", "bei denen"
- "Personen von Gemeinden die..."
- "Mitarbeiter deren Arbeitgeber..."
- "Events an denen ... teilnehmen"

## Time Filter Optionen:
- future_only: Nur zukünftige Einträge
- past_only: Nur vergangene Einträge
- all: Alle Einträge

## Datumsbereich (date_range):
Wenn der Benutzer einen spezifischen Zeitraum angibt, verwende date_range statt time_filter:
- "Events zwischen 1. Januar und 31. März 2025" → date_range: {{ "start": "2025-01-01", "end": "2025-03-31" }}
- "Events im Januar 2025" → date_range: {{ "start": "2025-01-01", "end": "2025-01-31" }}
- "Events letzte Woche" → date_range mit entsprechenden Daten
- "Events der letzten 30 Tage" → date_range mit start = heute - 30 Tage, end = heute
- Heute ist: {today}
Wenn kein spezifischer Zeitraum angegeben wird, verwende time_filter.

## Boolean-Operatoren (AND/OR):
Verwende `filters.logical_operator` für kombinierte Bedingungen:

### OR für Locations (admin_level_1):
- "Gemeinden in NRW oder Bayern" → admin_level_1: ["Nordrhein-Westfalen", "Bayern"], logical_operator: "OR"
- "Personen aus Berlin, Hamburg oder Bremen" → admin_level_1: ["Berlin", "Hamburg", "Bremen"], logical_operator: "OR"

### AND für Facets (facet_operator):
- "Personen MIT Pain Points UND Events" → facet_types: ["pain_point", "event_attendance"], facet_operator: "AND"
- "Gemeinden mit Pain Points UND Kontakten" → facet_types: ["pain_point", "contact"], facet_operator: "AND"

### Standard (wenn nicht explizit angegeben):
- Mehrere Locations = OR (zeige Ergebnisse aus ALLEN genannten Regionen)
- Mehrere Facets = OR (zeige Ergebnisse mit MINDESTENS EINEM der Facets)
- "UND"/"AND" im Text = AND (ALLE Bedingungen müssen erfüllt sein)
- "ODER"/"OR" im Text = OR (MINDESTENS EINE Bedingung muss erfüllt sein)

## Negation (NOT/OHNE/NICHT):
Verwende `negative_facet_types` und `negative_locations` für Ausschlüsse:

### Facets ausschließen:
- "Gemeinden OHNE Pain Points" → negative_facet_types: ["pain_point"]
- "Personen die KEINE Events besucht haben" → negative_facet_types: ["event_attendance"]
- "Entities OHNE Kontakte" → negative_facet_types: ["contact"]

### Locations ausschließen:
- "Gemeinden NICHT in NRW" → negative_locations: ["Nordrhein-Westfalen"]
- "Personen außerhalb von Bayern" → negative_locations: ["Bayern"]

Trigger-Wörter: "ohne", "nicht", "keine", "kein", "außer", "außerhalb", "excluding", "not"

## Wichtige Positionen (für "Entscheider"):
- Bürgermeister, Oberbürgermeister
- Landrat, Landrätin
- Dezernent, Dezernentin
- Amtsleiter, Amtsleiterin
- Gemeinderat, Stadtrat
- Kämmerer

## Query Type (WICHTIG!):
- count: Nur die Gesamtanzahl zurückgeben (bei Fragen wie "wie viele", "Anzahl", "count", "zähle", "how many")
- list: Eine Liste von Ergebnissen zurückgeben (bei Fragen wie "zeige", "liste", "welche", "wer")
- aggregate: Statistische Berechnungen durchführen (bei Fragen mit "durchschnitt", "average", "summe", "minimum", "maximum")

## Aggregations-Queries (query_type: aggregate):
Verwende für statistische Abfragen:
- "Durchschnittliche Anzahl Pain Points pro Gemeinde" → query_type: "aggregate", aggregate_function: "AVG", aggregate_target: "facet_count", aggregate_facet_type: "pain_point", group_by: "entity_type"
- "Wieviele Pain Points haben Gemeinden insgesamt?" → query_type: "aggregate", aggregate_function: "SUM", aggregate_target: "facet_count", aggregate_facet_type: "pain_point"
- "Maximale Anzahl Events pro Person" → query_type: "aggregate", aggregate_function: "MAX", aggregate_target: "facet_count", aggregate_facet_type: "event_attendance"
- "Anzahl Entities pro Bundesland" → query_type: "aggregate", aggregate_function: "COUNT", group_by: "admin_level_1"

Aggregate Functions: COUNT, SUM, AVG, MIN, MAX
Group By Options: entity_type, admin_level_1, country, facet_type

## Regionale Filter:
### country (ISO 3166-1 alpha-2 Code):
- Deutschland, Germany -> "DE"
- Österreich, Austria -> "AT"
- Schweiz -> "CH"
- Großbritannien, UK, United Kingdom -> "GB"

### admin_level_1 (Bundesländer, Regionen, States):
- Beispiele Deutschland: "Nordrhein-Westfalen" (auch NRW), "Bayern" (auch BY), "Baden-Württemberg", etc.
- Beispiele Österreich: "Wien", "Tirol", "Steiermark", etc.
- Verwende immer den vollen Namen (nicht Abkürzungen)

Analysiere die Benutzeranfrage und gib ein JSON zurück mit:
{{
  "query_type": "count|list|aggregate",
  "primary_entity_type": "<entity_type_slug>",
  "facet_types": ["facet_slug_1", "facet_slug_2"],
  "facet_operator": "AND|OR (Standard: OR, AND wenn alle Facets gleichzeitig vorhanden sein müssen)",
  "negative_facet_types": ["facet_slug_auszuschließen (Entities die diese NICHT haben)"],
  "time_filter": "future_only|past_only|all",
  "date_range": {{
    "start": "YYYY-MM-DD (optional, wenn spezifischer Zeitraum angegeben)",
    "end": "YYYY-MM-DD (optional, wenn spezifischer Zeitraum angegeben)"
  }},
  "aggregate": {{
    "function": "COUNT|SUM|AVG|MIN|MAX (nur für query_type: aggregate)",
    "target": "entity_count|facet_count",
    "facet_type": "facet_slug (wenn target=facet_count)",
    "group_by": "entity_type|admin_level_1|country|facet_type (optional)"
  }},
  "relation_chain": [
    {{
      "type": "works_for|attends|located_in|member_of",
      "direction": "source|target",
      "facet_filter": "optional: facet_slug (nur Entities mit diesem Facet)",
      "negative_facet_filter": "optional: facet_slug (Entities ohne dieses Facet)",
      "position_filter": ["optional: Position-Filter für Personen"],
      "location_filter": "optional: admin_level_1 für diesen Hop"
    }}
  ],
  "target_facets_at_chain_end": ["facet_slugs die die Ziel-Entities am Ende der Chain haben müssen"],
  "negative_facets_at_chain_end": ["facet_slugs die die Ziel-Entities am Ende der Chain NICHT haben dürfen"],
  "filters": {{
    "position_keywords": ["Bürgermeister", "Landrat"],
    "location_keywords": ["NRW", "Bayern"],
    "country": "DE",
    "admin_level_1": "Nordrhein-Westfalen (oder Array für OR: ['Nordrhein-Westfalen', 'Bayern'])",
    "negative_locations": ["Regionen auszuschließen"],
    "logical_operator": "AND|OR (Standard: OR für Locations)"
  }},
  "result_grouping": "by_event|by_person|by_municipality|flat",
  "explanation": "Kurze Erklärung was abgefragt wird"
}}

Benutzeranfrage: {query}

Antworte NUR mit validem JSON."""


async def load_facet_and_entity_types(session: AsyncSession) -> tuple[List[Dict], List[Dict]]:
    """Load facet types and entity types from the database with TTL caching."""
    from app.models import FacetType, EntityType

    # Check cache first
    cached = _types_cache.get_facet_entity_types()
    if cached is not None:
        logger.debug("Using cached facet and entity types")
        return cached

    logger.debug("Loading facet and entity types from database")

    # Load facet types
    facet_result = await session.execute(
        select(FacetType).where(FacetType.is_active.is_(True)).order_by(FacetType.display_order)
    )
    facet_types = [
        {
            "slug": ft.slug,
            "name": ft.name,
            "description": ft.description,
            "is_time_based": ft.is_time_based,
        }
        for ft in facet_result.scalars().all()
    ]

    # Load entity types
    entity_result = await session.execute(
        select(EntityType).where(EntityType.is_active.is_(True)).order_by(EntityType.display_order)
    )
    entity_types = [
        {
            "slug": et.slug,
            "name": et.name,
            "description": et.description,
        }
        for et in entity_result.scalars().all()
    ]

    # Cache the result
    result = (facet_types, entity_types)
    _types_cache.set_facet_entity_types(result)

    return result


async def load_all_types_for_write(session: AsyncSession) -> tuple[List[Dict], List[Dict], List[Dict], List[Dict]]:
    """Load all types needed for write command interpretation with TTL caching.

    Returns:
        Tuple of (entity_types, facet_types, relation_types, categories)
    """
    from app.models import FacetType, EntityType, RelationType, Category

    # Check cache first
    cached = _types_cache.get_all_types()
    if cached is not None:
        logger.debug("Using cached all types (entity, facet, relation, category)")
        return cached

    logger.debug("Loading all types from database")

    # Load entity types with full details
    entity_result = await session.execute(
        select(EntityType).where(EntityType.is_active.is_(True)).order_by(EntityType.display_order)
    )
    entity_types = [
        {
            "slug": et.slug,
            "name": et.name,
            "description": et.description,
            "supports_hierarchy": et.supports_hierarchy,
            "attribute_schema": et.attribute_schema,
        }
        for et in entity_result.scalars().all()
    ]

    # Load facet types with applicable entity types
    facet_result = await session.execute(
        select(FacetType).where(FacetType.is_active.is_(True)).order_by(FacetType.display_order)
    )
    facet_types = [
        {
            "slug": ft.slug,
            "name": ft.name,
            "description": ft.description,
            "applicable_entity_type_slugs": ft.applicable_entity_type_slugs or [],
        }
        for ft in facet_result.scalars().all()
    ]

    # Load relation types
    relation_result = await session.execute(
        select(RelationType).where(RelationType.is_active.is_(True))
    )
    relation_types = [
        {
            "slug": rt.slug,
            "name": rt.name,
            "description": rt.description,
        }
        for rt in relation_result.scalars().all()
    ]

    # Load categories
    category_result = await session.execute(
        select(Category).where(Category.is_active.is_(True))
    )
    categories = [
        {
            "slug": cat.slug,
            "name": cat.name,
            "description": cat.description,
        }
        for cat in category_result.scalars().all()
    ]

    # Cache the result
    result = (entity_types, facet_types, relation_types, categories)
    _types_cache.set_all_types(result)

    return result


def _validate_and_sanitize_query(question: str) -> str:
    """Validate and sanitize query input.

    Args:
        question: The query string to validate and sanitize

    Returns:
        Sanitized query string

    Raises:
        ValueError: If query is invalid (empty, too short, or too long after sanitization)
    """
    if not question or not question.strip():
        raise ValueError("Query cannot be empty")

    # Sanitize the input first
    sanitized = sanitize_user_input(question)

    if not sanitized:
        raise ValueError("Query cannot be empty after sanitization")

    query_length = len(sanitized)
    if query_length < MIN_QUERY_LENGTH:
        raise ValueError(f"Query too short (min {MIN_QUERY_LENGTH} characters)")
    if query_length > MAX_QUERY_LENGTH:
        raise ValueError(f"Query too long (max {MAX_QUERY_LENGTH} characters)")

    return sanitized


def _validate_query_input(question: str) -> None:
    """Validate query input for length and content (legacy, use _validate_and_sanitize_query).

    Args:
        question: The query string to validate

    Raises:
        ValueError: If query is invalid
    """
    _validate_and_sanitize_query(question)


async def interpret_query(question: str, session: Optional[AsyncSession] = None) -> Dict[str, Any]:
    """Use AI to interpret natural language query into structured query parameters.

    Args:
        question: The natural language query
        session: Database session for dynamic prompt generation

    Raises:
        ValueError: If Azure OpenAI is not configured or query is invalid
        RuntimeError: If query interpretation fails
    """
    # Validate and sanitize input
    sanitized_question = _validate_and_sanitize_query(question)

    client = get_openai_client()

    try:
        # Build prompt dynamically with session
        if session:
            facet_types, entity_types = await load_facet_and_entity_types(session)
            prompt = build_dynamic_query_prompt(facet_types, entity_types, query=sanitized_question)
            logger.debug("Using dynamic prompt with facet_types", facet_count=len(facet_types))
        else:
            raise ValueError("Database session is required for query interpretation")

        response = client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[
                {
                    "role": "system",
                    "content": "Du bist ein präziser Query-Interpreter. Antworte nur mit JSON.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=AI_TEMPERATURE_LOW,
            max_tokens=MAX_TOKENS_QUERY,
        )

        content = response.choices[0].message.content.strip()
        logger.debug("AI raw response", content=content[:200] if content else "empty")

        content = clean_json_response(content)
        logger.debug("AI cleaned response", content=content[:200] if content else "empty")

        parsed = json.loads(content)
        logger.info("Query interpreted successfully", interpretation=parsed)
        return parsed

    except ValueError:
        raise
    except Exception as e:
        logger.error("Failed to interpret query", error=str(e), exc_info=True)
        raise RuntimeError(f"KI-Service Fehler: Query-Interpretation fehlgeschlagen - {str(e)}")


async def interpret_write_command(question: str, session: Optional[AsyncSession] = None) -> Dict[str, Any]:
    """Use AI to interpret if the question is a write command.

    Args:
        question: The natural language command
        session: Database session for dynamic prompt generation (required)

    Raises:
        ValueError: If Azure OpenAI is not configured, session is missing, or query is invalid
        RuntimeError: If command interpretation fails
    """
    # Validate and sanitize input
    sanitized_question = _validate_and_sanitize_query(question)

    client = get_openai_client()

    if not session:
        raise ValueError("Database session is required for write command interpretation")

    try:
        # Load all types from database for dynamic prompt
        entity_types, facet_types, relation_types, categories = await load_all_types_for_write(session)

        # Build dynamic prompt
        prompt = build_dynamic_write_prompt(
            entity_types=entity_types,
            facet_types=facet_types,
            relation_types=relation_types,
            categories=categories,
            query=sanitized_question,
        )

        logger.debug(
            "Using dynamic write prompt",
            entity_count=len(entity_types),
            facet_count=len(facet_types),
            relation_count=len(relation_types),
            category_count=len(categories),
        )

        response = client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[
                {
                    "role": "system",
                    "content": "Du bist ein intelligenter Command-Interpreter. Analysiere Anfragen und erstelle passende Operationen. Antworte nur mit JSON.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=AI_TEMPERATURE_MEDIUM,  # Slightly higher for more creative interpretations
            max_tokens=MAX_TOKENS_WRITE,  # More tokens for complex combined operations
        )

        content = response.choices[0].message.content.strip()
        content = clean_json_response(content)

        parsed = json.loads(content)
        logger.info("Write command interpreted", interpretation=parsed)
        return parsed

    except ValueError:
        raise
    except Exception as e:
        logger.error("Failed to interpret write command", error=str(e))
        raise RuntimeError(f"KI-Service Fehler: Command-Interpretation fehlgeschlagen - {str(e)}")


async def detect_compound_query(question: str, session: Optional[AsyncSession] = None) -> Dict[str, Any]:
    """Use AI to detect if the query is a compound query (UND-Abfrage).

    A compound query requests multiple distinct datasets or visualizations
    that should be displayed separately (e.g., "show table AND line chart").

    Args:
        question: The natural language query
        session: Database session for loading types

    Returns:
        Dict with:
        - is_compound: bool - whether this is a compound query
        - reasoning: str - explanation for the decision
        - sub_queries: List[Dict] - decomposed sub-queries if compound

    Raises:
        ValueError: If Azure OpenAI is not configured, session is missing, or query is invalid
        RuntimeError: If detection fails
    """
    # Validate and sanitize input
    sanitized_question = _validate_and_sanitize_query(question)

    client = get_openai_client()

    if not session:
        raise ValueError("Database session is required for compound query detection")

    try:
        # Load types for context
        facet_types, entity_types = await load_facet_and_entity_types(session)

        # Build prompt (imported at module level)
        prompt = build_compound_query_prompt(
            entity_types=entity_types,
            facet_types=facet_types,
            query=sanitized_question,
        )

        logger.debug(
            "Detecting compound query",
            question=question[:100],
            entity_count=len(entity_types),
            facet_count=len(facet_types),
        )

        response = client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[
                {
                    "role": "system",
                    "content": "Du analysierst Benutzeranfragen und erkennst ob sie mehrere separate Datenabfragen enthalten. Antworte nur mit JSON.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=AI_TEMPERATURE_LOW,
            max_tokens=MAX_TOKENS_COMPOUND,
        )

        content = response.choices[0].message.content.strip()
        content = clean_json_response(content)

        parsed = json.loads(content)

        logger.info(
            "Compound query detection complete",
            is_compound=parsed.get("is_compound"),
            sub_query_count=len(parsed.get("sub_queries", [])),
            reasoning=parsed.get("reasoning", "")[:100],
        )

        return parsed

    except ValueError:
        raise
    except Exception as e:
        logger.error("Failed to detect compound query", error=str(e), exc_info=True)
        # Return non-compound as fallback
        return {
            "is_compound": False,
            "reasoning": f"Detection failed: {str(e)}",
            "sub_queries": [],
        }


async def interpret_plan_query(
    question: str,
    session: AsyncSession,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Interpret a plan mode query using Claude Opus.

    The Plan Mode is an interactive assistant that helps users formulate
    the correct prompts for Smart Query. It uses conversation history
    to maintain context across multiple exchanges.

    Args:
        question: The user's current message
        session: Database session for loading types
        conversation_history: List of previous messages [{"role": "user"|"assistant", "content": "..."}]

    Returns:
        Dict with:
        - success: bool - whether the request was successful
        - message: str - the assistant's response
        - has_generated_prompt: bool - whether a ready-to-use prompt was generated
        - generated_prompt: str | None - the generated prompt if available
        - suggested_mode: "read" | "write" | None - which mode to use for the prompt

    Raises:
        ValueError: If session is missing
        RuntimeError: If plan mode interpretation fails
    """
    if not session:
        raise ValueError("Database session is required for plan mode")

    # Sanitize the current question
    sanitized_question = sanitize_user_input(question)
    if not sanitized_question:
        return {
            "success": False,
            "message": "Die Anfrage ist ungültig oder leer.",
            "has_generated_prompt": False,
            "generated_prompt": None,
            "suggested_mode": None,
        }

    try:
        # Load all types from database
        entity_types, facet_types, relation_types, categories = await load_all_types_for_write(session)

        # Build the system prompt with code documentation and DB data
        system_prompt = build_plan_mode_prompt(
            entity_types=entity_types,
            facet_types=facet_types,
            relation_types=relation_types,
            categories=categories,
        )

        logger.debug(
            "Building plan mode prompt",
            entity_count=len(entity_types),
            facet_count=len(facet_types),
            relation_count=len(relation_types),
            category_count=len(categories),
        )

        # Build conversation messages with sanitized input
        # Note: conversation_history will be sanitized in call_claude_for_plan_mode
        messages = conversation_history or []
        # Add the current sanitized user message
        messages = messages + [{"role": "user", "content": sanitized_question}]

        # Try Claude Opus first
        response_text = await call_claude_for_plan_mode(
            system_prompt=system_prompt,
            messages=messages,
        )

        # Fallback to OpenAI if Claude is not available
        if response_text is None:
            logger.info("Falling back to OpenAI for plan mode")
            client = get_openai_client()

            # Build OpenAI messages
            openai_messages = [
                {"role": "system", "content": system_prompt},
            ]
            for msg in messages:
                openai_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })

            response = client.chat.completions.create(
                model=settings.azure_openai_deployment_name,
                messages=openai_messages,
                temperature=AI_TEMPERATURE_MEDIUM,
                max_tokens=MAX_TOKENS_PLAN_MODE,
            )
            response_text = response.choices[0].message.content.strip()

        # Analyze the response to detect if a prompt was generated
        has_generated_prompt = False
        generated_prompt = None
        suggested_mode = None

        # Look for the "Fertiger Prompt:" pattern in the response
        if "**Fertiger Prompt:**" in response_text or "**Modus:**" in response_text:
            has_generated_prompt = True

            # Extract the prompt (between > markers or after "Fertiger Prompt:")
            import re

            # Try to find prompt in blockquote format
            prompt_match = re.search(r'>\s*(.+?)(?:\n\n|\n\*\*)', response_text, re.DOTALL)
            if prompt_match:
                generated_prompt = prompt_match.group(1).strip()

            # Detect suggested mode
            if "Lese-Modus" in response_text or "Read" in response_text:
                suggested_mode = "read"
            elif "Schreib-Modus" in response_text or "Write" in response_text:
                suggested_mode = "write"

        logger.info(
            "Plan mode query interpreted",
            has_prompt=has_generated_prompt,
            suggested_mode=suggested_mode,
            response_length=len(response_text),
        )

        return {
            "success": True,
            "message": response_text,
            "has_generated_prompt": has_generated_prompt,
            "generated_prompt": generated_prompt,
            "suggested_mode": suggested_mode,
        }

    except ValueError:
        raise
    except Exception as e:
        logger.error("Failed to interpret plan query", error=str(e), exc_info=True)
        raise RuntimeError(f"Plan-Modus Fehler: {str(e)}")


async def interpret_plan_query_stream(
    question: str,
    session: AsyncSession,
    conversation_history: Optional[List[Dict[str, str]]] = None,
):
    """Interpret a plan mode query with streaming response.

    Yields SSE-formatted events as the response is generated.

    Args:
        question: The user's current message
        session: Database session for loading types
        conversation_history: List of previous messages

    Yields:
        SSE-formatted strings for streaming response
    """
    import json as json_module

    if not session:
        yield f"data: {json_module.dumps({'event': SSE_EVENT_ERROR, 'data': 'Database session required'})}\n\n"
        return

    # Sanitize the current question
    sanitized_question = sanitize_user_input(question)
    if not sanitized_question:
        yield f"data: {json_module.dumps({'event': SSE_EVENT_ERROR, 'data': 'Invalid or empty query'})}\n\n"
        return

    try:
        # Load all types from database
        entity_types, facet_types, relation_types, categories = await load_all_types_for_write(session)

        # Build the system prompt
        system_prompt = build_plan_mode_prompt(
            entity_types=entity_types,
            facet_types=facet_types,
            relation_types=relation_types,
            categories=categories,
        )

        logger.debug(
            "Starting plan mode streaming",
            entity_count=len(entity_types),
            facet_count=len(facet_types),
        )

        # Build conversation messages with sanitized input
        # Note: conversation_history will be further sanitized in call_claude_for_plan_mode_stream
        messages = conversation_history or []
        messages = messages + [{"role": "user", "content": sanitized_question}]

        # Stream the response
        async for event in call_claude_for_plan_mode_stream(
            system_prompt=system_prompt,
            messages=messages,
        ):
            yield event

    except Exception as e:
        logger.error("Failed to stream plan query", error=str(e), exc_info=True)
        yield f"data: {json_module.dumps({'event': SSE_EVENT_ERROR, 'data': str(e)})}\n\n"
