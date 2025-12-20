"""Entity, Facet, and Relation operations for Smart Query Service."""

import unicodedata
import uuid as uuid_module
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Entity,
    EntityType,
    FacetType,
    FacetValue,
    RelationType,
    EntityRelation,
)
from .utils import generate_slug


async def create_entity_type_from_command(
    session: AsyncSession,
    entity_type_data: Dict[str, Any],
) -> Tuple[Optional[EntityType], str]:
    """Create a new entity type from smart query command."""
    name = entity_type_data.get("name", "").strip()
    if not name:
        return None, "Name ist erforderlich"

    slug = generate_slug(name)

    # Check for duplicates
    existing = await session.execute(
        select(EntityType).where(
            or_(EntityType.name == name, EntityType.slug == slug)
        )
    )
    if existing.scalar():
        return None, f"Entity-Typ '{name}' existiert bereits"

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
        supports_hierarchy=entity_type_data.get("supports_hierarchy", False),
        hierarchy_config=entity_type_data.get("hierarchy_config"),
        attribute_schema=entity_type_data.get("attribute_schema"),
        display_order=10,  # Default order
        is_active=True,
        is_system=False,
    )
    session.add(entity_type)
    await session.flush()

    return entity_type, f"Entity-Typ '{name}' erstellt"


async def find_entity_by_name(
    session: AsyncSession,
    name: str,
    entity_type_slug: Optional[str] = None,
) -> Optional[Entity]:
    """Find an entity by name (case-insensitive)."""
    query = select(Entity).where(
        Entity.name.ilike(f"%{name}%"),
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


async def create_entity_from_command(
    session: AsyncSession,
    entity_type_slug: str,
    entity_data: Dict[str, Any],
) -> Tuple[Optional[Entity], str]:
    """Create a new entity from smart query command."""
    # Get entity type
    entity_type_result = await session.execute(
        select(EntityType).where(EntityType.slug == entity_type_slug)
    )
    entity_type = entity_type_result.scalar_one_or_none()
    if not entity_type:
        return None, f"Entity-Typ '{entity_type_slug}' nicht gefunden"

    name = entity_data.get("name", "").strip()
    if not name:
        return None, "Name ist erforderlich"

    slug = generate_slug(name)

    # Check for duplicates
    existing = await session.execute(
        select(Entity).where(
            Entity.entity_type_id == entity_type.id,
            or_(Entity.name == name, Entity.slug == slug),
        )
    )
    if existing.scalar():
        return None, f"Entity '{name}' existiert bereits"

    # Create entity
    name_normalized = unicodedata.normalize("NFKD", name.lower())
    entity = Entity(
        id=uuid_module.uuid4(),
        entity_type_id=entity_type.id,
        name=name,
        name_normalized=name_normalized,
        slug=slug,
        external_id=entity_data.get("external_id"),
        hierarchy_path=f"/{slug}",
        hierarchy_level=0,
        core_attributes=entity_data.get("core_attributes", {}),
        is_active=True,
    )
    session.add(entity)
    await session.flush()

    return entity, f"Entity '{name}' ({entity_type.name}) erstellt"


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
        confidence_score=0.9,  # Smart Query entry = high confidence
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

    return relation, f"Relation '{source_entity.name}' → '{target_entity.name}' ({relation_type.name}) erstellt"
