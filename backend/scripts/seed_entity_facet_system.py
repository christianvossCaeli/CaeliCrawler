#!/usr/bin/env python3
"""
Seed script for the Entity-Facet system.

Creates:
- System EntityTypes (municipality, person, organization, event)
- System FacetTypes (pain_point, positive_signal, contact, event_attendance, summary)
- System RelationTypes (works_for, attends, located_in)
- Demo AnalysisTemplates

Run with: python -m scripts.seed_entity_facet_system
"""

import asyncio
import sys
import uuid
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.database import get_session_context
from app.models import (
    AnalysisTemplate,
    Category,
    EntityType,
    FacetType,
    RelationType,
)

# =============================================================================
# SYSTEM ENTITY TYPES
# =============================================================================

ENTITY_TYPES = [
    {
        "slug": "territorial_entity",
        "name": "Gebietskörperschaft",
        "name_plural": "Gebietskörperschaften",
        "description": "Kommunen, Staedte, Gemeinden und Landkreise",
        "icon": "mdi-home-city",
        "color": "#4CAF50",
        "display_order": 1,
        "is_primary": True,
        "supports_hierarchy": True,
        "hierarchy_config": {
            "levels": ["country", "admin_level_1", "admin_level_2", "locality"],
            "labels": {
                "country": "Land",
                "admin_level_1": "Bundesland",
                "admin_level_2": "Landkreis",
                "locality": "Gemeinde",
            },
        },
        "attribute_schema": {
            "type": "object",
            "properties": {
                "population": {"type": "integer", "title": "Einwohner", "description": "Einwohnerzahl"},
                "area_km2": {"type": "number", "title": "Flaeche (km²)", "description": "Flaeche in km2"},
                "official_code": {"type": "string", "title": "Amtlicher Schluessel", "description": "AGS/GSS Code"},
                "locality_type": {"type": "string", "title": "Ortstyp", "description": "Art (Stadt, Gemeinde, etc.)"},
                "website": {"type": "string", "title": "Website", "description": "Offizielle Website"},
            },
        },
        "is_system": True,
    },
    {
        "slug": "person",
        "name": "Person",
        "name_plural": "Personen",
        "description": "Entscheider, Kontakte und relevante Personen",
        "icon": "mdi-account",
        "color": "#2196F3",
        "display_order": 2,
        "is_primary": False,
        "supports_hierarchy": False,
        "attribute_schema": {
            "type": "object",
            "properties": {
                "academic_title": {"type": "string", "title": "Titel", "description": "Titel (Dr., Prof., etc.)"},
                "first_name": {"type": "string", "title": "Vorname"},
                "last_name": {"type": "string", "title": "Nachname"},
                "email": {"type": "string", "title": "E-Mail", "format": "email"},
                "phone": {"type": "string", "title": "Telefon"},
                "role": {"type": "string", "title": "Position", "description": "Aktuelle Rolle/Position"},
            },
        },
        "is_system": True,
    },
    {
        "slug": "organization",
        "name": "Organisation",
        "name_plural": "Organisationen",
        "description": "Unternehmen, Verbaende und Institutionen",
        "icon": "mdi-domain",
        "color": "#9C27B0",
        "display_order": 3,
        "is_primary": False,
        "supports_hierarchy": False,
        "attribute_schema": {
            "type": "object",
            "properties": {
                "org_type": {
                    "type": "string",
                    "title": "Organisationstyp",
                    "description": "Typ (Unternehmen, Verband, etc.)",
                },
                "website": {"type": "string", "title": "Website"},
                "email": {"type": "string", "title": "E-Mail", "format": "email"},
                "address": {"type": "string", "title": "Adresse"},
            },
        },
        "is_system": True,
    },
    {
        "slug": "event",
        "name": "Veranstaltung",
        "name_plural": "Veranstaltungen",
        "description": "Messen, Konferenzen, Workshops und Events",
        "icon": "mdi-calendar-star",
        "color": "#FF9800",
        "display_order": 4,
        "is_primary": True,
        "supports_hierarchy": False,
        "attribute_schema": {
            "type": "object",
            "properties": {
                "event_date": {"type": "string", "title": "Startdatum", "format": "date-time"},
                "event_end_date": {"type": "string", "title": "Enddatum", "format": "date-time"},
                "location": {"type": "string", "title": "Ort"},
                "organizer": {"type": "string", "title": "Veranstalter"},
                "event_type": {
                    "type": "string",
                    "title": "Veranstaltungstyp",
                    "description": "Messe, Konferenz, Workshop, etc.",
                },
                "website": {"type": "string", "title": "Website"},
                "description": {"type": "string", "title": "Beschreibung"},
            },
        },
        "is_system": True,
    },
]


