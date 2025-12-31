"""Service for Entity-Facet System integration with AI extraction."""

import re
from datetime import datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    DataSource,
    Entity,
    EntityRelation,
    ExtractedData,
    FacetType,
    FacetValue,
    RelationType,
)
from app.models.facet_value import FacetValueSourceType
from app.utils.text import normalize_name

logger = structlog.get_logger()


async def get_or_create_entity(
    session: AsyncSession,
    entity_type_slug: str,
    name: str,
    external_id: str | None = None,
    parent_id: UUID | None = None,
    core_attributes: dict[str, Any] | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    country: str = "DE",
    similarity_threshold: float = 0.85,
) -> Entity | None:
    """
    Get or create an entity by name and type.

    Delegates to EntityMatchingService for consistent:
    - Name normalization
    - Duplicate detection (with optional fuzzy matching)
    - Race-condition-safe creation

    Args:
        session: Database session
        entity_type_slug: The entity type slug
        name: Entity name
        external_id: Optional external ID
        parent_id: Optional parent entity ID
        core_attributes: Optional JSON attributes
        latitude: Optional latitude
        longitude: Optional longitude
        country: Country code for normalization (default: DE)
        similarity_threshold: Threshold for fuzzy matching (default: 0.85, set to 1.0 for exact only)

    Returns:
        Entity if found or created, None if entity_type not found.
    """
    from services.entity_matching_service import EntityMatchingService

    service = EntityMatchingService(session)
    return await service.get_or_create_entity(
        entity_type_slug=entity_type_slug,
        name=name,
        country=country,
        external_id=external_id,
        core_attributes=core_attributes,
        parent_id=parent_id,
        latitude=latitude,
        longitude=longitude,
        similarity_threshold=similarity_threshold,
    )


async def get_facet_type_by_slug(session: AsyncSession, slug: str) -> FacetType | None:
    """Get facet type by slug."""
    result = await session.execute(
        select(FacetType).where(FacetType.slug == slug, FacetType.is_active.is_(True))
    )
    return result.scalar_one_or_none()



async def classify_facet_type_with_ai(
    session: AsyncSession,
    field_name: str,
    sample_data: Any = None,
) -> str | None:
    """
    Use AI (gpt-4.1-mini) to classify which existing FacetType best matches a field.

    This is used as an additional classification strategy when similarity matching
    is uncertain or returns low confidence scores.

    Args:
        session: Database session
        field_name: The field name to classify
        sample_data: Optional sample data to provide context

    Returns:
        The slug of the best matching FacetType, or None if no good match
    """
    from sqlalchemy import select

    from services.ai_service import AIService

    try:
        # Get all active FacetTypes
        stmt = select(FacetType).where(FacetType.is_active.is_(True))
        result = await session.execute(stmt)
        facet_types = result.scalars().all()

        if not facet_types:
            return None

        # Build description of available FacetTypes
        type_descriptions = []
        for ft in facet_types:
            desc = f"- {ft.slug}: {ft.name}"
            if ft.description:
                desc += f" ({ft.description})"
            type_descriptions.append(desc)

        types_text = "\n".join(type_descriptions)

        # Build sample data description if available
        sample_desc = ""
        if sample_data:
            if isinstance(sample_data, dict):
                keys = list(sample_data.keys())[:5]
                sample_desc = f"\nBeispiel-Felder: {', '.join(keys)}"
            elif isinstance(sample_data, list) and sample_data:
                first = sample_data[0]
                if isinstance(first, dict):
                    keys = list(first.keys())[:5]
                    sample_desc = f"\nBeispiel-Felder: {', '.join(keys)}"

        prompt = f"""Analysiere diesen Feldnamen aus einer Datenextraktion und bestimme,
ob er zu einem existierenden FacetType passt.

Feldname: "{field_name}"{sample_desc}

Verfügbare FacetTypes:
{types_text}

Antwort:
- Falls ein FacetType gut passt: Antworte NUR mit dem slug (z.B. "pain_point")
- Falls kein FacetType passt: Antworte NUR mit "NONE"

Nur den slug oder "NONE" ausgeben, keine Erklärung."""

        ai_service = AIService()
        response = await ai_service.generate_text(
            prompt=prompt,
            max_tokens=50,
            temperature=0.1,  # Low temperature for consistent results
        )

        if not response:
            return None

        # Parse response
        result_slug = response.strip().lower().strip('"\'')

        if result_slug == "none" or not result_slug:
            return None

        # Validate that the slug exists
        valid_slugs = {ft.slug for ft in facet_types}
        if result_slug in valid_slugs:
            logger.info(
                "AI classified FacetType",
                field_name=field_name,
                classified_slug=result_slug,
            )
            return result_slug

        return None

    except Exception as e:
        logger.warning(
            "AI FacetType classification failed",
            field_name=field_name,
            error=str(e),
        )
        return None


