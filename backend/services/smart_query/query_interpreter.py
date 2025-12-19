"""Query interpretation for Smart Query Service - AI-powered NLP query parsing."""

import json
import os
import re
from typing import Any, Dict, List, Optional

import structlog
from openai import AzureOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .prompts import WRITE_INTERPRETATION_PROMPT
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


def build_dynamic_query_prompt(facet_types: List[Dict[str, Any]], entity_types: List[Dict[str, Any]], query: str = "") -> str:
    """Build the query interpretation prompt dynamically with current facet and entity types."""

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

## Time Filter Optionen:
- future_only: Nur zukünftige Einträge
- past_only: Nur vergangene Einträge
- all: Alle Einträge

## Wichtige Positionen (für "Entscheider"):
- Bürgermeister, Oberbürgermeister
- Landrat, Landrätin
- Dezernent, Dezernentin
- Amtsleiter, Amtsleiterin
- Gemeinderat, Stadtrat
- Kämmerer

Analysiere die Benutzeranfrage und gib ein JSON zurück mit:
{{
  "primary_entity_type": "<entity_type_slug>",
  "facet_types": ["facet_slug_1", "facet_slug_2"],
  "time_filter": "future_only|past_only|all",
  "relation_chain": [
    {{"type": "works_for", "direction": "source|target"}}
  ],
  "filters": {{
    "position_keywords": ["Bürgermeister", "Landrat"],
    "location_keywords": ["NRW", "Bayern"],
    "date_range_days": 90
  }},
  "result_grouping": "by_event|by_person|by_municipality|flat",
  "explanation": "Kurze Erklärung was abgefragt wird"
}}

Benutzeranfrage: {query}

Antworte NUR mit validem JSON."""


async def load_facet_and_entity_types(session: AsyncSession) -> tuple[List[Dict], List[Dict]]:
    """Load facet types and entity types from the database."""
    from app.models import FacetType, EntityType

    # Load facet types
    facet_result = await session.execute(
        select(FacetType).where(FacetType.is_active == True).order_by(FacetType.display_order)
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
        select(EntityType).where(EntityType.is_active == True).order_by(EntityType.display_order)
    )
    entity_types = [
        {
            "slug": et.slug,
            "name": et.name,
            "description": et.description,
        }
        for et in entity_result.scalars().all()
    ]

    return facet_types, entity_types


async def interpret_query(question: str, session: Optional[AsyncSession] = None) -> Optional[Dict[str, Any]]:
    """Use AI to interpret natural language query into structured query parameters.

    Args:
        question: The natural language query
        session: Optional database session for dynamic prompt generation
    """
    client = get_openai_client()
    if not client:
        logger.warning("Azure OpenAI client not configured")
        return None

    try:
        # Build prompt dynamically if session is available
        if session:
            facet_types, entity_types = await load_facet_and_entity_types(session)
            prompt = build_dynamic_query_prompt(facet_types, entity_types, query=question)
            logger.debug("Using dynamic prompt with facet_types", facet_count=len(facet_types))
        else:
            # Fallback to static prompt if no session (backwards compatibility)
            from .prompts import QUERY_INTERPRETATION_PROMPT
            prompt = QUERY_INTERPRETATION_PROMPT.format(query=question)
            logger.debug("Using static prompt (no session)")

        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1-mini"),
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
