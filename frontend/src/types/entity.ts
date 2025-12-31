/**
 * Entity, Facet, Relation, and Analysis API Types
 *
 * TypeScript interfaces for the core data model.
 * These types replace `any` usages in api.ts and stores.
 */

import type { PaginationParams } from './admin'

// =============================================================================
// Entity Types
// =============================================================================

export interface EntityType {
  id: string
  name: string
  name_plural: string
  slug: string
  description?: string | null
  icon?: string
  color?: string
  attribute_schema?: EntityTypeSchema | Record<string, unknown> | null
  parent_type_id?: string | null
  parent_type_slug?: string | null
  applicable_facet_types?: string[]
  supports_hierarchy: boolean
  supports_pysis?: boolean
  hierarchy_config?: Record<string, unknown> | null
  entity_count?: number
  is_active?: boolean
  is_public?: boolean
  is_primary?: boolean
  is_system?: boolean
  created_at: string
  updated_at: string
}

export interface EntityTypeSchema {
  properties: Record<string, EntityTypeSchemaProperty>
  required?: string[]
  display_fields?: string[]
  search_fields?: string[]
}

export interface EntityTypeSchemaProperty {
  type: 'string' | 'number' | 'integer' | 'boolean' | 'array' | 'object' | 'date'
  title?: string
  label?: string
  description?: string
  enum?: string[]
  format?: string
  default?: unknown
  minimum?: number
  maximum?: number
}

export interface EntityTypeListParams extends PaginationParams {
  search?: string
  is_active?: boolean
  is_primary?: boolean
  is_public?: boolean
  include_private?: boolean
  include_counts?: boolean
}

export interface EntityTypeCreate {
  name: string
  name_plural?: string
  slug?: string
  description?: string
  icon?: string
  color?: string
  attribute_schema?: EntityTypeSchema
  parent_type_id?: string
  supports_hierarchy?: boolean
  applicable_facet_types?: string[]
  is_active?: boolean
  is_public?: boolean
}

export type EntityTypeUpdate = Partial<EntityTypeCreate>

// =============================================================================
// Entity
// =============================================================================

export interface Entity {
  id: string
  entity_type_id: string
  entity_type_slug: string | null
  entity_type_name: string | null
  name: string
  name_normalized?: string
  slug: string
  description?: string | null
  location_name?: string | null
  country?: string | null
  admin_level_1?: string | null
  admin_level_2?: string | null
  latitude?: number | null
  longitude?: number | null
  // Type-specific attributes from backend
  core_attributes?: Record<string, unknown>
  // Legacy alias for backwards compatibility
  attributes?: Record<string, unknown>
  parent_id?: string | null
  parent_name?: string | null
  parent_slug?: string | null
  hierarchy_path?: string | string[]
  children_count?: number
  facet_count?: number
  relation_count?: number
  document_count?: number
  source_count?: number
  is_active?: boolean
  owner_id?: string | null
  created_at: string
  updated_at: string
  // External data source fields
  external_id?: string | null
  api_configuration_id?: string | null
  external_source_name?: string | null
  // GeoJSON geometry for complex shapes
  geometry?: {
    type: string
    coordinates: unknown
  } | null
}

export interface EntityBrief {
  id: string
  name: string
  slug?: string
  entity_type_id?: string
  entity_type_slug?: string
  entity_type_name: string
  location_name?: string
}

export interface EntityListParams extends PaginationParams {
  entity_type_slug?: string
  entity_type_id?: string
  search?: string
  country?: string
  admin_level_1?: string
  admin_level_2?: string
  parent_id?: string
  is_active?: boolean
  has_facets?: boolean
  sort_by?: 'name' | 'created_at' | 'updated_at' | 'facet_count'
  sort_order?: 'asc' | 'desc'
  api_configuration_id?: string
}

