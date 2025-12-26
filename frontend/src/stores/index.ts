/**
 * Stores Index
 *
 * Central export point for all Pinia stores.
 * Allows convenient imports: import { useEntityStore, useEntityTypesStore } from '@/stores'
 */

// Main entity store (contains all entity-related functionality)
export { useEntityStore } from './entity'
export type {
  EntityType,
  Entity,
  EntityBrief,
  FacetType,
  FacetValue,
  RelationType,
  EntityRelation,
  AnalysisTemplate,
  FacetConfig,
  AggregationConfig,
  DisplayConfig,
  AnalysisOverviewItem,
  EntityFacetsSummary,
  FacetValueAggregated,
  EntityReport,
} from './entity'

// Specialized stores (for modular usage)
export { useEntityTypesStore } from './entityTypes'
export type { EntityType as EntityTypeDefinition } from './entityTypes'

export { useFacetTypesStore } from './facetTypes'
export type {
  FacetType as FacetTypeDefinition,
  FacetSchemaGenerationRequest,
  FacetSchemaGenerationResponse,
} from './facetTypes'

// Auth store
export { useAuthStore } from './auth'
export type { User, UserRole } from './auth'
