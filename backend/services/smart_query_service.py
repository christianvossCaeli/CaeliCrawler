"""Smart Query Service - KI-gestützte natürliche Sprache Abfragen und Datenmanipulation."""

import json
import os
import re
import unicodedata
import uuid as uuid_module
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import structlog
from openai import AzureOpenAI
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Entity,
    EntityType,
    FacetType,
    FacetValue,
    RelationType,
    EntityRelation,
    Category,
    DataSource,
    DataSourceCategory,
)

logger = structlog.get_logger()

# Azure OpenAI client
client = None
if os.getenv("AZURE_OPENAI_API_KEY"):
    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )


# Geographic alias mapping for German Bundesländer
GERMAN_STATE_ALIASES = {
    # Nordrhein-Westfalen
    "nrw": "Nordrhein-Westfalen",
    "nordrhein westfalen": "Nordrhein-Westfalen",
    "nordrhein-westfalen": "Nordrhein-Westfalen",
    # Bayern
    "by": "Bayern",
    "bayern": "Bayern",
    "freistaat bayern": "Bayern",
    # Baden-Württemberg
    "bw": "Baden-Württemberg",
    "baden württemberg": "Baden-Württemberg",
    "baden-württemberg": "Baden-Württemberg",
    # Niedersachsen
    "nds": "Niedersachsen",
    "niedersachsen": "Niedersachsen",
    # Hessen
    "he": "Hessen",
    "hessen": "Hessen",
    # Rheinland-Pfalz
    "rp": "Rheinland-Pfalz",
    "rheinland pfalz": "Rheinland-Pfalz",
    "rheinland-pfalz": "Rheinland-Pfalz",
    # Schleswig-Holstein
    "sh": "Schleswig-Holstein",
    "schleswig holstein": "Schleswig-Holstein",
    "schleswig-holstein": "Schleswig-Holstein",
    # Saarland
    "sl": "Saarland",
    "saarland": "Saarland",
    # Berlin
    "be": "Berlin",
    "berlin": "Berlin",
    # Brandenburg
    "bb": "Brandenburg",
    "brandenburg": "Brandenburg",
    # Mecklenburg-Vorpommern
    "mv": "Mecklenburg-Vorpommern",
    "meck pomm": "Mecklenburg-Vorpommern",
    "mecklenburg vorpommern": "Mecklenburg-Vorpommern",
    "mecklenburg-vorpommern": "Mecklenburg-Vorpommern",
    # Sachsen
    "sn": "Sachsen",
    "sachsen": "Sachsen",
    # Sachsen-Anhalt
    "st": "Sachsen-Anhalt",
    "sachsen anhalt": "Sachsen-Anhalt",
    "sachsen-anhalt": "Sachsen-Anhalt",
    # Thüringen
    "th": "Thüringen",
    "thüringen": "Thüringen",
    # Hamburg
    "hh": "Hamburg",
    "hamburg": "Hamburg",
    # Bremen
    "hb": "Bremen",
    "bremen": "Bremen",
}


def resolve_geographic_alias(alias: str) -> str:
    """Resolve a geographic alias to its canonical name (e.g., NRW -> Nordrhein-Westfalen)."""
    if not alias:
        return alias
    normalized = alias.lower().strip()
    return GERMAN_STATE_ALIASES.get(normalized, alias)


QUERY_INTERPRETATION_PROMPT = """Du bist ein Query-Interpreter für ein Entity-Facet-System.

## Verfügbare Entity Types:
- municipality: Gemeinden/Städte/Landkreise
- person: Personen (Entscheider, Kontakte)
- organization: Organisationen/Unternehmen/Verbände
- event: Veranstaltungen/Konferenzen/Messen

## Verfügbare Facet Types:
- pain_point: Probleme/Herausforderungen einer Gemeinde
- positive_signal: Chancen/positive Entwicklungen
- contact: Kontaktpersonen einer Gemeinde
- event_attendance: Event-Teilnahmen einer Person (hat time_filter!)
- summary: Zusammenfassungen

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
  "primary_entity_type": "person|municipality|event|organization",
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


# Write operation prompt - detects and parses create/update commands
WRITE_INTERPRETATION_PROMPT = """Du bist ein Command-Interpreter für ein Entity-Facet-System.
Analysiere ob der Benutzer Daten ERSTELLEN oder ÄNDERN möchte.

## Verfügbare Entity Types (Kategorien):
- municipality: Gemeinden/Städte/Landkreise (DE: Gemeinde, Stadt, Kommune)
- person: Personen (DE: Person, Kontakt, Ansprechpartner)
- organization: Organisationen (DE: Organisation, Unternehmen, Verband)
- event: Veranstaltungen (DE: Event, Messe, Konferenz)

## Verfügbare Facet Types:
- pain_point: Probleme/Herausforderungen (DE: Problem, Herausforderung, Hindernis)
- positive_signal: Chancen/positive Signale (DE: Chance, Potenzial, Interesse)
- contact: Kontaktperson (DE: Kontakt, Ansprechpartner)
- event_attendance: Event-Teilnahme (DE: nimmt teil, besucht)
- summary: Zusammenfassung

## Verfügbare Relations:
- works_for: Person arbeitet für Municipality/Organization
- attends: Person nimmt teil an Event
- located_in: Event findet statt in Municipality
- member_of: Person ist Mitglied von Organization

## Verfügbare Operationen:
- create_entity: Einzelne Entity erstellen
- create_entity_type: Neuen Entity-Typ erstellen
- create_facet: Facet zu Entity hinzufügen
- create_relation: Relation zwischen Entities erstellen
- create_category_setup: KOMPLEXE OPERATION - Erstellt EntityType + Category + verknüpft DataSources
- start_crawl: Crawls für DataSources starten
- combined: Mehrere Operationen in einem Befehl

## Befehle erkennen:
- "Erstelle", "Anlegen", "Neue/r/s", "Füge hinzu" → CREATE
- "Aktualisiere", "Ändere", "Setze" → UPDATE
- "Verknüpfe", "Verbinde" → CREATE_RELATION
- "Neuen Entity-Typ", "Neue Kategorie", "Neuen Typ" → CREATE_ENTITY_TYPE
- "Finde alle...", "Suche nach...", "Überwache...", "Crawle..." + geografische Einschränkung → CREATE_CATEGORY_SETUP
- "Starte Crawl", "Crawle", "Führe Crawl aus" → START_CRAWL
- Kombinierte Befehle mit "und dann", "danach", "anschließend" → COMBINED

## CREATE_CATEGORY_SETUP erkennen:
Trigger-Phrasen (kombiniert mit geografischer Einschränkung):
- "Finde bitte alle Events...", "Suche alle Veranstaltungen...", "Überwache Events..."
- Geografische Keywords: "in NRW", "aus Bayern", "von Gemeinden in...", "aus Nordrhein-Westfalen"
- Thematischer Fokus: "Events", "Entscheider", "Veranstaltungen", "Konferenzen"

## Geografische Aliase:
- NRW, Nordrhein Westfalen → Nordrhein-Westfalen
- BW, Baden Württemberg → Baden-Württemberg
- BY, Freistaat Bayern → Bayern
- SH → Schleswig-Holstein
- NDS → Niedersachsen
- HE → Hessen
- RP → Rheinland-Pfalz
- SL → Saarland
- BE → Berlin
- BB → Brandenburg
- MV → Mecklenburg-Vorpommern
- SN → Sachsen
- ST → Sachsen-Anhalt
- TH → Thüringen
- HH → Hamburg
- HB → Bremen

Analysiere die Anfrage und gib JSON zurück:
{{
  "operation": "create_entity|create_entity_type|create_facet|create_relation|create_category_setup|start_crawl|combined|none",
  "entity_type": "municipality|person|organization|event",
  "entity_data": {{
    "name": "Name der Entity",
    "core_attributes": {{"position": "...", "email": "..."}},
    "external_id": "optional"
  }},
  "entity_type_data": {{
    "name": "Name des Entity-Typs (z.B. 'Windpark')",
    "name_plural": "Plural-Form (z.B. 'Windparks')",
    "description": "Beschreibung",
    "icon": "mdi-wind-turbine",
    "color": "#4CAF50",
    "is_primary": true,
    "supports_hierarchy": false
  }},
  "facet_data": {{
    "facet_type": "pain_point|positive_signal|contact|summary",
    "target_entity_name": "Name der Ziel-Entity (z.B. Gemeinde)",
    "value": {{"description": "...", "severity": "high|medium|low"}},
    "text_representation": "Kurze Textdarstellung"
  }},
  "relation_data": {{
    "relation_type": "works_for|attends|located_in|member_of",
    "source_entity_name": "Name der Quell-Entity",
    "source_entity_type": "person|event",
    "target_entity_name": "Name der Ziel-Entity",
    "target_entity_type": "municipality|organization|event"
  }},
  "category_setup_data": {{
    "name": "Vorgeschlagener Name (z.B. 'Event-Besuche NRW')",
    "purpose": "Zweck/Beschreibung",
    "user_intent": "Original-Intent des Users",
    "search_focus": "event_attendance|pain_points|contacts|general",
    "search_terms": ["Begriff1", "Begriff2"],
    "geographic_filter": {{
      "admin_level_1": "Nordrhein-Westfalen",
      "admin_level_1_alias": "NRW",
      "country": "DE"
    }},
    "time_focus": "future_only|past_only|all",
    "target_entity_types": ["person", "event"],
    "extraction_handler": "event|default",
    "suggested_facets": ["event_attendance", "contact"]
  }},
  "crawl_command_data": {{
    "filter_type": "location|category|source_ids|entity_name",
    "location_name": "Ortsname (z.B. Gummersbach)",
    "admin_level_1": "Bundesland (z.B. Nordrhein-Westfalen)",
    "category_slug": "kategorie-slug",
    "source_ids": [],
    "include_all_categories": true
  }},
  "combined_operations": [
    {{"operation": "create_category_setup", "category_setup_data": {{...}}}},
    {{"operation": "start_crawl", "crawl_command_data": {{...}}}}
  ],
  "explanation": "Was wird erstellt/geändert"
}}

