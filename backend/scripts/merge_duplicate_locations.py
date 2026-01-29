#!/usr/bin/env python3
"""Merge duplicate Location entities.

This script identifies Location entities that are likely duplicates
(e.g., "Hannover" and "Region Hannover") and merges them.

Usage:
    # Dry run (analysis only)
    python -m scripts.merge_duplicate_locations --dry-run

    # Execute merge
    python -m scripts.merge_duplicate_locations

    # Target specific names
    python -m scripts.merge_duplicate_locations --name "Hannover"
"""

import asyncio
import sys
from pathlib import Path

import structlog

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import async_session_factory
from app.models import DataSource, Entity, FacetValue, Location

logger = structlog.get_logger(__name__)


class LocationMerger:
    """Service for merging duplicate Locations."""

    def __init__(self, session: AsyncSession, dry_run: bool = True, verbose: bool = False):
        self.session = session
        self.dry_run = dry_run
        self.verbose = verbose

    async def find_substring_duplicates(self, min_name_length: int = 4) -> list[tuple[Location, Location, str]]:
        """Find locations where one name is a substring of another.

        Returns:
            List of (shorter_location, longer_location, reason) tuples
            The shorter location is typically the "canonical" one to keep.
        """
        # Get all active locations
        result = await self.session.execute(
            select(Location).where(Location.is_active.is_(True))
        )
        locations = result.scalars().all()

        duplicates: list[tuple[Location, Location, str]] = []
        checked_pairs: set[tuple[str, str]] = set()

        for loc1 in locations:
            name1 = (loc1.name_normalized or loc1.name or "").lower().strip()
            if len(name1) < min_name_length:
                continue

            for loc2 in locations:
                if loc1.id == loc2.id:
                    continue

                # Skip if same country but different admin_level_1
                if loc1.country == loc2.country and loc1.admin_level_1 != loc2.admin_level_1:
                    # Different admin regions, likely not duplicates
                    continue

                name2 = (loc2.name_normalized or loc2.name or "").lower().strip()
                if len(name2) < min_name_length:
                    continue

                # Skip if already checked this pair
                pair_key = tuple(sorted([str(loc1.id), str(loc2.id)]))
                if pair_key in checked_pairs:
                    continue
                checked_pairs.add(pair_key)

                # Check substring containment
                if name1 in name2 and name1 != name2:
                    # name1 is contained in name2 (e.g., "hannover" in "region hannover")
                    # Keep the shorter, more canonical name
                    reason = f"'{loc1.name}' enthalten in '{loc2.name}'"
                    duplicates.append((loc1, loc2, reason))
                elif name2 in name1 and name1 != name2:
                    # name2 is contained in name1
                    reason = f"'{loc2.name}' enthalten in '{loc1.name}'"
                    duplicates.append((loc2, loc1, reason))

        return duplicates

    async def merge_locations(
        self, keep: Location, remove: Location, reason: str
    ) -> dict:
        """Merge two locations, keeping one and removing the other.

        Updates all references to point to the kept location.

        Returns:
            Statistics about the merge
        """
        stats = {
            "data_sources_updated": 0,
            "entities_updated": 0,
            "facet_values_updated": 0,
        }

        if self.dry_run:
            # Just count what would be updated
            ds_result = await self.session.execute(
                select(DataSource).where(DataSource.location_id == remove.id)
            )
            stats["data_sources_updated"] = len(ds_result.scalars().all())

            entity_result = await self.session.execute(
                select(Entity).where(Entity.location_id == remove.id)
            )
            stats["entities_updated"] = len(entity_result.scalars().all())

            logger.info(
                "Would merge locations",
                keep_name=keep.name,
                keep_id=str(keep.id),
                remove_name=remove.name,
                remove_id=str(remove.id),
                reason=reason,
                stats=stats,
                dry_run=True,
            )
            return stats

        # Update DataSources
        result = await self.session.execute(
            update(DataSource)
            .where(DataSource.location_id == remove.id)
            .values(location_id=keep.id)
            .returning(DataSource.id)
        )
        stats["data_sources_updated"] = len(result.fetchall())

        # Update Entities
        result = await self.session.execute(
            update(Entity)
            .where(Entity.location_id == remove.id)
            .values(location_id=keep.id)
            .returning(Entity.id)
        )
        stats["entities_updated"] = len(result.fetchall())

        # Deactivate the duplicate location
        remove.is_active = False
        remove.metadata = remove.metadata or {}
        remove.metadata["merged_into"] = str(keep.id)
        remove.metadata["merge_reason"] = reason

        await self.session.flush()

        logger.info(
            "Merged locations",
            keep_name=keep.name,
            keep_id=str(keep.id),
            remove_name=remove.name,
            remove_id=str(remove.id),
            reason=reason,
            stats=stats,
        )

        return stats

    async def run(self, target_name: str | None = None) -> dict:
        """Run the duplicate detection and merge process.

        Args:
            target_name: Optional name to filter for specific duplicates

        Returns:
            Summary statistics
        """
        print("\n" + "=" * 60)
        print("Location Duplicate Merger")
        print("=" * 60)
        print(f"Mode: {'DRY RUN' if self.dry_run else 'EXECUTE'}")
        if target_name:
            print(f"Target: {target_name}")
        print()

        # Find duplicates
        duplicates = await self.find_substring_duplicates()

        # Filter by target name if specified
        if target_name:
            target_lower = target_name.lower()
            duplicates = [
                (keep, remove, reason)
                for keep, remove, reason in duplicates
                if target_lower in keep.name.lower() or target_lower in remove.name.lower()
            ]

        if not duplicates:
            print("No duplicate locations found.")
            return {"pairs_processed": 0, "total_updates": 0}

        print(f"Found {len(duplicates)} duplicate pair(s):\n")

        total_stats = {
            "pairs_processed": 0,
            "data_sources_updated": 0,
            "entities_updated": 0,
        }

        for keep, remove, reason in duplicates:
            print(f"  Duplicate pair:")
            print(f"    KEEP:   '{keep.name}' (ID: {keep.id})")
            print(f"    REMOVE: '{remove.name}' (ID: {remove.id})")
            print(f"    Reason: {reason}")
            print()

            stats = await self.merge_locations(keep, remove, reason)
            total_stats["pairs_processed"] += 1
            total_stats["data_sources_updated"] += stats["data_sources_updated"]
            total_stats["entities_updated"] += stats["entities_updated"]

        if not self.dry_run:
            await self.session.commit()

        print("\n" + "-" * 60)
        print("Summary:")
        print(f"  Pairs processed: {total_stats['pairs_processed']}")
        print(f"  DataSources {'would be' if self.dry_run else ''} updated: {total_stats['data_sources_updated']}")
        print(f"  Entities {'would be' if self.dry_run else ''} updated: {total_stats['entities_updated']}")
        print("-" * 60)

        return total_stats


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Merge duplicate Locations")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Analyze only, don't merge anything",
    )
    parser.add_argument(
        "--name",
        type=str,
        default=None,
        help="Target specific location name",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=False,
        help="Verbose output",
    )

    args = parser.parse_args()

    async with async_session_factory() as session:
        merger = LocationMerger(
            session=session,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
        result = await merger.run(target_name=args.name)

    return result


if __name__ == "__main__":
    asyncio.run(main())
