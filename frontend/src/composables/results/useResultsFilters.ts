/**
 * Results Filters Composable
 *
 * Handles filter actions and data loading for the Results module.
 */

import { watch } from 'vue'
import { useRoute } from 'vue-router'
import { dataApi, adminApi, facetApi } from '@/services/api'
import type { ExtractedDataParams, ExtractionStatsParams } from '@/services/api/sources'
import { useDebounce, DEBOUNCE_DELAYS } from '@/composables/useDebounce'
import { useLogger } from '@/composables/useLogger'
import { useSnackbar } from '@/composables/useSnackbar'
import { useI18n } from 'vue-i18n'
import type { ResultsState } from './useResultsState'
import type { TableOptions } from './types'

// =============================================================================
// Composable
// =============================================================================

export function useResultsFilters(state: ResultsState) {
  const logger = useLogger('useResultsFilters')
  const { t } = useI18n()
  const route = useRoute()
  const { showError } = useSnackbar()

  // Request counter for race condition handling
  let requestCounter = 0

  // ===========================================================================
  // Data Loading
  // ===========================================================================

  /**
   * Load results data with current filters and pagination.
   */
  async function loadData(): Promise<void> {
    const requestId = ++requestCounter
    state.loading.value = true

    try {
      // Build query params
      const params: ExtractedDataParams = {
        page: state.page.value,
        per_page: state.perPage.value,
      }

      if (state.searchQuery.value) params.search = state.searchQuery.value
      if (state.extractionTypeFilter.value) params.extraction_type = state.extractionTypeFilter.value
      if (state.categoryFilter.value) params.category_id = state.categoryFilter.value
      if (state.minConfidence.value > 0) params.min_confidence = state.minConfidence.value / 100
      if (state.verifiedFilter.value !== null) params.human_verified = state.verifiedFilter.value
      if (state.dateFrom.value) params.created_from = state.dateFrom.value
      if (state.dateTo.value) params.created_to = state.dateTo.value
      if (state.sortBy.value.length > 0) {
        params.sort_by = state.sortBy.value[0].key
        params.sort_order = state.sortBy.value[0].order
      }

      // Build stats params (same filters, no pagination)
      const statsParams: ExtractionStatsParams = {}
      if (state.searchQuery.value) statsParams.search = state.searchQuery.value
      if (state.extractionTypeFilter.value) statsParams.extraction_type = state.extractionTypeFilter.value
      if (state.categoryFilter.value) statsParams.category_id = state.categoryFilter.value
      if (state.minConfidence.value > 0) statsParams.min_confidence = state.minConfidence.value / 100
      if (state.verifiedFilter.value !== null) statsParams.human_verified = state.verifiedFilter.value
      if (state.dateFrom.value) statsParams.created_from = state.dateFrom.value
      if (state.dateTo.value) statsParams.created_to = state.dateTo.value

      // Fetch data and stats in parallel
      const [dataRes, statsRes] = await Promise.all([
        dataApi.getExtractedData(params),
        dataApi.getExtractionStats(statsParams),
      ])

      // Check for race condition
      if (requestId !== requestCounter) return

      // Update state
      state.results.value = dataRes.data.items
      state.totalResults.value = dataRes.data.total
      state.stats.value = statsRes.data

      // Update extraction types from stats
      if (statsRes.data.by_type) {
        state.extractionTypes.value = Object.keys(statsRes.data.by_type)
      }
    } catch (error) {
      if (requestId !== requestCounter) return
      logger.error('Failed to load data:', error)
      showError(t('results.messages.errorLoading'))
    } finally {
      if (requestId === requestCounter) {
        state.loading.value = false
        state.initialLoad.value = false
      }
    }
  }

  /**
   * Load filter options (locations, categories).
   */
  async function loadFilters(): Promise<void> {
    try {
      const [locationsRes, categoriesRes] = await Promise.all([
        dataApi.getExtractionLocations(),
        adminApi.getCategories(),
      ])
      state.locations.value = locationsRes.data
      state.categories.value = categoriesRes.data.items || categoriesRes.data
    } catch (error) {
      logger.error('Failed to load filters:', error)
    }
  }

  /**
   * Load FacetTypes for the selected category.
   */
  async function loadFacetTypesForCategory(): Promise<void> {
    if (!state.categoryFilter.value) {
      state.facetTypes.value = []
      return
    }

    state.facetTypesLoading.value = true
    try {
      const response = await facetApi.getFacetTypesForCategory(state.categoryFilter.value, {
        ai_extraction_enabled: true,
        is_active: true,
      })
      state.facetTypes.value = response.data || []
      logger.debug(`Loaded ${state.facetTypes.value.length} FacetTypes for category`)
    } catch (error) {
      logger.error('Failed to load FacetTypes for category:', error)
      state.facetTypes.value = []
    } finally {
      state.facetTypesLoading.value = false
    }
  }

  // Watch category changes to reload FacetTypes
  watch(() => state.categoryFilter.value, loadFacetTypesForCategory)

  // ===========================================================================
  // Debounced Load
  // ===========================================================================

  const { debouncedFn: debouncedLoadData } = useDebounce(
    () => loadData(),
    { delay: DEBOUNCE_DELAYS.SEARCH }
  )

  // ===========================================================================
  // Filter Actions
  // ===========================================================================

  /**
   * Toggle verified filter (true/false/null).
   */
  function toggleVerifiedFilter(value: boolean): void {
    state.verifiedFilter.value = state.verifiedFilter.value === value ? null : value
    state.page.value = 1
    loadData()
  }

  /**
   * Clear all filters and reset to defaults.
   */
  function clearFilters(): void {
    state.searchQuery.value = ''
    state.locationFilter.value = null
    state.extractionTypeFilter.value = null
    state.categoryFilter.value = null
    state.minConfidence.value = 0
    state.verifiedFilter.value = null
    state.dateFrom.value = null
    state.dateTo.value = null
    state.page.value = 1
    loadData()
  }

  /**
   * Filter by entity reference name.
   */
  function filterByEntityReference(_entityType: string, entityName: string): void {
    state.searchQuery.value = entityName
    state.page.value = 1
    loadData()
  }

  /**
   * Handle table options update (pagination, sorting).
   */
  function onTableOptionsUpdate(options: TableOptions): void {
    state.page.value = options.page
    state.perPage.value = options.itemsPerPage
    if (options.sortBy && options.sortBy.length > 0) {
      state.sortBy.value = options.sortBy
    }
    loadData()
  }

  // ===========================================================================
  // Initialization
  // ===========================================================================

  /**
   * Initialize the module with URL params and load initial data.
   */
  async function initialize(): Promise<void> {
    // Check for verified filter from URL
    if (route.query.verified !== undefined) {
      state.verifiedFilter.value = route.query.verified === 'true'
    }

    // Load data and filters in parallel
    await Promise.all([loadData(), loadFilters()])
  }

  // ===========================================================================
  // Return
  // ===========================================================================

  return {
    // Data Loading
    loadData,
    loadFilters,
    loadFacetTypesForCategory,
    debouncedLoadData,

    // Filter Actions
    toggleVerifiedFilter,
    clearFilters,
    filterByEntityReference,
    onTableOptionsUpdate,

    // Initialization
    initialize,
  }
}
