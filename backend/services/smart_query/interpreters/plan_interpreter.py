"""Plan mode interpretation for Smart Query Service.

This module handles the Plan Mode - an interactive assistant that helps users
formulate the correct prompts for Smart Query operations.
"""

import json as json_module
import time
from typing import Any, Dict, List, Optional

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from ..prompts import build_plan_mode_prompt
from .base import (
    AI_TEMPERATURE_MEDIUM,
    MAX_TOKENS_PLAN_MODE,
    STREAMING_CONNECT_TIMEOUT,
    STREAMING_READ_TIMEOUT,
    STREAMING_TOTAL_TIMEOUT,
    SSE_EVENT_START,
    SSE_EVENT_CHUNK,
    SSE_EVENT_DONE,
    SSE_EVENT_ERROR,
    get_openai_client,
    sanitize_user_input,
    sanitize_conversation_messages,
    load_all_types_for_write,
)

logger = structlog.get_logger()


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
    import re

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


__all__ = [
    "call_claude_for_plan_mode_stream",
    "call_claude_for_plan_mode",
    "interpret_plan_query",
    "interpret_plan_query_stream",
]
