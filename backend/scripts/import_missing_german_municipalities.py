#!/usr/bin/env python3
"""
Import missing German municipalities from Wikidata as Entity records.

This script queries Wikidata for all German municipalities and imports those
not yet in the entities table, using the municipality EntityType.

Usage:
    python -m scripts.import_missing_german_municipalities [--bundesland NRW] [--limit 100] [--dry-run]
    docker compose exec backend python -m scripts.import_missing_german_municipalities --bundesland NRW
"""

import asyncio
import argparse
import httpx
import uuid
import unicodedata
import re
from typing import List, Dict, Optional, Set
from uuid import UUID

# Wikidata SPARQL endpoint
WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"

# SPARQL query for ALL German municipalities (not just those with websites)
SPARQL_QUERY_ALL = """
SELECT DISTINCT
    ?gemeinde
    ?gemeindeLabel
    ?website
    ?ags
    ?population
    ?bundeslandLabel
WHERE {
    # Gemeinde in Deutschland (inkl. Subklassen)
    ?gemeinde wdt:P31/wdt:P279* wd:Q262166 .

    # Must have AGS (Gemeindeschlüssel)
    ?gemeinde wdt:P439 ?ags .

    # Optional: Website
    OPTIONAL { ?gemeinde wdt:P856 ?website }

    # Optional: Einwohnerzahl
    OPTIONAL { ?gemeinde wdt:P1082 ?population }

    # Optional: Bundesland (über Verwaltungshierarchie)
    OPTIONAL {
        ?gemeinde wdt:P131* ?bundesland .
        ?bundesland wdt:P31 wd:Q1221156 .  # Bundesland
    }

    SERVICE wikibase:label { bd:serviceParam wikibase:language "de,en" }
}
ORDER BY ?ags
"""

# Bundesland filter query
SPARQL_QUERY_BUNDESLAND = """
SELECT DISTINCT
    ?gemeinde
    ?gemeindeLabel
    ?website
    ?ags
    ?population
WHERE {{
    ?gemeinde wdt:P31/wdt:P279* wd:Q262166 .
    ?gemeinde wdt:P439 ?ags .
    FILTER(STRSTARTS(?ags, "{ags_prefix}"))

    OPTIONAL {{ ?gemeinde wdt:P856 ?website }}
    OPTIONAL {{ ?gemeinde wdt:P1082 ?population }}

    SERVICE wikibase:label {{ bd:serviceParam wikibase:language "de,en" }}
}}
ORDER BY ?ags
"""

# AGS prefixes for Bundesländer (first 2 digits of Gemeindeschlüssel)
BUNDESLAND_AGS_PREFIX = {
    "SH": "01",   # Schleswig-Holstein
    "HH": "02",   # Hamburg
    "NI": "03",   # Niedersachsen
    "HB": "04",   # Bremen
    "NRW": "05",  # Nordrhein-Westfalen
    "HE": "06",   # Hessen
    "RP": "07",   # Rheinland-Pfalz
    "BW": "08",   # Baden-Württemberg
    "BY": "09",   # Bayern
    "SL": "10",   # Saarland
    "BE": "11",   # Berlin
    "BB": "12",   # Brandenburg
    "MV": "13",   # Mecklenburg-Vorpommern
    "SN": "14",   # Sachsen
    "ST": "15",   # Sachsen-Anhalt
    "TH": "16",   # Thüringen
}

# Reverse mapping: AGS prefix to Bundesland name
AGS_TO_BUNDESLAND = {
    "01": "Schleswig-Holstein",
    "02": "Hamburg",
    "03": "Niedersachsen",
    "04": "Freie Hansestadt Bremen",
    "05": "Nordrhein-Westfalen",
    "06": "Hessen",
    "07": "Rheinland-Pfalz",
    "08": "Baden-Württemberg",
    "09": "Bayern",
    "10": "Saarland",
    "11": "Berlin",
    "12": "Brandenburg",
    "13": "Mecklenburg-Vorpommern",
    "14": "Sachsen",
    "15": "Sachsen-Anhalt",
    "16": "Thüringen",
}


