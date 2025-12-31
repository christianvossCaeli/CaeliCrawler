#!/usr/bin/env python3
"""
Populate all embedding columns in the database.

This script should be run after migrations to fill embedding columns
for existing data. It uses batch processing to minimize API calls.

Usage:
    python populate_embeddings.py [--all] [--types] [--entities] [--facets] [--force]

Options:
    --all       Populate all embeddings (default if no options specified)
    --types     Only populate type embeddings (EntityType, FacetType, Category, RelationType)
    --entities  Only populate Entity embeddings
    --facets    Only populate FacetValue embeddings
    --force     Regenerate all embeddings (even existing ones)
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import async_session_factory
from app.models import Category, EntityType, FacetType
from app.utils.similarity import (
    batch_update_embeddings,
    batch_update_facet_value_embeddings,
    batch_update_relation_type_embeddings,
    batch_update_type_embeddings,
    get_similarity_stats,
    populate_all_embeddings,
    reset_similarity_stats,
)


async def main():
    parser = argparse.ArgumentParser(description="Populate embedding columns in the database")
    parser.add_argument("--all", action="store_true", help="Populate all embeddings")
    parser.add_argument("--types", action="store_true", help="Only type embeddings")
    parser.add_argument("--entities", action="store_true", help="Only Entity embeddings")
    parser.add_argument("--facets", action="store_true", help="Only FacetValue embeddings")
    parser.add_argument("--force", action="store_true", help="Regenerate all (even existing)")

    args = parser.parse_args()

    # Default to --all if no options specified
    if not any([args.all, args.types, args.entities, args.facets]):
        args.all = True

    only_missing = not args.force


    reset_similarity_stats()

    async with async_session_factory() as session:
        results = {}

        if args.all:
            results = await populate_all_embeddings(session, only_missing=only_missing)
        else:
            if args.types:
                results["entity_types"] = await batch_update_type_embeddings(
                    session, EntityType, only_missing
                )
                results["facet_types"] = await batch_update_type_embeddings(
                    session, FacetType, only_missing
                )
                results["categories"] = await batch_update_type_embeddings(
                    session, Category, only_missing
                )
                results["relation_types"] = await batch_update_relation_type_embeddings(
                    session, only_missing
                )
                await session.commit()

            if args.entities:
                results["entities"] = await batch_update_embeddings(
                    session, only_missing=only_missing
                )
                await session.commit()

            if args.facets:
                results["facet_values"] = await batch_update_facet_value_embeddings(
                    session, only_missing=only_missing
                )
                await session.commit()

    # Print results

    total = 0
    for _key, count in results.items():
        total += count


    get_similarity_stats()


if __name__ == "__main__":
    asyncio.run(main())
