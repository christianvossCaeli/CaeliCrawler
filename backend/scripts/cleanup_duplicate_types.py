#!/usr/bin/env python3
"""
Script to detect and cleanup duplicate FacetTypes, EntityTypes, and Categories.

This script uses semantic similarity to identify duplicate types and merges them
by updating all references to point to the canonical (oldest/first created) type.

Usage:
    # Dry run (preview changes without modifying database)
    python -m scripts.cleanup_duplicate_types --dry-run

    # Execute the cleanup
    python -m scripts.cleanup_duplicate_types

    # With verbose output
    python -m scripts.cleanup_duplicate_types --verbose

    # Only check specific type
    python -m scripts.cleanup_duplicate_types --type facet_type
    python -m scripts.cleanup_duplicate_types --type entity_type
    python -m scripts.cleanup_duplicate_types --type category
"""

import argparse
import asyncio
import sys
from pathlib import Path
from uuid import UUID

import structlog

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import func, select, update  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.database import get_session_context  # noqa: E402
from app.models import (  # noqa: E402
    Category,
    Entity,
    EntityType,
    FacetType,
    FacetValue,
)
from app.utils.similarity import (  # noqa: E402
    _cosine_similarity,
    are_concepts_equivalent,
    generate_embedding,
)

logger = structlog.get_logger(__name__)


