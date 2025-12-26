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
        entity_type_slug="territorial_entity",
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



import re
from dataclasses import dataclass


@dataclass
class CompositeEntityMatch:
    """Result of detecting a composite entity name."""
    is_composite: bool
    pattern_type: str  # e.g., "gemeinden_und", "region_gemeinde"
    extracted_names: List[str]
    original_name: str


# Patterns for detecting composite entity names that should not be created
COMPOSITE_ENTITY_PATTERNS = [
    # "Gemeinden X und Y" - multiple municipalities
    (
        r"(?:Gemeinden?|Städte|Märkte)\s+(.+?)\s+und\s+(.+?)(?:,|$)",
        "gemeinden_und",
    ),
    # "Region X, Gemeinde Y" or "Region X, Stadt Y" or "Region X, Markt Y"
    (
        r"Region\s+[^,]+,\s+(?:Gemeinde|Stadt|Markt)\s+([^,]+?)(?:,|$)",
        "region_gemeinde",
    ),
    # "Region X, insbesondere Gemeinde Y"
    (
        r"(?:insbesondere|speziell|vor allem)\s+(?:Gemeinde|Stadt|Markt)?\s*([^,]+?)(?:,|$)",
        "insbesondere",
    ),
]


def detect_composite_entity_name(name: str) -> CompositeEntityMatch:
    """
    Detect if an entity name is a composite that should be split into multiple entities.
    
    Examples of composite names that should not be created as single entities:
    - "Gemeinden Litzendorf und Buttenheim" → should use "Litzendorf" and "Buttenheim"
    - "Region Oberfranken-West, Gemeinde Litzendorf" → should use "Litzendorf"
    - "Region X, insbesondere Gemeinde Bad Rodach" → should use "Bad Rodach"
    
    Args:
        name: The entity name to check
        
    Returns:
        CompositeEntityMatch with detection results
    """
    # Check for "Gemeinden X und Y" pattern
    match = re.search(
        r"(?:Gemeinden?|Städte|Märkte)\s+(.+?)\s+und\s+(.+?)(?:,|\s*$)",
        name,
        re.IGNORECASE
    )
    if match:
        name1 = match.group(1).strip()
        name2 = match.group(2).strip()
        # Clean up trailing location info
        name2 = re.sub(r",?\s*(?:Landkreis|Region|Bayern|Kreis).*$", "", name2, flags=re.IGNORECASE)
        return CompositeEntityMatch(
            is_composite=True,
            pattern_type="gemeinden_und",
            extracted_names=[name1, name2],
            original_name=name,
        )
    
    # Check for "Region X, Gemeinde/Stadt/Markt Y" pattern
    match = re.search(
        r"Region\s+[^,]+,\s+(?:Gemeinde|Stadt|Markt)\s+([^,]+?)(?:,|\s*$)",
        name,
        re.IGNORECASE
    )
    if match:
        extracted = match.group(1).strip()
        # Clean up trailing location info
        extracted = re.sub(r",?\s*(?:Landkreis|Region|Bayern|Kreis).*$", "", extracted, flags=re.IGNORECASE)
        return CompositeEntityMatch(
            is_composite=True,
            pattern_type="region_gemeinde",
            extracted_names=[extracted],
            original_name=name,
        )
    
    # Check for "insbesondere Gemeinde X" pattern
    match = re.search(
        r"(?:insbesondere|speziell|vor allem)\s+(?:Gemeinde|Stadt|Markt)?\s*([^,]+?)(?:,|\s*$)",
        name,
        re.IGNORECASE
    )
    if match:
        extracted = match.group(1).strip()
        # Clean up trailing location info
        extracted = re.sub(r",?\s*(?:Landkreis|Region|Bayern|Kreis).*$", "", extracted, flags=re.IGNORECASE)
        return CompositeEntityMatch(
            is_composite=True,
            pattern_type="insbesondere",
            extracted_names=[extracted],
            original_name=name,
        )
    
    return CompositeEntityMatch(
        is_composite=False,
        pattern_type="",
        extracted_names=[],
        original_name=name,
    )


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
        4. Composite name detection - returns existing entity if found
        5. Create new entity if not found

        The creation is race-condition-safe using IntegrityError handling
        combined with the unique constraint on (entity_type_id, name_normalized).

        Args:
            entity_type_slug: The entity type slug (e.g., "territorial_entity", "person")
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
        # Note: We use embedding-based similarity for fuzzy matching,
        # so no entity-type-specific cleaning is needed here.
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

        # 5. Try embedding-based similarity match (if threshold < 1.0)
        # This uses semantic embeddings for entity-type-agnostic matching
        if similarity_threshold < 1.0:
            similar_entity = await self._find_similar_entity(
                entity_type.id, name, similarity_threshold
            )
            if similar_entity:
                logger.info(
                    "Found similar entity via embedding",
                    entity_id=str(similar_entity.id),
                    search_name=name,
                    matched_name=similar_entity.name,
                )
                return similar_entity

        # 6. Check for composite entity names (e.g., "Gemeinden X und Y")
        # If detected and component entities exist, return one of them instead
        composite = detect_composite_entity_name(name)
        if composite.is_composite:
            existing_entity = await self._resolve_composite_entity(
                entity_type.id, composite, country
            )
            if existing_entity:
                logger.info(
                    "Resolved composite entity name to existing entity",
                    composite_name=name,
                    pattern_type=composite.pattern_type,
                    extracted_names=composite.extracted_names,
                    resolved_to=existing_entity.name,
                    entity_id=str(existing_entity.id),
                )
                return existing_entity

        # 7. Create new entity (race-condition-safe, with embedding)
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

    async def get_entity_type(self, slug: str) -> Optional[EntityType]:
        """
        Get entity type by slug with caching.

        Public method for external access to entity types.

        Args:
            slug: The entity type slug

        Returns:
            EntityType if found, None otherwise
        """
        if slug in self._entity_type_cache:
            return self._entity_type_cache[slug]

        result = await self.session.execute(
            select(EntityType).where(EntityType.slug == slug)
        )
        entity_type = result.scalar_one_or_none()

        if entity_type:
            self._entity_type_cache[slug] = entity_type

        return entity_type

    # Alias for backwards compatibility
    async def _get_entity_type(self, slug: str) -> Optional[EntityType]:
        """Deprecated: Use get_entity_type instead."""
        return await self.get_entity_type(slug)

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


    async def _resolve_composite_entity(
        self,
        entity_type_id: uuid.UUID,
        composite: CompositeEntityMatch,
        country: str = "DE",
    ) -> Optional[Entity]:
        """
        Try to resolve a composite entity name to an existing entity.
        
        When a composite name like "Gemeinden Litzendorf und Buttenheim" is detected,
        this method searches for existing entities with the extracted component names
        (e.g., "Litzendorf", "Buttenheim") and returns the first match.
        
        This prevents creation of duplicate/composite entities when the individual
        entities already exist in the database.
        
        Args:
            entity_type_id: The entity type ID to search within
            composite: The composite entity detection result
            country: Country code for name normalization
            
        Returns:
            First matching existing entity, or None if no components exist
        """
        if not composite.is_composite or not composite.extracted_names:
            return None
            
        for extracted_name in composite.extracted_names:
            # Try exact match first
            name_normalized = normalize_entity_name(extracted_name, country=country)
            entity = await self._find_by_normalized_name(entity_type_id, name_normalized)
            if entity:
                return entity
            
            # Also try searching with the full extracted name (might have location suffixes)
            # e.g., "Bad Rodach" from "insbesondere Gemeinde Bad Rodach, Landkreis Coburg"
            result = await self.session.execute(
                select(Entity).where(
                    Entity.entity_type_id == entity_type_id,
                    Entity.name.ilike(f"%{extracted_name}%"),
                    Entity.is_active.is_(True),
                ).limit(1)
            )
            entity = result.scalar_one_or_none()
            if entity:
                return entity
        
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
        Create entity with race-condition safety and embedding generation.

        Uses IntegrityError handling to catch concurrent creation attempts.
        If a concurrent creation is detected, fetches the existing entity.
        Also generates and stores the name embedding for similarity matching.
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

            # Generate and store embedding for similarity matching
            await self._generate_entity_embedding(entity)

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

    async def _generate_entity_embedding(self, entity: Entity) -> None:
        """
        Generate and store embedding for an entity.

        This is called after entity creation to enable similarity matching.
        Failures are logged but don't prevent entity creation.
        """
        try:
            from app.utils.similarity import update_entity_embedding

            success = await update_entity_embedding(
                self.session,
                entity.id,
                name=entity.name,
            )
            if success:
                logger.debug(
                    "Generated embedding for new entity",
                    entity_id=str(entity.id),
                    name=entity.name,
                )
        except Exception as e:
            # Log but don't fail - embedding can be generated later
            logger.warning(
                "Failed to generate embedding for entity",
                entity_id=str(entity.id),
                name=entity.name,
                error=str(e),
            )
