/**
 * Entity Types Store
 *
 * Manages entity type definitions for the flexible Entity-Facet system.
 * Extracted from entity.ts for better modularity.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { entityApi } from '@/services/api'
import { extractErrorMessage as getErrorMessage } from '@/utils/errorMessage'

// ============================================================================
// Types
// ============================================================================

export interface EntityType {
  id: string
  slug: string
  name: string
  name_plural: string
  description: string | null
  icon: string
  color: string
  is_primary: boolean
  supports_hierarchy: boolean
  supports_pysis: boolean
  hierarchy_config: Record<string, unknown> | null
  attribute_schema: Record<string, unknown> | null
  display_order: number
  is_active: boolean
  is_system: boolean
  entity_count: number
  created_at: string
  updated_at: string
}

// ============================================================================
// Store Definition
// ============================================================================

export const useEntityTypesStore = defineStore('entityTypes', () => {
  // ========================================
  // State
  // ========================================

  const entityTypes = ref<EntityType[]>([])
  const entityTypesLoading = ref(false)
  const selectedEntityType = ref<EntityType | null>(null)
  const error = ref<string | null>(null)

  // ========================================
  // Computed
  // ========================================

  const primaryEntityTypes = computed(() =>
    entityTypes.value.filter(et => et.is_primary && et.is_active)
  )

  const activeEntityTypes = computed(() =>
    entityTypes.value.filter(et => et.is_active)
  )

  const entityTypesBySlug = computed(() => {
    const map = new Map<string, EntityType>()
    entityTypes.value.forEach(et => map.set(et.slug, et))
    return map
  })

  // ========================================
  // Actions
  // ========================================

  async function fetchEntityTypes(params?: Record<string, unknown>) {
    entityTypesLoading.value = true
    error.value = null
    try {
      const response = await entityApi.getEntityTypes(params)
      entityTypes.value = response.data.items
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to fetch entity types'
      throw err
    } finally {
      entityTypesLoading.value = false
    }
  }

  async function fetchEntityType(id: string) {
    try {
      const response = await entityApi.getEntityType(id)
      selectedEntityType.value = response.data
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to fetch entity type'
      throw err
    }
  }

  async function fetchEntityTypeBySlug(slug: string) {
    try {
      const response = await entityApi.getEntityTypeBySlug(slug)
      selectedEntityType.value = response.data
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to fetch entity type'
      throw err
    }
  }

  function getEntityTypeBySlug(slug: string): EntityType | undefined {
    return entityTypesBySlug.value.get(slug)
  }

  function clearError() {
    error.value = null
  }

  function resetState() {
    entityTypes.value = []
    selectedEntityType.value = null
    error.value = null
  }

  // ========================================
  // Return
  // ========================================

  return {
    // State
    entityTypes,
    entityTypesLoading,
    selectedEntityType,
    error,

    // Computed
    primaryEntityTypes,
    activeEntityTypes,
    entityTypesBySlug,

    // Actions
    fetchEntityTypes,
    fetchEntityType,
    fetchEntityTypeBySlug,
    getEntityTypeBySlug,
    clearError,
    resetState,
  }
})
