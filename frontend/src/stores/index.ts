/**
 * Stores Index
 *
 * Central export point for all Pinia stores.
 * Allows convenient imports: import { useEntityStore, useFacetStore } from '@/stores'
 */

// Main entity store (core entities + backwards compatibility proxies)
export { useEntityStore } from './entity'

// Modular sub-stores (recommended for new code)
export { useFacetStore } from './facet'
export { useRelationStore } from './relation'
export { useAnalysisStore } from './analysis'

// All types from central location
export type {
  EntityType,
  Entity,
  EntityBrief,
  FacetType,
  FacetValue,
  FacetValueAggregated,
  EntityFacetsSummary,
  RelationType,
  EntityRelation,
  AnalysisTemplate,
  AnalysisOverviewItem,
  EntityReport,
  FacetConfig,
  AggregationConfig,
  DisplayConfig,
} from './types/entity'

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

// LLM Usage store
export { useLLMUsageStore } from './llmUsage'
