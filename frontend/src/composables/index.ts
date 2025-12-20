/**
 * Composables package - Reusable Vue composition functions.
 *
 * This package provides:
 * - useFacetHelpers: Facet value formatting and display utilities
 * - useEntitiesFilters: Entity list filtering state and logic
 * - usePySisHelpers: PySis integration formatting and display utilities
 *
 * These composables were extracted from large view components
 * to improve maintainability and reusability.
 */

export { useFacetHelpers, attributeTranslations, type FacetValue } from './useFacetHelpers'
export {
  useEntitiesFilters,
  facetFilterOptions,
  locationFieldKeys,
  type BasicFilters,
  type LocationOptions,
  type SchemaAttribute,
} from './useEntitiesFilters'
export { usePySisHelpers } from './usePySisHelpers'
export { useAssistant } from './useAssistant'
export { useColorHelpers, isLightColor, getContrastColor } from './useColorHelpers'
