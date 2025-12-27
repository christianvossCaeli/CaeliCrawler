"""Write command interpretation for Smart Query Service.

This module handles the interpretation of write commands in natural language
into structured operation parameters.
"""

import json
from typing import Any, Dict, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from ..prompts import build_dynamic_write_prompt
from ..utils import clean_json_response
from .base import (
    AI_TEMPERATURE_MEDIUM,
    MAX_TOKENS_WRITE,
    get_openai_client,
    validate_and_sanitize_query,
    load_all_types_for_write,
)

logger = structlog.get_logger()


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
    sanitized_question = validate_and_sanitize_query(question)

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


__all__ = [
    "interpret_write_command",
]