export interface EntityCreate {
  entity_type_id?: string
  entity_type_slug?: string
  name: string
  slug?: string
  description?: string
  location_name?: string
  country?: string
  admin_level_1?: string
  admin_level_2?: string
  latitude?: number
  longitude?: number
  attributes?: Record<string, unknown>
  parent_id?: string
  is_active?: boolean
  external_id?: string
  api_configuration_id?: string
}

export type EntityUpdate = Partial<EntityCreate>

export interface EntityGeoJSON {
  type: 'FeatureCollection'
  features: Array<{
    type: 'Feature'
    id: string
    properties: {
      id: string
      name: string
      entity_type_slug: string
      location_name?: string
      facet_count: number
      [key: string]: unknown
    }
    geometry: {
      type: 'Point'
      coordinates: [number, number]
    } | null
  }>
}

export interface EntityHierarchy {
  id: string
  name: string
  slug: string
  entity_type_slug: string
  parent_id?: string
  children: EntityHierarchy[]
  level: number
  path: string[]
}

// =============================================================================
// Facet Types
// =============================================================================

export type FacetValueType =
  | 'text'
  | 'number'
  | 'boolean'
  | 'date'
  | 'datetime'
  | 'url'
  | 'email'
  | 'phone'
  | 'address'
  | 'json'
  | 'history'
  | 'reference'
  | 'list'
  | string

export interface FacetType {
  id: string
  name: string
  name_plural?: string
  slug: string
  description?: string | null
  value_type: string
  value_schema?: FacetTypeValueSchema | Record<string, unknown> | null
  icon?: string
  color?: string
  applicable_entity_types?: string[]
  applicable_entity_type_slugs?: string[]
  is_system?: boolean
  is_active?: boolean
  facet_count?: number
  created_at?: string
  updated_at?: string
  // Additional fields from API
  aggregation_method?: string
  deduplication_fields?: string[]
  is_time_based?: boolean
  time_field_path?: string | null  // Can be null from API
  default_time_filter?: string | null  // Can be null from API
  ai_extraction_enabled?: boolean
  ai_extraction_prompt?: string | null  // Can be null from API
  display_order?: number
  // Entity reference configuration (for linking facets to other entities)
  allows_entity_reference?: boolean
  target_entity_type_slugs?: string[]
  auto_create_entity?: boolean
}

/**
 * Display configuration for rendering FacetValues in the UI.
 * This is stored in FacetType.value_schema.display
 */
export interface FacetDisplayConfig {
  /** The primary field to display as main text (e.g., "description") */
  primary_field?: string
  /** Fields to display as chips/tags (e.g., ["type", "severity"]) */
  chip_fields?: string[]
  /** Field containing a quote to display in a quote block */
  quote_field?: string
  /** Field that represents severity (for color coding) */
  severity_field?: string
  /** Color mapping for severity values (e.g., {"hoch": "error", "mittel": "warning"}) */
  severity_colors?: Record<string, string>
  /** Layout style: "card", "inline", or "list" */
  layout?: 'card' | 'inline' | 'list'
}

export interface FacetTypeValueSchema {
  type?: string
  properties?: Record<string, unknown>
  format?: string
  enum?: string[]
  min?: number
  max?: number
  pattern?: string
  unit?: string
  unit_label?: string
  precision?: number
  tracks?: Record<string, FacetTrackConfig>
  reference_entity_type?: string
  /** Display configuration for UI rendering */
  display?: FacetDisplayConfig
  [key: string]: unknown
}

export interface FacetTrackConfig {
  label: string
  color: string
  style?: 'solid' | 'dashed' | 'dotted'
}

export interface FacetTypeListParams extends PaginationParams {
  search?: string
  value_type?: FacetValueType
  entity_type_slug?: string
  is_active?: boolean
  is_system?: boolean
  needs_review?: boolean
  include_counts?: boolean
}

