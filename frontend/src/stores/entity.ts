/**
 * Entity Store
 *
 * Manages entity types, entities, facets, relations, and analysis templates
 * for the flexible Entity-Facet system.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { entityApi, facetApi, relationApi, analysisApi } from '@/services/api'

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
  hierarchy_config: Record<string, any> | null
  attribute_schema: Record<string, any> | null
  display_order: number
  is_active: boolean
  is_system: boolean
  entity_count: number
  created_at: string
  updated_at: string
}

export interface Entity {
  id: string
  entity_type_id: string
  entity_type_slug: string | null
  entity_type_name: string | null
  name: string
  name_normalized: string
  slug: string
  external_id: string | null
  parent_id: string | null
  parent_name: string | null
  hierarchy_path: string
  hierarchy_level: number
  core_attributes: Record<string, any>
  latitude: number | null
  longitude: number | null
  is_active: boolean
  facet_count: number
  relation_count: number
  children_count: number
  created_at: string
  updated_at: string
}

export interface EntityBrief {
  id: string
  name: string
  slug: string
  entity_type_slug: string | null
  entity_type_name: string | null
  hierarchy_path: string
}

export interface FacetType {
  id: string
  slug: string
  name: string
  description: string | null
  value_type: string
  value_schema: Record<string, any> | null
  icon: string
  color: string
  display_order: number
  aggregation_method: string
  deduplication_fields: string[]
  is_time_based: boolean
  time_field_path: string | null
  default_time_filter: string | null
  ai_extraction_enabled: boolean
  ai_extraction_prompt: string | null
  is_active: boolean
  is_system: boolean
  value_count: number
  created_at: string
  updated_at: string
}

export interface FacetValue {
  id: string
  entity_id: string
  entity_name: string | null
  facet_type_id: string
  facet_type_slug: string | null
  facet_type_name: string | null
  category_id: string | null
  category_name: string | null
  value: any
  text_representation: string
  event_date: string | null
  valid_from: string | null
  valid_until: string | null
  source_document_id: string | null
  document_title: string | null
  document_url: string | null
  source_url: string | null
  confidence_score: number
  ai_model_used: string | null
  human_verified: boolean
  verified_by: string | null
  verified_at: string | null
  occurrence_count: number
  first_seen: string | null
  last_seen: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface RelationType {
  id: string
  slug: string
  name: string
  name_inverse: string
  description: string | null
  source_entity_type_id: string
  source_entity_type_name: string | null
  source_entity_type_slug: string | null
  target_entity_type_id: string
  target_entity_type_name: string | null
  target_entity_type_slug: string | null
  cardinality: string
  attribute_schema: Record<string, any> | null
  icon: string
  color: string
  display_order: number
  is_active: boolean
  is_system: boolean
  relation_count: number
  created_at: string
  updated_at: string
}

export interface EntityRelation {
  id: string
  relation_type_id: string
  relation_type_slug: string | null
  relation_type_name: string | null
  source_entity_id: string
  source_entity_name: string | null
  source_entity_type_slug: string | null
  target_entity_id: string
  target_entity_name: string | null
  target_entity_type_slug: string | null
  attributes: Record<string, any>
  valid_from: string | null
  valid_until: string | null
  source_document_id: string | null
  source_url: string | null
  confidence_score: number
  ai_model_used: string | null
  human_verified: boolean
  verified_by: string | null
  verified_at: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface AnalysisTemplate {
  id: string
  slug: string
  name: string
  description: string | null
  category_id: string | null
  category_name: string | null
  primary_entity_type_id: string
  primary_entity_type_name: string | null
  primary_entity_type_slug: string | null
  facet_config: FacetConfig[]
  aggregation_config: AggregationConfig
  display_config: DisplayConfig
  extraction_prompt_template: string | null
  is_default: boolean
  is_active: boolean
  is_system: boolean
  display_order: number
  created_at: string
  updated_at: string
}

export interface FacetConfig {
  facet_type_slug: string
  enabled: boolean
  display_order: number
  label: string | null
  time_filter: string | null
  custom_prompt: string | null
}

export interface AggregationConfig {
  group_by: string
  show_relations: string[]
  sort_by: string
  sort_order: string
}

export interface DisplayConfig {
  columns: string[]
  default_sort: string
  show_hierarchy: boolean
  show_map: boolean
}

export interface AnalysisOverviewItem {
  entity_id: string
  entity_name: string
  entity_slug: string
  external_id: string | null
  hierarchy_path: string
  latitude: number | null
  longitude: number | null
  total_facet_values: number
  verified_count: number
  avg_confidence: number
  facet_counts: Record<string, number>
  relation_count: number
  source_count: number
  latest_facet_date: string | null
}

export interface EntityFacetsSummary {
  entity_id: string
  entity_name: string
  entity_type_slug: string | null
  total_facet_values: number
  verified_count: number
  facet_type_count: number
  facets_by_type: FacetValueAggregated[]
}

export interface FacetValueAggregated {
  facet_type_id: string
  facet_type_slug: string
  facet_type_name: string
  facet_type_icon: string
  facet_type_color: string
  value_count: number
  verified_count: number
  avg_confidence: number
  latest_value: string | null
  sample_values: any[]
}

// ============================================================================
// Store Definition
// ============================================================================

export const useEntityStore = defineStore('entity', () => {
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

  // Facet Types
  const facetTypes = ref<FacetType[]>([])
  const facetTypesLoading = ref(false)

  // Facet Values
  const facetValues = ref<FacetValue[]>([])
  const facetValuesLoading = ref(false)
  const facetValuesTotal = ref(0)

  // Relation Types
  const relationTypes = ref<RelationType[]>([])
  const relationTypesLoading = ref(false)

  // Entity Relations
  const entityRelations = ref<EntityRelation[]>([])
  const entityRelationsLoading = ref(false)

  // Analysis Templates
  const analysisTemplates = ref<AnalysisTemplate[]>([])
  const analysisTemplatesLoading = ref(false)
  const selectedTemplate = ref<AnalysisTemplate | null>(null)

  // Analysis Overview
  const analysisOverview = ref<AnalysisOverviewItem[]>([])
  const analysisOverviewLoading = ref(false)

  // Entity Report
  const entityReport = ref<any>(null)
  const entityReportLoading = ref(false)

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
  // Entity Type Actions
  // ========================================

  async function fetchEntityTypes(params?: any) {
    entityTypesLoading.value = true
    error.value = null
    try {
      const response = await entityApi.getEntityTypes(params)
      entityTypes.value = response.data.items
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Failed to fetch entity types'
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
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Failed to fetch entity type'
      throw err
    }
  }

  async function fetchEntityTypeBySlug(slug: string) {
    try {
      const response = await entityApi.getEntityTypeBySlug(slug)
      selectedEntityType.value = response.data
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Failed to fetch entity type'
      throw err
    }
  }

  // ========================================
  // Entity Actions
  // ========================================

  async function fetchEntities(params?: any) {
    entitiesLoading.value = true
    error.value = null
    try {
      const response = await entityApi.getEntities(params)
      entities.value = response.data.items
      entitiesTotal.value = response.data.total
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Failed to fetch entities'
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
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Failed to fetch entity'
      throw err
    }
  }

  async function fetchEntityBySlug(typeSlug: string, entitySlug: string) {
    try {
      const response = await entityApi.getEntityBySlug(typeSlug, entitySlug)
      selectedEntity.value = response.data
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Failed to fetch entity'
      throw err
    }
  }

  async function createEntity(data: any) {
    try {
      const response = await entityApi.createEntity(data)
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Failed to create entity'
      throw err
    }
  }

  async function updateEntity(id: string, data: any) {
    try {
      const response = await entityApi.updateEntity(id, data)
      if (selectedEntity.value?.id === id) {
        selectedEntity.value = response.data
      }
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Failed to update entity'
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
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Failed to delete entity'
      throw err
    }
  }

  // ========================================
  // Facet Type Actions
  // ========================================

  async function fetchFacetTypes(params?: any) {
    facetTypesLoading.value = true
    error.value = null
    try {
      const response = await facetApi.getFacetTypes(params)
      facetTypes.value = response.data.items
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Failed to fetch facet types'
      throw err
    } finally {
      facetTypesLoading.value = false
    }
  }

  // ========================================
  // Facet Value Actions
  // ========================================

  async function fetchFacetValues(params?: any) {
    facetValuesLoading.value = true
    error.value = null
    try {
      const response = await facetApi.getFacetValues(params)
      facetValues.value = response.data.items
      facetValuesTotal.value = response.data.total
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Failed to fetch facet values'
      throw err
    } finally {
      facetValuesLoading.value = false
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
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Failed to verify facet value'
      throw err
    }
  }

  async function fetchEntityFacetsSummary(entityId: string, params?: any) {
    try {
      const response = await facetApi.getEntityFacetsSummary(entityId, params)
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Failed to fetch entity facets summary'
      throw err
    }
  }

  // ========================================
  // Relation Type Actions
  // ========================================

  async function fetchRelationTypes(params?: any) {
    relationTypesLoading.value = true
    error.value = null
    try {
      const response = await relationApi.getRelationTypes(params)
      relationTypes.value = response.data.items
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Failed to fetch relation types'
      throw err
    } finally {
      relationTypesLoading.value = false
    }
  }

  // ========================================
  // Entity Relation Actions
  // ========================================

  async function fetchEntityRelations(params?: any) {
    entityRelationsLoading.value = true
    error.value = null
    try {
      const response = await relationApi.getRelations(params)
      entityRelations.value = response.data.items
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Failed to fetch entity relations'
      throw err
    } finally {
      entityRelationsLoading.value = false
    }
  }

  async function fetchEntityRelationsGraph(entityId: string, params?: any) {
    try {
      const response = await relationApi.getEntityRelationsGraph(entityId, params)
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Failed to fetch relations graph'
      throw err
    }
  }

  // ========================================
  // Analysis Template Actions
  // ========================================

  async function fetchAnalysisTemplates(params?: any) {
    analysisTemplatesLoading.value = true
    error.value = null
    try {
      const response = await analysisApi.getTemplates(params)
      analysisTemplates.value = response.data.items
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Failed to fetch analysis templates'
      throw err
    } finally {
      analysisTemplatesLoading.value = false
    }
  }

  async function fetchAnalysisTemplate(id: string) {
    try {
      const response = await analysisApi.getTemplate(id)
      selectedTemplate.value = response.data
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Failed to fetch analysis template'
      throw err
    }
  }

  async function fetchAnalysisTemplateBySlug(slug: string) {
    try {
      const response = await analysisApi.getTemplateBySlug(slug)
      selectedTemplate.value = response.data
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Failed to fetch analysis template'
      throw err
    }
  }

  // ========================================
  // Analysis Overview & Report Actions
  // ========================================

  async function fetchAnalysisOverview(params?: any) {
    analysisOverviewLoading.value = true
    error.value = null
    try {
      const response = await analysisApi.getOverview(params)
      analysisOverview.value = response.data.entities
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Failed to fetch analysis overview'
      throw err
    } finally {
      analysisOverviewLoading.value = false
    }
  }

  async function fetchEntityReport(entityId: string, params?: any) {
    entityReportLoading.value = true
    error.value = null
    try {
      const response = await analysisApi.getEntityReport(entityId, params)
      entityReport.value = response.data
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Failed to fetch entity report'
      throw err
    } finally {
      entityReportLoading.value = false
    }
  }

  async function fetchAnalysisStats(params?: any) {
    try {
      const response = await analysisApi.getStats(params)
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Failed to fetch analysis stats'
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
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Failed to fetch location filter options'
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
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Failed to fetch attribute filter options'
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
  }

  function resetState() {
    entityTypes.value = []
    entities.value = []
    facetTypes.value = []
    facetValues.value = []
    relationTypes.value = []
    entityRelations.value = []
    analysisTemplates.value = []
    analysisOverview.value = []
    selectedEntityType.value = null
    selectedEntity.value = null
    selectedTemplate.value = null
    entityReport.value = null
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
    entities,
    entitiesLoading,
    entitiesTotal,
    selectedEntity,
    facetTypes,
    facetTypesLoading,
    facetValues,
    facetValuesLoading,
    facetValuesTotal,
    relationTypes,
    relationTypesLoading,
    entityRelations,
    entityRelationsLoading,
    analysisTemplates,
    analysisTemplatesLoading,
    selectedTemplate,
    analysisOverview,
    analysisOverviewLoading,
    entityReport,
    entityReportLoading,
    locationFilterOptions,
    attributeFilterOptions,
    filterOptionsLoading,
    error,

    // Computed
    primaryEntityTypes,
    activeEntityTypes,
    activeFacetTypes,
    timeBasedFacetTypes,
    aiEnabledFacetTypes,

    // Entity Type Actions
    fetchEntityTypes,
    fetchEntityType,
    fetchEntityTypeBySlug,

    // Entity Actions
    fetchEntities,
    fetchEntity,
    fetchEntityBySlug,
    createEntity,
    updateEntity,
    deleteEntity,

    // Facet Type Actions
    fetchFacetTypes,

    // Facet Value Actions
    fetchFacetValues,
    verifyFacetValue,
    fetchEntityFacetsSummary,

    // Relation Type Actions
    fetchRelationTypes,

    // Entity Relation Actions
    fetchEntityRelations,
    fetchEntityRelationsGraph,

    // Analysis Template Actions
    fetchAnalysisTemplates,
    fetchAnalysisTemplate,
    fetchAnalysisTemplateBySlug,

    // Analysis Overview & Report Actions
    fetchAnalysisOverview,
    fetchEntityReport,
    fetchAnalysisStats,

    // Filter Options Actions
    fetchLocationFilterOptions,
    fetchAttributeFilterOptions,

    // Utility
    clearError,
    resetState,
  }
})