Wenn es KEINE Schreib-Operation ist, setze "operation": "none".

## Icons (Material Design Icons - mdi-*):
- Windenergie: mdi-wind-turbine
- Solar: mdi-solar-power
- Gebäude: mdi-office-building
- Projekt: mdi-clipboard-list
- Dokument: mdi-file-document
- Firma: mdi-domain
- Land: mdi-earth
- Technologie: mdi-cog
- Event: mdi-calendar
- Person: mdi-account

## Farben (Hex):
- Grün: #4CAF50
- Blau: #2196F3
- Orange: #FF9800
- Rot: #F44336
- Lila: #9C27B0

Benutzeranfrage: {query}

Antworte NUR mit validem JSON."""


def generate_slug(name: str) -> str:
    """Generate a URL-safe slug from a name."""
    # Normalize unicode characters
    normalized = unicodedata.normalize("NFKD", name)
    # Convert to ASCII
    ascii_str = normalized.encode("ascii", "ignore").decode("ascii")
    # Convert to lowercase and replace spaces/special chars
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_str.lower())
    # Remove leading/trailing hyphens
    return slug.strip("-")


async def create_entity_type_from_command(
    session: AsyncSession,
    entity_type_data: Dict[str, Any],
) -> Tuple[Optional[EntityType], str]:
    """Create a new entity type from smart query command."""
    name = entity_type_data.get("name", "").strip()
    if not name:
        return None, "Name ist erforderlich"

    slug = generate_slug(name)

    # Check for duplicates
    existing = await session.execute(
        select(EntityType).where(
            or_(EntityType.name == name, EntityType.slug == slug)
        )
    )
    if existing.scalar():
        return None, f"Entity-Typ '{name}' existiert bereits"

    # Create entity type
    entity_type = EntityType(
        id=uuid_module.uuid4(),
        name=name,
        slug=slug,
        name_plural=entity_type_data.get("name_plural", f"{name}s"),
        description=entity_type_data.get("description"),
        icon=entity_type_data.get("icon", "mdi-folder"),
        color=entity_type_data.get("color", "#4CAF50"),
        is_primary=entity_type_data.get("is_primary", True),
        supports_hierarchy=entity_type_data.get("supports_hierarchy", False),
        hierarchy_config=entity_type_data.get("hierarchy_config"),
        attribute_schema=entity_type_data.get("attribute_schema"),
        display_order=10,  # Default order
        is_active=True,
        is_system=False,
    )
    session.add(entity_type)
    await session.flush()

    return entity_type, f"Entity-Typ '{name}' erstellt"


async def find_entity_by_name(
    session: AsyncSession,
    name: str,
    entity_type_slug: Optional[str] = None,
) -> Optional[Entity]:
    """Find an entity by name (case-insensitive)."""
    query = select(Entity).where(
        Entity.name.ilike(f"%{name}%"),
        Entity.is_active == True,
    )
    if entity_type_slug:
        entity_type_result = await session.execute(
            select(EntityType).where(EntityType.slug == entity_type_slug)
        )
        entity_type = entity_type_result.scalar_one_or_none()
        if entity_type:
            query = query.where(Entity.entity_type_id == entity_type.id)

    result = await session.execute(query.limit(1))
    return result.scalar_one_or_none()


async def create_entity_from_command(
    session: AsyncSession,
    entity_type_slug: str,
    entity_data: Dict[str, Any],
) -> Tuple[Entity, str]:
    """Create a new entity from smart query command."""
    # Get entity type
    entity_type_result = await session.execute(
        select(EntityType).where(EntityType.slug == entity_type_slug)
    )
    entity_type = entity_type_result.scalar_one_or_none()
    if not entity_type:
        return None, f"Entity-Typ '{entity_type_slug}' nicht gefunden"

    name = entity_data.get("name", "").strip()
    if not name:
        return None, "Name ist erforderlich"

    slug = generate_slug(name)

    # Check for duplicates
    existing = await session.execute(
        select(Entity).where(
            Entity.entity_type_id == entity_type.id,
            or_(Entity.name == name, Entity.slug == slug),
        )
    )
    if existing.scalar():
        return None, f"Entity '{name}' existiert bereits"

    # Create entity
    name_normalized = unicodedata.normalize("NFKD", name.lower())
    entity = Entity(
        id=uuid_module.uuid4(),
        entity_type_id=entity_type.id,
        name=name,
        name_normalized=name_normalized,
        slug=slug,
        external_id=entity_data.get("external_id"),
        hierarchy_path=f"/{slug}",
        hierarchy_level=0,
        core_attributes=entity_data.get("core_attributes", {}),
        is_active=True,
    )
    session.add(entity)
    await session.flush()

    return entity, f"Entity '{name}' ({entity_type.name}) erstellt"


async def create_facet_from_command(
    session: AsyncSession,
    facet_data: Dict[str, Any],
) -> Tuple[Optional[FacetValue], str]:
    """Create a new facet value from smart query command."""
    facet_type_slug = facet_data.get("facet_type")
    target_name = facet_data.get("target_entity_name")

    if not facet_type_slug or not target_name:
        return None, "Facet-Typ und Ziel-Entity sind erforderlich"

    # Find facet type
    facet_type_result = await session.execute(
        select(FacetType).where(FacetType.slug == facet_type_slug)
    )
    facet_type = facet_type_result.scalar_one_or_none()
    if not facet_type:
        return None, f"Facet-Typ '{facet_type_slug}' nicht gefunden"

    # Find target entity
    target_entity = await find_entity_by_name(session, target_name)
    if not target_entity:
        return None, f"Entity '{target_name}' nicht gefunden"

    # Create facet value
    facet_value = FacetValue(
        id=uuid_module.uuid4(),
        entity_id=target_entity.id,
        facet_type_id=facet_type.id,
        value=facet_data.get("value", {}),
        text_representation=facet_data.get("text_representation", ""),
        confidence_score=0.9,  # Manual entry = high confidence
        is_active=True,
    )
    session.add(facet_value)
    await session.flush()

    return facet_value, f"Facet '{facet_type.name}' für '{target_entity.name}' erstellt"


async def create_relation_from_command(
    session: AsyncSession,
    relation_data: Dict[str, Any],
) -> Tuple[Optional[EntityRelation], str]:
    """Create a new entity relation from smart query command."""
    relation_type_slug = relation_data.get("relation_type")
    source_name = relation_data.get("source_entity_name")
    source_type = relation_data.get("source_entity_type")
    target_name = relation_data.get("target_entity_name")
    target_type = relation_data.get("target_entity_type")

    if not all([relation_type_slug, source_name, target_name]):
        return None, "Relation-Typ, Quell- und Ziel-Entity sind erforderlich"

    # Find relation type
    relation_type_result = await session.execute(
        select(RelationType).where(RelationType.slug == relation_type_slug)
    )
    relation_type = relation_type_result.scalar_one_or_none()
    if not relation_type:
        return None, f"Relation-Typ '{relation_type_slug}' nicht gefunden"

    # Find source entity
    source_entity = await find_entity_by_name(session, source_name, source_type)
    if not source_entity:
        return None, f"Quell-Entity '{source_name}' nicht gefunden"

    # Find target entity
    target_entity = await find_entity_by_name(session, target_name, target_type)
    if not target_entity:
        return None, f"Ziel-Entity '{target_name}' nicht gefunden"

    # Check for existing relation
    existing = await session.execute(
        select(EntityRelation).where(
            EntityRelation.source_entity_id == source_entity.id,
            EntityRelation.target_entity_id == target_entity.id,
            EntityRelation.relation_type_id == relation_type.id,
        )
    )
    if existing.scalar():
        return None, f"Relation '{source_entity.name}' → '{target_entity.name}' existiert bereits"

    # Create relation
    relation = EntityRelation(
        id=uuid_module.uuid4(),
        source_entity_id=source_entity.id,
        target_entity_id=target_entity.id,
        relation_type_id=relation_type.id,
        is_active=True,
    )
    session.add(relation)
    await session.flush()

    return relation, f"Relation '{source_entity.name}' → '{target_entity.name}' ({relation_type.name}) erstellt"


async def interpret_write_command(question: str) -> Optional[Dict[str, Any]]:
    """Use AI to interpret if the question is a write command."""
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

        # Clean up markdown code blocks
        if "```" in content:
            match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
            if match:
                content = match.group(1)
            else:
                content = content.replace("```json", "").replace("```", "")
        content = content.strip()

        parsed = json.loads(content)
        logger.info("Write command interpreted", interpretation=parsed)
        return parsed

    except Exception as e:
        logger.error("Failed to interpret write command", error=str(e))
        return None


async def execute_write_command(
    session: AsyncSession,
    command: Dict[str, Any],
    current_user_id: Optional[UUID] = None,
) -> Dict[str, Any]:
    """Execute a write command and return the result."""
    operation = command.get("operation", "none")

    if operation == "none":
        return {"success": False, "message": "Keine Schreib-Operation erkannt"}

    result = {
        "success": False,
        "operation": operation,
        "message": "",
        "created_items": [],
    }

    try:
        if operation == "create_entity":
            entity_type = command.get("entity_type", "municipality")
            entity_data = command.get("entity_data", {})
            entity, message = await create_entity_from_command(session, entity_type, entity_data)
            result["message"] = message
            if entity:
                result["success"] = True
                result["created_items"].append({
                    "type": "entity",
                    "id": str(entity.id),
                    "name": entity.name,
                    "entity_type": entity_type,
                })

        elif operation == "create_facet":
            facet_data = command.get("facet_data", {})
            facet, message = await create_facet_from_command(session, facet_data)
            result["message"] = message
            if facet:
                result["success"] = True
                result["created_items"].append({
                    "type": "facet_value",
                    "id": str(facet.id),
                    "facet_type": facet_data.get("facet_type"),
                })

        elif operation == "create_relation":
            relation_data = command.get("relation_data", {})
            relation, message = await create_relation_from_command(session, relation_data)
            result["message"] = message
            if relation:
                result["success"] = True
                result["created_items"].append({
                    "type": "relation",
                    "id": str(relation.id),
                })

        elif operation == "create_entity_type":
            entity_type_data = command.get("entity_type_data", {})
            # Add ownership if user is provided
            if current_user_id:
                entity_type_data["created_by_id"] = current_user_id
                entity_type_data["owner_id"] = current_user_id
                entity_type_data.setdefault("is_public", False)
            entity_type, message = await create_entity_type_from_command(session, entity_type_data)
            result["message"] = message
            if entity_type:
                result["success"] = True
                result["created_items"].append({
                    "type": "entity_type",
                    "id": str(entity_type.id),
                    "name": entity_type.name,
                    "slug": entity_type.slug,
                    "icon": entity_type.icon,
                    "color": entity_type.color,
                })

        elif operation == "create_category_setup":
            setup_data = command.get("category_setup_data", {})
            user_intent = setup_data.get("user_intent", setup_data.get("purpose", ""))
            geographic_filter = setup_data.get("geographic_filter", {})

            # Use the new AI-powered generation (3 LLM calls)
            setup_result = await create_category_setup_with_ai(
                session,
                user_intent=user_intent,
                geographic_filter=geographic_filter,
                current_user_id=current_user_id,
            )

            result["message"] = setup_result.get("message", "Category-Setup erstellt")
            result["success"] = setup_result.get("success", False)
            result["steps"] = setup_result.get("steps", [])
            result["search_terms"] = setup_result.get("search_terms", [])
            result["url_patterns"] = setup_result.get("url_patterns", {})
            result["ai_extraction_prompt"] = setup_result.get("ai_extraction_prompt", "")

            if setup_result.get("entity_type_id"):
                result["created_items"].append({
                    "type": "entity_type",
                    "id": setup_result["entity_type_id"],
                    "name": setup_result["entity_type_name"],
                    "slug": setup_result["entity_type_slug"],
                })
            if setup_result.get("category_id"):
                result["created_items"].append({
                    "type": "category",
                    "id": setup_result["category_id"],
                    "name": setup_result["category_name"],
                    "slug": setup_result["category_slug"],
                })
            if setup_result.get("linked_data_source_count"):
                result["linked_sources_count"] = setup_result["linked_data_source_count"]

        elif operation == "start_crawl":
            crawl_data = command.get("crawl_command_data", {})
            crawl_result = await execute_crawl_command(session, crawl_data)
            result["message"] = crawl_result.get("message", "Crawl gestartet")
            result["success"] = crawl_result.get("success", False)
            result["crawl_jobs"] = crawl_result.get("jobs", [])
            result["sources_count"] = crawl_result.get("sources_count", 0)

        elif operation == "combined":
            # Support both "operations" and "combined_operations" keys
            operations_list = command.get("operations", []) or command.get("combined_operations", [])
            combined_result = await execute_combined_operations(session, operations_list, current_user_id)
            result["message"] = combined_result.get("message", "Kombinierte Operationen ausgeführt")
            result["success"] = combined_result.get("success", False)
            result["created_items"] = combined_result.get("created_items", [])
            result["operation_results"] = combined_result.get("operation_results", [])

        else:
            result["message"] = f"Unbekannte Operation: {operation}"

        if result["success"]:
            await session.commit()
        else:
            await session.rollback()

    except Exception as e:
        logger.error("Write command execution failed", error=str(e))
        await session.rollback()
        result["message"] = f"Fehler: {str(e)}"

    return result


async def interpret_query(question: str) -> Optional[Dict[str, Any]]:
    """Use AI to interpret natural language query into structured query parameters."""
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

        # Clean up markdown code blocks if present
        if "```" in content:
            # Extract content between ``` markers
            match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
            if match:
                content = match.group(1)
            else:
                # Fallback: remove leading ```json and trailing ```
                content = content.replace("```json", "").replace("```", "")
        content = content.strip()
        logger.debug("AI cleaned response", content=content[:200] if content else "empty")

        parsed = json.loads(content)
        logger.info("Query interpreted successfully", interpretation=parsed)
        return parsed

    except Exception as e:
        logger.error("Failed to interpret query", error=str(e), exc_info=True)
        return None


async def execute_smart_query(
    session: AsyncSession,
    query_params: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute the interpreted query against the Entity-Facet system."""

    results = {
        "items": [],
        "total": 0,
        "query_interpretation": query_params,
    }

    primary_type = query_params.get("primary_entity_type", "person")
    facet_types = query_params.get("facet_types", [])
    time_filter = query_params.get("time_filter", "all")
    filters = query_params.get("filters", {})
    grouping = query_params.get("result_grouping", "flat")

    # Get entity type
    entity_type_result = await session.execute(
        select(EntityType).where(EntityType.slug == primary_type)
    )
    entity_type = entity_type_result.scalar_one_or_none()
    if not entity_type:
        return results

    # Get facet types
    facet_type_map = {}
    for ft_slug in facet_types:
        ft_result = await session.execute(
            select(FacetType).where(FacetType.slug == ft_slug)
        )
        ft = ft_result.scalar_one_or_none()
        if ft:
            facet_type_map[ft_slug] = ft

    # Build base entity query
    entity_query = select(Entity).where(
        Entity.entity_type_id == entity_type.id,
        Entity.is_active == True,
    )

    # Apply position filters for persons
    position_keywords = filters.get("position_keywords", [])
    if position_keywords and primary_type == "person":
        position_conditions = []
        for keyword in position_keywords:
            position_conditions.append(
                Entity.core_attributes["position"].astext.ilike(f"%{keyword}%")
            )
        if position_conditions:
            entity_query = entity_query.where(or_(*position_conditions))

    # Apply location/name filters
    location_keywords = filters.get("location_keywords", [])
    if location_keywords:
        location_conditions = []
        for keyword in location_keywords:
            location_conditions.append(Entity.name.ilike(f"%{keyword}%"))
        if location_conditions:
            entity_query = entity_query.where(or_(*location_conditions))

    # If specific facet types are requested, first find entities that have those facets
    if facet_type_map and not location_keywords:
        # Get entity IDs that have the requested facet types
        facet_type_ids = [ft.id for ft in facet_type_map.values()]
        entity_ids_with_facets_result = await session.execute(
            select(FacetValue.entity_id)
            .distinct()
            .where(FacetValue.facet_type_id.in_(facet_type_ids))
            .where(FacetValue.is_active == True)
            .limit(500)
        )
        entity_ids_with_facets = [row[0] for row in entity_ids_with_facets_result.fetchall()]

        if entity_ids_with_facets:
            entity_query = entity_query.where(Entity.id.in_(entity_ids_with_facets))

    # Execute entity query
    entity_result = await session.execute(entity_query.limit(500))
    entities = entity_result.scalars().all()

    # Calculate time boundaries
    now = datetime.utcnow()
    days_ahead = filters.get("date_range_days", 90)
    future_cutoff = now + timedelta(days=days_ahead)

    # Get relation types for enrichment
    works_for_result = await session.execute(
        select(RelationType).where(RelationType.slug == "works_for")
    )
    works_for_type = works_for_result.scalar_one_or_none()

    # Process each entity
    items = []
    events_map = {}  # For grouping by event

    for entity in entities:
        entity_data = {
            "entity_id": str(entity.id),
            "entity_name": entity.name,
            "entity_slug": entity.slug,
            "entity_type": primary_type,
            "attributes": entity.core_attributes,
            "facets": {},
            "relations": {},
        }

        # Get facet values for this entity
        for ft_slug, ft in facet_type_map.items():
            fv_query = select(FacetValue).where(
                FacetValue.entity_id == entity.id,
                FacetValue.facet_type_id == ft.id,
                FacetValue.is_active == True,
            )

            # Apply time filter
            if time_filter == "future_only":
                fv_query = fv_query.where(
                    or_(
                        FacetValue.event_date >= now,
                        FacetValue.event_date.is_(None)
                    )
                )
            elif time_filter == "past_only":
                fv_query = fv_query.where(
                    FacetValue.event_date < now
                )

            fv_result = await session.execute(fv_query)
            facet_values = fv_result.scalars().all()

            entity_data["facets"][ft_slug] = [
                {
                    "id": str(fv.id),
                    "value": fv.value,
                    "text": fv.text_representation,
                    "event_date": fv.event_date.isoformat() if fv.event_date else None,
                    "confidence": fv.confidence_score,
                }
                for fv in facet_values
            ]

            # For event grouping
            if grouping == "by_event" and ft_slug == "event_attendance":
                for fv in facet_values:
                    event_name = fv.value.get("event_name", "Unknown")
                    event_date = fv.value.get("event_date", "")
                    event_key = f"{event_name}_{event_date}"

                    if event_key not in events_map:
                        events_map[event_key] = {
                            "event_name": event_name,
                            "event_date": event_date,
                            "event_location": fv.value.get("event_location"),
                            "attendees": [],
                        }

                    # Get municipality for this person
                    municipality_info = None
                    if works_for_type:
                        rel_result = await session.execute(
                            select(EntityRelation).where(
                                EntityRelation.source_entity_id == entity.id,
                                EntityRelation.relation_type_id == works_for_type.id,
                            )
                        )
                        rel = rel_result.scalar_one_or_none()
                        if rel:
                            muni = await session.get(Entity, rel.target_entity_id)
                            if muni:
                                municipality_info = {
                                    "id": str(muni.id),
                                    "name": muni.name,
                                }

                    events_map[event_key]["attendees"].append({
                        "person_id": str(entity.id),
                        "person_name": entity.name,
                        "position": entity.core_attributes.get("position"),
                        "municipality": municipality_info,
                        "role": fv.value.get("role"),
                        "topic": fv.value.get("topic"),
                    })

        # Get relations (e.g., works_for municipality)
        if works_for_type and primary_type == "person":
            rel_result = await session.execute(
                select(EntityRelation).where(
                    EntityRelation.source_entity_id == entity.id,
                    EntityRelation.relation_type_id == works_for_type.id,
                )
            )
            rel = rel_result.scalar_one_or_none()
            if rel:
                target = await session.get(Entity, rel.target_entity_id)
                if target:
                    entity_data["relations"]["works_for"] = {
                        "entity_id": str(target.id),
                        "entity_name": target.name,
                        "attributes": rel.attributes,
                    }

        # Only include if has relevant facets
        has_relevant_facets = any(
            len(fvs) > 0 for fvs in entity_data["facets"].values()
        )
        if has_relevant_facets or not facet_types:
            items.append(entity_data)

    # Return based on grouping
    if grouping == "by_event" and events_map:
        events_list = list(events_map.values())
        events_list.sort(key=lambda x: x.get("event_date") or "9999")
        results["items"] = events_list
        results["total"] = len(events_list)
        results["grouping"] = "by_event"
    else:
        results["items"] = items
        results["total"] = len(items)
        results["grouping"] = grouping

    return results


