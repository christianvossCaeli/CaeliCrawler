#!/usr/bin/env python3
"""
Script to merge duplicate EntityTypes into their canonical counterpart.

This script uses AI-based detection to identify EntityTypes that represent
territorial/geographic concepts and should be merged into the hierarchical
"territorial_entity" type.

Usage:
    # Dry run (preview changes without modifying database)
    python -m scripts.merge_duplicate_entity_types --dry-run

    # Execute the merge
    python -m scripts.merge_duplicate_entity_types

    # With verbose output
    python -m scripts.merge_duplicate_entity_types --verbose

    # Specify custom source and target EntityTypes
    python -m scripts.merge_duplicate_entity_types --source <source_slug> --target <target_slug>
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import List, Optional, Tuple
from uuid import UUID

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session_context
from app.models.entity import Entity
from app.models.entity_type import EntityType
from app.utils.similarity import get_hierarchy_mapping_async


class EntityTypeMerger:
    """Handles merging of duplicate EntityTypes."""

    def __init__(self, session: AsyncSession, dry_run: bool = True, verbose: bool = False):
        self.session = session
        self.dry_run = dry_run
        self.verbose = verbose
        self.stats = {
            "entity_types_found": 0,
            "entities_migrated": 0,
            "entity_types_deactivated": 0,
            "errors": [],
        }

    def log(self, message: str, level: str = "info"):
        """Log a message."""
        prefix = "[DRY RUN] " if self.dry_run else ""
        if level == "info":
            print(f"{prefix}{message}")
        elif level == "verbose" and self.verbose:
            print(f"{prefix}  → {message}")
        elif level == "error":
            print(f"{prefix}ERROR: {message}")
            self.stats["errors"].append(message)
        elif level == "warning":
            print(f"{prefix}WARNING: {message}")

    async def find_duplicate_entity_types(self) -> List[Tuple[EntityType, str, int, str]]:
        """
        Find all EntityTypes that are territorial duplicates using AI-based detection.

        Returns list of (EntityType, target_slug, hierarchy_level, level_name) tuples.
        """
        duplicates = []

        # Get all active EntityTypes
        result = await self.session.execute(
            select(EntityType).where(EntityType.is_active.is_(True))
        )
        entity_types = result.scalars().all()

        # Check if territorial_entity base type exists
        territorial_base = None
        for et in entity_types:
            if et.slug == "territorial_entity":
                territorial_base = et
                break

        if not territorial_base:
            self.log("No 'territorial_entity' base type found - cannot merge territorial duplicates", level="warning")
            return duplicates

        # Check each EntityType using AI-based hierarchy detection
        for entity_type in entity_types:
            if entity_type.slug == "territorial_entity":
                continue  # Skip the base type itself

            # Use AI to detect if this is a territorial type
            hierarchy_mapping = await get_hierarchy_mapping_async(entity_type.name)

            if hierarchy_mapping and hierarchy_mapping.get("parent_type_slug") == "territorial_entity":
                duplicates.append((
                    entity_type,
                    "territorial_entity",
                    hierarchy_mapping["hierarchy_level"],
                    hierarchy_mapping["level_name"],
                ))
                self.log(f"Found territorial duplicate: '{entity_type.name}' (Level {hierarchy_mapping['hierarchy_level']})")

        self.stats["entity_types_found"] = len(duplicates)
        return duplicates

    async def get_target_entity_type(self, target_slug: str) -> Optional[EntityType]:
        """Get the target EntityType to merge into."""
        result = await self.session.execute(
            select(EntityType).where(
                EntityType.slug == target_slug,
                EntityType.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def count_entities(self, entity_type_id: UUID) -> int:
        """Count entities for a given EntityType."""
        result = await self.session.execute(
            select(func.count()).select_from(Entity).where(
                Entity.entity_type_id == entity_type_id,
                Entity.is_active.is_(True),
            )
        )
        return result.scalar() or 0

    async def migrate_entities(
        self,
        source_type: EntityType,
        target_type: EntityType,
        hierarchy_level: int,
    ) -> int:
        """
        Migrate entities from source to target EntityType, handling duplicates.

        For each entity in source:
        - If an entity with the same name_normalized exists in target: deactivate source entity
        - Otherwise: migrate entity to target

        Returns the number of entities migrated.
        """
        # Get all source entities
        source_result = await self.session.execute(
            select(Entity).where(
                Entity.entity_type_id == source_type.id,
                Entity.is_active.is_(True),
            )
        )
        source_entities = source_result.scalars().all()

        if not source_entities:
            self.log(f"No entities to migrate from '{source_type.name}'", level="verbose")
            return 0

        # Get all target entity name_normalized values for duplicate detection
        target_result = await self.session.execute(
            select(Entity.name_normalized).where(
                Entity.entity_type_id == target_type.id,
                Entity.is_active.is_(True),
            )
        )
        target_names = {row[0] for row in target_result.all()}

        migrated_count = 0
        deactivated_count = 0

        for entity in source_entities:
            if entity.name_normalized in target_names:
                # Duplicate exists in target - deactivate source entity
                self.log(
                    f"  Duplicate found: '{entity.name}' - deactivating source",
                    level="verbose",
                )
                if not self.dry_run:
                    entity.is_active = False
                deactivated_count += 1
            else:
                # No duplicate - migrate to target
                if not self.dry_run:
                    entity.entity_type_id = target_type.id
                    entity.hierarchy_level = hierarchy_level
                migrated_count += 1
                # Add to target names to prevent duplicates within source
                target_names.add(entity.name_normalized)

        self.log(
            f"Migrating {migrated_count} entities, deactivating {deactivated_count} duplicates "
            f"from '{source_type.name}' to '{target_type.name}'"
        )

        if not self.dry_run:
            await self.session.flush()

        self.stats["entities_migrated"] += migrated_count
        if "entities_deactivated" not in self.stats:
            self.stats["entities_deactivated"] = 0
        self.stats["entities_deactivated"] += deactivated_count

        return migrated_count

    async def deactivate_entity_type(self, entity_type: EntityType):
        """Deactivate a duplicate EntityType after migration."""
        self.log(f"Deactivating duplicate EntityType: '{entity_type.name}'")

        if not self.dry_run:
            entity_type.is_active = False
            await self.session.flush()

        self.stats["entity_types_deactivated"] += 1

    async def merge_specific(
        self,
        source_slug: str,
        target_slug: str,
        hierarchy_level: int = 3,
    ) -> bool:
        """
        Merge a specific source EntityType into a target.

        Returns True if successful.
        """
        # Find source EntityType
        result = await self.session.execute(
            select(EntityType).where(
                EntityType.slug == source_slug,
                EntityType.is_active.is_(True),
            )
        )
        source_type = result.scalar_one_or_none()

        if not source_type:
            self.log(f"Source EntityType '{source_slug}' not found or inactive", level="warning")
            return False

        # Find target EntityType
        target_type = await self.get_target_entity_type(target_slug)
        if not target_type:
            self.log(f"Target EntityType '{target_slug}' not found or inactive", level="error")
            return False

        # Migrate entities
        await self.migrate_entities(source_type, target_type, hierarchy_level)

        # Deactivate source
        await self.deactivate_entity_type(source_type)

        return True

    async def merge_all_duplicates(self):
        """Find and merge all known duplicate EntityTypes."""
        duplicates = await self.find_duplicate_entity_types()

        if not duplicates:
            self.log("No duplicate EntityTypes found")
            return

        self.log(f"\nFound {len(duplicates)} duplicate EntityType(s) to merge\n")

        for source_type, target_slug, hierarchy_level, level_name in duplicates:
            # Get target EntityType
            target_type = await self.get_target_entity_type(target_slug)

            if not target_type:
                self.log(
                    f"Cannot merge '{source_type.name}': target '{target_slug}' not found",
                    level="error",
                )
                continue

            self.log(f"\n--- Merging '{source_type.name}' → '{target_type.name}' ---")
            self.log(f"  Hierarchy level: {hierarchy_level} ({level_name})", level="verbose")

            # Migrate entities
            await self.migrate_entities(source_type, target_type, hierarchy_level)

            # Deactivate source
            await self.deactivate_entity_type(source_type)

        if not self.dry_run:
            await self.session.commit()
            self.log("\n✓ Changes committed to database")
        else:
            self.log("\n✓ Dry run complete - no changes made")

    def print_summary(self):
        """Print summary of the merge operation."""
        print("\n" + "=" * 50)
        print("MERGE SUMMARY")
        print("=" * 50)
        print(f"EntityTypes found:       {self.stats['entity_types_found']}")
        print(f"Entities migrated:       {self.stats['entities_migrated']}")
        print(f"Entities deactivated:    {self.stats.get('entities_deactivated', 0)}")
        print(f"EntityTypes deactivated: {self.stats['entity_types_deactivated']}")

        if self.stats["errors"]:
            print(f"\nErrors ({len(self.stats['errors'])}):")
            for error in self.stats["errors"]:
                print(f"  - {error}")

        if self.dry_run:
            print("\n⚠️  This was a DRY RUN - no changes were made")
            print("   Run without --dry-run to apply changes")


async def main():
    parser = argparse.ArgumentParser(
        description="Merge duplicate EntityTypes into their canonical counterparts"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying the database",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--source",
        type=str,
        help="Specific source EntityType slug to merge",
    )
    parser.add_argument(
        "--target",
        type=str,
        default="territorial_entity",
        help="Target EntityType slug (default: territorial_entity)",
    )
    parser.add_argument(
        "--hierarchy-level",
        type=int,
        default=3,
        help="Hierarchy level for migrated entities (default: 3)",
    )

    args = parser.parse_args()

    print("\n" + "=" * 50)
    print("EntityType Duplicate Merger")
    print("=" * 50 + "\n")

    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made\n")

    async with get_session_context() as session:
        merger = EntityTypeMerger(
            session=session,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )

        if args.source:
            # Merge specific EntityType
            success = await merger.merge_specific(
                source_slug=args.source.lower(),
                target_slug=args.target.lower(),
                hierarchy_level=args.hierarchy_level,
            )
            if success and not args.dry_run:
                await session.commit()
        else:
            # Find and merge all known duplicates
            await merger.merge_all_duplicates()

        merger.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
