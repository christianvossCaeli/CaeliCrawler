#!/usr/bin/env python3
"""
Import UK local authorities from Wikidata as locations and website data sources.

This script queries Wikidata for UK local authorities (councils) that have
an official website and imports them as:
1. Locations (for the location dropdown)
2. Data sources (for web scraping)

Usage:
    python -m scripts.import_wikidata_uk [--country england|scotland|wales|ni] [--limit 100] [--dry-run]
    docker compose exec backend python -m scripts.import_wikidata_uk --country england
"""

import asyncio
import argparse
import httpx
import uuid
from typing import List, Dict, Optional

# Wikidata SPARQL endpoint
WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"

# SPARQL query for UK local authorities with websites
# Q15060255 = local authority of the United Kingdom
# Q1187580 = local authority of England
# Q15060266 = local authority of Scotland
# Q15060277 = local authority of Wales
# Q15060282 = district council of Northern Ireland
# P856 = official website
# P836 = GSS code (UK geography code)
# P131 = located in administrative territorial entity

SPARQL_QUERY_UK = """
SELECT DISTINCT
    ?council
    ?councilLabel
    ?website
    ?gss_code
    ?population
    ?countryLabel
WHERE {{
    # UK local authorities (various types)
    {{
        ?council wdt:P31/wdt:P279* wd:Q15060255 .  # local authority of the UK
    }} UNION {{
        ?council wdt:P31/wdt:P279* wd:Q1187580 .   # local authority of England
    }} UNION {{
        ?council wdt:P31/wdt:P279* wd:Q15060266 .  # local authority of Scotland
    }} UNION {{
        ?council wdt:P31/wdt:P279* wd:Q15060277 .  # local authority of Wales
    }} UNION {{
        ?council wdt:P31/wdt:P279* wd:Q15060282 .  # district council of NI
    }}

    # Must have a website
    ?council wdt:P856 ?website .

    # Optional: GSS code
    OPTIONAL {{ ?council wdt:P836 ?gss_code }}

    # Optional: Population
    OPTIONAL {{ ?council wdt:P1082 ?population }}

    # Get country (England, Scotland, Wales, Northern Ireland)
    OPTIONAL {{
        ?council wdt:P131* ?country .
        ?country wdt:P31 wd:Q3624078 .  # country
        FILTER(?country IN (wd:Q21, wd:Q22, wd:Q25, wd:Q26))  # England, Scotland, Wales, NI
    }}

    SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
}}
ORDER BY ?countryLabel ?councilLabel
"""

# Simpler query - get all UK local authorities with websites (no recursive paths)
SPARQL_QUERY_UK_SIMPLE = """
SELECT DISTINCT
    ?council
    ?councilLabel
    ?website
    ?gss_code
    ?population
    ?countryLabel
WHERE {
    # Direct instance of types we care about
    VALUES ?type {
        wd:Q15060255   # local authority of the UK
        wd:Q1187580    # local authority of England
        wd:Q15060266   # local authority of Scotland
        wd:Q15060277   # local authority of Wales
        wd:Q21451686   # London borough
        wd:Q21451695   # metropolitan borough
        wd:Q1136601    # unitary authority
        wd:Q180673     # ceremonial county
        wd:Q1059409    # county council
        wd:Q1115575    # district council
    }
    ?council wdt:P31 ?type .

    # Must have a website
    ?council wdt:P856 ?website .

    # GSS code (UK official code)
    OPTIONAL { ?council wdt:P836 ?gss_code }

    # Population
    OPTIONAL { ?council wdt:P1082 ?population }

    # Country
    OPTIONAL {
        ?council wdt:P17 ?country .
        ?council wdt:P131 ?admin .
        ?admin wdt:P31 wd:Q3624078 .  # is a country
    }

    SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
}
ORDER BY ?councilLabel
"""

# Country QIDs and LA types
UK_COUNTRIES = {
    "england": {"qid": "Q21", "la_type": "Q1187580", "name": "England"},
    "scotland": {"qid": "Q22", "la_type": "Q15060266", "name": "Scotland"},
    "wales": {"qid": "Q25", "la_type": "Q15060277", "name": "Wales"},
    "ni": {"qid": "Q26", "la_type": "Q15060282", "name": "Northern Ireland"},
}