def generate_slug(name: str) -> str:
    """Generate URL-friendly slug from name."""
    slug = name.lower()
    slug = re.sub(
        r"[äöüß]",
        lambda m: {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}[m.group()],
        slug,
    )
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug


def normalize_name(name: str) -> str:
    """
    Normalize name for search (lowercase, ASCII).

    Uses centralized normalization to ensure consistency with entity_facet_service.
    This prevents duplicate entities caused by different normalization methods.
    """
    # Import here to avoid circular imports during script execution
    try:
        from app.utils.text import normalize_entity_name
        return normalize_entity_name(name, country="DE")
    except ImportError:
        # Fallback for standalone execution - use same algorithm
        result = name.lower()
        # German umlauts
        replacements = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}
        for old, new in replacements.items():
            result = result.replace(old, new)
        # Remove diacritics
        result = unicodedata.normalize("NFD", result)
        result = "".join(c for c in result if not unicodedata.combining(c))
        # Remove non-alphanumeric
        result = re.sub(r"[^a-z0-9]", "", result)
        return result


def get_bundesland_from_ags(ags: str) -> Optional[str]:
    """Get Bundesland name from AGS prefix."""
    if not ags or len(ags) < 2:
        return None
    return AGS_TO_BUNDESLAND.get(ags[:2])


async def fetch_gemeinden_from_wikidata(
    bundesland: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict]:
    """Fetch municipalities from Wikidata."""

    if bundesland and bundesland.upper() in BUNDESLAND_AGS_PREFIX:
        query = SPARQL_QUERY_BUNDESLAND.format(
            ags_prefix=BUNDESLAND_AGS_PREFIX[bundesland.upper()]
        )
        print(f"Fetching municipalities for {bundesland} (AGS prefix: {BUNDESLAND_AGS_PREFIX[bundesland.upper()]})...")
    else:
        query = SPARQL_QUERY_ALL
        print("Fetching ALL German municipalities from Wikidata...")

    if limit:
        query += f"\nLIMIT {limit}"

    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.get(
            WIKIDATA_ENDPOINT,
            params={"query": query, "format": "json"},
            headers={"User-Agent": "CaeliCrawler/1.0 (Wind Energy Sales Intelligence)"}
        )
        response.raise_for_status()
        data = response.json()

    results = []
    seen_ags = set()

    for binding in data.get("results", {}).get("bindings", []):
        ags = binding.get("ags", {}).get("value", "")

        # Skip if no AGS or duplicate
        if not ags or ags in seen_ags:
            continue
        seen_ags.add(ags)

        # Extract data
        result = {
            "wikidata_id": binding.get("gemeinde", {}).get("value", "").split("/")[-1],
            "name": binding.get("gemeindeLabel", {}).get("value", ""),
            "website": binding.get("website", {}).get("value"),
            "ags": ags,
            "population": binding.get("population", {}).get("value"),
            "bundesland": binding.get("bundeslandLabel", {}).get("value"),
        }

        # Ensure bundesland from AGS if not from Wikidata
        if not result["bundesland"]:
            result["bundesland"] = get_bundesland_from_ags(ags)

        if result["name"]:  # Only add if has a name
            results.append(result)

    return results


async def get_existing_entities() -> Dict[str, Dict]:
    """Get existing municipality entities mapped by normalized name."""
    from app.database import async_session_factory
    from app.models import Entity, EntityType
    from sqlalchemy import select

    async with async_session_factory() as session:
        # Get municipality entity type
        et_result = await session.execute(
            select(EntityType).where(EntityType.slug == "municipality")
        )
        entity_type = et_result.scalar_one_or_none()

        if not entity_type:
            print("Warning: 'municipality' entity type not found!")
            return {}

        # Get all existing entities with their normalized names
        result = await session.execute(
            select(Entity.id, Entity.name, Entity.name_normalized, Entity.external_id, Entity.country).where(
                Entity.entity_type_id == entity_type.id
            )
        )
        entities = {}
        for row in result.fetchall():
            key = row.name_normalized.lower().strip()
            entities[key] = {
                "id": row.id,
                "name": row.name,
                "external_id": row.external_id,
                "country": row.country
            }
        return entities


