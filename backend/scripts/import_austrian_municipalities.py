#!/usr/bin/env python3
"""
Import Austrian municipalities from Wikidata.

This script:
1. Creates Austrian-specific categories if they don't exist
2. Fetches all Austrian municipalities (Gemeinden) from Wikidata
3. Creates Entity records with proper normalization
4. Creates DataSource records linked to entities (for municipalities with websites)

Usage:
    docker compose exec backend python -m scripts.import_austrian_municipalities [--dry-run] [--limit N]

Reference: See backend/scripts/README_municipality_import.md for full documentation.
"""

import asyncio
import argparse
import httpx
from typing import List, Dict, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# WICHTIG: Zentrale Normalisierung verwenden!
from app.utils.text import normalize_entity_name, create_slug
from app.database import async_session_factory
from app.models import Entity, EntityType, DataSource, SourceType, SourceStatus, Category


# =============================================================================
# CONFIGURATION
# =============================================================================

WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"

# Austrian Bundesländer (first digit of Gemeindekennziffer)
BUNDESLAND_CODES = {
    "1": "Burgenland",
    "2": "Kärnten",
    "3": "Niederösterreich",
    "4": "Oberösterreich",
    "5": "Salzburg",
    "6": "Steiermark",
    "7": "Tirol",
    "8": "Vorarlberg",
    "9": "Wien",
}

# Wikidata SPARQL query for Austrian municipalities
# Q667509 = municipality of Austria
# P964 = Gemeindekennziffer (Austrian municipality key)
# P856 = official website
# P1082 = population
# P131 = located in administrative territorial entity
SPARQL_QUERY = """
SELECT DISTINCT
    ?gemeinde
    ?gemeindeLabel
    ?website
    ?gkz
    ?population
    ?bundeslandLabel
    ?lat
    ?lon
WHERE {
    # Municipality of Austria (including subclasses)
    ?gemeinde wdt:P31/wdt:P279* wd:Q667509 .

    # Gemeindekennziffer (Austrian municipality key)
    OPTIONAL { ?gemeinde wdt:P964 ?gkz }

    # Official website
    OPTIONAL { ?gemeinde wdt:P856 ?website }

    # Population
    OPTIONAL { ?gemeinde wdt:P1082 ?population }

    # Bundesland (via administrative hierarchy)
    OPTIONAL {
        ?gemeinde wdt:P131* ?bundesland .
        ?bundesland wdt:P31 wd:Q261543 .  # Austrian federal state
    }

    # Coordinates
    OPTIONAL {
        ?gemeinde wdt:P625 ?coord .
        BIND(geof:latitude(?coord) AS ?lat)
        BIND(geof:longitude(?coord) AS ?lon)
    }

    SERVICE wikibase:label { bd:serviceParam wikibase:language "de,en" }
}
ORDER BY ?bundeslandLabel ?gemeindeLabel
"""


# =============================================================================
# AUSTRIAN CATEGORIES
# =============================================================================

