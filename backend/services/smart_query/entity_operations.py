"""Entity, Facet, and Relation operations for Smart Query Service."""

import uuid as uuid_module
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Entity,
    EntityType,
    FacetType,
    FacetValue,
    RelationType,
    EntityRelation,
    DataSource,
    Category,
)
from app.models.data_source import SourceType, SourceStatus
from app.models.data_source_category import DataSourceCategory
from app.utils.similarity import DEFAULT_SIMILARITY_THRESHOLD
from services.entity_matching_service import EntityMatchingService
from .utils import generate_slug

import structlog

logger = structlog.get_logger()

# Constants for Smart Query operations
SMART_QUERY_CONFIDENCE_SCORE = 0.9  # High confidence for user-initiated entries
DEFAULT_ENTITY_TYPE_ORDER = 10  # Default display order for new entity types


async def create_entity_type_from_command(
    session: AsyncSession,
    entity_type_data: Dict[str, Any],
) -> Tuple[Optional[EntityType], str]:
    """Create a new entity type from smart query command.

    Uses semantic similarity detection to find existing similar types
    and return them instead of creating duplicates.

    Also checks if the requested type is actually a hierarchy level of
    an existing hierarchical EntityType (e.g., "Bundesland" is a hierarchy
    level of "territorial_entity", not a separate type).
    """
    from app.utils.similarity import find_similar_entity_types, get_hierarchy_mapping

    name = entity_type_data.get("name", "").strip()
    if not name:
        return None, "Name ist erforderlich"

    # Use explicit slug if provided, otherwise generate from name
    slug = entity_type_data.get("slug") or generate_slug(name)

    # Check for exact duplicates first
    existing = await session.execute(
        select(EntityType).where(
            or_(EntityType.name == name, EntityType.slug == slug)
        )
    )
    exact_match = existing.scalar()
    if exact_match:
        return exact_match, f"Entity-Typ '{exact_match.name}' existiert bereits (exakt)"

    # Check if this is actually a hierarchy level of an existing type
    hierarchy_mapping = get_hierarchy_mapping(name)
    if hierarchy_mapping:
        parent_type_slug = hierarchy_mapping["parent_type_slug"]
        hierarchy_level = hierarchy_mapping["hierarchy_level"]
        level_name = hierarchy_mapping["level_name"]

        # Find the parent hierarchical type
        parent_type_result = await session.execute(
            select(EntityType).where(
                EntityType.slug == parent_type_slug,
                EntityType.is_active.is_(True),
            )
        )
        parent_type = parent_type_result.scalar_one_or_none()

        if parent_type:
            logger.info(
                "Redirecting to hierarchical EntityType",
                requested_name=name,
                parent_type=parent_type.name,
                parent_slug=parent_type_slug,
                hierarchy_level=hierarchy_level,
                level_name=level_name,
            )
            return parent_type, (
                f"'{level_name}' ist eine Hierarchie-Ebene (Level {hierarchy_level}) "
                f"von '{parent_type.name}'. Verwende diesen Typ und setze hierarchy_level={hierarchy_level}."
            )

    # Check for semantically similar types
    similar_types = await find_similar_entity_types(session, name, threshold=0.7)
    if similar_types:
        best_match, score, reason = similar_types[0]
        logger.info(
            "Found similar EntityType instead of creating duplicate",
            requested_name=name,
            matched_name=best_match.name,
            similarity_score=score,
            reason=reason,
        )
        return best_match, f"Ähnlicher Entity-Typ '{best_match.name}' gefunden ({reason})"

    # Create entity type
    entity_type = EntityType(
        id=uuid_module.uuid4(),
        name=name,
        slug=slug,
        name_plural=entity_type_data.get("name_plural", f"{name}s"),
        description=entity_type_data.get("description"),
        icon=entity_type_data.get("icon", "mdi-folder"),
        color=entity_type_data.get("color", "#4CAF50"),
        is_primary=entity_type_data.get("is_primary", True),
        is_public=entity_type_data.get("is_public", True),  # Default to public
        supports_hierarchy=entity_type_data.get("supports_hierarchy", False),
        hierarchy_config=entity_type_data.get("hierarchy_config"),
        attribute_schema=entity_type_data.get("attribute_schema"),
        display_order=DEFAULT_ENTITY_TYPE_ORDER,
        is_active=True,
        is_system=False,
    )
    session.add(entity_type)
    await session.flush()

    return entity_type, f"Entity-Typ '{name}' erstellt"


def _escape_like_pattern(pattern: str) -> str:
    """Escape special characters for SQL LIKE patterns."""
    # Escape backslash first, then %, then _
    return pattern.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def find_entity_by_name(
    session: AsyncSession,
    name: str,
    entity_type_slug: Optional[str] = None,
) -> Optional[Entity]:
    """Find an entity by name (case-insensitive).

    Note: Uses ILIKE for case-insensitive search.
    Special LIKE characters (%, _) in the name are escaped to prevent SQL injection.
    """
    # Escape LIKE special characters to prevent injection
    escaped_name = _escape_like_pattern(name)

    query = select(Entity).where(
        Entity.name.ilike(f"%{escaped_name}%", escape="\\"),
        Entity.is_active.is_(True),
    )
    if entity_type_slug:
        entity_type_result = await session.execute(
            select(EntityType).where(EntityType.slug == entity_type_slug)
        )
        entity_type = entity_type_result.scalar_one_or_none()
        if entity_type:
            query = query.where(Entity.entity_type_id == entity_type.id)

    result = await session.execute(query.limit(1))
    return result.scalar_one_or_none()


