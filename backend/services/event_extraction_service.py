"""Service for processing Event extraction results into Entity-Facet system.

This service handles the specialized extraction of event-related data,
creating Event entities, Person entities for attendees, and the relationships
between them. It uses the extraction_handler="event" category setting.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    EntityType,
    ExtractedData,
    DataSource,
    Category,
)
from services.entity_facet_service import (
    get_or_create_entity,
    get_facet_type_by_slug,
    create_facet_value,
    check_duplicate_facet,
    get_relation_type_by_slug,
    create_relation,
)

logger = structlog.get_logger()


class EventExtractionError(Exception):
    """Raised when event extraction encounters a configuration error."""
    pass


async def process_event_extraction(
    session: AsyncSession,
    extracted_data: ExtractedData,
    source: Optional[DataSource] = None,
    category: Optional[Category] = None,
) -> Dict[str, int]:
    """
    Process event extraction results into Entity-Facet system.

    Creates:
    - Event entity (uses category.target_entity_type if set, else standard "event")
    - Person entities for attendees (always uses standard "person" EntityType)
    - event_attendance FacetValues for persons
    - Relations (attends, works_for, located_in)

    Args:
        session: Database session
        extracted_data: ExtractedData with event content
        source: Optional DataSource for metadata
        category: Optional Category for entity type configuration

    Returns:
        Dict with counts of created items:
        - events: Number of event entities created
        - persons: Number of person entities created
        - event_attendances: Number of attendance facet values created
        - relations: Number of relations created

    Note:
        Returns empty counts dict if:
        - extracted_data has no content
        - No event data in extraction
        - Required relation/facet types not configured in database
    """
    content = extracted_data.final_content
    if not content:
        logger.debug(
            "Empty content in extraction",
            extraction_id=str(extracted_data.id),
        )
        return {}

    counts = {
        "events": 0,
        "persons": 0,
        "event_attendances": 0,
        "relations": 0,
    }

    # Get relation types
    attends_type = await get_relation_type_by_slug(session, "attends")
    works_for_type = await get_relation_type_by_slug(session, "works_for")
    located_in_type = await get_relation_type_by_slug(session, "located_in")
    event_attendance_facet = await get_facet_type_by_slug(session, "event_attendance")

    if not attends_type or not event_attendance_facet:
        missing = []
        if not attends_type:
            missing.append("RelationType 'attends'")
        if not event_attendance_facet:
            missing.append("FacetType 'event_attendance'")

        logger.error(
            "Required types not found for event processing - run seed script",
            missing_types=missing,
            extraction_id=str(extracted_data.id),
            hint="Run: python scripts/seed_entity_facet_system.py",
        )
        return counts

    # Extract event data
    event_data = content.get("event", {})
    if not event_data or not event_data.get("event_name"):
        logger.debug("No event data found in extraction")
        return counts

    # Parse event date
    event_date_str = event_data.get("event_date")
    event_date = None
    if event_date_str:
        try:
            event_date = datetime.fromisoformat(event_date_str.replace("Z", "+00:00"))
        except ValueError:
            try:
                event_date = datetime.strptime(event_date_str, "%Y-%m-%d")
            except ValueError:
                pass

    # Check if future event
    is_future = content.get("is_future_event", False)
    if event_date:
        is_future = event_date.date() >= datetime.now().date()

    # Determine which EntityType to use for the event
    # If category has a target_entity_type_id, use that; otherwise use standard "event"
    event_entity_type_slug = "event"
    if category and category.target_entity_type_id:
        # Load the target entity type to get its slug
        target_type = await session.get(EntityType, category.target_entity_type_id)
        if target_type:
            event_entity_type_slug = target_type.slug
            logger.info(
                "Using custom EntityType for events",
                category=category.slug,
                entity_type=event_entity_type_slug,
            )

    # Create Event entity
    event_entity = await get_or_create_entity(
        session,
        entity_type_slug=event_entity_type_slug,
        name=event_data.get("event_name"),
        core_attributes={
            "event_type": event_data.get("event_type"),
            "venue": event_data.get("event_venue"),
            "url": event_data.get("event_url"),
            "description": event_data.get("event_description"),
            "start_date": event_date_str,
            "end_date": event_data.get("event_end_date"),
            "is_future": is_future,
        },
    )

    if not event_entity:
        logger.warning("Could not create event entity")
        return counts

    counts["events"] = 1
    logger.info(
        "Created/found event entity",
        event_id=str(event_entity.id),
        event_name=event_entity.name,
        is_future=is_future,
    )

    # Link event to location (municipality) if known
    event_location = event_data.get("event_location")
    if event_location and located_in_type:
        location_entity = await get_or_create_entity(
            session,
            entity_type_slug="municipality",
            name=event_location,
        )
        if location_entity:
            await create_relation(
                session,
                source_entity_id=event_entity.id,
                target_entity_id=location_entity.id,
                relation_type_id=located_in_type.id,
                source_document_id=extracted_data.document_id,
                confidence_score=0.8,
            )
            counts["relations"] += 1

    # Process attendees
    attendees = content.get("attendees", [])
    base_confidence = extracted_data.confidence_score or 0.5

    for attendee in attendees if isinstance(attendees, list) else []:
        if not isinstance(attendee, dict):
            continue

        person_name = attendee.get("name", "").strip()
        if not person_name or len(person_name) < 3:
            continue

        # Create Person entity
        person_entity = await get_or_create_entity(
            session,
            entity_type_slug="person",
            name=person_name,
            core_attributes={
                "position": attendee.get("position"),
                "organization": attendee.get("organization"),
            },
        )

        if not person_entity:
            continue

        counts["persons"] += 1

        # Create event_attendance FacetValue for the person
        attendance_text = f"{event_entity.name}"
        if attendee.get("role"):
            attendance_text += f" ({attendee.get('role')})"

        # Check for duplicate attendance
        is_dupe = await check_duplicate_facet(
            session,
            person_entity.id,
            event_attendance_facet.id,
            attendance_text,
        )

        if not is_dupe:
            await create_facet_value(
                session,
                entity_id=person_entity.id,
                facet_type_id=event_attendance_facet.id,
                value={
                    "event_name": event_entity.name,
                    "event_date": event_date_str,
                    "event_location": event_location,
                    "role": attendee.get("role"),
                    "topic": attendee.get("topic"),
                    "confirmed": True,
                    "source": source.name if source else None,
                },
                text_representation=attendance_text,
                confidence_score=min(0.95, base_confidence + 0.05),
                source_document_id=extracted_data.document_id,
                event_date=event_date,
            )
            counts["event_attendances"] += 1

        # Create "attends" relation
        await create_relation(
            session,
            source_entity_id=person_entity.id,
            target_entity_id=event_entity.id,
            relation_type_id=attends_type.id,
            attributes={
                "role": attendee.get("role"),
                "topic": attendee.get("topic"),
                "session_time": attendee.get("session_time"),
            },
            source_document_id=extracted_data.document_id,
            confidence_score=base_confidence,
        )
        counts["relations"] += 1

        # Link person to municipality if they represent one
        municipality_name = attendee.get("municipality") or (
            attendee.get("organization")
            if attendee.get("organization_type") in ("Gemeinde", "Stadt", "Landkreis")
            else None
        )

        if municipality_name and works_for_type:
            municipality_entity = await get_or_create_entity(
                session,
                entity_type_slug="municipality",
                name=municipality_name,
            )
            if municipality_entity:
                await create_relation(
                    session,
                    source_entity_id=person_entity.id,
                    target_entity_id=municipality_entity.id,
                    relation_type_id=works_for_type.id,
                    attributes={
                        "position": attendee.get("position"),
                    },
                    source_document_id=extracted_data.document_id,
                    confidence_score=base_confidence,
                )
                counts["relations"] += 1

    logger.info(
        "Processed event extraction",
        event_name=event_entity.name,
        counts=counts,
    )

    return counts


async def convert_event_extraction_to_facets(
    session: AsyncSession,
    extracted_data: ExtractedData,
    source: Optional[DataSource] = None,
    category: Optional[Category] = None,
) -> Dict[str, int]:
    """
    Wrapper to process event extractions.
    Called from ai_tasks.py for event category documents.

    If category has a target_entity_type_id, events will be created
    with that EntityType instead of the standard "event" type.
    """
    return await process_event_extraction(session, extracted_data, source, category)
