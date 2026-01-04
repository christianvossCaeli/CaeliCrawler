/**
 * Categories View Composable
 *
 * Provides view-specific state and logic for the Categories view.
 * Uses useCategoriesStore as the single source of truth for category data.
 */
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { adminApi } from '@/services/api'
import { categoryApi } from '@/services/api/categories'
import { useCategoriesStore } from '@/stores/categories'
import { useDebounce, DEBOUNCE_DELAYS } from '@/composables/useDebounce'
import { useLogger } from '@/composables/useLogger'
import { getStatusColor } from '@/composables/useStatusColors'
import { emitCrawlerEvent } from '@/composables/useCrawlerEvents'
import type {
  CategoryResponse,
  CategoryFormData,
  CategoryFilters,
  CategorySource,
  DataSourcesTabState,
  CrawlerFilter,
  SnackbarState,
} from '@/types/category'
import {
  DEFAULT_DATA_SOURCES_TAB_STATE,
  DEFAULT_CRAWLER_FILTER,
  DEFAULT_SNACKBAR_STATE,
} from '@/types/category'

const logger = useLogger('useCategoriesView')

// Re-export types for backward compatibility
export type {
  CategoryFormData,
  CategoryFilters,
  CategorySource,
  DataSourcesTabState,
  CrawlerFilter,
  SnackbarState,
}

/**
 * @deprecated Use CategoryResponse from @/types/category instead
 * Kept for backward compatibility
 */
export type Category = CategoryResponse

/**
 * Language option type
 */
export interface LanguageOption {
  code: string
  name: string
  flag: string
}

/**
 * Available languages for categories
 */
export const AVAILABLE_LANGUAGES: LanguageOption[] = [
  { code: 'de', name: 'Deutsch', flag: '🇩🇪' },
  { code: 'en', name: 'English', flag: '🇬🇧' },
  { code: 'fr', name: 'Français', flag: '🇫🇷' },
  { code: 'nl', name: 'Nederlands', flag: '🇳🇱' },
  { code: 'it', name: 'Italiano', flag: '🇮🇹' },
  { code: 'es', name: 'Español', flag: '🇪🇸' },
  { code: 'pl', name: 'Polski', flag: '🇵🇱' },
  { code: 'da', name: 'Dansk', flag: '🇩🇰' },
]

/**
 * Shared state and logic for Categories view
 * Uses useCategoriesStore as single source of truth
 */
