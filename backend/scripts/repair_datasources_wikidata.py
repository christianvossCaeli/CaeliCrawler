#!/usr/bin/env python3
"""Repair DataSources with real official website URLs from Wikidata.

This script:
1. Queries Wikidata for German municipalities with their AGS codes and official websites (P856)
2. Updates repaired DataSources from Wikipedia URLs to real official websites
3. Keeps Wikipedia as fallback if no official website exists
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import httpx
import structlog

logger = structlog.get_logger()

# Wikidata SPARQL endpoint
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"

# SPARQL query to get AGS codes and official websites
WIKIDATA_QUERY = """
SELECT ?ags ?website ?gemeindeLabel WHERE {
  ?gemeinde wdt:P31/wdt:P279* wd:Q262166 .  # Instance of German municipality
  ?gemeinde wdt:P439 ?ags .                  # AGS code
  ?gemeinde wdt:P856 ?website .              # Official website
  SERVICE wikibase:label { bd:serviceParam wikibase:language "de,en" }
}
"""


async def fetch_wikidata_websites() -> dict[str, tuple[str, str]]:
    """Fetch AGS -> (website, name) mapping from Wikidata."""
    logger.info("Fetching official websites from Wikidata...")

    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": "CaeliCrawler/1.0 (Data Repair Script)"
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.get(
            WIKIDATA_SPARQL,
            params={"query": WIKIDATA_QUERY, "format": "json"},
            headers=headers
        )
        response.raise_for_status()
        data = response.json()

    result = {}
    for binding in data.get("results", {}).get("bindings", []):
        ags = binding.get("ags", {}).get("value", "")
        website = binding.get("website", {}).get("value", "")
        name = binding.get("gemeindeLabel", {}).get("value", "")

        if ags and website:
            # Normalize AGS (some have leading zeros stripped)
            ags = ags.zfill(8)
            # Keep the first website if multiple exist
            if ags not in result:
                result[ags] = (website, name)

    logger.info(f"Found {len(result)} municipalities with official websites")
    return result


async def repair_datasources():
    """Update repaired DataSources with real official website URLs."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.database import get_session_context
    from app.models import DataSource

    # First, fetch Wikidata data
    ags_to_website = await fetch_wikidata_websites()

    # Then update DataSources
    async with get_session_context() as session:
        session: AsyncSession

        # Get all repaired DataSources
        result = await session.execute(
            select(DataSource).where(
                DataSource.extra_data["repair_reason"].isnot(None)
            )
        )

        repaired_sources = result.scalars().all()
        logger.info(f"Found {len(repaired_sources)} repaired DataSources to process")

        # Get all existing base_urls to avoid unique constraint violations
        existing_urls_result = await session.execute(
            select(DataSource.base_url)
        )
        existing_urls = {row[0] for row in existing_urls_result.fetchall()}
        logger.info(f"Found {len(existing_urls)} existing base_urls")

        # Track URLs we're adding in this batch
        used_urls = set()

        updated_count = 0
        kept_wikipedia = 0
        shared_website_count = 0
        errors = []

        for ds in repaired_sources:
            extra_data = ds.extra_data or {}

            ags = extra_data.get("original_ags", "")
            if not ags:
                errors.append(f"{ds.name}: No AGS in extra_data")
                continue

            # Normalize AGS
            ags = ags.zfill(8)

            # Look up official website
            website_data = ags_to_website.get(ags)

            if website_data:
                official_url, wikidata_name = website_data

                # Check if URL already exists or is being used in this batch
                if official_url in existing_urls or official_url in used_urls:
                    # Multiple municipalities share this website
                    # Keep Wikipedia but store the official URL in extra_data
                    ds.extra_data = {
                        **extra_data,
                        "shared_official_url": official_url,
                        "url_source": "wikipedia_shared_website",
                        "note": "Official website shared with other municipalities",
                    }
                    shared_website_count += 1
                else:
                    # Update the DataSource using ORM
                    ds.base_url = official_url
                    ds.extra_data = {
                        **extra_data,
                        "wikidata_url": official_url,
                        "url_source": "wikidata_p856",
                    }
                    used_urls.add(official_url)
                    updated_count += 1

                    if updated_count % 100 == 0:
                        logger.info(f"Updated {updated_count} DataSources...")
            else:
                # Keep Wikipedia URL but mark as fallback
                ds.extra_data = {
                    **extra_data,
                    "url_source": "wikipedia_fallback",
                    "no_official_website": True,
                }
                kept_wikipedia += 1

        await session.commit()

        logger.info(
            "Shared website handling",
            shared_website_count=shared_website_count,
        )

        # Summary
        logger.info(
            "Repair completed",
            updated_to_official=updated_count,
            kept_wikipedia=kept_wikipedia,
            errors=len(errors)
        )

        if errors:
            logger.warning(f"Errors: {errors[:10]}...")

        return {
            "updated_to_official": updated_count,
            "kept_wikipedia": kept_wikipedia,
            "shared_website": shared_website_count,
            "errors": errors
        }


async def main():
    """Main entry point."""
    print("=" * 60)
    print("DataSource Repair: Wikipedia -> Official Website")
    print("=" * 60)

    result = await repair_datasources()

    print("\nResults:")
    print(f"  Updated to official website: {result['updated_to_official']}")
    print(f"  Kept Wikipedia (shared URL): {result['shared_website']}")
    print(f"  Kept Wikipedia (no official): {result['kept_wikipedia']}")
    print(f"  Errors: {len(result['errors'])}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