async def lookup_location_coordinates(
    session: AsyncSession,
    location_name: str,
) -> Optional[Dict[str, Any]]:
    """
    Look up coordinates for a location/territorial entity.

    This function searches for an existing entity with coordinates that matches
    the given location name. It's used to inherit coordinates from territorial
    entities (municipalities, cities) when creating new entities.

    Args:
        session: Database session
        location_name: Name of the location to look up (e.g., "München", "Berlin")

    Returns:
        Dict with latitude, longitude, admin_level_1 or None if not found
    """
    if not location_name or not location_name.strip():
        return None

    location_name = location_name.strip()
    escaped_name = _escape_like_pattern(location_name)

    # First, try exact match in territorial_entity type
    entity_type_result = await session.execute(
        select(EntityType).where(EntityType.slug == "territorial_entity")
    )
    entity_type = entity_type_result.scalar_one_or_none()

    if entity_type:
        # Try exact name match first (more precise)
        exact_query = select(Entity).where(
            Entity.entity_type_id == entity_type.id,
            Entity.name.ilike(escaped_name, escape="\\"),
            Entity.latitude.isnot(None),
            Entity.longitude.isnot(None),
            Entity.is_active.is_(True),
        ).limit(1)

        result = await session.execute(exact_query)
        entity = result.scalar_one_or_none()

        if entity:
            logger.debug(
                "Found exact location match",
                location_name=location_name,
                entity_name=entity.name,
                latitude=entity.latitude,
                longitude=entity.longitude,
            )
            return {
                "latitude": entity.latitude,
                "longitude": entity.longitude,
                "admin_level_1": entity.admin_level_1,
                "entity_id": str(entity.id),
                "entity_name": entity.name,
            }

        # Try partial match in territorial entities
        partial_query = select(Entity).where(
            Entity.entity_type_id == entity_type.id,
            Entity.name.ilike(f"%{escaped_name}%", escape="\\"),
            Entity.latitude.isnot(None),
            Entity.longitude.isnot(None),
            Entity.is_active.is_(True),
        ).limit(1)

        result = await session.execute(partial_query)
        entity = result.scalar_one_or_none()

        if entity:
            logger.debug(
                "Found partial location match in territorial_entity",
                location_name=location_name,
                entity_name=entity.name,
                latitude=entity.latitude,
                longitude=entity.longitude,
            )
            return {
                "latitude": entity.latitude,
                "longitude": entity.longitude,
                "admin_level_1": entity.admin_level_1,
                "entity_id": str(entity.id),
                "entity_name": entity.name,
            }

    # Fallback: Search in any entity type with coordinates
    fallback_query = select(Entity).where(
        Entity.name.ilike(f"%{escaped_name}%", escape="\\"),
        Entity.latitude.isnot(None),
        Entity.longitude.isnot(None),
        Entity.is_active.is_(True),
    ).limit(1)

    result = await session.execute(fallback_query)
    entity = result.scalar_one_or_none()

    if entity:
        logger.debug(
            "Found location match in fallback search",
            location_name=location_name,
            entity_name=entity.name,
            latitude=entity.latitude,
            longitude=entity.longitude,
        )
        return {
            "latitude": entity.latitude,
            "longitude": entity.longitude,
            "admin_level_1": entity.admin_level_1,
            "entity_id": str(entity.id),
            "entity_name": entity.name,
        }

    logger.debug(
        "No location coordinates found",
        location_name=location_name,
    )
    return None


async def create_entity_from_command(
    session: AsyncSession,
    entity_type_slug: str,
    entity_data: Dict[str, Any],
) -> Tuple[Optional[Entity], str]:
    """
    Create or find an entity from smart query command.

    Uses centralized EntityMatchingService for consistent:
    - Name normalization
    - Duplicate detection
    - Race-condition-safe creation
    """
    name = entity_data.get("name", "").strip()
    if not name:
        return None, "Name ist erforderlich"

    # Use centralized EntityMatchingService for consistent entity creation
    service = EntityMatchingService(session)

    # Get entity type first for better error messages
    entity_type = await service.get_entity_type(entity_type_slug)
    if not entity_type:
        return None, f"Entity-Typ '{entity_type_slug}' nicht gefunden"

    # Check if entity already exists before attempting creation
    # This allows us to reliably detect if the entity was newly created
    from app.utils.text import normalize_entity_name
    name_normalized = normalize_entity_name(name, entity_data.get("country", "DE"))

    existing_entity = await session.execute(
        select(Entity).where(
            Entity.entity_type_id == entity_type.id,
            Entity.name_normalized == name_normalized,
            Entity.is_active.is_(True),
        )
    )
    entity_existed = existing_entity.scalar_one_or_none() is not None

    # Location reference lookup: inherit coordinates from territorial entities
    # Only if no coordinates are explicitly provided
    latitude = entity_data.get("latitude")
    longitude = entity_data.get("longitude")
    admin_level_1 = entity_data.get("admin_level_1")
    location_source = None

    if not latitude and not longitude and entity_data.get("location_reference"):
        location_coords = await lookup_location_coordinates(
            session,
            entity_data["location_reference"]
        )
        if location_coords:
            latitude = location_coords["latitude"]
            longitude = location_coords["longitude"]
            location_source = location_coords.get("entity_name")
            # Also inherit admin_level_1 if not explicitly set
            if not admin_level_1 and location_coords.get("admin_level_1"):
                admin_level_1 = location_coords["admin_level_1"]
            logger.info(
                "Inherited coordinates from location reference",
                entity_name=name,
                location_reference=entity_data["location_reference"],
                source_entity=location_source,
                latitude=latitude,
                longitude=longitude,
            )

    entity = await service.get_or_create_entity(
        entity_type_slug=entity_type_slug,
        name=name,
        country=entity_data.get("country", "DE"),
        external_id=entity_data.get("external_id"),
        core_attributes=entity_data.get("core_attributes", {}),
        latitude=latitude,
        longitude=longitude,
        admin_level_1=admin_level_1,
        admin_level_2=entity_data.get("admin_level_2"),
        similarity_threshold=entity_data.get("similarity_threshold", DEFAULT_SIMILARITY_THRESHOLD),
    )

    if not entity:
        return None, f"Entity konnte nicht erstellt werden"

    type_name = entity_type.name

    if not entity_existed:
        return entity, f"Entity '{name}' ({type_name}) erstellt"
    else:
        return entity, f"Entity '{entity.name}' ({type_name}) gefunden"


async def create_facet_from_command(
    session: AsyncSession,
    facet_data: Dict[str, Any],
) -> Tuple[Optional[FacetValue], str]:
    """Create a new facet value from smart query command."""
    facet_type_slug = facet_data.get("facet_type")
    target_name = facet_data.get("target_entity_name")

    if not facet_type_slug or not target_name:
        return None, "Facet-Typ und Ziel-Entity sind erforderlich"

    # Find facet type
    facet_type_result = await session.execute(
        select(FacetType).where(FacetType.slug == facet_type_slug)
    )
    facet_type = facet_type_result.scalar_one_or_none()
    if not facet_type:
        return None, f"Facet-Typ '{facet_type_slug}' nicht gefunden"

    # Find target entity
    target_entity = await find_entity_by_name(session, target_name)
    if not target_entity:
        return None, f"Entity '{target_name}' nicht gefunden"

    # Create facet value
    from app.models.facet_value import FacetValueSourceType
    facet_value = FacetValue(
        id=uuid_module.uuid4(),
        entity_id=target_entity.id,
        facet_type_id=facet_type.id,
        value=facet_data.get("value", {}),
        text_representation=facet_data.get("text_representation", ""),
        source_type=FacetValueSourceType.SMART_QUERY,
        confidence_score=SMART_QUERY_CONFIDENCE_SCORE,
        is_active=True,
    )
    session.add(facet_value)
    await session.flush()

    return facet_value, f"Facet '{facet_type.name}' für '{target_entity.name}' erstellt"