async def smart_query(
    session: AsyncSession,
    question: str,
    allow_write: bool = False,
) -> Dict[str, Any]:
    """
    Execute a natural language query against the Entity-Facet system.

    1. Checks if this is a write command (if allow_write=True)
    2. If write: interprets and executes the command
    3. If read: interprets the question and executes the query
    4. Returns structured results
    """
    # First, check if this is a write command
    if allow_write:
        write_command = await interpret_write_command(question)
        if write_command and write_command.get("operation", "none") != "none":
            logger.info(
                "Executing write command",
                question=question,
                command=write_command,
            )
            result = await execute_write_command(session, write_command)
            result["original_question"] = question
            result["mode"] = "write"
            result["interpretation"] = write_command
            return result

    # Fall through to read query
    query_params = await interpret_query(question)

    if not query_params:
        # Fallback: try a simple keyword-based interpretation
        query_params = fallback_interpret(question)

    logger.info(
        "Smart query interpreted",
        question=question,
        interpretation=query_params,
    )

    # Execute the query
    results = await execute_smart_query(session, query_params)
    results["original_question"] = question
    results["mode"] = "read"

    return results


async def smart_write(
    session: AsyncSession,
    command: str,
) -> Dict[str, Any]:
    """
    Execute a write command in natural language.

    Convenience function that always allows write operations.
    """
    return await smart_query(session, command, allow_write=True)


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


