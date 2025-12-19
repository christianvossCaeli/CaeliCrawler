#!/usr/bin/env python3
"""
Sync municipalities from DataSources to Municipality table.

Creates Municipality records for all DataSources that have a municipality name
but no corresponding Municipality record. Also enriches with district info.

Usage:
    docker compose exec backend python scripts/sync_municipalities_from_sources.py
"""

import asyncio
import sys
import uuid
from pathlib import Path

import httpx

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.municipality import Municipality
from app.models.data_source import DataSource


async def lookup_district(name: str, state: str = "Nordrhein-Westfalen") -> str | None:
    """Look up district (Landkreis) for a municipality using Nominatim API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": f"{name}, {state}, Germany",
                    "format": "json",
                    "addressdetails": 1,
                    "limit": 1,
                },
                headers={"User-Agent": "CaeliCrawler/1.0"},
                timeout=10.0,
            )
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    address = data[0].get("address", {})
                    # Try different address fields for district
                    district = (
                        address.get("county") or
                        address.get("city_district") or
                        address.get("state_district")
                    )
                    return district
    except Exception as e:
        print(f"    Warning: Could not lookup district for {name}: {e}")
    return None


async def sync_municipalities():
    """Create Municipality records from DataSource.municipality values."""
    async with async_session_factory() as session:
        # Get all unique municipality names from DataSources
        sources_q = (
            select(DataSource.municipality, DataSource.bundesland)
            .where(
                DataSource.municipality.isnot(None),
                DataSource.municipality != "",
            )
            .distinct()
        )
        sources_result = await session.execute(sources_q)
        source_municipalities = sources_result.fetchall()

        print(f"Found {len(source_municipalities)} unique municipalities in DataSources")

        # Get existing Municipality names (normalized for comparison)
        existing_q = select(Municipality.name, Municipality.name_normalized)
        existing_result = await session.execute(existing_q)
        existing_normalized = {row.name_normalized for row in existing_result.fetchall()}

        print(f"Found {len(existing_normalized)} existing Municipality records")

        created = 0
        skipped = 0

        for row in source_municipalities:
            name = row.municipality
            bundesland = row.bundesland or "Nordrhein-Westfalen"  # Default to NRW

            name_normalized = Municipality.normalize_name(name)

            if name_normalized in existing_normalized:
                skipped += 1
                continue

            # Create new Municipality record
            municipality = Municipality(
                id=uuid.uuid4(),
                name=name,
                name_normalized=name_normalized,
                state=bundesland,
                is_active=True,
            )
            session.add(municipality)
            existing_normalized.add(name_normalized)  # Avoid duplicates in this run
            created += 1
            print(f"  Created: {name} ({bundesland})")

        await session.commit()

        print(f"\nCreated {created} new Municipality records")
        print(f"Skipped {skipped} (already exist)")


async def enrich_municipalities_with_district():
    """Enrich municipalities that have no district with lookup from Nominatim."""
    async with async_session_factory() as session:
        # Get municipalities without district
        query = select(Municipality).where(
            Municipality.is_active == True,
            Municipality.district.is_(None),
        )
        result = await session.execute(query)
        municipalities = result.scalars().all()

        print(f"\nFound {len(municipalities)} municipalities without district")

        enriched = 0
        for muni in municipalities:
            # Rate limit: wait 1 second between requests (Nominatim policy)
            await asyncio.sleep(1)

            district = await lookup_district(muni.name, muni.state or "Nordrhein-Westfalen")
            if district:
                muni.district = district
                enriched += 1
                print(f"  Enriched: {muni.name} -> {district}")
            else:
                print(f"  No district found for: {muni.name}")

        await session.commit()
        print(f"\nEnriched {enriched} municipalities with district info")


async def link_sources_to_municipalities():
    """Link DataSources to their Municipality records."""
    async with async_session_factory() as session:
        # Get all municipalities
        munis_result = await session.execute(
            select(Municipality).where(Municipality.is_active == True)
        )
        municipalities = {
            m.name_normalized: m.id
            for m in munis_result.scalars().all()
        }

        # Get unlinked DataSources
        unlinked_q = select(DataSource).where(
            DataSource.municipality_id.is_(None),
            DataSource.municipality.isnot(None),
            DataSource.municipality != "",
        )
        unlinked_result = await session.execute(unlinked_q)
        unlinked_sources = unlinked_result.scalars().all()

        linked = 0
        for source in unlinked_sources:
            name_normalized = Municipality.normalize_name(source.municipality)
            if name_normalized in municipalities:
                source.municipality_id = municipalities[name_normalized]
                linked += 1

        await session.commit()
        print(f"\nLinked {linked} DataSources to Municipality records")


async def main(enrich_districts: bool = False):
    print("=== Syncing Municipalities from DataSources ===\n")
    await sync_municipalities()
    print("\n=== Linking DataSources to Municipalities ===\n")
    await link_sources_to_municipalities()

    if enrich_districts:
        print("\n=== Enriching Municipalities with District Info ===")
        print("(This may take a while due to API rate limiting...)\n")
        await enrich_municipalities_with_district()

    print("\nDone!")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sync municipalities from data sources")
    parser.add_argument(
        "--enrich-districts",
        action="store_true",
        help="Look up and fill in missing district (Landkreis) info via Nominatim API"
    )
    args = parser.parse_args()
    asyncio.run(main(enrich_districts=args.enrich_districts))