async def create_relation_from_command(
    session: AsyncSession,
    relation_data: Dict[str, Any],
) -> Tuple[Optional[EntityRelation], str]:
    """Create a new entity relation from smart query command."""
    relation_type_slug = relation_data.get("relation_type")
    source_name = relation_data.get("source_entity_name")
    source_type = relation_data.get("source_entity_type")
    target_name = relation_data.get("target_entity_name")
    target_type = relation_data.get("target_entity_type")

    if not all([relation_type_slug, source_name, target_name]):
        return None, "Relation-Typ, Quell- und Ziel-Entity sind erforderlich"

    # Find relation type
    relation_type_result = await session.execute(
        select(RelationType).where(RelationType.slug == relation_type_slug)
    )
    relation_type = relation_type_result.scalar_one_or_none()
    if not relation_type:
        return None, f"Relation-Typ '{relation_type_slug}' nicht gefunden"

    # Find source entity
    source_entity = await find_entity_by_name(session, source_name, source_type)
    if not source_entity:
        return None, f"Quell-Entity '{source_name}' nicht gefunden"

    # Find target entity
    target_entity = await find_entity_by_name(session, target_name, target_type)
    if not target_entity:
        return None, f"Ziel-Entity '{target_name}' nicht gefunden"

    # Check for existing relation
    existing = await session.execute(
        select(EntityRelation).where(
            EntityRelation.source_entity_id == source_entity.id,
            EntityRelation.target_entity_id == target_entity.id,
            EntityRelation.relation_type_id == relation_type.id,
        )
    )
    if existing.scalar():
        return None, f"Relation '{source_entity.name}' → '{target_entity.name}' existiert bereits"

    # Create relation
    relation = EntityRelation(
        id=uuid_module.uuid4(),
        source_entity_id=source_entity.id,
        target_entity_id=target_entity.id,
        relation_type_id=relation_type.id,
        is_active=True,
    )
    session.add(relation)
    await session.flush()

    # For 'located_in' relations: inherit coordinates from target entity if source has none
    # This ensures entities get geographic data when linked to a location
    coords_inherited = False
    if relation_type_slug == "located_in" and target_entity:
        if target_entity.latitude and target_entity.longitude:
            if not source_entity.latitude and not source_entity.longitude:
                source_entity.latitude = target_entity.latitude
                source_entity.longitude = target_entity.longitude
                # Also inherit admin_level_1 if not set
                if not source_entity.admin_level_1 and target_entity.admin_level_1:
                    source_entity.admin_level_1 = target_entity.admin_level_1
                await session.flush()
                coords_inherited = True
                logger.info(
                    "Inherited coordinates from located_in relation",
                    source_entity=source_entity.name,
                    target_entity=target_entity.name,
                    latitude=target_entity.latitude,
                    longitude=target_entity.longitude,
                )

    message = f"Relation '{source_entity.name}' → '{target_entity.name}' ({relation_type.name}) erstellt"
    if coords_inherited:
        message += f" (Koordinaten von '{target_entity.name}' übernommen)"

    return relation, message


async def create_located_in_relation(
    session: AsyncSession,
    source_entity: Entity,
    target_entity: Entity,
) -> Optional[EntityRelation]:
    """Create a 'located_in' relation between two entities.

    This is used for cross-entity-type relations, e.g., Windpark -> Gemeinde.
    Automatically creates the 'located_in' RelationType if it doesn't exist.

    Args:
        session: Database session
        source_entity: The entity that is located somewhere (e.g., Windpark)
        target_entity: The location entity (e.g., Gemeinde)

    Returns:
        Created EntityRelation or None if already exists
    """
    # Get or create the 'located_in' relation type for this source/target type combo
    # The slug needs to be unique per source/target entity type combination
    source_type_id = source_entity.entity_type_id
    target_type_id = target_entity.entity_type_id

    # First check for an existing relation type that matches this combo
    relation_type_result = await session.execute(
        select(RelationType).where(
            RelationType.slug == "located_in",
            RelationType.source_entity_type_id == source_type_id,
            RelationType.target_entity_type_id == target_type_id,
        )
    )
    relation_type = relation_type_result.scalar_one_or_none()

    if not relation_type:
        # Check if ANY located_in exists - if so, need a unique slug
        any_located_in = await session.execute(
            select(RelationType).where(RelationType.slug == "located_in")
        )
        existing_located_in = any_located_in.scalar_one_or_none()

        if existing_located_in:
            # Use an extended slug for different type combinations
            source_type_result = await session.execute(
                select(EntityType).where(EntityType.id == source_type_id)
            )
            source_type = source_type_result.scalar_one_or_none()
            slug = f"located_in_{source_type.slug}" if source_type else "located_in_generic"
        else:
            slug = "located_in"

        # Create the relation type with the correct entity type IDs
        relation_type = RelationType(
            id=uuid_module.uuid4(),
            name="Befindet sich in",
            name_inverse="Enthält",
            slug=slug,
            description="Räumliche Zuordnung einer Entity zu einem Gebiet",
            source_entity_type_id=source_type_id,
            target_entity_type_id=target_type_id,
            cardinality="n:m",
            icon="mdi-map-marker",
            color="#4CAF50",
            is_active=True,
            is_system=True,
        )
        session.add(relation_type)
        await session.flush()
        logger.info(
            "Created RelationType",
            slug=slug,
            source_type_id=str(source_type_id),
            target_type_id=str(target_type_id),
        )

    # Check if relation already exists
    existing = await session.execute(
        select(EntityRelation).where(
            EntityRelation.source_entity_id == source_entity.id,
            EntityRelation.target_entity_id == target_entity.id,
            EntityRelation.relation_type_id == relation_type.id,
        )
    )
    if existing.scalar():
        logger.debug(
            "Relation already exists",
            source=source_entity.name,
            target=target_entity.name,
        )
        return None

    # Create the relation
    relation = EntityRelation(
        id=uuid_module.uuid4(),
        source_entity_id=source_entity.id,
        target_entity_id=target_entity.id,
        relation_type_id=relation_type.id,
        is_active=True,
    )
    session.add(relation)
    await session.flush()

    logger.info(
        "Created located_in relation",
        source=source_entity.name,
        target=target_entity.name,
    )

    return relation


