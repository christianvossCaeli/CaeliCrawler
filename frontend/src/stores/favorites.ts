/**
 * Favorites Store
 *
 * Manages user's favorite entities state.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { favoritesApi } from '@/services/api'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger('FavoritesStore')

export interface FavoriteEntity {
  id: string
  name: string
  slug: string
  entity_type_id: string
  entity_type_slug: string | null
  entity_type_name: string | null
  entity_type_icon: string | null
  entity_type_color: string | null
  hierarchy_path: string | null
  is_active: boolean
}

export interface Favorite {
  id: string
  user_id: string
  entity_id: string
  created_at: string
  entity: FavoriteEntity
}

export const useFavoritesStore = defineStore('favorites', () => {
  // State
  const favorites = ref<Favorite[]>([])
  const favoriteIds = ref<Set<string>>(new Set())
  const isLoading = ref(false)
  const total = ref(0)
  const page = ref(1)
  const perPage = ref(20)
  const error = ref<string | null>(null)

  // Computed
  const favoriteCount = computed(() => favoriteIds.value.size)

  /**
   * Check if entity is favorited (instant lookup)
   */
  function isFavorited(entityId: string): boolean {
    return favoriteIds.value.has(entityId)
  }

  /**
   * Get favorite by entity ID
   */
  function getFavoriteByEntityId(entityId: string): Favorite | undefined {
    return favorites.value.find((f) => f.entity_id === entityId)
  }

  /**
   * Load favorites list from API
   */
  async function loadFavorites(options?: {
    page?: number
    per_page?: number
    entity_type_slug?: string
    search?: string
    sort_by?: string
    sort_order?: 'asc' | 'desc'
  }): Promise<void> {
    isLoading.value = true
    error.value = null

    // Update perPage if provided
    if (options?.per_page) {
      perPage.value = options.per_page
    }

    try {
      const response = await favoritesApi.list({
        page: options?.page || page.value,
        per_page: perPage.value,
        entity_type_slug: options?.entity_type_slug,
        search: options?.search,
        sort_by: options?.sort_by,
        sort_order: options?.sort_order,
      })

      favorites.value = response.data.items
      total.value = response.data.total
      page.value = response.data.page

      // Update favoriteIds set for quick lookup
      favoriteIds.value = new Set(favorites.value.map((f) => f.entity_id))
    } catch (e) {
      logger.error('Failed to load favorites:', e)
      error.value = 'Failed to load favorites'
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Add entity to favorites
   */
  async function addFavorite(entityId: string): Promise<Favorite | null> {
    try {
      const response = await favoritesApi.add(entityId)
      const favorite = response.data

      // Add to local state
      favorites.value.unshift(favorite)
      favoriteIds.value.add(entityId)
      total.value++

      return favorite
    } catch (e) {
      logger.error('Failed to add favorite:', e)
      error.value = 'Failed to add favorite'
      return null
    }
  }

  /**
   * Remove favorite by entity ID
   */
  async function removeFavorite(entityId: string): Promise<boolean> {
    try {
      await favoritesApi.removeByEntity(entityId)

      // Remove from local state
      const index = favorites.value.findIndex((f) => f.entity_id === entityId)
      if (index > -1) {
        favorites.value.splice(index, 1)
      }
      favoriteIds.value.delete(entityId)
      total.value = Math.max(0, total.value - 1)

      return true
    } catch (e) {
      logger.error('Failed to remove favorite:', e)
      error.value = 'Failed to remove favorite'
      return false
    }
  }

  /**
   * Toggle favorite status for entity
   */
  async function toggleFavorite(entityId: string): Promise<boolean> {
    if (isFavorited(entityId)) {
      const success = await removeFavorite(entityId)
      return !success // Returns false if now NOT favorited
    } else {
      const favorite = await addFavorite(entityId)
      return favorite !== null // Returns true if now favorited
    }
  }

  /**
   * Check favorite status from API (for initial load on entity detail)
   */
  async function checkFavorite(entityId: string): Promise<boolean> {
    try {
      const response = await favoritesApi.check(entityId)
      if (response.data.is_favorited) {
        favoriteIds.value.add(entityId)
      } else {
        favoriteIds.value.delete(entityId)
      }
      return response.data.is_favorited
    } catch (e) {
      logger.error('Failed to check favorite status:', e)
      return false
    }
  }

  /**
   * Clear all favorites from local state (on logout)
   */
  function clearFavorites(): void {
    favorites.value = []
    favoriteIds.value.clear()
    total.value = 0
    page.value = 1
  }

  return {
    // State
    favorites,
    favoriteIds,
    isLoading,
    total,
    page,
    perPage,
    error,

    // Computed
    favoriteCount,

    // Actions
    isFavorited,
    getFavoriteByEntityId,
    loadFavorites,
    addFavorite,
    removeFavorite,
    toggleFavorite,
    checkFavorite,
    clearFavorites,
  }
})
