"""
Entity API Endpoints

This module provides CRUD operations and retrieval endpoints for entities.
The endpoints are organized into logical groups:

- CRUD: list_entities, create_entity, get_entity, update_entity, delete_entity
- Retrieval: get_entity_by_slug, get_entity_brief, get_entity_hierarchy, get_entity_children
- Filters: get_location_filter_options, get_attribute_filter_options
- Relationships: get_entity_documents, get_entity_sources, get_entity_external_data
- Geo: get_entities_geojson

All endpoints are re-exported from _core.py for backward compatibility.
"""

from ._core import (
    router,
    list_entities,
    create_entity,
    get_entity,
    get_entity_by_slug,
    update_entity,
    delete_entity,
    get_entity_brief,
    get_entity_hierarchy,
    get_entity_children,
    get_location_filter_options,
    get_attribute_filter_options,
    get_entity_documents,
    get_entity_sources,
    get_entity_external_data,
    get_entities_geojson,
)

__all__ = [
    "router",
    # CRUD
    "list_entities",
    "create_entity",
    "get_entity",
    "get_entity_by_slug",
    "update_entity",
    "delete_entity",
    # Retrieval
    "get_entity_brief",
    "get_entity_hierarchy",
    "get_entity_children",
    # Filters
    "get_location_filter_options",
    "get_attribute_filter_options",
    # Relationships
    "get_entity_documents",
    "get_entity_sources",
    "get_entity_external_data",
    # Geo
    "get_entities_geojson",
]