async def match_entity_to_parent_by_name(
    session: AsyncSession,
    name_to_match: str,
    parent_entity_type_slug: str = "territorial_entity",
    admin_level_1: Optional[str] = None,
    match_strategies: Optional[List[str]] = None,
    skip_prefixes: Optional[List[str]] = None,
    source_entity_type_slug: Optional[str] = None,
) -> Optional[Entity]:
    """Match an entity to a parent based on name extraction.

    Extracts potential parent names from a string like
    "Gummersbach Teil I - Aggertalsperre" and finds matching entities.

    This is a generic function that can match to any entity type,
    not just Gemeinden.

    Args:
        session: Database session
        name_to_match: Name from API (e.g., "Gummersbach Teil I - Aggertalsperre")
        parent_entity_type_slug: Slug of parent entity type to match against
            (e.g., "territorial_entity", "bundesland", "organization")
        admin_level_1: State/region to narrow search (optional)
        match_strategies: List of strategies to use for extracting names
            Options: "first_word", "before_separator", "full_name", "skip_prefix"
            Default: all strategies
        skip_prefixes: List of prefixes to skip when extracting names (e.g., ["Windpark", "Solarpark"])
            If not provided, will be derived from source_entity_type_slug or be empty
        source_entity_type_slug: Slug of source entity type (used to auto-generate skip_prefixes)

    Returns:
        Matching parent Entity or None
    """
    if not name_to_match or not name_to_match.strip():
        return None

    # Get target entity type
    entity_type_result = await session.execute(
        select(EntityType).where(EntityType.slug == parent_entity_type_slug)
    )
    entity_type = entity_type_result.scalar_one_or_none()
    if not entity_type:
        logger.warning(f"Parent entity type '{parent_entity_type_slug}' not found")
        return None

    # Define default strategies
    if match_strategies is None:
        match_strategies = ["first_word", "before_separator", "full_name", "skip_prefix"]

    # Extract potential parent names from name_to_match
    potential_names = []

    # Build skip_prefixes dynamically if not provided
    if skip_prefixes is None:
        skip_prefixes = []
        # Auto-generate from source entity type name if provided
        if source_entity_type_slug:
            source_type_result = await session.execute(
                select(EntityType).where(EntityType.slug == source_entity_type_slug)
            )
            source_type = source_type_result.scalar_one_or_none()
            if source_type:
                # Add entity type name and common abbreviations as prefixes
                skip_prefixes.append(source_type.name)
                # Also add slug-based variations (e.g., "windpark" -> "Windpark")
                skip_prefixes.append(source_entity_type_slug.replace("-", " ").title())

    words = name_to_match.split()

    # 0. Skip prefix strategy - if name starts with known prefix, use next word(s)
    if "skip_prefix" in match_strategies and len(words) > 1:
        if words[0] in skip_prefixes:
            # "Windpark Gummersbach Teil I" -> "Gummersbach"
            remaining_words = words[1:]
            # Add first word after prefix
            if remaining_words:
                first_after_prefix = remaining_words[0]
                if len(first_after_prefix) > 2 and first_after_prefix not in skip_prefixes:
                    potential_names.append(first_after_prefix)
            # Also try first two words after prefix (for names like "Bad Homburg")
            if len(remaining_words) > 1:
                two_words = f"{remaining_words[0]} {remaining_words[1]}"
                # Exclude if second word is a separator word
                if remaining_words[1] not in ["Teil", "Am", "Bei", "I", "II", "III", "IV", "V"]:
                    potential_names.append(two_words)

    # 1. First word (often the main name) - skip if it's a known prefix
    if "first_word" in match_strategies:
        first_word = words[0] if words else ""
        if first_word and len(first_word) > 2 and first_word not in skip_prefixes:
            potential_names.append(first_word)

    # 2. Part before common separators (Teil, -, Am, Bei, etc.)
    if "before_separator" in match_strategies:
        for separator in [" Teil ", " - ", " Am ", " Bei ", " an ", " im ", " bei ", " (", ":"]:
            if separator in name_to_match:
                part = name_to_match.split(separator)[0].strip()
                if part and part not in potential_names:
                    # Also try stripping prefix from this part
                    part_words = part.split()
                    if part_words and part_words[0] in skip_prefixes and len(part_words) > 1:
                        stripped_part = " ".join(part_words[1:])
                        if stripped_part not in potential_names:
                            potential_names.append(stripped_part)
                    potential_names.append(part)

    # 3. Full name (for simple cases like "Beuron")
    if "full_name" in match_strategies:
        if name_to_match.strip() not in potential_names:
            potential_names.append(name_to_match.strip())

    logger.debug(
        "Parent matching candidates",
        name_to_match=name_to_match,
        parent_type=parent_entity_type_slug,
        candidates=potential_names,
        admin_level_1=admin_level_1,
    )

    # Try each potential name
    for name in potential_names:
        escaped_name = _escape_like_pattern(name)

        # Build query - exact match first
        query = select(Entity).where(
            Entity.entity_type_id == entity_type.id,
            Entity.name.ilike(escaped_name, escape="\\"),
            Entity.is_active.is_(True),
        )

        # Filter by Bundesland if provided
        if admin_level_1:
            query = query.where(Entity.admin_level_1 == admin_level_1)

        result = await session.execute(query.limit(1))
        entity = result.scalar_one_or_none()

        if entity:
            logger.info(
                "Parent match found",
                name_to_match=name_to_match,
                matched_name=name,
                parent_entity=entity.name,
                parent_id=str(entity.id),
                parent_type=parent_entity_type_slug,
            )
            return entity

        # Try partial match (starts with)
        partial_query = select(Entity).where(
            Entity.entity_type_id == entity_type.id,
            Entity.name.ilike(f"{escaped_name}%", escape="\\"),  # Starts with
            Entity.is_active.is_(True),
        )
        if admin_level_1:
            partial_query = partial_query.where(Entity.admin_level_1 == admin_level_1)

        result = await session.execute(partial_query.limit(1))
        entity = result.scalar_one_or_none()

        if entity:
            logger.info(
                "Parent partial match found",
                name_to_match=name_to_match,
                matched_name=name,
                parent_entity=entity.name,
                parent_id=str(entity.id),
                parent_type=parent_entity_type_slug,
            )
            return entity

    logger.debug(
        "No parent match found",
        name_to_match=name_to_match,
        parent_type=parent_entity_type_slug,
        admin_level_1=admin_level_1,
    )
    return None


async def find_or_create_parent_entity(
    session: AsyncSession,
    parent_name: str,
    parent_type_slug: str,
    country: str = "DE",
) -> Optional[Entity]:
    """Find or create a parent entity for hierarchy building.

    Args:
        session: Database session
        parent_name: Name of the parent entity (e.g., "Bayern")
        parent_type_slug: Slug of the parent entity type (e.g., "bundesland")
        country: Country code

    Returns:
        The parent Entity or None if not found/created
    """
    # First try to find existing entity
    entity = await find_entity_by_name(session, parent_name, parent_type_slug)
    if entity:
        return entity

    # Try to create it
    entity, _ = await create_entity_from_command(
        session,
        parent_type_slug,
        {
            "name": parent_name,
            "country": country,
        },
    )
    return entity


