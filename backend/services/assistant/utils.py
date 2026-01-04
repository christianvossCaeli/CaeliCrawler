"""Assistant Service - Utility Functions."""

import structlog

logger = structlog.get_logger()


def format_entity_link(entity_type: str, slug: str, name: str) -> str:
    """Format an entity reference as a clickable link: [[type:slug:name]]."""
    return f"[[{entity_type}:{slug}:{name}]]"


def extract_json_from_response(response_text: str) -> str | None:
    """Extract JSON from a response that may contain markdown code blocks."""
    import re

    # Try to find JSON in code blocks first
    json_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", response_text)
    if json_match:
        return json_match.group(1)

    # Try to find raw JSON
    json_match = re.search(r"(\{[\s\S]*\})", response_text)
    if json_match:
        return json_match.group(1)

    return None


def truncate_for_prompt(text: str, max_length: int = 2000) -> str:
    """Truncate text for use in prompts to avoid token limits."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "... [truncated]"


def safe_json_loads(text: str, default: dict = None) -> dict:
    """Safely parse JSON with fallback to default."""
    import json

    if default is None:
        default = {}

    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Failed to parse JSON", text=text[:100] if text else None)
        return default


def format_entity_summary(entity: dict) -> str:
    """Format entity data for prompt context."""
    parts = [f"Name: {entity.get('name', 'Unknown')}"]

    if entity.get("description"):
        parts.append(f"Beschreibung: {entity['description']}")

    if entity.get("entity_type"):
        parts.append(f"Typ: {entity['entity_type']}")

    return "\n".join(parts)
