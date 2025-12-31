"""
Similarity matching utilities for entity and type deduplication.

This package provides embedding-based similarity matching using OpenAI
text-embedding-3-large vectors with pgvector for efficient semantic
similarity search.

The package is organized into focused modules:
- embedding: Core embedding generation and caching
- concept_matching: Cross-lingual concept normalization
- (Future) entity_search: Entity similarity search functions
- (Future) type_search: Type similarity search functions

For backwards compatibility, all functions are re-exported from the
legacy similarity module.
"""

# =============================================================================
# Core embedding infrastructure (extracted)
# =============================================================================

# =============================================================================
# Legacy imports - Functions not yet migrated to separate modules
# Import from the original file in parent directory
# =============================================================================
# Note: These will be migrated to separate modules in future iterations
# For now, import from the legacy file to maintain backwards compatibility
from ..similarity_legacy import (
    _hierarchy_mapping_cache,  # noqa: F401
    # Internal
    _normalize_type_name,
    batch_update_embeddings,
    batch_update_facet_value_embeddings,
    batch_update_relation_type_embeddings,
    batch_update_type_embeddings,
    check_location_geo_proximity,
    # Config matching
    compute_config_hash,
    find_duplicate_by_config,
    find_duplicate_entity_attachment,
    find_duplicate_location,
    find_entity_type_by_alias,
    find_similar_categories,
    # Entity search
    find_similar_entities,
    find_similar_entity_types,
    find_similar_facet_types,
    find_similar_facet_values,
    find_similar_locations_by_name,
    find_similar_relation_types,
    # Type search
    find_similar_types,
    # Hierarchy
    get_hierarchy_mapping,
    get_hierarchy_mapping_async,
    invalidate_all_similarity_caches,
    # Cache management
    invalidate_hierarchy_cache,
    populate_all_embeddings,
    update_entity_embedding,
    update_facet_value_embedding,
    update_relation_type_embeddings,
    update_type_embedding,
)

# =============================================================================
# Concept matching (extracted)
# =============================================================================
from .concept_matching import (
    _canonical_concept_cache,  # noqa: F401
    _concept_equivalence_cache,  # noqa: F401
    are_concepts_equivalent,
    get_cached_canonical_concept,
    get_canonical_concept,
    invalidate_concept_caches,
)
from .embedding import (
    DEFAULT_SIMILARITY_THRESHOLD,
    EMBEDDING_CACHE_SIZE,
    EMBEDDING_DIMENSIONS,
    SIMILARITY_THRESHOLDS,
    _cosine_similarity,
    clear_embedding_cache,
    cosine_similarity,
    generate_embedding,
    generate_embeddings_batch,
    generate_entity_embedding,
    get_similarity_stats,
    reset_similarity_stats,
)

__all__ = [
    # Constants
    "SIMILARITY_THRESHOLDS",
    "DEFAULT_SIMILARITY_THRESHOLD",
    "EMBEDDING_DIMENSIONS",
    "EMBEDDING_CACHE_SIZE",
    # Stats
    "get_similarity_stats",
    "reset_similarity_stats",
    # Cache management
    "clear_embedding_cache",
    "invalidate_concept_caches",
    "invalidate_hierarchy_cache",
    "invalidate_all_similarity_caches",
    # Core functions
    "generate_embedding",
    "generate_entity_embedding",
    "generate_embeddings_batch",
    "cosine_similarity",
    "_cosine_similarity",
    # Concept matching
    "get_canonical_concept",
    "get_cached_canonical_concept",
    "are_concepts_equivalent",
    # Entity search
    "find_similar_entities",
    "find_similar_locations_by_name",
    "check_location_geo_proximity",
    "find_duplicate_location",
    "find_duplicate_entity_attachment",
    "update_entity_embedding",
    "batch_update_embeddings",
    # Type search
    "find_similar_types",
    "find_similar_entity_types",
    "find_entity_type_by_alias",
    "find_similar_facet_types",
    "find_similar_categories",
    "find_similar_relation_types",
    "find_similar_facet_values",
    "update_type_embedding",
    "update_relation_type_embeddings",
    "update_facet_value_embedding",
    "batch_update_type_embeddings",
    "batch_update_facet_value_embeddings",
    "batch_update_relation_type_embeddings",
    "populate_all_embeddings",
    # Config matching
    "compute_config_hash",
    "find_duplicate_by_config",
    # Hierarchy
    "get_hierarchy_mapping",
    "get_hierarchy_mapping_async",
    "_normalize_type_name",
]