# =============================================================================
# CREATE_CATEGORY_SETUP - Komplexe Operation
# =============================================================================


def generate_entity_type_schema(search_focus: str, user_intent: str) -> Dict[str, Any]:
    """Generate attribute_schema for a new EntityType based on search focus."""
    schemas = {
        "event_attendance": {
            "type": "object",
            "properties": {
                "event_name": {"type": "string", "description": "Name der Veranstaltung"},
                "event_date": {"type": "string", "format": "date", "description": "Datum"},
                "event_end_date": {"type": "string", "format": "date", "description": "Enddatum"},
                "event_location": {"type": "string", "description": "Veranstaltungsort"},
                "event_type": {"type": "string", "description": "Art (Konferenz, Messe, etc.)"},
                "attendees_summary": {"type": "string", "description": "Zusammenfassung der Teilnehmer"},
            },
            "required": ["event_name"],
        },
        "pain_points": {
            "type": "object",
            "properties": {
                "issue_type": {"type": "string", "description": "Art des Problems"},
                "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                "description": {"type": "string", "description": "Beschreibung"},
                "affected_area": {"type": "string", "description": "Betroffener Bereich"},
            },
            "required": ["description"],
        },
        "contacts": {
            "type": "object",
            "properties": {
                "contact_name": {"type": "string", "description": "Name"},
                "role": {"type": "string", "description": "Position/Rolle"},
                "organization": {"type": "string", "description": "Organisation"},
                "email": {"type": "string", "format": "email"},
                "phone": {"type": "string"},
            },
            "required": ["contact_name"],
        },
        "general": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Titel"},
                "description": {"type": "string", "description": "Beschreibung"},
                "category": {"type": "string", "description": "Kategorie"},
            },
        },
    }
    return schemas.get(search_focus, schemas["general"])


