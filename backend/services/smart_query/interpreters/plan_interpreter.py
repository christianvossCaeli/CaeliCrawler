"""Plan mode interpretation for Smart Query Service.

This module handles the Plan Mode - an interactive assistant that helps users
formulate the correct prompts for Smart Query operations.
"""

import json as json_module
import time
from typing import Any
from uuid import UUID

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AIInterpretationError, SessionRequiredError
from app.models.llm_usage import LLMProvider, LLMTaskType
from app.models.user_api_credentials import LLMPurpose
from services.credentials_resolver import get_anthropic_compatible_config
from services.llm_client_service import LLMClientService
from services.llm_usage_tracker import estimate_tokens, record_llm_usage

from ..prompts import build_plan_mode_prompt
from .base import (
    AI_TEMPERATURE_MEDIUM,
    MAX_TOKENS_PLAN_MODE,
    SSE_EVENT_CHUNK,
    SSE_EVENT_DONE,
    SSE_EVENT_ERROR,
    SSE_EVENT_START,
    STREAMING_CONNECT_TIMEOUT,
    STREAMING_READ_TIMEOUT,
    STREAMING_TOTAL_TIMEOUT,
    load_all_types_for_write,
    sanitize_conversation_messages,
    sanitize_user_input,
)

logger = structlog.get_logger()


