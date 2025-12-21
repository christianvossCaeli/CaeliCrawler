"""Multi-Entity Extraction Service for processing multiple EntityTypes per Category."""

import uuid
from typing import Any, Dict, List, Optional, Tuple

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Category,
    CategoryEntityType,
    Entity,
    EntityRelation,
    EntityType,
    FacetType,
    FacetValue,
    RelationType,
)
from app.utils.text import normalize_entity_name, create_slug
from services.entity_matching_service import EntityMatchingService

logger = structlog.get_logger()


class MultiEntityExtractionService:
    """
    Service for handling extraction of multiple EntityTypes from documents.

    When a Category is configured with multiple EntityTypes, this service:
    1. Generates appropriate extraction prompts for each type
    2. Processes extraction results to create entities of each type
    3. Creates relations between entities based on configuration
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_extraction_prompt(self, category: Category) -> str:
        """
        Generate a multi-entity extraction prompt for a category.

        Returns a prompt that instructs the AI to extract entities of
        all configured types with their relations.
        """
        # Load associations with entity types
        result = await self.session.execute(
            select(CategoryEntityType)
            .where(CategoryEntityType.category_id == category.id)
            .options(selectinload(CategoryEntityType.entity_type))
            .order_by(CategoryEntityType.extraction_order)
        )
        associations = result.scalars().all()

        if not associations:
            # Fallback to legacy single entity type
            if category.ai_extraction_prompt:
                return category.ai_extraction_prompt
            return self._get_default_prompt()

        # Build multi-entity prompt
        prompt_parts = [
            f"Extrahiere aus dem folgenden Text Informationen für die Kategorie '{category.name}'.",
            f"Zweck: {category.purpose}",
            "",
            "Zu extrahierende Entity-Typen:",
        ]

        for i, assoc in enumerate(associations, 1):
            entity_type = assoc.entity_type
            config = assoc.extraction_config or {}

            prompt_parts.append(f"\n{i}. {entity_type.name.upper()} ({entity_type.slug}):")
            prompt_parts.append(f"   Beschreibung: {entity_type.description or 'Keine Beschreibung'}")

            if entity_type.attribute_schema:
                fields = entity_type.attribute_schema.get("properties", {})
                if fields:
                    prompt_parts.append("   Zu extrahierende Felder:")
                    for field_name, field_def in fields.items():
                        field_type = field_def.get("type", "string")
                        prompt_parts.append(f"   - {field_name} ({field_type})")

            if config.get("extraction_hints"):
                prompt_parts.append(f"   Hinweise: {config['extraction_hints']}")

            is_primary = "(HAUPT-ENTITY)" if assoc.is_primary else ""
            prompt_parts.append(f"   {is_primary}")

        # Add relations section
        all_relations = []
        for assoc in associations:
            if assoc.relation_config:
                all_relations.extend(assoc.relation_config)

        if all_relations:
            prompt_parts.append("\nZU EXTRAHIERENDE RELATIONEN:")
            for rel in all_relations:
                from_type = rel.get("from_type", "?")
                to_type = rel.get("to_type", "?")
                relation = rel.get("relation", "related_to")
                prompt_parts.append(f"   - {from_type} --[{relation}]--> {to_type}")

        prompt_parts.extend([
            "",
            "Antworte im JSON-Format mit folgendem Schema:",
            "{",
            '  "entities": {',
            '    "<entity_type_slug>": [',
            '      {',
            '        "name": "...",',
            '        "attributes": {...}',
            '      }',
            '    ]',
            '  },',
            '  "relations": [',
            '    {',
            '      "from_type": "...",',
            '      "from_name": "...",',
            '      "relation": "...",',
            '      "to_type": "...",',
            '      "to_name": "..."',
            '    }',
            '  ]',
            "}",
        ])

        return "\n".join(prompt_parts)

    async def process_extraction_result(
        self,
        category: Category,
        extracted_data: Dict[str, Any],
        document_id: Optional[uuid.UUID] = None,
        source_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process multi-entity extraction results.

        Args:
            category: The category being processed
            extracted_data: AI extraction result containing entities and relations
            document_id: Optional source document ID
            source_url: Optional source URL

        Returns:
            Dict with created entities and relations statistics
        """
        result = {
            "entities_created": {},
            "entities_found": {},
            "relations_created": 0,
            "errors": [],
        }

        # Load associations to get entity type mappings
        assoc_result = await self.session.execute(
            select(CategoryEntityType)
            .where(CategoryEntityType.category_id == category.id)
            .options(selectinload(CategoryEntityType.entity_type))
        )
        associations = {
            assoc.entity_type.slug: assoc.entity_type
            for assoc in assoc_result.scalars().all()
        }

        # Track created/found entities for relation creation
        entity_map: Dict[Tuple[str, str], Entity] = {}

        # Process entities by type
        entities_data = extracted_data.get("entities", {})
        for type_slug, entity_list in entities_data.items():
            if type_slug not in associations:
                result["errors"].append(f"Unknown entity type: {type_slug}")
                continue

            entity_type = associations[type_slug]
            created_count = 0
            found_count = 0

            # Collect all names for batch lookup (N+1 Query Fix)
            names = [
                entity_data.get("name")
                for entity_data in entity_list
                if entity_data.get("name")
            ]

            # Batch find existing entities
            existing_entities = await self._batch_find_entities(entity_type.id, names)

            for entity_data in entity_list:
                name = entity_data.get("name")
                if not name:
                    continue

                # Check batch results instead of individual query
                existing = existing_entities.get(name)
                if existing:
                    entity_map[(type_slug, name)] = existing
                    found_count += 1
                else:
                    # Create new entity using EntityMatchingService for consistency
                    # This ensures proper name_normalized, slug, and race-condition safety
                    entity_service = EntityMatchingService(self.session)
                    new_entity = await entity_service.get_or_create_entity(
                        entity_type_slug=type_slug,
                        name=name,
                        core_attributes=entity_data.get("attributes", {}),
                    )
                    if new_entity:
                        entity_map[(type_slug, name)] = new_entity
                        # Check if entity was just created or found by EntityMatchingService
                        if new_entity.name not in existing_entities:
                            created_count += 1
                        else:
                            found_count += 1

            result["entities_created"][type_slug] = created_count
            result["entities_found"][type_slug] = found_count

        # Process relations with batch queries (N+1 Query Fix)
        relations_data = extracted_data.get("relations", [])
        if relations_data:
            # Step 1: Batch-load all required RelationTypes (1 query instead of N)
            relation_slugs = {
                rel_data.get("relation", "related_to")
                for rel_data in relations_data
            }
            relation_type_cache = await self._batch_get_or_create_relation_types(
                list(relation_slugs)
            )

            # Step 2: Pre-calculate all potential relation keys for batch existence check
            potential_relations = []
            for rel_data in relations_data:
                from_type = rel_data.get("from_type")
                from_name = rel_data.get("from_name")
                to_type = rel_data.get("to_type")
                to_name = rel_data.get("to_name")
                relation_slug = rel_data.get("relation", "related_to")

                from_entity = entity_map.get((from_type, from_name))
                to_entity = entity_map.get((to_type, to_name))
                relation_type = relation_type_cache.get(relation_slug)

                if from_entity and to_entity and relation_type:
                    potential_relations.append({
                        "from_entity": from_entity,
                        "to_entity": to_entity,
                        "relation_type": relation_type,
                    })

            # Step 3: Batch check existing relations (1 query instead of N)
            existing_relations_set = await self._batch_find_existing_relations(
                potential_relations
            )

            # Step 4: Create only non-existing relations
            for rel in potential_relations:
                try:
                    key = (
                        rel["from_entity"].id,
                        rel["to_entity"].id,
                        rel["relation_type"].id,
                    )
                    if key not in existing_relations_set:
                        new_relation = EntityRelation(
                            source_entity_id=rel["from_entity"].id,
                            target_entity_id=rel["to_entity"].id,
                            relation_type_id=rel["relation_type"].id,
                        )
                        self.session.add(new_relation)
                        result["relations_created"] += 1
                except Exception as e:
                    result["errors"].append(f"Error creating relation: {str(e)}")

        await self.session.commit()

        logger.info(
            "Multi-entity extraction completed",
            category=category.name,
            entities_created=result["entities_created"],
            entities_found=result["entities_found"],
            relations_created=result["relations_created"],
            errors_count=len(result["errors"]),
        )

        return result

    async def _find_entity(
        self, entity_type_id: uuid.UUID, name: str
    ) -> Optional[Entity]:
        """Find an existing entity by type and normalized name.

        Uses normalized name for consistent matching.
        """
        name_normalized = normalize_entity_name(name, country="DE")
        result = await self.session.execute(
            select(Entity).where(
                Entity.entity_type_id == entity_type_id,
                Entity.name_normalized == name_normalized,
                Entity.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def _batch_find_entities(
        self, entity_type_id: uuid.UUID, names: List[str], chunk_size: int = 100
    ) -> Dict[str, Entity]:
        """
        Batch find existing entities by type and names.

        Optimized to avoid N+1 query problem by fetching all
        entities in chunked queries to prevent SQL IN clause overflow.

        Uses normalized names for consistent matching across all import paths.

        Args:
            entity_type_id: The entity type UUID
            names: List of entity names to find
            chunk_size: Maximum number of names per query (default: 100)

        Returns:
            Dict mapping entity name to Entity object
        """
        if not names:
            return {}

        # Build normalized name mapping for consistent matching
        name_to_normalized: Dict[str, str] = {}
        normalized_to_names: Dict[str, List[str]] = {}

        for name in names:
            normalized = normalize_entity_name(name, country="DE")
            name_to_normalized[name] = normalized
            if normalized not in normalized_to_names:
                normalized_to_names[normalized] = []
            normalized_to_names[normalized].append(name)

        # Get unique normalized names for query
        unique_normalized = list(normalized_to_names.keys())
        entities: Dict[str, Entity] = {}

        # Process in chunks to prevent SQL IN clause from becoming too large
        for i in range(0, len(unique_normalized), chunk_size):
            chunk = unique_normalized[i : i + chunk_size]

            result = await self.session.execute(
                select(Entity).where(
                    Entity.entity_type_id == entity_type_id,
                    Entity.name_normalized.in_(chunk),  # Use normalized name for matching
                    Entity.is_active.is_(True),
                )
            )

            for entity in result.scalars().all():
                # Map entity to all original names that normalize to this
                entities[entity.name] = entity
                entities[entity.name_normalized] = entity
                # Also map to any original names that were requested
                if entity.name_normalized in normalized_to_names:
                    for original_name in normalized_to_names[entity.name_normalized]:
                        entities[original_name] = entity

        return entities

    async def _find_or_create_relation_type(self, slug: str) -> RelationType:
        """Find or create a relation type by slug."""
        result = await self.session.execute(
            select(RelationType).where(RelationType.slug == slug)
        )
        relation_type = result.scalar_one_or_none()

        if not relation_type:
            # Create new relation type
            relation_type = RelationType(
                slug=slug,
                name=slug.replace("_", " ").title(),
                name_reverse=f"reverse of {slug}".title(),
            )
            self.session.add(relation_type)
            await self.session.flush()

        return relation_type

    async def _find_relation(
        self,
        source_id: uuid.UUID,
        target_id: uuid.UUID,
        relation_type_id: uuid.UUID,
    ) -> Optional[EntityRelation]:
        """Find an existing relation."""
        result = await self.session.execute(
            select(EntityRelation).where(
                EntityRelation.source_entity_id == source_id,
                EntityRelation.target_entity_id == target_id,
                EntityRelation.relation_type_id == relation_type_id,
            )
        )
        return result.scalar_one_or_none()

    async def _batch_get_or_create_relation_types(
        self, slugs: List[str]
    ) -> Dict[str, RelationType]:
        """
        Batch load or create relation types.

        Optimized to avoid N+1 queries by:
        1. Loading all existing types in one query
        2. Creating missing types in batch

        Args:
            slugs: List of relation type slugs

        Returns:
            Dict mapping slug to RelationType
        """
        if not slugs:
            return {}

        # Load all existing relation types in one query
        result = await self.session.execute(
            select(RelationType).where(RelationType.slug.in_(slugs))
        )
        relation_types = {rt.slug: rt for rt in result.scalars().all()}

        # Create missing relation types
        new_types_created = False
        for slug in slugs:
            if slug not in relation_types:
                new_rt = RelationType(
                    slug=slug,
                    name=slug.replace("_", " ").title(),
                    name_reverse=f"reverse of {slug}".title(),
                )
                self.session.add(new_rt)
                relation_types[slug] = new_rt
                new_types_created = True

        # Flush to get IDs for newly created types
        if new_types_created:
            await self.session.flush()

        return relation_types

    async def _batch_find_existing_relations(
        self, potential_relations: List[Dict[str, Any]]
    ) -> set:
        """
        Batch check for existing relations.

        Optimized to avoid N+1 queries by checking all relations in one query.

        Args:
            potential_relations: List of dicts with from_entity, to_entity, relation_type

        Returns:
            Set of (source_id, target_id, relation_type_id) tuples for existing relations
        """
        if not potential_relations:
            return set()

        # Build list of (source, target) tuples for query
        source_target_pairs = [
            (rel["from_entity"].id, rel["to_entity"].id)
            for rel in potential_relations
        ]

        # Get unique source and target IDs
        source_ids = list({pair[0] for pair in source_target_pairs})
        target_ids = list({pair[1] for pair in source_target_pairs})

        # Query all potentially matching relations in one query
        result = await self.session.execute(
            select(EntityRelation).where(
                EntityRelation.source_entity_id.in_(source_ids),
                EntityRelation.target_entity_id.in_(target_ids),
            )
        )

        # Build set of existing relation keys
        existing_set = set()
        for rel in result.scalars().all():
            existing_set.add((
                rel.source_entity_id,
                rel.target_entity_id,
                rel.relation_type_id,
            ))

        return existing_set

    def _get_default_prompt(self) -> str:
        """Get default extraction prompt."""
        return """
Extrahiere relevante Informationen aus dem Text.

Antworte im JSON-Format:
{
  "entities": {},
  "relations": []
}
"""

    async def get_category_entity_types(
        self, category_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """
        Get all entity types for a category with their configuration.

        Returns list of dicts with entity type info and extraction config.
        """
        result = await self.session.execute(
            select(CategoryEntityType)
            .where(CategoryEntityType.category_id == category_id)
            .options(selectinload(CategoryEntityType.entity_type))
            .order_by(CategoryEntityType.extraction_order)
        )

        entity_types = []
        for assoc in result.scalars().all():
            entity_types.append({
                "id": str(assoc.entity_type.id),
                "slug": assoc.entity_type.slug,
                "name": assoc.entity_type.name,
                "is_primary": assoc.is_primary,
                "extraction_order": assoc.extraction_order,
                "extraction_config": assoc.extraction_config,
                "relation_config": assoc.relation_config,
            })

        return entity_types

    async def add_entity_type_to_category(
        self,
        category_id: uuid.UUID,
        entity_type_id: uuid.UUID,
        is_primary: bool = False,
        extraction_order: int = 0,
        extraction_config: Optional[Dict[str, Any]] = None,
        relation_config: Optional[List[Dict[str, Any]]] = None,
    ) -> CategoryEntityType:
        """
        Add an entity type to a category.

        Args:
            category_id: Category UUID
            entity_type_id: EntityType UUID
            is_primary: Whether this is the primary entity type
            extraction_order: Order for extraction (lower = first)
            extraction_config: Custom extraction configuration
            relation_config: Relation definitions

        Returns:
            Created CategoryEntityType association
        """
        # If setting as primary, unset any existing primary
        if is_primary:
            # Single query to find and update existing primaries (fixed duplicate query bug)
            result = await self.session.execute(
                select(CategoryEntityType).where(
                    CategoryEntityType.category_id == category_id,
                    CategoryEntityType.is_primary == True,
                )
            )
            for existing in result.scalars().all():
                existing.is_primary = False

        association = CategoryEntityType(
            category_id=category_id,
            entity_type_id=entity_type_id,
            is_primary=is_primary,
            extraction_order=extraction_order,
            extraction_config=extraction_config or {},
            relation_config=relation_config or [],
        )
        self.session.add(association)
        await self.session.flush()

        return association

    async def remove_entity_type_from_category(
        self,
        category_id: uuid.UUID,
        entity_type_id: uuid.UUID,
    ) -> bool:
        """Remove an entity type from a category."""
        result = await self.session.execute(
            select(CategoryEntityType).where(
                CategoryEntityType.category_id == category_id,
                CategoryEntityType.entity_type_id == entity_type_id,
            )
        )
        association = result.scalar_one_or_none()

        if association:
            await self.session.delete(association)
            await self.session.flush()
            return True

        return False