AUSTRIAN_CATEGORIES = [
    {
        "name": "Kommunale News Österreich",
        "slug": "kommunale-news-at",
        "description": "Aktuelle Meldungen und Pressemitteilungen von österreichischen Gemeinden",
        "purpose": """Monitoring öffentlicher Kommunikation zu Windenergie in Österreich:
- Pressemitteilungen zu Energieprojekten
- News über Bürgerbeteiligungen
- Ankündigungen von Informationsveranstaltungen
- Statements von Bürgermeistern""",
        "search_terms": [
            "Windkraft", "Windenergie", "Erneuerbare Energie",
            "Energiewende", "Klimaschutz", "Windpark",
            "Repowering", "Bürgerwindpark"
        ],
        "ai_extraction_prompt": """Analysiere diese österreichische kommunale Pressemitteilung/News für Sales Intelligence.

EXTRAHIERE IM JSON-FORMAT:
{
  "is_relevant": true/false,
  "municipality": "Name der Gemeinde/Stadt",
  "bundesland": "Bundesland",
  "publication_date": "YYYY-MM-DD",
  "news_type": "Pressemitteilung|Ankündigung|Bericht|Statement",
  "topic": "Hauptthema der Meldung",
  "sentiment": "positiv|neutral|negativ|gemischt",
  "decision_makers": [{"person": "Name", "role": "Position", "statement": "Zitat"}],
  "positive_signals": ["Identifizierte Chancen"],
  "pain_points": ["Erwähnte Bedenken oder Probleme"],
  "summary": "Kurze Zusammenfassung"
}""",
        "schedule_cron": "0 8 * * *",
    },
    {
        "name": "Ratsinformationen Österreich",
        "slug": "ratsinformationen-at",
        "description": "Gemeinderats- und Landtagssitzungen aus österreichischen Kommunen",
        "purpose": """Monitoring kommunaler Entscheidungen zu Windenergie in Österreich:
- Flächenwidmungspläne
- Genehmigungsverfahren
- Bürgerbeteiligung
- Beschlüsse zu Windkraftanlagen""",
        "search_terms": [
            "Windkraft", "Windenergie", "Windrad", "Windpark",
            "Flächenwidmung", "Raumordnung", "UVP",
            "Genehmigung", "Bauverfahren"
        ],
        "ai_extraction_prompt": """Analysiere dieses österreichische kommunale Dokument für Sales Intelligence.

EXTRAHIERE IM JSON-FORMAT:
{
  "is_relevant": true/false,
  "relevanz": "hoch|mittel|gering|keine",
  "municipality": "Name der Gemeinde/Stadt",
  "bundesland": "Bundesland",
  "document_type": "Beschluss|Antrag|Anfrage|Bericht",
  "pain_points": [{"type": "Bürgerprotest|Naturschutz|Genehmigung", "description": "...", "severity": "hoch|mittel|niedrig"}],
  "positive_signals": [{"type": "Interesse|Planung|Genehmigung", "description": "..."}],
  "decision_makers": [{"name": "Name", "role": "Position", "stance": "positiv|neutral|negativ"}],
  "summary": "Kurze Zusammenfassung"
}""",
        "schedule_cron": "0 6 * * *",
    },
]


# =============================================================================
# WIKIDATA FETCHING
# =============================================================================

async def fetch_municipalities_from_wikidata(limit: Optional[int] = None) -> List[Dict]:
    """Fetch Austrian municipalities from Wikidata."""
    print("Fetching Austrian municipalities from Wikidata...")

    query = SPARQL_QUERY
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
    seen_names = set()

    for binding in data.get("results", {}).get("bindings", []):
        name = binding.get("gemeindeLabel", {}).get("value", "")

        # Skip if no name or duplicate
        if not name or name in seen_names:
            continue
        seen_names.add(name)

        # Extract GKZ
        gkz = binding.get("gkz", {}).get("value")

        # Get Bundesland from GKZ or from Wikidata
        bundesland = binding.get("bundeslandLabel", {}).get("value")
        if not bundesland and gkz and len(gkz) >= 1:
            bundesland = BUNDESLAND_CODES.get(gkz[0])

        # Parse population
        population = None
        pop_str = binding.get("population", {}).get("value")
        if pop_str:
            try:
                population = int(float(pop_str))
            except (ValueError, TypeError):
                pass

        # Parse coordinates
        lat = None
        lon = None
        lat_str = binding.get("lat", {}).get("value")
        lon_str = binding.get("lon", {}).get("value")
        if lat_str and lon_str:
            try:
                lat = float(lat_str)
                lon = float(lon_str)
            except (ValueError, TypeError):
                pass

        # Clean website URL
        website = binding.get("website", {}).get("value")
        if website and website.startswith("http://"):
            website = website.replace("http://", "https://")

        results.append({
            "wikidata_id": binding.get("gemeinde", {}).get("value", "").split("/")[-1],
            "name": name,
            "gkz": gkz,
            "website": website,
            "population": population,
            "bundesland": bundesland,
            "latitude": lat,
            "longitude": lon,
        })

    return results


# =============================================================================
# CATEGORY CREATION
# =============================================================================

