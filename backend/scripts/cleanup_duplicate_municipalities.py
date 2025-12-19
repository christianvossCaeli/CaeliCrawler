#!/usr/bin/env python3
"""
Cleanup script for duplicate municipality entities.

Problem:
- Different normalization functions created duplicate entities:
  - entity_facet_service.py: "Köln" → "koln" (umlauts removed)
  - import_missing_german_municipalities.py: "Köln" → "köln" (umlauts kept)

This script:
1. Finds duplicate municipalities (same name, different normalization)
2. Keeps the entity WITH AGS code (from Wikidata import)
3. Reassigns DataSources from duplicate entity to canonical entity
4. Deletes the duplicate entity

Usage:
    python -m scripts.cleanup_duplicate_municipalities [--dry-run]
    docker compose exec backend python -m scripts.cleanup_duplicate_municipalities --dry-run
"""

# Disable SQLAlchemy logging FIRST before any imports
import logging
logging.getLogger("sqlalchemy.engine").setLevel(logging.ERROR)
logging.getLogger("sqlalchemy").setLevel(logging.ERROR)

import asyncio
import argparse
import sys
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import UUID

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models import Entity, EntityType, DataSource, FacetValue


def normalize_for_comparison(name: str) -> str:
    """
    Normalize name for comparison purposes.
    This function removes all diacritics and non-alphanumeric characters
    to find matches regardless of the normalization method used.
    """
    result = name.lower()
    # Remove diacritics
    result = unicodedata.normalize("NFD", result)
    result = "".join(c for c in result if not unicodedata.combining(c))
    # Remove non-alphanumeric
    result = re.sub(r"[^a-z0-9]", "", result)
    return result


async def find_duplicates(session: AsyncSession) -> List[Dict]:
    """
    Find duplicate municipality entities.

    Returns a list of dicts with:
    - comparison_key: the normalized name for comparison
    - entities: list of entity dicts with id, name, external_id, data_source_count
    """
    # Get municipality entity type
    result = await session.execute(
        select(EntityType).where(EntityType.slug == "municipality")
    )
    entity_type = result.scalar_one_or_none()
    if not entity_type:
        print("ERROR: municipality entity type not found!")
        return []

    # Get all German municipality entities
    result = await session.execute(
        select(Entity).where(
            Entity.entity_type_id == entity_type.id,
            Entity.country == "DE"
        )
    )
    entities = result.scalars().all()

    # Group by normalized comparison key
    grouped: Dict[str, List[Entity]] = {}
    for entity in entities:
        key = normalize_for_comparison(entity.name)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(entity)

    # Find groups with duplicates
    duplicates = []
    for key, entity_list in grouped.items():
        if len(entity_list) > 1:
            # Get data source counts for each entity
            entity_info = []
            for entity in entity_list:
                ds_count_result = await session.execute(
                    select(func.count()).where(DataSource.entity_id == entity.id)
                )
                ds_count = ds_count_result.scalar()

                entity_info.append({
                    "id": entity.id,
                    "name": entity.name,
                    "name_normalized": entity.name_normalized,
                    "external_id": entity.external_id,
                    "admin_level_1": entity.admin_level_1,
                    "data_source_count": ds_count,
                    "has_ags": entity.external_id is not None,
                })

            duplicates.append({
                "comparison_key": key,
                "entities": entity_info,
            })

    return duplicates


def choose_canonical_entity(entities: List[Dict]) -> Tuple[Dict, List[Dict]]:
    """
    Choose the canonical (to keep) entity from a list of duplicates.

    Priority:
    1. Entity with AGS code (external_id)
    2. If multiple have AGS, the one with more data sources
    3. If none have AGS, the one with more data sources

    Returns: (canonical_entity, duplicates_to_remove)
    """
    with_ags = [e for e in entities if e["has_ags"]]
    without_ags = [e for e in entities if not e["has_ags"]]

    if with_ags:
        # Sort by data_source_count descending
        with_ags.sort(key=lambda x: x["data_source_count"], reverse=True)
        canonical = with_ags[0]
        duplicates = with_ags[1:] + without_ags
    else:
        # No entity has AGS - keep the one with most data sources
        entities_sorted = sorted(entities, key=lambda x: x["data_source_count"], reverse=True)
        canonical = entities_sorted[0]
        duplicates = entities_sorted[1:]

    return canonical, duplicates


async def reassign_data_sources(
    session: AsyncSession,
    from_entity_id: UUID,
    to_entity_id: UUID,
    dry_run: bool = False
) -> int:
    """Reassign data sources from one entity to another."""
    if dry_run:
        result = await session.execute(
            select(func.count()).where(DataSource.entity_id == from_entity_id)
        )
        return result.scalar()

    result = await session.execute(
        update(DataSource)
        .where(DataSource.entity_id == from_entity_id)
        .values(entity_id=to_entity_id)
        .returning(DataSource.id)
    )
    updated_ids = result.scalars().all()
    return len(updated_ids)


async def reassign_facet_values(
    session: AsyncSession,
    from_entity_id: UUID,
    to_entity_id: UUID,
    dry_run: bool = False
) -> int:
    """Reassign facet values from one entity to another."""
    if dry_run:
        result = await session.execute(
            select(func.count()).where(FacetValue.entity_id == from_entity_id)
        )
        return result.scalar()

    result = await session.execute(
        update(FacetValue)
        .where(FacetValue.entity_id == from_entity_id)
        .values(entity_id=to_entity_id)
        .returning(FacetValue.id)
    )
    updated_ids = result.scalars().all()
    return len(updated_ids)