async def emit_facet_type_created_notification(
    facet_type: FacetType,
    created_from_field: str,
) -> None:
    """
    Emit notification event when a new FacetType is auto-created.

    This allows admins to review auto-created FacetTypes.
    """
    try:
        from workers.notification_tasks import emit_event

        emit_event.delay(
            "FACET_TYPE_AUTO_CREATED",
            {
                "facet_type_id": str(facet_type.id),
                "facet_type_slug": facet_type.slug,
                "facet_type_name": facet_type.name,
                "created_from_field": created_from_field,
                "needs_review": True,
                "message": f"Neuer FacetType '{facet_type.name}' wurde automatisch erstellt für Feld '{created_from_field}'",
            }
        )

        logger.info(
            "Emitted FACET_TYPE_AUTO_CREATED notification",
            facet_type_slug=facet_type.slug,
            created_from_field=created_from_field,
        )
    except Exception as e:
        logger.warning(
            "Failed to emit FacetType creation notification",
            error=str(e),
        )

def _infer_value_schema_from_data(data: Any) -> dict[str, Any]:
    """
    Infer a JSON schema from sample data.

    This creates a basic schema that can be used for the FacetType's value_schema.
    The schema includes display hints for the frontend.
    """
    if data is None:
        return {"type": "object", "properties": {}}

    if isinstance(data, str):
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string"}
            },
            "display": {
                "primary_field": "text",
                "layout": "inline"
            }
        }

    if isinstance(data, (int, float)):
        return {
            "type": "object",
            "properties": {
                "value": {"type": "number"}
            },
            "display": {
                "primary_field": "value",
                "layout": "inline"
            }
        }

    if isinstance(data, list):
        # For arrays, infer from first element if present
        if data and isinstance(data[0], dict):
            return _infer_value_schema_from_data(data[0])
        return {
            "type": "array",
            "items": {"type": "string"}
        }

    if isinstance(data, dict):
        properties = {}
        chip_fields = []
        primary_field = None

        for key, value in data.items():
            if value is None:
                properties[key] = {"type": "string", "nullable": True}
            elif isinstance(value, str):
                properties[key] = {"type": "string"}
                # Heuristics for display
                if key in ("description", "text", "aenderungen", "beschreibung"):
                    primary_field = key
                elif key in ("typ", "type", "ausweisung_typ", "status", "severity"):
                    chip_fields.append(key)
            elif isinstance(value, bool):
                properties[key] = {"type": "boolean"}
            elif isinstance(value, int):
                properties[key] = {"type": "integer"}
                if key.endswith("_ha") or key.endswith("_km2") or "flaeche" in key or "anzahl" in key:
                    chip_fields.append(key)
            elif isinstance(value, float):
                properties[key] = {"type": "number"}
                if key.endswith("_ha") or key.endswith("_km2") or "flaeche" in key:
                    chip_fields.append(key)
            elif isinstance(value, list):
                properties[key] = {"type": "array", "items": {"type": "string"}}
            elif isinstance(value, dict):
                properties[key] = {"type": "object"}

        # Auto-detect primary field if not found
        if not primary_field:
            for candidate in ["description", "text", "name", "title", "aenderungen", "beschreibung", "inhalt"]:
                if candidate in properties:
                    primary_field = candidate
                    break
            if not primary_field and properties:
                primary_field = list(properties.keys())[0]

        return {
            "type": "object",
            "properties": properties,
            "display": {
                "primary_field": primary_field or "description",
                "chip_fields": chip_fields[:4],  # Max 4 chips
                "layout": "card"
            }
        }

    return {"type": "object", "properties": {}}


