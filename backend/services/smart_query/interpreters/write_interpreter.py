"""Write command interpretation for Smart Query Service.

This module handles the interpretation of write commands in natural language
into structured operation parameters.
"""

import json
import time
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AIInterpretationError, SessionRequiredError
from app.models.llm_usage import LLMTaskType
from app.models.user_api_credentials import LLMPurpose
from services.llm_client_service import LLMClientService
from services.llm_usage_tracker import record_llm_usage

from ..prompts import build_dynamic_write_prompt
from ..utils import clean_json_response
from .base import (
    AI_TEMPERATURE_MEDIUM,
    MAX_TOKENS_WRITE,
    load_all_types_for_write,
    validate_and_sanitize_query,
)

logger = structlog.get_logger()


async def interpret_write_command(question: str, session: AsyncSession | None = None) -> dict[str, Any]:
    """Use AI to interpret if the question is a write command.

    Args:
        question: The natural language command
        session: Database session for dynamic prompt generation and LLM credentials (required)

    Raises:
        ValueError: If LLM is not configured, session is missing, or query is invalid
        RuntimeError: If command interpretation fails
    """
    # Validate and sanitize input
    sanitized_question = validate_and_sanitize_query(question)

    if not session:
        raise SessionRequiredError("write command interpretation")

    # Get LLM client
    llm_service = LLMClientService(session)
    client, config = await llm_service.get_system_client(LLMPurpose.DOCUMENT_ANALYSIS)
    if not client or not config:
        raise ValueError("No LLM credentials configured")

    model_name = llm_service.get_model_name(config)
    provider = llm_service.get_provider(config)

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

        start_time = time.time()
        response = await client.chat.completions.create(
            model=model_name,
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

        if response.usage:
            await record_llm_usage(
                provider=provider,
                model=model_name,
                task_type=LLMTaskType.CHAT,
                task_name="interpret_write_command",
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                duration_ms=int((time.time() - start_time) * 1000),
                is_error=False,
            )

        content = response.choices[0].message.content.strip()
        content = clean_json_response(content)

        parsed = json.loads(content)
        logger.info("Write command interpreted", interpretation=parsed)
        return parsed

    except (SessionRequiredError, AIInterpretationError):
        raise
    except Exception as e:
        logger.error("Failed to interpret write command", error=str(e))
        raise AIInterpretationError("Command-Interpretation", detail=str(e)) from None


__all__ = [
    "interpret_write_command",
]
