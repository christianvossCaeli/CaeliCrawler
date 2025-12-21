"""
Centralized Entity Matching Service.

This service provides consistent entity creation and matching across all
import paths (Crawling, Smart Query, REST API, API Import).

IMPORTANT: All entity creation MUST go through this service to ensure:
1. Consistent name normalization
2. Race-condition-safe creation (UPSERT pattern)
3. Optional similarity matching for fuzzy deduplication
4. Proper external_id handling

Usage:
    service = EntityMatchingService(session)
    entity = await service.get_or_create_entity(
        entity_type_slug="municipality",
        name="München",
        country="DE",
    )
"""

import uuid
from typing import Any, Dict, List, Optional, Tuple

import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Entity, EntityType
from app.utils.text import normalize_entity_name, create_slug

logger = structlog.get_logger()


class EntityMatchingService:
    """
    Centralized service for consistent entity creation and matching.

    Provides:
    - Consistent name normalization across all creation paths
    - Race-condition-safe entity creation via UPSERT pattern
    - Optional similarity matching for fuzzy deduplication
    - External ID-based matching for API imports
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self._entity_type_cache: Dict[str, EntityType] = {}

    async def get_or_create_entity(
        self,
        entity_type_slug: str,
        name: str,
        country: str = "DE",
        external_id: Optional[str] = None,
        core_attributes: Optional[Dict[str, Any]] = None,
        parent_id: Optional[uuid.UUID] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        admin_level_1: Optional[str] = None,
        admin_level_2: Optional[str] = None,
        similarity_threshold: float = 1.0,
        created_by_id: Optional[uuid.UUID] = None,
        owner_id: Optional[uuid.UUID] = None,
    ) -> Optional[Entity]:
        """
        Get or create an entity with consistent matching.

        Matching order:
        1. external_id (if provided) - exact match
        2. name_normalized + entity_type - exact match
        3. similarity matching (if threshold < 1.0) - fuzzy match
        4. Create new entity if not found

        The creation is race-condition-safe using IntegrityError handling
        combined with the unique constraint on (entity_type_id, name_normalized).

        Args:
            entity_type_slug: The entity type slug (e.g., "municipality", "person")
            name: The entity name
            country: ISO 3166-1 alpha-2 country code (default: "DE")
            external_id: Optional external ID for API imports
            core_attributes: Optional JSON attributes
            parent_id: Optional parent entity ID for hierarchies
            latitude: Optional latitude for geo-entities
            longitude: Optional longitude for geo-entities
            admin_level_1: Optional admin level 1 (e.g., Bundesland)
            admin_level_2: Optional admin level 2 (e.g., Landkreis)
            similarity_threshold: Threshold for fuzzy matching (1.0 = exact only)
            created_by_id: Optional user ID who created this entity
            owner_id: Optional owner user ID

        Returns:
            Entity if found or created, None if entity_type not found
        """
        # 1. Get entity type
        entity_type = await self._get_entity_type(entity_type_slug)
        if not entity_type:
            logger.warning("Entity type not found", slug=entity_type_slug)
            return None

        # 2. Normalize name consistently
        name_normalized = normalize_entity_name(name, country=country)
        slug = create_slug(name, country=country)

        # 3. Try external_id match first (if provided)
        if external_id:
            entity = await self._find_by_external_id(entity_type.id, external_id)
            if entity:
                logger.debug(
                    "Found entity by external_id",
                    entity_id=str(entity.id),
                    external_id=external_id,
                )
                return entity

        # 4. Try exact normalized name match
        entity = await self._find_by_normalized_name(entity_type.id, name_normalized)
        if entity:
            logger.debug(
                "Found entity by normalized name",
                entity_id=str(entity.id),
                name=name,
                name_normalized=name_normalized,
            )
            return entity

        # 5. Try similarity match (if threshold < 1.0)
        if similarity_threshold < 1.0:
            similar_entity = await self._find_similar_entity(
                entity_type.id, name, similarity_threshold
            )
            if similar_entity:
                logger.info(
                    "Found similar entity",
                    entity_id=str(similar_entity.id),
                    search_name=name,
                    matched_name=similar_entity.name,
                )
                return similar_entity

        # 6. Create new entity (race-condition-safe)
        return await self._create_entity_safe(
            entity_type=entity_type,
            name=name,
            name_normalized=name_normalized,
            slug=slug,
            country=country,
            external_id=external_id,
            core_attributes=core_attributes or {},
            parent_id=parent_id,
            latitude=latitude,
            longitude=longitude,
            admin_level_1=admin_level_1,
            admin_level_2=admin_level_2,
            created_by_id=created_by_id,
            owner_id=owner_id,
        )

    async def batch_get_or_create_entities(
        self,
        entity_type_slug: str,
        names: List[str],
        country: str = "DE",
    ) -> Dict[str, Entity]:
        """
        Batch get or create entities for multiple names.

        Optimized to avoid N+1 queries by:
        1. Batch loading all existing entities by normalized names
        2. Creating only missing entities

        Args:
            entity_type_slug: The entity type slug
            names: List of entity names
            country: Country code for normalization

        Returns:
            Dict mapping original name to Entity
        """
        if not names:
            return {}

        entity_type = await self._get_entity_type(entity_type_slug)
        if not entity_type:
            return {}

        # Build normalized name mapping
        name_to_normalized: Dict[str, str] = {}
        normalized_to_names: Dict[str, List[str]] = {}

        for name in names:
            normalized = normalize_entity_name(name, country=country)
            name_to_normalized[name] = normalized
            if normalized not in normalized_to_names:
                normalized_to_names[normalized] = []
            normalized_to_names[normalized].append(name)

        # Batch query existing entities
        unique_normalized = list(normalized_to_names.keys())
        existing_entities: Dict[str, Entity] = {}

        # Query in chunks to avoid SQL IN clause overflow
        chunk_size = 100
        for i in range(0, len(unique_normalized), chunk_size):
            chunk = unique_normalized[i : i + chunk_size]
            result = await self.session.execute(
                select(Entity).where(
                    Entity.entity_type_id == entity_type.id,
                    Entity.name_normalized.in_(chunk),
                    Entity.is_active.is_(True),
                )
            )
            for entity in result.scalars().all():
                existing_entities[entity.name_normalized] = entity

        # Build result mapping
        result: Dict[str, Entity] = {}

        for name in names:
            normalized = name_to_normalized[name]

            if normalized in existing_entities:
                result[name] = existing_entities[normalized]
            else:
                # Create new entity
                entity = await self._create_entity_safe(
                    entity_type=entity_type,
                    name=name,
                    name_normalized=normalized,
                    slug=create_slug(name, country=country),
                    country=country,
                    core_attributes={},
                )
                if entity:
                    result[name] = entity
                    existing_entities[normalized] = entity  # Cache for later

        return result

    async def _get_entity_type(self, slug: str) -> Optional[EntityType]:
        """Get entity type by slug with caching."""
        if slug in self._entity_type_cache:
            return self._entity_type_cache[slug]

        result = await self.session.execute(
            select(EntityType).where(EntityType.slug == slug)
        )
        entity_type = result.scalar_one_or_none()

        if entity_type:
            self._entity_type_cache[slug] = entity_type

        return entity_type

    async def _find_by_external_id(
        self, entity_type_id: uuid.UUID, external_id: str
    ) -> Optional[Entity]:
        """Find entity by external ID."""
        result = await self.session.execute(
            select(Entity).where(
                Entity.entity_type_id == entity_type_id,
                Entity.external_id == external_id,
                Entity.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def _find_by_normalized_name(
        self, entity_type_id: uuid.UUID, name_normalized: str
    ) -> Optional[Entity]:
        """Find entity by normalized name."""
        result = await self.session.execute(
            select(Entity).where(
                Entity.entity_type_id == entity_type_id,
                Entity.name_normalized == name_normalized,
                Entity.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def _find_similar_entity(
        self, entity_type_id: uuid.UUID, name: str, threshold: float
    ) -> Optional[Entity]:
        """Find entity with similar name using fuzzy matching."""
        try:
            from app.utils.similarity import find_similar_entities

            matches = await find_similar_entities(
                self.session, entity_type_id, name, threshold
            )
            if matches:
                return matches[0][0]  # Return best match
        except ImportError:
            logger.warning("Similarity module not available")
        return None

    async def _create_entity_safe(
        self,
        entity_type: EntityType,
        name: str,
        name_normalized: str,
        slug: str,
        country: str = "DE",
        external_id: Optional[str] = None,
        core_attributes: Optional[Dict[str, Any]] = None,
        parent_id: Optional[uuid.UUID] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        admin_level_1: Optional[str] = None,
        admin_level_2: Optional[str] = None,
        created_by_id: Optional[uuid.UUID] = None,
        owner_id: Optional[uuid.UUID] = None,
    ) -> Optional[Entity]:
        """
        Create entity with race-condition safety.

        Uses IntegrityError handling to catch concurrent creation attempts.
        If a concurrent creation is detected, fetches the existing entity.
        """
        # Build hierarchy path
        hierarchy_path = f"/{slug}"
        hierarchy_level = 0

        if parent_id:
            parent = await self.session.get(Entity, parent_id)
            if parent:
                hierarchy_path = f"{parent.hierarchy_path}/{slug}"
                hierarchy_level = parent.hierarchy_level + 1

        entity = Entity(
            entity_type_id=entity_type.id,
            name=name,
            name_normalized=name_normalized,
            slug=slug,
            external_id=external_id,
            parent_id=parent_id,
            hierarchy_path=hierarchy_path,
            hierarchy_level=hierarchy_level,
            country=country.upper() if country else None,
            admin_level_1=admin_level_1,
            admin_level_2=admin_level_2,
            core_attributes=core_attributes or {},
            latitude=latitude,
            longitude=longitude,
            is_active=True,
            created_by_id=created_by_id,
            owner_id=owner_id,
        )

        self.session.add(entity)

        try:
            await self.session.flush()
            logger.info(
                "Created new entity",
                entity_id=str(entity.id),
                name=name,
                entity_type=entity_type.slug,
            )
            return entity
        except IntegrityError as e:
            # Concurrent creation detected - fetch existing entity
            if "uq_entity_type_name_normalized" in str(e):
                await self.session.rollback()
                logger.info(
                    "Concurrent entity creation detected, fetching existing",
                    name=name,
                    name_normalized=name_normalized,
                )
                return await self._find_by_normalized_name(
                    entity_type.id, name_normalized
                )
            # Re-raise other integrity errors
            raise
