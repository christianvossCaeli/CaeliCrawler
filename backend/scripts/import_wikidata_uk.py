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

import argparse
import asyncio
import uuid

import httpx

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
    country: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Fetch UK local authorities from Wikidata."""
    # Use simple query to avoid timeouts
    query = SPARQL_QUERY_UK_SIMPLE

    if limit:
        query += f"\nLIMIT {limit}"

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.get(
            WIKIDATA_ENDPOINT,
            params={"query": query, "format": "json"},
            headers={"User-Agent": "CaeliCrawler/1.0 (Wind Energy Sales Intelligence)"},
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
        raw_name = binding.get("councilLabel", {}).get("value", "")
        # Clean council name to get actual place name (removes "Council", "City of" etc.)
        cleaned_name = clean_council_name(raw_name)

        result = {
            "wikidata_id": binding.get("council", {}).get("value", "").split("/")[-1],
            "name": cleaned_name,
            "name_original": raw_name,  # Keep original for reference
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


def clean_council_name(name: str) -> str:
    """
    Clean UK council/authority names to get the actual place name.

    Removes institutional suffixes/prefixes that don't represent the place:
    - "X Council" -> "X"
    - "X City Council" -> "X"
    - "City of X" -> "X"
    - "Borough of X" -> "X"
    - "County of X" -> "X"

    This prevents creating duplicate entries for the same place.
    """
    import re

    original = name

    # Remove common suffixes (order matters - longer patterns first)
    patterns_to_remove = [
        r"\s+City\s+Council$",  # "Aberdeen City Council" -> "Aberdeen"
        r"\s+Borough\s+Council$",  # "X Borough Council" -> "X"
        r"\s+District\s+Council$",  # "X District Council" -> "X"
        r"\s+County\s+Council$",  # "X County Council" -> "X"
        r"\s+Council$",  # "Angus Council" -> "Angus"
    ]

    for pattern in patterns_to_remove:
        name = re.sub(pattern, "", name, flags=re.IGNORECASE)

    # Remove common prefixes
    prefix_patterns = [
        r"^City\s+of\s+",  # "City of Edinburgh" -> "Edinburgh"
        r"^Borough\s+of\s+",  # "Borough of X" -> "X"
        r"^County\s+of\s+",  # "County of X" -> "X"
        r"^Royal\s+Borough\s+of\s+",  # "Royal Borough of X" -> "X"
    ]

    for pattern in prefix_patterns:
        name = re.sub(pattern, "", name, flags=re.IGNORECASE)

    # Don't return empty string
    name = name.strip()
    if not name:
        return original

    return name


async def import_locations_from_councils(
    councils: list[dict],
    dry_run: bool = False,
) -> dict:
    """Import UK councils as locations."""

    if dry_run:
        return {"locations_created": 0, "locations_skipped": 0}

    from sqlalchemy import select

    from app.database import async_session_factory
    from app.models import Location

    stats = {"locations_created": 0, "locations_skipped": 0, "locations_errors": 0}

    # Track seen GSS codes to avoid duplicates within the same import
    seen_gss_codes = set()

    # Track seen names to avoid duplicates within the same import
    seen_names = set()

    async with async_session_factory() as session:
        for council in councils:
            try:
                gss_code = council.get("gss_code")
                name = council["name"]
                name_norm = normalize_name(name)

                # Skip if we've already seen this GSS code in this batch
                if gss_code and gss_code in seen_gss_codes:
                    stats["locations_skipped"] += 1
                    continue

                # Skip if we've already seen this name in this batch
                if name_norm in seen_names:
                    stats["locations_skipped"] += 1
                    continue

                # Check if location already exists (by GSS code or name)
                if gss_code:
                    existing = await session.execute(
                        select(Location).where(Location.country == "GB", Location.official_code == gss_code)
                    )
                    if existing.scalar_one_or_none():
                        seen_gss_codes.add(gss_code)
                        seen_names.add(name_norm)
                        stats["locations_skipped"] += 1
                        continue

                # Always check by normalized name (even with GSS code)
                existing = await session.execute(
                    select(Location).where(Location.country == "GB", Location.name_normalized == name_norm)
                )
                if existing.scalar_one_or_none():
                    seen_names.add(name_norm)
                    stats["locations_skipped"] += 1
                    continue

                # Mark as seen
                if gss_code:
                    seen_gss_codes.add(gss_code)
                seen_names.add(name_norm)

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
                    await session.commit()

            except Exception:
                stats["locations_errors"] += 1
                # Rollback current transaction and start fresh
                await session.rollback()

        # Final commit
        try:
            await session.commit()
        except Exception:
            await session.rollback()

    return stats


async def import_councils_as_sources(
    councils: list[dict],
    category_id,
    dry_run: bool = False,
) -> dict:
    """Import UK councils as data sources."""

    if dry_run:
        for _c in councils[:10]:
            pass
        if len(councils) > 10:
            pass
        return {"sources_imported": 0, "sources_skipped": 0, "sources_errors": 0}

    from sqlalchemy import select

    from app.database import async_session_factory
    from app.models import DataSource, Location, SourceStatus, SourceType

    stats = {"sources_imported": 0, "sources_skipped": 0, "sources_errors": 0}

    async with async_session_factory() as session:
        for council in councils:
            try:
                # Check if already exists
                existing = await session.execute(select(DataSource).where(DataSource.base_url == council["website"]))
                if existing.scalar_one_or_none():
                    stats["sources_skipped"] += 1
                    continue

                # Try to find the location
                location_id = None
                gss_code = council.get("gss_code")
                if gss_code:
                    loc_result = await session.execute(
                        select(Location).where(Location.country == "GB", Location.official_code == gss_code)
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
                            "wind",
                            "wind energy",
                            "wind farm",
                            "wind turbine",
                            "renewable",
                            "energy",
                            "climate",
                            "planning",
                            "planning application",
                            "development",
                        ],
                        "render_javascript": False,
                    },
                    extra_data={
                        "wikidata_id": council["wikidata_id"],
                        "gss_code": council.get("gss_code"),
                        "population": council.get("population"),
                    },
                )
                session.add(source)
                stats["sources_imported"] += 1

                if stats["sources_imported"] % 50 == 0:
                    await session.commit()

            except Exception:
                stats["sources_errors"] += 1

        await session.commit()

    return stats


async def main():
    parser = argparse.ArgumentParser(description="Import UK local authorities from Wikidata")
    parser.add_argument("--country", "-c", help="Filter by country (england, scotland, wales, ni)", default=None)
    parser.add_argument("--limit", "-l", type=int, help="Limit number of councils to import", default=None)
    parser.add_argument(
        "--dry-run", "-n", action="store_true", help="Don't actually import, just show what would be done"
    )
    parser.add_argument("--category", help="Category slug to use (default: kommunale-news)", default="kommunale-news")
    parser.add_argument("--locations-only", action="store_true", help="Only import locations, skip data sources")
    parser.add_argument("--sources-only", action="store_true", help="Only import data sources, skip locations")

    args = parser.parse_args()

    # Fetch from Wikidata
    councils = await fetch_uk_councils_from_wikidata(
        country=args.country,
        limit=args.limit,
    )

    if not councils:
        return

    # Show sample
    for c in councils[:5]:
        f" (Pop: {int(float(c['population'])):,})" if c.get("population") else ""
        f" [{c['admin_level_1']}]" if c.get("admin_level_1") else ""

    # STEP 1: Import locations (unless --sources-only)
    location_stats = {"locations_created": 0, "locations_skipped": 0, "locations_errors": 0}
    if not args.sources_only:
        location_stats = await import_locations_from_councils(
            councils,
            dry_run=args.dry_run,
        )
        if location_stats.get("locations_errors", 0) > 0:
            pass

    # STEP 2: Import data sources (unless --locations-only)
    source_stats = {"sources_imported": 0, "sources_skipped": 0, "sources_errors": 0}
    if not args.locations_only:
        category_id = None
        if not args.dry_run:
            # Get category
            from sqlalchemy import select

            from app.database import async_session_factory
            from app.models import Category

            async with async_session_factory() as session:
                result = await session.execute(select(Category).where(Category.slug == args.category))
                category = result.scalar_one_or_none()

                if not category:
                    pass
                else:
                    category_id = category.id

        if category_id or args.dry_run:
            source_stats = await import_councils_as_sources(
                councils,
                category_id,
                dry_run=args.dry_run,
            )
            if source_stats.get("sources_errors", 0) > 0:
                pass

    if not args.sources_only:
        pass
    if not args.locations_only:
        pass


if __name__ == "__main__":
    asyncio.run(main())
