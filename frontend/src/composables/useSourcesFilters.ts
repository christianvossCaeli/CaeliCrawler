import { ref, computed, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { adminApi } from '@/services/api'
import type {
  SourcesFiltersState,
  SidebarCounts,
  TagCount,
  SourceType,
  SourceStatus,
} from '@/types/sources'

/**
 * Options for useSourcesFilters composable
 */
export interface UseSourcesFiltersOptions {
  /** Debounce delay for search in ms */
  searchDebounce?: number
  /** Auto-initialize from route query params */
  useRouteParams?: boolean
  /** Callback when filters change */
  onFilterChange?: () => void
}

const DEFAULT_OPTIONS: UseSourcesFiltersOptions = {
  searchDebounce: 300,
  useRouteParams: true,
}

/**
 * Composable for DataSource filtering
 *
 * Provides:
 * - Filter state management
 * - Sidebar counts loading
 * - Available tags loading
 * - Debounced search
 * - Route query param initialization
 */
export function useSourcesFilters(options: UseSourcesFiltersOptions = {}) {
  const opts = { ...DEFAULT_OPTIONS, ...options }
  const route = useRoute()

  // ==========================================================================
  // State
  // ==========================================================================

  const filters = ref<SourcesFiltersState>({
    category_id: null,
    source_type: null,
    status: null,
    search: '',
    tags: [],
  })

  const sidebarCounts = ref<SidebarCounts>({
    total: 0,
    categories: [],
    types: [],
    statuses: [],
  })

  const availableTags = ref<TagCount[]>([])
  const loadingCounts = ref(false)
  const loadingTags = ref(false)

  // Debounce timer
  let searchTimeout: ReturnType<typeof setTimeout> | null = null

  // ==========================================================================
  // Computed
  // ==========================================================================

  /**
   * Check if any filters are active
   */
  const hasActiveFilters = computed(() => {
    return !!(
      filters.value.category_id ||
      filters.value.source_type ||
      filters.value.status ||
      filters.value.tags.length > 0
    )
  })

  /**
   * Get tag labels for combobox (sorted by usage)
   */
  const tagSuggestions = computed(() => availableTags.value.map((t) => t.tag))

  /**
   * Get total count from sidebar
   */
  const totalCount = computed(() => sidebarCounts.value.total)

  /**
   * Get filter params for API call (excludes empty values)
   */
  const filterParams = computed(() => {
    const params: Record<string, unknown> = { ...filters.value }
    // Remove empty tags array
    if (!params.tags || (params.tags as string[]).length === 0) {
      delete params.tags
    }
    // Remove empty search
    if (!params.search) {
      delete params.search
    }
    return params
  })

  // ==========================================================================
  // Filter Methods
  // ==========================================================================

  /**
   * Set category filter
   */
  function setCategory(categoryId: string | null) {
    filters.value.category_id = categoryId
    opts.onFilterChange?.()
  }

  /**
   * Set source type filter
   */
  function setType(type: SourceType | string | null) {
    filters.value.source_type = type as SourceType | null
    opts.onFilterChange?.()
  }

  /**
   * Set status filter
   */
  function setStatus(status: SourceStatus | string | null) {
    filters.value.status = status as SourceStatus | null
    opts.onFilterChange?.()
  }

  /**
   * Set tags filter
   */
  function setTags(tags: string[]) {
    filters.value.tags = tags
    opts.onFilterChange?.()
  }

  /**
   * Set search with debounce
   */
  function setSearch(search: string) {
    filters.value.search = search

    if (searchTimeout) {
      clearTimeout(searchTimeout)
    }

    searchTimeout = setTimeout(() => {
      opts.onFilterChange?.()
    }, opts.searchDebounce)
  }

  /**
   * Clear all filters
   */
  function clearAllFilters() {
    filters.value = {
      category_id: null,
      source_type: null,
      status: null,
      search: '',
      tags: [],
    }
    opts.onFilterChange?.()
  }

  /**
   * Get category name by ID
   */
  function getCategoryName(categoryId: string): string {
    const cat = sidebarCounts.value.categories.find((c) => c.id === categoryId)
    return cat?.name || categoryId
  }

  // ==========================================================================
  // Data Loading
  // ==========================================================================

  /**
   * Load sidebar counts from API
   */
  async function loadSidebarCounts(): Promise<void> {
    loadingCounts.value = true
    try {
      const response = await adminApi.getSourceCounts()
      sidebarCounts.value = response.data
    } catch (error) {
      console.error('Failed to load sidebar counts:', error)
    } finally {
      loadingCounts.value = false
    }
  }

  /**
   * Load available tags from API
   */
  async function loadAvailableTags(): Promise<void> {
    loadingTags.value = true
    try {
      const response = await adminApi.getAvailableTags()
      availableTags.value = response.data.tags || []
    } catch (error) {
      console.error('Failed to load available tags:', error)
    } finally {
      loadingTags.value = false
    }
  }

  /**
   * Initialize filters from route query params
   */
  function initFromRoute() {
    if (!opts.useRouteParams) return

    if (route.query.category_id) {
      filters.value.category_id = route.query.category_id as string
    }
    if (route.query.source_type) {
      filters.value.source_type = route.query.source_type as SourceType
    }
    if (route.query.status) {
      filters.value.status = route.query.status as SourceStatus
    }
    if (route.query.search) {
      filters.value.search = route.query.search as string
    }
    if (route.query.tags) {
      const tags = route.query.tags
      filters.value.tags = Array.isArray(tags) ? (tags as string[]) : [tags as string]
    }
  }

  /**
   * Refresh all filter-related data
   */
  async function refresh(): Promise<void> {
    await Promise.all([loadSidebarCounts(), loadAvailableTags()])
  }

  // ==========================================================================
  // Cleanup
  // ==========================================================================

  /**
   * Cleanup function for onUnmounted
   */
  function cleanup() {
    if (searchTimeout) {
      clearTimeout(searchTimeout)
      searchTimeout = null
    }
  }

  // Auto-cleanup on unmount
  onUnmounted(cleanup)

  return {
    // State
    filters,
    sidebarCounts,
    availableTags,
    loadingCounts,
    loadingTags,

    // Computed
    hasActiveFilters,
    tagSuggestions,
    totalCount,
    filterParams,

    // Filter methods
    setCategory,
    setType,
    setStatus,
    setTags,
    setSearch,
    clearAllFilters,
    getCategoryName,

    // Data loading
    loadSidebarCounts,
    loadAvailableTags,
    initFromRoute,
    refresh,

    // Cleanup
    cleanup,
  }
}