async def create_entity_with_hierarchy(
    session: AsyncSession,
    entity_type_slug: str,
    entity_data: Dict[str, Any],
    parent_entity: Optional[Entity] = None,
    explicit_hierarchy_level: Optional[int] = None,
) -> Tuple[Optional[Entity], str]:
    """Create an entity with hierarchy information.

    Args:
        session: Database session
        entity_type_slug: Slug of the entity type
        entity_data: Entity data dict including:
            - name: Entity name
            - country: Country code
            - admin_level_1: State/region
            - admin_level_2: District/county
            - core_attributes: Additional attributes
            - external_id: External ID (e.g., AGS code)
            - latitude/longitude: Coordinates
        parent_entity: Optional parent entity for hierarchy
        explicit_hierarchy_level: Optional explicit hierarchy level to set.
            If provided, overrides the calculated level from parent.
            Use this for bulk imports where level is known (e.g., 1 for Bundesland, 2 for Gemeinde).

    Returns:
        Tuple of (Entity, message)
    """
    name = entity_data.get("name", "").strip()
    if not name:
        return None, "Name ist erforderlich"

    # Get entity type
    entity_type_result = await session.execute(
        select(EntityType).where(EntityType.slug == entity_type_slug)
    )
    entity_type = entity_type_result.scalar_one_or_none()
    if not entity_type:
        return None, f"Entity-Typ '{entity_type_slug}' nicht gefunden"

    # Build hierarchy path and level
    hierarchy_path = None
    hierarchy_level = 0

    # Use explicit hierarchy level if provided
    if explicit_hierarchy_level is not None:
        hierarchy_level = explicit_hierarchy_level

    if parent_entity:
        if parent_entity.hierarchy_path:
            hierarchy_path = f"{parent_entity.hierarchy_path}/{name}"
        else:
            hierarchy_path = f"/{parent_entity.name}/{name}"
        # Only calculate from parent if no explicit level
        if explicit_hierarchy_level is None:
            hierarchy_level = (parent_entity.hierarchy_level or 0) + 1
    elif entity_data.get("country"):
        hierarchy_path = f"/{entity_data['country']}/{name}"
        # Only set default level if no explicit level
        if explicit_hierarchy_level is None:
            hierarchy_level = 1

    # Use centralized service for entity creation
    service = EntityMatchingService(session)

    # Check if entity already exists
    from app.utils.text import normalize_entity_name
    name_normalized = normalize_entity_name(name, entity_data.get("country", "DE"))

    existing_result = await session.execute(
        select(Entity).where(
            Entity.entity_type_id == entity_type.id,
            Entity.name_normalized == name_normalized,
            Entity.is_active.is_(True),
        )
    )
    existing_entity = existing_result.scalar_one_or_none()

    if existing_entity:
        # Update hierarchy info if missing
        if parent_entity and not existing_entity.parent_id:
            existing_entity.parent_id = parent_entity.id
            existing_entity.hierarchy_path = hierarchy_path
            existing_entity.hierarchy_level = hierarchy_level
            await session.flush()
        return existing_entity, f"Entity '{name}' existiert bereits"

    # Create new entity
    entity = await service.get_or_create_entity(
        entity_type_slug=entity_type_slug,
        name=name,
        country=entity_data.get("country", "DE"),
        external_id=entity_data.get("external_id"),
        core_attributes=entity_data.get("core_attributes", {}),
        latitude=entity_data.get("latitude"),
        longitude=entity_data.get("longitude"),
        admin_level_1=entity_data.get("admin_level_1"),
        admin_level_2=entity_data.get("admin_level_2"),
    )

    if entity:
        # Set hierarchy fields
        entity.parent_id = parent_entity.id if parent_entity else None
        entity.hierarchy_path = hierarchy_path
        entity.hierarchy_level = hierarchy_level
        await session.flush()
        return entity, f"Entity '{name}' erstellt"

    return None, f"Entity '{name}' konnte nicht erstellt werden"


