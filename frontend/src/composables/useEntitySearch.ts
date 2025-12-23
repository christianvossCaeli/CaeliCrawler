/**
 * Entity Search Composable
 *
 * Centralized entity search with debouncing for N:M entity linking.
 * Replaces duplicate implementations in stores/sources.ts and useSourcesCrud.ts.
 *
 * @module composables/useEntitySearch
 *
 * ## Features
 * - Debounced search using VueUse (auto-cleanup on unmount)
 * - Configurable min query length and max results
 * - Entity selection management (add/remove/clear)
 * - Filters out already selected entities from results
 *
 * ## Usage
 * ```typescript
 * const {
 *   searchQuery,
 *   searchResults,
 *   selectedEntities,
 *   isSearching,
 *   search,
 *   select,
 *   remove,
 *   clear,
 *   loadEntities
 * } = useEntitySearch()
 * ```
 */

import { ref, computed } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import { entityApi } from '@/services/api'
import { ENTITY_SEARCH } from '@/config/sources'
import { useLogger } from './useLogger'

/**
 * Brief entity representation for search results and selection
 */
export interface EntityBrief {
  id: string
  name: string
  entity_type_name?: string
  entity_type_color?: string
  entity_type_icon?: string
  hierarchy_path?: string
}

/**
 * Options for useEntitySearch composable
 */
export interface UseEntitySearchOptions {
  /** Minimum query length to trigger search (default: from config) */
  minQueryLength?: number
  /** Maximum results to return (default: from config) */
  maxResults?: number
  /** Debounce delay in ms (default: from config) */
  debounceMs?: number
  /** Initial selected entities */
  initialEntities?: EntityBrief[]
}

/**
 * Composable for entity search with debouncing
 */
export function useEntitySearch(options: UseEntitySearchOptions = {}) {
  const {
    minQueryLength = ENTITY_SEARCH.MIN_QUERY_LENGTH,
    maxResults = ENTITY_SEARCH.MAX_RESULTS,
    debounceMs = ENTITY_SEARCH.DEBOUNCE_MS,
    initialEntities = [],
  } = options

  const logger = useLogger('EntitySearch')

  // ==========================================================================
  // State
  // ==========================================================================

  const searchQuery = ref('')
  const searchResults = ref<EntityBrief[]>([])
  const selectedEntities = ref<EntityBrief[]>(initialEntities)
  const isSearching = ref(false)

  // ==========================================================================
  // Computed
  // ==========================================================================

  /** Get IDs of selected entities */
  const selectedEntityIds = computed(() => selectedEntities.value.map((e) => e.id))

  /** Check if any entities are selected */
  const hasSelection = computed(() => selectedEntities.value.length > 0)

  // ==========================================================================
  // Internal Functions
  // ==========================================================================

  /**
   * Internal search function - called by debounced wrapper
   */
  async function performSearch(query: string): Promise<void> {
    isSearching.value = true

    try {
      const response = await entityApi.searchEntities({
        q: query,
        per_page: maxResults,
      })

      // Filter out already selected entities
      const selectedIds = new Set(selectedEntities.value.map((e) => e.id))
      searchResults.value = (response.data.items || [])
        .filter((e: EntityBrief) => !selectedIds.has(e.id))
        .map((e: EntityBrief) => ({
          id: e.id,
          name: e.name,
          entity_type_name: e.entity_type_name,
          entity_type_color: e.entity_type_color,
          entity_type_icon: e.entity_type_icon,
          hierarchy_path: e.hierarchy_path,
        }))
    } catch (error) {
      logger.error('Search failed', error)
      searchResults.value = []
    } finally {
      isSearching.value = false
    }
  }

  /**
   * Debounced search using VueUse (auto-cleanup on unmount)
   */
  const debouncedSearch = useDebounceFn(performSearch, debounceMs)

  // ==========================================================================
  // Public Functions
  // ==========================================================================

  /**
   * Search for entities with the given query
   * Automatically debounced to reduce API calls
   */
  function search(query: string): void {
    searchQuery.value = query

    if (!query || query.length < minQueryLength) {
      searchResults.value = []
      return
    }

    debouncedSearch(query)
  }

  /**
   * Select an entity (add to selection)
   */
  function select(entity: EntityBrief): void {
    if (!entity) return

    // Don't add duplicates
    if (selectedEntities.value.find((e) => e.id === entity.id)) {
      return
    }

    selectedEntities.value = [...selectedEntities.value, entity]

    // Clear search after selection
    searchQuery.value = ''
    searchResults.value = []
  }

  /**
   * Remove an entity from selection
   */
  function remove(entityId: string): void {
    selectedEntities.value = selectedEntities.value.filter((e) => e.id !== entityId)
  }

  /**
   * Clear all selected entities
   */
  function clear(): void {
    selectedEntities.value = []
    searchQuery.value = ''
    searchResults.value = []
  }

  /**
   * Set selected entities directly (for edit mode)
   */
  function setSelection(entities: EntityBrief[]): void {
    selectedEntities.value = entities
  }

  /**
   * Load entities by their IDs (for edit mode)
   */
  async function loadEntities(entityIds: string[]): Promise<void> {
    if (!entityIds || entityIds.length === 0) {
      selectedEntities.value = []
      return
    }

    try {
      const responses = await Promise.allSettled(
        entityIds.map((id) => entityApi.getEntity(id))
      )

      selectedEntities.value = responses
        .filter((r): r is PromiseFulfilledResult<Awaited<ReturnType<typeof entityApi.getEntity>>> =>
          r.status === 'fulfilled'
        )
        .map((r) => ({
          id: r.value.data.id,
          name: r.value.data.name,
          entity_type_name: r.value.data.entity_type_name,
          entity_type_color: r.value.data.entity_type_color,
          entity_type_icon: r.value.data.entity_type_icon,
        }))

      // Log any failed loads
      const failed = responses.filter((r) => r.status === 'rejected')
      if (failed.length > 0) {
        logger.warn(`Failed to load ${failed.length} entities`)
      }
    } catch (error) {
      logger.error('Failed to load linked entities', error)
      selectedEntities.value = []
    }
  }

  // ==========================================================================
  // Return
  // ==========================================================================

  return {
    // State
    searchQuery,
    searchResults,
    selectedEntities,
    isSearching,

    // Computed
    selectedEntityIds,
    hasSelection,

    // Functions
    search,
    select,
    remove,
    clear,
    setSelection,
    loadEntities,
  }
}
