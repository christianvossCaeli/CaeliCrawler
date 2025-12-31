"""
Migration script: Convert legacy extracted_content fields to entity_references.

This script:
1. Finds all ExtractedData with municipality in extracted_content
2. Creates entity_references entries from those values
3. Updates categories with default entity_reference_config and display_fields

Run with: python -m scripts.migrate_to_entity_references
"""

import asyncio
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models import Category, Entity, EntityType, ExtractedData
from app.utils.text import normalize_entity_name


async def resolve_entity(
    session: AsyncSession,
    entity_type_slug: str,
    entity_name: str,
) -> UUID | None:
    """Resolve an entity name to its UUID."""
    try:
        et_result = await session.execute(
            select(EntityType).where(EntityType.slug == entity_type_slug)
        )
        entity_type = et_result.scalar_one_or_none()
        if not entity_type:
            return None

        name_normalized = normalize_entity_name(entity_name, country="DE")
        entity_result = await session.execute(
            select(Entity).where(
                Entity.entity_type_id == entity_type.id,
                Entity.name_normalized == name_normalized,
                Entity.is_active.is_(True),
            )
        )
        entity = entity_result.scalar_one_or_none()
        return entity.id if entity else None
    except Exception:
        return None


async def migrate_extracted_data(session: AsyncSession, batch_size: int = 100):
    """Migrate ExtractedData municipality to entity_references."""

    # Get all ExtractedData without entity_references but with municipality
    offset = 0
    total_migrated = 0
    total_skipped = 0

    while True:
        result = await session.execute(
            select(ExtractedData)
            .where(
                ExtractedData.entity_references.is_(None)
                | (ExtractedData.entity_references == [])
            )
            .offset(offset)
            .limit(batch_size)
        )
        extractions = result.scalars().all()

        if not extractions:
            break

        for ext in extractions:
            content = ext.extracted_content or {}
            municipality = content.get("municipality")

            if not municipality or not isinstance(municipality, str):
                total_skipped += 1
                continue

            if municipality.lower() in ("", "unbekannt", "null", "none"):
                total_skipped += 1
                continue

            # Resolve entity
            entity_id = await resolve_entity(session, "territorial-entity", municipality)

            # Create entity_references
            ext.entity_references = [{
                "entity_type": "territorial-entity",
                "entity_name": municipality,
                "entity_id": str(entity_id) if entity_id else None,
                "role": "primary",
                "confidence": ext.confidence_score or 0.5,
            }]

            if entity_id:
                ext.primary_entity_id = entity_id

            total_migrated += 1

        await session.commit()
        offset += batch_size



async def update_categories(session: AsyncSession):
    """Set default entity_reference_config and display_fields for categories."""

    # Default configuration for categories that analyze documents
    default_entity_ref_config = {
        "entity_types": ["territorial-entity", "person"],
        "field_mappings": {
            "municipality": "territorial-entity",
            "region": "territorial-entity",
        },
        "array_field_mappings": {
            "decision_makers": {
                "entity_type": "person",
                "name_fields": ["name", "person"],
                "role_field": "role",
                "default_role": "decision_maker",
            }
        }
    }

    default_display_fields = {
        "columns": [
            {"key": "document", "label": "Dokument", "type": "document_link", "width": "220px"},
            {"key": "entity_references.territorial-entity", "label": "Kommune", "type": "entity_link", "width": "150px"},
            {"key": "confidence_score", "label": "Konfidenz", "type": "confidence", "width": "110px"},
            {"key": "relevance_score", "label": "Relevanz", "type": "confidence", "width": "110px"},
            {"key": "human_verified", "label": "Geprüft", "type": "boolean", "width": "80px"},
            {"key": "created_at", "label": "Erfasst", "type": "date", "width": "100px"},
        ],
        "entity_reference_columns": ["territorial-entity"],
    }

    # Update categories without entity_reference_config
    result = await session.execute(
        select(Category).where(Category.entity_reference_config.is_(None))
    )
    categories = result.scalars().all()

    updated = 0
    for cat in categories:
        cat.entity_reference_config = default_entity_ref_config
        cat.display_fields = default_display_fields
        updated += 1  # noqa: SIM113

    await session.commit()


async def main():
    """Run the migration."""

    async with async_session_factory() as session:
        await migrate_extracted_data(session)
        await update_categories(session)



if __name__ == "__main__":
    asyncio.run(main())
