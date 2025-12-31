/**
 * Generic Facet Components
 *
 * These components provide a dynamic, schema-based rendering system
 * for FacetTypes and FacetValues. They replace hardcoded slug-based
 * templates with a flexible approach that:
 *
 * - Uses FacetType.icon and FacetType.color for visual styling
 * - Reads display configuration from FacetType.value_schema.display
 * - Works with any FacetType without code changes
 */

export { default as GenericFacetValueRenderer } from './GenericFacetValueRenderer.vue'
export { default as GenericFacetCard } from './GenericFacetCard.vue'
