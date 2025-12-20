"""Multi-Hop Relation Resolver for Smart Query.

Enables complex queries like:
- "Zeige Personen, deren Gemeinden Pain Points haben"
- "Events bei denen Bürgermeister aus NRW teilnehmen"
- "Organisationen mit Mitarbeitern die Events besucht haben"
"""

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

import structlog
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Entity,
    EntityType,
    EntityRelation,
    RelationType,
    FacetType,
    FacetValue,
)

logger = structlog.get_logger()

# Maximum depth for relation traversal (prevents infinite loops and performance issues)
MAX_RELATION_DEPTH = 3

# Cache TTL in seconds (5 minutes)
CACHE_TTL = 300


class RelationHop:
    """Represents a single hop in a relation chain."""

    def __init__(
        self,
        relation_type_slug: str,
        direction: str = "source",  # "source" = follow from source to target, "target" = follow from target to source
        facet_filter: Optional[str] = None,  # Optional: only include if entity has this facet
        negative_facet_filter: Optional[str] = None,  # Optional: exclude if entity has this facet
        position_filter: Optional[List[str]] = None,  # Optional: filter by position
        location_filter: Optional[str] = None,  # Optional: filter by admin_level_1
    ):
        self.relation_type_slug = relation_type_slug
        self.direction = direction
        self.facet_filter = facet_filter
        self.negative_facet_filter = negative_facet_filter
        self.position_filter = position_filter
        self.location_filter = location_filter

    def __repr__(self) -> str:
        return f"RelationHop({self.relation_type_slug}, dir={self.direction})"


class RelationChain:
    """Represents a chain of relation hops."""

    def __init__(self, hops: List[RelationHop]):
        if len(hops) > MAX_RELATION_DEPTH:
            raise ValueError(f"Relation chain exceeds maximum depth of {MAX_RELATION_DEPTH}")
        self.hops = hops

    def __repr__(self) -> str:
        return f"RelationChain({' -> '.join(str(h) for h in self.hops)})"