async def bulk_create_entities_from_api_data(
    session: AsyncSession,
    entity_type_slug: str,
    items: List[Dict[str, Any]],
    field_mapping: Dict[str, str],
    parent_config: Optional[Dict[str, Any]] = None,
    parent_match_config: Optional[Dict[str, Any]] = None,
    api_config: Optional[Dict[str, Any]] = None,
    progress_callback: Optional[callable] = None,
    hierarchy_level: Optional[int] = None,
    parent_field: Optional[str] = None,
) -> Dict[str, Any]:
    """Bulk create entities from external API data.

    Args:
        session: Database session
        entity_type_slug: Target entity type slug
        items: List of raw data items from API
        field_mapping: Mapping from API fields to entity fields:
            - name: API field for entity name
            - external_id: API field for external ID
            - admin_level_1: API field for state/region
            - admin_level_2: API field for district
            - population: API field for population (core_attributes)
            - area: API field for area (core_attributes)
            - latitude: API field for latitude
            - longitude: API field for longitude
        parent_config: Optional config for parent lookup by direct field:
            - field: API field containing parent name
            - entity_type: Parent entity type slug
            - cache: Dict to cache parent entities
        parent_match_config: Optional config for fuzzy parent matching by name:
            - field: API field containing name for matching (e.g., "areaName")
            - admin_level_field: API field for filtering (e.g., Bundesland)
            - parent_entity_type: Entity type to match against (default: "territorial_entity")
            - match_strategies: List of matching strategies (default: all)
        api_config: Optional API configuration for DataSource creation:
            - template: API template name
            - base_url: API base URL
            - description: API description
        progress_callback: Optional callback(created, total) for progress
        hierarchy_level: Optional explicit hierarchy level to set on all created entities
            (e.g., 1 for Bundesland, 2 for Gemeinde within a hierarchical entity type)
        parent_field: Optional API field containing parent entity name for hierarchical
            linking WITHIN THE SAME entity type. When set, looks up parent by name
            in the same entity_type_slug (not a different type like parent_config).
            Used with hierarchy_level to build proper parent-child relationships.

    Returns:
        Dict with results: created_count, existing_count, errors, entities
    """
    result = {
        "created_count": 0,
        "existing_count": 0,
        "error_count": 0,
        "errors": [],
        "entities": [],
    }

    # Cache for parent entities
    parent_cache: Dict[str, Optional[Entity]] = {}
    if parent_config:
        parent_cache = parent_config.get("cache", {})

    # Cache for hierarchical parent lookup within same entity type
    # This is separate from parent_config which looks in DIFFERENT entity types
    hierarchy_parent_cache: Dict[str, Optional[Entity]] = {}

    # Pre-load existing entities of this type for faster hierarchical parent lookup
    if parent_field:
        entity_type_result = await session.execute(
            select(EntityType).where(EntityType.slug == entity_type_slug)
        )
        entity_type = entity_type_result.scalar_one_or_none()
        if entity_type:
            existing_entities_result = await session.execute(
                select(Entity).where(
                    Entity.entity_type_id == entity_type.id,
                    Entity.is_active.is_(True),
                )
            )
            for entity in existing_entities_result.scalars().all():
                # Cache by exact name (case-insensitive)
                hierarchy_parent_cache[entity.name.lower()] = entity
                # Also cache by normalized name without common suffixes
                if entity.name_normalized:
                    hierarchy_parent_cache[entity.name_normalized.lower()] = entity
            logger.info(
                "Pre-loaded hierarchy parent cache",
                entity_type=entity_type_slug,
                cached_count=len(hierarchy_parent_cache),
            )

    total = len(items)

    for i, item in enumerate(items):
        try:
            # Reset per-item variables
            cross_type_relation_target = None

            # Map fields
            entity_data = {}

            # Name (required) - supports both direct field and template
            name_template = field_mapping.get("name_template")
            name_field = field_mapping.get("name", "label")

            if name_template and "{" in name_template:
                # Use template like "Windpark {auctionId}"
                try:
                    entity_data["name"] = name_template.format(**item).strip()
                except KeyError as e:
                    result["error_count"] += 1
                    result["errors"].append(f"Item {i}: Template field missing: {e}")
                    continue
            else:
                entity_data["name"] = item.get(name_field, "").strip()

            if not entity_data["name"]:
                result["error_count"] += 1
                result["errors"].append(f"Item {i}: Missing name field '{name_field}'")
                continue

            # External ID (always convert to string)
            if "external_id" in field_mapping:
                ext_id = item.get(field_mapping["external_id"])
                entity_data["external_id"] = str(ext_id) if ext_id is not None else None

            # Admin levels
            if "admin_level_1" in field_mapping:
                entity_data["admin_level_1"] = item.get(field_mapping["admin_level_1"])
            if "admin_level_2" in field_mapping:
                entity_data["admin_level_2"] = item.get(field_mapping["admin_level_2"])

            # Country
            entity_data["country"] = field_mapping.get("country", "DE")

            # Coordinates
            if "latitude" in field_mapping and item.get(field_mapping["latitude"]):
                try:
                    entity_data["latitude"] = float(item.get(field_mapping["latitude"]))
                except (ValueError, TypeError):
                    pass
            if "longitude" in field_mapping and item.get(field_mapping["longitude"]):
                try:
                    entity_data["longitude"] = float(item.get(field_mapping["longitude"]))
                except (ValueError, TypeError):
                    pass

            # Core attributes - standard fields
            core_attrs = {}
            if "population" in field_mapping and item.get(field_mapping["population"]):
                try:
                    core_attrs["population"] = int(float(item.get(field_mapping["population"])))
                except (ValueError, TypeError):
                    pass
            if "area" in field_mapping and item.get(field_mapping["area"]):
                try:
                    core_attrs["area_km2"] = float(item.get(field_mapping["area"]))
                except (ValueError, TypeError):
                    pass

            # Custom core attributes - any field not in standard mappings
            standard_fields = {"name", "name_template", "external_id", "admin_level_1", "admin_level_2",
                             "country", "latitude", "longitude", "population", "area", "website"}
            for attr_name, api_field in field_mapping.items():
                if attr_name not in standard_fields and not attr_name.startswith("_"):
                    value = item.get(api_field)
                    if value is not None:
                        core_attrs[attr_name] = value
            entity_data["core_attributes"] = core_attrs

            # Parent lookup
            parent_entity = None
            if parent_config:
                parent_field = parent_config.get("field")
                parent_type = parent_config.get("entity_type")
                parent_name = item.get(parent_field, "").strip() if parent_field else None

                if parent_name:
                    # Check cache
                    cache_key = f"{parent_type}:{parent_name}"
                    if cache_key in parent_cache:
                        parent_entity = parent_cache[cache_key]
                    else:
                        # Find or create parent
                        parent_entity = await find_or_create_parent_entity(
                            session,
                            parent_name,
                            parent_type,
                            entity_data["country"],
                        )
                        parent_cache[cache_key] = parent_entity

                    # Set admin_level_1 from parent if not set
                    if parent_entity and not entity_data.get("admin_level_1"):
                        entity_data["admin_level_1"] = parent_name

            # Fuzzy parent matching by name (if no parent found via parent_config)
            parent_matched = None
            if not parent_entity and parent_match_config:
                match_field = parent_match_config.get("field")
                admin_level_field = parent_match_config.get("admin_level_field")
                parent_entity_type = parent_match_config.get("parent_entity_type", "territorial_entity")
                match_strategies = parent_match_config.get("match_strategies")

                name_to_match = item.get(match_field, "").strip() if match_field else None
                admin_level_1 = item.get(admin_level_field) if admin_level_field else entity_data.get("admin_level_1")

                if name_to_match:
                    # Check cache
                    cache_key = f"parent_match:{parent_entity_type}:{name_to_match}:{admin_level_1}"
                    if cache_key in parent_cache:
                        parent_matched = parent_cache[cache_key]
                    else:
                        # Get skip_prefixes from config or auto-generate from entity type
                        skip_prefixes = parent_match_config.get("skip_prefixes")
                        parent_matched = await match_entity_to_parent_by_name(
                            session,
                            name_to_match,
                            parent_entity_type,
                            admin_level_1,
                            match_strategies,
                            skip_prefixes=skip_prefixes,
                            source_entity_type_slug=entity_type_slug,  # Pass for dynamic prefix generation
                        )
                        parent_cache[cache_key] = parent_matched

                    if parent_matched:
                        # For cross-entity-type matching (e.g., Windpark -> Gemeinde),
                        # we DON'T set parent_entity (that's for same-type hierarchy).
                        # Instead, we track it to create an EntityRelation later.
                        cross_type_relation_target = parent_matched

                        # Track matched parents count
                        if "parents_matched" not in result:
                            result["parents_matched"] = 0
                        result["parents_matched"] += 1

                        # Inherit coordinates from parent if not set
                        if parent_matched.latitude and not entity_data.get("latitude"):
                            entity_data["latitude"] = parent_matched.latitude
                        if parent_matched.longitude and not entity_data.get("longitude"):
                            entity_data["longitude"] = parent_matched.longitude
                        # Inherit admin_level_1 from matched entity
                        if parent_matched.admin_level_1 and not entity_data.get("admin_level_1"):
                            entity_data["admin_level_1"] = parent_matched.admin_level_1

            # Hierarchical parent lookup WITHIN SAME entity type
            # This is for hierarchical entity types where Bundesland and Gemeinde
            # are both in the same entity type (e.g., "territorial-entity")
            hierarchy_parent = None
            if parent_field and not parent_entity:
                parent_name = item.get(parent_field, "").strip() if parent_field else None
                if parent_name:
                    # Try exact match first (case-insensitive)
                    cache_key = parent_name.lower()
                    if cache_key in hierarchy_parent_cache:
                        hierarchy_parent = hierarchy_parent_cache[cache_key]
                    else:
                        # Try to find in database if not in cache
                        # (might have been created earlier in this batch)
                        escaped_name = _escape_like_pattern(parent_name)
                        entity_type_result = await session.execute(
                            select(EntityType).where(EntityType.slug == entity_type_slug)
                        )
                        entity_type = entity_type_result.scalar_one_or_none()
                        if entity_type:
                            parent_query = select(Entity).where(
                                Entity.entity_type_id == entity_type.id,
                                Entity.name.ilike(escaped_name, escape="\\"),
                                Entity.is_active.is_(True),
                            ).limit(1)
                            parent_result = await session.execute(parent_query)
                            hierarchy_parent = parent_result.scalar_one_or_none()
                            # Cache for next lookups
                            hierarchy_parent_cache[cache_key] = hierarchy_parent

                    if hierarchy_parent:
                        parent_entity = hierarchy_parent
                        # Track hierarchical parent matches
                        if "hierarchy_parents_matched" not in result:
                            result["hierarchy_parents_matched"] = 0
                        result["hierarchy_parents_matched"] += 1

                        # Set admin_level_1 from parent name if not set
                        if not entity_data.get("admin_level_1"):
                            entity_data["admin_level_1"] = parent_name

                        logger.debug(
                            "Found hierarchical parent",
                            child_name=entity_data["name"],
                            parent_name=hierarchy_parent.name,
                            parent_id=str(hierarchy_parent.id),
                        )
                    else:
                        logger.warning(
                            "Hierarchical parent not found",
                            child_name=entity_data["name"],
                            parent_field=parent_field,
                            parent_name=parent_name,
                        )

            # Create entity with explicit hierarchy_level if provided
            entity, message = await create_entity_with_hierarchy(
                session,
                entity_type_slug,
                entity_data,
                parent_entity,
                explicit_hierarchy_level=hierarchy_level,
            )

            if entity:
                if "erstellt" in message:
                    result["created_count"] += 1
                    # Add to hierarchy cache for subsequent items in this batch
                    # This allows children to find parents created earlier in the same batch
                    if parent_field:
                        hierarchy_parent_cache[entity.name.lower()] = entity
                        if entity.name_normalized:
                            hierarchy_parent_cache[entity.name_normalized.lower()] = entity
                else:
                    result["existing_count"] += 1

                entity_result = {
                    "id": str(entity.id),
                    "name": entity.name,
                    "status": "created" if "erstellt" in message else "existing",
                    "hierarchy_level": entity.hierarchy_level,
                    "parent_id": str(entity.parent_id) if entity.parent_id else None,
                }

                # Create EntityRelation for cross-entity-type matching (e.g., Windpark -> Gemeinde)
                # Do this for both new and existing entities (relation might not exist yet)
                if cross_type_relation_target:
                    try:
                        relation = await create_located_in_relation(
                            session=session,
                            source_entity=entity,
                            target_entity=cross_type_relation_target,
                        )
                        if relation:
                            entity_result["relation_id"] = str(relation.id)
                            entity_result["located_in"] = cross_type_relation_target.name
                            if "relations_created" not in result:
                                result["relations_created"] = 0
                            result["relations_created"] += 1
                    except Exception as rel_error:
                        logger.warning(
                            "Failed to create located_in relation",
                            source_entity=entity.name,
                            target_entity=cross_type_relation_target.name,
                            error=str(rel_error),
                        )

                # Create DataSource for website if provided
                website_url = None
                data_source_created = False
                if "website" in field_mapping:
                    website_url = item.get(field_mapping["website"], "")
                    if website_url and isinstance(website_url, str) and website_url.startswith("http"):
                        try:
                            data_source = await create_data_source_for_entity(
                                session=session,
                                entity=entity,
                                website_url=website_url,
                                entity_type_slug=entity_type_slug,
                                admin_level_1=entity_data.get("admin_level_1"),
                                country=entity_data.get("country", "DE"),
                            )
                            if data_source:
                                entity_result["data_source_id"] = str(data_source.id)
                                entity_result["data_source_url"] = website_url
                                if "data_sources_created" not in result:
                                    result["data_sources_created"] = 0
                                result["data_sources_created"] += 1
                                data_source_created = True
                        except Exception as ds_error:
                            logger.warning(
                                "Failed to create DataSource for entity",
                                entity_id=str(entity.id),
                                website=website_url,
                                error=str(ds_error),
                            )

                # Create API DataSource if api_config provided and no website DataSource
                if api_config and not data_source_created and "erstellt" in message:
                    try:
                        api_ds = await create_api_data_source_for_entity(
                            session=session,
                            entity=entity,
                            api_config=api_config,
                            entity_type_slug=entity_type_slug,
                            admin_level_1=entity_data.get("admin_level_1"),
                            country=entity_data.get("country", "DE"),
                        )
                        if api_ds:
                            entity_result["data_source_id"] = str(api_ds.id)
                            entity_result["data_source_type"] = "api"
                            if "data_sources_created" not in result:
                                result["data_sources_created"] = 0
                            result["data_sources_created"] += 1
                    except Exception as ds_error:
                        logger.warning(
                            "Failed to create API DataSource for entity",
                            entity_id=str(entity.id),
                            error=str(ds_error),
                        )

                result["entities"].append(entity_result)

            # Progress callback
            if progress_callback and (i + 1) % 100 == 0:
                await progress_callback(i + 1, total)

            # Commit in batches to avoid memory issues
            if (i + 1) % 500 == 0:
                await session.flush()
                logger.info(
                    "Bulk create progress",
                    processed=i + 1,
                    total=total,
                    created=result["created_count"],
                )

        except Exception as e:
            result["error_count"] += 1
            result["errors"].append(f"Item {i}: {str(e)}")
            logger.warning("Bulk create item error", item_index=i, error=str(e))

    # Final flush
    await session.flush()

    logger.info(
        "Bulk create completed",
        entity_type=entity_type_slug,
        created=result["created_count"],
        existing=result["existing_count"],
        errors=result["error_count"],
        data_sources=result.get("data_sources_created", 0),
    )

    return result


