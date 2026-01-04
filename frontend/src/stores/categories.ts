/**
 * Categories Pinia Store
 *
 * Centralized state management for categories with caching,
 * pagination, and cross-component state access.
 */
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { categoryApi } from '@/services/api/categories'
import { useLogger } from '@/composables/useLogger'
import type {
  CategoryResponse,
  CategoryListResponse,
  CategoryCreate,
  CategoryUpdate,
  CategoryListParams,
  CategoryStats,
  CategoryFilters,
} from '@/types/category'
import { DEFAULT_CATEGORY_FILTERS } from '@/types/category'

const logger = useLogger('categoriesStore')

/**
 * Pagination state
 */
interface PaginationState {
  page: number
  perPage: number
  total: number
  totalPages: number
  sortBy: string
  sortOrder: 'asc' | 'desc'
}

/**
 * Default pagination state
 */
const DEFAULT_PAGINATION: PaginationState = {
  page: 1,
  perPage: 20,
  total: 0,
  totalPages: 0,
  sortBy: 'name',
  sortOrder: 'asc',
}

/**
 * Cache entry with timestamp for expiration
 */
interface CacheEntry<T> {
  data: T
  timestamp: number
}

/**
 * Cache expiration time (5 minutes)
 */
const CACHE_TTL = 5 * 60 * 1000

