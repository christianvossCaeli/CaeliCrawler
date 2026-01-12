/**
 * Tests for Categories Pinia Store
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useCategoriesStore } from './categories'
import type { CategoryResponse, CategoryListResponse, CategoryStats } from '@/types/category'
import { mockAxiosResponse } from '@/test/setup'

// Mock the API module
vi.mock('@/services/api/categories', () => ({
  categoryApi: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    getStats: vi.fn(),
  },
}))

// Mock logger
vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}))

// Import mocked module
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
  schedule_cron: '',
  schedule_enabled: false,
  extraction_handler: 'default',
  ai_extraction_prompt: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  source_count: 0,
  document_count: 0,
  target_entity_type_id: null,
  target_entity_type: null,
}

const mockCategory2: CategoryResponse = {
  ...mockCategory,
  id: 'cat-456',
  name: 'Second Category',
  slug: 'second-category',
  schedule_enabled: true,
}

const mockListResponse: CategoryListResponse = {
  items: [mockCategory, mockCategory2],
  total: 2,
  page: 1,
  pages: 1,
  per_page: 20,
}

describe('Categories Store', () => {
  let store: ReturnType<typeof useCategoriesStore>

  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    store = useCategoriesStore()
  })

  // ==========================================================================
  // Initial State
  // ==========================================================================

  describe('Initial State', () => {
    it('should have empty categories', () => {
      expect(store.categories).toEqual([])
    })

    it('should have no selected category', () => {
      expect(store.selectedCategory).toBeNull()
    })

    it('should have loading as false', () => {
      expect(store.loading).toBe(false)
    })

    it('should have default pagination', () => {
      expect(store.pagination.page).toBe(1)
      expect(store.pagination.perPage).toBe(20)
      expect(store.pagination.total).toBe(0)
      expect(store.pagination.totalPages).toBe(0)
      expect(store.pagination.sortBy).toBe('name')
      expect(store.pagination.sortOrder).toBe('asc')
    })

    it('should have default filters', () => {
      expect(store.filters.search).toBe('')
      expect(store.filters.status).toBeNull()
    })
  })

  // ==========================================================================
  // Computed Properties
  // ==========================================================================

  describe('Computed Properties', () => {
    describe('hasCategories', () => {
      it('should return false when no categories', () => {
        expect(store.hasCategories).toBe(false)
      })

      it('should return true when categories exist', () => {
        store.categories = [mockCategory]
        expect(store.hasCategories).toBe(true)
      })
    })

    describe('scheduledCategories', () => {
      it('should return only scheduled categories', () => {
        store.categories = [mockCategory, mockCategory2]
        expect(store.scheduledCategories).toHaveLength(1)
        expect(store.scheduledCategories[0].id).toBe('cat-456')
      })
    })

    describe('categoryOptions', () => {
      it('should return value/label pairs', () => {
        store.categories = [mockCategory]
        expect(store.categoryOptions).toEqual([
          { value: 'cat-123', label: 'Test Category' },
        ])
      })
    })

    describe('getById', () => {
      it('should return category from list', () => {
        store.categories = [mockCategory]
        const result = store.getById('cat-123')
        expect(result).toEqual(mockCategory)
      })

      it('should return undefined for unknown id', () => {
        const result = store.getById('unknown')
        expect(result).toBeUndefined()
      })
    })
  })

  // ==========================================================================
  // Fetch Categories
  // ==========================================================================

  describe('fetchCategories', () => {
    it('should set loading to true during fetch', async () => {
      vi.mocked(categoryApi.list).mockImplementation(async () => {
        expect(store.loading).toBe(true)
        return mockAxiosResponse(mockListResponse)
      })

      await store.fetchCategories()

      expect(store.loading).toBe(false)
    })

    it('should populate categories from response', async () => {
      vi.mocked(categoryApi.list).mockResolvedValue(
        mockAxiosResponse(mockListResponse)
      )

      await store.fetchCategories()

      expect(store.categories).toHaveLength(2)
      expect(store.categories[0]).toEqual(mockCategory)
    })

    it('should update pagination from response', async () => {
      vi.mocked(categoryApi.list).mockResolvedValue(
        mockAxiosResponse(mockListResponse)
      )

      await store.fetchCategories()

      expect(store.pagination.page).toBe(1)
      expect(store.pagination.perPage).toBe(20)
      expect(store.pagination.total).toBe(2)
      expect(store.pagination.totalPages).toBe(1)
    })

    it('should use filter params', async () => {
      store.filters.search = 'test'
      store.filters.scheduled = 'scheduled'

      vi.mocked(categoryApi.list).mockResolvedValue(
        mockAxiosResponse(mockListResponse)
      )

      await store.fetchCategories()

      expect(categoryApi.list).toHaveBeenCalledWith(
        expect.objectContaining({
          search: 'test',
          scheduled_only: true,
        })
      )
    })

    it('should accept custom params', async () => {
      vi.mocked(categoryApi.list).mockResolvedValue(
        mockAxiosResponse(mockListResponse)
      )

      await store.fetchCategories({ page: 2, per_page: 10 })

      expect(categoryApi.list).toHaveBeenCalledWith(
        expect.objectContaining({
          page: 2,
          per_page: 10,
        })
      )
    })

    it('should throw on error', async () => {
      vi.mocked(categoryApi.list).mockRejectedValue(new Error('API Error'))

      await expect(store.fetchCategories()).rejects.toThrow('API Error')
    })
  })

  // ==========================================================================
  // Fetch Single Category
  // ==========================================================================

  describe('fetchCategory', () => {
    it('should return cached category if valid', async () => {
      // Pre-populate cache by fetching list
      vi.mocked(categoryApi.list).mockResolvedValue(
        mockAxiosResponse(mockListResponse)
      )
      await store.fetchCategories()

      const result = await store.fetchCategory('cat-123')

      expect(result).toEqual(mockCategory)
      expect(categoryApi.get).not.toHaveBeenCalled()
    })

    it('should fetch from API when not cached', async () => {
      vi.mocked(categoryApi.get).mockResolvedValue(
        mockAxiosResponse(mockCategory)
      )

      const result = await store.fetchCategory('cat-123')

      expect(result).toEqual(mockCategory)
      expect(categoryApi.get).toHaveBeenCalledWith('cat-123')
    })

    it('should force refresh when requested', async () => {
      // Pre-populate cache
      vi.mocked(categoryApi.list).mockResolvedValue(
        mockAxiosResponse(mockListResponse)
      )
      await store.fetchCategories()

      vi.mocked(categoryApi.get).mockResolvedValue(
        mockAxiosResponse({ ...mockCategory, name: 'Updated Name' })
      )

      const result = await store.fetchCategory('cat-123', true)

      expect(result.name).toBe('Updated Name')
      expect(categoryApi.get).toHaveBeenCalled()
    })
  })

  // ==========================================================================
  // Create Category
  // ==========================================================================

  describe('createCategory', () => {
    it('should create category and refresh list', async () => {
      vi.mocked(categoryApi.create).mockResolvedValue(
        mockAxiosResponse(mockCategory)
      )
      vi.mocked(categoryApi.list).mockResolvedValue(
        mockAxiosResponse(mockListResponse)
      )

      const result = await store.createCategory({
        name: 'Test Category',
        purpose: 'Testing',
        languages: ['de'],
        search_terms: [],
        document_types: [],
      })

      expect(result).toEqual(mockCategory)
      expect(categoryApi.create).toHaveBeenCalled()
      expect(categoryApi.list).toHaveBeenCalled()
    })
  })

  // ==========================================================================
  // Update Category
  // ==========================================================================

  describe('updateCategory', () => {
    it('should update category and update in list', async () => {
      store.categories = [mockCategory]

      const updatedCategory = { ...mockCategory, name: 'Updated Name' }
      vi.mocked(categoryApi.update).mockResolvedValue(
        mockAxiosResponse(updatedCategory)
      )

      const result = await store.updateCategory('cat-123', { name: 'Updated Name' })

      expect(result.name).toBe('Updated Name')
      expect(store.categories[0].name).toBe('Updated Name')
    })

    it('should update selected category if same', async () => {
      store.selectedCategory = mockCategory

      const updatedCategory = { ...mockCategory, name: 'Updated Name' }
      vi.mocked(categoryApi.update).mockResolvedValue(
        mockAxiosResponse(updatedCategory)
      )

      await store.updateCategory('cat-123', { name: 'Updated Name' })

      expect(store.selectedCategory?.name).toBe('Updated Name')
    })
  })

  // ==========================================================================
  // Delete Category
  // ==========================================================================

  describe('deleteCategory', () => {
    it('should delete category and remove from list', async () => {
      store.categories = [mockCategory, mockCategory2]

      vi.mocked(categoryApi.delete).mockResolvedValue(
        mockAxiosResponse(null)
      )

      await store.deleteCategory('cat-123')

      expect(store.categories).toHaveLength(1)
      expect(store.categories[0].id).toBe('cat-456')
    })

    it('should clear selected category if deleted', async () => {
      store.selectedCategory = mockCategory

      vi.mocked(categoryApi.delete).mockResolvedValue(
        mockAxiosResponse(null)
      )

      await store.deleteCategory('cat-123')

      expect(store.selectedCategory).toBeNull()
    })

    it('should update pagination total', async () => {
      store.pagination.total = 2
      store.categories = [mockCategory]

      vi.mocked(categoryApi.delete).mockResolvedValue(
        mockAxiosResponse(null)
      )

      await store.deleteCategory('cat-123')

      expect(store.pagination.total).toBe(1)
    })
  })

  // ==========================================================================
  // Category Stats
  // ==========================================================================

  describe('getCategoryStats', () => {
    const mockStats: CategoryStats = {
      id: 'cat-123',
      name: 'Test Category',
      source_count: 10,
      document_count: 100,
      extracted_count: 50,
      active_jobs: 0,
    }

    it('should fetch and cache stats', async () => {
      vi.mocked(categoryApi.getStats).mockResolvedValue(
        mockAxiosResponse(mockStats)
      )

      const result = await store.getCategoryStats('cat-123')

      expect(result).toEqual(mockStats)
    })

    it('should return cached stats on subsequent calls', async () => {
      vi.mocked(categoryApi.getStats).mockResolvedValue(
        mockAxiosResponse(mockStats)
      )

      await store.getCategoryStats('cat-123')
      await store.getCategoryStats('cat-123')

      expect(categoryApi.getStats).toHaveBeenCalledTimes(1)
    })

    it('should force refresh when requested', async () => {
      vi.mocked(categoryApi.getStats).mockResolvedValue(
        mockAxiosResponse(mockStats)
      )

      await store.getCategoryStats('cat-123')
      await store.getCategoryStats('cat-123', true)

      expect(categoryApi.getStats).toHaveBeenCalledTimes(2)
    })
  })

  // ==========================================================================
  // Selection & Filters
  // ==========================================================================

  describe('Selection & Filters', () => {
    describe('selectCategory', () => {
      it('should set selected category', () => {
        store.selectCategory(mockCategory)
        expect(store.selectedCategory).toEqual(mockCategory)
      })

      it('should clear selected category', () => {
        store.selectedCategory = mockCategory
        store.selectCategory(null)
        expect(store.selectedCategory).toBeNull()
      })
    })

    describe('setFilters', () => {
      it('should update filters', () => {
        store.setFilters({ search: 'test', status: 'active' })
        expect(store.filters.search).toBe('test')
        expect(store.filters.status).toBe('active')
      })

      it('should merge with existing filters', () => {
        store.filters.search = 'existing'
        store.setFilters({ status: 'inactive' })
        expect(store.filters.search).toBe('existing')
        expect(store.filters.status).toBe('inactive')
      })
    })

    describe('resetFilters', () => {
      it('should reset filters to defaults', () => {
        store.filters.search = 'test'
        store.filters.status = 'active'

        store.resetFilters()

        expect(store.filters.search).toBe('')
        expect(store.filters.status).toBeNull()
      })
    })

    describe('setPagination', () => {
      it('should update pagination', () => {
        store.setPagination({ page: 2, perPage: 50 })
        expect(store.pagination.page).toBe(2)
        expect(store.pagination.perPage).toBe(50)
      })
    })
  })

  // ==========================================================================
  // Cache Management
  // ==========================================================================

  describe('Cache Management', () => {
    describe('clearCache', () => {
      it('should clear all caches', async () => {
        // Populate caches
        vi.mocked(categoryApi.list).mockResolvedValue(
          mockAxiosResponse(mockListResponse)
        )
        await store.fetchCategories()

        store.clearCache()

        // Fetching should now require API call
        vi.mocked(categoryApi.get).mockResolvedValue(
          mockAxiosResponse(mockCategory)
        )
        await store.fetchCategory('cat-123')
        expect(categoryApi.get).toHaveBeenCalled()
      })
    })

    describe('invalidateCache', () => {
      it('should invalidate specific category cache', async () => {
        // Populate cache
        vi.mocked(categoryApi.list).mockResolvedValue(
          mockAxiosResponse(mockListResponse)
        )
        await store.fetchCategories()

        store.invalidateCache('cat-123')

        // Fetching should now require API call
        vi.mocked(categoryApi.get).mockResolvedValue(
          mockAxiosResponse(mockCategory)
        )
        await store.fetchCategory('cat-123')
        expect(categoryApi.get).toHaveBeenCalled()
      })
    })
  })

  // ==========================================================================
  // Reset Store
  // ==========================================================================

  describe('$reset', () => {
    it('should reset all state to defaults', async () => {
      // Populate state
      vi.mocked(categoryApi.list).mockResolvedValue(
        mockAxiosResponse(mockListResponse)
      )
      await store.fetchCategories()
      store.selectedCategory = mockCategory
      store.filters.search = 'test'
      store.pagination.page = 5

      store.$reset()

      expect(store.categories).toEqual([])
      expect(store.selectedCategory).toBeNull()
      expect(store.loading).toBe(false)
      expect(store.pagination.page).toBe(1)
      expect(store.filters.search).toBe('')
    })
  })
})
