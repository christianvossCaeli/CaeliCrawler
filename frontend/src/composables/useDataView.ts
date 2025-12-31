/**
 * useDataView - Base composable for data views
 *
 * Consolidates common patterns from view composables:
 * - useResultsView
 * - useDocumentsView
 * - useCategoriesView
 * - useEntitiesView
 *
 * Provides:
 * - Filter management (search, pagination, sorting)
 * - Loading state management
 * - CSV export functionality
 * - Error handling with snackbar
 * - Debounced data loading
 *
 * @example
 * ```typescript
 * const {
 *   filters,
 *   loading,
 *   pagination,
 *   loadData,
 *   exportCsv,
 *   handleError
 * } = useDataView<MyItem>({
 *   fetchFn: async (params) => api.getItems(params),
 *   csvConfig: { filename: 'items', columns: [...] }
 * })
 * ```
 */

import { ref, computed, watch, type Ref, type ComputedRef } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { format } from 'date-fns'
import { useSnackbar } from './useSnackbar'
import { useDebounce, DEBOUNCE_DELAYS } from './useDebounce'
import { getErrorMessage } from '@/utils/errorMessage'

// =============================================================================
// Types
// =============================================================================

export interface DataViewFilters {
  search: string
  page: number
  perPage: number
  sortBy: string
  sortOrder: 'asc' | 'desc'
  [key: string]: unknown
}

export interface DataViewPagination {
  page: number
  perPage: number
  total: number
  totalPages: number
}

export interface TableOptions {
  page: number
  itemsPerPage: number
  sortBy?: Array<{ key: string; order: 'asc' | 'desc' }>
}

export interface CsvColumn<T> {
  key: keyof T | string
  header: string
  formatter?: (value: unknown, item: T) => string
}

export interface CsvConfig<T> {
  filename: string
  columns: CsvColumn<T>[]
}

export interface DataViewOptions<T, F extends DataViewFilters = DataViewFilters> {
  /** Function to fetch data with filters */
  fetchFn: (filters: F) => Promise<{ items: T[]; total: number }>
  /** Initial filter values */
  initialFilters?: Partial<F>
  /** Default items per page */
  defaultPerPage?: number
  /** CSV export configuration */
  csvConfig?: CsvConfig<T>
  /** Sync filters with URL query params */
  syncWithRoute?: boolean
  /** Custom error message for load failures */
  loadErrorMessage?: string
}

// =============================================================================
// useFilters - Filter state management
// =============================================================================

export function useFilters<F extends DataViewFilters>(
  initialFilters?: Partial<F>,
  defaultPerPage = 20
) {
  const filters = ref<F>({
    search: '',
    page: 1,
    perPage: defaultPerPage,
    sortBy: 'created_at',
    sortOrder: 'desc',
    ...initialFilters,
  } as F) as Ref<F>

  const hasActiveFilters = computed(() => {
    const { search, page: _page, perPage: _perPage, sortBy: _sortBy, sortOrder: _sortOrder, ...rest } = filters.value
    // Check if any filter has a value (excluding pagination defaults)
    return (
      !!search ||
      Object.values(rest).some((v) => v !== null && v !== undefined && v !== '')
    )
  })

  function updateFilter<K extends keyof F>(key: K, value: F[K]) {
    filters.value[key] = value
    // Reset to page 1 when filters change (except page itself)
    if (key !== 'page') {
      filters.value.page = 1
    }
  }

  function clearFilters() {
    const { perPage, sortBy, sortOrder } = filters.value
    filters.value = {
      search: '',
      page: 1,
      perPage,
      sortBy,
      sortOrder,
      ...initialFilters,
    } as F
  }

  function setPage(page: number) {
    filters.value.page = page
  }

  function setPerPage(perPage: number) {
    filters.value.perPage = perPage
    filters.value.page = 1
  }

  function setSort(sortBy: string, sortOrder: 'asc' | 'desc' = 'asc') {
    filters.value.sortBy = sortBy
    filters.value.sortOrder = sortOrder
  }

  return {
    filters,
    hasActiveFilters,
    updateFilter,
    clearFilters,
    setPage,
    setPerPage,
    setSort,
  }
}

// =============================================================================
// useLoadingState - Loading state management
// =============================================================================

export function useLoadingState() {
  const loading = ref(true)
  const initialLoad = ref(true)
  const refreshing = ref(false)

  function startLoading(isRefresh = false) {
    if (isRefresh) {
      refreshing.value = true
    } else {
      loading.value = true
    }
  }

  function stopLoading() {
    loading.value = false
    initialLoad.value = false
    refreshing.value = false
  }

  return {
    loading,
    initialLoad,
    refreshing,
    startLoading,
    stopLoading,
  }
}

// =============================================================================
// usePagination - Pagination management
// =============================================================================

export function usePagination<F extends DataViewFilters>(
  filters: Ref<F>,
  total: Ref<number>
): {
  pagination: ComputedRef<DataViewPagination>
  onTableOptionsUpdate: (options: TableOptions) => void
} {
  const pagination = computed<DataViewPagination>(() => ({
    page: filters.value.page,
    perPage: filters.value.perPage,
    total: total.value,
    totalPages: Math.ceil(total.value / filters.value.perPage),
  }))

  function onTableOptionsUpdate(options: TableOptions) {
    filters.value.page = options.page
    filters.value.perPage = options.itemsPerPage
    if (options.sortBy && options.sortBy.length > 0) {
      filters.value.sortBy = options.sortBy[0].key
      filters.value.sortOrder = options.sortBy[0].order
    }
  }

  return {
    pagination,
    onTableOptionsUpdate,
  }
}

// =============================================================================
// useCsvExport - CSV export functionality
// =============================================================================