# =============================================================================
# SYSTEM FACET TYPES
# =============================================================================

FACET_TYPES = [
    {
        "slug": "pain_point",
        "name": "Pain Point",
        "name_plural": "Pain Points",
        "description": "Probleme, Herausforderungen und negative Signale",
        "icon": "mdi-alert-circle",
        "color": "#F44336",
        "display_order": 1,
        "value_type": "structured",
        "value_schema": {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "type": {
                    "type": "string",
                    "enum": [
                        "Buergerprotest",
                        "Naturschutz",
                        "Abstandsregelung",
                        "Genehmigung",
                        "Laerm",
                        "Optik",
                        "Artenschutz",
                        "Sonstiges",
                    ],
                },
                "severity": {"type": "string", "enum": ["hoch", "mittel", "niedrig"]},
                "quote": {"type": "string"},
            },
            "required": ["description"],
            # Display configuration for generic rendering
            "display": {
                "primary_field": "description",
                "chip_fields": ["type", "severity"],
                "quote_field": "quote",
                "severity_field": "severity",
                "severity_colors": {
                    "hoch": "error",
                    "mittel": "warning",
                    "niedrig": "info",
                },
                "layout": "card",
            },
        },
        "applicable_entity_type_slugs": ["territorial_entity"],
        "aggregation_method": "dedupe",
        "deduplication_fields": ["description"],
        "is_time_based": False,
        "ai_extraction_enabled": True,
        "ai_extraction_prompt": "Extrahiere Pain Points bezueglich Windenergie aus diesem Dokument. Finde Probleme wie Buergerproteste, Naturschutzkonflikte, Genehmigungsprobleme.",
        "is_system": True,
    },
    {
        "slug": "positive_signal",
        "name": "Positives Signal",
        "name_plural": "Positive Signale",
        "description": "Chancen, positive Entwicklungen und Opportunitaeten",
        "icon": "mdi-lightbulb-on",
        "color": "#4CAF50",
        "display_order": 2,
        "value_type": "structured",
        "value_schema": {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "type": {
                    "type": "string",
                    "enum": ["Projektankuendigung", "Foerderung", "Buergerbeteiligung", "Klimaziel", "Sonstiges"],
                },
                "quote": {"type": "string"},
            },
            "required": ["description"],
            # Display configuration for generic rendering
            "display": {
                "primary_field": "description",
                "chip_fields": ["type"],
                "quote_field": "quote",
                "layout": "card",
            },
        },
        "applicable_entity_type_slugs": ["territorial_entity"],
        "aggregation_method": "dedupe",
        "deduplication_fields": ["description"],
        "is_time_based": False,
        "ai_extraction_enabled": True,
        "ai_extraction_prompt": "Extrahiere positive Signale bezueglich Windenergie aus diesem Dokument. Finde Chancen wie Projektankuendigungen, Foerderungen, Klimaziele.",
        "is_system": True,
    },
    {
        "slug": "contact",
        "name": "Kontakt",
        "name_plural": "Kontakte",
        "description": "Entscheider und Ansprechpartner",
        "icon": "mdi-account-tie",
        "color": "#2196F3",
        "display_order": 3,
        "value_type": "structured",
        "value_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "role": {"type": "string"},
                "email": {"type": "string", "format": "email"},
                "phone": {"type": "string"},
                "statement": {"type": "string"},
                "sentiment": {"type": "string", "enum": ["positiv", "neutral", "negativ"]},
            },
            "required": ["name"],
            # Display configuration for generic rendering
            "display": {
                "primary_field": "name",
                "chip_fields": ["role", "sentiment"],
                "quote_field": "statement",
                "severity_field": "sentiment",
                "severity_colors": {
                    "positiv": "success",
                    "neutral": "grey",
                    "negativ": "error",
                },
                "layout": "card",
            },
        },
        "applicable_entity_type_slugs": ["territorial_entity", "organization"],
        "aggregation_method": "dedupe",
        "deduplication_fields": ["name"],
        "is_time_based": False,
        "ai_extraction_enabled": True,
        "ai_extraction_prompt": "Extrahiere Entscheider und Kontaktpersonen aus diesem Dokument. Finde Namen, Rollen und Kontaktdaten.",
        "is_system": True,
    },
    {
        "slug": "event_attendance",
        "name": "Event-Teilnahme",
        "name_plural": "Event-Teilnahmen",
        "description": "Geplante oder vergangene Teilnahme an Veranstaltungen",
        "icon": "mdi-calendar-check",
        "color": "#FF9800",
        "display_order": 4,
        "value_type": "structured",
        "value_schema": {
            "type": "object",
            "properties": {
                "event_name": {"type": "string"},
                "event_date": {"type": "string", "format": "date"},
                "event_location": {"type": "string"},
                "role": {"type": "string", "enum": ["Redner", "Teilnehmer", "Aussteller", "Organisator"]},
                "confirmed": {"type": "boolean"},
                "source": {"type": "string"},
            },
            "required": ["event_name"],
            # Display configuration for generic rendering
            "display": {
                "primary_field": "event_name",
                "chip_fields": ["role", "event_date", "event_location"],
                "layout": "card",
            },
        },
        "applicable_entity_type_slugs": ["person"],
        "aggregation_method": "list",
        "is_time_based": True,
        "time_field_path": "event_date",
        "default_time_filter": "future_only",
        "ai_extraction_enabled": True,
        "ai_extraction_prompt": "Extrahiere geplante Veranstaltungsteilnahmen aus diesem Dokument. Finde welche Personen auf welche Events gehen.",
        "is_system": True,
    },
    {
        "slug": "summary",
        "name": "Zusammenfassung",
        "name_plural": "Zusammenfassungen",
        "description": "KI-generierte Zusammenfassungen von Dokumenten",
        "icon": "mdi-text-box",
        "color": "#607D8B",
        "display_order": 5,
        "value_type": "text",
        "value_schema": {
            "type": "string",
            # Display configuration for generic rendering
            "display": {
                "primary_field": "text",
                "layout": "inline",
            },
        },
        "applicable_entity_type_slugs": [],  # All entity types
        "aggregation_method": "list",
        "is_time_based": False,
        "ai_extraction_enabled": True,
        "ai_extraction_prompt": "Erstelle eine kurze Zusammenfassung (2-3 Saetze) der wichtigsten Windenergie-relevanten Punkte.",
        "is_system": True,
    },
]


