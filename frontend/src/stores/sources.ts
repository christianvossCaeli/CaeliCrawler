/**
 * Sources Store
 *
 * Central state management for the Sources management view.
 * Uses Pinia composition API with Vue 3.5+ features.
 *
 * @module stores/sources
 *
 * ## Features
 * - Data source CRUD with optimistic updates
 * - Category management (N:M relationships)
 * - Tag management with autocomplete
 * - Entity linking (N:M) with debounced search
 * - SharePoint integration with connection testing
 * - Bulk CSV import with validation/preview
 * - Filter state with sidebar count aggregation
 *
 * ## Usage
 * ```typescript
 * import { useSourcesStore } from '@/stores/sources'
 * const store = useSourcesStore()
 * await store.initialize()
 * ```
 *
 * ## Error Handling
 * Uses centralized `withApiErrorHandling` utility.
 * Errors stored in `error` ref, clear with `clearError()`.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import { adminApi, entityApi } from '@/services/api'
import type {
  DataSourceResponse,
  DataSourceCreate,
  DataSourceUpdate,
  DataSourceListParams,
  DataSourceFormData,
  DataSourceBulkImport,
  DataSourceBulkImportResult,
  BulkImportState,
  SourcesFiltersState,
  SidebarCounts,
  SharePointTestResult,
  TagCount,
  SourceType,
} from '@/types/sources'
import { createDefaultFormData, createDefaultFilters, DEFAULT_CRAWL_CONFIG, getApiErrorMessage, isSourceType } from '@/types/sources'
import type { CategoryResponse } from '@/types/category'
import { parseCsv } from '@/utils/csvParser'
import { withApiErrorHandling, withLoadingState } from '@/utils/apiErrorHandler'
import { useLogger } from '@/composables/useLogger'
import { SOURCES_PAGINATION, ENTITY_SEARCH, BULK_IMPORT } from '@/config/sources'
import type { EntityBrief } from '@/stores/entity'

// Re-export helper functions and types for consumers
export { createDefaultFormData, createDefaultFilters }
export type { EntityBrief }

// =============================================================================
// Store Definition
// =============================================================================

export const useSourcesStore = defineStore('sources', () => {
  const logger = useLogger('SourcesStore')

  // ==========================================================================
  // State
  // ==========================================================================

  // Data sources
  const sources = ref<DataSourceResponse[]>([])
  const sourcesLoading = ref(false)
  const sourcesTotal = ref(0)
  const currentPage = ref(1)
  const itemsPerPage = ref(50)

  // Categories
  const categories = ref<CategoryResponse[]>([])
  const categoriesLoading = ref(false)

  // Tags
  const availableTags = ref<TagCount[]>([])
  const tagsLoading = ref(false)

  // Sidebar counts
  const sidebarCounts = ref<SidebarCounts>({
    total: 0,
    categories: [],
    types: [],
    statuses: [],
  })

  // Filters
  const filters = ref<SourcesFiltersState>({
    category_id: null,
    source_type: null,
    status: null,
    search: '',
    tags: [],
  })

  // Form state - use centralized factory function
  const formData = ref<DataSourceFormData>(createDefaultFormData())

  // Dialog state
  const editMode = ref(false)
  const selectedSource = ref<DataSourceResponse | null>(null)
  const selectedCategoryInfo = ref<CategoryResponse | null>(null)
  const saving = ref(false)

  // Entity linking (N:M)
  const selectedEntities = ref<EntityBrief[]>([])
  const entitySearchResults = ref<EntityBrief[]>([])
  const searchingEntities = ref(false)

  // SharePoint test
  const sharepointTesting = ref(false)
  const sharepointTestResult = ref<SharePointTestResult | null>(null)

  // Bulk import state
  const bulkImport = ref<BulkImportState>({
    category_ids: [],
    default_tags: [],
    inputMode: 'text',
    csvText: '',
    csvFile: null,
    preview: [],
    validCount: 0,
    duplicateCount: 0,
    errorCount: 0,
    importing: false,
    skip_duplicates: true,
  })

  // Error handling
  const error = ref<string | null>(null)

  // ==========================================================================
  // Computed
  // ==========================================================================

  const hasActiveFilters = computed(() => {
    return !!(
      filters.value.category_id ||
      filters.value.source_type ||
      filters.value.status ||
      filters.value.tags.length > 0
    )
  })

  const tagSuggestions = computed(() => availableTags.value.map((t) => t.tag))

  const canPreviewBulkImport = computed(() => {
    if (bulkImport.value.inputMode === 'text') {
      return bulkImport.value.csvText.trim().length > 0
    }
    return bulkImport.value.csvFile !== null
  })

  const canExecuteBulkImport = computed(() => {
    return bulkImport.value.category_ids.length > 0 && bulkImport.value.validCount > 0
  })

  // ==========================================================================
  // Data Source Actions
  // ==========================================================================

  async function fetchSources(page = 1, perPage = itemsPerPage.value): Promise<void> {
    await withLoadingState(async () => {
      await withApiErrorHandling(
        async () => {
          const params: DataSourceListParams = {
            ...filters.value,
            page,
            per_page: perPage,
          }
          // Don't send empty tags array
          if (!params.tags || params.tags.length === 0) {
            delete params.tags
          }
          const response = await adminApi.getSources(params)
          sources.value = response.data.items
          sourcesTotal.value = response.data.total
          currentPage.value = page
          return response
        },
        { errorRef: error, fallbackMessage: 'Failed to load sources' }
      )
    }, sourcesLoading)
  }

  async function createSource(data: DataSourceCreate): Promise<DataSourceResponse> {
    return await withLoadingState(async () => {
      const result = await withApiErrorHandling(
        async () => {
          const response = await adminApi.createSource(data)
          // Reload sources and sidebar counts
          await Promise.all([fetchSources(), fetchSidebarCounts(), fetchAvailableTags()])
          return response.data
        },
        { errorRef: error, fallbackMessage: 'Failed to create source' }
      )
      return result as DataSourceResponse
    }, saving)
  }

  async function updateSource(id: string, data: DataSourceUpdate): Promise<DataSourceResponse> {
    return await withLoadingState(async () => {
      const result = await withApiErrorHandling(
        async () => {
          const response = await adminApi.updateSource(id, data)
          // Update in local state
          const index = sources.value.findIndex((s) => s.id === id)
          if (index >= 0) {
            sources.value[index] = response.data
          }
          // Reload sidebar counts and tags
          await Promise.all([fetchSidebarCounts(), fetchAvailableTags()])
          return response.data
        },
        { errorRef: error, fallbackMessage: 'Failed to update source' }
      )
      return result as DataSourceResponse
    }, saving)
  }

  async function deleteSource(id: string): Promise<void> {
    await withApiErrorHandling(
      async () => {
        await adminApi.deleteSource(id)
        sources.value = sources.value.filter((s) => s.id !== id)
        sourcesTotal.value--
        // Reload sidebar counts
        await fetchSidebarCounts()
      },
      { errorRef: error, fallbackMessage: 'Failed to delete source' }
    )
  }

  async function startCrawl(source: DataSourceResponse): Promise<void> {
    await withApiErrorHandling(
      () => adminApi.startCrawl({ source_ids: [source.id] }),
      { errorRef: error, fallbackMessage: 'Failed to start crawl' }
    )
  }

  async function resetSource(source: DataSourceResponse): Promise<void> {
    await withApiErrorHandling(
      async () => {
        await adminApi.resetSource(source.id)
        await fetchSources(currentPage.value)
      },
      { errorRef: error, fallbackMessage: 'Failed to reset source' }
    )
  }

  // ==========================================================================
  // Category Actions
  // ==========================================================================

  async function fetchCategories(): Promise<void> {
    await withLoadingState(async () => {
      await withApiErrorHandling(
        async () => {
          const response = await adminApi.getCategories({ per_page: SOURCES_PAGINATION.CATEGORIES_PER_PAGE })
          categories.value = response.data.items
          return response
        },
        { errorRef: error, fallbackMessage: 'Failed to load categories' }
      )
    }, categoriesLoading)
  }

  // ==========================================================================
  // Sidebar & Tags Actions
  // ==========================================================================

  async function fetchSidebarCounts(): Promise<void> {
    try {
      const response = await adminApi.getSourceCounts()
      sidebarCounts.value = response.data
    } catch (err: unknown) {
      logger.warn('Failed to load sidebar counts', err)
    }
  }

  async function fetchAvailableTags(): Promise<void> {
    tagsLoading.value = true
    try {
      const response = await adminApi.getAvailableTags()
      availableTags.value = response.data.tags || []
    } catch (err: unknown) {
      logger.warn('Failed to load available tags', err)
    } finally {
      tagsLoading.value = false
    }
  }

  // ==========================================================================
  // Filter Actions
  // ==========================================================================

  function setFilter<K extends keyof SourcesFiltersState>(
    key: K,
    value: SourcesFiltersState[K]
  ): void {
    filters.value[key] = value
    currentPage.value = 1
  }

  function clearAllFilters(): void {
    filters.value = {
      category_id: null,
      source_type: null,
      status: null,
      search: '',
      tags: [],
    }
    currentPage.value = 1
  }

  function getCategoryName(categoryId: string): string {
    const cat = sidebarCounts.value.categories.find((c) => c.id === categoryId)
    return cat?.name || categoryId
  }

  // ==========================================================================
  // Form Actions
  // ==========================================================================

  function resetFormData(): void {
    // Use centralized factory function
    formData.value = createDefaultFormData()
    selectedEntities.value = []
    sharepointTestResult.value = null
  }

  function prepareCreateForm(): void {
    editMode.value = false
    selectedSource.value = null
    resetFormData()
  }

  async function prepareEditForm(source: DataSourceResponse): Promise<void> {
    editMode.value = true
    selectedSource.value = source
    sharepointTestResult.value = null
    selectedEntities.value = []

    // Extract category IDs from N:M categories array
    const categoryIds = source.categories?.map((c) => c.id) || []
    // Fallback to legacy category_id if no N:M categories
    if (categoryIds.length === 0 && source.category_id) {
      categoryIds.push(source.category_id)
    }

    // Load linked entities (N:M)
    const linkedEntityIds =
      source.extra_data?.entity_ids ||
      (source.extra_data?.entity_id ? [source.extra_data.entity_id] : [])

    if (linkedEntityIds.length > 0) {
      try {
        const entityPromises = linkedEntityIds.map((id: string) => entityApi.getEntity(id))
        const responses = await Promise.allSettled(entityPromises)
        selectedEntities.value = responses
          .filter((r): r is PromiseFulfilledResult<Awaited<ReturnType<typeof entityApi.getEntity>>> =>
            r.status === 'fulfilled'
          )
          .map((r) => r.value.data)
        const failed = responses.filter((r) => r.status === 'rejected')
        if (failed.length > 0) {
          logger.warn(`Failed to load ${failed.length} linked entities`)
        }
      } catch (e) {
        logger.error('Failed to load linked entities', e)
      }
    }

    formData.value = {
      ...source,
      category_id: source.category_id || '',
      category_ids: categoryIds,
      api_endpoint: source.api_endpoint || '',
      tags: source.tags || [],
      extra_data: { entity_ids: linkedEntityIds },
      crawl_config: { ...DEFAULT_CRAWL_CONFIG, ...(source.crawl_config || {}) },
    } as DataSourceFormData
  }

  async function saveForm(): Promise<DataSourceResponse> {
    if (editMode.value && selectedSource.value) {
      return updateSource(selectedSource.value.id, formData.value as DataSourceUpdate)
    } else {
      return createSource(formData.value as DataSourceCreate)
    }
  }

  // ==========================================================================
  // Entity Search Actions (N:M linking) - with VueUse debounce
  // ==========================================================================

  /**
   * Internal search function - called by debounced wrapper
   */
  async function _performEntitySearch(query: string): Promise<void> {
    searchingEntities.value = true

    try {
      const response = await entityApi.searchEntities({ q: query, per_page: ENTITY_SEARCH.MAX_RESULTS })
      // Filter out already selected entities
      const selectedIds = new Set(selectedEntities.value.map((e) => e.id))
      entitySearchResults.value = (response.data.items || []).filter(
        (e: EntityBrief) => !selectedIds.has(e.id)
      )
    } catch (e) {
      logger.error('Failed to search entities', e)
      entitySearchResults.value = []
    } finally {
      searchingEntities.value = false
    }
  }

  /**
   * Debounced entity search using VueUse
   * Waits for configured delay after last keystroke before executing
   */
  const debouncedEntitySearch = useDebounceFn(_performEntitySearch, ENTITY_SEARCH.DEBOUNCE_MS)

  /**
   * Search entities with debouncing to reduce API calls
   */
  function searchEntities(query: string): void {
    if (!query || query.length < ENTITY_SEARCH.MIN_QUERY_LENGTH) {
      entitySearchResults.value = []
      return
    }
    debouncedEntitySearch(query)
  }

  /**
   * Cancel pending entity search (for cleanup on unmount)
   * @deprecated VueUse handles cleanup automatically when component unmounts
   */
  function cleanupEntitySearch(): void {
    // VueUse's useDebounceFn handles cleanup automatically
    // This function is kept for backwards compatibility
  }

  function selectEntity(entity: EntityBrief): void {
    if (entity && !selectedEntities.value.find((e) => e.id === entity.id)) {
      selectedEntities.value.push(entity)
      formData.value.extra_data.entity_ids = selectedEntities.value.map((e) => e.id)
    }
    entitySearchResults.value = []
  }

  function removeEntity(entityId: string): void {
    selectedEntities.value = selectedEntities.value.filter((e) => e.id !== entityId)
    formData.value.extra_data.entity_ids = selectedEntities.value.map((e) => e.id)
  }

  function clearAllEntities(): void {
    selectedEntities.value = []
    formData.value.extra_data.entity_ids = []
    entitySearchResults.value = []
  }

  // ==========================================================================
  // SharePoint Actions
  // ==========================================================================

  async function testSharePointConnection(): Promise<SharePointTestResult> {
    if (!formData.value.crawl_config.site_url) {
      throw new Error('Site URL is required')
    }

    sharepointTestResult.value = null

    const siteUrl = formData.value.crawl_config.site_url!
    return await withLoadingState(async () => {
      try {
        const response = await adminApi.testSharePointConnection(siteUrl)
        const data = response.data

        const success =
          data.authentication &&
          (data.target_site_accessible || !formData.value.crawl_config.site_url)

        sharepointTestResult.value = {
          success,
          message: success ? 'Connection successful' : 'Connection failed',
          details: {
            authentication: data.authentication,
            sites_found: data.sites_found,
            target_site_accessible: data.target_site_accessible,
            target_site_name: data.target_site_name,
            drives: data.drives,
            errors: data.errors,
          },
        }

        // Auto-fill drive_name if only one drive and none selected
        if (success && data.drives?.length === 1 && !formData.value.crawl_config.drive_name) {
          formData.value.crawl_config.drive_name = data.drives[0].name
        }

        return sharepointTestResult.value
      } catch (err: unknown) {
        sharepointTestResult.value = {
          success: false,
          message: getApiErrorMessage(err, 'Connection error'),
        }
        throw err
      }
    }, sharepointTesting)
  }

  // ==========================================================================
  // Bulk Import Actions
  // ==========================================================================

  function resetBulkImport(): void {
    bulkImport.value = {
      category_ids: [],
      default_tags: [],
      inputMode: 'text',
      csvText: '',
      csvFile: null,
      preview: [],
      validCount: 0,
      duplicateCount: 0,
      errorCount: 0,
      importing: false,
      skip_duplicates: true,
    }
  }

  /** CSV validation error message */
  const csvValidationError = ref<string | null>(null)

  /**
   * Parse CSV text and update bulk import preview state
   * Delegates to centralized csvParser utility for consistent parsing
   */
  function parseBulkImportPreview(): void {
    const text = bulkImport.value.csvText
    csvValidationError.value = null

    if (!text.trim()) {
      bulkImport.value.preview = []
      bulkImport.value.validCount = 0
      bulkImport.value.duplicateCount = 0
      bulkImport.value.errorCount = 0
      return
    }

    // Use centralized CSV parser
    const existingUrls = sources.value
      .map((s) => s.base_url)
      .filter((url): url is string => !!url)

    const result = parseCsv(text, {
      defaultTags: bulkImport.value.default_tags,
      existingUrls,
      skipDuplicates: bulkImport.value.skip_duplicates,
    })

    // Handle validation errors from parser
    if (result.error) {
      csvValidationError.value = result.error
      bulkImport.value.preview = []
      bulkImport.value.validCount = 0
      bulkImport.value.duplicateCount = 0
      bulkImport.value.errorCount = 1
      return
    }

    // Update state with parse results
    bulkImport.value.preview = result.items
    bulkImport.value.validCount = result.validCount
    bulkImport.value.duplicateCount = result.duplicateCount
    bulkImport.value.errorCount = result.errorCount
  }

  async function onCsvFileSelected(files: File | File[] | null): Promise<void> {
    if (!files) return
    const file = Array.isArray(files) ? files[0] : files
    if (!file) return

    // Check file size limit
    if (file.size > BULK_IMPORT.MAX_FILE_SIZE) {
      csvValidationError.value = `File exceeds maximum size of ${BULK_IMPORT.MAX_FILE_SIZE / 1024 / 1024}MB`
      return
    }

    try {
      const text = await file.text()
      bulkImport.value.csvText = text
      bulkImport.value.csvFile = file
      parseBulkImportPreview()
    } catch (err) {
      logger.error('Failed to read CSV file', err)
      csvValidationError.value = 'Failed to read file'
    }
  }

  async function executeBulkImport(): Promise<DataSourceBulkImportResult> {
    if (!canExecuteBulkImport.value) {
      throw new Error('Cannot execute bulk import')
    }

    const importingRef = ref(false)
    // Sync with bulkImport.importing
    const updateImporting = (val: boolean) => {
      bulkImport.value.importing = val
      importingRef.value = val
    }

    updateImporting(true)
    try {
      const result = await withApiErrorHandling(
        async () => {
          // Filter valid items with type validation
          const validItems = bulkImport.value.preview.filter((item) => {
            if (item.error) return false
            if (item.duplicate && bulkImport.value.skip_duplicates) return false
            // Validate source_type with type guard
            if (!isSourceType(item.source_type)) return false
            return true
          })

          // Build sources array for API (type is now validated)
          const sourcesToImport = validItems
            .filter((item) => isSourceType(item.source_type))
            .map((item) => ({
              name: item.name,
              base_url: item.base_url,
              source_type: item.source_type as SourceType,
              tags: item.tags,
            }))

          const importData: DataSourceBulkImport = {
            category_ids: bulkImport.value.category_ids,
            default_tags: bulkImport.value.default_tags,
            sources: sourcesToImport,
            skip_duplicates: bulkImport.value.skip_duplicates,
          }

          const apiResult = await adminApi.bulkImportSources(importData)

          // Reload data
          await Promise.all([fetchSources(), fetchSidebarCounts(), fetchAvailableTags()])

          return apiResult.data
        },
        { errorRef: error, fallbackMessage: 'Bulk import failed' }
      )
      return result as DataSourceBulkImportResult
    } finally {
      updateImporting(false)
    }
  }

  // ==========================================================================
  // Utility Functions
  // ==========================================================================

  function clearError(): void {
    error.value = null
  }

  function resetState(): void {
    sources.value = []
    sourcesTotal.value = 0
    categories.value = []
    availableTags.value = []
    sidebarCounts.value = { total: 0, categories: [], types: [], statuses: [] }
    clearAllFilters()
    resetFormData()
    resetBulkImport()
    error.value = null
  }

  // Initialize data
  async function initialize(): Promise<void> {
    await Promise.all([fetchCategories(), fetchSidebarCounts(), fetchAvailableTags(), fetchSources()])
  }

  // ==========================================================================
  // Return
  // ==========================================================================

  return {
    // State
    sources,
    sourcesLoading,
    sourcesTotal,
    currentPage,
    itemsPerPage,
    categories,
    categoriesLoading,
    availableTags,
    tagsLoading,
    sidebarCounts,
    filters,
    formData,
    editMode,
    selectedSource,
    selectedCategoryInfo,
    saving,
    selectedEntities,
    entitySearchResults,
    searchingEntities,
    sharepointTesting,
    sharepointTestResult,
    bulkImport,
    csvValidationError,
    error,

    // Computed
    hasActiveFilters,
    tagSuggestions,
    canPreviewBulkImport,
    canExecuteBulkImport,

    // Data Source Actions
    fetchSources,
    createSource,
    updateSource,
    deleteSource,
    startCrawl,
    resetSource,

    // Category Actions
    fetchCategories,

    // Sidebar & Tags Actions
    fetchSidebarCounts,
    fetchAvailableTags,

    // Filter Actions
    setFilter,
    clearAllFilters,
    getCategoryName,

    // Form Actions
    resetFormData,
    prepareCreateForm,
    prepareEditForm,
    saveForm,

    // Entity Search Actions
    searchEntities,
    selectEntity,
    removeEntity,
    clearAllEntities,
    cleanupEntitySearch,

    // SharePoint Actions
    testSharePointConnection,

    // Bulk Import Actions
    resetBulkImport,
    parseBulkImportPreview,
    onCsvFileSelected,
    executeBulkImport,

    // Utility
    clearError,
    resetState,
    initialize,
  }
})