def _humanize_field_name(field_name: str) -> str:
    """
    Convert a snake_case field name to a human-readable name.

    Examples:
        - "flaechenausweisung" → "Flächenausweisung"
        - "pain_points" → "Pain Points"
        - "decision_makers" → "Decision Makers"
    """
    # German-specific replacements
    replacements = {
        "ae": "ä",
        "oe": "ö",
        "ue": "ü",
        "ss": "ß",
    }

    # Split on underscores
    words = field_name.split("_")

    # Capitalize each word
    result = []
    for word in words:
        # Apply German replacements if it looks German
        german_word = word.lower()
        for old, new in replacements.items():
            # Only apply if it makes sense (not at word boundaries that would create invalid German)
            german_word = german_word.replace(old, new)

        # Capitalize first letter
        if german_word:
            result.append(german_word[0].upper() + german_word[1:])

    return " ".join(result)


def _pluralize_name(name: str) -> str:
    """
    Create a simple plural form of a name.
    Handles basic German and English patterns.
    """
    if not name:
        return name

    # Already plural
    if name.endswith("s") or name.endswith("en") or name.endswith("er"):
        return name

    # German patterns
    if name.endswith("ung"):
        return name + "en"
    if name.endswith("heit") or name.endswith("keit"):
        return name + "en"
    if name.endswith("e"):
        return name + "n"

    # Default: add 's'
    return name + "s"


