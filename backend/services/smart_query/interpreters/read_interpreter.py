"""Read query interpretation for Smart Query Service.

This module handles the interpretation of read-only natural language queries
into structured query parameters.
"""

import json
from datetime import date
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from ..prompts import build_compound_query_prompt
from ..utils import clean_json_response
from .base import (
    AI_TEMPERATURE_LOW,
    MAX_TOKENS_QUERY,
    MAX_TOKENS_COMPOUND,
    get_openai_client,
    validate_and_sanitize_query,
    load_facet_and_entity_types,
)

logger = structlog.get_logger()


def build_dynamic_query_prompt(
    facet_types: List[Dict[str, Any]],
    entity_types: List[Dict[str, Any]],
    query: str = "",
) -> str:
    """Build the query interpretation prompt dynamically with current facet and entity types."""
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
    sanitized_question = validate_and_sanitize_query(question)

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
    sanitized_question = validate_and_sanitize_query(question)

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


__all__ = [
    "build_dynamic_query_prompt",
    "interpret_query",
    "detect_compound_query",
]
