/**
 * Smart Query History Store
 *
 * Manages user's Smart Query operation history and favorites.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { smartQueryHistoryApi } from '@/services/api'
import { useLogger } from '@/composables/useLogger'
import { addToSet, removeFromSet, clearSet } from '@/utils/immutableSet'

const logger = useLogger('SmartQueryHistoryStore')

export interface SmartQueryOperation {
  id: string
  user_id: string
  command_text: string
  command_hash: string
  operation_type: string
  interpretation: Record<string, unknown>
  result_summary: Record<string, unknown>
  display_name: string | null
  is_favorite: boolean
  execution_count: number
  was_successful: boolean
  created_at: string
  last_executed_at: string
}

export const useSmartQueryHistoryStore = defineStore('smartQueryHistory', () => {
  // State
  const history = ref<SmartQueryOperation[]>([])
  const favoriteIds = ref<Set<string>>(new Set())
  const isLoading = ref(false)
  const total = ref(0)
  const page = ref(1)
  const perPage = ref(20)
  const error = ref<string | null>(null)

  // Computed
  const favoriteCount = computed(() => favoriteIds.value.size)
  const favorites = computed(() => history.value.filter((op) => op.is_favorite))

  /**
   * Check if operation is favorited (instant lookup)
   */
  function isFavorited(operationId: string): boolean {
    return favoriteIds.value.has(operationId)
  }

  /**
   * Get operation by ID
   */
  function getOperationById(operationId: string): SmartQueryOperation | undefined {
    return history.value.find((op) => op.id === operationId)
  }

  /**
   * Load history from API
   */
  async function loadHistory(options?: {
    page?: number
    per_page?: number
    favorites_only?: boolean
    operation_type?: string
    search?: string
  }): Promise<void> {
    isLoading.value = true
    error.value = null

    if (options?.per_page) {
      perPage.value = options.per_page
    }

    try {
      const response = await smartQueryHistoryApi.getHistory({
        page: options?.page || page.value,
        per_page: perPage.value,
        favorites_only: options?.favorites_only,
        operation_type: options?.operation_type,
        search: options?.search,
      })

      history.value = response.data.items
      total.value = response.data.total
      page.value = response.data.page

      // Update favoriteIds set for quick lookup
      favoriteIds.value = new Set(history.value.filter((op) => op.is_favorite).map((op) => op.id))
    } catch (e) {
      logger.error('Failed to load Smart Query history:', e)
      error.value = 'Failed to load history'
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Toggle favorite status for an operation
   */
  async function toggleFavorite(operationId: string): Promise<boolean> {
    try {
      const response = await smartQueryHistoryApi.toggleFavorite(operationId)
      const newState = response.data.is_favorite

      // Update local state
      const operation = history.value.find((op) => op.id === operationId)
      if (operation) {
        operation.is_favorite = newState
      }

      if (newState) {
        favoriteIds.value = addToSet(favoriteIds.value, operationId)
      } else {
        favoriteIds.value = removeFromSet(favoriteIds.value, operationId)
      }

      return newState
    } catch (e) {
      logger.error('Failed to toggle favorite:', e)
      error.value = 'Failed to toggle favorite'
      return false
    }
  }

  /**
   * Execute an operation from history
   */
  async function executeFromHistory(operationId: string): Promise<{ success: boolean; data?: unknown }> {
    try {
      const response = await smartQueryHistoryApi.execute(operationId)

      // Update local state
      const operation = history.value.find((op) => op.id === operationId)
      if (operation) {
        operation.execution_count += 1
        operation.last_executed_at = new Date().toISOString()
        operation.was_successful = response.data.success
      }

      return response.data
    } catch (e) {
      logger.error('Failed to execute from history:', e)
      error.value = 'Failed to execute operation'
      throw e
    }
  }

  /**
   * Delete an operation from history
   */
  async function deleteFromHistory(operationId: string): Promise<boolean> {
    try {
      await smartQueryHistoryApi.delete(operationId)

      // Remove from local state
      const index = history.value.findIndex((op) => op.id === operationId)
      if (index > -1) {
        history.value.splice(index, 1)
      }
      favoriteIds.value = removeFromSet(favoriteIds.value, operationId)
      total.value = Math.max(0, total.value - 1)

      return true
    } catch (e) {
      logger.error('Failed to delete from history:', e)
      error.value = 'Failed to delete operation'
      return false
    }
  }

  /**
   * Clear all history (preserves favorites by default)
   */
  async function clearHistory(includeFavorites: boolean = false): Promise<boolean> {
    try {
      await smartQueryHistoryApi.clearHistory(includeFavorites)

      // Update local state
      if (includeFavorites) {
        history.value = []
        favoriteIds.value = clearSet()
        total.value = 0
      } else {
        history.value = history.value.filter((op) => op.is_favorite)
        total.value = history.value.length
      }

      return true
    } catch (e) {
      logger.error('Failed to clear history:', e)
      error.value = 'Failed to clear history'
      return false
    }
  }

  /**
   * Add operation to history (for local updates after execution)
   */
  function addToHistory(operation: SmartQueryOperation): void {
    // Check if already exists (deduplication)
    const existing = history.value.find((op) => op.command_hash === operation.command_hash)
    if (existing) {
      existing.execution_count = operation.execution_count
      existing.last_executed_at = operation.last_executed_at
      existing.was_successful = operation.was_successful
      existing.result_summary = operation.result_summary
    } else {
      history.value.unshift(operation)
      total.value++
    }
  }

  /**
   * Clear store on logout
   */
  function clearStore(): void {
    history.value = []
    favoriteIds.value = clearSet()
    total.value = 0
    page.value = 1
    error.value = null
  }

  return {
    // State
    history,
    favoriteIds,
    isLoading,
    total,
    page,
    perPage,
    error,

    // Computed
    favoriteCount,
    favorites,

    // Actions
    isFavorited,
    getOperationById,
    loadHistory,
    toggleFavorite,
    executeFromHistory,
    deleteFromHistory,
    clearHistory,
    addToHistory,
    clearStore,
  }
})
