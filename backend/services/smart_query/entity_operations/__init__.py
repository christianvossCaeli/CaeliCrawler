"""Entity operations module for Smart Query Service.

This module provides functions for:
- EntityType creation and lookup
- Entity CRUD operations
- Facet and Relation creation
- Location coordinate lookup
- Hierarchy operations
- Data source operations

All functions are re-exported from specialized sub-modules for backwards compatibility.
"""

# Re-export everything from the base module for backwards compatibility
# This allows gradual migration to the modular structure
from services.smart_query.entity_operations.base import (
    # Constants
    DEFAULT_ENTITY_TYPE_ORDER,
    SMART_QUERY_CONFIDENCE_SCORE,
    # EntityType operations
    create_entity_type_from_command,
    # Entity lookup/creation
    find_entity_by_name,
    create_entity_from_command,
    # Facet/Relation operations
    create_facet_from_command,
    create_relation_from_command,
    # Location operations
    lookup_location_coordinates,
    create_located_in_relation,
    # Hierarchy operations
    match_entity_to_parent_by_name,
    find_or_create_parent_entity,
    create_entity_with_hierarchy,
    # Data source operations
    bulk_create_entities_from_api_data,
    create_data_source_for_entity,
    create_api_data_source_for_entity,
    link_data_source_to_category,
)

__all__ = [
    # Constants
    "SMART_QUERY_CONFIDENCE_SCORE",
    "DEFAULT_ENTITY_TYPE_ORDER",
    # EntityType operations
    "create_entity_type_from_command",
    # Entity lookup/creation
    "find_entity_by_name",
    "create_entity_from_command",
    # Facet/Relation operations
    "create_facet_from_command",
    "create_relation_from_command",
    # Location operations
    "lookup_location_coordinates",
    "create_located_in_relation",
    # Hierarchy operations
    "match_entity_to_parent_by_name",
    "find_or_create_parent_entity",
    "create_entity_with_hierarchy",
    # Data source operations
    "bulk_create_entities_from_api_data",
    "create_data_source_for_entity",
    "create_api_data_source_for_entity",
    "link_data_source_to_category",
]