async def ensure_categories(session: AsyncSession) -> Dict[str, UUID]:
    """Ensure Austrian categories exist and return their IDs."""
    category_ids = {}

    for cat_data in AUSTRIAN_CATEGORIES:
        # Check if exists
        result = await session.execute(
            select(Category).where(Category.slug == cat_data["slug"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"  Category exists: {cat_data['name']}")
            category_ids[cat_data["slug"]] = existing.id
        else:
            # Create new
            category = Category(
                name=cat_data["name"],
                slug=cat_data["slug"],
                description=cat_data["description"],
                purpose=cat_data["purpose"],
                search_terms=cat_data["search_terms"],
                ai_extraction_prompt=cat_data["ai_extraction_prompt"],
                schedule_cron=cat_data["schedule_cron"],
                is_active=True,
            )
            session.add(category)
            await session.flush()
            print(f"  Created category: {cat_data['name']}")
            category_ids[cat_data["slug"]] = category.id

    return category_ids


# =============================================================================
# ENTITY IMPORT
# =============================================================================

async def import_entities(
    session: AsyncSession,
    municipalities: List[Dict],
    entity_type_id: UUID,
    dry_run: bool = False,
) -> Dict[str, any]:
    """Import municipalities as Entity records."""
    stats = {"created": 0, "skipped": 0, "errors": 0}
    entity_map = {}  # name_normalized -> entity_id

    for muni in municipalities:
        try:
            # WICHTIG: Zentrale Normalisierung verwenden!
            name_normalized = normalize_entity_name(muni["name"], country="AT")

            # Check if exists
            result = await session.execute(
                select(Entity).where(
                    Entity.entity_type_id == entity_type_id,
                    Entity.name_normalized == name_normalized,
                    Entity.country == "AT",
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                stats["skipped"] += 1
                entity_map[name_normalized] = existing.id
                continue

            if dry_run:
                stats["created"] += 1
                continue

            # Create Entity
            entity = Entity(
                entity_type_id=entity_type_id,
                name=muni["name"],
                name_normalized=name_normalized,
                slug=create_slug(muni["name"], country="AT"),
                external_id=muni.get("gkz"),
                country="AT",
                admin_level_1=muni.get("bundesland"),
                core_attributes={
                    "wikidata_id": muni.get("wikidata_id"),
                    "population": muni.get("population"),
                    "gkz": muni.get("gkz"),
                },
                latitude=muni.get("latitude"),
                longitude=muni.get("longitude"),
            )
            session.add(entity)
            await session.flush()

            entity_map[name_normalized] = entity.id
            stats["created"] += 1

            if stats["created"] % 100 == 0:
                print(f"    Created {stats['created']} entities...")
                await session.commit()

        except Exception as e:
            print(f"    Error importing entity {muni['name']}: {e}")
            stats["errors"] += 1

    if not dry_run:
        await session.commit()

    return {"stats": stats, "entity_map": entity_map}


# =============================================================================
# DATA SOURCE IMPORT
# =============================================================================

async def import_data_sources(
    session: AsyncSession,
    municipalities: List[Dict],
    entity_map: Dict[str, UUID],
    category_id: UUID,
    dry_run: bool = False,
) -> Dict:
    """Import DataSource records for municipalities with websites."""
    stats = {"created": 0, "skipped": 0, "no_website": 0, "errors": 0}

    for muni in municipalities:
        website = muni.get("website")
        if not website:
            stats["no_website"] += 1
            continue

        try:
            # Check if DataSource already exists
            result = await session.execute(
                select(DataSource).where(DataSource.base_url == website)
            )
            if result.scalar_one_or_none():
                stats["skipped"] += 1
                continue

            if dry_run:
                stats["created"] += 1
                continue

            # Get entity_id
            name_normalized = normalize_entity_name(muni["name"], country="AT")
            entity_id = entity_map.get(name_normalized)

            # Create DataSource
            source = DataSource(
                category_id=category_id,
                name=f"{muni['name']} - Kommunale Website",
                source_type=SourceType.WEBSITE,
                base_url=website,
                country="AT",
                entity_id=entity_id,
                location_name=muni["name"],
                admin_level_1=muni.get("bundesland"),
                status=SourceStatus.ACTIVE,
                priority=5,
                crawl_config={
                    "max_depth": 3,
                    "max_pages": 200,
                    "download_extensions": ["pdf", "doc", "docx"],
                    "filter_keywords": [
                        "wind", "windkraft", "windenergie", "windrad",
                        "flächenwidmung", "raumordnung", "bebauungsplan",
                        "erneuerbare", "energie", "klimaschutz",
                        "genehmigung", "umweltverträglichkeit"
                    ],
                    "render_javascript": False,
                },
                extra_data={
                    "wikidata_id": muni.get("wikidata_id"),
                    "gkz": muni.get("gkz"),
                    "population": muni.get("population"),
                },
            )
            session.add(source)
            stats["created"] += 1

            if stats["created"] % 100 == 0:
                print(f"    Created {stats['created']} data sources...")
                await session.commit()

        except Exception as e:
            print(f"    Error creating DataSource for {muni['name']}: {e}")
            stats["errors"] += 1

    if not dry_run:
        await session.commit()

    return stats


# =============================================================================
# MAIN
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(
        description="Import Austrian municipalities from Wikidata"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Don't actually import, just show what would be done"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        help="Limit number of municipalities to import",
        default=None
    )
    args = parser.parse_args()

    print("=" * 70)
    print("Austrian Municipality Import")
    print("=" * 70)

    if args.dry_run:
        print("[DRY RUN MODE - No changes will be made]")

    # Step 1: Fetch from Wikidata
    print("\n--- Step 1: Fetching from Wikidata ---")
    municipalities = await fetch_municipalities_from_wikidata(limit=args.limit)
    print(f"Found {len(municipalities)} municipalities")

    # Show sample
    print("\nSample municipalities:")
    for m in municipalities[:5]:
        pop = f" (Pop: {m['population']:,})" if m.get('population') else ""
        gkz = f" [GKZ: {m['gkz']}]" if m.get('gkz') else ""
        web = " (has website)" if m.get('website') else ""
        print(f"  - {m['name']}, {m.get('bundesland', '?')}{pop}{gkz}{web}")
    if len(municipalities) > 5:
        print(f"  ... and {len(municipalities) - 5} more")

    # Stats by Bundesland
    print("\nMunicipalities by Bundesland:")
    by_bundesland = {}
    for m in municipalities:
        bl = m.get("bundesland", "Unbekannt")
        by_bundesland[bl] = by_bundesland.get(bl, 0) + 1
    for bl, count in sorted(by_bundesland.items()):
        print(f"  {bl}: {count}")

    with_website = sum(1 for m in municipalities if m.get("website"))
    print(f"\nWith website: {with_website} ({100*with_website/len(municipalities):.1f}%)")

    async with async_session_factory() as session:
        # Step 2: Ensure categories exist
        print("\n--- Step 2: Ensuring Categories ---")
        if not args.dry_run:
            category_ids = await ensure_categories(session)
            await session.commit()
        else:
            print("  [DRY RUN] Would create/verify categories")
            category_ids = {"kommunale-news-at": None}

        # Step 3: Get municipality EntityType
        print("\n--- Step 3: Getting EntityType ---")
        result = await session.execute(
            select(EntityType).where(EntityType.slug == "municipality")
        )
        entity_type = result.scalar_one_or_none()

        if not entity_type:
            print("ERROR: EntityType 'municipality' not found!")
            print("Please run seed_entity_facet_system.py first.")
            return

        print(f"  Found EntityType: {entity_type.name} (ID: {entity_type.id})")

        # Step 4: Import entities
        print("\n--- Step 4: Importing Entities ---")
        entity_result = await import_entities(
            session, municipalities, entity_type.id, dry_run=args.dry_run
        )
        entity_stats = entity_result["stats"]
        entity_map = entity_result["entity_map"]

        print(f"  Entities created: {entity_stats['created']}")
        print(f"  Entities skipped (existing): {entity_stats['skipped']}")
        if entity_stats["errors"]:
            print(f"  Errors: {entity_stats['errors']}")

        # Step 5: Import data sources
        print("\n--- Step 5: Importing DataSources ---")
        if args.dry_run or not category_ids.get("kommunale-news-at"):
            ds_stats = {"created": with_website, "skipped": 0, "no_website": len(municipalities) - with_website}
            print(f"  [DRY RUN] Would create ~{with_website} DataSources")
        else:
            ds_stats = await import_data_sources(
                session,
                municipalities,
                entity_map,
                category_ids["kommunale-news-at"],
                dry_run=args.dry_run,
            )
            print(f"  DataSources created: {ds_stats['created']}")
            print(f"  DataSources skipped (existing): {ds_stats['skipped']}")
            print(f"  No website: {ds_stats['no_website']}")
            if ds_stats.get("errors"):
                print(f"  Errors: {ds_stats['errors']}")

    # Summary
    print("\n" + "=" * 70)
    print("IMPORT SUMMARY")
    print("=" * 70)
    print(f"  Municipalities from Wikidata: {len(municipalities)}")
    print(f"  Entities created: {entity_stats['created']}")
    print(f"  Entities skipped: {entity_stats['skipped']}")
    print(f"  DataSources created: {ds_stats.get('created', 0)}")
    print(f"  DataSources skipped: {ds_stats.get('skipped', 0)}")

    if not args.dry_run:
        print("\nNext steps:")
        print("  1. Run duplicate check: python -m scripts.cleanup_duplicate_municipalities --country AT --dry-run")
        print("  2. Verify in database: SELECT COUNT(*) FROM entities WHERE country = 'AT'")

    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
