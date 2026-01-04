/**
 * Results State Composable
 *
 * Centralized reactive state for the Results module.
 * Provides all refs and computed properties.
 */

import { ref, computed, type Ref, type ComputedRef } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { RESULTS_PAGINATION } from './constants'
import type {
  SearchResult,
  ResultsStats,
  TableHeader,
  CategoryOption,
  SortConfig,
} from './types'
import type { FacetType } from '@/types/entity'

// =============================================================================
// State Interface
// =============================================================================

export interface ResultsState {
  // Loading
  loading: Ref<boolean>
  initialLoad: Ref<boolean>
  bulkVerifying: Ref<boolean>

  // Data
  results: Ref<SearchResult[]>
  totalResults: Ref<number>
  locations: Ref<string[]>
  categories: Ref<CategoryOption[]>
  extractionTypes: Ref<string[]>
  selectedResults: Ref<string[]>
  stats: Ref<ResultsStats>

  // FacetTypes
  facetTypes: Ref<FacetType[]>
  facetTypesLoading: Ref<boolean>

  // Filters
  searchQuery: Ref<string>
  locationFilter: Ref<string | null>
  extractionTypeFilter: Ref<string | null>
  categoryFilter: Ref<string | null>
  minConfidence: Ref<number>
  verifiedFilter: Ref<boolean | null>
  dateFrom: Ref<string | null>
  dateTo: Ref<string | null>

  // Pagination
  page: Ref<number>
  perPage: Ref<number>
  sortBy: Ref<SortConfig[]>

  // Dialog
  detailsDialog: Ref<boolean>
  selectedResult: Ref<SearchResult | null>

  // Headers
  headers: Ref<TableHeader[]>

  // Computed
  showLocationFilter: ComputedRef<boolean>
  hasActiveFilters: ComputedRef<boolean>
  canVerify: ComputedRef<boolean>
}

// =============================================================================
// Composable
// =============================================================================

export function useResultsState(): ResultsState {
  const { t } = useI18n()
  const auth = useAuthStore()

  // ===========================================================================
  // Loading State
  // ===========================================================================

  const loading = ref(true)
  const initialLoad = ref(true)
  const bulkVerifying = ref(false)

  // ===========================================================================
  // Data
  // ===========================================================================

  const results = ref<SearchResult[]>([])
  const totalResults = ref(0)
  const locations = ref<string[]>([])
  const categories = ref<CategoryOption[]>([])
  const extractionTypes = ref<string[]>([])
  const selectedResults = ref<string[]>([])

  const stats = ref<ResultsStats>({
    total: 0,
    verified: 0,
    unverified: 0,
    avg_confidence: null,
    high_confidence_count: 0,
    low_confidence_count: 0,
  })

  // ===========================================================================
  // FacetTypes (for category-specific display)
  // ===========================================================================

  const facetTypes = ref<FacetType[]>([])
  const facetTypesLoading = ref(false)

  // ===========================================================================
  // Filters
  // ===========================================================================

  const searchQuery = ref('')
  const locationFilter = ref<string | null>(null)
  const extractionTypeFilter = ref<string | null>(null)
  const categoryFilter = ref<string | null>(null)
  const minConfidence = ref(0)
  const verifiedFilter = ref<boolean | null>(null)
  const dateFrom = ref<string | null>(null)
  const dateTo = ref<string | null>(null)

  // ===========================================================================
  // Pagination
  // ===========================================================================

  const page = ref(RESULTS_PAGINATION.DEFAULT_PAGE)
  const perPage = ref(RESULTS_PAGINATION.DEFAULT_PER_PAGE)
  const sortBy = ref<SortConfig[]>([
    { key: RESULTS_PAGINATION.DEFAULT_SORT_BY, order: RESULTS_PAGINATION.DEFAULT_SORT_ORDER },
  ])

  // ===========================================================================
  // Dialog State
  // ===========================================================================

  const detailsDialog = ref(false)
  const selectedResult = ref<SearchResult | null>(null)

  // ===========================================================================
  // Table Headers
  // ===========================================================================

  const headers = ref<TableHeader[]>([
    { title: t('results.columns.document'), key: 'document', sortable: false, width: '220px' },
    { title: t('results.columns.type'), key: 'extraction_type', width: '140px', sortable: true },
    { title: t('results.columns.entities'), key: 'entity_count', width: '100px', sortable: true, align: 'center' },
    { title: t('results.columns.confidence'), key: 'confidence_score', width: '110px', sortable: true },
    { title: t('results.columns.verified'), key: 'human_verified', width: '90px', sortable: true },
    { title: t('results.columns.created'), key: 'created_at', width: '100px', sortable: true },
    { title: t('results.columns.actions'), key: 'actions', sortable: false, align: 'end' },
  ])

  // ===========================================================================
  // Computed Properties
  // ===========================================================================

  const showLocationFilter = computed(() => locations.value.length > 0)

  const hasActiveFilters = computed(() =>
    Boolean(
      searchQuery.value ||
        locationFilter.value ||
        extractionTypeFilter.value ||
        categoryFilter.value ||
        minConfidence.value > 0 ||
        verifiedFilter.value !== null ||
        dateFrom.value ||
        dateTo.value
    )
  )

  const canVerify = computed(() => auth.isEditor ?? false)

  // ===========================================================================
  // Return
  // ===========================================================================

  return {
    // Loading
    loading,
    initialLoad,
    bulkVerifying,

    // Data
    results,
    totalResults,
    locations,
    categories,
    extractionTypes,
    selectedResults,
    stats,

    // FacetTypes
    facetTypes,
    facetTypesLoading,

    // Filters
    searchQuery,
    locationFilter,
    extractionTypeFilter,
    categoryFilter,
    minConfidence,
    verifiedFilter,
    dateFrom,
    dateTo,

    // Pagination
    page,
    perPage,
    sortBy,

    // Dialog
    detailsDialog,
    selectedResult,

    // Headers
    headers,

    // Computed
    showLocationFilter,
    hasActiveFilters,
    canVerify,
  }
}