export function useCategoriesView() {
  const { t } = useI18n()
  const router = useRouter()
  const store = useCategoriesStore()

  // Get reactive references from store
  const { categories, selectedCategory, loading, pagination, filters } = storeToRefs(store)

  // View-specific state (not in store)
  const categorySources = ref<CategorySource[]>([])
  const categorySourcesLoading = ref(false)
  const categorySourcesStats = ref({
    total: 0,
    active: 0,
    pending: 0,
    error: 0,
  })
  const categorySourcesTotal = ref(0)
  const categorySourcesPage = ref(1)
  const categorySourcesPerPage = ref(20)
  const categorySourcesSearch = ref('')
  const categorySourcesCategoryId = ref<string | null>(null)

  // Snackbar
  const snackbar = ref<SnackbarState>({ ...DEFAULT_SNACKBAR_STATE })

  // Computed values derived from store
  const totalCategories = computed(() => pagination.value.total)
  const categoryPage = computed({
    get: () => pagination.value.page,
    set: (value: number) => store.setPagination({ page: value }),
  })
  const categoryPerPage = computed({
    get: () => pagination.value.perPage,
    set: (value: number) => store.setPagination({ perPage: value }),
  })
  const categorySortBy = computed({
    get: () => pagination.value.sortBy,
    set: (value: string) => store.setPagination({ sortBy: value }),
  })
  const categorySortOrder = computed({
    get: () => pagination.value.sortOrder,
    set: (value: 'asc' | 'desc') => store.setPagination({ sortOrder: value }),
  })
  const categoryFilters = computed({
    get: () => filters.value,
    set: (value: CategoryFilters) => store.setFilters(value),
  })

  // Filtered categories (server-side)
  const filteredCategories = computed(() => categories.value)

  // Filter options
  const statusFilterOptions = computed(() => [
    { value: 'active', label: t('categories.statusOptions.active') },
    { value: 'inactive', label: t('categories.statusOptions.inactive') },
  ])

  const documentFilterOptions = computed(() => [
    { value: 'with', label: t('categories.filters.withDocuments') },
    { value: 'without', label: t('categories.filters.withoutDocuments') },
  ])

  const languageFilterOptions = AVAILABLE_LANGUAGES
  const availableLanguages = AVAILABLE_LANGUAGES

  // Methods - delegate to store
  const loadCategories = async () => {
    try {
      await store.fetchCategories()
    } catch (error) {
      logger.error('Failed to load categories:', error)
      showSnackbar(t('categories.messages.loadError'), 'error')
    }
  }

  const showSnackbar = (text: string, color: SnackbarState['color'] = 'success') => {
    snackbar.value = {
      show: true,
      text,
      color,
    }
  }

  const deleteCategory = async (categoryId: string) => {
    try {
      await store.deleteCategory(categoryId)
      showSnackbar(t('categories.messages.deleted'), 'success')
      return true
    } catch (error) {
      logger.error('Failed to delete category:', error)
      showSnackbar(t('categories.messages.deleteError'), 'error')
      return false
    }
  }

  const reanalyzeDocuments = async (categoryId: string, reanalyzeAll: boolean) => {
    try {
      const response = await adminApi.reanalyzeDocuments({
        category_id: categoryId,
        reanalyze_all: reanalyzeAll,
      })
      showSnackbar(response.data.message || t('categories.messages.reanalyzeStarted'), 'success')
      return true
    } catch (error) {
      logger.error('Failed to start reanalysis:', error)
      showSnackbar(t('categories.messages.reanalyzeError'), 'error')
      return false
    }
  }

  const loadSourcesForCategory = async (
    categoryId: string,
    options?: { page?: number; perPage?: number; search?: string }
  ) => {
    categorySources.value = []
    categorySourcesLoading.value = true

    const page = options?.page ?? categorySourcesPage.value
    const perPage = options?.perPage ?? categorySourcesPerPage.value
    const search = options?.search ?? categorySourcesSearch.value

    categorySourcesPage.value = page
    categorySourcesPerPage.value = perPage
    categorySourcesSearch.value = search

    const shouldRefreshStats = categorySourcesCategoryId.value !== categoryId
    categorySourcesCategoryId.value = categoryId

    try {
      const params: Record<string, unknown> = {
        category_id: categoryId,
        page,
        per_page: perPage,
      }
      if (search) params.search = search
      const response = await adminApi.getSources(params)
      categorySources.value = response.data.items
      categorySourcesTotal.value = response.data.total

      if (shouldRefreshStats) {
        const statsResponse = await adminApi.getSourceStatusStats({ category_id: categoryId })
        const counts = statsResponse.data.by_status || {}
        categorySourcesStats.value = {
          total: statsResponse.data.total || 0,
          active: counts.ACTIVE || 0,
          pending: counts.PENDING || 0,
          error: counts.ERROR || 0,
        }
      }
    } catch (error) {
      logger.error('Failed to load sources for category:', error)
      showSnackbar(t('categories.messages.sourcesLoadError'), 'error')
    } finally {
      categorySourcesLoading.value = false
    }
  }

  const navigateToSourcesFiltered = (categoryId: string) => {
    router.push({
      path: '/sources',
      query: { category_id: categoryId },
    })
  }

  // Helper functions
  const getLanguageFlag = (code: string): string => {
    const lang = availableLanguages.find((l) => l.code === code)
    return lang?.flag || code.toUpperCase()
  }

  const getSourceTypeIcon = (type?: string) => {
    if (!type) return 'mdi-database'
    const icons: Record<string, string> = {
      WEBSITE: 'mdi-web',
      OPARL_API: 'mdi-api',
      RSS: 'mdi-rss',
      CUSTOM_API: 'mdi-code-json',
    }
    return icons[type] || 'mdi-database'
  }

  return {
    // State (from store via storeToRefs)
    loading,
    categories,
    selectedCategory,

    // View-specific state
    categorySources,
    categorySourcesLoading,
    snackbar,
    categorySourcesTotal,
    categorySourcesPage,
    categorySourcesPerPage,
    categorySourcesSearch,

    // Computed (wrapping store)
    totalCategories,
    categoryPage,
    categoryPerPage,
    categorySortBy,
    categorySortOrder,
    categoryFilters,
    filteredCategories,
    categorySourcesStats,

    // Filter options
    statusFilterOptions,
    documentFilterOptions,
    languageFilterOptions,
    availableLanguages,

    // Methods
    loadCategories,
    showSnackbar,
    deleteCategory,
    reanalyzeDocuments,
    loadSourcesForCategory,
    navigateToSourcesFiltered,
    getLanguageFlag,
    getStatusColor,
    getSourceTypeIcon,

    // Store instance for direct access if needed
    store,
  }
}