class DuplicateTypesCleaner:
    """Handles detection and cleanup of duplicate types."""

    def __init__(
        self,
        session: AsyncSession,
        dry_run: bool = True,
        verbose: bool = False,
        similarity_threshold: float = 0.85,  # Higher threshold for merging
    ):
        self.session = session
        self.dry_run = dry_run
        self.verbose = verbose
        self.similarity_threshold = similarity_threshold
        self.stats = {
            "facet_types_duplicates": 0,
            "facet_types_merged": 0,
            "entity_types_duplicates": 0,
            "entity_types_merged": 0,
            "categories_duplicates": 0,
            "categories_merged": 0,
            "references_updated": 0,
            "errors": [],
        }

    def log(self, message: str, level: str = "info"):
        """Log a message."""
        if level == "info" or level == "verbose" and self.verbose:
            pass
        elif level == "error":
            self.stats["errors"].append(message)
        elif level == "warning":
            pass

    async def find_duplicate_facet_types(self) -> list[tuple[FacetType, FacetType, float]]:
        """
        Find duplicate FacetTypes using semantic similarity.

        Returns list of (duplicate, canonical, similarity_score) tuples.
        The canonical is the one to keep (usually the oldest).
        """
        self.log("\n=== Scanning FacetTypes for duplicates ===")

        result = await self.session.execute(
            select(FacetType).where(FacetType.is_active.is_(True)).order_by(FacetType.created_at.asc())  # Oldest first
        )
        facet_types = result.scalars().all()

        self.log(f"Found {len(facet_types)} active FacetTypes")

        duplicates: list[tuple[FacetType, FacetType, float]] = []
        processed_ids: set[UUID] = set()

        # Group by similar names using embeddings
        for i, ft1 in enumerate(facet_types):
            if ft1.id in processed_ids:
                continue

            # Get or generate embedding for ft1
            if ft1.name_embedding is not None:
                emb1 = ft1.name_embedding
            else:
                emb1 = await generate_embedding(ft1.name)
                if emb1 is None:
                    continue

            for ft2 in facet_types[i + 1 :]:
                if ft2.id in processed_ids:
                    continue

                # Quick exact match check first
                if ft1.name.lower() == ft2.name.lower() or ft1.slug == ft2.slug:
                    self.log(
                        f"  Exact duplicate: '{ft2.name}' (slug: {ft2.slug}) -> '{ft1.name}' (slug: {ft1.slug})",
                        level="verbose",
                    )
                    duplicates.append((ft2, ft1, 1.0))
                    processed_ids.add(ft2.id)
                    continue

                # Get or generate embedding for ft2
                if ft2.name_embedding is not None:
                    emb2 = ft2.name_embedding
                else:
                    emb2 = await generate_embedding(ft2.name)
                    if emb2 is None:
                        continue

                # Calculate similarity
                similarity = _cosine_similarity(emb1, emb2)

                if similarity >= self.similarity_threshold:
                    self.log(f"  Similar: '{ft2.name}' ({int(similarity * 100)}%) -> '{ft1.name}'", level="verbose")
                    duplicates.append((ft2, ft1, similarity))
                    processed_ids.add(ft2.id)
                elif similarity >= 0.5:  # Medium similarity - check concept equivalence
                    # Use AI to check if concepts are equivalent (cross-lingual check)
                    is_equivalent = await are_concepts_equivalent(ft1.name, ft2.name)
                    if is_equivalent:
                        self.log(f"  Cross-lingual: '{ft2.name}' ≡ '{ft1.name}'", level="verbose")
                        duplicates.append((ft2, ft1, 0.95))
                        processed_ids.add(ft2.id)

        self.stats["facet_types_duplicates"] = len(duplicates)
        self.log(f"Found {len(duplicates)} duplicate FacetTypes")

        return duplicates

    async def find_duplicate_entity_types(self) -> list[tuple[EntityType, EntityType, float]]:
        """
        Find duplicate EntityTypes using semantic similarity.

        Returns list of (duplicate, canonical, similarity_score) tuples.
        """
        self.log("\n=== Scanning EntityTypes for duplicates ===")

        result = await self.session.execute(
            select(EntityType).where(EntityType.is_active.is_(True)).order_by(EntityType.created_at.asc())
        )
        entity_types = result.scalars().all()

        self.log(f"Found {len(entity_types)} active EntityTypes")

        duplicates: list[tuple[EntityType, EntityType, float]] = []
        processed_ids: set[UUID] = set()

        for i, et1 in enumerate(entity_types):
            if et1.id in processed_ids:
                continue

            if et1.name_embedding is not None:
                emb1 = et1.name_embedding
            else:
                emb1 = await generate_embedding(et1.name)
                if emb1 is None:
                    continue

            for et2 in entity_types[i + 1 :]:
                if et2.id in processed_ids:
                    continue

                # Quick exact match check
                if et1.name.lower() == et2.name.lower() or et1.slug == et2.slug:
                    self.log(
                        f"  Exact duplicate: '{et2.name}' (slug: {et2.slug}) -> '{et1.name}' (slug: {et1.slug})",
                        level="verbose",
                    )
                    duplicates.append((et2, et1, 1.0))
                    processed_ids.add(et2.id)
                    continue

                if et2.name_embedding is not None:
                    emb2 = et2.name_embedding
                else:
                    emb2 = await generate_embedding(et2.name)
                    if emb2 is None:
                        continue

                similarity = _cosine_similarity(emb1, emb2)

                if similarity >= self.similarity_threshold:
                    self.log(f"  Similar: '{et2.name}' ({int(similarity * 100)}%) -> '{et1.name}'", level="verbose")
                    duplicates.append((et2, et1, similarity))
                    processed_ids.add(et2.id)
                elif similarity >= 0.5:  # Medium similarity - check concept equivalence
                    is_equivalent = await are_concepts_equivalent(et1.name, et2.name)
                    if is_equivalent:
                        self.log(f"  Cross-lingual: '{et2.name}' ≡ '{et1.name}'", level="verbose")
                        duplicates.append((et2, et1, 0.95))
                        processed_ids.add(et2.id)

        self.stats["entity_types_duplicates"] = len(duplicates)
        self.log(f"Found {len(duplicates)} duplicate EntityTypes")

        return duplicates

    async def find_duplicate_categories(self) -> list[tuple[Category, Category, float]]:
        """
        Find duplicate Categories using semantic similarity.

        Returns list of (duplicate, canonical, similarity_score) tuples.
        """
        self.log("\n=== Scanning Categories for duplicates ===")

        result = await self.session.execute(select(Category).order_by(Category.created_at.asc()))
        categories = result.scalars().all()

        self.log(f"Found {len(categories)} Categories")

        duplicates: list[tuple[Category, Category, float]] = []
        processed_ids: set[UUID] = set()

        for i, cat1 in enumerate(categories):
            if cat1.id in processed_ids:
                continue

            if hasattr(cat1, "name_embedding") and cat1.name_embedding is not None:
                emb1 = cat1.name_embedding
            else:
                emb1 = await generate_embedding(cat1.name)
                if emb1 is None:
                    continue

            for cat2 in categories[i + 1 :]:
                if cat2.id in processed_ids:
                    continue

                # Quick exact match check
                if cat1.name.lower() == cat2.name.lower() or cat1.slug == cat2.slug:
                    self.log(
                        f"  Exact duplicate: '{cat2.name}' (slug: {cat2.slug}) -> '{cat1.name}' (slug: {cat1.slug})",
                        level="verbose",
                    )
                    duplicates.append((cat2, cat1, 1.0))
                    processed_ids.add(cat2.id)
                    continue

                if hasattr(cat2, "name_embedding") and cat2.name_embedding is not None:
                    emb2 = cat2.name_embedding
                else:
                    emb2 = await generate_embedding(cat2.name)
                    if emb2 is None:
                        continue

                similarity = _cosine_similarity(emb1, emb2)

                if similarity >= self.similarity_threshold:
                    self.log(f"  Similar: '{cat2.name}' ({int(similarity * 100)}%) -> '{cat1.name}'", level="verbose")
                    duplicates.append((cat2, cat1, similarity))
                    processed_ids.add(cat2.id)
                elif similarity >= 0.5:  # Medium similarity - check concept equivalence
                    is_equivalent = await are_concepts_equivalent(cat1.name, cat2.name)
                    if is_equivalent:
                        self.log(f"  Cross-lingual: '{cat2.name}' ≡ '{cat1.name}'", level="verbose")
                        duplicates.append((cat2, cat1, 0.95))
                        processed_ids.add(cat2.id)

        self.stats["categories_duplicates"] = len(duplicates)
        self.log(f"Found {len(duplicates)} duplicate Categories")

        return duplicates

    async def merge_facet_types(
        self,
        duplicate: FacetType,
        canonical: FacetType,
    ):
        """
        Merge a duplicate FacetType into the canonical one.

        Updates all references and deactivates the duplicate.
        """
        self.log(f"Merging FacetType '{duplicate.name}' -> '{canonical.name}'")

        if self.dry_run:
            # Count affected records
            count = await self.session.execute(
                select(func.count()).select_from(FacetValue).where(FacetValue.facet_type_id == duplicate.id)
            )
            facet_value_count = count.scalar() or 0
            self.log(f"  Would update {facet_value_count} FacetValues", level="verbose")
            self.stats["references_updated"] += facet_value_count
        else:
            # Update FacetValue references
            result = await self.session.execute(
                update(FacetValue).where(FacetValue.facet_type_id == duplicate.id).values(facet_type_id=canonical.id)
            )
            updated = result.rowcount
            self.stats["references_updated"] += updated
            self.log(f"  Updated {updated} FacetValues", level="verbose")

            # Merge applicable_entity_type_slugs
            if duplicate.applicable_entity_type_slugs:
                merged_slugs = list(
                    set((canonical.applicable_entity_type_slugs or []) + (duplicate.applicable_entity_type_slugs or []))
                )
                canonical.applicable_entity_type_slugs = merged_slugs

            # Deactivate duplicate
            duplicate.is_active = False

            await self.session.flush()

        self.stats["facet_types_merged"] += 1

    async def merge_entity_types(
        self,
        duplicate: EntityType,
        canonical: EntityType,
    ):
        """
        Merge a duplicate EntityType into the canonical one.

        Updates all Entity references and deactivates the duplicate.
        """
        self.log(f"Merging EntityType '{duplicate.name}' -> '{canonical.name}'")

        if self.dry_run:
            count = await self.session.execute(
                select(func.count()).select_from(Entity).where(Entity.entity_type_id == duplicate.id)
            )
            entity_count = count.scalar() or 0
            self.log(f"  Would update {entity_count} Entities", level="verbose")
            self.stats["references_updated"] += entity_count
        else:
            # Update Entity references
            result = await self.session.execute(
                update(Entity).where(Entity.entity_type_id == duplicate.id).values(entity_type_id=canonical.id)
            )
            updated = result.rowcount
            self.stats["references_updated"] += updated
            self.log(f"  Updated {updated} Entities", level="verbose")

            # Update FacetType applicable_entity_type_slugs
            facet_types_result = await self.session.execute(
                select(FacetType).where(FacetType.applicable_entity_type_slugs.contains([duplicate.slug]))
            )
            for ft in facet_types_result.scalars().all():
                if ft.applicable_entity_type_slugs:
                    new_slugs = [canonical.slug if s == duplicate.slug else s for s in ft.applicable_entity_type_slugs]
                    ft.applicable_entity_type_slugs = list(set(new_slugs))

            # Deactivate duplicate
            duplicate.is_active = False

            await self.session.flush()

        self.stats["entity_types_merged"] += 1

    async def merge_categories(
        self,
        duplicate: Category,
        canonical: Category,
    ):
        """
        Merge a duplicate Category into the canonical one.

        Updates all DataSource and Entity references.
        """
        self.log(f"Merging Category '{duplicate.name}' -> '{canonical.name}'")

        from app.models import DataSource

        if self.dry_run:
            # Count affected DataSources
            count = await self.session.execute(
                select(func.count()).select_from(DataSource).where(DataSource.category_id == duplicate.id)
            )
            ds_count = count.scalar() or 0
            self.log(f"  Would update {ds_count} DataSources", level="verbose")
            self.stats["references_updated"] += ds_count
        else:
            # Update DataSource references
            result = await self.session.execute(
                update(DataSource).where(DataSource.category_id == duplicate.id).values(category_id=canonical.id)
            )
            updated = result.rowcount
            self.stats["references_updated"] += updated
            self.log(f"  Updated {updated} DataSources", level="verbose")

            # Update child categories
            children_result = await self.session.execute(select(Category).where(Category.parent_id == duplicate.id))
            for child in children_result.scalars().all():
                child.parent_id = canonical.id

            # Deactivate duplicate
            duplicate.is_active = False

            await self.session.flush()

        self.stats["categories_merged"] += 1

    async def cleanup_facet_types(self):
        """Find and cleanup duplicate FacetTypes."""
        duplicates = await self.find_duplicate_facet_types()

        for duplicate, canonical, score in duplicates:
            self.log(
                f"\n  '{duplicate.name}' ({duplicate.slug}) -> '{canonical.name}' ({canonical.slug}) [{int(score * 100)}%]"
            )
            await self.merge_facet_types(duplicate, canonical)

    async def cleanup_entity_types(self):
        """Find and cleanup duplicate EntityTypes."""
        duplicates = await self.find_duplicate_entity_types()

        for duplicate, canonical, score in duplicates:
            self.log(
                f"\n  '{duplicate.name}' ({duplicate.slug}) -> '{canonical.name}' ({canonical.slug}) [{int(score * 100)}%]"
            )
            await self.merge_entity_types(duplicate, canonical)

    async def cleanup_categories(self):
        """Find and cleanup duplicate Categories."""
        duplicates = await self.find_duplicate_categories()

        for duplicate, canonical, score in duplicates:
            self.log(
                f"\n  '{duplicate.name}' ({duplicate.slug}) -> '{canonical.name}' ({canonical.slug}) [{int(score * 100)}%]"
            )
            await self.merge_categories(duplicate, canonical)

    async def cleanup_all(self):
        """Run cleanup for all types."""
        await self.cleanup_facet_types()
        await self.cleanup_entity_types()
        await self.cleanup_categories()

        if not self.dry_run:
            await self.session.commit()
            self.log("\n=== Changes committed to database ===")
        else:
            self.log("\n=== Dry run complete - no changes made ===")

    def print_summary(self):
        """Print summary of the cleanup operation."""

        if self.stats["errors"]:
            for _error in self.stats["errors"]:
                pass

        if self.dry_run:
            pass


async def main():
    parser = argparse.ArgumentParser(description="Cleanup duplicate FacetTypes, EntityTypes, and Categories")
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
        "--type",
        choices=["facet_type", "entity_type", "category", "all"],
        default="all",
        help="Type to cleanup (default: all)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="Similarity threshold for merging (default: 0.85)",
    )

    args = parser.parse_args()

    if args.dry_run:
        pass

    async with get_session_context() as session:
        cleaner = DuplicateTypesCleaner(
            session=session,
            dry_run=args.dry_run,
            verbose=args.verbose,
            similarity_threshold=args.threshold,
        )

        if args.type == "all":
            await cleaner.cleanup_all()
        elif args.type == "facet_type":
            await cleaner.cleanup_facet_types()
            if not args.dry_run:
                await session.commit()
        elif args.type == "entity_type":
            await cleaner.cleanup_entity_types()
            if not args.dry_run:
                await session.commit()
        elif args.type == "category":
            await cleaner.cleanup_categories()
            if not args.dry_run:
                await session.commit()

        cleaner.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