async def create_data_source_for_entity(
    session: AsyncSession,
    entity: Entity,
    website_url: str,
    entity_type_slug: str,
    admin_level_1: Optional[str] = None,
    country: str = "DE",
) -> Optional[DataSource]:
    """Create a DataSource for an entity's official website.

    This function creates a DataSource entry for the entity's website,
    links it to the entity via extra_data, and automatically assigns
    appropriate tags and categories.

    Args:
        session: Database session
        entity: The entity to link the DataSource to
        website_url: The official website URL
        entity_type_slug: Entity type slug (e.g., "territorial_entity", "bundesland")
        admin_level_1: State/region name for tagging
        country: Country code

    Returns:
        Created DataSource or None if already exists/error
    """
    from urllib.parse import urlparse

    # Check if DataSource with this URL already exists
    existing = await session.execute(
        select(DataSource).where(DataSource.base_url == website_url)
    )
    if existing.scalar_one_or_none():
        logger.debug("DataSource already exists", url=website_url)
        return None

    # Generate tags based on entity type and location
    tags = []

    # Add entity type tag
    if entity_type_slug:
        tags.append(entity_type_slug)

    # Add location tags
    if admin_level_1:
        # Normalize Bundesland name to slug format
        admin_slug = generate_slug(admin_level_1)
        tags.append(admin_slug)
        tags.append("kommunal")

    # Add country tag
    if country:
        tags.append(country.lower())

    # Determine source type
    source_type = SourceType.WEBSITE

    # Extract domain for name if entity name is not suitable
    parsed_url = urlparse(website_url)
    domain = parsed_url.netloc

    # Create DataSource
    data_source = DataSource(
        name=f"{entity.name} - Offizielle Website",
        source_type=source_type,
        base_url=website_url,
        status=SourceStatus.ACTIVE,
        tags=tags,
        priority=5,  # Medium priority
        crawl_config={
            "max_depth": 3,
            "max_pages": 100,
            "render_javascript": False,
            "include_patterns": [],
            "exclude_patterns": [
                r"/impressum",
                r"/datenschutz",
                r"/login",
            ],
        },
        extra_data={
            "entity_id": str(entity.id),
            "entity_name": entity.name,
            "entity_type": entity_type_slug,
            "admin_level_1": admin_level_1,
            "country": country,
            "source": "wikidata_import",
            "domain": domain,
        },
    )

    session.add(data_source)
    await session.flush()

    # Try to link to an appropriate category
    await link_data_source_to_category(
        session=session,
        data_source=data_source,
        entity_type_slug=entity_type_slug,
        admin_level_1=admin_level_1,
        country=country,
    )

    logger.debug(
        "DataSource created for entity",
        entity_id=str(entity.id),
        entity_name=entity.name,
        data_source_id=str(data_source.id),
        url=website_url,
        tags=tags,
    )

    return data_source


