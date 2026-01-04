/**
 * Entity Store
 *
 * Core store for entity types and entities.
 * For facet values, use useFacetStore from './facet'
 * For facet types, use useFacetTypesStore from './facetTypes'
 * For relations, use useRelationStore from './relation'
 * For analysis, use useAnalysisStore from './analysis'
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { entityApi } from '@/services/api'
import type { EntityCreate, EntityUpdate } from '@/types/entity'
import type { EntityType, Entity } from './types/entity'
import { getErrorMessage } from './types/entity'

// Import sub-stores for backwards compatibility
import { useFacetStore } from './facet'
import { useFacetTypesStore } from './facetTypes'
import { useRelationStore } from './relation'
import { useAnalysisStore } from './analysis'

// ============================================================================
// Store Definition
// ============================================================================

export const useEntityStore = defineStore('entity', () => {
  // Get sub-stores
  const facetStore = useFacetStore()
  const facetTypesStore = useFacetTypesStore()
  const relationStore = useRelationStore()
  const analysisStore = useAnalysisStore()

  // ========================================
  // State
  // ========================================

  // Entity Types
  const entityTypes = ref<EntityType[]>([])
  const entityTypesLoading = ref(false)
  const selectedEntityType = ref<EntityType | null>(null)

  // Entities
  const entities = ref<Entity[]>([])
  const entitiesLoading = ref(false)
  const entitiesTotal = ref(0)
  const selectedEntity = ref<Entity | null>(null)

  // Filter Options
  const locationFilterOptions = ref<{
    countries: string[]
    admin_level_1: string[]
    admin_level_2: string[]
  }>({ countries: [], admin_level_1: [], admin_level_2: [] })
  const attributeFilterOptions = ref<{
    entity_type_slug: string
    entity_type_name: string
    attributes: Array<{
      key: string
      title: string
      description: string | null
      type: string
      format: string | null
    }>
    attribute_values?: Record<string, string[]>
  } | null>(null)
  const filterOptionsLoading = ref(false)

  // Error handling
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

  // Proxy computed from facetTypesStore for backwards compatibility
  const activeFacetTypes = computed(() => facetTypesStore.activeFacetTypes)
  const timeBasedFacetTypes = computed(() => facetTypesStore.timeBasedFacetTypes)
  const aiEnabledFacetTypes = computed(() => facetTypesStore.aiEnabledFacetTypes)

  // ========================================
  // Entity Type Actions
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

  // ========================================
  // Entity Actions
  // ========================================

  async function fetchEntities(params?: Record<string, unknown>) {
    entitiesLoading.value = true
    error.value = null
    try {
      const response = await entityApi.getEntities(params)
      entities.value = response.data.items
      entitiesTotal.value = response.data.total
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to fetch entities'
      throw err
    } finally {
      entitiesLoading.value = false
    }
  }

  async function fetchEntity(id: string) {
    try {
      const response = await entityApi.getEntity(id)
      selectedEntity.value = response.data
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to fetch entity'
      throw err
    }
  }

  async function fetchEntityBySlug(typeSlug: string, entitySlug: string) {
    try {
      const response = await entityApi.getEntityBySlug(typeSlug, entitySlug)
      selectedEntity.value = response.data
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to fetch entity'
      throw err
    }
  }

  async function createEntity(data: EntityCreate) {
    try {
      const response = await entityApi.createEntity(data)
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to create entity'
      throw err
    }
  }

  async function updateEntity(id: string, data: EntityUpdate) {
    try {
      const response = await entityApi.updateEntity(id, data)
      if (selectedEntity.value?.id === id) {
        selectedEntity.value = response.data
      }
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to update entity'
      throw err
    }
  }

  async function deleteEntity(id: string, force = false) {
    try {
      await entityApi.deleteEntity(id, force)
      entities.value = entities.value.filter(e => e.id !== id)
      if (selectedEntity.value?.id === id) {
        selectedEntity.value = null
      }
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to delete entity'
      throw err
    }
  }

  // ========================================
  // Filter Options Actions
  // ========================================

  async function fetchLocationFilterOptions(params?: { country?: string; admin_level_1?: string }) {
    filterOptionsLoading.value = true
    try {
      const response = await entityApi.getLocationFilterOptions(params)
      locationFilterOptions.value = response.data
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to fetch location filter options'
      throw err
    } finally {
      filterOptionsLoading.value = false
    }
  }

  async function fetchAttributeFilterOptions(params: { entity_type_slug: string; attribute_key?: string }) {
    filterOptionsLoading.value = true
    try {
      const response = await entityApi.getAttributeFilterOptions(params)
      attributeFilterOptions.value = response.data
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to fetch attribute filter options'
      throw err
    } finally {
      filterOptionsLoading.value = false
    }
  }

  // ========================================
  // Utility Functions
  // ========================================

  function clearError() {
    error.value = null
    facetStore.clearError()
    facetTypesStore.clearError()
    relationStore.clearError()
    analysisStore.clearError()
  }

  function resetState() {
    entityTypes.value = []
    entities.value = []
    selectedEntityType.value = null
    selectedEntity.value = null
    error.value = null
    // Reset sub-stores
    facetStore.resetState()
    facetTypesStore.resetState()
    relationStore.resetState()
    analysisStore.resetState()
  }

  // ========================================
  // Return - includes backwards compatibility proxies
  // ========================================

  return {
    // Core State
    entityTypes,
    entityTypesLoading,
    selectedEntityType,
    entities,
    entitiesLoading,
    entitiesTotal,
    selectedEntity,
    locationFilterOptions,
    attributeFilterOptions,
    filterOptionsLoading,
    error,

    // Core Computed
    primaryEntityTypes,
    activeEntityTypes,

    // Core Entity Type Actions
    fetchEntityTypes,
    fetchEntityType,
    fetchEntityTypeBySlug,

    // Core Entity Actions
    fetchEntities,
    fetchEntity,
    fetchEntityBySlug,
    createEntity,
    updateEntity,
    deleteEntity,

    // Filter Options Actions
    fetchLocationFilterOptions,
    fetchAttributeFilterOptions,

    // Utility
    clearError,
    resetState,

    // =========================================================================
    // BACKWARDS COMPATIBILITY PROXIES
    // These proxy to the new sub-stores for existing code that uses entityStore
    // Consider migrating to the dedicated stores:
    //   - useFacetTypesStore for facet types
    //   - useFacetStore for facet values
    //   - useRelationStore for relations
    //   - useAnalysisStore for analysis
    // =========================================================================

    // Facet Types State (from facetTypesStore)
    facetTypes: computed(() => facetTypesStore.facetTypes),
    facetTypesLoading: computed(() => facetTypesStore.facetTypesLoading),

    // Facet Values State (from facetStore)
    facetValues: computed(() => facetStore.facetValues),
    facetValuesLoading: computed(() => facetStore.facetValuesLoading),
    facetValuesTotal: computed(() => facetStore.facetValuesTotal),

    // Facet Types Computed (from facetTypesStore)
    activeFacetTypes,
    timeBasedFacetTypes,
    aiEnabledFacetTypes,

    // Facet Type Actions (proxy to facetTypesStore)
    fetchFacetTypes: facetTypesStore.fetchFacetTypes,
    fetchFacetType: facetTypesStore.fetchFacetType,
    fetchFacetTypeBySlug: facetTypesStore.fetchFacetTypeBySlug,
    createFacetType: facetTypesStore.createFacetType,
    updateFacetType: facetTypesStore.updateFacetType,
    deleteFacetType: facetTypesStore.deleteFacetType,
    generateFacetTypeSchema: facetTypesStore.generateFacetTypeSchema,

    // Facet Value Actions (proxy to facetStore)
    fetchFacetValues: facetStore.fetchFacetValues,
    fetchFacetValue: facetStore.fetchFacetValue,
    createFacetValue: facetStore.createFacetValue,
    updateFacetValue: facetStore.updateFacetValue,
    verifyFacetValue: facetStore.verifyFacetValue,
    deleteFacetValue: facetStore.deleteFacetValue,
    fetchEntityFacetsSummary: facetStore.fetchEntityFacetsSummary,
    searchFacetValues: facetStore.searchFacetValues,

    // Relation State (from relationStore)
    relationTypes: computed(() => relationStore.relationTypes),
    relationTypesLoading: computed(() => relationStore.relationTypesLoading),
    entityRelations: computed(() => relationStore.entityRelations),
    entityRelationsLoading: computed(() => relationStore.entityRelationsLoading),

    // Relation Actions (proxy to relationStore)
    fetchRelationTypes: relationStore.fetchRelationTypes,
    fetchEntityRelations: relationStore.fetchEntityRelations,
    fetchEntityRelationsGraph: relationStore.fetchEntityRelationsGraph,

    // Analysis State (from analysisStore)
    analysisTemplates: computed(() => analysisStore.analysisTemplates),
    analysisTemplatesLoading: computed(() => analysisStore.analysisTemplatesLoading),
    selectedTemplate: computed(() => analysisStore.selectedTemplate),
    analysisOverview: computed(() => analysisStore.analysisOverview),
    analysisOverviewLoading: computed(() => analysisStore.analysisOverviewLoading),
    entityReport: computed(() => analysisStore.entityReport),
    entityReportLoading: computed(() => analysisStore.entityReportLoading),

    // Analysis Actions (proxy to analysisStore)
    fetchAnalysisTemplates: analysisStore.fetchAnalysisTemplates,
    fetchAnalysisTemplate: analysisStore.fetchAnalysisTemplate,
    fetchAnalysisTemplateBySlug: analysisStore.fetchAnalysisTemplateBySlug,
    fetchAnalysisOverview: analysisStore.fetchAnalysisOverview,
    fetchEntityReport: analysisStore.fetchEntityReport,
    fetchAnalysisStats: analysisStore.fetchAnalysisStats,
    setSelectedTemplate: analysisStore.setSelectedTemplate,
  }
})

// Re-export all types for backwards compatibility
export type {
  EntityType,
  Entity,
  EntityBrief,
  FacetType,
  FacetValue,
  FacetValueAggregated,
  EntityFacetsSummary,
  RelationType,
  EntityRelation,
  AnalysisTemplate,
  AnalysisOverviewItem,
  EntityReport,
  FacetConfig,
  AggregationConfig,
  DisplayConfig,
} from './types/entity'