export interface FacetTypeCreate {
  name: string
  name_plural?: string
  slug?: string
  description?: string
  value_type: FacetValueType
  value_schema?: FacetTypeValueSchema | Record<string, unknown> | null
  icon?: string
  color?: string
  applicable_entity_type_slugs?: string[]
  is_active?: boolean
}

export type FacetTypeUpdate = Partial<FacetTypeCreate>

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
  value_type: FacetValueType
  value_schema: FacetTypeValueSchema
  icon: string
  color: string
  suggestions: string[]
}

// =============================================================================
// Facet Values
// =============================================================================

export type FacetSourceType =
  | 'MANUAL'
  | 'AI_EXTRACTED'
  | 'AI_ANALYZED'
  | 'IMPORTED'
  | 'API_SYNC'
  | 'DOCUMENT'

export interface FacetValue {
  id: string
  entity_id?: string
  entity_name?: string
  facet_type_id?: string
  facet_type_slug?: string
  facet_type_name?: string
  value?: Record<string, unknown> | string | number | boolean | null
  value_display?: string
  text_representation?: string
  effective_date?: string
  expiration_date?: string
  source_type?: FacetSourceType
  source_document_id?: string
  source_url?: string
  document_title?: string
  document_url?: string
  confidence_score?: number
  ai_model_used?: string
  human_verified?: boolean
  verified_by?: string
  verified_at?: string
  notes?: string
  created_at?: string
  updated_at?: string
  // Target entity reference (for linking to other entities like persons, organizations)
  target_entity_id?: string
  target_entity_name?: string
  target_entity_slug?: string
  target_entity_type_slug?: string
}

// Facet group for entity detail views (matches API response)
export interface FacetGroup {
  facet_type_id: string
  facet_type_slug: string
  facet_type_name: string
  value_type?: string
  // Alternative field names for backward compatibility
  facet_type_value_type?: string
  facet_type_icon?: string
  facet_type_color?: string
  icon?: string
  color?: string
  value_count?: number
  verified_count?: number
  value_schema?: Record<string, unknown>
  values?: FacetValue[]
  // sample_values contains partial FacetValue objects from API
  sample_values?: Record<string, unknown>[]
}

// Facets summary for entity overview (matches API response)
export interface FacetsSummary {
  facets_by_type?: FacetGroup[]
  total_count?: number
  total_facet_values?: number
  verified_count?: number
}

export interface FacetValueListParams extends PaginationParams {
  entity_id?: string
  facet_type_id?: string
  facet_type_slug?: string
  source_type?: FacetSourceType
  human_verified?: boolean
  min_confidence?: number
  search?: string
}

export interface FacetValueCreate {
  entity_id: string
  facet_type_id?: string
  facet_type_slug?: string
  value: unknown
  effective_date?: string
  expiration_date?: string
  source_type?: FacetSourceType
  source_document_id?: string
  source_url?: string | null
  confidence_score?: number
  notes?: string
  text_representation?: string
  target_entity_id?: string
}

export interface FacetValueUpdate {
  value?: unknown
  effective_date?: string
  expiration_date?: string
  source_type?: FacetSourceType
  source_url?: string
  notes?: string
  human_verified?: boolean
  target_entity_id?: string | null  // For linking to another entity
}

export interface FacetValueVerify {
  human_verified?: boolean
  verified?: boolean
  verified_by?: string
  notes?: string
}

export interface EntityFacetsSummary {
  entity_id: string
  entity_name: string
  facet_types: Array<{
    facet_type_id: string
    facet_type_slug: string
    facet_type_name: string
    value_type: FacetValueType
    values: FacetValue[]
    value_count: number
    latest_value?: unknown
    verified_count: number
  }>
  total_facets: number
  verified_facets: number
  ai_generated_facets: number
}

// =============================================================================
// Relation Types
// =============================================================================