async def call_claude_for_plan_mode_stream(
    system_prompt: str,
    messages: list[dict[str, str]],
    session: AsyncSession,
    max_tokens: int = MAX_TOKENS_PLAN_MODE,
):
    """Call Claude Opus for Plan Mode with streaming response.

    Yields SSE-formatted events as the response is generated.
    Uses database-stored Anthropic credentials.

    Args:
        system_prompt: The system prompt with Smart Query documentation
        messages: Conversation history as list of {"role": "user"|"assistant", "content": "..."}
        session: Database session for loading credentials
        max_tokens: Maximum tokens in response

    Yields:
        SSE-formatted strings: data: {"event": "...", "data": "..."}
        Returns early with 'anthropic_not_configured' event if no Anthropic credentials found.
    """
    # Load Anthropic credentials from database
    llm_service = LLMClientService(session)
    admin_user = await llm_service._get_admin_with_credentials()

    anthropic_config = None
    if admin_user:
        anthropic_config = await get_anthropic_compatible_config(
            session, admin_user.id, LLMPurpose.PLAN_MODE
        )

    if not anthropic_config:
        logger.info("Claude API not configured in DB, will use fallback")
        yield f"data: {json_module.dumps({'event': 'anthropic_not_configured'})}\n\n"
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

    # Build endpoint URL
    endpoint = anthropic_config["endpoint"].rstrip("/")
    if not endpoint.endswith("/messages"):
        endpoint = f"{endpoint}/v1/messages"

    try:
        async with httpx.AsyncClient(timeout=timeout_config) as client:  # noqa: SIM117
            async with client.stream(
                "POST",
                endpoint,
                headers={
                    "api-key": anthropic_config["api_key"],
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": anthropic_config["model"],
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
    messages: list[dict[str, str]],
    session: AsyncSession,
    max_tokens: int = MAX_TOKENS_PLAN_MODE,
    user_id: UUID | None = None,
) -> str | None:
    """Call Claude Opus for Plan Mode with conversation history.

    Uses database-stored Anthropic credentials.

    Args:
        system_prompt: The system prompt with Smart Query documentation
        messages: Conversation history as list of {"role": "user"|"assistant", "content": "..."}
        session: Database session for loading credentials
        max_tokens: Maximum tokens in response
        user_id: Optional user ID for tracking

    Returns:
        Response content or None if Anthropic not configured (fallback to OpenAI)
    """
    # Load Anthropic credentials from database
    llm_service = LLMClientService(session)
    admin_user = await llm_service._get_admin_with_credentials()

    anthropic_config = None
    if admin_user:
        anthropic_config = await get_anthropic_compatible_config(
            session, admin_user.id, LLMPurpose.PLAN_MODE
        )

    if not anthropic_config:
        logger.info("Claude API not configured in DB, falling back to OpenAI")
        return None

    # Sanitize and limit conversation history using comprehensive sanitization
    sanitized_messages = sanitize_conversation_messages(messages)

    if not sanitized_messages:
        logger.warning("No valid messages after sanitization")
        return None

    start_time = time.time()
    is_error = False
    error_message = None
    prompt_tokens = 0
    completion_tokens = 0
    response_text = None
    model_name = anthropic_config["model"]

    # Build endpoint URL
    endpoint = anthropic_config["endpoint"].rstrip("/")
    if not endpoint.endswith("/messages"):
        endpoint = f"{endpoint}/v1/messages"

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                endpoint,
                headers={
                    "api-key": anthropic_config["api_key"],
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": model_name,
                    "max_tokens": max_tokens,
                    "system": system_prompt,
                    "messages": sanitized_messages,
                },
            )
            response.raise_for_status()
            data = response.json()

            # Extract token usage from Claude response
            usage = data.get("usage", {})
            prompt_tokens = usage.get("input_tokens", 0)
            completion_tokens = usage.get("output_tokens", 0)

            # Extract content from Claude response
            if "content" in data and len(data["content"]) > 0:
                response_text = data["content"][0].get("text", "")
            else:
                logger.warning("Claude API returned empty content")

    except httpx.TimeoutException:
        logger.error("Claude API request timed out after 120 seconds")
        is_error = True
        error_message = "Request timed out after 120 seconds"
    except httpx.HTTPStatusError as e:
        logger.error(
            "Claude API HTTP error",
            status_code=e.response.status_code,
            detail=e.response.text[:500] if e.response.text else None,
        )
        is_error = True
        error_message = f"HTTP error: {e.response.status_code}"
    except httpx.HTTPError as e:
        logger.error("Claude API request failed", error=str(e))
        is_error = True
        error_message = str(e)
    except Exception as e:
        logger.error("Claude API unexpected error", error=str(e), exc_info=True)
        is_error = True
        error_message = str(e)

    # Record LLM usage
    duration_ms = int((time.time() - start_time) * 1000)

    # Estimate tokens if not provided by API
    if prompt_tokens == 0:
        prompt_tokens = estimate_tokens(system_prompt) + sum(
            estimate_tokens(m.get("content", "")) for m in sanitized_messages
        )
    if completion_tokens == 0 and response_text:
        completion_tokens = estimate_tokens(response_text)

    try:
        await record_llm_usage(
            provider=LLMProvider.ANTHROPIC,
            model=model_name,
            task_type=LLMTaskType.PLAN_MODE,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            task_name="smart_query_plan_mode",
            user_id=user_id,
            duration_ms=duration_ms,
            is_error=is_error,
            error_message=error_message,
        )
    except Exception as e:
        logger.warning("Failed to record LLM usage", error=str(e))

    return response_text


