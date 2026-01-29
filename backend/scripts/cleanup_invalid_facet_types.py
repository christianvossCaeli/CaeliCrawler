#!/usr/bin/env python3
"""Cleanup script for invalid FacetTypes created by AI extraction.

This script identifies and removes FacetTypes that were incorrectly created
from internal AI extraction fields (like 'suggested_additional_pages').

Usage:
    # Dry run (analysis only)
    python -m scripts.cleanup_invalid_facet_types --dry-run

    # Execute cleanup
    python -m scripts.cleanup_invalid_facet_types

    # With verbose output
    python -m scripts.cleanup_invalid_facet_types --verbose
"""

import asyncio
import sys
from pathlib import Path
from uuid import UUID

import structlog

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models import FacetType, FacetValue

logger = structlog.get_logger(__name__)

# FacetType slugs that should never exist (internal AI extraction fields)
INVALID_FACET_TYPE_SLUGS = {
    "suggested_additional_pages",
    "source_page",
    "source_pages",
    "page_numbers",
    "analyzed_pages",
    "total_pages",
    "meta",
    "metadata",
    # Add more as discovered
}

# Patterns that indicate invalid FacetTypes (regex-like patterns)
INVALID_SLUG_PATTERNS = [
    "page",  # Any slug containing 'page' is likely internal
]


class FacetTypeCleanup:
    """Service for cleaning up invalid FacetTypes."""

    def __init__(self, session: AsyncSession, dry_run: bool = True, verbose: bool = False):
        self.session = session
        self.dry_run = dry_run
        self.verbose = verbose

    async def find_invalid_facet_types(self) -> list[FacetType]:
        """Find FacetTypes with invalid slugs."""
        # Get all FacetTypes
        result = await self.session.execute(
            select(FacetType).where(FacetType.is_active.is_(True))
        )
        all_types = result.scalars().all()

        invalid_types = []
        for ft in all_types:
            slug = ft.slug.lower()

            # Check exact matches
            if slug in INVALID_FACET_TYPE_SLUGS:
                invalid_types.append(ft)
                continue

            # Check pattern matches
            for pattern in INVALID_SLUG_PATTERNS:
                if pattern in slug and ft.is_system is False:
                    # Only flag non-system types with suspicious patterns
                    invalid_types.append(ft)
                    break

        return invalid_types

    async def count_facet_values(self, facet_type_id: UUID) -> int:
        """Count FacetValues for a FacetType."""
        result = await self.session.execute(
            select(func.count(FacetValue.id)).where(
                FacetValue.facet_type_id == facet_type_id
            )
        )
        return result.scalar() or 0

    async def delete_facet_type(self, facet_type: FacetType) -> tuple[int, int]:
        """Delete a FacetType and its FacetValues.

        Returns:
            Tuple of (facet_values_deleted, facet_types_deleted)
        """
        # Count values first
        value_count = await self.count_facet_values(facet_type.id)

        if self.dry_run:
            logger.info(
                "Would delete FacetType",
                slug=facet_type.slug,
                name=facet_type.name,
                facet_values=value_count,
                dry_run=True,
            )
            return value_count, 1

        # Delete FacetValues first (foreign key constraint)
        await self.session.execute(
            delete(FacetValue).where(FacetValue.facet_type_id == facet_type.id)
        )

        # Delete FacetType
        await self.session.delete(facet_type)
        await self.session.flush()

        logger.info(
            "Deleted FacetType",
            slug=facet_type.slug,
            name=facet_type.name,
            facet_values_deleted=value_count,
        )

        return value_count, 1

    async def run(self) -> dict:
        """Run the cleanup process.

        Returns:
            Summary statistics
        """
        print("\n" + "=" * 60)
        print("FacetType Cleanup Script")
        print("=" * 60)
        print(f"Mode: {'DRY RUN' if self.dry_run else 'EXECUTE'}")
        print()

        # Find invalid FacetTypes
        invalid_types = await self.find_invalid_facet_types()

        if not invalid_types:
            print("No invalid FacetTypes found.")
            return {"facet_types": 0, "facet_values": 0}

        print(f"Found {len(invalid_types)} invalid FacetType(s):\n")

        total_values = 0
        total_types = 0

        for ft in invalid_types:
            value_count = await self.count_facet_values(ft.id)
            print(f"  - {ft.slug}")
            print(f"    Name: {ft.name}")
            print(f"    Description: {ft.description[:80] if ft.description else 'N/A'}...")
            print(f"    FacetValues: {value_count}")
            print(f"    needs_review: {ft.needs_review}")
            print()

            values_deleted, types_deleted = await self.delete_facet_type(ft)
            total_values += values_deleted
            total_types += types_deleted

        if not self.dry_run:
            await self.session.commit()

        print("\n" + "-" * 60)
        print("Summary:")
        print(f"  FacetTypes {'would be' if self.dry_run else ''} deleted: {total_types}")
        print(f"  FacetValues {'would be' if self.dry_run else ''} deleted: {total_values}")
        print("-" * 60)

        return {"facet_types": total_types, "facet_values": total_values}


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Cleanup invalid FacetTypes")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Analyze only, don't delete anything",
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
        cleanup = FacetTypeCleanup(
            session=session,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
        result = await cleanup.run()

    return result


if __name__ == "__main__":
    asyncio.run(main())
