/**
 * Relation Store
 *
 * Manages relation types and entity relations for the Entity-Facet system.
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { relationApi } from '@/services/api'
import type { RelationType, EntityRelation } from './types/entity'
import { getErrorMessage } from './types/entity'

// ============================================================================
// Store Definition
// ============================================================================

export const useRelationStore = defineStore('relation', () => {
  // ========================================
  // State
  // ========================================

  // Relation Types
  const relationTypes = ref<RelationType[]>([])
  const relationTypesLoading = ref(false)

  // Entity Relations
  const entityRelations = ref<EntityRelation[]>([])
  const entityRelationsLoading = ref(false)

  // Error handling
  const error = ref<string | null>(null)

  // ========================================
  // Relation Type Actions
  // ========================================

  async function fetchRelationTypes(params?: Record<string, unknown>) {
    relationTypesLoading.value = true
    error.value = null
    try {
      const response = await relationApi.getRelationTypes(params)
      relationTypes.value = response.data.items
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to fetch relation types'
      throw err
    } finally {
      relationTypesLoading.value = false
    }
  }

  // ========================================
  // Entity Relation Actions
  // ========================================

  async function fetchEntityRelations(params?: Record<string, unknown>) {
    entityRelationsLoading.value = true
    error.value = null
    try {
      const response = await relationApi.getRelations(params)
      entityRelations.value = response.data.items
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to fetch entity relations'
      throw err
    } finally {
      entityRelationsLoading.value = false
    }
  }

  async function fetchEntityRelationsGraph(entityId: string, params?: Record<string, unknown>) {
    try {
      const response = await relationApi.getEntityRelationsGraph(entityId, params)
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to fetch relations graph'
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
    relationTypes.value = []
    entityRelations.value = []
    error.value = null
  }

  // ========================================
  // Return
  // ========================================

  return {
    // State
    relationTypes,
    relationTypesLoading,
    entityRelations,
    entityRelationsLoading,
    error,

    // Relation Type Actions
    fetchRelationTypes,

    // Entity Relation Actions
    fetchEntityRelations,
    fetchEntityRelationsGraph,

    // Utility
    clearError,
    resetState,
  }
})

// Re-export types for convenience
export type { RelationType, EntityRelation } from './types/entity'
