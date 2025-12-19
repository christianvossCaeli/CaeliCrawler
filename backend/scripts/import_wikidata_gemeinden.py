#!/usr/bin/env python3
"""
Import German municipalities from Wikidata as locations and website data sources.

This script queries Wikidata for all German municipalities (Gemeinden) that have
an official website and imports them as:
1. Locations (for the location dropdown)
2. Data sources (for web scraping)

Usage:
    python -m scripts.import_wikidata_gemeinden [--bundesland NRW] [--limit 100] [--dry-run]
    docker compose exec backend python -m scripts.import_wikidata_gemeinden --bundesland NRW
"""

import asyncio
import argparse
import httpx
import uuid
from typing import List, Dict, Optional
from uuid import UUID

# Wikidata SPARQL endpoint
WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"

# SPARQL query for German municipalities with websites
# P31 = instance of, P279 = subclass of
# Q262166 = municipality of Germany
# Q42744322 = urban municipality of Germany
# Q116457956 = rural municipality of Germany
# P856 = official website
# P439 = German municipality key (AGS)
# P131 = located in administrative territorial entity (for Bundesland)
# P1082 = population

SPARQL_QUERY = """
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

    # Muss eine Website haben
    ?gemeinde wdt:P856 ?website .

    # Optional: AGS (Gemeindeschlüssel)
    OPTIONAL { ?gemeinde wdt:P439 ?ags }

    # Optional: Einwohnerzahl
    OPTIONAL { ?gemeinde wdt:P1082 ?population }

    # Optional: Bundesland (über Verwaltungshierarchie)
    OPTIONAL {
        ?gemeinde wdt:P131* ?bundesland .
        ?bundesland wdt:P31 wd:Q1221156 .  # Bundesland
    }

    SERVICE wikibase:label { bd:serviceParam wikibase:language "de,en" }
}
ORDER BY ?bundeslandLabel ?gemeindeLabel
"""

