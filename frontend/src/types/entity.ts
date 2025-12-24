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
  description?: string
  icon?: string
  color?: string
  schema?: EntityTypeSchema
  parent_type_id?: string
  parent_type_slug?: string
  applicable_facet_types?: string[]
  is_hierarchical: boolean
  entity_count: number
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
  type: 'string' | 'number' | 'boolean' | 'array' | 'object' | 'date'
  label?: string
  description?: string
  enum?: string[]
  format?: string
  default?: unknown
}

export interface EntityTypeListParams extends PaginationParams {
  search?: string
  is_hierarchical?: boolean
  is_active?: boolean
  include_counts?: boolean
}

export interface EntityTypeCreate {
  name: string
  name_plural?: string
  slug?: string
  description?: string
  icon?: string
  color?: string
  schema?: EntityTypeSchema
  parent_type_id?: string
  is_hierarchical?: boolean
  applicable_facet_types?: string[]
}

export interface EntityTypeUpdate extends Partial<EntityTypeCreate> {}

// =============================================================================
// Entity
// =============================================================================

export interface Entity {
  id: string
  entity_type_id: string
  entity_type_slug: string
  entity_type_name: string
  name: string
  slug: string
  description?: string
  location_name?: string
  country?: string
  admin_level_1?: string
  admin_level_2?: string
  latitude?: number
  longitude?: number
  attributes: Record<string, unknown>
  parent_id?: string
  parent_name?: string
  children_count: number
  facet_count: number
  relation_count: number
  document_count: number
  source_count: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface EntityBrief {
  id: string
  name: string
  slug: string
  entity_type_id: string
  entity_type_slug: string
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
}

export interface EntityUpdate extends Partial<EntityCreate> {}

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
  name_plural: string
  slug: string
  description?: string
  value_type: FacetValueType
  value_schema?: FacetTypeValueSchema
  icon?: string
  color?: string
  applicable_entity_types: string[]
  is_system: boolean
  is_active: boolean
  facet_count: number
  created_at: string
  updated_at: string
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
  include_counts?: boolean
}

export interface FacetTypeCreate {
  name: string
  name_plural?: string
  slug?: string
  description?: string
  value_type: FacetValueType
  value_schema?: FacetTypeValueSchema
  icon?: string
  color?: string
  applicable_entity_type_slugs?: string[]
  is_active?: boolean
}

export interface FacetTypeUpdate extends Partial<FacetTypeCreate> {}

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
  entity_id: string
  entity_name: string
  facet_type_id: string
  facet_type_slug: string
  facet_type_name: string
  value: unknown
  value_display?: string
  effective_date?: string
  expiration_date?: string
  source_type: FacetSourceType
  source_document_id?: string
  source_url?: string
  confidence_score: number
  ai_model_used?: string
  human_verified: boolean
  verified_by?: string
  verified_at?: string
  notes?: string
  created_at: string
  updated_at: string
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
}

export interface FacetValueUpdate {
  value?: unknown
  effective_date?: string
  expiration_date?: string
  source_type?: FacetSourceType
  source_url?: string
  notes?: string
  human_verified?: boolean
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
  name_reverse?: string
  slug: string
  description?: string
  icon?: string
  color?: string
  source_entity_types: string[]
  target_entity_types: string[]
  is_symmetric: boolean
  is_system: boolean
  is_active: boolean
  relation_count: number
  created_at: string
  updated_at: string
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

export interface RelationTypeUpdate extends Partial<RelationTypeCreate> {}

// =============================================================================
// Relations (Entity Connections)
// =============================================================================

export interface Relation {
  id: string
  relation_type_id: string
  relation_type_slug: string
  relation_type_name: string
  source_entity_id: string
  source_entity_name: string
  source_entity_type_slug: string
  target_entity_id: string
  target_entity_name: string
  target_entity_type_slug: string
  attributes?: Record<string, unknown>
  effective_date?: string
  expiration_date?: string
  source_type: FacetSourceType
  source_document_id?: string
  source_url?: string
  confidence_score: number
  human_verified: boolean
  verified_by?: string
  verified_at?: string
  notes?: string
  created_at: string
  updated_at: string
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

export interface AnalysisTemplateUpdate extends Partial<AnalysisTemplateCreate> {}

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
// Re-export common types for convenience
// =============================================================================

export type { PaginationParams, PaginatedResponse } from './admin'
