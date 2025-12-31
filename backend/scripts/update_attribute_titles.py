#!/usr/bin/env python3
"""
Update script to add German titles to existing entity type attribute schemas.

Run with: python -m scripts.update_attribute_titles
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.database import get_session_context
from app.models import EntityType

# Location fields that map to Entity columns (not core_attributes)
# These are treated specially by the filter system
LOCATION_FIELDS = {
    "country": {"type": "string", "title": "Land", "description": "ISO 3166-1 alpha-2 Laendercode"},
    "admin_level_1": {"type": "string", "title": "Region", "description": "Bundesland / Region"},
    "admin_level_2": {"type": "string", "title": "Bezirk", "description": "Landkreis / Bezirk"},
}

# Define the updated attribute schemas with German titles
ATTRIBUTE_SCHEMAS = {
    "municipality": {
        "type": "object",
        "properties": {
            # Location fields first
            **LOCATION_FIELDS,
            # Then type-specific attributes
            "population": {"type": "integer", "title": "Einwohner", "description": "Einwohnerzahl"},
            "area_km2": {"type": "number", "title": "Flaeche (km²)", "description": "Flaeche in km2"},
            "official_code": {"type": "string", "title": "Amtlicher Schluessel", "description": "AGS/GSS Code"},
            "locality_type": {"type": "string", "title": "Ortstyp", "description": "Art (Stadt, Gemeinde, etc.)"},
            "website": {"type": "string", "title": "Website", "description": "Offizielle Website"},
        },
    },
    "person": {
        "type": "object",
        "properties": {
            # Location fields
            **LOCATION_FIELDS,
            # Type-specific attributes
            "academic_title": {"type": "string", "title": "Titel", "description": "Titel (Dr., Prof., etc.)"},
            "first_name": {"type": "string", "title": "Vorname"},
            "last_name": {"type": "string", "title": "Nachname"},
            "email": {"type": "string", "title": "E-Mail", "format": "email"},
            "phone": {"type": "string", "title": "Telefon"},
            "role": {"type": "string", "title": "Position", "description": "Aktuelle Rolle/Position"},
        },
    },
    "organization": {
        "type": "object",
        "properties": {
            # Location fields
            **LOCATION_FIELDS,
            # Type-specific attributes
            "org_type": {"type": "string", "title": "Organisationstyp", "description": "Typ (Unternehmen, Verband, etc.)"},
            "website": {"type": "string", "title": "Website"},
            "email": {"type": "string", "title": "E-Mail", "format": "email"},
            "address": {"type": "string", "title": "Adresse"},
        },
    },
    "event": {
        "type": "object",
        "properties": {
            # Location fields
            **LOCATION_FIELDS,
            # Type-specific attributes
            "event_date": {"type": "string", "title": "Startdatum", "format": "date-time"},
            "event_end_date": {"type": "string", "title": "Enddatum", "format": "date-time"},
            "location": {"type": "string", "title": "Ort"},
            "organizer": {"type": "string", "title": "Veranstalter"},
            "event_type": {"type": "string", "title": "Veranstaltungstyp", "description": "Messe, Konferenz, Workshop, etc."},
            "website": {"type": "string", "title": "Website"},
            "description": {"type": "string", "title": "Beschreibung"},
        },
    },
}


async def update_entity_type_schemas():
    """Update attribute schemas for existing entity types."""

    async with get_session_context() as session:
        for slug, new_schema in ATTRIBUTE_SCHEMAS.items():
            result = await session.execute(
                select(EntityType).where(EntityType.slug == slug)
            )
            entity_type = result.scalar_one_or_none()

            if entity_type:
                entity_type.attribute_schema = new_schema
            else:
                pass

        await session.commit()


if __name__ == "__main__":
    asyncio.run(update_entity_type_schemas())