# =============================================================================
# SYSTEM RELATION TYPES
# =============================================================================

# Note: These will be created after entity_types are created and their IDs are known


# =============================================================================
# ANALYSIS TEMPLATES
# =============================================================================

# Note: These will be created after entity_types and facet_types are created


async def seed_entity_types(session) -> dict:
    """Seed entity types and return mapping of slug -> id."""
    entity_type_ids = {}

    for et_data in ENTITY_TYPES:
        # Check if already exists
        result = await session.execute(select(EntityType).where(EntityType.slug == et_data["slug"]))
        existing = result.scalar_one_or_none()

        if existing:
            entity_type_ids[et_data["slug"]] = existing.id
            continue

        entity_type = EntityType(
            id=uuid.uuid4(),
            **et_data,
        )
        session.add(entity_type)
        entity_type_ids[et_data["slug"]] = entity_type.id

    await session.flush()
    return entity_type_ids


async def seed_facet_types(session) -> dict:
    """Seed facet types and return mapping of slug -> id."""
    facet_type_ids = {}

    for ft_data in FACET_TYPES:
        # Check if already exists
        result = await session.execute(select(FacetType).where(FacetType.slug == ft_data["slug"]))
        existing = result.scalar_one_or_none()

        if existing:
            facet_type_ids[ft_data["slug"]] = existing.id
            continue

        facet_type = FacetType(
            id=uuid.uuid4(),
            **ft_data,
        )
        session.add(facet_type)
        facet_type_ids[ft_data["slug"]] = facet_type.id

    await session.flush()
    return facet_type_ids