/**
 * Crawler-specific state and logic
 */
export function useCategoryCrawler() {
  const { t } = useI18n()

  const crawlerDialog = ref(false)
  const startingCrawler = ref(false)
  const selectedCategoryForCrawler = ref<Category | null>(null)
  const crawlerFilteredCount = ref(0)
  const crawlerFilter = ref<CrawlerFilter>({ ...DEFAULT_CRAWLER_FILTER })

  const updateCrawlerFilteredCount = async () => {
    if (!selectedCategoryForCrawler.value) return

    try {
      const params: Record<string, unknown> = {
        category_id: selectedCategoryForCrawler.value.id,
        per_page: 1,
      }
      if (crawlerFilter.value.search) params.search = crawlerFilter.value.search
      if (crawlerFilter.value.status) params.status = crawlerFilter.value.status
      if (crawlerFilter.value.source_type) params.source_type = crawlerFilter.value.source_type

      const response = await adminApi.getSources(params)
      let count = response.data.total || 0

      if (crawlerFilter.value.limit && crawlerFilter.value.limit > 0) {
        count = Math.min(count, crawlerFilter.value.limit)
      }

      crawlerFilteredCount.value = count
    } catch (error) {
      logger.error('Failed to get filtered count:', error)
      crawlerFilteredCount.value = selectedCategoryForCrawler.value?.source_count || 0
    }
  }

  const { debouncedFn: debouncedUpdateCrawlerCount } = useDebounce(
    () => updateCrawlerFilteredCount(),
    { delay: DEBOUNCE_DELAYS.SEARCH }
  )

  const handleCrawlerFilterUpdate = (newFilter: CrawlerFilter) => {
    const searchChanged = newFilter.search !== crawlerFilter.value.search
    crawlerFilter.value = newFilter
    if (searchChanged) {
      debouncedUpdateCrawlerCount()
    } else {
      updateCrawlerFilteredCount()
    }
  }

  const resetCrawlerFilters = () => {
    crawlerFilter.value = {
      search: null,
      limit: null,
      status: null,
      source_type: null,
    }
    updateCrawlerFilteredCount()
  }

  const openCrawlerDialog = (category: Category) => {
    selectedCategoryForCrawler.value = category
    crawlerFilter.value = {
      search: null,
      limit: null,
      status: null,
      source_type: null,
    }
    crawlerFilteredCount.value = category.source_count || 0
    crawlerDialog.value = true
    updateCrawlerFilteredCount()
  }

  const startFilteredCrawl = async () => {
    if (!selectedCategoryForCrawler.value) return false

    startingCrawler.value = true
    try {
      const params: Record<string, unknown> = {
        category_id: selectedCategoryForCrawler.value.id,
      }
      if (crawlerFilter.value.search) params.search = crawlerFilter.value.search
      if (crawlerFilter.value.status) params.status = crawlerFilter.value.status
      if (crawlerFilter.value.source_type) params.source_type = crawlerFilter.value.source_type
      if (crawlerFilter.value.limit) params.limit = crawlerFilter.value.limit

      await adminApi.startCrawl(params)
      crawlerDialog.value = false
      // Notify CrawlerView to refresh immediately
      emitCrawlerEvent('crawl-started')

      return {
        success: true,
        message: t('categories.crawler.started', { count: crawlerFilteredCount.value }),
      }
    } catch (error) {
      logger.error('Failed to start crawl:', error)
      return {
        success: false,
        message: t('categories.crawler.errorStarting'),
      }
    } finally {
      startingCrawler.value = false
    }
  }

  return {
    crawlerDialog,
    startingCrawler,
    selectedCategoryForCrawler,
    crawlerFilteredCount,
    crawlerFilter,
    handleCrawlerFilterUpdate,
    resetCrawlerFilters,
    openCrawlerDialog,
    startFilteredCrawl,
    updateCrawlerFilteredCount,
  }
}

