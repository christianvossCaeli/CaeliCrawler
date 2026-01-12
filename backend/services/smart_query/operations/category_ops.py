"""Category and relation operations for Smart Query Service.

Operations:
- assign_facet_types: Assign facet types to entity types
- link_category_entity_types: Link a category to entity types
- link_existing_category: Link an existing category
- create_relation_type: Create a new relation type
"""

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .base import OperationResult, WriteOperation, register_operation

logger = structlog.get_logger()


@register_operation("assign_facet_types")
class AssignFacetTypesOperation(WriteOperation):
    """Assign facet types to entity types.

    Supports two formats:
    1. Single facet to multiple entity types:
       - facet_type_slug: "pain_point"
       - target_entity_type_slugs: ["territorial_entity", "windpark"]

    2. Multiple facets to single entity type:
       - entity_type_slug: "territorial_entity"
       - facet_type_slugs: ["pain_point", "contact"]
    """

    async def execute(
        self,
        session: AsyncSession,
        command: dict[str, Any],
        user_id: UUID | None = None,
    ) -> OperationResult:
        from app.models import EntityType, FacetType

        assign_data = command.get("assign_data", {})

        # Support both formats
        facet_type_slug = assign_data.get("facet_type_slug")  # Single facet
        target_entity_type_slugs = assign_data.get("target_entity_type_slugs", [])  # Multiple targets

        entity_type_slug = assign_data.get("entity_type_slug")  # Single target
        facet_type_slugs = assign_data.get("facet_type_slugs", [])  # Multiple facets

        auto_detect = assign_data.get("auto_detect", False)

        assigned_facets = []
        assigned_to_entity_types = []

        try:
            # Format 1: Single facet to multiple entity types
            if facet_type_slug and target_entity_type_slugs:
                ft_result = await session.execute(select(FacetType).where(FacetType.slug == facet_type_slug))
                facet_type = ft_result.scalar_one_or_none()

                if not facet_type:
                    return OperationResult(
                        success=False,
                        message=f"Facet-Typ '{facet_type_slug}' nicht gefunden",
                    )

                # Verify entity types exist
                for et_slug in target_entity_type_slugs:
                    et_result = await session.execute(select(EntityType).where(EntityType.slug == et_slug))
                    if et_result.scalar_one_or_none():
                        # Add to applicable_entity_type_slugs if not already there
                        current_slugs = list(facet_type.applicable_entity_type_slugs or [])
                        if et_slug not in current_slugs:
                            current_slugs.append(et_slug)
                            facet_type.applicable_entity_type_slugs = current_slugs
                            assigned_to_entity_types.append(et_slug)

                assigned_facets.append(facet_type_slug)
                await session.flush()

                return OperationResult(
                    success=True,
                    message=f"Facet '{facet_type_slug}' für {len(assigned_to_entity_types)} Entity-Types aktiviert",
                    data={
                        "assigned_facets": assigned_facets,
                        "assigned_to_entity_types": assigned_to_entity_types,
                    },
                )

            # Format 2: Multiple facets to single entity type
            if entity_type_slug:
                # Verify entity type exists
                et_result = await session.execute(select(EntityType).where(EntityType.slug == entity_type_slug))
                entity_type = et_result.scalar_one_or_none()

                if not entity_type:
                    return OperationResult(
                        success=False,
                        message=f"Entity-Typ '{entity_type_slug}' nicht gefunden",
                    )

                # Get facet types
                if auto_detect or not facet_type_slugs:
                    ft_result = await session.execute(select(FacetType).where(FacetType.is_active))
                    facet_types = list(ft_result.scalars().all())
                else:
                    ft_result = await session.execute(select(FacetType).where(FacetType.slug.in_(facet_type_slugs)))
                    facet_types = list(ft_result.scalars().all())

                for facet_type in facet_types:
                    current_slugs = list(facet_type.applicable_entity_type_slugs or [])
                    if entity_type_slug not in current_slugs:
                        current_slugs.append(entity_type_slug)
                        facet_type.applicable_entity_type_slugs = current_slugs
                        assigned_facets.append(facet_type.slug)

                await session.flush()

                return OperationResult(
                    success=True,
                    message=f"{len(assigned_facets)} Facet-Types für '{entity_type_slug}' aktiviert",
                    data={
                        "assigned_facets": assigned_facets,
                        "assigned_to_entity_types": [entity_type_slug],
                    },
                )

            return OperationResult(
                success=False,
                message="Keine gültige Konfiguration: entity_type_slug oder facet_type_slug + target_entity_type_slugs erforderlich",
            )

        except Exception as e:
            logger.error("Assign facet types failed", error=str(e), exc_info=True)
            return OperationResult(
                success=False,
                message=f"Fehler: {str(e)}",
            )


