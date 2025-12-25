"""Assistant Service - Common Utilities and Shared Configuration.

This module contains shared utilities, constants, and client initialization
that are used across the assistant service modules.

Exports:
    - get_openai_client: Azure OpenAI client factory
    - validate_entity_context: Validate entity ID and context
    - build_suggestions_list: Build smart suggestions from results
"""

from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import structlog
from openai import AzureOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models import Entity
from app.schemas.assistant import SuggestedAction

logger = structlog.get_logger()

# Global Azure OpenAI client (lazily initialized)
_client: Optional[AzureOpenAI] = None


def get_openai_client() -> Optional[AzureOpenAI]:
    """Get or initialize the Azure OpenAI client.

    Returns:
        AzureOpenAI client instance or None if not configured
    """
    global _client

    if _client is None and settings.azure_openai_api_key:
        _client = AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint,
        )

    return _client


async def validate_entity_context(
    db: AsyncSession,
    entity_id: str,
    with_facets: bool = False
) -> Optional[Entity]:
    """Validate entity ID and load entity with optional relationships.

    Args:
        db: Database session
        entity_id: Entity ID to validate
        with_facets: Whether to load facets

    Returns:
        Entity instance or None if not found/invalid
    """
    try:
        # Validate UUID format
        uuid_id = UUID(entity_id)
    except (ValueError, TypeError, AttributeError) as e:
        logger.warning("invalid_entity_id", entity_id=entity_id, error=str(e))
        return None

    # Build query with optional eager loading
    query = select(Entity).where(Entity.id == uuid_id)
    query = query.options(selectinload(Entity.entity_type))

    result = await db.execute(query)
    return result.scalar_one_or_none()


def build_suggestions_list(
    total: int,
    has_data: bool,
    entity_type: Optional[str] = None,
    facet_types: Optional[List[Any]] = None,
    translator: Optional[Any] = None
) -> List[SuggestedAction]:
    """Build contextual suggested actions based on results.

    Args:
        total: Total number of results
        has_data: Whether results have data
        entity_type: Optional entity type for suggestions
        facet_types: Optional list of facet types for suggestions
        translator: Optional translator instance

    Returns:
        List of suggested actions
    """
    suggestions = []

    if has_data and total > 0:
        label = translator.t("show_details") if translator else "Details anzeigen"
        suggestions.append(SuggestedAction(
            label=label,
            action="query",
            value="Zeig mir mehr Details" if not translator or translator.language == "de" else "Show more details"
        ))

    if facet_types:
        for ft in facet_types[:2]:
            name_plural = getattr(ft, 'name_plural', None) or getattr(ft, 'name', 'Facets')
            suggestions.append(SuggestedAction(
                label=name_plural,
                action="query",
                value=f"Zeige {name_plural}" if entity_type else name_plural
            ))

    label = translator.t("new_search") if translator else "Neue Suche"
    suggestions.append(SuggestedAction(
        label=label,
        action="query",
        value="/search "
    ))

    return suggestions


def format_count_message(
    total: int,
    entity_type: Optional[str] = None,
    translator: Optional[Any] = None
) -> str:
    """Format a count message for query results.

    Args:
        total: Number of results
        entity_type: Optional entity type name
        translator: Optional translator instance

    Returns:
        Formatted message string
    """
    if total == 0:
        return translator.t("no_results") if translator else "Keine Ergebnisse gefunden."

    entity_label = entity_type or ("Einträge" if not translator or translator.language == "de" else "entries")

    if total == 1:
        return f"1 {entity_label} gefunden."

    return f"{total} {entity_label} gefunden."


async def get_entity_with_context(
    db: AsyncSession,
    entity_id: str
) -> Optional[Dict[str, Any]]:
    """Get entity with full context data for AI processing.

    Loads entity with:
    - Entity type
    - Core attributes
    - Location data

    Args:
        db: Database session
        entity_id: Entity ID string

    Returns:
        Dict with entity context data or None if not found
    """
    entity = await validate_entity_context(db, entity_id)
    if not entity:
        return None

    return {
        "id": str(entity.id),
        "name": entity.name,
        "slug": entity.slug,
        "type": entity.entity_type.slug if entity.entity_type else None,
        "type_name": entity.entity_type.name if entity.entity_type else "Unbekannt",
        "core_attributes": entity.core_attributes or {},
        "location": {
            "country": entity.country,
            "admin_level_1": entity.admin_level_1,
            "admin_level_2": entity.admin_level_2,
        }
    }


class EntityNotFoundException(Exception):
    """Raised when entity is not found or invalid."""
    pass


class AIServiceNotAvailableException(Exception):
    """Raised when Azure OpenAI is not configured."""
    pass