/**
 * DataSources tab state and logic
 */
export function useCategoryDataSources() {
  const { t } = useI18n()

  const dataSourcesTab = ref<DataSourcesTabState>({ ...DEFAULT_DATA_SOURCES_TAB_STATE })

  const loadAvailableTags = async () => {
    try {
      const response = await adminApi.getAvailableTags()
      dataSourcesTab.value.availableTags = (response.data.tags || []).map(
        (t: { tag: string }) => t.tag
      )
    } catch (error) {
      logger.error('Failed to load available tags:', error)
      dataSourcesTab.value.availableTags = []
      throw error
    }
  }

  const searchSourcesByTags = async (categoryId: string, assignedSources: CategorySource[]) => {
    if (!dataSourcesTab.value.selectedTags.length) {
      dataSourcesTab.value.foundSources = []
      return
    }

    dataSourcesTab.value.loading = true
    try {
      const response = await adminApi.getSourcesByTags({
        tags: dataSourcesTab.value.selectedTags,
        match_mode: dataSourcesTab.value.matchMode,
        exclude_category_id: categoryId,
        limit: 1000,
      })

      const assignedSourceIds = new Set(assignedSources.map((s) => s.id))
      dataSourcesTab.value.foundSources = response.data.map((source: CategorySource) => ({
        ...source,
        is_assigned: assignedSourceIds.has(source.id),
      }))
    } catch (error) {
      logger.error('Failed to search sources by tags:', error)
      dataSourcesTab.value.foundSources = []
      throw error
    } finally {
      dataSourcesTab.value.loading = false
    }
  }

  const assignSourcesByTags = async (categoryId: string) => {
    if (!dataSourcesTab.value.selectedTags.length) return null

    dataSourcesTab.value.assigning = true
    try {
      const response = await categoryApi.assignSourcesByTags(categoryId, {
        tags: dataSourcesTab.value.selectedTags,
        match_mode: dataSourcesTab.value.matchMode,
        mode: 'add',
      })

      const assignedCount = response.data.assigned || dataSourcesTab.value.foundSources.length
      return {
        success: true,
        count: assignedCount,
        message: t('categories.dataSourcesTab.assignSuccess', { count: assignedCount }),
      }
    } catch (error) {
      logger.error('Failed to assign sources:', error)
      return {
        success: false,
        message: t('categories.dataSourcesTab.assignError'),
      }
    } finally {
      dataSourcesTab.value.assigning = false
    }
  }

  const resetDataSourcesTab = () => {
    dataSourcesTab.value = {
      selectedTags: [],
      matchMode: 'all',
      foundSources: [],
      loading: false,
      assigning: false,
      availableTags: dataSourcesTab.value.availableTags,
    }
  }

  return {
    dataSourcesTab,
    loadAvailableTags,
    searchSourcesByTags,
    assignSourcesByTags,
    resetDataSourcesTab,
  }
}
