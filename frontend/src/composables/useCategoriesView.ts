import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { adminApi } from '@/services/api'
import { useDebounce, DEBOUNCE_DELAYS } from '@/composables/useDebounce'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger('useCategoriesView')

export interface Category {
  id: string
  name: string
  description?: string
  purpose: string
  search_terms?: string[]
  document_types?: string[]
  languages?: string[]
  url_include_patterns?: string[]
  url_exclude_patterns?: string[]
  schedule_cron?: string
  ai_extraction_prompt?: string
  is_active: boolean
  source_count?: number
  document_count?: number
  target_entity_type?: {
    id: string
    name: string
  }
}

export interface CategoryFormData {
  name: string
  description: string
  purpose: string
  search_terms: string[]
  document_types: string[]
  languages: string[]
  url_include_patterns: string[]
  url_exclude_patterns: string[]
  schedule_cron: string
  ai_extraction_prompt: string
  is_active: boolean
}

export interface CategoryFilters {
  search: string
  status: string | null
  hasDocuments: string | null
  language: string | null
}

export interface CategorySource {
  id: string
  name: string
  status?: string
  source_type?: string
  base_url?: string
  last_crawled_at?: string
  is_assigned?: boolean
}

export interface DataSourcesTabState {
  selectedTags: string[]
  matchMode: 'all' | 'any'
  foundSources: CategorySource[]
  loading: boolean
  assigning: boolean
  availableTags: string[]
}

export interface CrawlerFilter {
  search: string | null
  limit: number | null
  status: string | null
  source_type: string | null
}

export interface SnackbarState {
  show: boolean
  text: string
  color: 'success' | 'error' | 'warning' | 'info'
}

/**
 * Shared state and logic for Categories view
 */
export function useCategoriesView() {
  const { t } = useI18n()
  const router = useRouter()

  // State
  const loading = ref(false)
  const categories = ref<Category[]>([])
  const selectedCategory = ref<Category | null>(null)
  const categorySources = ref<CategorySource[]>([])
  const categorySourcesLoading = ref(false)

  // Filters
  const categoryFilters = ref<CategoryFilters>({
    search: '',
    status: null,
    hasDocuments: null,
    language: null,
  })

  // Snackbar
  const snackbar = ref<SnackbarState>({
    show: false,
    text: '',
    color: 'success',
  })

  // Filter options
  const statusFilterOptions = computed(() => [
    { value: 'active', label: t('categories.statusOptions.active') },
    { value: 'inactive', label: t('categories.statusOptions.inactive') },
  ])

  const documentFilterOptions = computed(() => [
    { value: 'with', label: t('categories.filters.withDocuments') },
    { value: 'without', label: t('categories.filters.withoutDocuments') },
  ])

  const languageFilterOptions = [
    { code: 'de', name: 'Deutsch', flag: '🇩🇪' },
    { code: 'en', name: 'English', flag: '🇬🇧' },
    { code: 'fr', name: 'Français', flag: '🇫🇷' },
    { code: 'nl', name: 'Nederlands', flag: '🇳🇱' },
    { code: 'it', name: 'Italiano', flag: '🇮🇹' },
    { code: 'es', name: 'Español', flag: '🇪🇸' },
    { code: 'pl', name: 'Polski', flag: '🇵🇱' },
    { code: 'da', name: 'Dansk', flag: '🇩🇰' },
  ]

  const availableLanguages = languageFilterOptions

  // Filtered categories
  const filteredCategories = computed(() => {
    let result = categories.value

    // Search filter
    if (categoryFilters.value.search) {
      const search = categoryFilters.value.search.toLowerCase()
      result = result.filter(c =>
        c.name?.toLowerCase().includes(search) ||
        c.purpose?.toLowerCase().includes(search) ||
        c.description?.toLowerCase().includes(search)
      )
    }

    // Status filter
    if (categoryFilters.value.status) {
      const isActive = categoryFilters.value.status === 'active'
      result = result.filter(c => c.is_active === isActive)
    }

    // Documents filter
    if (categoryFilters.value.hasDocuments) {
      if (categoryFilters.value.hasDocuments === 'with') {
        result = result.filter(c => (c.document_count || 0) > 0)
      } else {
        result = result.filter(c => (c.document_count || 0) === 0)
      }
    }

    // Language filter
    if (categoryFilters.value.language) {
      result = result.filter(c =>
        (c.languages || ['de']).includes(categoryFilters.value.language as string)
      )
    }

    return result
  })

  // Computed stats for sources dialog
  const categorySourcesStats = computed(() => {
    const sources = categorySources.value
    return {
      total: sources.length,
      active: sources.filter(s => s.status === 'ACTIVE').length,
      pending: sources.filter(s => s.status === 'PENDING').length,
      error: sources.filter(s => s.status === 'ERROR').length,
    }
  })

  // Methods
  const loadCategories = async () => {
    loading.value = true
    try {
      const response = await adminApi.getCategories({ per_page: 100 })
      categories.value = response.data.items
    } catch (error) {
      logger.error('Failed to load categories:', error)
      showSnackbar(t('categories.messages.loadError'), 'error')
    } finally {
      loading.value = false
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
      await adminApi.deleteCategory(categoryId)
      showSnackbar(t('categories.messages.deleted'), 'success')
      await loadCategories()
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

  const loadSourcesForCategory = async (categoryId: string) => {
    categorySources.value = []
    categorySourcesLoading.value = true

    try {
      const response = await adminApi.getSources({
        category_id: categoryId,
        per_page: 10000,
      })
      categorySources.value = response.data.items
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
      query: { category_id: categoryId }
    })
  }

  // Helper functions
  const getLanguageFlag = (code: string): string => {
    const lang = availableLanguages.find(l => l.code === code)
    return lang?.flag || code.toUpperCase()
  }

  const getStatusColor = (status?: string) => {
    if (!status) return 'grey'
    const colors: Record<string, string> = {
      ACTIVE: 'success',
      PENDING: 'warning',
      ERROR: 'error',
      PAUSED: 'grey',
    }
    return colors[status] || 'grey'
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
    // State
    loading,
    categories,
    selectedCategory,
    categorySources,
    categorySourcesLoading,
    categoryFilters,
    snackbar,

    // Computed
    filteredCategories,
    statusFilterOptions,
    documentFilterOptions,
    languageFilterOptions,
    availableLanguages,
    categorySourcesStats,

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
  const crawlerFilter = ref<CrawlerFilter>({
    search: null,
    limit: null,
    status: null,
    source_type: null,
  })

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

  const dataSourcesTab = ref<DataSourcesTabState>({
    selectedTags: [],
    matchMode: 'all',
    foundSources: [],
    loading: false,
    assigning: false,
    availableTags: [],
  })

  const loadAvailableTags = async () => {
    try {
      const response = await adminApi.getAvailableTags()
      dataSourcesTab.value.availableTags = (response.data.tags || []).map((t: { tag: string }) => t.tag)
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

      const assignedSourceIds = new Set(assignedSources.map(s => s.id))
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
      const response = await adminApi.assignSourcesByTags(categoryId, {
        tags: dataSourcesTab.value.selectedTags,
        match_mode: dataSourcesTab.value.matchMode,
        mode: 'add',
      })

      const assignedCount = response.data.assigned_count || dataSourcesTab.value.foundSources.length
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