async def seed_relation_types(session, entity_type_ids: dict) -> dict:
    """Seed relation types."""
    relation_type_ids = {}

    relation_types = [
        {
            "slug": "works_for",
            "name": "arbeitet fuer",
            "name_inverse": "beschaeftigt",
            "description": "Person arbeitet fuer eine Organisation oder Gemeinde",
            "source_entity_type_id": entity_type_ids["person"],
            "target_entity_type_id": entity_type_ids["territorial_entity"],
            "icon": "mdi-briefcase",
            "color": "#2196F3",
            "cardinality": "n:1",
            "attribute_schema": {
                "type": "object",
                "properties": {
                    "role": {"type": "string"},
                    "since": {"type": "string", "format": "date"},
                    "until": {"type": "string", "format": "date"},
                },
            },
            "is_system": True,
        },
        {
            "slug": "attends",
            "name": "nimmt teil an",
            "name_inverse": "hat Teilnehmer",
            "description": "Person nimmt an einer Veranstaltung teil",
            "source_entity_type_id": entity_type_ids["person"],
            "target_entity_type_id": entity_type_ids["event"],
            "icon": "mdi-calendar-account",
            "color": "#FF9800",
            "cardinality": "n:m",
            "attribute_schema": {
                "type": "object",
                "properties": {
                    "role": {"type": "string", "enum": ["Redner", "Teilnehmer", "Aussteller", "Organisator"]},
                    "confirmed": {"type": "boolean"},
                },
            },
            "is_system": True,
        },
        {
            "slug": "located_in",
            "name": "befindet sich in",
            "name_inverse": "enthaelt",
            "description": "Event oder Organisation befindet sich in einer Gebietskörperschaft",
            "source_entity_type_id": entity_type_ids["event"],
            "target_entity_type_id": entity_type_ids["territorial_entity"],
            "icon": "mdi-map-marker",
            "color": "#4CAF50",
            "cardinality": "n:1",
            "is_system": True,
        },
        {
            "slug": "member_of",
            "name": "ist Mitglied von",
            "name_inverse": "hat Mitglied",
            "description": "Person ist Mitglied einer Organisation",
            "source_entity_type_id": entity_type_ids["person"],
            "target_entity_type_id": entity_type_ids["organization"],
            "icon": "mdi-account-group",
            "color": "#9C27B0",
            "cardinality": "n:m",
            "attribute_schema": {
                "type": "object",
                "properties": {
                    "role": {"type": "string"},
                    "since": {"type": "string", "format": "date"},
                },
            },
            "is_system": True,
        },
    ]

    for rt_data in relation_types:
        # Check if already exists
        result = await session.execute(select(RelationType).where(RelationType.slug == rt_data["slug"]))
        existing = result.scalar_one_or_none()

        if existing:
            relation_type_ids[rt_data["slug"]] = existing.id
            continue

        relation_type = RelationType(
            id=uuid.uuid4(),
            **rt_data,
        )
        session.add(relation_type)
        relation_type_ids[rt_data["slug"]] = relation_type.id

    await session.flush()
    return relation_type_ids


