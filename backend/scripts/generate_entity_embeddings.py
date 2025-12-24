#!/usr/bin/env python3
"""
Generate embeddings for existing entities.

This script generates name embeddings for all entities that don't have one yet.
It uses the Azure OpenAI text-embedding-3-large model via the AI service.

Usage:
    # Generate embeddings for all entities without embeddings
    python scripts/generate_entity_embeddings.py

    # Generate embeddings for a specific entity type
    python scripts/generate_entity_embeddings.py --entity-type territorial_entity

    # Force regenerate all embeddings (even if they exist)
    python scripts/generate_entity_embeddings.py --force

    # Limit the number of entities to process
    python scripts/generate_entity_embeddings.py --limit 100

    # Use a smaller batch size (default: 100)
    python scripts/generate_entity_embeddings.py --batch-size 50
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models import Entity, EntityType
from services.ai_service import AIService

logger = structlog.get_logger(__name__)


async def get_entity_stats(session: AsyncSession) -> dict:
    """Get statistics about entity embeddings."""
    total = (await session.execute(
        select(func.count()).select_from(Entity).where(Entity.is_active.is_(True))
    )).scalar()

    with_embedding = (await session.execute(
        select(func.count()).select_from(Entity).where(
            Entity.is_active.is_(True),
            Entity.name_embedding.isnot(None),
        )
    )).scalar()

    return {
        "total": total,
        "with_embedding": with_embedding,
        "without_embedding": total - with_embedding,
    }


async def generate_embeddings(
    entity_type_slug: str | None = None,
    force: bool = False,
    limit: int | None = None,
    batch_size: int = 100,
) -> int:
    """
    Generate embeddings for entities.

    Args:
        entity_type_slug: Optional entity type to filter by
        force: If True, regenerate all embeddings even if they exist
        limit: Maximum number of entities to process
        batch_size: Number of entities to process per API call

    Returns:
        Number of entities updated
    """
    async with async_session_factory() as session:
        # Print initial stats
        stats = await get_entity_stats(session)
        logger.info(
            "Entity embedding statistics",
            total=stats["total"],
            with_embedding=stats["with_embedding"],
            without_embedding=stats["without_embedding"],
        )

        # Build query
        query = select(Entity).where(Entity.is_active.is_(True))

        if entity_type_slug:
            # Get entity type ID
            et_result = await session.execute(
                select(EntityType).where(EntityType.slug == entity_type_slug)
            )
            entity_type = et_result.scalar_one_or_none()
            if not entity_type:
                logger.error(f"Entity type not found: {entity_type_slug}")
                return 0
            query = query.where(Entity.entity_type_id == entity_type.id)
            logger.info(f"Filtering by entity type: {entity_type_slug}")

        if not force:
            query = query.where(Entity.name_embedding.is_(None))

        if limit:
            query = query.limit(limit)

        # Get entities
        result = await session.execute(query)
        entities = result.scalars().all()

        if not entities:
            logger.info("No entities need embedding updates")
            return 0

        logger.info(f"Processing {len(entities)} entities...")

        ai_service = AIService()
        updated_count = 0
        failed_count = 0

        # Process in batches
        for i in range(0, len(entities), batch_size):
            batch = entities[i : i + batch_size]
            names = [e.name for e in batch]
            batch_num = i // batch_size + 1
            total_batches = (len(entities) + batch_size - 1) // batch_size

            try:
                logger.info(f"Processing batch {batch_num}/{total_batches}...")
                embeddings = await ai_service.generate_embeddings(names)

                for entity, embedding in zip(batch, embeddings):
                    try:
                        # Update via ORM - pgvector handles the conversion
                        entity.name_embedding = embedding
                        updated_count += 1
                    except Exception as e:
                        logger.error(f"Failed to update entity {entity.id}: {e}")
                        failed_count += 1

                await session.commit()
                logger.info(
                    f"Batch {batch_num} complete",
                    updated=updated_count,
                    failed=failed_count,
                )

            except Exception as e:
                logger.error(f"Failed to process batch {batch_num}: {e}")
                await session.rollback()
                failed_count += len(batch)

        # Print final stats
        final_stats = await get_entity_stats(session)
        logger.info(
            "Embedding generation complete",
            updated=updated_count,
            failed=failed_count,
            total_with_embedding=final_stats["with_embedding"],
        )

        return updated_count


async def main():
    parser = argparse.ArgumentParser(
        description="Generate embeddings for existing entities"
    )
    parser.add_argument(
        "--entity-type",
        type=str,
        help="Only process entities of this type (e.g., 'territorial_entity')",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate embeddings even if they exist",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of entities to process",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of entities per API batch (default: 100)",
    )

    args = parser.parse_args()

    updated = await generate_embeddings(
        entity_type_slug=args.entity_type,
        force=args.force,
        limit=args.limit,
        batch_size=args.batch_size,
    )

    print(f"\nUpdated {updated} entities with embeddings.")


if __name__ == "__main__":
    asyncio.run(main())