@register_operation("link_category_entity_types")
class LinkCategoryEntityTypesOperation(WriteOperation):
    """Link entity types to categories."""

    async def execute(
        self,
        session: AsyncSession,
        command: dict[str, Any],
        user_id: UUID | None = None,
    ) -> OperationResult:
        from app.models import Category, CategoryEntityType, EntityType

        link_data = command.get("link_data", {})

        category_slug = link_data.get("category_slug")
        entity_type_slugs = link_data.get("entity_type_slugs", [])
        auto_detect = link_data.get("auto_detect", False)

        linked_entity_types = []
        linked_categories = []

        try:
            if auto_detect:
                # Get all categories
                cat_result = await session.execute(select(Category))
                categories = list(cat_result.scalars().all())
            else:
                cat_result = await session.execute(select(Category).where(Category.slug == category_slug))
                categories = list(cat_result.scalars().all())

            if not categories:
                return OperationResult(
                    success=False,
                    message="Keine passenden Kategorien gefunden",
                )

            # Get entity types
            et_result = await session.execute(select(EntityType).where(EntityType.slug.in_(entity_type_slugs)))
            entity_types = list(et_result.scalars().all())

            if not entity_types:
                return OperationResult(
                    success=False,
                    message="Keine passenden Entity-Types gefunden",
                )

            # Create links
            for category in categories:
                for entity_type in entity_types:
                    # Check if link already exists
                    existing = await session.execute(
                        select(CategoryEntityType).where(
                            CategoryEntityType.category_id == category.id,
                            CategoryEntityType.entity_type_id == entity_type.id,
                        )
                    )
                    if not existing.scalar_one_or_none():
                        link = CategoryEntityType(
                            category_id=category.id,
                            entity_type_id=entity_type.id,
                            is_primary=(entity_type.slug == "territorial_entity"),
                        )
                        session.add(link)
                        linked_entity_types.append(entity_type.slug)
                        linked_categories.append(category.slug)

            await session.flush()

            return OperationResult(
                success=True,
                message=f"{len(set(linked_entity_types))} Entity-Types mit {len(set(linked_categories))} Kategorien verknüpft",
                data={
                    "linked_entity_types": list(set(linked_entity_types)),
                    "linked_categories": list(set(linked_categories)),
                },
            )

        except Exception as e:
            logger.error("Link category entity types failed", error=str(e), exc_info=True)
            return OperationResult(
                success=False,
                message=f"Fehler: {str(e)}",
            )


@register_operation("link_existing_category")
class LinkExistingCategoryOperation(WriteOperation):
    """Link to an existing category by slug.

    This is used when the AI references an existing category instead of creating a new one.
    """

    async def execute(
        self,
        session: AsyncSession,
        command: dict[str, Any],
        user_id: UUID | None = None,
    ) -> OperationResult:
        from app.models import Category

        link_data = command.get("link_data", {})
        category_slug = link_data.get("category_slug") or command.get("category_slug")

        if not category_slug:
            return OperationResult(
                success=False,
                message="category_slug erforderlich",
            )

        try:
            cat_result = await session.execute(select(Category).where(Category.slug == category_slug))
            category = cat_result.scalar_one_or_none()

            if not category:
                return OperationResult(
                    success=False,
                    message=f"Kategorie '{category_slug}' nicht gefunden",
                )

            return OperationResult(
                success=True,
                message=f"Kategorie '{category.name}' verknüpft",
                data={
                    "category_id": str(category.id),
                    "category_slug": category.slug,
                    "category_name": category.name,
                },
            )

        except Exception as e:
            logger.error("Link existing category failed", error=str(e), exc_info=True)
            return OperationResult(
                success=False,
                message=f"Fehler: {str(e)}",
            )


@register_operation("create_relation_type")
class CreateRelationTypeOperation(WriteOperation):
    """Create or verify a relation type between entity types."""

    async def execute(
        self,
        session: AsyncSession,
        command: dict[str, Any],
        user_id: UUID | None = None,
    ) -> OperationResult:
        from app.models import EntityType, RelationType

        relation_data = command.get("relation_type_data", {})

        relation_type_slug = relation_data.get("relation_type")
        source_type_slug = relation_data.get("source_type")
        target_type_slug = relation_data.get("target_type")

        try:
            # Find the existing relation type
            rt_result = await session.execute(select(RelationType).where(RelationType.slug == relation_type_slug))
            relation_type = rt_result.scalar_one_or_none()

            if not relation_type:
                return OperationResult(
                    success=False,
                    message=f"Relation-Typ '{relation_type_slug}' nicht gefunden",
                )

            # Verify entity types exist
            source_result = await session.execute(select(EntityType).where(EntityType.slug == source_type_slug))
            source_type = source_result.scalar_one_or_none()

            target_result = await session.execute(select(EntityType).where(EntityType.slug == target_type_slug))
            target_type = target_result.scalar_one_or_none()

            if not source_type:
                return OperationResult(
                    success=False,
                    message=f"Quell-Entity-Typ '{source_type_slug}' nicht gefunden",
                )

            if not target_type:
                return OperationResult(
                    success=False,
                    message=f"Ziel-Entity-Typ '{target_type_slug}' nicht gefunden",
                )

            return OperationResult(
                success=True,
                message=f"Relation '{relation_type.name}' ({source_type.name} → {target_type.name}) verifiziert",
                data={
                    "relation_type_slug": relation_type_slug,
                    "source_type_slug": source_type_slug,
                    "target_type_slug": target_type_slug,
                },
            )

        except Exception as e:
            logger.error("Create relation type failed", error=str(e), exc_info=True)
            return OperationResult(
                success=False,
                message=f"Fehler: {str(e)}",
            )
