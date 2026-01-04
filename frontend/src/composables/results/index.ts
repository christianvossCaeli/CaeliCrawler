/**
 * Results Module - Facade Export
 *
 * Provides a unified API for the Results/Extracted Data module.
 * Combines state, filters, actions, and helpers into a single composable.
 */

import { useFacetTypeRenderer } from '@/composables/useFacetTypeRenderer'
import { useResultsState } from './useResultsState'
import { useResultsFilters } from './useResultsFilters'
import { useResultsActions } from './useResultsActions'
import { useResultsHelpers } from './useResultsHelpers'

// =============================================================================
// Re-exports
// =============================================================================

// Types
export type {
  EntityReference,
  SignalItem,
  DecisionMaker,
  OutreachRecommendation,
  ExtractedContent,
  SearchResult,
  TableHeader,
  TableOptions,
  SortOrder,
  SortConfig,
  ResultsStats,
  ResultsFilterState,
  DynamicContentField,
  CategoryOption,
} from './types'

// Constants
export {
  CONFIDENCE_THRESHOLDS,
  CONFIDENCE_COLORS,
  SEVERITY_COLORS,
  SEVERITY_ICONS,
  PRIORITY_COLORS,
  SENTIMENT_COLORS,
  ENTITY_TYPE_CONFIG,
  DEFAULT_ENTITY_CONFIG,
  RESERVED_CONTENT_FIELDS,
  CHIP_DISPLAY_FIELDS,
  FIELD_ICONS,
  FIELD_COLORS,
  DEFAULT_FIELD_ICON,
  DEFAULT_FIELD_COLOR,
  RESULTS_PAGINATION,
  EXPORT_CONFIG,
} from './constants'

// Utility function
export { normalizeResultItem } from './types'

// Individual composables (for selective imports)
export { useResultsState } from './useResultsState'
export { useResultsFilters } from './useResultsFilters'
export { useResultsActions } from './useResultsActions'
export { useResultsHelpers } from './useResultsHelpers'

// =============================================================================
// Main Composable
// =============================================================================

/**
 * Main Results composable that combines all functionality.
 *
 * Usage:
 * ```ts
 * const results = useResults()
 *
 * // Access state
 * results.state.results.value
 * results.state.loading.value
 *
 * // Use filters
 * results.filters.loadData()
 * results.filters.clearFilters()
 *
 * // Use actions
 * results.actions.verifyResult(item)
 * results.actions.exportCsv()
 *
 * // Use helpers
 * results.helpers.getConfidenceColor(0.85)
 * results.helpers.formatDate(dateStr)
 * ```
 */
export function useResults() {
  // Initialize state first (shared across all sub-composables)
  const state = useResultsState()

  // Initialize sub-composables with shared state
  const filters = useResultsFilters(state)
  const actions = useResultsActions(state)
  const helpers = useResultsHelpers()

  // FacetType renderer for generic facet display
  const { getValuesForFacetType, hasValues } = useFacetTypeRenderer()

  return {
    // Grouped exports for clean API
    state,
    filters,
    actions,
    helpers,

    // FacetType helpers
    getValuesForFacetType,
    hasValues,
  }
}

// =============================================================================
// Flat Composable (backwards compatible with useResultsView)
// =============================================================================

/**
 * Flat API matching the original useResultsView interface.
 * Use this for backwards compatibility or simpler access patterns.
 *
 * @deprecated Prefer useResults() for new code
 */
export function useResultsView() {
  const { state, filters, actions, helpers, getValuesForFacetType, hasValues } = useResults()

  return {
    // State (flat)
    ...state,

    // Helpers
    getConfidenceColor: helpers.getConfidenceColor,
    getSeverityColor: helpers.getSeverityColor,
    getSeverityIcon: helpers.getSeverityIcon,
    getSentimentColor: helpers.getSentimentColor,
    getPriorityColor: helpers.getPriorityColor,
    getEntityTypeColor: helpers.getEntityTypeColor,
    getEntityTypeIcon: helpers.getEntityTypeIcon,
    getContent: helpers.getContent,
    getEntityReferencesByType: helpers.getEntityReferencesByType,
    getPrimaryEntityRef: helpers.getPrimaryEntityRef,
    formatDate: helpers.formatDate,
    getDynamicContentFields: helpers.getDynamicContentFields,
    getValueText: helpers.getValueText,
    formatFieldLabel: helpers.formatFieldLabel,

    // Filters
    loadData: filters.loadData,
    loadFilters: filters.loadFilters,
    loadFacetTypesForCategory: filters.loadFacetTypesForCategory,
    debouncedLoadData: filters.debouncedLoadData,
    toggleVerifiedFilter: filters.toggleVerifiedFilter,
    clearFilters: filters.clearFilters,
    filterByEntityReference: filters.filterByEntityReference,
    onTableOptionsUpdate: filters.onTableOptionsUpdate,
    initialize: filters.initialize,

    // Actions
    showDetails: actions.showDetails,
    verifyResult: actions.verifyResult,
    bulkVerify: actions.bulkVerify,
    exportJson: actions.exportJson,
    exportCsv: actions.exportCsv,
    copyToClipboard: actions.copyToClipboard,

    // FacetType helpers
    getValuesForFacetType,
    hasValues,
  }
}