async def interpret_plan_query(
    question: str,
    session: AsyncSession,
    conversation_history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
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
        raise SessionRequiredError("plan mode")

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
            session=session,
        )

        # Fallback to OpenAI if Claude is not available
        if response_text is None:
            logger.info("Falling back to OpenAI for plan mode")

            # Get LLM client
            llm_service = LLMClientService(session)
            client, config = await llm_service.get_system_client(LLMPurpose.DOCUMENT_ANALYSIS)
            if not client or not config:
                raise ValueError("No LLM credentials configured")

            model_name = llm_service.get_model_name(config)
            provider = llm_service.get_provider(config)

            # Build OpenAI messages
            openai_messages = [
                {"role": "system", "content": system_prompt},
            ]
            for msg in messages:
                openai_messages.append(
                    {
                        "role": msg["role"],
                        "content": msg["content"],
                    }
                )

            start_time = time.time()
            response = await client.chat.completions.create(
                model=model_name,
                messages=openai_messages,
                temperature=AI_TEMPERATURE_MEDIUM,
                max_tokens=MAX_TOKENS_PLAN_MODE,
            )

            if response.usage:
                await record_llm_usage(
                    provider=provider,
                    model=model_name,
                    task_type=LLMTaskType.PLAN_MODE,
                    task_name="interpret_plan_query_openai_fallback",
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                    duration_ms=int((time.time() - start_time) * 1000),
                    is_error=False,
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
            prompt_match = re.search(r">\s*(.+?)(?:\n\n|\n\*\*)", response_text, re.DOTALL)
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

    except (SessionRequiredError, AIInterpretationError):
        raise
    except Exception as e:
        logger.error("Failed to interpret plan query", error=str(e), exc_info=True)
        raise AIInterpretationError("Plan-Modus", detail=str(e)) from None


async def interpret_plan_query_stream(
    question: str,
    session: AsyncSession,
    conversation_history: list[dict[str, str]] | None = None,
    page_context: dict | None = None,
):
    """Interpret a plan mode query with streaming response.

    Yields SSE-formatted events as the response is generated.

    Args:
        question: The user's current message
        session: Database session for loading types
        conversation_history: List of previous messages
        page_context: Optional dict with current page context for context-aware responses

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

        # Build the system prompt with optional page context
        system_prompt = build_plan_mode_prompt(
            entity_types=entity_types,
            facet_types=facet_types,
            relation_types=relation_types,
            categories=categories,
            page_context=page_context,
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

        # Try Claude first, with fallback detection
        use_openai_fallback = False
        async for event in call_claude_for_plan_mode_stream(
            system_prompt=system_prompt,
            messages=messages,
            session=session,
        ):
            # Check if Anthropic is not configured
            if "anthropic_not_configured" in event:
                use_openai_fallback = True
                break
            yield event

        # Fallback to OpenAI streaming if Anthropic not configured
        if use_openai_fallback:
            logger.info("Using OpenAI fallback for plan mode streaming")

            llm_service = LLMClientService(session)
            client, config = await llm_service.get_system_client(LLMPurpose.PLAN_MODE)

            if not client or not config:
                yield f"data: {json_module.dumps({'event': SSE_EVENT_ERROR, 'data': 'No LLM credentials configured'})}\n\n"
                return

            model_name = llm_service.get_model_name(config)

            # Build OpenAI messages
            openai_messages = [{"role": "system", "content": system_prompt}]
            for msg in messages:
                openai_messages.append({"role": msg["role"], "content": msg["content"]})

            # Signal start of streaming
            yield f"data: {json_module.dumps({'event': SSE_EVENT_START})}\n\n"

            try:
                stream = await client.chat.completions.create(
                    model=model_name,
                    messages=openai_messages,
                    temperature=AI_TEMPERATURE_MEDIUM,
                    max_tokens=MAX_TOKENS_PLAN_MODE,
                    stream=True,
                )

                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        text = chunk.choices[0].delta.content
                        yield f"data: {json_module.dumps({'event': SSE_EVENT_CHUNK, 'data': text})}\n\n"

                yield f"data: {json_module.dumps({'event': SSE_EVENT_DONE})}\n\n"

            except Exception as e:
                logger.error("OpenAI streaming failed", error=str(e))
                yield f"data: {json_module.dumps({'event': SSE_EVENT_ERROR, 'data': str(e)})}\n\n"

    except Exception as e:
        logger.error("Failed to stream plan query", error=str(e), exc_info=True)
        yield f"data: {json_module.dumps({'event': SSE_EVENT_ERROR, 'data': str(e)})}\n\n"


__all__ = [
    "call_claude_for_plan_mode_stream",
    "call_claude_for_plan_mode",
    "interpret_plan_query",
    "interpret_plan_query_stream",
]