def generate_ai_extraction_prompt(
    user_intent: str,
    search_focus: str,
    target_entity_type_name: str,
) -> str:
    """Generate an AI extraction prompt based on user intent and search focus."""

    focus_prompts = {
        "event_attendance": f"""Extrahiere aus diesem Dokument alle Informationen über Events und Veranstaltungen.

## Zu extrahieren:
1. **Event-Details:**
   - Name der Veranstaltung
   - Datum und Uhrzeit
   - Ort/Location
   - Art (Konferenz, Messe, Tagung, Workshop, etc.)

2. **Teilnehmer:**
   - Personenname und vollständiger Titel
   - Position/Rolle (Bürgermeister, Landrat, Dezernent, etc.)
   - Organisation/Gemeinde die die Person vertritt
   - Rolle auf dem Event (Redner, Teilnehmer, Aussteller, Organisator)

## Fokus: {user_intent}

## Output:
Erstelle für jedes gefundene Event eine Entity vom Typ "{target_entity_type_name}".
Verknüpfe die Teilnehmer als Relations (attends) mit ihren Personen-Entities.

Gib das Ergebnis als strukturiertes JSON zurück mit:
- events: [{{event_name, event_date, event_location, event_type, attendees: [{{name, position, organization, role}}]}}]
- is_future_event: boolean (basierend auf event_date)""",

        "pain_points": f"""Extrahiere aus diesem Dokument alle Pain Points, Probleme und Herausforderungen.

## Zu extrahieren:
1. **Probleme/Herausforderungen:**
   - Beschreibung des Problems
   - Betroffener Bereich (Personal, IT, Finanzen, etc.)
   - Schweregrad (hoch/mittel/niedrig)
   - Relevante Zitate

2. **Kontext:**
   - Welche Gemeinde/Organisation ist betroffen?
   - Zeitlicher Rahmen
   - Geplante Maßnahmen

## Fokus: {user_intent}

## Output:
Erstelle für jedes Problem eine Entity vom Typ "{target_entity_type_name}".
Bewerte jeden Pain Point nach Schweregrad.""",

        "contacts": f"""Extrahiere aus diesem Dokument alle relevanten Kontaktpersonen und Entscheider.

## Zu extrahieren:
1. **Kontaktdaten:**
   - Vollständiger Name und Titel
   - Position/Rolle
   - Organisation/Gemeinde
   - E-Mail und Telefon (falls vorhanden)

2. **Zusätzliche Infos:**
   - Zitate oder Aussagen der Person
   - Zuständigkeitsbereich
   - Sentiment (positiv/negativ/neutral)

## Fokus: {user_intent}

## Output:
Erstelle für jede Person eine Entity vom Typ "{target_entity_type_name}".""",

        "general": f"""Analysiere dieses Dokument im Hinblick auf:
{user_intent}

Extrahiere relevante Informationen strukturiert.

## Output:
Erstelle Entities vom Typ "{target_entity_type_name}" für alle relevanten Funde.""",
    }

    return focus_prompts.get(search_focus, focus_prompts["general"])


def generate_url_patterns(search_focus: str, user_intent: str) -> Tuple[List[str], List[str]]:
    """
    Generate URL include and exclude patterns based on search focus.

    Returns:
        Tuple of (include_patterns, exclude_patterns)
    """
    # Common exclude patterns (always exclude these)
    common_exclude = [
        r"/impressum",
        r"/datenschutz",
        r"/privacy",
        r"/kontakt$",
        r"/contact$",
        r"/login",
        r"/logout",
        r"/admin/",
        r"/api/",
        r"/wp-admin/",
        r"/wp-login",
        r"/sitemap",
        r"\.xml$",
        r"\.json$",
        r"/feed/",
        r"/rss",
        r"/print/",
        r"/drucken/",
        r"/suche\?",
        r"/search\?",
    ]

    # Focus-specific patterns
    focus_patterns = {
        "event_attendance": {
            "include": [
                r"/event",
                r"/veranstaltung",
                r"/termin",
                r"/kalender",
                r"/agenda",
                r"/konferenz",
                r"/kongress",
                r"/messe",
                r"/tagung",
                r"/seminar",
                r"/workshop",
                r"/news",
                r"/aktuell",
                r"/meldung",
                r"/presse",
                r"/mitteilung",
            ],
            "exclude": common_exclude + [
                r"/archiv/\d{4}/\d{2}/",  # Alte Monatsarchive
                r"/stellenangebot",
                r"/karriere",
                r"/job",
            ],
        },
        "pain_points": {
            "include": [
                r"/news",
                r"/aktuell",
                r"/meldung",
                r"/bericht",
                r"/protokoll",
                r"/sitzung",
                r"/beschluss",
                r"/antrag",
                r"/politik",
                r"/gemeinderat",
                r"/stadtrat",
            ],
            "exclude": common_exclude,
        },
        "contacts": {
            "include": [
                r"/person",
                r"/team",
                r"/mitarbeiter",
                r"/ansprechpartner",
                r"/leitung",
                r"/vorstand",
                r"/gremien",
                r"/politik",
                r"/buergermeister",
                r"/landrat",
                r"/ratsmitglied",
            ],
            "exclude": common_exclude,
        },
        "general": {
            "include": [
                r"/news",
                r"/aktuell",
                r"/meldung",
                r"/presse",
            ],
            "exclude": common_exclude,
        },
    }

    patterns = focus_patterns.get(search_focus, focus_patterns["general"])
    return patterns["include"], patterns["exclude"]


def expand_search_terms(search_focus: str, raw_terms: List[str]) -> List[str]:
    """
    Expand abstract search terms into concrete terms.

    E.g., "Entscheider" -> "Bürgermeister", "Landrat", "Oberbürgermeister", etc.
    """
    # Term expansion mappings
    expansions = {
        "entscheider": [
            "Bürgermeister",
            "Oberbürgermeister",
            "Landrat",
            "Landrätin",
            "Dezernent",
            "Dezernentin",
            "Amtsleiter",
            "Amtsleiterin",
            "Kämmerer",
            "Kämmerin",
            "Gemeinderat",
            "Stadtrat",
            "Kreisrat",
            "Fraktionsvorsitzender",
            "Verwaltungsleiter",
        ],
        "politiker": [
            "Bürgermeister",
            "Oberbürgermeister",
            "Landrat",
            "Landrätin",
            "Abgeordneter",
            "Abgeordnete",
            "Minister",
            "Ministerin",
            "Staatssekretär",
            "Fraktionsvorsitzender",
        ],
        "veranstaltung": [
            "Event",
            "Konferenz",
            "Kongress",
            "Tagung",
            "Messe",
            "Seminar",
            "Workshop",
            "Symposium",
            "Forum",
            "Gipfel",
        ],
        "event": [
            "Veranstaltung",
            "Konferenz",
            "Kongress",
            "Tagung",
            "Messe",
            "Seminar",
            "Workshop",
        ],
        "gemeinde": [
            "Gemeinde",
            "Stadt",
            "Kommune",
            "Landkreis",
            "Kreis",
        ],
    }

    expanded = []
    for term in raw_terms:
        term_lower = term.lower()
        if term_lower in expansions:
            # Add the expanded terms
            expanded.extend(expansions[term_lower])
        else:
            # Keep the original term
            expanded.append(term)

    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for t in expanded:
        if t.lower() not in seen:
            seen.add(t.lower())
            unique.append(t)

    return unique


# =============================================================================
# AI-POWERED GENERATION FUNCTIONS (3 separate LLM calls)
# =============================================================================

AI_ENTITY_TYPE_PROMPT = """Du generierst eine EntityType-Konfiguration basierend auf einer Benutzeranfrage.

## Benutzeranfrage:
{user_intent}

## Geografischer Fokus:
{geographic_context}

## Aufgabe:
Analysiere die Anfrage und erstelle eine passende EntityType-Konfiguration.

## Ausgabe (JSON):
{{
  "name": "Kurzer, prägnanter Name (z.B. 'Event-Besuche NRW')",
  "name_plural": "Pluralform",
  "description": "Ausführliche Beschreibung was dieser Typ repräsentiert",
  "icon": "Material Design Icon (mdi-calendar, mdi-account, mdi-office-building, mdi-lightbulb, mdi-alert, mdi-handshake)",
  "color": "Hex-Farbe (#2196F3=blau, #4CAF50=grün, #FF9800=orange, #9C27B0=lila)",
  "attribute_schema": {{
    "type": "object",
    "properties": {{
      "field_name": {{"type": "string", "description": "Beschreibung"}}
    }},
    "required": ["wichtigstes_feld"]
  }},
  "search_focus": "event_attendance|pain_points|contacts|opportunities|general"
}}

Antworte NUR mit validem JSON."""


AI_CATEGORY_PROMPT = """Du generierst eine Category-Konfiguration für Web-Crawling und KI-Extraktion.

## Benutzeranfrage:
{user_intent}

## EntityType:
Name: {entity_type_name}
Beschreibung: {entity_type_description}

## Aufgabe:
Erstelle eine Category-Konfiguration mit einem detaillierten KI-Extraktions-Prompt.

## Ausgabe (JSON):
{{
  "purpose": "Kurze Zweckbeschreibung für die Category",
  "search_terms": ["Begriff1", "Begriff2", "Begriff3", "..."],
  "extraction_handler": "event|default",
  "ai_extraction_prompt": "Detaillierter mehrzeiliger Prompt für die KI-Extraktion...\\n\\nMit Anweisungen...\\n\\nUnd Beispielen..."
}}

## Wichtig für search_terms:
- Erweitere abstrakte Begriffe: "Entscheider" → "Bürgermeister", "Landrat", "Dezernent", etc.
- Füge relevante Synonyme hinzu
- Mindestens 10-15 konkrete Suchbegriffe
- In der Sprache der Zieldokumente (meist Deutsch)

## Wichtig für ai_extraction_prompt:
- Sehr detailliert (200-500 Wörter)
- Klare Struktur mit ## Überschriften
- Konkrete Beispiele was extrahiert werden soll
- Bezug zum EntityType "{entity_type_name}"
- Output-Format spezifizieren (JSON-Struktur)

Antworte NUR mit validem JSON."""