async def get_municipality_entity_type_id() -> Optional[UUID]:
    """Get the municipality entity type ID."""
    from app.database import async_session_factory
    from app.models import EntityType
    from sqlalchemy import select

    async with async_session_factory() as session:
        result = await session.execute(
            select(EntityType).where(EntityType.slug == "municipality")
        )
        entity_type = result.scalar_one_or_none()
        return entity_type.id if entity_type else None


async def update_existing_and_import_missing(
    gemeinden: List[Dict],
    existing_entities: Dict[str, Dict],
    entity_type_id: UUID,
    dry_run: bool = False,
) -> Dict:
    """Update existing entities with AGS codes and import missing ones."""

    to_update = []
    to_create = []

    for gemeinde in gemeinden:
        name = gemeinde["name"]
        ags = gemeinde["ags"]
        name_norm = normalize_name(name).lower().strip()

        # Check if entity exists by normalized name (DE entities only)
        if name_norm in existing_entities:
            existing = existing_entities[name_norm]
            # Only update DE entities that don't have external_id yet
            if existing["country"] == "DE" and not existing["external_id"]:
                to_update.append({
                    "id": existing["id"],
                    "name": existing["name"],
                    "ags": ags,
                    "bundesland": gemeinde.get("bundesland") or get_bundesland_from_ags(ags),
                    "population": gemeinde.get("population"),
                    "website": gemeinde.get("website"),
                    "wikidata_id": gemeinde.get("wikidata_id"),
                })
        else:
            to_create.append(gemeinde)

    print(f"\n  Entities to update (add AGS): {len(to_update)}")
    print(f"  Entities to create (new): {len(to_create)}")

    if dry_run:
        print(f"\n[DRY RUN] Would update {len(to_update)} and create {len(to_create)} entities")
        if to_update:
            print("\nUpdates (first 10):")
            for item in to_update[:10]:
                print(f"  - {item['name']} -> AGS: {item['ags']}")
        if to_create:
            print("\nNew entities (first 10):")
            for g in to_create[:10]:
                bl = g.get("bundesland") or "Unknown"
                print(f"  - {g['name']} ({bl}) [AGS: {g['ags']}]")
            if len(to_create) > 10:
                print(f"  ... and {len(to_create) - 10} more")
        return {"updated": 0, "created": 0, "errors": 0}

    from app.database import async_session_factory
    from app.models import Entity
    from sqlalchemy import select

    stats = {"updated": 0, "created": 0, "errors": 0}

    # Step 1: Update existing entities with AGS codes
    print("\n  Updating existing entities with AGS codes...")
    for item in to_update:
        try:
            async with async_session_factory() as session:
                entity = await session.get(Entity, item["id"])
                if entity:
                    entity.external_id = item["ags"]

                    # Also update core_attributes
                    core_attrs = dict(entity.core_attributes) if entity.core_attributes else {}
                    core_attrs["official_code"] = item["ags"]
                    if item.get("wikidata_id"):
                        core_attrs["wikidata_id"] = item["wikidata_id"]
                    if item.get("website"):
                        core_attrs["website"] = item["website"]
                    if item.get("population"):
                        try:
                            core_attrs["population"] = int(float(item["population"]))
                        except (ValueError, TypeError):
                            pass
                    entity.core_attributes = core_attrs

                    await session.commit()
                    stats["updated"] += 1

                    if stats["updated"] % 500 == 0:
                        print(f"    Updated {stats['updated']} entities...")
        except Exception as e:
            print(f"    Error updating {item['name']}: {e}")
            stats["errors"] += 1

    # Step 2: Create new entities
    print(f"\n  Creating {len(to_create)} new entities...")
    for gemeinde in to_create:
        try:
            async with async_session_factory() as session:
                name = gemeinde["name"]
                ags = gemeinde["ags"]
                bundesland = gemeinde.get("bundesland") or get_bundesland_from_ags(ags)

                # Check for duplicate slug within municipality type
                slug = generate_slug(name)
                existing = await session.execute(
                    select(Entity).where(
                        Entity.entity_type_id == entity_type_id,
                        Entity.slug == slug
                    )
                )
                if existing.scalar_one_or_none():
                    # Make slug unique by adding AGS
                    slug = f"{slug}-{ags}"

                # Parse population
                population = None
                if gemeinde.get("population"):
                    try:
                        population = int(float(gemeinde["population"]))
                    except (ValueError, TypeError):
                        pass

                # Build core_attributes
                core_attributes = {
                    "official_code": ags,
                    "locality_type": "municipality",
                }
                if gemeinde.get("wikidata_id"):
                    core_attributes["wikidata_id"] = gemeinde["wikidata_id"]
                if gemeinde.get("website"):
                    core_attributes["website"] = gemeinde["website"]
                if population:
                    core_attributes["population"] = population

                # Create entity
                entity = Entity(
                    id=uuid.uuid4(),
                    entity_type_id=entity_type_id,
                    name=name,
                    name_normalized=normalize_name(name),
                    slug=slug,
                    external_id=ags,
                    country="DE",
                    admin_level_1=bundesland,
                    admin_level_2=None,
                    hierarchy_path=f"/{slug}",
                    hierarchy_level=0,
                    core_attributes=core_attributes,
                    is_active=True,
                )
                session.add(entity)
                await session.commit()
                stats["created"] += 1

                if stats["created"] % 500 == 0:
                    print(f"    Created {stats['created']} entities...")

        except Exception as e:
            print(f"    Error creating entity {gemeinde['name']}: {e}")
            stats["errors"] += 1

    return stats