async def get_or_create_facet_type(
    session: AsyncSession,
    field_name: str,
    sample_data: Any = None,
    similarity_threshold: float = 0.8,
    auto_create: bool = True,
    use_ai_classification: bool = True,
) -> FacetType | None:
    """
    Get or create a FacetType based on a field name from extracted content.

    This function enables dynamic FacetType creation based on AI-extracted data:
    1. First tries to find an existing FacetType by exact slug match
    2. Then tries semantic similarity matching against existing FacetType names
    3. Optionally uses AI (gpt-4.1-mini) to classify uncertain matches
    4. Falls back to hardcoded mappings
    5. If not found and auto_create is True, creates a new FacetType

    When a new FacetType is created:
    - It is marked with needs_review=True in metadata
    - An admin notification is emitted

    The value_schema is inferred from the sample_data structure.

    Args:
        session: Database session
        field_name: The field name from extracted_content (e.g., "flaechenausweisung")
        sample_data: Sample data to infer the value schema from
        similarity_threshold: Threshold for semantic similarity matching (default: 0.8)
        auto_create: Whether to create new FacetType if not found (default: True)
        use_ai_classification: Whether to use AI for classification (default: True)

    Returns:
        FacetType if found or created, None if not found and auto_create is False
    """
    from app.utils.similarity import find_similar_facet_types, generate_embedding

    # Generate slug from field name
    slug = field_name.lower().replace(" ", "_")
    slug = re.sub(r'[^a-z0-9_]', '', slug)
    slug = re.sub(r'_+', '_', slug).strip('_')

    # 1. Try exact slug match first
    existing = await get_facet_type_by_slug(session, slug)
    if existing:
        logger.debug("Found FacetType by slug", slug=slug, facet_type_id=str(existing.id))
        return existing

    # 2. Try similarity matching against existing FacetType names
    similarity_match = None
    similarity_score = 0.0
    try:
        matches = await find_similar_facet_types(session, field_name, threshold=similarity_threshold)
        if matches:
            similarity_match, similarity_score, _ = matches[0]

            # High confidence match
            if similarity_score >= 0.9:
                logger.info(
                    "Found similar FacetType (high confidence)",
                    field_name=field_name,
                    matched_slug=similarity_match.slug,
                    similarity=round(similarity_score, 3),
                )
                return similarity_match
    except Exception as e:
        logger.warning("Similarity search failed", field_name=field_name, error=str(e))

    # 3. For medium confidence matches, use AI classification to confirm
    if use_ai_classification and similarity_match and 0.7 <= similarity_score < 0.9:
        ai_classified_slug = await classify_facet_type_with_ai(
            session, field_name, sample_data
        )
        if ai_classified_slug:
            # AI confirmed a match
            if ai_classified_slug == similarity_match.slug:
                logger.info(
                    "AI confirmed similarity match",
                    field_name=field_name,
                    matched_slug=ai_classified_slug,
                )
                return similarity_match
            else:
                # AI suggests different type
                ai_type = await get_facet_type_by_slug(session, ai_classified_slug)
                if ai_type:
                    logger.info(
                        "AI classified to different FacetType",
                        field_name=field_name,
                        similarity_suggested=similarity_match.slug,
                        ai_classified=ai_classified_slug,
                    )
                    return ai_type
        else:
            # AI says no match, but we had medium confidence similarity
            # Still return similarity match if score is reasonable
            if similarity_score >= 0.8:
                return similarity_match

    # 4. No AI classification or low confidence - try AI as primary classifier
    if use_ai_classification and not similarity_match:
        ai_classified_slug = await classify_facet_type_with_ai(
            session, field_name, sample_data
        )
        if ai_classified_slug:
            ai_type = await get_facet_type_by_slug(session, ai_classified_slug)
            if ai_type:
                logger.info(
                    "AI classified FacetType",
                    field_name=field_name,
                    ai_classified=ai_classified_slug,
                )
                return ai_type

    # 5. Check fallback mappings
    fallback_slug = FALLBACK_FIELD_MAPPINGS.get(field_name.lower())
    if fallback_slug:
        fallback_type = await get_facet_type_by_slug(session, fallback_slug)
        if fallback_type:
            logger.debug("Found FacetType via fallback mapping", field_name=field_name, slug=fallback_slug)
            return fallback_type

    # 6. Create new FacetType if allowed
    if not auto_create:
        logger.debug("No FacetType found and auto_create is False", field_name=field_name)
        return None

    # Infer schema from sample data
    value_schema = _infer_value_schema_from_data(sample_data) if sample_data else {
        "type": "object",
        "properties": {},
        "display": {"primary_field": "text", "layout": "card"}
    }

    # Create human-readable name
    name = _humanize_field_name(field_name)
    name_plural = _pluralize_name(name)

    # Generate embedding for future similarity matching
    embedding = await generate_embedding(f"{name}: {field_name}")

    # Determine value_type based on data
    if isinstance(sample_data, list):
        value_type = "list"
    elif isinstance(sample_data, str):
        value_type = "text"
    else:
        value_type = "structured"

    # Create the FacetType with needs_review flag
    new_facet_type = FacetType(
        slug=slug,
        name=name,
        name_plural=name_plural,
        name_embedding=embedding,
        description=f"Automatisch erstellt für Feld '{field_name}'. Bitte überprüfen.",
        value_type=value_type,
        value_schema=value_schema,
        applicable_entity_type_slugs=["territorial_entity"],  # Default to territorial entities
        icon="mdi-tag-outline",
        color="#607D8B",  # Default grey-blue
        ai_extraction_enabled=True,
        is_active=True,
        is_system=False,
        needs_review=True,  # Mark for admin review
    )

    session.add(new_facet_type)
    await session.flush()

    logger.info(
        "Created new FacetType (needs review)",
        slug=slug,
        name=name,
        field_name=field_name,
        value_type=value_type,
        facet_type_id=str(new_facet_type.id),
        needs_review=True,
    )

    # Emit admin notification
    await emit_facet_type_created_notification(new_facet_type, field_name)

    return new_facet_type