export const useCategoriesStore = defineStore('categories', () => {
  // ============================================
  // State
  // ============================================

  /** List of categories */
  const categories = ref<CategoryResponse[]>([])

  /** Currently selected category */
  const selectedCategory = ref<CategoryResponse | null>(null)

  /** Loading state */
  const loading = ref(false)

  /** Pagination state */
  const pagination = ref<PaginationState>({ ...DEFAULT_PAGINATION })

  /** Filter state */
  const filters = ref<CategoryFilters>({ ...DEFAULT_CATEGORY_FILTERS })

  /** Cache for individual categories by ID */
  const cache = ref(new Map<string, CacheEntry<CategoryResponse>>())

  /** Cache for category stats */
  const statsCache = ref(new Map<string, CacheEntry<CategoryStats>>())

  // ============================================
  // Getters / Computed
  // ============================================

  /**
   * Get category by ID from cache or list
   */
  const getById = computed(() => (id: string): CategoryResponse | undefined => {
    // Check cache first
    const cached = cache.value.get(id)
    if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
      return cached.data
    }

    // Fall back to list
    return categories.value.find((c) => c.id === id)
  })

  /**
   * Check if categories are loaded
   */
  const hasCategories = computed(() => categories.value.length > 0)

  /**
   * Get active categories only
   */
  const activeCategories = computed(() =>
    categories.value.filter((c) => c.is_active)
  )

  /**
   * Get category options for select inputs
   */
  const categoryOptions = computed(() =>
    categories.value.map((c) => ({
      value: c.id,
      label: c.name,
    }))
  )

  // ============================================
  // Actions
  // ============================================

  /**
   * Fetch categories with current pagination and filters
   */
  async function fetchCategories(params?: Partial<CategoryListParams>) {
    loading.value = true

    try {
      const queryParams: CategoryListParams = {
        page: params?.page ?? pagination.value.page,
        per_page: params?.per_page ?? pagination.value.perPage,
        search: filters.value.search || undefined,
        is_active:
          filters.value.status === 'active'
            ? true
            : filters.value.status === 'inactive'
              ? false
              : undefined,
        ...params,
      }

      const response = await categoryApi.list(queryParams)
      const data: CategoryListResponse = response.data

      categories.value = data.items
      pagination.value = {
        ...pagination.value,
        page: data.page,
        perPage: data.per_page,
        total: data.total,
        totalPages: data.pages,
      }

      // Update cache with fetched items
      data.items.forEach((category) => {
        cache.value.set(category.id, {
          data: category,
          timestamp: Date.now(),
        })
      })

      logger.debug(
        `Fetched ${data.items.length} categories (page ${data.page}/${data.pages})`
      )
    } catch (error) {
      logger.error('Failed to fetch categories:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch a single category by ID
   */
  async function fetchCategory(id: string, forceRefresh = false): Promise<CategoryResponse> {
    // Check cache if not forcing refresh
    if (!forceRefresh) {
      const cached = cache.value.get(id)
      if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
        return cached.data
      }
    }

    try {
      const response = await categoryApi.get(id)
      const category = response.data

      // Update cache
      cache.value.set(id, {
        data: category,
        timestamp: Date.now(),
      })

      return category
    } catch (error) {
      logger.error(`Failed to fetch category ${id}:`, error)
      throw error
    }
  }

  /**
   * Create a new category
   */
  async function createCategory(data: CategoryCreate): Promise<CategoryResponse> {
    try {
      const response = await categoryApi.create(data)
      const category = response.data

      // Add to cache
      cache.value.set(category.id, {
        data: category,
        timestamp: Date.now(),
      })

      // Refresh list
      await fetchCategories()

      logger.info(`Created category: ${category.name}`)
      return category
    } catch (error) {
      logger.error('Failed to create category:', error)
      throw error
    }
  }

  /**
   * Update an existing category
   */
  async function updateCategory(
    id: string,
    data: CategoryUpdate
  ): Promise<CategoryResponse> {
    try {
      const response = await categoryApi.update(id, data)
      const category = response.data

      // Update cache
      cache.value.set(id, {
        data: category,
        timestamp: Date.now(),
      })

      // Update in list
      const index = categories.value.findIndex((c) => c.id === id)
      if (index >= 0) {
        categories.value[index] = category
      }

      // Update selected if it's the same
      if (selectedCategory.value?.id === id) {
        selectedCategory.value = category
      }

      logger.info(`Updated category: ${category.name}`)
      return category
    } catch (error) {
      logger.error(`Failed to update category ${id}:`, error)
      throw error
    }
  }

  /**
   * Delete a category
   */
  async function deleteCategory(id: string): Promise<void> {
    try {
      await categoryApi.delete(id)

      // Remove from cache
      cache.value.delete(id)
      statsCache.value.delete(id)

      // Remove from list
      categories.value = categories.value.filter((c) => c.id !== id)

      // Clear selected if it was deleted
      if (selectedCategory.value?.id === id) {
        selectedCategory.value = null
      }

      // Update total
      pagination.value.total = Math.max(0, pagination.value.total - 1)

      logger.info(`Deleted category ${id}`)
    } catch (error) {
      logger.error(`Failed to delete category ${id}:`, error)
      throw error
    }
  }

  /**
   * Get category statistics
   */
  async function getCategoryStats(
    id: string,
    forceRefresh = false
  ): Promise<CategoryStats> {
    // Check cache if not forcing refresh
    if (!forceRefresh) {
      const cached = statsCache.value.get(id)
      if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
        return cached.data
      }
    }

    try {
      const response = await categoryApi.getStats(id)
      const stats = response.data

      // Update cache
      statsCache.value.set(id, {
        data: stats,
        timestamp: Date.now(),
      })

      return stats
    } catch (error) {
      logger.error(`Failed to fetch stats for category ${id}:`, error)
      throw error
    }
  }

  /**
   * Select a category
   */
  function selectCategory(category: CategoryResponse | null) {
    selectedCategory.value = category
  }

  /**
   * Update filters
   */
  function setFilters(newFilters: Partial<CategoryFilters>) {
    filters.value = { ...filters.value, ...newFilters }
  }

  /**
   * Reset filters to defaults
   */
  function resetFilters() {
    filters.value = { ...DEFAULT_CATEGORY_FILTERS }
  }

  /**
   * Update pagination
   */
  function setPagination(updates: Partial<PaginationState>) {
    pagination.value = { ...pagination.value, ...updates }
  }

  /**
   * Clear cache
   */
  function clearCache() {
    cache.value.clear()
    statsCache.value.clear()
  }

  /**
   * Invalidate cache for a specific category
   */
  function invalidateCache(id: string) {
    cache.value.delete(id)
    statsCache.value.delete(id)
  }

  /**
   * Reset store to initial state
   */
  function $reset() {
    categories.value = []
    selectedCategory.value = null
    loading.value = false
    pagination.value = { ...DEFAULT_PAGINATION }
    filters.value = { ...DEFAULT_CATEGORY_FILTERS }
    cache.value.clear()
    statsCache.value.clear()
  }

  return {
    // State
    categories,
    selectedCategory,
    loading,
    pagination,
    filters,

    // Getters
    getById,
    hasCategories,
    activeCategories,
    categoryOptions,

    // Actions
    fetchCategories,
    fetchCategory,
    createCategory,
    updateCategory,
    deleteCategory,
    getCategoryStats,
    selectCategory,
    setFilters,
    resetFilters,
    setPagination,
    clearCache,
    invalidateCache,
    $reset,
  }
})

export default useCategoriesStore
