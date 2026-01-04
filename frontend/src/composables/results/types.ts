/**
 * Results Module Types
 *
 * Centralized type definitions for the Results/Extracted Data module.
 */

// =============================================================================
// Entity References
// =============================================================================

export interface EntityReference {
  entity_id: string | null
  entity_name: string
  entity_type: string
  relevance_score?: number
  role?: 'primary' | 'secondary' | 'decision_maker' | string
  confidence?: number
}

// =============================================================================
// Signal & Decision Maker Types
// =============================================================================

export interface SignalItem {
  description?: string
  text?: string
  concern?: string
  type?: string
  severity?: string
  quote?: string
  source?: string
  source_url?: string
  opportunity?: string
}

export interface DecisionMaker {
  name?: string
  person?: string
  role?: string
  position?: string
  department?: string
  contact?: string
  email?: string
  phone?: string
  telefon?: string
  sentiment?: string
  statement?: string
  quote?: string
  source?: string
  source_url?: string
  influence_level?: string
}

export interface OutreachRecommendation {
  priority?: string
  reason?: string
}

// =============================================================================
// Extracted Content
// =============================================================================

export interface ExtractedContent {
  is_relevant?: boolean
  relevanz?: string
  summary?: string
  municipality?: string
  pain_points?: (string | SignalItem)[]
  positive_signals?: (string | SignalItem)[]
  decision_makers?: DecisionMaker[]
  outreach_recommendation?: OutreachRecommendation
  [key: string]: unknown
}

// =============================================================================
// Search Result
// =============================================================================

export interface SearchResult {
  id: string
  document_id?: string
  document_title?: string
  document_url?: string
  content?: string
  extraction_type?: string
  entity_references?: EntityReference[]
  confidence_score?: number
  human_verified?: boolean
  verified_by?: string
  verified_at?: string
  created_at: string
  updated_at?: string
  source_name?: string
  final_content?: ExtractedContent
  extracted_content?: ExtractedContent
  raw?: SearchResult
  ai_model_used?: string
  tokens_used?: number
}

/**
 * Normalizes a search result item, handling the raw wrapper from v-data-table.
 * Use this to avoid repetitive `item.raw?.field || item.field` patterns.
 */
export function normalizeResultItem(item: SearchResult | { raw?: SearchResult }): SearchResult {
  if ('raw' in item && item.raw) {
    return item.raw
  }
  return item as SearchResult
}

// =============================================================================
// Table Types
// =============================================================================

export interface TableHeader {
  title: string
  key: string
  sortable?: boolean
  align?: 'start' | 'center' | 'end'
  width?: string
}

export interface TableOptions {
  page: number
  itemsPerPage: number
  sortBy?: Array<{ key: string; order: 'asc' | 'desc' }>
}

export type SortOrder = 'asc' | 'desc'

export interface SortConfig {
  key: string
  order: SortOrder
}

// =============================================================================
// Statistics
// =============================================================================

export interface ResultsStats {
  total: number
  verified: number
  unverified: number
  avg_confidence: number | null
  high_confidence_count: number
  low_confidence_count: number
  by_type?: Record<string, number>
}

// =============================================================================
// Filter State
// =============================================================================

export interface ResultsFilterState {
  searchQuery: string
  locationFilter: string | null
  extractionTypeFilter: string | null
  categoryFilter: string | null
  minConfidence: number
  verifiedFilter: boolean | null
  dateFrom: string | null
  dateTo: string | null
}

// =============================================================================
// Dynamic Content Fields
// =============================================================================

export interface DynamicContentField {
  key: string
  label: string
  values: unknown[]
  icon: string
  color: string
  displayType: 'chips' | 'list'
}

// =============================================================================
// Category & Filter Options
// =============================================================================

export interface CategoryOption {
  id: string
  name: string
}