async def create_facet_value(
    session: AsyncSession,
    entity_id: UUID,
    facet_type_id: UUID,
    value: dict[str, Any],
    text_representation: str,
    confidence_score: float = 0.5,
    source_document_id: UUID | None = None,
    source_url: str | None = None,
    event_date: datetime | None = None,
    source_type: FacetValueSourceType = FacetValueSourceType.DOCUMENT,
    target_entity_id: UUID | None = None,
    facet_type: FacetType | None = None,
    resolve_entity_reference: bool = True,
) -> FacetValue | None:
    """Create a new facet value with optional entity reference resolution.

    Args:
        session: Database session
        entity_id: UUID of the entity
        facet_type_id: UUID of the facet type
        value: Structured value dict
        text_representation: Human-readable text representation
        confidence_score: Confidence score (0-1)
        source_document_id: Optional source document UUID
        source_url: Optional source URL
        event_date: Optional event date
        source_type: How this value was created (default: DOCUMENT for AI extraction)
        target_entity_id: Optional pre-resolved target entity UUID
        facet_type: Optional FacetType for entity reference resolution
        resolve_entity_reference: Whether to auto-resolve entity references (default: True)

    Returns:
        Created FacetValue, or None if duplicate was detected by database constraint
    """
    from sqlalchemy.exc import IntegrityError

    # Auto-resolve entity reference if configured
    resolved_target_entity_id = target_entity_id
    if resolve_entity_reference and not target_entity_id and facet_type and facet_type.allows_entity_reference:
        from services.entity_matching_service import EntityMatchingService
        matching_service = EntityMatchingService(session)
        resolved_target_entity_id = await matching_service.resolve_target_entity_for_facet(
            facet_type=facet_type,
            facet_value_data=value,
            source_entity_id=entity_id,
        )

    facet_value = FacetValue(
        entity_id=entity_id,
        facet_type_id=facet_type_id,
        value=value,
        text_representation=text_representation[:2000] if text_representation else "",
        confidence_score=confidence_score,
        source_document_id=source_document_id,
        source_url=source_url,
        event_date=event_date,
        source_type=source_type,
        target_entity_id=resolved_target_entity_id,
    )
    session.add(facet_value)

    try:
        await session.flush()

        # Generate embedding for semantic similarity search
        from app.utils.similarity import generate_embedding
        embedding = await generate_embedding(text_representation)
        if embedding:
            facet_value.text_embedding = embedding

        return facet_value
    except IntegrityError as e:
        # Duplicate detected by database unique index - rollback and return None
        if "ix_facet_values_dedup" in str(e):
            await session.rollback()
            logger.debug(
                "Duplicate facet value prevented by database",
                entity_id=str(entity_id),
                facet_type_id=str(facet_type_id),
                text_preview=text_representation[:50] if text_representation else "",
            )
            return None
        raise  # Re-raise if it's a different IntegrityError  # Re-raise if it's a different IntegrityError


async def check_duplicate_facet(
    session: AsyncSession,
    entity_id: UUID,
    facet_type_id: UUID,
    text_representation: str,
    similarity_threshold: float = 0.9,
) -> bool:
    """
    Check if a similar facet value already exists.

    Uses simple string matching for now. Could be enhanced with embeddings.
    """
    # Normalize for comparison
    normalized = normalize_name(text_representation)

    # Get existing facet values for this entity and type
    result = await session.execute(
        select(FacetValue).where(
            FacetValue.entity_id == entity_id,
            FacetValue.facet_type_id == facet_type_id,
        )
    )
    existing = result.scalars().all()

    for fv in existing:
        existing_normalized = normalize_name(fv.text_representation or "")
        # Simple substring check
        if normalized in existing_normalized or existing_normalized in normalized:
            return True
        # Check for high similarity (Jaccard-like)
        if len(normalized) > 10 and len(existing_normalized) > 10:
            set1 = set(normalized.split())
            set2 = set(existing_normalized.split())
            if set1 and set2:
                intersection = len(set1 & set2)
                union = len(set1 | set2)
                if union > 0 and intersection / union >= similarity_threshold:
                    return True

    return False


