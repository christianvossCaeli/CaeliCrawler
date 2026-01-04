/**
 * Entity Facets Composable
 *
 * This file re-exports from the modular facets composables for backwards compatibility.
 * For new code, consider importing directly from '@/composables/facets'.
 *
 * @see @/composables/facets/index.ts for the modular implementation
 */

// Re-export the facade composable
export { useEntityFacets } from './facets'

// Re-export all types for convenience
export type {
  FacetGroup,
  FacetValue,
  FacetDetail,
  NewFacet,
  FacetSchemaProperty,
  FacetSchema,
  EnrichmentSources,
  EntitySearchResult,
  SourceFacet,
} from './facets'