AI_CRAWL_CONFIG_PROMPT = """Du generierst URL-Filter-Konfiguration für einen Web-Crawler.

## Benutzeranfrage:
{user_intent}

## Suchfokus:
{search_focus}

## Search Terms:
{search_terms}

## Aufgabe:
Erstelle URL-Pattern-Filter die relevante Seiten einschließen und irrelevante ausschließen.

## Ausgabe (JSON):
{{
  "url_include_patterns": [
    "/pattern1",
    "/pattern2"
  ],
  "url_exclude_patterns": [
    "/impressum",
    "/datenschutz",
    "/pattern_to_exclude"
  ],
  "reasoning": "Kurze Begründung für die gewählten Patterns"
}}

## Include-Patterns:
- URL-Teile die auf relevante Inhalte hindeuten
- z.B. /news, /aktuell, /event, /veranstaltung, /meldung, /presse
- Case-insensitive Regex-Patterns

## Exclude-Patterns (immer inkludieren):
- /impressum, /datenschutz, /privacy, /kontakt, /login, /admin/, /api/
- /sitemap, /feed/, /rss, /print/, /suche, /search
- Zusätzliche kontextspezifische Ausschlüsse

Antworte NUR mit validem JSON."""


async def ai_generate_entity_type_config(
    user_intent: str,
    geographic_context: str,
) -> Dict[str, Any]:
    """
    Step 1/3: Generate EntityType configuration using LLM.

    Returns dict with: name, name_plural, description, icon, color, attribute_schema, search_focus
    """
    if not client:
        logger.warning("Azure OpenAI client not configured, using fallback")
        return {
            "name": "Neue Kategorie",
            "name_plural": "Neue Kategorien",
            "description": user_intent,
            "icon": "mdi-folder",
            "color": "#2196F3",
            "attribute_schema": {"type": "object", "properties": {}},
            "search_focus": "general",
        }

    prompt = AI_ENTITY_TYPE_PROMPT.format(
        user_intent=user_intent,
        geographic_context=geographic_context or "Keine geografische Einschränkung",
    )

    try:
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000,
        )

        content = response.choices[0].message.content.strip()
        # Clean up markdown code blocks if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()

        result = json.loads(content)
        logger.info("AI generated EntityType config", name=result.get("name"))
        return result

    except Exception as e:
        logger.error("Failed to generate EntityType config via AI", error=str(e))
        return {
            "name": "Neue Kategorie",
            "name_plural": "Neue Kategorien",
            "description": user_intent,
            "icon": "mdi-folder",
            "color": "#2196F3",
            "attribute_schema": {"type": "object", "properties": {}},
            "search_focus": "general",
        }


async def ai_generate_category_config(
    user_intent: str,
    entity_type_name: str,
    entity_type_description: str,
) -> Dict[str, Any]:
    """
    Step 2/3: Generate Category configuration with AI extraction prompt.

    Returns dict with: purpose, search_terms, extraction_handler, ai_extraction_prompt
    """
    if not client:
        logger.warning("Azure OpenAI client not configured, using fallback")
        return {
            "purpose": user_intent,
            "search_terms": ["Event", "Veranstaltung", "Konferenz"],
            "extraction_handler": "default",
            "ai_extraction_prompt": f"Extrahiere relevante Informationen zu: {user_intent}",
        }

    prompt = AI_CATEGORY_PROMPT.format(
        user_intent=user_intent,
        entity_type_name=entity_type_name,
        entity_type_description=entity_type_description,
    )

    try:
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000,
        )

        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()

        result = json.loads(content)
        logger.info(
            "AI generated Category config",
            search_terms_count=len(result.get("search_terms", [])),
        )
        return result

    except Exception as e:
        logger.error("Failed to generate Category config via AI", error=str(e))
        return {
            "purpose": user_intent,
            "search_terms": ["Event", "Veranstaltung", "Konferenz"],
            "extraction_handler": "default",
            "ai_extraction_prompt": f"Extrahiere relevante Informationen zu: {user_intent}",
        }


async def ai_generate_crawl_config(
    user_intent: str,
    search_focus: str,
    search_terms: List[str],
) -> Dict[str, Any]:
    """
    Step 3/3: Generate URL patterns for crawling.

    Returns dict with: url_include_patterns, url_exclude_patterns, reasoning
    """
    if not client:
        logger.warning("Azure OpenAI client not configured, using fallback")
        include, exclude = generate_url_patterns(search_focus, user_intent)
        return {
            "url_include_patterns": include,
            "url_exclude_patterns": exclude,
            "reasoning": "Fallback: Regelbasierte Patterns",
        }

    prompt = AI_CRAWL_CONFIG_PROMPT.format(
        user_intent=user_intent,
        search_focus=search_focus,
        search_terms=", ".join(search_terms[:20]),  # Limit for prompt size
    )

    try:
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=1000,
        )

        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()

        result = json.loads(content)
        logger.info(
            "AI generated Crawl config",
            include_count=len(result.get("url_include_patterns", [])),
            exclude_count=len(result.get("url_exclude_patterns", [])),
        )
        return result

    except Exception as e:
        logger.error("Failed to generate Crawl config via AI", error=str(e))
        include, exclude = generate_url_patterns(search_focus, user_intent)
        return {
            "url_include_patterns": include,
            "url_exclude_patterns": exclude,
            "reasoning": "Fallback: Regelbasierte Patterns",
        }