# Fallback mapping for critical fields when similarity matching fails
FALLBACK_FIELD_MAPPINGS = {
    "pain_points": "pain_point",
    "concerns_raised": "pain_point",
    "positive_signals": "positive_signal",
    "opportunities": "positive_signal",
    "decision_makers": "contact",
    "contacts": "contact",
    "summary": "summary",
    "summaries": "summary",
}


async def get_facet_type_for_field(
    session: AsyncSession,
    field_name: str,
    threshold: float = 0.7,
) -> FacetType | None:
    """
    Find the matching FacetType for an extracted_content field using similarity.

    Uses embedding-based similarity matching via find_similar_facet_types().
    Falls back to FALLBACK_FIELD_MAPPINGS if similarity matching fails.

    Examples:
        - "pain_points" → FacetType "pain_point" (similarity: 0.95)
        - "concerns_raised" → FacetType "pain_point" (similarity: 0.85)
        - "opportunities" → FacetType "positive_signal" (similarity: 0.82)

    Args:
        session: Database session
        field_name: The field name from extracted_content (e.g., "pain_points")
        threshold: Minimum similarity threshold (default: 0.7)

    Returns:
        The matching FacetType or None if no match found
    """
    from app.utils.similarity import find_similar_facet_types

    # Try similarity-based matching first
    try:
        matches = await find_similar_facet_types(
            session,
            field_name,
            threshold=threshold,
        )
        if matches:
            best_match, similarity_score, _ = matches[0]
            logger.debug(
                "Similarity-based FacetType match",
                field_name=field_name,
                facet_type_slug=best_match.slug,
                similarity=round(similarity_score, 3),
            )
            return best_match
    except Exception as e:
        logger.warning(
            "Similarity matching failed, using fallback",
            field_name=field_name,
            error=str(e),
        )

    # Fallback to hardcoded mapping
    fallback_slug = FALLBACK_FIELD_MAPPINGS.get(field_name.lower())
    if fallback_slug:
        facet_type = await get_facet_type_by_slug(session, fallback_slug)
        if facet_type:
            logger.debug(
                "Fallback FacetType match",
                field_name=field_name,
                facet_type_slug=fallback_slug,
            )
            return facet_type

    logger.debug("No FacetType match found", field_name=field_name)
    return None


