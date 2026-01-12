/**
 * Tests for useCategoriesView composable
 *
 * Tests the view composable that bridges useCategoriesStore
 * with view-specific state and functionality.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useCategoriesView, useCategoryCrawler, useCategoryDataSources, AVAILABLE_LANGUAGES } from './useCategoriesView'
import type { CategoryResponse } from '@/types/category'
import { mockAxiosResponse } from '@/test/setup'

// Mock the stores and API modules
import { ref } from 'vue'

const mockCategories = ref<CategoryResponse[]>([])
const mockSelectedCategory = ref<CategoryResponse | null>(null)
const mockLoading = ref(false)
const mockPagination = ref({
  page: 1,
  perPage: 20,
  total: 0,
  totalPages: 0,
  sortBy: 'name',
  sortOrder: 'asc' as const,
})
const mockFilters = ref({
  search: '',
  status: null as string | null,
  hasDocuments: null as string | null,
  language: null as string | null,
})

vi.mock('@/stores/categories', () => ({
  useCategoriesStore: vi.fn(() => ({
    categories: mockCategories,
    selectedCategory: mockSelectedCategory,
    loading: mockLoading,
    pagination: mockPagination,
    filters: mockFilters,
    fetchCategories: vi.fn(),
    deleteCategory: vi.fn(),
    setPagination: vi.fn(),
    setFilters: vi.fn(),
  })),
}))

vi.mock('@/services/api', () => ({
  adminApi: {
    getSources: vi.fn(),
    getSourceStatusStats: vi.fn(),
    reanalyzeDocuments: vi.fn(),
    getAvailableTags: vi.fn(),
    getSourcesByTags: vi.fn(),
    startCrawl: vi.fn(),
  },
}))

vi.mock('@/services/api/categories', () => ({
  categoryApi: {
    assignSourcesByTags: vi.fn(),
  },
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}))

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string, params?: Record<string, unknown>) => {
      if (params) return `${key}:${JSON.stringify(params)}`
      return key
    },
  }),
}))

vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}))

vi.mock('@/composables/useStatusColors', () => ({
  getStatusColor: (status: string) => {
    const colors: Record<string, string> = {
      ACTIVE: 'success',
      PENDING: 'warning',
      ERROR: 'error',
    }
    return colors[status] || 'grey'
  },
}))

vi.mock('@/composables/useDebounce', () => ({
  useDebounce: (fn: () => void) => ({
    debouncedFn: fn,
  }),
  DEBOUNCE_DELAYS: {
    SEARCH: 300,
  },
}))

// Import mocked modules
import { adminApi } from '@/services/api'
import { categoryApi } from '@/services/api/categories'

// Mock category data
const mockCategory: CategoryResponse = {
  id: 'cat-123',
  name: 'Test Category',
  slug: 'test-category',
  purpose: 'Testing purposes',
  description: 'A test category',
  is_public: false,
  languages: ['de', 'en'],
  search_terms: ['test'],
  document_types: ['html', 'pdf'],
  url_include_patterns: [],
  url_exclude_patterns: [],
  schedule_cron: '0 2 * * *',
  schedule_enabled: false,
  extraction_handler: 'default',
  ai_extraction_prompt: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  source_count: 5,
  document_count: 100,
  target_entity_type_id: null,
  target_entity_type: null,
}

describe('useCategoriesView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    // Reset mock state
    mockCategories.value = []
    mockSelectedCategory.value = null
    mockLoading.value = false
    mockPagination.value = {
      page: 1,
      perPage: 20,
      total: 0,
      totalPages: 0,
      sortBy: 'name',
      sortOrder: 'asc',
    }
    mockFilters.value = {
      search: '',
      status: null,
      hasDocuments: null,
      language: null,
    }
  })

  // ==========================================================================
  // AVAILABLE_LANGUAGES Export
  // ==========================================================================

  describe('AVAILABLE_LANGUAGES', () => {
    it('should export available languages', () => {
      expect(AVAILABLE_LANGUAGES).toHaveLength(8)
      expect(AVAILABLE_LANGUAGES[0]).toEqual({ code: 'de', name: 'Deutsch', flag: '🇩🇪' })
    })

    it('should include common European languages', () => {
      const codes = AVAILABLE_LANGUAGES.map((l) => l.code)
      expect(codes).toContain('de')
      expect(codes).toContain('en')
      expect(codes).toContain('fr')
      expect(codes).toContain('nl')
    })
  })

  // ==========================================================================
  // State & Computed
  // ==========================================================================

  describe('State & Computed', () => {
    it('should return reactive state from store', () => {
      const { loading, categories, selectedCategory } = useCategoriesView()

      expect(loading.value).toBe(false)
      expect(categories.value).toEqual([])
      expect(selectedCategory.value).toBeNull()
    })

    it('should provide computed pagination values', () => {
      const { categoryPage, categoryPerPage, categorySortBy, categorySortOrder } = useCategoriesView()

      expect(categoryPage.value).toBe(1)
      expect(categoryPerPage.value).toBe(20)
      expect(categorySortBy.value).toBe('name')
      expect(categorySortOrder.value).toBe('asc')
    })

    it('should provide filter options', () => {
      const { statusFilterOptions, documentFilterOptions, languageFilterOptions } = useCategoriesView()

      expect(statusFilterOptions.value).toHaveLength(2)
      expect(documentFilterOptions.value).toHaveLength(2)
      expect(languageFilterOptions).toHaveLength(8)
    })
  })

  // ==========================================================================
  // Methods
  // ==========================================================================

  describe('loadCategories', () => {
    it('should call store.fetchCategories', async () => {
      const { loadCategories, store } = useCategoriesView()

      await loadCategories()

      expect(store.fetchCategories).toHaveBeenCalled()
    })

    it('should show error snackbar on failure', async () => {
      const { loadCategories, snackbar, store } = useCategoriesView()
      vi.mocked(store.fetchCategories).mockRejectedValue(new Error('Network error'))

      await loadCategories()

      expect(snackbar.value.show).toBe(true)
      expect(snackbar.value.color).toBe('error')
    })
  })

  describe('deleteCategory', () => {
    it('should call store.deleteCategory and show success snackbar', async () => {
      const { deleteCategory, snackbar, store } = useCategoriesView()
      vi.mocked(store.deleteCategory).mockResolvedValue()

      const result = await deleteCategory('cat-123')

      expect(store.deleteCategory).toHaveBeenCalledWith('cat-123')
      expect(result).toBe(true)
      expect(snackbar.value.color).toBe('success')
    })

    it('should show error snackbar on failure', async () => {
      const { deleteCategory, snackbar, store } = useCategoriesView()
      vi.mocked(store.deleteCategory).mockRejectedValue(new Error('Delete failed'))

      const result = await deleteCategory('cat-123')

      expect(result).toBe(false)
      expect(snackbar.value.color).toBe('error')
    })
  })

  describe('reanalyzeDocuments', () => {
    it('should call API and show success snackbar', async () => {
      const { reanalyzeDocuments, snackbar } = useCategoriesView()
      vi.mocked(adminApi.reanalyzeDocuments).mockResolvedValue(
        mockAxiosResponse({ message: 'Started' })
      )

      const result = await reanalyzeDocuments('cat-123', true)

      expect(adminApi.reanalyzeDocuments).toHaveBeenCalledWith({
        category_id: 'cat-123',
        reanalyze_all: true,
      })
      expect(result).toBe(true)
      expect(snackbar.value.color).toBe('success')
    })

    it('should show error snackbar on failure', async () => {
      const { reanalyzeDocuments, snackbar } = useCategoriesView()
      vi.mocked(adminApi.reanalyzeDocuments).mockRejectedValue(new Error('API error'))

      const result = await reanalyzeDocuments('cat-123', false)

      expect(result).toBe(false)
      expect(snackbar.value.color).toBe('error')
    })
  })

  describe('loadSourcesForCategory', () => {
    it('should load sources and stats for a category', async () => {
      const { loadSourcesForCategory, categorySources, categorySourcesStats } = useCategoriesView()
      vi.mocked(adminApi.getSources).mockResolvedValue(
        mockAxiosResponse({
          items: [{ id: 'src-1', name: 'Source 1' }],
          total: 1,
        })
      )
      vi.mocked(adminApi.getSourceStatusStats).mockResolvedValue(
        mockAxiosResponse({
          total: 1,
          by_status: { ACTIVE: 1, PENDING: 0, ERROR: 0 },
        })
      )

      await loadSourcesForCategory('cat-123')

      expect(adminApi.getSources).toHaveBeenCalled()
      expect(adminApi.getSourceStatusStats).toHaveBeenCalled()
      expect(categorySources.value).toHaveLength(1)
      expect(categorySourcesStats.value.active).toBe(1)
    })
  })

  describe('Helper functions', () => {
    it('getLanguageFlag should return flag for known language', () => {
      const { getLanguageFlag } = useCategoriesView()

      expect(getLanguageFlag('de')).toBe('🇩🇪')
      expect(getLanguageFlag('en')).toBe('🇬🇧')
    })

    it('getLanguageFlag should return uppercase code for unknown language', () => {
      const { getLanguageFlag } = useCategoriesView()

      expect(getLanguageFlag('xyz')).toBe('XYZ')
    })

    it('getSourceTypeIcon should return correct icon', () => {
      const { getSourceTypeIcon } = useCategoriesView()

      expect(getSourceTypeIcon('WEBSITE')).toBe('mdi-web')
      expect(getSourceTypeIcon('OPARL_API')).toBe('mdi-api')
      expect(getSourceTypeIcon('RSS')).toBe('mdi-rss')
      expect(getSourceTypeIcon(undefined)).toBe('mdi-database')
    })
  })
})

// ==========================================================================
// useCategoryCrawler
// ==========================================================================

describe('useCategoryCrawler', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('Initial State', () => {
    it('should have correct initial state', () => {
      const crawler = useCategoryCrawler()

      expect(crawler.crawlerDialog.value).toBe(false)
      expect(crawler.startingCrawler.value).toBe(false)
      expect(crawler.selectedCategoryForCrawler.value).toBeNull()
      expect(crawler.crawlerFilteredCount.value).toBe(0)
    })
  })

  describe('openCrawlerDialog', () => {
    it('should open dialog with category', () => {
      const crawler = useCategoryCrawler()
      vi.mocked(adminApi.getSources).mockResolvedValue(
        mockAxiosResponse({ items: [], total: 5 })
      )

      crawler.openCrawlerDialog(mockCategory)

      expect(crawler.crawlerDialog.value).toBe(true)
      expect(crawler.selectedCategoryForCrawler.value).toEqual(mockCategory)
      expect(crawler.crawlerFilteredCount.value).toBe(5) // from category.source_count
    })
  })

  describe('startFilteredCrawl', () => {
    it('should start crawl and close dialog', async () => {
      const crawler = useCategoryCrawler()
      crawler.selectedCategoryForCrawler.value = mockCategory
      crawler.crawlerDialog.value = true
      vi.mocked(adminApi.startCrawl).mockResolvedValue(mockAxiosResponse({}))

      const result = await crawler.startFilteredCrawl()

      expect(adminApi.startCrawl).toHaveBeenCalled()
      expect(result).toHaveProperty('success', true)
      expect(crawler.crawlerDialog.value).toBe(false)
    })

    it('should return error result on failure', async () => {
      const crawler = useCategoryCrawler()
      crawler.selectedCategoryForCrawler.value = mockCategory
      vi.mocked(adminApi.startCrawl).mockRejectedValue(new Error('API error'))

      const result = await crawler.startFilteredCrawl()

      expect(result).toHaveProperty('success', false)
    })

    it('should not start if no category selected', async () => {
      const crawler = useCategoryCrawler()
      crawler.selectedCategoryForCrawler.value = null

      const result = await crawler.startFilteredCrawl()

      expect(result.success).toBe(false)
      expect(adminApi.startCrawl).not.toHaveBeenCalled()
    })
  })

  describe('resetCrawlerFilters', () => {
    it('should reset all filters', () => {
      const crawler = useCategoryCrawler()
      crawler.crawlerFilter.value = {
        search: 'test',
        limit: 100,
        status: 'ACTIVE',
        source_type: 'WEBSITE',
      }

      crawler.resetCrawlerFilters()

      expect(crawler.crawlerFilter.value.search).toBeNull()
      expect(crawler.crawlerFilter.value.limit).toBeNull()
      expect(crawler.crawlerFilter.value.status).toBeNull()
      expect(crawler.crawlerFilter.value.source_type).toBeNull()
    })
  })
})

// ==========================================================================
// useCategoryDataSources
// ==========================================================================

describe('useCategoryDataSources', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('Initial State', () => {
    it('should have correct initial state', () => {
      const dataSources = useCategoryDataSources()

      expect(dataSources.dataSourcesTab.value.selectedTags).toEqual([])
      expect(dataSources.dataSourcesTab.value.matchMode).toBe('all')
      expect(dataSources.dataSourcesTab.value.foundSources).toEqual([])
      expect(dataSources.dataSourcesTab.value.loading).toBe(false)
    })
  })

  describe('loadAvailableTags', () => {
    it('should load tags from API', async () => {
      const dataSources = useCategoryDataSources()
      vi.mocked(adminApi.getAvailableTags).mockResolvedValue(
        mockAxiosResponse({
          tags: [{ tag: 'tag1' }, { tag: 'tag2' }],
        })
      )

      await dataSources.loadAvailableTags()

      expect(dataSources.dataSourcesTab.value.availableTags).toEqual(['tag1', 'tag2'])
    })

    it('should set empty array on error', async () => {
      const dataSources = useCategoryDataSources()
      vi.mocked(adminApi.getAvailableTags).mockRejectedValue(new Error('API error'))

      await expect(dataSources.loadAvailableTags()).rejects.toThrow()
      expect(dataSources.dataSourcesTab.value.availableTags).toEqual([])
    })
  })

  describe('searchSourcesByTags', () => {
    it('should not search if no tags selected', async () => {
      const dataSources = useCategoryDataSources()
      dataSources.dataSourcesTab.value.selectedTags = []

      await dataSources.searchSourcesByTags('cat-123', [])

      expect(adminApi.getSourcesByTags).not.toHaveBeenCalled()
      expect(dataSources.dataSourcesTab.value.foundSources).toEqual([])
    })

    it('should search sources by tags', async () => {
      const dataSources = useCategoryDataSources()
      dataSources.dataSourcesTab.value.selectedTags = ['tag1']
      vi.mocked(adminApi.getSourcesByTags).mockResolvedValue(
        mockAxiosResponse([{ id: 'src-1', name: 'Source 1' }])
      )

      await dataSources.searchSourcesByTags('cat-123', [])

      expect(adminApi.getSourcesByTags).toHaveBeenCalledWith({
        tags: ['tag1'],
        match_mode: 'all',
        exclude_category_id: 'cat-123',
        limit: 1000,
      })
      expect(dataSources.dataSourcesTab.value.foundSources).toHaveLength(1)
    })
  })

  describe('assignSourcesByTags', () => {
    it('should not assign if no tags selected', async () => {
      const dataSources = useCategoryDataSources()
      dataSources.dataSourcesTab.value.selectedTags = []

      const result = await dataSources.assignSourcesByTags('cat-123')

      // Returns NO_OP_RESULT when no tags selected
      expect(result).toEqual({ success: true, count: 0 })
      expect(categoryApi.assignSourcesByTags).not.toHaveBeenCalled()
    })

    it('should assign sources by tags', async () => {
      const dataSources = useCategoryDataSources()
      dataSources.dataSourcesTab.value.selectedTags = ['tag1']
      vi.mocked(categoryApi.assignSourcesByTags).mockResolvedValue(
        mockAxiosResponse({ assigned: 5 })
      )

      const result = await dataSources.assignSourcesByTags('cat-123')

      expect(categoryApi.assignSourcesByTags).toHaveBeenCalledWith('cat-123', {
        tags: ['tag1'],
        match_mode: 'all',
        mode: 'add',
      })
      expect(result?.success).toBe(true)
      expect(result?.count).toBe(5)
    })
  })

  describe('resetDataSourcesTab', () => {
    it('should reset tab state but preserve available tags', () => {
      const dataSources = useCategoryDataSources()
      dataSources.dataSourcesTab.value = {
        selectedTags: ['tag1'],
        matchMode: 'any',
        foundSources: [{ id: 'src-1', name: 'Source 1' }],
        loading: true,
        assigning: true,
        availableTags: ['tag1', 'tag2', 'tag3'],
        pendingSourceIds: [],
        directSelectedSources: [],
        sourceSearchResults: [],
        searchingDirectSources: false,
        assignedSources: [],
        assignedSourcesTotal: 0,
        assignedSourcesLoading: false,
        assignedSourcesPage: 1,
        assignedSourcesPerPage: 25,
        assignedSourcesSearch: '',
        assignedSourcesTagFilter: [],
        availableTagsInAssigned: [],
      }

      dataSources.resetDataSourcesTab()

      expect(dataSources.dataSourcesTab.value.selectedTags).toEqual([])
      expect(dataSources.dataSourcesTab.value.matchMode).toBe('all')
      expect(dataSources.dataSourcesTab.value.foundSources).toEqual([])
      expect(dataSources.dataSourcesTab.value.loading).toBe(false)
      expect(dataSources.dataSourcesTab.value.assigning).toBe(false)
      // Available tags should be preserved
      expect(dataSources.dataSourcesTab.value.availableTags).toEqual(['tag1', 'tag2', 'tag3'])
    })
  })
})