async def create_category_setup_with_ai(
    session: AsyncSession,
    user_intent: str,
    geographic_filter: Dict[str, Any],
    current_user_id: Optional[UUID] = None,
    progress_callback: Optional[callable] = None,
) -> Dict[str, Any]:
    """
    Execute CREATE_CATEGORY_SETUP with full AI generation (3 LLM calls).

    Args:
        session: Database session
        user_intent: Original user query
        geographic_filter: Geographic constraints (admin_level_1, country)
        current_user_id: User ID for ownership
        progress_callback: Optional callback(step, total, message) for progress updates

    Returns:
        Result dict with created entities and progress info
    """
    result = {
        "success": False,
        "message": "",
        "steps": [],
        "entity_type_id": None,
        "entity_type_name": None,
        "entity_type_slug": None,
        "category_id": None,
        "category_name": None,
        "category_slug": None,
        "linked_data_source_count": 0,
        "ai_extraction_prompt": "",
        "url_patterns": {},
        "search_terms": [],
        "warnings": [],
    }

    def report_progress(step: int, message: str, success: bool = True):
        result["steps"].append({
            "step": step,
            "total": 3,
            "message": message,
            "success": success,
        })
        if progress_callback:
            progress_callback(step, 3, message)
        logger.info(f"Smart Query Progress [{step}/3]: {message}")

    try:
        # Resolve geographic context
        admin_level_1 = geographic_filter.get("admin_level_1")
        if not admin_level_1 and geographic_filter.get("admin_level_1_alias"):
            admin_level_1 = resolve_geographic_alias(geographic_filter["admin_level_1_alias"])
        geographic_context = admin_level_1 or "Deutschland"

        # =========================================================================
        # STEP 1/3: Generate EntityType Configuration
        # =========================================================================
        report_progress(1, "Generiere EntityType-Konfiguration...")

        et_config = await ai_generate_entity_type_config(user_intent, geographic_context)

        name = et_config.get("name", "Neue Kategorie").strip()
        slug = generate_slug(name)

        # Check for duplicates
        existing_et = await session.execute(
            select(EntityType).where(
                or_(EntityType.name == name, EntityType.slug == slug)
            )
        )
        if existing_et.scalar():
            # Add suffix to make unique
            name = f"{name} ({geographic_context})"
            slug = generate_slug(name)

        entity_type = EntityType(
            id=uuid_module.uuid4(),
            name=name,
            slug=slug,
            name_plural=et_config.get("name_plural", name),
            description=et_config.get("description", user_intent),
            icon=et_config.get("icon", "mdi-folder"),
            color=et_config.get("color", "#2196F3"),
            display_order=100,
            is_primary=True,
            supports_hierarchy=False,
            attribute_schema=et_config.get("attribute_schema", {}),
            is_active=True,
            is_system=False,
            is_public=False,
            created_by_id=current_user_id,
            owner_id=current_user_id,
        )
        session.add(entity_type)
        await session.flush()

        result["entity_type_id"] = str(entity_type.id)
        result["entity_type_name"] = entity_type.name
        result["entity_type_slug"] = entity_type.slug
        result["steps"][-1]["result"] = f"EntityType '{name}' erstellt"

        # =========================================================================
        # STEP 2/3: Generate Category Configuration
        # =========================================================================
        report_progress(2, "Generiere Category & AI-Extraktions-Prompt...")

        cat_config = await ai_generate_category_config(
            user_intent,
            entity_type.name,
            entity_type.description,
        )

        search_terms = cat_config.get("search_terms", [])
        ai_prompt = cat_config.get("ai_extraction_prompt", "")
        extraction_handler = cat_config.get("extraction_handler", "default")

        # =========================================================================
        # STEP 3/3: Generate Crawl Configuration
        # =========================================================================
        report_progress(3, "Generiere URL-Filter & Crawl-Konfiguration...")

        crawl_config = await ai_generate_crawl_config(
            user_intent,
            et_config.get("search_focus", "general"),
            search_terms,
        )

        url_include_patterns = crawl_config.get("url_include_patterns", [])
        url_exclude_patterns = crawl_config.get("url_exclude_patterns", [])

        # =========================================================================
        # CREATE CATEGORY
        # =========================================================================
        cat_name = name
        cat_slug = slug

        existing_cat = await session.execute(
            select(Category).where(
                or_(Category.name == cat_name, Category.slug == cat_slug)
            )
        )
        if existing_cat.scalar():
            cat_name = f"{name} (Crawl)"
            cat_slug = f"{slug}-crawl"

        category = Category(
            id=uuid_module.uuid4(),
            name=cat_name,
            slug=cat_slug,
            description=f"KI-generiert: {user_intent}",
            purpose=cat_config.get("purpose", user_intent),
            search_terms=search_terms,
            document_types=["html", "pdf"],
            url_include_patterns=url_include_patterns,
            url_exclude_patterns=url_exclude_patterns,
            languages=["de"],
            ai_extraction_prompt=ai_prompt,
            extraction_handler=extraction_handler,
            schedule_cron="0 2 * * *",
            is_active=True,
            is_public=False,
            created_by_id=current_user_id,
            owner_id=current_user_id,
            target_entity_type_id=entity_type.id,
        )
        session.add(category)
        await session.flush()

        result["category_id"] = str(category.id)
        result["category_name"] = category.name
        result["category_slug"] = category.slug
        result["ai_extraction_prompt"] = ai_prompt
        result["search_terms"] = search_terms
        result["url_patterns"] = {
            "include": url_include_patterns,
            "exclude": url_exclude_patterns,
            "reasoning": crawl_config.get("reasoning", ""),
        }

        # =========================================================================
        # LINK DATA SOURCES
        # =========================================================================
        matching_sources = await find_matching_data_sources(session, geographic_filter)

        linked_count = 0
        for source in matching_sources:
            existing_link = await session.execute(
                select(DataSourceCategory).where(
                    DataSourceCategory.data_source_id == source.id,
                    DataSourceCategory.category_id == category.id,
                )
            )
            if not existing_link.scalar():
                link = DataSourceCategory(
                    id=uuid_module.uuid4(),
                    data_source_id=source.id,
                    category_id=category.id,
                )
                session.add(link)
                linked_count += 1

        await session.commit()

        result["linked_data_source_count"] = linked_count
        result["success"] = True
        result["message"] = f"Erfolgreich erstellt: EntityType '{entity_type.name}', Category '{category.name}', {linked_count} Datenquellen verknüpft"

        logger.info(
            "AI-powered category setup completed",
            entity_type=entity_type.name,
            category=category.name,
            sources=linked_count,
        )

        return result

    except Exception as e:
        logger.error("Failed to create category setup with AI", error=str(e))
        result["message"] = f"Fehler: {str(e)}"
        return result


async def find_matching_data_sources(
    session: AsyncSession,
    geographic_filter: Dict[str, Any],
    limit: int = 1000,
) -> List[DataSource]:
    """Find data sources matching geographic criteria."""
    admin_level_1 = geographic_filter.get("admin_level_1")
    admin_level_1_alias = geographic_filter.get("admin_level_1_alias")
    country = geographic_filter.get("country", "DE")

    if not admin_level_1 and admin_level_1_alias:
        admin_level_1 = resolve_geographic_alias(admin_level_1_alias)
    elif admin_level_1:
        admin_level_1 = resolve_geographic_alias(admin_level_1)

    if not admin_level_1:
        logger.warning("No admin_level_1 filter provided")
        return []

    logger.info(
        "Finding matching data sources",
        admin_level_1=admin_level_1,
        country=country,
    )

    # Strategy 1: Direct match on DataSource.admin_level_1
    direct_query = select(DataSource).where(
        DataSource.admin_level_1 == admin_level_1,
    )
    if country:
        direct_query = direct_query.where(DataSource.country == country)

    direct_result = await session.execute(direct_query.limit(limit))
    direct_matches = list(direct_result.scalars().all())

    # Strategy 2: Fallback via Entity relationship
    entity_query = (
        select(DataSource)
        .join(Entity, DataSource.entity_id == Entity.id)
        .where(Entity.admin_level_1 == admin_level_1)
    )
    if country:
        entity_query = entity_query.where(Entity.country == country)

    entity_result = await session.execute(entity_query.limit(limit))
    entity_matches = list(entity_result.scalars().all())

    # Combine and deduplicate
    all_sources = {ds.id: ds for ds in direct_matches + entity_matches}

    logger.info(
        "Found matching data sources",
        direct_count=len(direct_matches),
        entity_count=len(entity_matches),
        total_unique=len(all_sources),
    )

    return list(all_sources.values())


async def create_category_setup(
    session: AsyncSession,
    setup_data: Dict[str, Any],
    current_user_id: Optional[UUID] = None,
) -> Dict[str, Any]:
    """Execute CREATE_CATEGORY_SETUP operation - creates EntityType + Category + links DataSources."""
    result = {
        "success": False,
        "message": "",
        "entity_type_id": None,
        "entity_type_name": None,
        "entity_type_slug": None,
        "category_id": None,
        "category_name": None,
        "category_slug": None,
        "linked_data_source_count": 0,
        "ai_extraction_prompt": "",
        "warnings": [],
    }

    try:
        # 1. Extract and validate data
        name = setup_data.get("name", "").strip()
        purpose = setup_data.get("purpose", "").strip()
        user_intent = setup_data.get("user_intent", purpose)
        search_focus = setup_data.get("search_focus", "general")
        search_terms = setup_data.get("search_terms", [])
        geographic_filter = setup_data.get("geographic_filter", {})
        time_focus = setup_data.get("time_focus", "all")
        extraction_handler = setup_data.get("extraction_handler", "default")

        if not name:
            result["message"] = "Name ist erforderlich"
            return result

        if not purpose:
            purpose = user_intent or f"Automatisch erstellt: {name}"

        # 2. Generate slug
        slug = generate_slug(name)

        # 3. Check for duplicate EntityType
        existing_et = await session.execute(
            select(EntityType).where(
                or_(EntityType.name == name, EntityType.slug == slug)
            )
        )
        if existing_et.scalar():
            result["message"] = f"EntityType '{name}' existiert bereits"
            return result

        # 4. Generate attribute schema
        attribute_schema = generate_entity_type_schema(search_focus, user_intent)

        # 4b. Generate URL patterns for crawling
        url_include_patterns, url_exclude_patterns = generate_url_patterns(search_focus, user_intent)

        # 4c. Expand search terms (e.g., "Entscheider" -> concrete roles)
        expanded_search_terms = expand_search_terms(search_focus, search_terms)

        # 5. Create EntityType
        entity_type = EntityType(
            id=uuid_module.uuid4(),
            name=name,
            slug=slug,
            name_plural=f"{name}",  # Same as name for custom types
            description=f"Automatisch erstellt: {user_intent}",
            icon="mdi-calendar" if search_focus == "event_attendance" else "mdi-folder",
            color="#2196F3" if search_focus == "event_attendance" else "#4CAF50",
            display_order=100,  # After system types
            is_primary=True,
            supports_hierarchy=False,
            attribute_schema=attribute_schema,
            is_active=True,
            is_system=False,
            is_public=False,  # Private by default
            created_by_id=current_user_id,
            owner_id=current_user_id,
        )
        session.add(entity_type)
        await session.flush()

        logger.info(
            "Created EntityType",
            entity_type_id=str(entity_type.id),
            name=entity_type.name,
        )

        # 6. Generate AI extraction prompt
        ai_prompt = generate_ai_extraction_prompt(user_intent, search_focus, name)

        # 7. Determine extraction handler
        if search_focus == "event_attendance":
            extraction_handler = "event"

        # 8. Check for duplicate Category
        existing_cat = await session.execute(
            select(Category).where(
                or_(Category.name == name, Category.slug == slug)
            )
        )
        if existing_cat.scalar():
            # Use a slightly different name/slug for category
            cat_name = f"{name} (Crawl)"
            cat_slug = f"{slug}-crawl"
        else:
            cat_name = name
            cat_slug = slug

        # 9. Create Category with URL patterns and expanded search terms
        category = Category(
            id=uuid_module.uuid4(),
            name=cat_name,
            slug=cat_slug,
            description=f"Automatisch erstellt: {user_intent}",
            purpose=purpose,
            search_terms=expanded_search_terms or ["Event", "Veranstaltung", "Konferenz", "Tagung"],
            document_types=["html", "pdf"],
            url_include_patterns=url_include_patterns,
            url_exclude_patterns=url_exclude_patterns,
            languages=["de"],
            ai_extraction_prompt=ai_prompt,
            extraction_handler=extraction_handler,
            schedule_cron="0 2 * * *",
            is_active=True,
            is_public=False,  # Private by default
            created_by_id=current_user_id,
            owner_id=current_user_id,
            target_entity_type_id=entity_type.id,
        )
        session.add(category)
        await session.flush()

        logger.info(
            "Created Category",
            category_id=str(category.id),
            name=category.name,
        )

        # 10. Find and link matching DataSources
        matching_sources = await find_matching_data_sources(session, geographic_filter)

        linked_count = 0
        for source in matching_sources:
            # Check if link already exists
            existing_link = await session.execute(
                select(DataSourceCategory).where(
                    DataSourceCategory.data_source_id == source.id,
                    DataSourceCategory.category_id == category.id,
                )
            )
            if not existing_link.scalar():
                link = DataSourceCategory(
                    id=uuid_module.uuid4(),
                    data_source_id=source.id,
                    category_id=category.id,
                    is_primary=False,
                )
                session.add(link)
                linked_count += 1

        await session.flush()

        # 11. Build result
        result["success"] = True
        result["message"] = f"Setup erstellt: EntityType '{entity_type.name}', Category '{category.name}', {linked_count} DataSources verknüpft"
        result["entity_type_id"] = str(entity_type.id)
        result["entity_type_name"] = entity_type.name
        result["entity_type_slug"] = entity_type.slug
        result["category_id"] = str(category.id)
        result["category_name"] = category.name
        result["category_slug"] = category.slug
        result["linked_data_source_count"] = linked_count
        result["ai_extraction_prompt"] = ai_prompt

        if linked_count == 0:
            admin_level = geographic_filter.get("admin_level_1") or geographic_filter.get("admin_level_1_alias")
            result["warnings"].append(
                f"Keine DataSources für Filter '{admin_level}' gefunden. "
                "Bitte DataSources manuell hinzufügen."
            )

        return result

    except Exception as e:
        logger.error("Category setup failed", error=str(e), exc_info=True)
        result["message"] = f"Fehler: {str(e)}"
        return result