async def convert_extraction_to_facets(
    session: AsyncSession,
    extracted_data: ExtractedData,
    source: DataSource | None = None,
) -> dict[str, int]:
    """
    Convert ExtractedData to FacetValues in the Entity-Facet system.

    This is a generic implementation that:
    1. Iterates over ALL fields in extracted_content
    2. Finds or creates matching FacetTypes dynamically
    3. Creates FacetValues with appropriate structure

    Metadata fields (municipality, source_location, etc.) are skipped.

    Returns dict with counts of created facet values per type.
    """
    content = extracted_data.final_content
    if not content:
        return {}

    # Determine municipality name from AI extraction
    municipality_name = (
        content.get("municipality")
        or content.get("source_location")
    )

    if not municipality_name or municipality_name.lower() in ("", "unbekannt", "null"):
        logger.debug("No municipality name found, skipping facet creation")
        return {}

    # Get or create territorial entity (municipality/city/town)
    entity = await get_or_create_entity(
        session,
        entity_type_slug="territorial_entity",
        name=municipality_name,
    )
    if not entity:
        return {}

    base_confidence = extracted_data.confidence_score or 0.5
    counts: dict[str, int] = {}

    # Metadata fields to skip (not actual facet data)
    SKIP_FIELDS = {
        "municipality", "source_location", "source_region", "source_admin_level_1",
        "region", "landkreis", "bundesland", "land", "country",
        "document_type", "relevance", "relevance_score", "confidence",
        "extraction_date", "processing_notes", "raw_text",
    }

    # Process each field in extracted_content
    for field_name, field_value in content.items():
        # Skip metadata fields
        if field_name.lower() in SKIP_FIELDS:
            continue

        # Skip empty values
        if field_value is None:
            continue
        if isinstance(field_value, (list, dict)) and not field_value:
            continue
        if isinstance(field_value, str) and len(field_value.strip()) < 5:
            continue

        # Get or create FacetType for this field
        facet_type = await get_or_create_facet_type(
            session,
            field_name=field_name,
            sample_data=field_value,
            auto_create=True,
        )

        if not facet_type:
            logger.warning("Could not get or create FacetType", field_name=field_name)
            continue

        # Initialize counter for this type
        if facet_type.slug not in counts:
            counts[facet_type.slug] = 0

        # Get display config for text representation extraction
        display_config = (facet_type.value_schema or {}).get("display", {})
        primary_field = display_config.get("primary_field", "description")

        # Process based on value type
        if isinstance(field_value, list):
            # Array of values
            for item in field_value:
                created = await _process_single_facet_value(
                    session=session,
                    entity=entity,
                    facet_type=facet_type,
                    value=item,
                    primary_field=primary_field,
                    base_confidence=base_confidence,
                    source_document_id=extracted_data.document_id,
                )
                if created:
                    counts[facet_type.slug] += 1

        elif isinstance(field_value, dict):
            # Single structured value
            created = await _process_single_facet_value(
                session=session,
                entity=entity,
                facet_type=facet_type,
                value=field_value,
                primary_field=primary_field,
                base_confidence=base_confidence,
                source_document_id=extracted_data.document_id,
            )
            if created:
                counts[facet_type.slug] += 1

        elif isinstance(field_value, str):
            # Simple text value
            text = field_value.strip()
            if len(text) >= 10:
                # Check for duplicates
                is_dupe = await check_duplicate_facet(
                    session, entity.id, facet_type.id, text
                )
                if not is_dupe:
                    await create_facet_value(
                        session,
                        entity_id=entity.id,
                        facet_type_id=facet_type.id,
                        value={"text": text},
                        text_representation=text[:500],
                        confidence_score=base_confidence,
                        source_document_id=extracted_data.document_id,
                        facet_type=facet_type,
                    )
                    counts[facet_type.slug] += 1

        elif isinstance(field_value, (int, float)):
            # Numeric value - wrap in object
            value_obj = {"value": field_value}
            text_repr = f"{field_name}: {field_value}"

            await create_facet_value(
                session,
                entity_id=entity.id,
                facet_type_id=facet_type.id,
                value=value_obj,
                text_representation=text_repr,
                confidence_score=base_confidence,
                source_document_id=extracted_data.document_id,
                facet_type=facet_type,
            )
            counts[facet_type.slug] += 1

    logger.info(
        "Created facet values from extraction",
        entity_id=str(entity.id),
        entity_name=municipality_name,
        counts=counts,
        total=sum(counts.values()),
    )

    return counts


