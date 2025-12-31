/**
 * Facet Types Store
 *
 * Manages facet type definitions for the flexible Entity-Facet system.
 * Extracted from entity.ts for better modularity.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { facetApi } from '@/services/api'
import type { FacetType, FacetTypeCreate, FacetTypeUpdate } from '@/types/entity'
import { extractErrorMessage as getErrorMessage } from '@/utils/errorMessage'

// Re-export FacetType for backwards compatibility
export type { FacetType }

export interface FacetSchemaGenerationRequest {
  name: string
  name_plural?: string
  description?: string
  applicable_entity_types?: string[]
}

export interface FacetSchemaGenerationResponse {
  name: string
  name_plural: string
  slug: string
  description: string
  value_type: string
  value_schema: Record<string, unknown>
  icon: string
  color: string
  suggestions: string[]
}

// ============================================================================
// Store Definition
// ============================================================================

export const useFacetTypesStore = defineStore('facetTypes', () => {
  // ========================================
  // State
  // ========================================

  const facetTypes = ref<FacetType[]>([])
  const facetTypesLoading = ref(false)
  const selectedFacetType = ref<FacetType | null>(null)
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

  const facetTypesBySlug = computed(() => {
    const map = new Map<string, FacetType>()
    facetTypes.value.forEach(ft => map.set(ft.slug, ft))
    return map
  })

  const facetTypesForEntityType = computed(() => {
    return (entityTypeSlug: string) =>
      facetTypes.value.filter(
        ft => ft.is_active && ft.applicable_entity_type_slugs?.includes(entityTypeSlug)
      )
  })

  // ========================================
  // Actions
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
      selectedFacetType.value = response.data
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to fetch facet type'
      throw err
    }
  }

  async function fetchFacetTypeBySlug(slug: string) {
    try {
      const response = await facetApi.getFacetTypeBySlug(slug)
      selectedFacetType.value = response.data
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

  async function generateFacetTypeSchema(data: FacetSchemaGenerationRequest): Promise<FacetSchemaGenerationResponse> {
    try {
      const response = await facetApi.generateFacetTypeSchema(data)
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to generate facet type schema'
      throw err
    }
  }

  function getFacetTypeBySlug(slug: string): FacetType | undefined {
    return facetTypesBySlug.value.get(slug)
  }

  function clearError() {
    error.value = null
  }

  function resetState() {
    facetTypes.value = []
    selectedFacetType.value = null
    error.value = null
  }

  // ========================================
  // Return
  // ========================================

  return {
    // State
    facetTypes,
    facetTypesLoading,
    selectedFacetType,
    error,

    // Computed
    activeFacetTypes,
    timeBasedFacetTypes,
    aiEnabledFacetTypes,
    facetTypesBySlug,
    facetTypesForEntityType,

    // Actions
    fetchFacetTypes,
    fetchFacetType,
    fetchFacetTypeBySlug,
    createFacetType,
    updateFacetType,
    deleteFacetType,
    generateFacetTypeSchema,
    getFacetTypeBySlug,
    clearError,
    resetState,
  }
})