async def create_api_data_source_for_entity(
    session: AsyncSession,
    entity: Entity,
    api_config: Dict[str, Any],
    entity_type_slug: str,
    admin_level_1: Optional[str] = None,
    country: str = "DE",
) -> Optional[DataSource]:
    """Create a DataSource for an entity from an API import.

    This function creates a DataSource entry that tracks the API origin
    of an entity, enabling re-crawling and updates.

    Args:
        session: Database session
        entity: The entity to link the DataSource to
        api_config: API configuration with template, base_url, etc.
        entity_type_slug: Entity type slug
        admin_level_1: State/region name for tagging
        country: Country code

    Returns:
        Created DataSource or None if error
    """
    template_name = api_config.get("template", "")
    base_url = api_config.get("base_url", "")

    # Create unique URL per entity using external_id
    if entity.external_id:
        unique_url = f"{base_url.rstrip('/')}/{entity.external_id}"
    else:
        unique_url = f"{base_url.rstrip('/')}/{entity.slug}"

    # Check if DataSource with this URL already exists
    existing = await session.execute(
        select(DataSource).where(DataSource.base_url == unique_url)
    )
    if existing.scalar_one_or_none():
        logger.debug("API DataSource already exists", url=unique_url)
        return None

    # Generate tags
    tags = [entity_type_slug]
    if template_name:
        tags.append(template_name.replace("_", "-"))
    if admin_level_1:
        tags.append(generate_slug(admin_level_1))
    if country:
        tags.append(country.lower())
    tags.append("api-import")

    # Determine source type
    source_type = SourceType.CUSTOM_API

    # Create DataSource
    data_source = DataSource(
        name=f"{entity.name} - {api_config.get('description', 'API')}",
        source_type=source_type,
        base_url=unique_url,
        status=SourceStatus.ACTIVE,
        tags=tags,
        priority=50,
        crawl_config={
            "api_type": api_config.get("type", "rest"),
            "template": template_name,
            "external_id": entity.external_id,
        },
        extra_data={
            "entity_id": str(entity.id),
            "entity_name": entity.name,
            "entity_type": entity_type_slug,
            "import_source": template_name or "api",
        },
    )

    session.add(data_source)
    await session.flush()

    # Link to category
    await link_data_source_to_category(
        session=session,
        data_source=data_source,
        entity_type_slug=entity_type_slug,
        admin_level_1=admin_level_1,
        country=country,
    )

    logger.debug(
        "API DataSource created for entity",
        entity_id=str(entity.id),
        entity_name=entity.name,
        data_source_id=str(data_source.id),
        url=unique_url,
    )

    return data_source


async def link_data_source_to_category(
    session: AsyncSession,
    data_source: DataSource,
    entity_type_slug: str,
    admin_level_1: Optional[str] = None,
    country: str = "DE",
) -> Optional[Category]:
    """Link a DataSource to an appropriate category.

    Tries to find a matching category based on:
    1. Entity type (e.g., "municipality" -> "kommunale-websites")
    2. Location (e.g., "NRW" -> "ratsinformationen-nrw")
    3. Generic fallback categories

    Args:
        session: Database session
        data_source: The DataSource to link
        entity_type_slug: Entity type slug
        admin_level_1: State/region name
        country: Country code

    Returns:
        Linked Category or None
    """
    # Build list of potential category slugs to try
    potential_slugs = []

    # Try specific regional categories first
    if admin_level_1 and country == "DE":
        admin_slug = generate_slug(admin_level_1)
        # Common patterns for German regional categories
        potential_slugs.extend([
            f"kommunale-websites-{admin_slug}",
            f"kommunal-{admin_slug}",
            f"ratsinformationen-{admin_slug}",
            f"gemeinden-{admin_slug}",
        ])

    # Try entity-type-based categories
    if entity_type_slug:
        potential_slugs.extend([
            f"{entity_type_slug}-websites",
            f"kommunale-{entity_type_slug}",
            entity_type_slug,
        ])

    # Add generic fallbacks
    potential_slugs.extend([
        "kommunale-websites",
        "kommunale-news",
        "ratsinformationen-nrw",  # Most common
    ])

    # Try to find a matching category
    for slug in potential_slugs:
        result = await session.execute(
            select(Category).where(
                Category.slug == slug,
                Category.is_active == True,
            )
        )
        category = result.scalar_one_or_none()

        if category:
            # Check if link already exists
            existing_link = await session.execute(
                select(DataSourceCategory).where(
                    DataSourceCategory.data_source_id == data_source.id,
                    DataSourceCategory.category_id == category.id,
                )
            )
            if not existing_link.scalar_one_or_none():
                # Create the link
                link = DataSourceCategory(
                    data_source_id=data_source.id,
                    category_id=category.id,
                    is_primary=True,
                )
                session.add(link)

                # Also set legacy category_id for backwards compatibility
                data_source.category_id = category.id

                logger.debug(
                    "DataSource linked to category",
                    data_source_id=str(data_source.id),
                    category_slug=slug,
                    category_name=category.name,
                )

                return category

    logger.debug(
        "No matching category found for DataSource",
        data_source_id=str(data_source.id),
        tried_slugs=potential_slugs[:5],
    )

    return None