async def fetch_uk_councils_from_wikidata(
    country: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict]:
    """Fetch UK local authorities from Wikidata."""
    # Use simple query to avoid timeouts
    query = SPARQL_QUERY_UK_SIMPLE
    print("Fetching all UK local authorities...")

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

        # Get country from label or parameter
        country_label = binding.get("countryLabel", {}).get("value", "")
        if not country_label and country:
            country_label = UK_COUNTRIES.get(country.lower(), {}).get("name", "")

        # Extract data
        result = {
            "wikidata_id": binding.get("council", {}).get("value", "").split("/")[-1],
            "name": binding.get("councilLabel", {}).get("value", ""),
            "website": website,
            "gss_code": binding.get("gss_code", {}).get("value"),
            "population": binding.get("population", {}).get("value"),
            "admin_level_1": country_label,
        }

        # Clean up website URL
        if result["website"]:
            # Ensure https
            if result["website"].startswith("http://"):
                result["website"] = result["website"].replace("http://", "https://")
            results.append(result)

    return results


def normalize_name(name: str, country: str = "GB") -> str:
    """Normalize location name for search."""
    result = name.lower()
    if country == "GB":
        result = result.replace("saint ", "st ")
        result = result.replace("-upon-", " upon ")
        result = result.replace("-on-", " on ")
    return result


async def import_locations_from_councils(
    councils: List[Dict],
    dry_run: bool = False,
) -> Dict:
    """Import UK councils as locations."""

    if dry_run:
        print(f"\n[DRY RUN] Would import {len(councils)} locations")
        return {"locations_created": 0, "locations_skipped": 0}

    from app.database import async_session_factory
    from app.models import Location
    from sqlalchemy import select

    stats = {"locations_created": 0, "locations_skipped": 0, "locations_errors": 0}

    # Track seen GSS codes to avoid duplicates within the same import
    seen_gss_codes = set()

    async with async_session_factory() as session:
        for council in councils:
            try:
                gss_code = council.get("gss_code")

                # Skip if we've already seen this GSS code in this batch
                if gss_code and gss_code in seen_gss_codes:
                    stats["locations_skipped"] += 1
                    continue

                # Check if location already exists (by GSS code or name)
                if gss_code:
                    existing = await session.execute(
                        select(Location).where(
                            Location.country == "GB",
                            Location.official_code == gss_code
                        )
                    )
                    if existing.scalar_one_or_none():
                        seen_gss_codes.add(gss_code)
                        stats["locations_skipped"] += 1
                        continue
                else:
                    # Check by normalized name for entries without GSS code
                    existing = await session.execute(
                        select(Location).where(
                            Location.country == "GB",
                            Location.name_normalized == normalize_name(council["name"])
                        )
                    )
                    if existing.scalar_one_or_none():
                        stats["locations_skipped"] += 1
                        continue

                # Mark GSS code as seen
                if gss_code:
                    seen_gss_codes.add(gss_code)

                # Create location
                population = council.get("population")
                if population:
                    try:
                        population = int(float(population))
                    except (ValueError, TypeError):
                        population = None

                location = Location(
                    id=uuid.uuid4(),
                    country="GB",
                    official_code=gss_code,
                    name=council["name"],
                    name_normalized=normalize_name(council["name"]),
                    admin_level_1=council.get("admin_level_1"),
                    admin_level_2=None,
                    locality_type="local_authority",
                    country_metadata={"wikidata_id": council.get("wikidata_id")},
                    population=population,
                    is_active=True,
                )
                session.add(location)
                stats["locations_created"] += 1

                # Commit in smaller batches to avoid issues
                if stats["locations_created"] % 100 == 0:
                    print(f"  Created {stats['locations_created']} locations...")
                    await session.commit()

            except Exception as e:
                print(f"  Error creating location {council['name']}: {e}")
                stats["locations_errors"] += 1
                # Rollback current transaction and start fresh
                await session.rollback()

        # Final commit
        try:
            await session.commit()
        except Exception as e:
            print(f"  Final commit error: {e}")
            await session.rollback()

    return stats