async def main():
    parser = argparse.ArgumentParser(
        description="Import missing German municipalities from Wikidata as Entity records"
    )
    parser.add_argument(
        "--bundesland", "-b",
        help="Filter by Bundesland (e.g., NRW, BY, NI)",
        default=None
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        help="Limit number of municipalities to fetch",
        default=None
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Don't actually import, just show what would be done"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Import/Update German Municipalities from Wikidata")
    print("=" * 60)

    # Step 1: Get existing entities
    print("\nStep 1: Loading existing entities...")
    existing_entities = await get_existing_entities()
    de_entities = sum(1 for e in existing_entities.values() if e["country"] == "DE")
    with_ags = sum(1 for e in existing_entities.values() if e["external_id"])
    print(f"  Found {len(existing_entities)} existing municipality entities")
    print(f"  - DE entities: {de_entities}")
    print(f"  - With AGS code: {with_ags}")

    # Step 2: Get municipality entity type
    entity_type_id = await get_municipality_entity_type_id()
    if not entity_type_id:
        print("\nERROR: 'municipality' entity type not found!")
        print("Please run seed_entity_facet_system.py first.")
        return

    # Step 3: Fetch from Wikidata
    print("\nStep 2: Fetching from Wikidata...")
    gemeinden = await fetch_gemeinden_from_wikidata(
        bundesland=args.bundesland,
        limit=args.limit,
    )
    print(f"  Found {len(gemeinden)} municipalities in Wikidata")

    if not gemeinden:
        print("No municipalities found in Wikidata!")
        return

    # Show sample
    print("\nSample municipalities from Wikidata:")
    for g in gemeinden[:5]:
        bl = g.get("bundesland") or "Unknown"
        name_norm = normalize_name(g["name"]).lower().strip()
        status = "EXISTS" if name_norm in existing_entities else "NEW"
        print(f"  [{status}] {g['name']} ({bl}) [AGS: {g['ags']}]")

    # Step 4: Update existing and import missing
    print("\nStep 3: Processing municipalities...")
    stats = await update_existing_and_import_missing(
        gemeinden,
        existing_entities,
        entity_type_id,
        dry_run=args.dry_run,
    )

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"  Entities updated (AGS added): {stats['updated']}")
    print(f"  Entities created (new): {stats['created']}")
    if stats['errors'] > 0:
        print(f"  Errors: {stats['errors']}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
