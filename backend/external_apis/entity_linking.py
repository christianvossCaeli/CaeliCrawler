"""AI-powered entity linking service.

This service provides intelligent entity linking capabilities:
- Fuzzy matching of location names to municipality entities
- AI interpretation of ambiguous location hints
- Relationship creation between entities
"""

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Entity, EntityRelation, EntityType, RelationType
from services.entity_facet_service import (
    create_relation,
    get_relation_type_by_slug,
    normalize_name,
)

logger = structlog.get_logger(__name__)


class EntityLinkingService:
    """Service for linking external API records to existing entities.

    This service uses a combination of:
    1. Exact name matching
    2. Normalized name matching (case-insensitive, special char removal)
    3. AI-powered interpretation for ambiguous cases

    The AI interpretation is particularly useful for:
    - Extracting municipality names from complex address strings
    - Handling regional/colloquial name variations
    - Disambiguating between similarly named places
    """

    def __init__(self, session: AsyncSession, use_ai: bool = True):
        """Initialize the entity linking service.

        Args:
            session: Database session.
            use_ai: Whether to use AI for ambiguous cases. Default True.
        """
        self.session = session
        self.use_ai = use_ai
        self._ai_service = None
        self._entity_type_cache: dict[str, EntityType] = {}
        self._relation_type_cache: dict[str, RelationType] = {}

    async def _get_ai_service(self):
        """Lazily initialize AI service."""
        if self._ai_service is None:
            from services.ai_service import get_ai_service

            self._ai_service = get_ai_service()
        return self._ai_service

    async def _get_entity_type(self, slug: str) -> EntityType | None:
        """Get entity type by slug with caching."""
        if slug not in self._entity_type_cache:
            result = await self.session.execute(
                select(EntityType).where(
                    EntityType.slug == slug,
                    EntityType.is_active.is_(True),
                )
            )
            entity_type = result.scalar_one_or_none()
            if entity_type:
                self._entity_type_cache[slug] = entity_type
        return self._entity_type_cache.get(slug)

    async def _get_relation_type(self, slug: str) -> RelationType | None:
        """Get relation type by slug with caching."""
        if slug not in self._relation_type_cache:
            relation_type = await get_relation_type_by_slug(self.session, slug)
            if relation_type:
                self._relation_type_cache[slug] = relation_type
        return self._relation_type_cache.get(slug)

    async def find_municipality_for_location(
        self,
        location_hints: list[str],
        country: str | None = "DE",
    ) -> Entity | None:
        """Find matching municipality entity for location hints.

        This method tries multiple strategies:
        1. Exact name matching against municipality entities
        2. Normalized name matching (lowercase, no special chars)
        3. AI interpretation as fallback for ambiguous hints

        Args:
            location_hints: List of location-related strings from the API.
            country: ISO country code to filter by. Default "DE".

        Returns:
            Matching municipality Entity, or None if not found.
        """
        if not location_hints:
            return None

        # Get territorial entity type (formerly municipality)
        municipality_type = await self._get_entity_type("territorial_entity")
        if not municipality_type:
            # Fallback to old slug for backwards compatibility
            municipality_type = await self._get_entity_type("municipality")
        if not municipality_type:
            logger.warning("territorial_entity_type_not_found")
            return None

        # Try each hint with different matching strategies
        for hint in location_hints:
            if not hint or hint.startswith("geo:"):
                continue  # Skip empty hints and geo coordinates

            entity = await self._find_entity_by_name(hint, municipality_type.id, country)
            if entity:
                logger.debug(
                    "municipality_found_by_direct_match",
                    hint=hint,
                    entity_name=entity.name,
                )
                return entity

        # Try AI interpretation as fallback
        if self.use_ai and location_hints:
            interpreted = await self._ai_interpret_location(location_hints)
            if interpreted:
                entity = await self._find_entity_by_name(interpreted, municipality_type.id, country)
                if entity:
                    logger.info(
                        "municipality_found_by_ai",
                        hints=location_hints,
                        interpreted=interpreted,
                        entity_name=entity.name,
                    )
                    return entity

        logger.debug(
            "municipality_not_found",
            hints=location_hints,
        )
        return None

    async def _find_entity_by_name(
        self,
        name: str,
        entity_type_id: UUID,
        country: str | None = None,
    ) -> Entity | None:
        """Find entity by name using exact and normalized matching.

        Args:
            name: Name to search for.
            entity_type_id: Entity type to filter by.
            country: Optional country code to filter by.

        Returns:
            Matching Entity, or None.
        """
        # Build base query
        base_conditions = [
            Entity.entity_type_id == entity_type_id,
            Entity.is_active.is_(True),
        ]
        if country:
            base_conditions.append(Entity.country == country)

        # Try exact match first
        result = await self.session.execute(select(Entity).where(*base_conditions, Entity.name == name))
        entity = result.scalar_one_or_none()
        if entity:
            return entity

        # Try normalized match
        normalized = normalize_name(name)
        result = await self.session.execute(
            select(Entity).where(*base_conditions, Entity.name_normalized == normalized)
        )
        entity = result.scalar_one_or_none()
        if entity:
            return entity

        # NOTE: Removed substring matching (contains) as it caused false positives
        # like "Falken" matching "Falkenstein". AI interpretation provides a better
        # fallback for ambiguous cases.
        return None

    async def _ai_interpret_location(self, hints: list[str]) -> str | None:
        """Use AI to interpret location hints and extract municipality name.

        The AI is prompted to extract just the municipality name from
        potentially complex location strings like addresses or regional
        descriptions.

        Args:
            hints: List of location hint strings.

        Returns:
            Interpreted municipality name, or None.
        """
        # Filter out non-useful hints
        useful_hints = [h for h in hints if h and not h.startswith("geo:") and len(h) > 2]
        if not useful_hints:
            return None

        try:
            ai_service = await self._get_ai_service()

            prompt = f"""Extrahiere den deutschen Gemeindenamen aus diesen Standorthinweisen.

Standorthinweise: {", ".join(useful_hints)}

Antworte NUR mit dem Gemeindenamen (z.B. "Münster", "Berlin", "Aachen").
- Keine Bundesländer oder Regionen (z.B. nicht "Nordrhein-Westfalen")
- Keine Landkreise (z.B. nicht "Kreis Steinfurt")
- Keine Ortsteile, nur die Hauptgemeinde
- Wenn kein eindeutiger Gemeindename erkennbar ist, antworte mit "UNBEKANNT"

Gemeindename:"""

            response = await ai_service.generate_text(
                prompt=prompt,
                temperature=0.1,
                max_tokens=50,
            )

            result = response.strip().strip('"').strip("'")

            if result and result.upper() != "UNBEKANNT" and len(result) > 1:
                logger.debug(
                    "ai_location_interpretation",
                    hints=useful_hints,
                    result=result,
                )
                return result

        except Exception as e:
            logger.warning(
                "ai_location_interpretation_failed",
                error=str(e),
                hints=useful_hints,
            )

        return None

    async def find_entities_by_type(
        self,
        location_hints: list[str],
        entity_type_slug: str,
    ) -> list[Entity]:
        """Find entities of a specific type matching location hints.

        This is a more generic version that can search for any entity type,
        not just municipalities.

        Args:
            location_hints: List of location-related strings.
            entity_type_slug: Slug of the entity type to search for.

        Returns:
            List of matching entities.
        """
        entity_type = await self._get_entity_type(entity_type_slug)
        if not entity_type:
            return []

        results = []
        seen_ids = set()

        for hint in location_hints:
            if not hint or hint.startswith("geo:"):
                continue

            entity = await self._find_entity_by_name(hint, entity_type.id)
            if entity and entity.id not in seen_ids:
                results.append(entity)
                seen_ids.add(entity.id)

        return results

    async def create_location_relation(
        self,
        source_entity_id: UUID,
        target_municipality_id: UUID,
        confidence: float = 0.8,
    ) -> EntityRelation | None:
        """Create 'located_in' relation between entity and municipality.

        Args:
            source_entity_id: ID of the source entity (e.g., wind project).
            target_municipality_id: ID of the target municipality.
            confidence: Confidence score for the relation (0-1).

        Returns:
            Created EntityRelation, or None if creation failed.
        """
        relation_type = await self._get_relation_type("located_in")
        if not relation_type:
            logger.warning("located_in_relation_type_not_found")
            return None

        try:
            relation = await create_relation(
                self.session,
                source_entity_id=source_entity_id,
                target_entity_id=target_municipality_id,
                relation_type_id=relation_type.id,
                confidence_score=confidence,
            )

            if relation:
                logger.info(
                    "location_relation_created",
                    source_id=str(source_entity_id),
                    target_id=str(target_municipality_id),
                    confidence=confidence,
                )

            return relation

        except Exception as e:
            logger.error(
                "location_relation_creation_failed",
                error=str(e),
                source_id=str(source_entity_id),
                target_id=str(target_municipality_id),
            )
            return None

    async def link_entity_to_locations(
        self,
        entity_id: UUID,
        location_hints: list[str],
        link_types: list[str] | None = None,
    ) -> dict[str, list[UUID]]:
        """Link an entity to location-based entities.

        This method attempts to find and link to multiple entity types
        based on location hints (e.g., municipality, region).

        Args:
            entity_id: ID of the entity to link.
            location_hints: List of location-related strings.
            link_types: Entity types to link to. Defaults to ["municipality"].

        Returns:
            Dictionary mapping entity type slugs to lists of linked entity IDs.
        """
        link_types = link_types or ["territorial_entity"]
        results: dict[str, list[UUID]] = {}

        for entity_type_slug in link_types:
            linked_ids = []

            if entity_type_slug in ("territorial_entity", "municipality"):
                # Use specialized territorial entity finder
                municipality = await self.find_municipality_for_location(location_hints)
                if municipality:
                    relation = await self.create_location_relation(entity_id, municipality.id)
                    if relation:
                        linked_ids.append(municipality.id)
            else:
                # Generic entity type linking
                entities = await self.find_entities_by_type(location_hints, entity_type_slug)
                for entity in entities:
                    # Create appropriate relation based on type
                    relation_slug = self._get_relation_slug_for_type(entity_type_slug)
                    relation_type = await self._get_relation_type(relation_slug)
                    if relation_type:
                        relation = await create_relation(
                            self.session,
                            source_entity_id=entity_id,
                            target_entity_id=entity.id,
                            relation_type_id=relation_type.id,
                        )
                        if relation:
                            linked_ids.append(entity.id)

            results[entity_type_slug] = linked_ids

        return results

    def _get_relation_slug_for_type(self, entity_type_slug: str) -> str:
        """Get the appropriate relation type slug for an entity type.

        Args:
            entity_type_slug: Entity type slug.

        Returns:
            Relation type slug.
        """
        mapping = {
            "municipality": "located_in",
            "region": "located_in",
            "organization": "affiliated_with",
            "person": "related_to",
        }
        return mapping.get(entity_type_slug, "related_to")