async def delete_entity(
    session: AsyncSession,
    entity_id: UUID,
    dry_run: bool = False
) -> bool:
    """Delete an entity."""
    if dry_run:
        return True

    await session.execute(
        delete(Entity).where(Entity.id == entity_id)
    )
    return True


async def cleanup_duplicates(dry_run: bool = False):
    """Main cleanup function."""
    print("=" * 70)
    print("MUNICIPALITY DUPLICATE CLEANUP")
    print("=" * 70)

    if dry_run:
        print("\n[DRY RUN MODE - No changes will be made]\n")

    async with async_session_factory() as session:
        # Step 1: Find duplicates
        print("\nStep 1: Finding duplicates...")
        duplicates = await find_duplicates(session)

        if not duplicates:
            print("  No duplicates found!")
            return

        print(f"  Found {len(duplicates)} duplicate groups")

        # Step 2: Process each duplicate group
        print("\nStep 2: Processing duplicates...")

        total_reassigned_ds = 0
        total_reassigned_fv = 0
        total_deleted = 0

        for dup_group in duplicates:
            canonical, to_remove = choose_canonical_entity(dup_group["entities"])

            print(f"\n  '{canonical['name']}' ({dup_group['comparison_key']}):")
            print(f"    Keeping: {canonical['name']} (AGS: {canonical['external_id']}, DS: {canonical['data_source_count']})")

            for dup in to_remove:
                print(f"    Removing: {dup['name']} (AGS: {dup['external_id']}, DS: {dup['data_source_count']})")

                # Reassign data sources
                reassigned_ds = await reassign_data_sources(
                    session, dup["id"], canonical["id"], dry_run
                )
                if reassigned_ds > 0:
                    print(f"      -> Reassigned {reassigned_ds} data sources")
                    total_reassigned_ds += reassigned_ds

                # Reassign facet values
                reassigned_fv = await reassign_facet_values(
                    session, dup["id"], canonical["id"], dry_run
                )
                if reassigned_fv > 0:
                    print(f"      -> Reassigned {reassigned_fv} facet values")
                    total_reassigned_fv += reassigned_fv

                # Delete duplicate entity
                await delete_entity(session, dup["id"], dry_run)
                print(f"      -> Deleted entity")
                total_deleted += 1

        if not dry_run:
            await session.commit()

        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"  Duplicate groups processed: {len(duplicates)}")
        print(f"  Data sources reassigned: {total_reassigned_ds}")
        print(f"  Facet values reassigned: {total_reassigned_fv}")
        print(f"  Entities deleted: {total_deleted}")

        if dry_run:
            print("\n[DRY RUN - No changes were made. Run without --dry-run to apply changes]")


async def fix_remaining_unlinked_datasources(dry_run: bool = False):
    """
    Fix data sources that have a website URL matching an entity's website
    but are not linked via entity_id.
    """
    print("\n" + "=" * 70)
    print("FIXING UNLINKED DATA SOURCES")
    print("=" * 70)

    if dry_run:
        print("\n[DRY RUN MODE - No changes will be made]\n")

    async with async_session_factory() as session:
        # Get municipality entity type
        result = await session.execute(
            select(EntityType).where(EntityType.slug == "municipality")
        )
        entity_type = result.scalar_one_or_none()
        if not entity_type:
            print("ERROR: municipality entity type not found!")
            return

        # Find unlinked data sources that could be linked by URL
        # This is a complex query, so we'll do it in Python

        # Get all entities with websites
        result = await session.execute(
            select(Entity).where(
                Entity.entity_type_id == entity_type.id,
                Entity.country == "DE",
                Entity.core_attributes["website"].isnot(None)
            )
        )
        entities = result.scalars().all()

        # Build a map of website URL -> entity
        url_to_entity: Dict[str, Entity] = {}
        for entity in entities:
            website = entity.core_attributes.get("website") if entity.core_attributes else None
            if website:
                # Normalize URL
                website = website.rstrip("/")
                url_to_entity[website] = entity
                # Also add without trailing slash
                url_to_entity[website + "/"] = entity

        print(f"  Found {len(url_to_entity) // 2} entities with websites")

        # Get unlinked data sources
        result = await session.execute(
            select(DataSource).where(
                DataSource.entity_id.is_(None),
                DataSource.country == "DE"
            )
        )
        unlinked_sources = result.scalars().all()

        print(f"  Found {len(unlinked_sources)} unlinked data sources")

        linked_count = 0
        for ds in unlinked_sources:
            # Try to match by URL
            base_url = ds.base_url.rstrip("/")
            entity = url_to_entity.get(base_url) or url_to_entity.get(base_url + "/")

            if entity:
                if not dry_run:
                    ds.entity_id = entity.id
                print(f"    Linked: {ds.name} -> {entity.name}")
                linked_count += 1

        if not dry_run:
            await session.commit()

        print(f"\n  Total linked: {linked_count}")


async def main():
    parser = argparse.ArgumentParser(
        description="Cleanup duplicate municipality entities"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Don't make changes, just show what would be done"
    )
    parser.add_argument(
        "--fix-unlinked",
        action="store_true",
        help="Also fix unlinked data sources by matching URLs"
    )

    args = parser.parse_args()

    await cleanup_duplicates(dry_run=args.dry_run)

    if args.fix_unlinked:
        await fix_remaining_unlinked_datasources(dry_run=args.dry_run)


if __name__ == "__main__":
    asyncio.run(main())