export interface RelationType {
  id: string
  name: string
  name_inverse?: string | null
  name_reverse?: string
  slug?: string
  description?: string
  icon?: string
  color?: string | null
  source_entity_types?: string[]
  target_entity_types?: string[]
  is_symmetric?: boolean
  is_system?: boolean
  is_active?: boolean
  relation_count?: number
  created_at?: string
  updated_at?: string
}

export interface RelationTypeListParams extends PaginationParams {
  search?: string
  entity_type_slug?: string
  is_active?: boolean
  include_counts?: boolean
}

export interface RelationTypeCreate {
  name: string
  name_reverse?: string
  slug?: string
  description?: string
  icon?: string
  color?: string
  source_entity_type_slugs?: string[]
  target_entity_type_slugs?: string[]
  is_symmetric?: boolean
  is_active?: boolean
}

export type RelationTypeUpdate = Partial<RelationTypeCreate>

// =============================================================================
// Relations (Entity Connections)
// =============================================================================

export interface Relation {
  id: string
  relation_type_id: string
  relation_type_slug?: string
  relation_type_name: string
  source_entity_id: string
  source_entity_name: string
  source_entity_slug?: string
  source_entity_type_slug: string
  target_entity_id: string
  target_entity_name: string
  target_entity_slug?: string
  target_entity_type_slug: string
  attributes?: Record<string, unknown>
  effective_date?: string
  expiration_date?: string
  source_type?: FacetSourceType | string
  source_document_id?: string
  source_url?: string
  confidence_score?: number
  human_verified?: boolean
  verified_by?: string
  verified_at?: string
  notes?: string
  created_at?: string
  updated_at?: string
}

export interface RelationListParams extends PaginationParams {
  entity_id?: string
  relation_type_id?: string
  relation_type_slug?: string
  source_entity_id?: string
  target_entity_id?: string
  human_verified?: boolean
  min_confidence?: number
}

export interface RelationCreate {
  relation_type_id?: string
  relation_type_slug?: string
  source_entity_id: string
  target_entity_id: string
  attributes?: Record<string, unknown> | null
  effective_date?: string
  expiration_date?: string
  source_type?: FacetSourceType | string
  source_document_id?: string
  source_url?: string
  confidence_score?: number
  notes?: string
}

export interface RelationUpdate {
  relation_type_id?: string
  source_entity_id?: string
  target_entity_id?: string
  attributes?: Record<string, unknown> | null
  effective_date?: string
  expiration_date?: string
  source_url?: string
  notes?: string
  human_verified?: boolean
}

export interface RelationVerify {
  human_verified?: boolean
  verified?: boolean
  verified_by?: string
  notes?: string
}

export interface EntityRelationsGraph {
  entity_id: string
  entity_name: string
  nodes: Array<{
    id: string
    name: string
    entity_type_slug: string
    entity_type_name: string
    is_center: boolean
  }>
  edges: Array<{
    id: string
    source: string
    target: string
    relation_type_slug: string
    relation_type_name: string
    is_symmetric: boolean
  }>
}

// =============================================================================
// Analysis API Types
// =============================================================================

