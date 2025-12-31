/**
 * Entity Store Types
 *
 * Shared types for all entity-related stores.
 */

// ============================================================================
// Entity Types
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

export interface Entity {
  id: string
  entity_type_id: string
  entity_type_slug: string | null
  entity_type_name: string | null
  name: string
  name_normalized: string
  slug: string
  external_id: string | null
  api_configuration_id: string | null
  external_source_name: string | null
  parent_id: string | null
  parent_name: string | null
  parent_slug: string | null
  hierarchy_path: string
  hierarchy_level: number
  core_attributes: Record<string, unknown>
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

// ============================================================================
// Facet Types
// ============================================================================

export interface FacetType {
  id: string
  slug: string
  name: string
  name_plural?: string
  description: string | null
  value_type: string
  value_schema: Record<string, unknown> | null
  applicable_entity_type_slugs?: string[]
  icon?: string
  color?: string
  display_order?: number
  aggregation_method?: string
  deduplication_fields?: string[]
  is_time_based?: boolean
  time_field_path?: string | null
  default_time_filter?: string | null
  ai_extraction_enabled?: boolean
  ai_extraction_prompt?: string | null
  is_active?: boolean
  is_system?: boolean
  value_count?: number
  created_at?: string
  updated_at?: string
  // Entity reference configuration (for linking facets to other entities)
  allows_entity_reference?: boolean
  target_entity_type_slugs?: string[]
  auto_create_entity?: boolean
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
  value: unknown
  text_representation?: string
  event_date: string | null
  valid_from: string | null
  valid_until: string | null
  source_type: string | null
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
  facet_type_value_type: string
  value_count: number
  verified_count: number
  avg_confidence: number
  latest_value: string | null
  // sample_values contains partial FacetValue objects from API
  sample_values: Record<string, unknown>[]
}

// ============================================================================
// Relation Types
// ============================================================================

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
  attribute_schema: Record<string, unknown> | null
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
  attributes: Record<string, unknown>
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

// ============================================================================
// Analysis Types
// ============================================================================

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

export interface EntityReport {
  entity: Entity
  facets_summary: EntityFacetsSummary
  relations: EntityRelation[]
  documents: Array<{
    id: string
    title: string
    url: string
    analyzed_at: string | null
  }>
  sources: Array<{
    id: string
    name: string
    url: string
    status: string
  }>
}

// ============================================================================
// Utilities
// ============================================================================

// Re-export error message utility from centralized location
export { extractErrorMessage as getErrorMessage } from '@/utils/errorMessage'