class RelationResolver:
    """Service for resolving multi-hop relations in queries."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._relation_type_cache: Dict[str, RelationType] = {}
        self._facet_type_cache: Dict[str, FacetType] = {}
        self._entity_type_cache: Dict[str, EntityType] = {}
        self._cache_timestamp: Optional[datetime] = None

    async def _ensure_cache(self) -> None:
        """Ensure caches are populated and not stale."""
        now = datetime.utcnow()
        if self._cache_timestamp and (now - self._cache_timestamp).seconds < CACHE_TTL:
            return

        # Load relation types
        result = await self.session.execute(
            select(RelationType).where(RelationType.is_active.is_(True))
        )
        self._relation_type_cache = {rt.slug: rt for rt in result.scalars().all()}

        # Load facet types
        result = await self.session.execute(
            select(FacetType).where(FacetType.is_active.is_(True))
        )
        self._facet_type_cache = {ft.slug: ft for ft in result.scalars().all()}

        # Load entity types
        result = await self.session.execute(
            select(EntityType).where(EntityType.is_active.is_(True))
        )
        self._entity_type_cache = {et.slug: et for et in result.scalars().all()}

        self._cache_timestamp = now
        logger.debug(
            "Relation resolver cache refreshed",
            relation_types=len(self._relation_type_cache),
            facet_types=len(self._facet_type_cache),
            entity_types=len(self._entity_type_cache),
        )

    async def resolve_relation_chain(
        self,
        starting_entity_ids: List[UUID],
        chain: RelationChain,
    ) -> Tuple[List[UUID], Dict[UUID, List[Dict[str, Any]]]]:
        """Resolve a relation chain starting from a set of entities.

        Args:
            starting_entity_ids: List of entity IDs to start from
            chain: The relation chain to follow

        Returns:
            Tuple of:
            - List of final entity IDs after traversing the chain
            - Dict mapping each final entity ID to its traversal path
        """
        await self._ensure_cache()

        if not starting_entity_ids:
            return [], {}

        current_ids = set(starting_entity_ids)
        paths: Dict[UUID, List[Dict[str, Any]]] = {
            eid: [{"entity_id": eid, "hop": 0}] for eid in starting_entity_ids
        }

        for hop_index, hop in enumerate(chain.hops):
            logger.debug(
                "Processing relation hop",
                hop_index=hop_index,
                hop=str(hop),
                current_count=len(current_ids),
            )

            next_ids, new_paths = await self._resolve_single_hop(
                current_ids, hop, paths, hop_index + 1
            )

            if not next_ids:
                logger.debug("No entities found after hop", hop_index=hop_index)
                return [], {}

            current_ids = next_ids
            paths = new_paths

        return list(current_ids), paths

    async def _resolve_single_hop(
        self,
        entity_ids: Set[UUID],
        hop: RelationHop,
        current_paths: Dict[UUID, List[Dict[str, Any]]],
        hop_number: int,
    ) -> Tuple[Set[UUID], Dict[UUID, List[Dict[str, Any]]]]:
        """Resolve a single hop in the relation chain.

        Args:
            entity_ids: Current set of entity IDs
            hop: The hop to resolve
            current_paths: Current traversal paths
            hop_number: The hop number (1-based)

        Returns:
            Tuple of new entity IDs and updated paths
        """
        relation_type = self._relation_type_cache.get(hop.relation_type_slug)
        if not relation_type:
            logger.warning(
                "Unknown relation type",
                relation_type_slug=hop.relation_type_slug,
            )
            return set(), {}

        # Build query based on direction
        if hop.direction == "source":
            # Following from source to target: entity_ids are sources, we want targets
            query = (
                select(EntityRelation)
                .where(
                    EntityRelation.relation_type_id == relation_type.id,
                    EntityRelation.source_entity_id.in_(entity_ids),
                    EntityRelation.is_active.is_(True),
                )
            )
            source_field = "source_entity_id"
            target_field = "target_entity_id"
        else:
            # Following from target to source: entity_ids are targets, we want sources
            query = (
                select(EntityRelation)
                .where(
                    EntityRelation.relation_type_id == relation_type.id,
                    EntityRelation.target_entity_id.in_(entity_ids),
                    EntityRelation.is_active.is_(True),
                )
            )
            source_field = "target_entity_id"
            target_field = "source_entity_id"

        result = await self.session.execute(query)
        relations = result.scalars().all()

        if not relations:
            return set(), {}

        # Collect next entity IDs
        next_ids: Set[UUID] = set()
        entity_mapping: Dict[UUID, Set[UUID]] = defaultdict(set)  # source -> targets

        for rel in relations:
            source_id = getattr(rel, source_field)
            target_id = getattr(rel, target_field)
            entity_mapping[source_id].add(target_id)
            next_ids.add(target_id)

        # Apply filters to next entities if specified
        if hop.facet_filter or hop.negative_facet_filter or hop.position_filter or hop.location_filter:
            next_ids = await self._apply_hop_filters(
                next_ids,
                facet_filter=hop.facet_filter,
                negative_facet_filter=hop.negative_facet_filter,
                position_filter=hop.position_filter,
                location_filter=hop.location_filter,
            )

        # Update paths
        new_paths: Dict[UUID, List[Dict[str, Any]]] = {}
        for source_id, targets in entity_mapping.items():
            if source_id not in current_paths:
                continue
            for target_id in targets:
                if target_id not in next_ids:
                    continue  # Filtered out
                if target_id not in new_paths:
                    new_paths[target_id] = []
                for path in current_paths[source_id]:
                    new_path = path.copy()
                    new_path.append({
                        "entity_id": target_id,
                        "hop": hop_number,
                        "relation_type": hop.relation_type_slug,
                        "from_entity": source_id,
                    })
                    new_paths[target_id].append(new_path)

        return next_ids, new_paths

    async def _apply_hop_filters(
        self,
        entity_ids: Set[UUID],
        facet_filter: Optional[str] = None,
        negative_facet_filter: Optional[str] = None,
        position_filter: Optional[List[str]] = None,
        location_filter: Optional[str] = None,
    ) -> Set[UUID]:
        """Apply additional filters to entities at a hop.

        Args:
            entity_ids: Current entity IDs
            facet_filter: Only include entities with this facet type
            negative_facet_filter: Exclude entities with this facet type
            position_filter: Only include entities with one of these positions
            location_filter: Only include entities in this admin_level_1

        Returns:
            Filtered set of entity IDs
        """
        if not entity_ids:
            return set()

        # Start with all entities
        conditions = [
            Entity.id.in_(entity_ids),
            Entity.is_active.is_(True),
        ]

        # Apply location filter
        if location_filter:
            conditions.append(Entity.admin_level_1 == location_filter)

        # Apply position filter
        if position_filter:
            position_conditions = []
            for pos in position_filter:
                position_conditions.append(
                    Entity.core_attributes["position"].astext.ilike(f"%{pos}%")
                )
            if position_conditions:
                conditions.append(or_(*position_conditions))

        # Execute base query
        query = select(Entity.id).where(*conditions)
        result = await self.session.execute(query)
        filtered_ids = {row[0] for row in result.fetchall()}

        # Apply positive facet filter
        if facet_filter and filtered_ids:
            facet_type = self._facet_type_cache.get(facet_filter)
            if facet_type:
                fv_result = await self.session.execute(
                    select(FacetValue.entity_id)
                    .distinct()
                    .where(
                        FacetValue.entity_id.in_(filtered_ids),
                        FacetValue.facet_type_id == facet_type.id,
                        FacetValue.is_active.is_(True),
                    )
                )
                filtered_ids = {row[0] for row in fv_result.fetchall()}

        # Apply negative facet filter
        if negative_facet_filter and filtered_ids:
            neg_facet_type = self._facet_type_cache.get(negative_facet_filter)
            if neg_facet_type:
                neg_result = await self.session.execute(
                    select(FacetValue.entity_id)
                    .distinct()
                    .where(
                        FacetValue.entity_id.in_(filtered_ids),
                        FacetValue.facet_type_id == neg_facet_type.id,
                        FacetValue.is_active.is_(True),
                    )
                )
                exclude_ids = {row[0] for row in neg_result.fetchall()}
                filtered_ids = filtered_ids - exclude_ids

        return filtered_ids

    async def resolve_entities_with_related_facets(
        self,
        primary_entity_type_slug: str,
        relation_chain: List[Dict[str, Any]],
        target_facet_types: List[str],
        negative_facet_types: Optional[List[str]] = None,
        base_filters: Optional[Dict[str, Any]] = None,
    ) -> List[UUID]:
        """Find entities of a given type whose related entities (via relation chain) have specific facets.

        Example:
            "Personen, deren Gemeinden Pain Points haben"
            - primary_entity_type_slug: "person"
            - relation_chain: [{"type": "works_for", "direction": "source"}]
            - target_facet_types: ["pain_point"]

        Args:
            primary_entity_type_slug: The type of entities to return
            relation_chain: List of relation hops to follow
            target_facet_types: Facet types that the final entities must have
            negative_facet_types: Facet types that the final entities must NOT have
            base_filters: Additional filters for the primary entities

        Returns:
            List of primary entity IDs that match the criteria
        """
        await self._ensure_cache()

        # Get primary entity type
        entity_type = self._entity_type_cache.get(primary_entity_type_slug)
        if not entity_type:
            logger.warning("Unknown entity type", entity_type_slug=primary_entity_type_slug)
            return []

        # Build base conditions for primary entities
        conditions = [
            Entity.entity_type_id == entity_type.id,
            Entity.is_active.is_(True),
        ]

        # Apply base filters
        if base_filters:
            if base_filters.get("admin_level_1"):
                admin_level = base_filters["admin_level_1"]
                if isinstance(admin_level, list):
                    conditions.append(Entity.admin_level_1.in_(admin_level))
                else:
                    conditions.append(Entity.admin_level_1 == admin_level)

            if base_filters.get("country"):
                conditions.append(Entity.country == base_filters["country"])

            if base_filters.get("position_keywords"):
                pos_conditions = []
                for kw in base_filters["position_keywords"]:
                    pos_conditions.append(
                        Entity.core_attributes["position"].astext.ilike(f"%{kw}%")
                    )
                if pos_conditions:
                    conditions.append(or_(*pos_conditions))

        # Get all primary entities
        primary_result = await self.session.execute(
            select(Entity.id).where(*conditions)
        )
        primary_ids = [row[0] for row in primary_result.fetchall()]

        if not primary_ids:
            return []

        logger.debug(
            "Starting multi-hop resolution",
            primary_type=primary_entity_type_slug,
            primary_count=len(primary_ids),
            hops=len(relation_chain),
        )

        # Build and resolve the relation chain
        hops = []
        for hop_config in relation_chain:
            hop = RelationHop(
                relation_type_slug=hop_config.get("type", ""),
                direction=hop_config.get("direction", "source"),
                facet_filter=hop_config.get("facet_filter"),
                negative_facet_filter=hop_config.get("negative_facet_filter"),
                position_filter=hop_config.get("position_filter"),
                location_filter=hop_config.get("location_filter"),
            )
            hops.append(hop)

        chain = RelationChain(hops)

        # Resolve the chain to get final (related) entity IDs
        final_ids, paths = await self.resolve_relation_chain(primary_ids, chain)

        if not final_ids:
            return []

        # Filter final entities by facet requirements
        if target_facet_types:
            facet_type_ids = [
                self._facet_type_cache[ft].id
                for ft in target_facet_types
                if ft in self._facet_type_cache
            ]
            if facet_type_ids:
                fv_result = await self.session.execute(
                    select(FacetValue.entity_id)
                    .distinct()
                    .where(
                        FacetValue.entity_id.in_(final_ids),
                        FacetValue.facet_type_id.in_(facet_type_ids),
                        FacetValue.is_active.is_(True),
                    )
                )
                final_ids = [row[0] for row in fv_result.fetchall()]

        if negative_facet_types and final_ids:
            neg_facet_type_ids = [
                self._facet_type_cache[ft].id
                for ft in negative_facet_types
                if ft in self._facet_type_cache
            ]
            if neg_facet_type_ids:
                neg_result = await self.session.execute(
                    select(FacetValue.entity_id)
                    .distinct()
                    .where(
                        FacetValue.entity_id.in_(final_ids),
                        FacetValue.facet_type_id.in_(neg_facet_type_ids),
                        FacetValue.is_active.is_(True),
                    )
                )
                exclude_ids = {row[0] for row in neg_result.fetchall()}
                final_ids = [eid for eid in final_ids if eid not in exclude_ids]

        if not final_ids:
            return []

        # Reverse-map: Find which primary entities lead to the qualifying final entities
        final_ids_set = set(final_ids)
        matching_primary_ids = []

        for primary_id, path_list in paths.items():
            # Check if any path ends at a qualifying final entity
            for path in path_list:
                if len(path) > 0:
                    # The last entry in the path is the final entity
                    last_hop = path[-1] if isinstance(path[-1], dict) else path
                    final_entity_id = last_hop.get("entity_id") if isinstance(last_hop, dict) else path[-1]
                    if final_entity_id in final_ids_set:
                        matching_primary_ids.append(primary_id)
                        break

        # Deduplicate
        matching_primary_ids = list(set(matching_primary_ids))

        logger.info(
            "Multi-hop resolution complete",
            primary_type=primary_entity_type_slug,
            matching_count=len(matching_primary_ids),
            final_entities_with_facets=len(final_ids),
        )

        return matching_primary_ids

    async def get_relation_path_details(
        self,
        entity_id: UUID,
        relation_chain: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Get detailed path information for a single entity through a relation chain.

        Useful for explaining why an entity matched a multi-hop query.

        Args:
            entity_id: The entity to trace
            relation_chain: The relation chain to follow

        Returns:
            List of path details with entity names and relation info
        """
        await self._ensure_cache()

        hops = [
            RelationHop(
                relation_type_slug=hop.get("type", ""),
                direction=hop.get("direction", "source"),
            )
            for hop in relation_chain
        ]
        chain = RelationChain(hops)

        final_ids, paths = await self.resolve_relation_chain([entity_id], chain)

        if not paths:
            return []

        # Collect all entity IDs from paths
        all_entity_ids: Set[UUID] = set()
        for entity_paths in paths.values():
            for path in entity_paths:
                for hop_info in path:
                    if isinstance(hop_info, dict):
                        all_entity_ids.add(hop_info["entity_id"])
                        if "from_entity" in hop_info:
                            all_entity_ids.add(hop_info["from_entity"])

        # Load entity details
        entity_details: Dict[UUID, Entity] = {}
        if all_entity_ids:
            result = await self.session.execute(
                select(Entity).where(Entity.id.in_(all_entity_ids))
            )
            for entity in result.scalars().all():
                entity_details[entity.id] = entity

        # Build detailed paths
        detailed_paths = []
        for final_id, entity_paths in paths.items():
            for path in entity_paths:
                detailed_path = []
                for hop_info in path:
                    if isinstance(hop_info, dict):
                        entity = entity_details.get(hop_info["entity_id"])
                        detail = {
                            "entity_id": str(hop_info["entity_id"]),
                            "entity_name": entity.name if entity else "Unknown",
                            "entity_type": entity.entity_type.slug if entity and entity.entity_type else None,
                            "hop": hop_info.get("hop", 0),
                        }
                        if "relation_type" in hop_info:
                            detail["relation_type"] = hop_info["relation_type"]
                            rel_type = self._relation_type_cache.get(hop_info["relation_type"])
                            detail["relation_name"] = rel_type.name if rel_type else hop_info["relation_type"]
                        if "from_entity" in hop_info:
                            from_entity = entity_details.get(hop_info["from_entity"])
                            detail["from_entity_name"] = from_entity.name if from_entity else "Unknown"
                        detailed_path.append(detail)
                detailed_paths.append(detailed_path)

        return detailed_paths


