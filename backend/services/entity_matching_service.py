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
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Entity, EntityType
from app.models.facet_type import FacetType
from app.utils.text import create_slug, normalize_core_entity_name, normalize_entity_name

logger = structlog.get_logger()


import re  # noqa: E402
from dataclasses import dataclass  # noqa: E402


@dataclass
class CompositeEntityMatch:
    """Result of detecting a composite entity name."""

    is_composite: bool
    pattern_type: str  # e.g., "gemeinden_und", "region_gemeinde"
    extracted_names: list[str]
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
    match = re.search(r"(?:Gemeinden?|Städte|Märkte)\s+(.+?)\s+und\s+(.+?)(?:,|\s*$)", name, re.IGNORECASE)
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
    match = re.search(r"Region\s+[^,]+,\s+(?:Gemeinde|Stadt|Markt)\s+([^,]+?)(?:,|\s*$)", name, re.IGNORECASE)
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
        r"(?:insbesondere|speziell|vor allem)\s+(?:Gemeinde|Stadt|Markt)?\s*([^,]+?)(?:,|\s*$)", name, re.IGNORECASE
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
        self._entity_type_cache: dict[str, EntityType] = {}

    # Default threshold for AI-based embedding similarity search
    # 0.85 = high confidence match (same entity, different formatting)
    DEFAULT_SIMILARITY_THRESHOLD = 0.80  # Lowered from 0.85 for stricter deduplication = 0.85

    async def get_or_create_entity(
        self,
        entity_type_slug: str,
        name: str,
        country: str = "DE",
        external_id: str | None = None,
        core_attributes: dict[str, Any] | None = None,
        parent_id: uuid.UUID | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        admin_level_1: str | None = None,
        admin_level_2: str | None = None,
        similarity_threshold: float = None,
        auto_deduplicate: bool = True,
        created_by_id: uuid.UUID | None = None,
        owner_id: uuid.UUID | None = None,
    ) -> Entity | None:
        """
        Get or create an entity with intelligent duplicate detection.

        Matching order (with auto_deduplicate=True):
        1. external_id (if provided) - exact match
        2. name_normalized + entity_type - exact match
        3. Core name match - structural patterns (parentheses, commas)
        4. AI embedding similarity - semantic matching via OpenAI embeddings
        5. Composite name detection - returns existing entity if found
        6. Cross-type exact name check - prevents duplicates across entity types
        7. Create new entity if not found

        The AI embedding search uses pgvector's cosine similarity to find
        semantically similar names, even across languages or naming conventions.
        E.g., "Windpark Nordsee" might match "North Sea Wind Farm".

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
            similarity_threshold: Threshold for AI matching (default: 0.85).
                                  Set to 1.0 to disable AI matching.
            auto_deduplicate: Enable automatic duplicate detection (default: True)
            created_by_id: Optional user ID who created this entity
            owner_id: Optional owner user ID

        Returns:
            Entity if found or created, None if entity_type not found
        """
        # Use default threshold if not specified and auto_deduplicate is enabled
        if similarity_threshold is None:
            similarity_threshold = self.DEFAULT_SIMILARITY_THRESHOLD if auto_deduplicate else 1.0

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

        # 5. Try core name match (catches "Markt X" vs "X", "X (Region Y)" vs "X")
        # This is a fast pattern-based check that runs automatically
        core_match = await self._find_by_core_name(entity_type.id, name, country, name_normalized)
        if core_match:
            entity, reason = core_match
            logger.info(
                "Found entity by core name match",
                entity_id=str(entity.id),
                search_name=name,
                matched_name=entity.name,
                reason=reason,
            )
            return entity

        # 6. Try embedding-based semantic similarity match (if threshold < 1.0)
        # This uses AI embeddings to find semantically similar names
        # E.g., "Windkraftanlage Nordsee" might match "Offshore Wind Farm North Sea"
        if similarity_threshold < 1.0:
            similar_entity = await self._find_similar_entity(entity_type.id, name, similarity_threshold)
            if similar_entity:
                logger.info(
                    "Found similar entity via embedding",
                    entity_id=str(similar_entity.id),
                    search_name=name,
                    matched_name=similar_entity.name,
                )
                return similar_entity

        # 7. Check for composite entity names (e.g., "Gemeinden X und Y")
        # If detected and component entities exist, return one of them instead
        composite = detect_composite_entity_name(name)
        if composite.is_composite:
            existing_entity = await self._resolve_composite_entity(entity_type.id, composite, country)
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

        # 8. Final safety check: Look for exact name match across ALL entity types
        # This catches cases where the same entity was created with a different type
        # (e.g., "Düsseldorf" as both city and organization)
        cross_type_match = await self._find_exact_name_any_type(name_normalized, entity_type.id)
        if cross_type_match is not None:
            if cross_type_match.entity_type_id == entity_type.id:
                # Same type - this shouldn't happen but return the match
                logger.warning(
                    "Found existing entity in final safety check (same type)",
                    search_name=name,
                    matched_name=cross_type_match.name,
                    entity_id=str(cross_type_match.id),
                )
                return cross_type_match
            else:
                # Different type - log warning but return existing to prevent duplicate
                logger.warning(
                    "Found existing entity with same name but different type",
                    search_name=name,
                    search_type=entity_type.slug,
                    matched_name=cross_type_match.name,
                    matched_type_id=str(cross_type_match.entity_type_id),
                    entity_id=str(cross_type_match.id),
                )
                # Return existing entity to prevent creating a duplicate name
                return cross_type_match

        # 9. Create new entity (race-condition-safe, with embedding)
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

    async def find_entity(
        self,
        entity_type_slug: str,
        name: str,
        country: str = "DE",
        external_id: str | None = None,
        similarity_threshold: float = None,
    ) -> Entity | None:
        """
        Find an existing entity without creating a new one.

        Matching order:
        1. external_id (if provided) - exact match
        2. name_normalized + entity_type - exact match
        3. Core name match - structural patterns
        4. AI embedding similarity - semantic matching (if threshold < 1.0)
        5. Composite name detection - find component entities

        Args:
            entity_type_slug: The entity type slug
            name: Entity name to search for
            country: Country code for normalization (default: DE)
            external_id: Optional external ID for API imports
            similarity_threshold: Threshold for AI matching (default: 0.85).
                                  Set to 1.0 to disable AI matching.

        Returns:
            Entity if found, None otherwise
        """
        if similarity_threshold is None:
            similarity_threshold = self.DEFAULT_SIMILARITY_THRESHOLD

        # 1. Get entity type
        entity_type = await self._get_entity_type(entity_type_slug)
        if not entity_type:
            logger.debug("Entity type not found", slug=entity_type_slug)
            return None

        # 2. Normalize name
        name_normalized = normalize_entity_name(name, country=country)

        # 3. Try external_id match first (if provided)
        if external_id:
            entity = await self._find_by_external_id(entity_type.id, external_id)
            if entity:
                return entity

        # 4. Try exact normalized name match
        entity = await self._find_by_normalized_name(entity_type.id, name_normalized)
        if entity:
            return entity

        # 5. Try core name match
        core_match = await self._find_by_core_name(entity_type.id, name, country, name_normalized)
        if core_match:
            entity, _reason = core_match
            return entity

        # 6. Try embedding-based semantic similarity match (if threshold < 1.0)
        if similarity_threshold < 1.0:
            similar_entity = await self._find_similar_entity(entity_type.id, name, similarity_threshold)
            if similar_entity:
                return similar_entity

        # 7. Check for composite entity names
        composite = detect_composite_entity_name(name)
        if composite.is_composite:
            existing_entity = await self._resolve_composite_entity(entity_type.id, composite, country)
            if existing_entity:
                return existing_entity

        return None

    async def batch_get_or_create_entities(
        self,
        entity_type_slug: str,
        names: list[str],
        country: str = "DE",
    ) -> dict[str, Entity]:
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
        name_to_normalized: dict[str, str] = {}
        normalized_to_names: dict[str, list[str]] = {}

        for name in names:
            normalized = normalize_entity_name(name, country=country)
            name_to_normalized[name] = normalized
            if normalized not in normalized_to_names:
                normalized_to_names[normalized] = []
            normalized_to_names[normalized].append(name)

        # Batch query existing entities
        unique_normalized = list(normalized_to_names.keys())
        existing_entities: dict[str, Entity] = {}

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
        result: dict[str, Entity] = {}

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

    async def get_entity_type(self, slug: str) -> EntityType | None:
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

        result = await self.session.execute(select(EntityType).where(EntityType.slug == slug))
        entity_type = result.scalar_one_or_none()

        if entity_type:
            self._entity_type_cache[slug] = entity_type

        return entity_type

    # Alias for backwards compatibility
    async def _get_entity_type(self, slug: str) -> EntityType | None:
        """Deprecated: Use get_entity_type instead."""
        return await self.get_entity_type(slug)

    async def _find_by_external_id(self, entity_type_id: uuid.UUID, external_id: str) -> Entity | None:
        """Find entity by external ID."""
        result = await self.session.execute(
            select(Entity).where(
                Entity.entity_type_id == entity_type_id,
                Entity.external_id == external_id,
                Entity.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def _find_by_normalized_name(self, entity_type_id: uuid.UUID, name_normalized: str) -> Entity | None:
        """Find entity by normalized name."""
        result = await self.session.execute(
            select(Entity).where(
                Entity.entity_type_id == entity_type_id,
                Entity.name_normalized == name_normalized,
                Entity.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def _find_exact_name_any_type(
        self,
        name_normalized: str,
        preferred_entity_type_id: uuid.UUID | None = None,
    ) -> Entity | None:
        """
        Find entity by exact normalized name across ALL entity types.

        This is a safety check to prevent creating duplicates when the same
        entity name exists but was categorized under a different type.
        For example, "Düsseldorf" might exist as both a city and an organization.

        Args:
            name_normalized: The normalized entity name to search for
            preferred_entity_type_id: If provided, prefer entities of this type

        Returns:
            Existing entity if found, None otherwise
        """
        # First try to find in preferred entity type
        if preferred_entity_type_id:
            result = await self.session.execute(
                select(Entity).where(
                    Entity.entity_type_id == preferred_entity_type_id,
                    Entity.name_normalized == name_normalized,
                    Entity.is_active.is_(True),
                )
            )
            entity = result.scalar_one_or_none()
            if entity:
                return entity

        # Then search across all entity types
        result = await self.session.execute(
            select(Entity)
            .where(
                Entity.name_normalized == name_normalized,
                Entity.is_active.is_(True),
            )
            .order_by(Entity.created_at.asc())  # Prefer older entities
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _find_by_core_name(
        self,
        entity_type_id: uuid.UUID,
        name: str,
        country: str = "DE",
        name_normalized: str = None,
    ) -> tuple[Entity, str] | None:
        """
        Find entity by normalized core name.

        This helps detect duplicates where entities have different administrative
        prefixes or suffixes but the same core name, such as:
        - "Markt Erlbach" vs "Erlbach"
        - "Region Oberfranken-West" vs "Oberfranken-West (Region 4), Bayern"
        - "Acme Corp (US Division)" vs "Acme Corp"

        Uses an efficient two-step approach:
        1. Quick filter using LIKE on normalized name (substring match)
        2. Precise match using normalized core name comparison

        Args:
            entity_type_id: The entity type UUID
            name: The entity name to search for
            country: Country code for normalization
            name_normalized: Pre-computed normalized name (optional)

        Returns:
            Tuple of (Entity, match_reason) if found, None otherwise
        """
        from app.utils.text import extract_core_entity_name

        core_name = extract_core_entity_name(name, country=country)
        core_normalized = normalize_core_entity_name(name, country=country)

        # Skip if core name is too short (likely not meaningful)
        if len(core_normalized) < 4:
            return None

        # Note: We intentionally do NOT skip when core_normalized == name_normalized.
        # Even if the search term has no parenthetical content (e.g., "Regionalverband Ruhr"),
        # we still want to find entities with parentheses (e.g., "Regionalverband Ruhr (RVR)")
        # that share the same core name.

        # Efficient query: Use LIKE with the core_normalized as substring
        # This leverages indexes and reduces the result set
        result = await self.session.execute(
            select(Entity)
            .where(
                Entity.entity_type_id == entity_type_id,
                Entity.is_active.is_(True),
                Entity.name_normalized.contains(core_normalized),
            )
            .limit(50)  # Reasonable limit for performance
        )
        candidates = result.scalars().all()

        for entity in candidates:
            existing_core = normalize_core_entity_name(entity.name, country=country)
            if existing_core == core_normalized:
                # Skip if it's an exact name match (already handled by _find_by_normalized_name)
                if entity.name_normalized == (name_normalized or normalize_entity_name(name, country)):
                    continue
                logger.info(
                    "Found duplicate by core name",
                    search_name=name,
                    search_core=core_name,
                    matched_name=entity.name,
                    entity_id=str(entity.id),
                )
                return (
                    entity,
                    f"Core name match: '{entity.name}' has same core '{core_name}' as '{name}'",
                )

        return None

    async def _find_similar_entity(self, entity_type_id: uuid.UUID, name: str, threshold: float) -> Entity | None:
        """Find entity with similar name using fuzzy matching."""
        try:
            from app.utils.similarity import find_similar_entities

            matches = await find_similar_entities(self.session, entity_type_id, name, threshold)
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
    ) -> Entity | None:
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
            # Escape SQL wildcards to prevent injection
            safe_name = extracted_name.replace("%", "\\%").replace("_", "\\_")
            result = await self.session.execute(
                select(Entity)
                .where(
                    Entity.entity_type_id == entity_type_id,
                    Entity.name.ilike(f"%{safe_name}%", escape="\\"),
                    Entity.is_active.is_(True),
                )
                .limit(1)
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
        external_id: str | None = None,
        core_attributes: dict[str, Any] | None = None,
        parent_id: uuid.UUID | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        admin_level_1: str | None = None,
        admin_level_2: str | None = None,
        created_by_id: uuid.UUID | None = None,
        owner_id: uuid.UUID | None = None,
    ) -> Entity | None:
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
                return await self._find_by_normalized_name(entity_type.id, name_normalized)
            # Re-raise other integrity errors
            raise

    async def _generate_entity_embedding(self, entity: Entity, max_retries: int = 3) -> None:
        """
        Generate and store embedding for an entity with retry logic.

        This is called after entity creation to enable similarity matching.
        Failures are logged but don't prevent entity creation.

        Uses exponential backoff to handle transient API failures:
        - Attempt 1: immediate
        - Attempt 2: after 1 second
        - Attempt 3: after 2 seconds

        Args:
            entity: The entity to generate embedding for
            max_retries: Maximum number of retry attempts (default: 3)
        """
        import asyncio

        from app.utils.similarity import update_entity_embedding

        for attempt in range(1, max_retries + 1):
            try:
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
                        attempt=attempt,
                    )
                    return
                else:
                    logger.warning(
                        "Embedding generation returned False",
                        entity_id=str(entity.id),
                        name=entity.name,
                        attempt=attempt,
                    )
            except Exception as e:
                if attempt < max_retries:
                    wait_time = attempt  # Exponential backoff: 1s, 2s
                    logger.warning(
                        "Embedding generation failed, retrying",
                        entity_id=str(entity.id),
                        name=entity.name,
                        error=str(e),
                        attempt=attempt,
                        max_retries=max_retries,
                        retry_in_seconds=wait_time,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    # Final attempt failed - log error but don't fail entity creation
                    logger.error(
                        "Failed to generate embedding after all retries",
                        entity_id=str(entity.id),
                        name=entity.name,
                        error=str(e),
                        attempts=max_retries,
                    )

    # =========================================================================
    # FACET-TO-ENTITY REFERENCE METHODS
    # =========================================================================

    async def resolve_target_entity_for_facet(
        self,
        facet_type: FacetType,
        facet_value_data: dict[str, Any],
        source_entity_id: uuid.UUID | None = None,
    ) -> uuid.UUID | None:
        """
        Resolve or create a target entity for a facet value.

        This is the main entry point for linking facet values to entities.
        For example, a "contact" facet can be linked to a "person" entity.

        Args:
            facet_type: The FacetType configuration
            facet_value_data: The facet value's structured data (e.g., {name: "Max", role: "CEO"})
            source_entity_id: The entity this facet belongs to (for context/logging)

        Returns:
            target_entity_id if matched/created, None otherwise

        Example:
            >>> service = EntityMatchingService(session)
            >>> target_id = await service.resolve_target_entity_for_facet(
            ...     facet_type=contact_facet_type,
            ...     facet_value_data={"name": "Max Mustermann", "role": "Bürgermeister"},
            ... )
        """
        if not facet_type.allows_entity_reference:
            return None

        # Extract name from facet value data
        name = self._extract_name_from_facet_value(facet_value_data)
        if not name:
            logger.debug(
                "No name found in facet value data",
                facet_type=facet_type.slug,
                value_keys=list(facet_value_data.keys()),
            )
            return None

        # Determine entity type to search/create
        target_entity_type_slugs = facet_type.target_entity_type_slugs or []

        # Classify the name to determine if it's a person or organization
        entity_type_slug = self._classify_entity_type(name, facet_value_data, target_entity_type_slugs)

        if not entity_type_slug:
            logger.debug(
                "Could not determine entity type for facet value",
                facet_type=facet_type.slug,
                name=name,
            )
            return None

        # Extract additional attributes for matching
        core_attributes = self._extract_core_attributes_from_facet(facet_value_data)

        # Use existing get_or_create_entity method
        entity = await self.get_or_create_entity(
            entity_type_slug=entity_type_slug,
            name=name,
            core_attributes=core_attributes,
            auto_deduplicate=True,
            # Only create if auto_create_entity is enabled
            similarity_threshold=0.85 if facet_type.auto_create_entity else 1.0,
        )

        if entity:
            logger.info(
                "Resolved target entity for facet",
                facet_type=facet_type.slug,
                entity_id=str(entity.id),
                entity_name=entity.name,
                source_entity_id=str(source_entity_id) if source_entity_id else None,
            )
            return entity.id

        # If we didn't find/create an entity and auto_create is enabled,
        # create a new entity explicitly
        if facet_type.auto_create_entity:
            entity_type = await self.get_entity_type(entity_type_slug)
            if entity_type:
                entity = await self._create_entity_safe(
                    entity_type=entity_type,
                    name=name,
                    name_normalized=normalize_entity_name(name),
                    slug=create_slug(name),
                    core_attributes=core_attributes,
                )
                if entity:
                    logger.info(
                        "Created new entity from facet value",
                        facet_type=facet_type.slug,
                        entity_id=str(entity.id),
                        entity_name=entity.name,
                        entity_type=entity_type_slug,
                    )
                    return entity.id

        return None

    def _extract_name_from_facet_value(self, value: dict[str, Any]) -> str | None:
        """
        Extract entity name from facet value data.

        Supports common contact/person/organization data structures.
        """
        # Try direct name fields
        for field in ["name", "full_name", "display_name", "title", "organisation", "organization", "company", "firma"]:
            if field in value and value[field]:
                return str(value[field]).strip()

        # Try combining first/last name (for persons)
        first_name = value.get("first_name", "") or value.get("vorname", "") or value.get("given_name", "")
        last_name = value.get("last_name", "") or value.get("nachname", "") or value.get("family_name", "")
        if first_name or last_name:
            full_name = f"{first_name} {last_name}".strip()
            if full_name:
                return full_name

        # Try role-based name (e.g., "Bürgermeister")
        role = value.get("role", "") or value.get("position", "") or value.get("funktion", "")
        if role:
            return str(role).strip()

        return None

    def _classify_entity_type(self, name: str, value: dict[str, Any], allowed_types: list[str]) -> str | None:
        """
        Classify whether a name/value represents a person or organization.

        Uses heuristics to determine entity type:
        - Names with typical person patterns (first+last name) → person
        - Names with organization patterns (GmbH, AG, e.V., etc.) → organization
        - Roles/positions → organization (usually refers to a department)
        """
        import re

        name_lower = name.lower()

        # Check for organization indicators (comprehensive list)
        org_patterns = [
            "gmbh",
            "ag",
            "e.v.",
            "ev",
            "verein",
            "verband",
            "gesellschaft",
            "behörde",
            "amt",
            "ministerium",
            "direktion",
            "abteilung",
            "regierung",
            "verwaltung",
            "bundesland",
            "kreis",
            "landkreis",
            "stadt",
            "gemeinde",
            "kommune",
            "region",
            "bezirk",
            "universität",
            "hochschule",
            "institut",
            "stiftung",
            "zuständig",
            "planungsbehörde",
            "regionalverband",
            # Additional patterns
            "planungsverband",
            "landesamt",
            "landtag",
            "landesregierung",
            "landesplanungsbehörde",
            "verbandsversammlung",
            "genehmigungsdirektion",
            "regionaldirektion",
            "planungsausschuss",
            "bezirksregierung",
            "regierungsbezirk",
            "fachkommission",
            "bundesamt",
            "sekretariat",
            "ausschuss",
            "kommission",
            "träger",
        ]

        for pattern in org_patterns:
            if pattern in name_lower:
                if "organization" in allowed_types:
                    return "organization"
                elif allowed_types:
                    return allowed_types[0]

        # Check for person name patterns first (titles, hyphenated names, etc.)
        person_patterns = [
            # Title + Name (Dr., Prof., Dipl.-Geogr., Dr.-Ing.)
            r"^(dr\.?\-?ing\.?|dr\.|prof\.|dipl\.?\-?\w*\.?)\s",
            # Two words starting with capital letters (including hyphens in names)
            r"^[A-ZÄÖÜ][a-zäöüß]+[\-]?[A-ZÄÖÜ]?[a-zäöüß]*\s+[A-ZÄÖÜ][a-zäöüß\-]+$",
            # Three words with nobility particles
            r"^[A-ZÄÖÜ][a-zäöüß]+\s+(von|van|de|zu|vom)\s+[A-ZÄÖÜ]",
        ]

        for pattern in person_patterns:
            if re.search(pattern, name, re.IGNORECASE):
                if "person" in allowed_types:
                    return "person"
                elif allowed_types:
                    return allowed_types[0]

        # Check if it looks like a person name (2-4 words, capitalized)
        words = name.split()
        if len(words) >= 2 and len(words) <= 4:
            # Allow hyphenated names and umlauts
            def is_name_word(word: str) -> bool:
                # Remove common titles
                word = re.sub(r"^(dr|prof|dipl|ing|herr|frau)\.?\-?", "", word, flags=re.IGNORECASE)
                if not word:
                    return True
                # Check if word starts with uppercase and contains only letters/hyphens
                return bool(re.match(r"^[A-ZÄÖÜ][a-zäöüß\-]*$", word))

            looks_like_person = all(is_name_word(w) for w in words if w)
            if looks_like_person:
                if "person" in allowed_types:
                    return "person"
                elif allowed_types:
                    return allowed_types[0]

        # Check for explicit type hints in the value
        entity_type_hint = value.get("entity_type") or value.get("type")
        if entity_type_hint:
            hint_lower = str(entity_type_hint).lower()
            if "person" in hint_lower and "person" in allowed_types:
                return "person"
            if "org" in hint_lower and "organization" in allowed_types:
                return "organization"

        # Default to first allowed type
        return allowed_types[0] if allowed_types else None

    def _extract_core_attributes_from_facet(self, value: dict[str, Any]) -> dict[str, Any]:
        """
        Extract core attributes from facet value for entity creation.

        These attributes are stored in entity.core_attributes for matching
        and display purposes.
        """
        attrs = {}

        # Email
        email = value.get("email") or value.get("e_mail") or value.get("mail")
        if email:
            attrs["email"] = str(email).lower().strip()

        # Phone
        phone = value.get("phone") or value.get("telefon") or value.get("tel")
        if phone:
            attrs["phone"] = str(phone).strip()

        # Role/Position
        role = value.get("role") or value.get("position") or value.get("funktion")
        if role:
            attrs["role"] = str(role).strip()

        # Department
        department = value.get("department") or value.get("abteilung")
        if department:
            attrs["department"] = str(department).strip()

        # Website
        website = value.get("website") or value.get("url") or value.get("homepage")
        if website:
            attrs["website"] = str(website).strip()

        return attrs

    async def batch_resolve_target_entities(
        self,
        facet_type: FacetType,
        facet_values: list[dict[str, Any]],
    ) -> dict[int, uuid.UUID | None]:
        """
        Batch resolve target entities for multiple facet values.

        Optimized for bulk processing with deduplication.

        Args:
            facet_type: The FacetType configuration
            facet_values: List of facet value data dicts

        Returns:
            Dict mapping index to target_entity_id (or None)
        """
        if not facet_type.allows_entity_reference:
            return dict.fromkeys(range(len(facet_values)))

        results: dict[int, uuid.UUID | None] = {}
        name_to_entity: dict[str, uuid.UUID] = {}

        for i, value in enumerate(facet_values):
            name = self._extract_name_from_facet_value(value)
            if not name:
                results[i] = None
                continue

            # Check cache first
            name_normalized = normalize_entity_name(name)
            if name_normalized in name_to_entity:
                results[i] = name_to_entity[name_normalized]
                continue

            # Resolve entity
            entity_id = await self.resolve_target_entity_for_facet(
                facet_type=facet_type,
                facet_value_data=value,
            )
            results[i] = entity_id
            if entity_id:
                name_to_entity[name_normalized] = entity_id

        return results