export function useCsvExport<T>(config?: CsvConfig<T>) {
  const { t } = useI18n()
  const { showSuccess, showError } = useSnackbar()

  function exportCsv(items: T[], customConfig?: CsvConfig<T>) {
    const cfg = customConfig || config
    if (!cfg) {
      showError(t('common.exportConfigMissing', 'Export configuration missing'))
      return
    }

    try {
      // Build header row
      const headers = cfg.columns.map((col) => col.header)

      // Build data rows
      const rows = items.map((item) =>
        cfg.columns.map((col) => {
          const value = getNestedValue(item, col.key as string)
          if (col.formatter) {
            return escapeCsvValue(col.formatter(value, item))
          }
          return escapeCsvValue(String(value ?? ''))
        })
      )

      // Combine into CSV
      const csv = [
        headers.join(','),
        ...rows.map((row) => row.join(',')),
      ].join('\n')

      // Download file
      const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${cfg.filename}-${format(new Date(), 'yyyy-MM-dd')}.csv`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)

      showSuccess(t('common.csvExported', 'Data exported successfully'))
    } catch (error) {
      showError(getErrorMessage(error) || t('common.exportFailed', 'Export failed'))
    }
  }

  return { exportCsv }
}

// =============================================================================
// Helper functions
// =============================================================================

function getNestedValue(obj: unknown, path: string): unknown {
  return path.split('.').reduce((acc: unknown, part) => {
    if (acc && typeof acc === 'object' && part in acc) {
      return (acc as Record<string, unknown>)[part]
    }
    return undefined
  }, obj)
}

function escapeCsvValue(value: string): string {
  if (value.includes(',') || value.includes('"') || value.includes('\n')) {
    return `"${value.replace(/"/g, '""')}"`
  }
  return value
}

// =============================================================================
// Main composable: useDataView
// =============================================================================

export function useDataView<T, F extends DataViewFilters = DataViewFilters>(
  options: DataViewOptions<T, F>
) {
  const { t } = useI18n()
  const route = useRoute()
  const router = useRouter()
  const { showError, showSuccess, showWarning } = useSnackbar()

  // Data state
  const items = ref<T[]>([]) as Ref<T[]>
  const total = ref(0)
  const error = ref<string | null>(null)

  // Filter management
  const {
    filters,
    hasActiveFilters,
    updateFilter,
    clearFilters,
    setPage,
    setPerPage,
    setSort,
  } = useFilters<F>(options.initialFilters, options.defaultPerPage)

  // Loading state
  const { loading, initialLoad, refreshing, startLoading, stopLoading } =
    useLoadingState()

  // Pagination
  const { pagination, onTableOptionsUpdate } = usePagination(filters, total)

  // CSV export
  const { exportCsv: exportCsvBase } = useCsvExport<T>(options.csvConfig)

  // Debounced load
  const { debouncedFn: debouncedLoadData } = useDebounce(
    () => loadData(),
    { delay: DEBOUNCE_DELAYS.SEARCH }
  )

  // ==========================================================================
  // Core functions
  // ==========================================================================

  async function loadData(isRefresh = false) {
    startLoading(isRefresh)
    error.value = null

    try {
      const result = await options.fetchFn(filters.value)
      items.value = result.items
      total.value = result.total
    } catch (e) {
      error.value =
        getErrorMessage(e) ||
        options.loadErrorMessage ||
        t('common.loadFailed', 'Failed to load data')
      showError(error.value)
    } finally {
      stopLoading()
    }
  }

  function refresh() {
    return loadData(true)
  }

  function exportCsv() {
    if (items.value.length === 0) {
      showWarning(t('common.noDataToExport', 'No data to export'))
      return
    }
    exportCsvBase(items.value)
  }

  function handleError(e: unknown, customMessage?: string) {
    const message = getErrorMessage(e) || customMessage || t('common.error', 'An error occurred')
    showError(message)
    return message
  }

  // ==========================================================================
  // Route sync (optional)
  // ==========================================================================

  if (options.syncWithRoute) {
    // Initialize from route query
    const query = route.query
    if (query.search) filters.value.search = String(query.search)
    if (query.page) filters.value.page = Number(query.page)
    if (query.perPage) filters.value.perPage = Number(query.perPage)
    if (query.sortBy) filters.value.sortBy = String(query.sortBy)
    if (query.sortOrder) filters.value.sortOrder = query.sortOrder as 'asc' | 'desc'

    // Sync filters to route
    watch(
      filters,
      (newFilters) => {
        const query: Record<string, string> = {}
        if (newFilters.search) query.search = newFilters.search
        if (newFilters.page > 1) query.page = String(newFilters.page)
        if (newFilters.perPage !== options.defaultPerPage) {
          query.perPage = String(newFilters.perPage)
        }
        router.replace({ query })
      },
      { deep: true }
    )
  }

  // ==========================================================================
  // Watch filters and reload
  // ==========================================================================

  watch(
    () => filters.value.search,
    () => {
      if (!initialLoad.value) {
        debouncedLoadData()
      }
    }
  )

  watch(
    () => [filters.value.page, filters.value.perPage, filters.value.sortBy, filters.value.sortOrder],
    () => {
      if (!initialLoad.value) {
        loadData()
      }
    }
  )

  // ==========================================================================
  // Return
  // ==========================================================================

  return {
    // Data
    items,
    total,
    error,

    // Filters
    filters,
    hasActiveFilters,
    updateFilter,
    clearFilters,
    setPage,
    setPerPage,
    setSort,

    // Loading
    loading,
    initialLoad,
    refreshing,

    // Pagination
    pagination,
    onTableOptionsUpdate,

    // Actions
    loadData,
    refresh,
    debouncedLoadData,
    exportCsv,
    handleError,

    // Snackbar (for convenience)
    showError,
    showSuccess,
    showWarning,
  }
}