async def seed_analysis_templates(session, entity_type_ids: dict, facet_type_ids: dict):
    """Seed analysis templates."""

    # Get default category if exists
    result = await session.execute(select(Category).limit(1))
    default_category = result.scalar_one_or_none()
    category_id = default_category.id if default_category else None

    templates = [
        {
            "name": "Windkraft Gemeinde-Analyse",
            "slug": "windkraft-gemeinde-analyse",
            "description": "Analyse von Gebietskörperschaften auf Windkraft-relevante Pain Points, positive Signale und Entscheider",
            "category_id": category_id,
            "primary_entity_type_id": entity_type_ids["territorial_entity"],
            "facet_config": [
                {"facet_type_slug": "pain_point", "enabled": True, "display_order": 1, "label": "Pain Points"},
                {
                    "facet_type_slug": "positive_signal",
                    "enabled": True,
                    "display_order": 2,
                    "label": "Positive Signale",
                },
                {"facet_type_slug": "contact", "enabled": True, "display_order": 3, "label": "Entscheider"},
                {"facet_type_slug": "summary", "enabled": True, "display_order": 4},
            ],
            "aggregation_config": {
                "group_by": "entity",
                "show_relations": ["works_for"],
                "sort_by": "name",
            },
            "display_config": {
                "columns": ["name", "admin_level_1", "pain_point_count", "positive_signal_count", "contact_count"],
                "default_sort": "name",
                "show_hierarchy": True,
            },
            "is_default": True,
            "is_system": True,
        },
        {
            "name": "Event-Tracking",
            "slug": "event-tracking",
            "description": "Tracking welche Entscheider auf welche Veranstaltungen gehen",
            "primary_entity_type_id": entity_type_ids["event"],
            "facet_config": [
                {
                    "facet_type_slug": "event_attendance",
                    "enabled": True,
                    "display_order": 1,
                    "time_filter": "future_only",
                },
            ],
            "aggregation_config": {
                "group_by": "entity",
                "show_relations": ["attends", "located_in"],
                "sort_by": "event_date",
            },
            "display_config": {
                "columns": ["name", "event_date", "location", "attendee_count"],
                "default_sort": "event_date",
                "show_hierarchy": False,
            },
            "is_default": False,
            "is_system": True,
        },
        {
            "name": "Personen-Profil",
            "slug": "personen-profil",
            "description": "Uebersicht ueber Personen und ihre Aktivitaeten",
            "primary_entity_type_id": entity_type_ids["person"],
            "facet_config": [
                {"facet_type_slug": "event_attendance", "enabled": True, "display_order": 1},
                {"facet_type_slug": "contact", "enabled": True, "display_order": 2},
            ],
            "aggregation_config": {
                "group_by": "entity",
                "show_relations": ["works_for", "attends", "member_of"],
                "sort_by": "name",
            },
            "display_config": {
                "columns": ["name", "role", "organization", "event_count"],
                "default_sort": "name",
            },
            "is_default": False,
            "is_system": True,
        },
    ]

    for tmpl_data in templates:
        # Check if already exists
        result = await session.execute(select(AnalysisTemplate).where(AnalysisTemplate.slug == tmpl_data["slug"]))
        existing = result.scalar_one_or_none()

        if existing:
            continue

        template = AnalysisTemplate(
            id=uuid.uuid4(),
            **tmpl_data,
        )
        session.add(template)

    await session.flush()


async def main():
    """Main seed function."""

    async with get_session_context() as session:
        try:
            # Seed in order (respecting FK dependencies)
            entity_type_ids = await seed_entity_types(session)
            facet_type_ids = await seed_facet_types(session)
            await seed_relation_types(session, entity_type_ids)
            await seed_analysis_templates(session, entity_type_ids, facet_type_ids)

            await session.commit()

        except Exception:
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())
