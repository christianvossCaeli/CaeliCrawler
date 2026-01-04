/**
 * Facets Composable Types
 *
 * Shared types for facet-related composables.
 */

import type { FacetGroup, FacetValue } from '@/types/entity'

// Re-export for convenience
export type { FacetGroup, FacetValue }

// Alias for backward compatibility
export type FacetDetail = FacetValue

export interface NewFacet {
  facet_type_id: string
  text_representation: string
  source_url: string
  confidence_score: number
  value: Record<string, unknown>
  target_entity_id: string | null
}

export interface FacetSchemaProperty {
  type?: string
  title?: string
  description?: string
  enum?: string[]
  format?: string
  items?: { type: string; enum?: string[] }
  minimum?: number
  maximum?: number
}

export interface FacetSchema {
  type?: string
  properties?: Record<string, FacetSchemaProperty>
  required?: string[]
}

export interface EnrichmentSources {
  pysis: { available: boolean; count: number; last_updated: string | null }
  relations: { available: boolean; count: number; last_updated: string | null }
  documents: { available: boolean; count: number; last_updated: string | null }
  extractions: { available: boolean; count: number; last_updated: string | null }
  attachments: { available: boolean; count: number; last_updated: string | null }
  existing_facets: number
}

export interface EntitySearchResult {
  id: string
  name: string
  entity_type_name: string
  entity_type_icon?: string
  entity_type_color?: string
}

// Compatible type for SourceDetailsDialog
export interface SourceFacet {
  source_type: string
  source_url?: string | null
  document_title?: string | null
  document_url?: string | null
  verified_by?: string | null
  ai_model_used?: string | null
  confidence_score?: number | null
  created_at?: string | null
  verified_at?: string | null
  human_verified?: boolean
  value?: Record<string, unknown> | null
}