async def _process_single_facet_value(
    session: AsyncSession,
    entity: Entity,
    facet_type: FacetType,
    value: Any,
    primary_field: str,
    base_confidence: float,
    source_document_id: UUID | None,
) -> bool:
    """
    Process a single facet value (from array or single object).

    Returns True if value was created, False if skipped (duplicate, invalid, etc.)
    """
    # Handle string values
    if isinstance(value, str):
        text = value.strip()
        if len(text) < 10:
            return False

        is_dupe = await check_duplicate_facet(
            session, entity.id, facet_type.id, text
        )
        if is_dupe:
            return False

        await create_facet_value(
            session,
            entity_id=entity.id,
            facet_type_id=facet_type.id,
            value={"text": text, "description": text},
            text_representation=text[:500],
            confidence_score=base_confidence,
            source_document_id=source_document_id,
            facet_type=facet_type,
            resolve_entity_reference=True,
        )
        return True

    # Handle dict values
    if isinstance(value, dict):
        # Extract text representation from common fields
        text_repr = _extract_text_representation(value, primary_field)

        if not text_repr or len(text_repr) < 3:
            # Try to create a representation from all non-null values
            parts = []
            for k, v in value.items():
                if v is not None and isinstance(v, (str, int, float)):
                    parts.append(f"{k}: {v}")
            text_repr = "; ".join(parts[:3]) if parts else str(value)[:100]

        if len(text_repr) < 3:
            return False

        # Check for duplicates using primary text
        is_dupe = await check_duplicate_facet(
            session, entity.id, facet_type.id, text_repr
        )
        if is_dupe:
            return False

        await create_facet_value(
            session,
            entity_id=entity.id,
            facet_type_id=facet_type.id,
            value=value,
            text_representation=text_repr[:500],
            confidence_score=min(0.95, base_confidence + 0.05),
            source_document_id=source_document_id,
            facet_type=facet_type,
            resolve_entity_reference=True,
        )
        return True

    return False


def _extract_text_representation(value: dict[str, Any], primary_field: str) -> str:
    """
    Extract the best text representation from a value dict.

    Tries primary_field first, then common field names.
    """
    # Try primary field
    if primary_field and primary_field in value:
        text = value[primary_field]
        if isinstance(text, str) and text:
            return text.strip()

    # Try common field names in order of preference
    candidates = [
        "description", "text", "name", "title", "content",
        "beschreibung", "bezeichnung", "aenderungen", "inhalt",
        "summary", "zusammenfassung", "message", "nachricht",
    ]

    for field in candidates:
        if field in value:
            text = value[field]
            if isinstance(text, str) and text:
                return text.strip()

    # Try first non-null string field
    for _k, v in value.items():
        if isinstance(v, str) and len(v) > 10:
            return v.strip()

    return ""


# =============================================================================
# Relation Functions (shared between services)
# =============================================================================


async def get_relation_type_by_slug(
    session: AsyncSession, slug: str
) -> RelationType | None:
    """Get relation type by slug.

    Args:
        session: Database session
        slug: Relation type slug (e.g., 'attends', 'works_for', 'located_in')

    Returns:
        RelationType if found and active, None otherwise
    """
    result = await session.execute(
        select(RelationType).where(
            RelationType.slug == slug, RelationType.is_active.is_(True)
        )
    )
    return result.scalar_one_or_none()


async def create_relation(
    session: AsyncSession,
    source_entity_id: UUID,
    target_entity_id: UUID,
    relation_type_id: UUID,
    attributes: dict[str, Any] | None = None,
    source_document_id: UUID | None = None,
    confidence_score: float = 0.5,
) -> EntityRelation | None:
    """Create a relation between two entities if it doesn't exist.

    Args:
        session: Database session
        source_entity_id: UUID of the source entity
        target_entity_id: UUID of the target entity
        relation_type_id: UUID of the relation type
        attributes: Optional dict of additional attributes
        source_document_id: Optional source document UUID
        confidence_score: Confidence score (0-1)

    Returns:
        EntityRelation (existing or newly created)
    """
    # Check for existing relation
    result = await session.execute(
        select(EntityRelation).where(
            EntityRelation.source_entity_id == source_entity_id,
            EntityRelation.target_entity_id == target_entity_id,
            EntityRelation.relation_type_id == relation_type_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    relation = EntityRelation(
        source_entity_id=source_entity_id,
        target_entity_id=target_entity_id,
        relation_type_id=relation_type_id,
        attributes=attributes or {},
        source_document_id=source_document_id,
        confidence_score=confidence_score,
    )
    session.add(relation)
    return relation
