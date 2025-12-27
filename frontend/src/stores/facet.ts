/**
 * Facet Store
 *
 * Manages facet types and facet values for the Entity-Facet system.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { facetApi } from '@/services/api'
import type {
  FacetTypeCreate,
  FacetTypeUpdate,
  FacetValueCreate,
  FacetValueUpdate,
} from '@/types/entity'
import type { FacetType, FacetValue, EntityFacetsSummary } from './types/entity'
import { getErrorMessage } from './types/entity'

// ============================================================================
// Store Definition
// ============================================================================

export const useFacetStore = defineStore('facet', () => {
  // ========================================
  // State
  // ========================================

  // Facet Types
  const facetTypes = ref<FacetType[]>([])
  const facetTypesLoading = ref(false)

  // Facet Values
  const facetValues = ref<FacetValue[]>([])
  const facetValuesLoading = ref(false)
  const facetValuesTotal = ref(0)

  // Error handling
  const error = ref<string | null>(null)

  // ========================================
  // Computed
  // ========================================

  const activeFacetTypes = computed(() =>
    facetTypes.value.filter(ft => ft.is_active)
  )

  const timeBasedFacetTypes = computed(() =>
    facetTypes.value.filter(ft => ft.is_time_based && ft.is_active)
  )

  const aiEnabledFacetTypes = computed(() =>
    facetTypes.value.filter(ft => ft.ai_extraction_enabled && ft.is_active)
  )

  // ========================================
  // Facet Type Actions
  // ========================================

  async function fetchFacetTypes(params?: Record<string, unknown>) {
    facetTypesLoading.value = true
    error.value = null
    try {
      const response = await facetApi.getFacetTypes(params)
      facetTypes.value = response.data.items
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to fetch facet types'
      throw err
    } finally {
      facetTypesLoading.value = false
    }
  }

  async function fetchFacetType(id: string) {
    try {
      const response = await facetApi.getFacetType(id)
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to fetch facet type'
      throw err
    }
  }

  async function fetchFacetTypeBySlug(slug: string) {
    try {
      const response = await facetApi.getFacetTypeBySlug(slug)
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to fetch facet type'
      throw err
    }
  }

  async function createFacetType(data: FacetTypeCreate) {
    try {
      const response = await facetApi.createFacetType(data)
      // Refresh the list to include the new facet type
      await fetchFacetTypes()
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to create facet type'
      throw err
    }
  }

  async function updateFacetType(id: string, data: FacetTypeUpdate) {
    try {
      const response = await facetApi.updateFacetType(id, data)
      // Update local state
      const index = facetTypes.value.findIndex(ft => ft.id === id)
      if (index >= 0) {
        facetTypes.value[index] = response.data
      }
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to update facet type'
      throw err
    }
  }

  async function deleteFacetType(id: string) {
    try {
      await facetApi.deleteFacetType(id)
      facetTypes.value = facetTypes.value.filter(ft => ft.id !== id)
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to delete facet type'
      throw err
    }
  }

  async function generateFacetTypeSchema(data: {
    name: string
    name_plural?: string
    description?: string
    applicable_entity_types?: string[]
  }) {
    try {
      const response = await facetApi.generateFacetTypeSchema(data)
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to generate facet type schema'
      throw err
    }
  }

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

  async function fetchEntityFacetsSummary(entityId: string, params?: Record<string, unknown>): Promise<EntityFacetsSummary> {
    try {
      const response = await facetApi.getEntityFacetsSummary(entityId, params)
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to fetch entity facets summary'
      throw err
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
  // Utility Functions
  // ========================================

  function clearError() {
    error.value = null
  }

  function resetState() {
    facetTypes.value = []
    facetValues.value = []
    facetValuesTotal.value = 0
    error.value = null
  }

  // ========================================
  // Return
  // ========================================

  return {
    // State
    facetTypes,
    facetTypesLoading,
    facetValues,
    facetValuesLoading,
    facetValuesTotal,
    error,

    // Computed
    activeFacetTypes,
    timeBasedFacetTypes,
    aiEnabledFacetTypes,

    // Facet Type Actions
    fetchFacetTypes,
    fetchFacetType,
    fetchFacetTypeBySlug,
    createFacetType,
    updateFacetType,
    deleteFacetType,
    generateFacetTypeSchema,

    // Facet Value Actions
    fetchFacetValues,
    fetchFacetValue,
    createFacetValue,
    updateFacetValue,
    verifyFacetValue,
    deleteFacetValue,
    fetchEntityFacetsSummary,
    searchFacetValues,

    // Utility
    clearError,
    resetState,
  }
})

// Re-export types for convenience
export type { FacetType, FacetValue, EntityFacetsSummary, FacetValueAggregated } from './types/entity'