async def get_relation_resolver(session: AsyncSession) -> RelationResolver:
    """Factory function for RelationResolver."""
    return RelationResolver(session)


def parse_relation_chain_from_query(query_params: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Parse relation chain configuration from query parameters.

    Handles both simple and complex relation chain formats.

    Args:
        query_params: The interpreted query parameters

    Returns:
        List of relation hop configurations, or None if no multi-hop chain
    """
    relation_chain = query_params.get("relation_chain", [])

    if not relation_chain:
        return None

    # Validate and normalize the chain
    normalized_chain = []
    for hop in relation_chain:
        if isinstance(hop, dict):
            normalized_hop = {
                "type": hop.get("type", ""),
                "direction": hop.get("direction", "source"),
            }
            # Optional filters at each hop
            if hop.get("facet_filter"):
                normalized_hop["facet_filter"] = hop["facet_filter"]
            if hop.get("negative_facet_filter"):
                normalized_hop["negative_facet_filter"] = hop["negative_facet_filter"]
            if hop.get("position_filter"):
                normalized_hop["position_filter"] = hop["position_filter"]
            if hop.get("location_filter"):
                normalized_hop["location_filter"] = hop["location_filter"]

            normalized_chain.append(normalized_hop)
        elif isinstance(hop, str):
            # Simple format: just the relation type slug
            normalized_chain.append({
                "type": hop,
                "direction": "source",
            })

    return normalized_chain if normalized_chain else None