async def import_councils_as_sources(
    councils: List[Dict],
    category_id,
    dry_run: bool = False,
) -> Dict:
    """Import UK councils as data sources."""

    if dry_run:
        print(f"\n[DRY RUN] Would import {len(councils)} data sources")
        for c in councils[:10]:
            print(f"  - {c['name']}: {c['website']}")
        if len(councils) > 10:
            print(f"  ... and {len(councils) - 10} more")
        return {"sources_imported": 0, "sources_skipped": 0, "sources_errors": 0}

    from app.database import async_session_factory
    from app.models import DataSource, SourceType, SourceStatus, Location
    from sqlalchemy import select

    stats = {"sources_imported": 0, "sources_skipped": 0, "sources_errors": 0}

    async with async_session_factory() as session:
        for council in councils:
            try:
                # Check if already exists
                existing = await session.execute(
                    select(DataSource).where(
                        DataSource.base_url == council["website"]
                    )
                )
                if existing.scalar_one_or_none():
                    stats["sources_skipped"] += 1
                    continue

                # Try to find the location
                location_id = None
                gss_code = council.get("gss_code")
                if gss_code:
                    loc_result = await session.execute(
                        select(Location).where(
                            Location.country == "GB",
                            Location.official_code == gss_code
                        )
                    )
                    location = loc_result.scalar_one_or_none()
                    if location:
                        location_id = location.id

                # Create data source
                source = DataSource(
                    category_id=category_id,
                    name=f"{council['name']} - Council Website",
                    source_type=SourceType.WEBSITE,
                    base_url=council["website"],
                    country="GB",
                    location_id=location_id,
                    location_name=council["name"],
                    admin_level_1=council.get("admin_level_1"),
                    status=SourceStatus.ACTIVE,
                    priority=5,
                    crawl_config={
                        "max_depth": 3,
                        "max_pages": 200,
                        "download_extensions": ["pdf", "doc", "docx"],
                        "filter_keywords": [
                            "wind", "wind energy", "wind farm", "wind turbine",
                            "renewable", "energy", "climate", "planning",
                            "planning application", "development"
                        ],
                        "render_javascript": False,
                    },
                    extra_data={
                        "wikidata_id": council["wikidata_id"],
                        "gss_code": council.get("gss_code"),
                        "population": council.get("population"),
                    }
                )
                session.add(source)
                stats["sources_imported"] += 1

                if stats["sources_imported"] % 50 == 0:
                    print(f"  Imported {stats['sources_imported']} sources...")
                    await session.commit()

            except Exception as e:
                print(f"  Error importing source {council['name']}: {e}")
                stats["sources_errors"] += 1

        await session.commit()

    return stats


async def main():
    parser = argparse.ArgumentParser(
        description="Import UK local authorities from Wikidata"
    )
    parser.add_argument(
        "--country", "-c",
        help="Filter by country (england, scotland, wales, ni)",
        default=None
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        help="Limit number of councils to import",
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
    print("Wikidata UK Local Authorities Import")
    print("=" * 60)

    # Fetch from Wikidata
    councils = await fetch_uk_councils_from_wikidata(
        country=args.country,
        limit=args.limit,
    )
    print(f"\nFound {len(councils)} local authorities with websites")

    if not councils:
        print("No local authorities found!")
        return

    # Show sample
    print("\nSample local authorities:")
    for c in councils[:5]:
        pop = f" (Pop: {int(float(c['population'])):,})" if c.get('population') else ""
        region = f" [{c['admin_level_1']}]" if c.get('admin_level_1') else ""
        print(f"  - {c['name']}{pop}{region}: {c['website']}")

    # STEP 1: Import locations (unless --sources-only)
    location_stats = {"locations_created": 0, "locations_skipped": 0, "locations_errors": 0}
    if not args.sources_only:
        print("\n--- Step 1: Importing Locations ---")
        location_stats = await import_locations_from_councils(
            councils,
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
                    print("Skipping data source import.")
                else:
                    category_id = category.id
                    print(f"\n--- Step 2: Importing Data Sources ---")
                    print(f"  Target category: {args.category}")

        if category_id or args.dry_run:
            source_stats = await import_councils_as_sources(
                councils,
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
