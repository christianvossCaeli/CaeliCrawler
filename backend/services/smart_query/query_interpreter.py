"""Query interpretation for Smart Query Service - AI-powered NLP query parsing."""

import json
import os
import re
from typing import Any, Dict, Optional

import structlog
from openai import AzureOpenAI

from .prompts import QUERY_INTERPRETATION_PROMPT, WRITE_INTERPRETATION_PROMPT
from .utils import clean_json_response

logger = structlog.get_logger()

# Azure OpenAI client - initialized lazily
_client = None


def get_openai_client() -> Optional[AzureOpenAI]:
    """Get or create the Azure OpenAI client."""
    global _client
    if _client is None and os.getenv("AZURE_OPENAI_API_KEY"):
        _client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        )
    return _client


async def interpret_query(question: str) -> Optional[Dict[str, Any]]:
    """Use AI to interpret natural language query into structured query parameters."""
    client = get_openai_client()
    if not client:
        logger.warning("Azure OpenAI client not configured")
        return None

    try:
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1-mini"),
            messages=[
                {
                    "role": "system",
                    "content": "Du bist ein präziser Query-Interpreter. Antworte nur mit JSON.",
                },
                {
                    "role": "user",
                    "content": QUERY_INTERPRETATION_PROMPT.format(query=question),
                },
            ],
            temperature=0.1,
            max_tokens=1000,
        )

        content = response.choices[0].message.content.strip()
        logger.debug("AI raw response", content=content[:200] if content else "empty")

        content = clean_json_response(content)
        logger.debug("AI cleaned response", content=content[:200] if content else "empty")

        parsed = json.loads(content)
        logger.info("Query interpreted successfully", interpretation=parsed)
        return parsed

    except Exception as e:
        logger.error("Failed to interpret query", error=str(e), exc_info=True)
        return None


async def interpret_write_command(question: str) -> Optional[Dict[str, Any]]:
    """Use AI to interpret if the question is a write command."""
    client = get_openai_client()
    if not client:
        return None

    try:
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1-mini"),
            messages=[
                {
                    "role": "system",
                    "content": "Du bist ein präziser Command-Interpreter. Antworte nur mit JSON.",
                },
                {
                    "role": "user",
                    "content": WRITE_INTERPRETATION_PROMPT.format(query=question),
                },
            ],
            temperature=0.1,
            max_tokens=1500,
        )

        content = response.choices[0].message.content.strip()
        content = clean_json_response(content)

        parsed = json.loads(content)
        logger.info("Write command interpreted", interpretation=parsed)
        return parsed

    except Exception as e:
        logger.error("Failed to interpret write command", error=str(e))
        return None


def fallback_interpret(question: str) -> Dict[str, Any]:
    """Simple keyword-based fallback interpretation."""
    question_lower = question.lower()

    params = {
        "primary_entity_type": "person",
        "facet_types": [],
        "time_filter": "all",
        "filters": {},
        "result_grouping": "flat",
        "explanation": "Fallback interpretation based on keywords",
    }

    # Detect entity type
    if "event" in question_lower or "veranstaltung" in question_lower or "konferenz" in question_lower:
        params["facet_types"].append("event_attendance")
        params["result_grouping"] = "by_event"

    # Detect time filter
    if "künftig" in question_lower or "zukunft" in question_lower or "future" in question_lower:
        params["time_filter"] = "future_only"
    elif "vergangen" in question_lower or "past" in question_lower:
        params["time_filter"] = "past_only"

    # Detect position filters
    position_keywords = []
    if "bürgermeister" in question_lower:
        position_keywords.append("Bürgermeister")
    if "landrat" in question_lower:
        position_keywords.append("Landrat")
    if "entscheider" in question_lower:
        position_keywords.extend(["Bürgermeister", "Landrat", "Dezernent", "Amtsleiter"])

    if position_keywords:
        params["filters"]["position_keywords"] = position_keywords

    # Default time range
    params["filters"]["date_range_days"] = 90

    return params
