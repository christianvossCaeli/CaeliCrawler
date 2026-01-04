/**
 * Facet Value Store
 *
 * Manages facet values for the Entity-Facet system.
 * For facet type definitions, use useFacetTypesStore from './facetTypes'
 *
 * Features:
 * - Caching for entity facets summary (TTL-based)
 * - Batch operations (bulkVerify, bulkDelete)
 * - Optimistic updates with rollback on error
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { facetApi } from '@/services/api'
import type {
  FacetValueCreate,
  FacetValueUpdate,
} from '@/types/entity'
import type { FacetValue, EntityFacetsSummary } from './types/entity'
import { getErrorMessage } from './types/entity'

// ============================================================================
// Cache Configuration
// ============================================================================

const CACHE_TTL_MS = 30_000 // 30 seconds

interface CacheEntry<T> {
  data: T
  timestamp: number
}

// ============================================================================
// Store Definition
// ============================================================================

export const useFacetStore = defineStore('facet', () => {
  // ========================================
  // State
  // ========================================

  // Facet Values
  const facetValues = ref<FacetValue[]>([])
  const facetValuesLoading = ref(false)
  const facetValuesTotal = ref(0)

  // Error handling
  const error = ref<string | null>(null)

  // Cache for entity facets summary
  const summaryCache = ref<Map<string, CacheEntry<EntityFacetsSummary>>>(new Map())

  // ========================================
  // Computed Properties
  // ========================================

  const hasFacetValues = computed(() => facetValues.value.length > 0)
  const hasError = computed(() => error.value !== null)
  const isEmpty = computed(() => !facetValuesLoading.value && facetValues.value.length === 0)

  // ========================================
  // Facet Value Actions
  // ========================================

  async function fetchFacetValues(params?: Record<string, unknown>) {
    facetValuesLoading.value = true
    error.value = null
    try {
      const response = await facetApi.getFacetValues(params)
      facetValues.value = response.data.items
      facetValuesTotal.value = response.data.total
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to fetch facet values'
      throw err
    } finally {
      facetValuesLoading.value = false
    }
  }

  async function fetchFacetValue(id: string) {
    try {
      const response = await facetApi.getFacetValue(id)
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to fetch facet value'
      throw err
    }
  }

  async function createFacetValue(data: FacetValueCreate) {
    try {
      const response = await facetApi.createFacetValue(data)
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to create facet value'
      throw err
    }
  }

  async function updateFacetValue(id: string, data: FacetValueUpdate) {
    try {
      const response = await facetApi.updateFacetValue(id, data)
      const index = facetValues.value.findIndex(fv => fv.id === id)
      if (index >= 0) {
        facetValues.value[index] = response.data
      }
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to update facet value'
      throw err
    }
  }

  async function verifyFacetValue(id: string, verified: boolean, verifiedBy?: string) {
    try {
      const response = await facetApi.verifyFacetValue(id, { verified, verified_by: verifiedBy })
      const index = facetValues.value.findIndex(fv => fv.id === id)
      if (index >= 0) {
        facetValues.value[index] = response.data
      }
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to verify facet value'
      throw err
    }
  }

  async function deleteFacetValue(id: string) {
    try {
      await facetApi.deleteFacetValue(id)
      facetValues.value = facetValues.value.filter(fv => fv.id !== id)
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to delete facet value'
      throw err
    }
  }

  async function fetchEntityFacetsSummary(
    entityId: string,
    params?: Record<string, unknown>,
    options?: { skipCache?: boolean }
  ): Promise<EntityFacetsSummary> {
    const cacheKey = `${entityId}:${JSON.stringify(params || {})}`

    // Check cache first (unless skipCache is true)
    if (!options?.skipCache) {
      const cached = summaryCache.value.get(cacheKey)
      if (cached && Date.now() - cached.timestamp < CACHE_TTL_MS) {
        return cached.data
      }
    }

    try {
      const response = await facetApi.getEntityFacetsSummary(entityId, params)

      // Store in cache
      summaryCache.value.set(cacheKey, {
        data: response.data,
        timestamp: Date.now(),
      })

      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to fetch entity facets summary'
      throw err
    }
  }

  /**
   * Invalidate cache for a specific entity
   */
  function invalidateSummaryCache(entityId?: string) {
    if (entityId) {
      // Remove all cache entries for this entity
      for (const key of summaryCache.value.keys()) {
        if (key.startsWith(`${entityId}:`)) {
          summaryCache.value.delete(key)
        }
      }
    } else {
      // Clear entire cache
      summaryCache.value.clear()
    }
  }

  async function searchFacetValues(params: {
    q: string
    entity_id?: string
    facet_type_slug?: string
    limit?: number
  }) {
    try {
      const response = await facetApi.searchFacetValues(params)
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to search facet values'
      throw err
    }
  }

  // ========================================
  // Batch Operations
  // ========================================

  /**
   * Verify multiple facet values at once
   */
  async function bulkVerifyFacetValues(
    ids: string[],
    verified: boolean,
    verifiedBy?: string
  ): Promise<{ success: string[]; failed: string[] }> {
    const results = { success: [] as string[], failed: [] as string[] }

    // Process in parallel with Promise.allSettled
    const promises = ids.map(async (id) => {
      try {
        await verifyFacetValue(id, verified, verifiedBy)
        return { id, success: true }
      } catch {
        return { id, success: false }
      }
    })

    const settled = await Promise.allSettled(promises)
    settled.forEach((result) => {
      if (result.status === 'fulfilled') {
        if (result.value.success) {
          results.success.push(result.value.id)
        } else {
          results.failed.push(result.value.id)
        }
      }
    })

    return results
  }

  /**
   * Delete multiple facet values at once
   */
  async function bulkDeleteFacetValues(
    ids: string[]
  ): Promise<{ success: string[]; failed: string[] }> {
    const results = { success: [] as string[], failed: [] as string[] }

    // Process in parallel with Promise.allSettled
    const promises = ids.map(async (id) => {
      try {
        await deleteFacetValue(id)
        return { id, success: true }
      } catch {
        return { id, success: false }
      }
    })

    const settled = await Promise.allSettled(promises)
    settled.forEach((result) => {
      if (result.status === 'fulfilled') {
        if (result.value.success) {
          results.success.push(result.value.id)
        } else {
          results.failed.push(result.value.id)
        }
      }
    })

    return results
  }

  // ========================================
  // Optimistic Update Operations
  // ========================================

  /**
   * Update facet value with optimistic update and rollback on error
   */
  async function updateFacetValueOptimistic(id: string, data: FacetValueUpdate) {
    const index = facetValues.value.findIndex(fv => fv.id === id)
    const previousValue = index >= 0 ? { ...facetValues.value[index] } : null

    // Optimistic update
    if (index >= 0) {
      facetValues.value[index] = { ...facetValues.value[index], ...data } as FacetValue
    }

    try {
      const response = await facetApi.updateFacetValue(id, data)
      // Update with actual server response
      if (index >= 0) {
        facetValues.value[index] = response.data
      }
      return response.data
    } catch (err: unknown) {
      // Rollback on error
      if (index >= 0 && previousValue) {
        facetValues.value[index] = previousValue as FacetValue
      }
      error.value = getErrorMessage(err) || 'Failed to update facet value'
      throw err
    }
  }

  /**
   * Delete facet value with optimistic update and rollback on error
   */
  async function deleteFacetValueOptimistic(id: string) {
    const index = facetValues.value.findIndex(fv => fv.id === id)
    const previousValues = [...facetValues.value]

    // Optimistic delete
    if (index >= 0) {
      facetValues.value.splice(index, 1)
    }

    try {
      await facetApi.deleteFacetValue(id)
    } catch (err: unknown) {
      // Rollback on error
      facetValues.value = previousValues
      error.value = getErrorMessage(err) || 'Failed to delete facet value'
      throw err
    }
  }

  /**
   * Verify facet value with optimistic update and rollback on error
   */
  async function verifyFacetValueOptimistic(id: string, verified: boolean, verifiedBy?: string) {
    const index = facetValues.value.findIndex(fv => fv.id === id)
    const previousValue = index >= 0 ? { ...facetValues.value[index] } : null

    // Optimistic update
    if (index >= 0) {
      facetValues.value[index] = {
        ...facetValues.value[index],
        human_verified: verified,
        verified_by: verifiedBy,
      } as FacetValue
    }

    try {
      const response = await facetApi.verifyFacetValue(id, { verified, verified_by: verifiedBy })
      // Update with actual server response
      if (index >= 0) {
        facetValues.value[index] = response.data
      }
      return response.data
    } catch (err: unknown) {
      // Rollback on error
      if (index >= 0 && previousValue) {
        facetValues.value[index] = previousValue as FacetValue
      }
      error.value = getErrorMessage(err) || 'Failed to verify facet value'
      throw err
    }
  }

  // ========================================
  // Utility Functions
  // ========================================

  function clearError() {
    error.value = null
  }

  function resetState() {
    facetValues.value = []
    facetValuesTotal.value = 0
    error.value = null
  }

  // ========================================
  // Return
  // ========================================

  return {
    // State
    facetValues,
    facetValuesLoading,
    facetValuesTotal,
    error,

    // Computed
    hasFacetValues,
    hasError,
    isEmpty,

    // Facet Value Actions
    fetchFacetValues,
    fetchFacetValue,
    createFacetValue,
    updateFacetValue,
    verifyFacetValue,
    deleteFacetValue,
    fetchEntityFacetsSummary,
    searchFacetValues,

    // Batch Operations
    bulkVerifyFacetValues,
    bulkDeleteFacetValues,

    // Optimistic Updates
    updateFacetValueOptimistic,
    deleteFacetValueOptimistic,
    verifyFacetValueOptimistic,

    // Utility
    clearError,
    resetState,
    invalidateSummaryCache,
  }
})

// Re-export types for convenience
export type { FacetValue, EntityFacetsSummary, FacetValueAggregated } from './types/entity'
