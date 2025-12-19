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

## Befehle erkennen:
- "Erstelle", "Anlegen", "Neue/r/s", "Füge hinzu" → CREATE
- "Aktualisiere", "Ändere", "Setze" → UPDATE
- "Verknüpfe", "Verbinde" → CREATE_RELATION
- "Neuen Entity-Typ", "Neue Kategorie", "Neuen Typ" → CREATE_ENTITY_TYPE

Analysiere die Anfrage und gib JSON zurück:
{{
  "operation": "create_entity|create_entity_type|create_facet|create_relation|update_entity|none",
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