export interface AnalysisTemplate {
  id: string
  name: string
  slug: string
  description?: string
  template_type: 'REPORT' | 'COMPARISON' | 'TREND' | 'CUSTOM'
  entity_type_slug?: string
  config: AnalysisTemplateConfig
  is_system: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface AnalysisTemplateConfig {
  sections: AnalysisSection[]
  facet_types?: string[]
  comparison_fields?: string[]
  chart_types?: string[]
  filters?: Record<string, unknown>
}

export interface AnalysisSection {
  id: string
  title: string
  type: 'TEXT' | 'TABLE' | 'CHART' | 'STATS' | 'MAP'
  config: Record<string, unknown>
}

export interface AnalysisTemplateListParams extends PaginationParams {
  search?: string
  template_type?: string
  entity_type_slug?: string
  is_active?: boolean
}

export interface AnalysisTemplateCreate {
  name: string
  slug?: string
  description?: string
  template_type: 'REPORT' | 'COMPARISON' | 'TREND' | 'CUSTOM'
  entity_type_slug?: string
  config: AnalysisTemplateConfig
  is_active?: boolean
}

export type AnalysisTemplateUpdate = Partial<AnalysisTemplateCreate>

export interface AnalysisOverview {
  entity_type_slug: string
  total_entities: number
  entities_with_facets: number
  entities_with_relations: number
  facet_coverage: Record<string, number>
  top_locations: Array<{ location: string; count: number }>
  recent_activity: Array<{
    date: string
    created: number
    updated: number
  }>
}

export interface EntityReport {
  entity: Entity
  facets: EntityFacetsSummary
  relations: {
    outgoing: Relation[]
    incoming: Relation[]
    total: number
  }
  documents: Array<{
    id: string
    title: string
    url: string
    analyzed_at?: string
  }>
  sources: Array<{
    id: string
    name: string
    url: string
    status: string
  }>
  timeline: Array<{
    date: string
    event_type: string
    description: string
    entity_id?: string
  }>
  insights: Array<{
    type: string
    title: string
    message: string
    priority: number
  }>
}

export interface AnalysisStats {
  total_entities: number
  total_facet_types: number
  total_facet_values: number
  total_relations: number
  entities_by_type: Record<string, number>
  facets_by_type: Record<string, number>
  relations_by_type: Record<string, number>
  coverage_stats: {
    entities_with_facets_percent: number
    entities_with_relations_percent: number
    verified_facets_percent: number
  }
}

// =============================================================================
// Smart Query Types
// =============================================================================

export interface SmartQueryRequest {
  question: string
  allow_write?: boolean
}

export interface SmartWriteRequest {
  question: string
  preview_only?: boolean
  confirmed?: boolean
}

export interface SmartQueryResponse {
  success: boolean
  operation_type: 'READ' | 'WRITE' | 'ERROR'
  query_interpretation: string
  data?: unknown
  visualization?: SmartQueryVisualization
  explanation?: string
  suggested_actions?: SmartQueryAction[]
  warnings?: string[]
  error?: string
}

export interface SmartQueryVisualization {
  type: 'table' | 'bar_chart' | 'line_chart' | 'pie_chart' | 'stat_card' | 'text' | 'comparison' | 'map'
  title: string
  subtitle?: string
  config?: Record<string, unknown>
}

export interface SmartQueryAction {
  label: string
  action: string
  params: Record<string, unknown>
  icon?: string
}

export interface SmartQueryExample {
  category: string
  questions: Array<{
    text: string
    description: string
    tags: string[]
  }>
}

// =============================================================================
// Filter Options Types
// =============================================================================

export interface LocationFilterOptions {
  countries: Array<{ value: string; label: string; count: number }>
  admin_level_1: Array<{ value: string; label: string; country: string; count: number }>
  admin_level_2: Array<{ value: string; label: string; admin_level_1: string; count: number }>
}

export interface AttributeFilterOptions {
  attribute_key: string
  values: Array<{ value: string; label: string; count: number }>
}

// =============================================================================
// Document Types (for entity documents)
// =============================================================================

// Named EntityDocument to avoid conflict with DOM Document interface
export interface EntityDocument {
  id: string
  title?: string
  url?: string
  created_at?: string
  document_type?: string
  content_type?: string
  file_size?: number
  analyzed?: boolean
}

// =============================================================================
// Entity Note Types
// =============================================================================

export interface EntityNote {
  id: string
  content: string
  author?: string
  created_by?: string
  created_at: string
  updated_at?: string
}

// =============================================================================
// Simplified DataSource for entity linking
// =============================================================================

export interface DataSource {
  id: string
  name: string
  base_url?: string
  status?: string
  last_crawled_at?: string
}

// =============================================================================
// Re-export common types for convenience
// =============================================================================

export type { PaginationParams, PaginatedResponse } from './admin'