# Bundesland filter query - simplified, uses located in state property
SPARQL_QUERY_BUNDESLAND = """
SELECT DISTINCT
    ?gemeinde
    ?gemeindeLabel
    ?website
    ?ags
WHERE {{
    ?gemeinde wdt:P31/wdt:P279* wd:Q262166 .
    ?gemeinde wdt:P856 ?website .
    ?gemeinde wdt:P439 ?ags .
    FILTER(STRSTARTS(?ags, "{ags_prefix}"))

    SERVICE wikibase:label {{ bd:serviceParam wikibase:language "de,en" }}
}}
ORDER BY ?gemeindeLabel
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

# Wikidata QIDs for German Bundesländer
BUNDESLAND_QIDS = {
    "BW": "Q985",      # Baden-Württemberg
    "BY": "Q980",      # Bayern
    "BE": "Q64",       # Berlin
    "BB": "Q1208",     # Brandenburg
    "HB": "Q1209",     # Bremen
    "HH": "Q1055",     # Hamburg
    "HE": "Q1199",     # Hessen
    "MV": "Q1196",     # Mecklenburg-Vorpommern
    "NI": "Q1197",     # Niedersachsen
    "NRW": "Q1198",    # Nordrhein-Westfalen
    "RP": "Q1200",     # Rheinland-Pfalz
    "SL": "Q1201",     # Saarland
    "SN": "Q1202",     # Sachsen
    "ST": "Q1206",     # Sachsen-Anhalt
    "SH": "Q1194",     # Schleswig-Holstein
    "TH": "Q1205",     # Thüringen
}


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
        query = SPARQL_QUERY
        print("Fetching all German municipalities...")

    if limit:
        query += f"\nLIMIT {limit}"

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.get(
            WIKIDATA_ENDPOINT,
            params={"query": query, "format": "json"},
            headers={"User-Agent": "CaeliCrawler/1.0 (Wind Energy Sales Intelligence)"}
        )
        response.raise_for_status()
        data = response.json()

    results = []
    seen_websites = set()

    for binding in data.get("results", {}).get("bindings", []):
        website = binding.get("website", {}).get("value", "")

        # Skip duplicates
        if website in seen_websites:
            continue
        seen_websites.add(website)

        # Extract data
        result = {
            "wikidata_id": binding.get("gemeinde", {}).get("value", "").split("/")[-1],
            "name": binding.get("gemeindeLabel", {}).get("value", ""),
            "website": website,
            "ags": binding.get("ags", {}).get("value"),
            "population": binding.get("population", {}).get("value"),
            "bundesland": binding.get("bundeslandLabel", {}).get("value"),
        }

        # Clean up website URL
        if result["website"]:
            # Ensure https
            if result["website"].startswith("http://"):
                result["website"] = result["website"].replace("http://", "https://")
            results.append(result)

    return results


def normalize_name(name: str, country: str = "DE") -> str:
    """Normalize location name for search."""
    result = name.lower()
    if country == "DE":
        replacements = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}
        for old, new in replacements.items():
            result = result.replace(old, new)
    return result


def get_bundesland_from_ags(ags: str) -> Optional[str]:
    """Get Bundesland name from AGS prefix."""
    if not ags or len(ags) < 2:
        return None

    prefix_to_land = {
        "01": "Schleswig-Holstein",
        "02": "Hamburg",
        "03": "Niedersachsen",
        "04": "Bremen",
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
    return prefix_to_land.get(ags[:2])


async def import_locations_from_gemeinden(
    gemeinden: List[Dict],
    dry_run: bool = False,
) -> Dict:
    """Import municipalities as locations."""

    if dry_run:
        print(f"\n[DRY RUN] Would import {len(gemeinden)} locations")
        return {"locations_created": 0, "locations_skipped": 0}

    from app.database import async_session_factory
    from app.models import Location
    from sqlalchemy import select

    stats = {"locations_created": 0, "locations_skipped": 0, "locations_errors": 0}

    # Track AGS codes we've already seen in this batch
    seen_ags_codes = set()

    for gemeinde in gemeinden:
        ags = gemeinde.get("ags")
        if not ags:
            continue

        # Skip duplicates within this batch
        if ags in seen_ags_codes:
            stats["locations_skipped"] += 1
            continue
        seen_ags_codes.add(ags)

        try:
            async with async_session_factory() as session:
                # Check if location already exists
                existing = await session.execute(
                    select(Location).where(
                        Location.country == "DE",
                        Location.official_code == ags
                    )
                )
                if existing.scalar_one_or_none():
                    stats["locations_skipped"] += 1
                    continue

                # Get bundesland from AGS if not provided
                bundesland = gemeinde.get("bundesland") or get_bundesland_from_ags(ags)

                # Create location
                population = gemeinde.get("population")
                if population:
                    try:
                        population = int(float(population))
                    except (ValueError, TypeError):
                        population = None

                location = Location(
                    id=uuid.uuid4(),
                    country="DE",
                    official_code=ags,
                    name=gemeinde["name"],
                    name_normalized=normalize_name(gemeinde["name"]),
                    admin_level_1=bundesland,
                    admin_level_2=None,  # Could be filled from district data
                    locality_type="municipality",
                    country_metadata={"wikidata_id": gemeinde.get("wikidata_id")},
                    population=population,
                    is_active=True,
                )
                session.add(location)
                await session.commit()
                stats["locations_created"] += 1

                if stats["locations_created"] % 500 == 0:
                    print(f"  Created {stats['locations_created']} locations...")

        except Exception as e:
            print(f"  Error creating location {gemeinde['name']}: {e}")
            stats["locations_errors"] += 1

    return stats


async def import_gemeinden(
    gemeinden: List[Dict],
    category_id: UUID,
    dry_run: bool = False,
) -> Dict:
    """Import municipalities as data sources."""

    if dry_run:
        print(f"\n[DRY RUN] Would import {len(gemeinden)} data sources")
        for g in gemeinden[:10]:
            print(f"  - {g['name']}: {g['website']}")
        if len(gemeinden) > 10:
            print(f"  ... and {len(gemeinden) - 10} more")
        return {"sources_imported": 0, "sources_skipped": 0, "sources_errors": 0}

    from app.database import async_session_factory
    from app.models import DataSource, SourceType, SourceStatus, Location
    from sqlalchemy import select

    stats = {"sources_imported": 0, "sources_skipped": 0, "sources_errors": 0}

    # Track URLs we've already seen in this batch
    seen_urls = set()

    for gemeinde in gemeinden:
        url = gemeinde["website"]

        # Skip duplicates within this batch
        if url in seen_urls:
            stats["sources_skipped"] += 1
            continue
        seen_urls.add(url)

        try:
            async with async_session_factory() as session:
                # Check if already exists (by URL in same category)
                existing = await session.execute(
                    select(DataSource).where(
                        DataSource.category_id == category_id,
                        DataSource.base_url == url
                    )
                )
                if existing.scalar_one_or_none():
                    stats["sources_skipped"] += 1
                    continue

                # Try to find the location
                location_id = None
                ags = gemeinde.get("ags")
                if ags:
                    loc_result = await session.execute(
                        select(Location).where(
                            Location.country == "DE",
                            Location.official_code == ags
                        )
                    )
                    location = loc_result.scalar_one_or_none()
                    if location:
                        location_id = location.id

                # Get bundesland
                bundesland = gemeinde.get("bundesland") or get_bundesland_from_ags(ags)

                # Create data source
                source = DataSource(
                    category_id=category_id,
                    name=f"{gemeinde['name']} - Kommunale Website",
                    source_type=SourceType.WEBSITE,
                    base_url=url,
                    country="DE",
                    location_id=location_id,
                    location_name=gemeinde["name"],
                    admin_level_1=bundesland,
                    status=SourceStatus.ACTIVE,
                    priority=5,
                    crawl_config={
                        "max_depth": 3,
                        "max_pages": 200,
                        "download_extensions": ["pdf", "doc", "docx"],
                        "filter_keywords": [
                            "wind", "windkraft", "windenergie", "windrad",
                            "flächennutzung", "bebauungsplan", "bauleitplan",
                            "erneuerbare", "energie", "klimaschutz",
                            "genehmigung", "bauantrag"
                        ],
                        "render_javascript": False,
                    },
                    extra_data={
                        "wikidata_id": gemeinde["wikidata_id"],
                        "ags": gemeinde.get("ags"),
                        "population": gemeinde.get("population"),
                    }
                )
                session.add(source)
                await session.commit()
                stats["sources_imported"] += 1

                if stats["sources_imported"] % 500 == 0:
                    print(f"  Imported {stats['sources_imported']} sources...")

        except Exception as e:
            print(f"  Error importing source {gemeinde['name']}: {e}")
            stats["sources_errors"] += 1

    return stats


async def main():
    parser = argparse.ArgumentParser(
        description="Import German municipalities from Wikidata"
    )
    parser.add_argument(
        "--bundesland", "-b",
        help="Filter by Bundesland (e.g., NRW, BY, NI)",
        default=None
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        help="Limit number of municipalities to import",
        default=None
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Don't actually import, just show what would be done"
    )
    parser.add_argument(
        "--category",
        help="Category slug to use (default: kommunale-news)",
        default="kommunale-news"
    )
    parser.add_argument(
        "--locations-only",
        action="store_true",
        help="Only import locations, skip data sources"
    )
    parser.add_argument(
        "--sources-only",
        action="store_true",
        help="Only import data sources, skip locations"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Wikidata Gemeinden Import")
    print("=" * 60)

    # Fetch from Wikidata
    gemeinden = await fetch_gemeinden_from_wikidata(
        bundesland=args.bundesland,
        limit=args.limit,
    )
    print(f"\nFound {len(gemeinden)} municipalities with websites")

    if not gemeinden:
        print("No municipalities found!")
        return

    # Show sample
    print("\nSample municipalities:")
    for g in gemeinden[:5]:
        pop = f" (Pop: {int(float(g['population'])):,})" if g.get('population') else ""
        ags = f" [AGS: {g['ags']}]" if g.get('ags') else ""
        print(f"  - {g['name']}{pop}{ags}: {g['website']}")

    # STEP 1: Import locations (unless --sources-only)
    location_stats = {"locations_created": 0, "locations_skipped": 0, "locations_errors": 0}
    if not args.sources_only:
        print("\n--- Step 1: Importing Locations ---")
        location_stats = await import_locations_from_gemeinden(
            gemeinden,
            dry_run=args.dry_run,
        )
        print(f"  Locations created: {location_stats.get('locations_created', 0)}")
        print(f"  Locations skipped: {location_stats.get('locations_skipped', 0)}")
        if location_stats.get('locations_errors', 0) > 0:
            print(f"  Locations errors: {location_stats['locations_errors']}")

    # STEP 2: Import data sources (unless --locations-only)
    source_stats = {"sources_imported": 0, "sources_skipped": 0, "sources_errors": 0}
    if not args.locations_only:
        category_id = None
        if not args.dry_run:
            # Get category
            from app.database import async_session_factory
            from app.models import Category
            from sqlalchemy import select

            async with async_session_factory() as session:
                result = await session.execute(
                    select(Category).where(Category.slug == args.category)
                )
                category = result.scalar_one_or_none()

                if not category:
                    print(f"\nWarning: Category '{args.category}' not found!")
                    print("Creating category first with seed_data.py or manually")
                    print("Skipping data source import.")
                else:
                    category_id = category.id
                    print(f"\n--- Step 2: Importing Data Sources ---")
                    print(f"  Target category: {args.category}")

        if category_id or args.dry_run:
            source_stats = await import_gemeinden(
                gemeinden,
                category_id,
                dry_run=args.dry_run,
            )
            print(f"  Sources imported: {source_stats.get('sources_imported', 0)}")
            print(f"  Sources skipped: {source_stats.get('sources_skipped', 0)}")
            if source_stats.get('sources_errors', 0) > 0:
                print(f"  Sources errors: {source_stats['sources_errors']}")

    print("\n" + "=" * 60)
    print("Import Summary")
    print("=" * 60)
    if not args.sources_only:
        print(f"  Locations created: {location_stats.get('locations_created', 0)}")
        print(f"  Locations skipped: {location_stats.get('locations_skipped', 0)}")
    if not args.locations_only:
        print(f"  Sources imported: {source_stats.get('sources_imported', 0)}")
        print(f"  Sources skipped: {source_stats.get('sources_skipped', 0)}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