# =============================================================================
# START_CRAWL Operation
# =============================================================================


async def find_sources_for_crawl(
    session: AsyncSession,
    crawl_data: Dict[str, Any],
    limit: int = 100,
) -> List[DataSource]:
    """Find data sources matching crawl criteria."""
    filter_type = crawl_data.get("filter_type", "location")
    location_name = crawl_data.get("location_name")
    admin_level_1 = crawl_data.get("admin_level_1")
    category_slug = crawl_data.get("category_slug")
    source_ids = crawl_data.get("source_ids", [])

    query = select(DataSource).where(DataSource.status != "ERROR")

    if source_ids:
        # Explicit source IDs
        query = query.where(DataSource.id.in_([UUID(sid) for sid in source_ids]))

    elif filter_type == "location" and location_name:
        # Filter by location_name (e.g., "Gummersbach")
        query = query.where(
            or_(
                DataSource.location_name.ilike(f"%{location_name}%"),
                DataSource.name.ilike(f"%{location_name}%"),
            )
        )

    elif filter_type == "location" and admin_level_1:
        # Filter by admin_level_1 (e.g., "Nordrhein-Westfalen")
        resolved = resolve_geographic_alias(admin_level_1)
        query = query.where(DataSource.admin_level_1 == resolved)

    elif filter_type == "category" and category_slug:
        # Filter by category
        cat_result = await session.execute(
            select(Category).where(Category.slug == category_slug)
        )
        category = cat_result.scalar_one_or_none()
        if category:
            query = (
                query
                .join(DataSourceCategory, DataSource.id == DataSourceCategory.data_source_id)
                .where(DataSourceCategory.category_id == category.id)
            )

    elif filter_type == "entity_name":
        # Filter by linked entity name
        entity_name = location_name or crawl_data.get("entity_name")
        if entity_name:
            query = (
                query
                .join(Entity, DataSource.entity_id == Entity.id)
                .where(Entity.name.ilike(f"%{entity_name}%"))
            )

    result = await session.execute(query.limit(limit))
    return list(result.scalars().all())


async def execute_crawl_command(
    session: AsyncSession,
    crawl_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute START_CRAWL operation - starts crawls for matching sources."""
    from workers.crawl_tasks import create_crawl_job

    result = {
        "success": False,
        "message": "",
        "job_count": 0,
        "source_count": 0,
        "sources": [],
        "warnings": [],
    }

    try:
        # Find matching sources
        sources = await find_sources_for_crawl(session, crawl_data)

        if not sources:
            result["message"] = "Keine passenden DataSources gefunden"
            return result

        result["source_count"] = len(sources)

        # Get categories for each source
        include_all_categories = crawl_data.get("include_all_categories", True)
        job_count = 0

        for source in sources:
            # Get all categories for this source
            if include_all_categories:
                cat_result = await session.execute(
                    select(DataSourceCategory.category_id)
                    .where(DataSourceCategory.data_source_id == source.id)
                )
                category_ids = [row[0] for row in cat_result.fetchall()]

                # Also include legacy category_id if set
                if source.category_id and source.category_id not in category_ids:
                    category_ids.append(source.category_id)
            else:
                # Only primary category
                category_ids = [source.category_id] if source.category_id else []

            if not category_ids:
                result["warnings"].append(f"Source '{source.name}' hat keine Kategorie")
                continue

            # Create crawl job for each category
            for cat_id in category_ids:
                try:
                    create_crawl_job.delay(str(source.id), str(cat_id))
                    job_count += 1
                except Exception as e:
                    logger.error(
                        "Failed to create crawl job",
                        source_id=str(source.id),
                        category_id=str(cat_id),
                        error=str(e),
                    )

            result["sources"].append({
                "id": str(source.id),
                "name": source.name,
                "category_count": len(category_ids),
            })

        result["success"] = True
        result["job_count"] = job_count
        result["message"] = f"{job_count} Crawl-Jobs für {len(sources)} Sources erstellt"

        return result

    except Exception as e:
        logger.error("Crawl command failed", error=str(e), exc_info=True)
        result["message"] = f"Fehler: {str(e)}"
        return result


# =============================================================================
# Combined Operations
# =============================================================================


async def execute_combined_operations(
    session: AsyncSession,
    operations: List[Dict[str, Any]],
    current_user_id: Optional[UUID] = None,
) -> Dict[str, Any]:
    """Execute multiple operations sequentially."""
    result = {
        "success": False,
        "message": "",
        "operation_results": [],
        "warnings": [],
    }

    try:
        for i, op in enumerate(operations):
            op_type = op.get("operation")
            op_result = None

            logger.info(f"Executing combined operation {i+1}/{len(operations)}", operation=op_type)

            if op_type == "create_category_setup":
                setup_data = op.get("category_setup_data", {})
                op_result = await create_category_setup(session, setup_data, current_user_id)

            elif op_type == "start_crawl":
                crawl_data = op.get("crawl_command_data", {})
                op_result = await execute_crawl_command(session, crawl_data)

            elif op_type == "create_entity_type":
                entity_type_data = op.get("entity_type_data", {})
                entity_type, message = await create_entity_type_from_command(session, entity_type_data)
                op_result = {
                    "success": entity_type is not None,
                    "message": message,
                    "entity_type_id": str(entity_type.id) if entity_type else None,
                }

            elif op_type == "create_entity":
                entity_type = op.get("entity_type", "municipality")
                entity_data = op.get("entity_data", {})
                entity, message = await create_entity_from_command(session, entity_type, entity_data)
                op_result = {
                    "success": entity is not None,
                    "message": message,
                    "entity_id": str(entity.id) if entity else None,
                }

            else:
                op_result = {"success": False, "message": f"Unbekannte Operation: {op_type}"}

            result["operation_results"].append({
                "operation": op_type,
                "index": i,
                **op_result,
            })

            # If an operation fails, stop and rollback
            if not op_result.get("success", False):
                result["message"] = f"Operation {i+1} ({op_type}) fehlgeschlagen: {op_result.get('message')}"
                await session.rollback()
                return result

        # All operations successful
        await session.flush()
        result["success"] = True
        result["message"] = f"Alle {len(operations)} Operationen erfolgreich ausgeführt"

        return result

    except Exception as e:
        logger.error("Combined operations failed", error=str(e), exc_info=True)
        await session.rollback()
        result["message"] = f"Fehler: {str(e)}"
        return result
