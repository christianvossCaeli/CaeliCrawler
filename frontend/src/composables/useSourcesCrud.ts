import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { adminApi, entityApi } from '@/services/api'
import { useErrorHandler, type ApiError } from './useErrorHandler'
import { ENTITY_SEARCH } from '@/config/sources'
import type {
  DataSourceResponse,
  DataSourceFormData,
  DataSourceBulkImportItem,
  BulkImportState,
  LinkedEntity,
  SourceType,
} from '@/types/sources'

/**
 * Loading states for individual actions
 */
export interface ActionLoadingStates {
  saving: boolean
  deleting: boolean
  starting: Record<string, boolean>  // Per-source crawl start
  resetting: Record<string, boolean> // Per-source reset
  importing: boolean
}

/**
 * Options for useSourcesCrud composable
 */
export interface UseSourcesCrudOptions {
  onSuccess?: () => void
  onError?: (error: ApiError) => void
}

/**
 * Composable for DataSource CRUD operations
 *
 * Provides:
 * - Create, update, delete operations
 * - Start crawl and reset functionality
 * - Bulk import handling
 * - Individual loading states per action
 * - Entity search for N:M linking
 */
export function useSourcesCrud(options: UseSourcesCrudOptions = {}) {
  const { t } = useI18n()
  const { handleError, showSuccess } = useErrorHandler()

  // ==========================================================================
  // State
  // ==========================================================================

  // Dialog state
  const dialog = ref(false)
  const deleteDialog = ref(false)
  const bulkDialog = ref(false)
  const editMode = ref(false)

  // Selected items
  const selectedSource = ref<DataSourceResponse | null>(null)

  // Loading states
  const loading = ref<ActionLoadingStates>({
    saving: false,
    deleting: false,
    starting: {},
    resetting: {},
    importing: false,
  })

  // Entity search for N:M linking
  const entitySearchQuery = ref('')
  const entitySearchResults = ref<LinkedEntity[]>([])
  const searchingEntities = ref(false)
  const selectedEntities = ref<LinkedEntity[]>([])
  let entitySearchTimeout: ReturnType<typeof setTimeout> | null = null

  // ==========================================================================
  // Computed
  // ==========================================================================

  const isSaving = computed(() => loading.value.saving)
  const isDeleting = computed(() => loading.value.deleting)
  const isImporting = computed(() => loading.value.importing)

  /**
   * Check if a specific source is currently starting a crawl
   */
  const isStartingCrawl = (sourceId: string): boolean => {
    return loading.value.starting[sourceId] ?? false
  }

  /**
   * Check if a specific source is currently resetting
   */
  const isResetting = (sourceId: string): boolean => {
    return loading.value.resetting[sourceId] ?? false
  }

  // ==========================================================================
  // CRUD Operations
  // ==========================================================================

  /**
   * Save a data source (create or update)
   */
  async function saveSource(
    formData: DataSourceFormData,
    sourceId?: string
  ): Promise<DataSourceResponse | null> {
    loading.value.saving = true

    try {
      let result: DataSourceResponse

      if (sourceId) {
        const response = await adminApi.updateSource(sourceId, formData)
        result = response.data
        showSuccess(t('sources.messages.updated'))
      } else {
        const response = await adminApi.createSource(formData)
        result = response.data
        showSuccess(t('sources.messages.created'))
      }

      dialog.value = false
      options.onSuccess?.()
      return result
    } catch (error) {
      const apiError = error as ApiError
      handleError(error, {
        defaultMessage: t('sources.errors.saveFailed'),
      })
      options.onError?.(apiError)
      return null
    } finally {
      loading.value.saving = false
    }
  }

  /**
   * Delete a data source
   */
  async function deleteSource(sourceId: string): Promise<boolean> {
    loading.value.deleting = true

    try {
      await adminApi.deleteSource(sourceId)
      showSuccess(t('sources.messages.deleted'))
      deleteDialog.value = false
      options.onSuccess?.()
      return true
    } catch (error) {
      const apiError = error as ApiError
      handleError(error, {
        defaultMessage: t('sources.errors.deleteFailed'),
      })
      options.onError?.(apiError)
      return false
    } finally {
      loading.value.deleting = false
    }
  }

  /**
   * Start a crawl for a data source
   */
  async function startCrawl(source: DataSourceResponse): Promise<boolean> {
    loading.value.starting[source.id] = true

    try {
      await adminApi.startCrawl({ source_ids: [source.id] })
      showSuccess(t('sources.messages.crawlStarted', { name: source.name }))
      return true
    } catch (error) {
      const apiError = error as ApiError
      handleError(error, {
        defaultMessage: t('sources.messages.crawlError'),
      })
      options.onError?.(apiError)
      return false
    } finally {
      loading.value.starting[source.id] = false
    }
  }

  /**
   * Reset a data source (clear error state)
   */
  async function resetSource(source: DataSourceResponse): Promise<boolean> {
    loading.value.resetting[source.id] = true

    try {
      await adminApi.resetSource(source.id)
      showSuccess(t('sources.messages.reset', { name: source.name }))
      options.onSuccess?.()
      return true
    } catch (error) {
      const apiError = error as ApiError
      handleError(error, {
        defaultMessage: t('sources.messages.resetError'),
      })
      options.onError?.(apiError)
      return false
    } finally {
      loading.value.resetting[source.id] = false
    }
  }

  /**
   * Bulk import data sources
   */
  async function bulkImport(data: BulkImportState): Promise<{ imported: number; skipped: number } | null> {
    loading.value.importing = true

    try {
      // Filter valid items
      const validItems = data.preview.filter((item) => {
        if (item.error) return false
        if (item.duplicate && data.skip_duplicates) return false
        return true
      })

      // Build sources array for API with proper type assertion
      const sourcesToImport: DataSourceBulkImportItem[] = validItems.map((item) => ({
        name: item.name,
        base_url: item.base_url,
        source_type: item.source_type as SourceType,
        tags: item.tags,
      }))

      const response = await adminApi.bulkImportSources({
        category_ids: data.category_ids,
        default_tags: data.default_tags,
        sources: sourcesToImport,
        skip_duplicates: data.skip_duplicates,
      })

      const result = {
        imported: response.data.imported,
        skipped: response.data.skipped,
      }

      showSuccess(
        t('sources.messages.bulkImportSuccess', {
          imported: result.imported,
          skipped: result.skipped,
        })
      )

      bulkDialog.value = false
      options.onSuccess?.()
      return result
    } catch (error) {
      const apiError = error as ApiError
      handleError(error, {
        defaultMessage: t('sources.messages.bulkImportError'),
      })
      options.onError?.(apiError)
      return null
    } finally {
      loading.value.importing = false
    }
  }

  // ==========================================================================
  // Dialog Management
  // ==========================================================================

  /**
   * Open create dialog
   */
  function openCreateDialog() {
    editMode.value = false
    selectedSource.value = null
    clearEntitySearch()
    dialog.value = true
  }

  /**
   * Open edit dialog
   */
  function openEditDialog(source: DataSourceResponse) {
    editMode.value = true
    selectedSource.value = source
    clearEntitySearch()
    dialog.value = true
  }

  /**
   * Open delete confirmation dialog
   */
  function openDeleteDialog(source: DataSourceResponse) {
    selectedSource.value = source
    deleteDialog.value = true
  }

  /**
   * Open bulk import dialog
   */
  function openBulkImportDialog() {
    bulkDialog.value = true
  }

  // ==========================================================================
  // Entity Search (N:M Linking)
  // ==========================================================================

  /**
   * Search for entities to link (using centralized config)
   */
  async function searchEntities(query: string) {
    if (!query || query.length < ENTITY_SEARCH.MIN_QUERY_LENGTH) {
      entitySearchResults.value = []
      return
    }

    if (entitySearchTimeout) clearTimeout(entitySearchTimeout)

    entitySearchTimeout = setTimeout(async () => {
      searchingEntities.value = true
      try {
        const response = await entityApi.searchEntities({
          q: query,
          per_page: ENTITY_SEARCH.MAX_RESULTS,
        })
        // Filter out already selected entities
        const selectedIds = new Set(selectedEntities.value.map((e) => e.id))
        entitySearchResults.value = (response.data.items || [])
          .filter((e: LinkedEntity) => !selectedIds.has(e.id))
          .map((e: LinkedEntity) => ({
            id: e.id,
            name: e.name,
            entity_type_name: e.entity_type_name,
            entity_type_color: e.entity_type_color,
            entity_type_icon: e.entity_type_icon,
          }))
      } catch (error) {
        console.error('Failed to search entities:', error)
        entitySearchResults.value = []
      } finally {
        searchingEntities.value = false
      }
    }, ENTITY_SEARCH.DEBOUNCE_MS)
  }

  /**
   * Select an entity to link
   */
  function selectEntity(entity: LinkedEntity) {
    if (!selectedEntities.value.find((e) => e.id === entity.id)) {
      selectedEntities.value.push(entity)
    }
    entitySearchQuery.value = ''
    entitySearchResults.value = []
  }

  /**
   * Remove an entity from selection
   */
  function removeEntity(entityId: string) {
    selectedEntities.value = selectedEntities.value.filter((e) => e.id !== entityId)
  }

  /**
   * Clear all entity selections
   */
  function clearEntitySearch() {
    selectedEntities.value = []
    entitySearchQuery.value = ''
    entitySearchResults.value = []
  }

  /**
   * Load linked entities for a source
   */
  async function loadLinkedEntities(entityIds: string[]) {
    if (entityIds.length === 0) {
      selectedEntities.value = []
      return
    }

    try {
      const entityPromises = entityIds.map((id) => entityApi.getEntity(id))
      const responses = await Promise.all(entityPromises)
      selectedEntities.value = responses.map((r) => ({
        id: r.data.id,
        name: r.data.name,
        entity_type_name: r.data.entity_type_name,
        entity_type_color: r.data.entity_type_color,
        entity_type_icon: r.data.entity_type_icon,
      }))
    } catch (error) {
      console.error('Failed to load linked entities:', error)
      selectedEntities.value = []
    }
  }

  /**
   * Get entity IDs from selection
   */
  const selectedEntityIds = computed(() => selectedEntities.value.map((e) => e.id))

  // ==========================================================================
  // Cleanup
  // ==========================================================================

  /**
   * Cleanup function for onUnmounted
   */
  function cleanup() {
    if (entitySearchTimeout) {
      clearTimeout(entitySearchTimeout)
      entitySearchTimeout = null
    }
  }

  return {
    // State
    dialog,
    deleteDialog,
    bulkDialog,
    editMode,
    selectedSource,
    loading,

    // Computed loading states
    isSaving,
    isDeleting,
    isImporting,
    isStartingCrawl,
    isResetting,

    // CRUD operations
    saveSource,
    deleteSource,
    startCrawl,
    resetSource,
    bulkImport,

    // Dialog management
    openCreateDialog,
    openEditDialog,
    openDeleteDialog,
    openBulkImportDialog,

    // Entity search
    entitySearchQuery,
    entitySearchResults,
    searchingEntities,
    selectedEntities,
    selectedEntityIds,
    searchEntities,
    selectEntity,
    removeEntity,
    clearEntitySearch,
    loadLinkedEntities,

    // Cleanup
    cleanup,
  }
}
