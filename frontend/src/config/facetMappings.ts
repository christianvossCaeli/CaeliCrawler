/**
 * Centralized Facet Mappings Configuration
 *
 * This file contains all severity, sentiment, and source type mappings
 * used across the facets system. Values are normalized to uppercase
 * constants to ensure consistency.
 */

// =============================================================================
// Severity Mappings
// =============================================================================

/**
 * Normalized severity levels used internally.
 * Backend may send German or English values - we normalize to these constants.
 */
export type SeverityLevel = 'HIGH' | 'MEDIUM' | 'LOW' | 'UNKNOWN'

/**
 * Maps raw severity values (German/English) to normalized constants.
 */
export const SEVERITY_NORMALIZE_MAP: Record<string, SeverityLevel> = {
  // German values
  hoch: 'HIGH',
  mittel: 'MEDIUM',
  niedrig: 'LOW',
  // English values
  high: 'HIGH',
  medium: 'MEDIUM',
  low: 'LOW',
  // Already normalized
  HIGH: 'HIGH',
  MEDIUM: 'MEDIUM',
  LOW: 'LOW',
}

/**
 * Vuetify color mappings for severity levels.
 */
export const SEVERITY_COLORS: Record<SeverityLevel, string> = {
  HIGH: 'error',
  MEDIUM: 'warning',
  LOW: 'success',
  UNKNOWN: 'grey',
}

/**
 * MDI icon mappings for severity levels.
 */
export const SEVERITY_ICONS: Record<SeverityLevel, string> = {
  HIGH: 'mdi-alert',
  MEDIUM: 'mdi-alert-circle-outline',
  LOW: 'mdi-information-outline',
  UNKNOWN: 'mdi-minus',
}

/**
 * Normalize a severity value from backend to internal constant.
 */
export function normalizeSeverity(value: string | null | undefined): SeverityLevel {
  if (!value) return 'UNKNOWN'
  return SEVERITY_NORMALIZE_MAP[value.toLowerCase()] || 'UNKNOWN'
}

/**
 * Get color for a severity value (handles both raw and normalized).
 */
export function getSeverityColor(severity: string | null | undefined): string {
  const normalized = normalizeSeverity(severity)
  return SEVERITY_COLORS[normalized]
}

/**
 * Get icon for a severity value (handles both raw and normalized).
 */
export function getSeverityIcon(severity: string | null | undefined): string {
  const normalized = normalizeSeverity(severity)
  return SEVERITY_ICONS[normalized]
}

// =============================================================================
// Sentiment Mappings
// =============================================================================

/**
 * Normalized sentiment levels used internally.
 */
export type SentimentLevel = 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL' | 'UNKNOWN'

/**
 * Maps raw sentiment values (German/English) to normalized constants.
 */
export const SENTIMENT_NORMALIZE_MAP: Record<string, SentimentLevel> = {
  // German values
  positiv: 'POSITIVE',
  negativ: 'NEGATIVE',
  // English values
  positive: 'POSITIVE',
  negative: 'NEGATIVE',
  neutral: 'NEUTRAL',
  // Already normalized
  POSITIVE: 'POSITIVE',
  NEGATIVE: 'NEGATIVE',
  NEUTRAL: 'NEUTRAL',
}

/**
 * Vuetify color mappings for sentiment levels.
 */
export const SENTIMENT_COLORS: Record<SentimentLevel, string> = {
  POSITIVE: 'success',
  NEGATIVE: 'error',
  NEUTRAL: 'grey',
  UNKNOWN: 'grey',
}

/**
 * MDI icon mappings for sentiment levels.
 */
export const SENTIMENT_ICONS: Record<SentimentLevel, string> = {
  POSITIVE: 'mdi-emoticon-happy-outline',
  NEGATIVE: 'mdi-emoticon-sad-outline',
  NEUTRAL: 'mdi-emoticon-neutral-outline',
  UNKNOWN: 'mdi-emoticon-outline',
}

/**
 * Normalize a sentiment value from backend to internal constant.
 */
export function normalizeSentiment(value: string | null | undefined): SentimentLevel {
  if (!value) return 'UNKNOWN'
  return SENTIMENT_NORMALIZE_MAP[value.toLowerCase()] || 'UNKNOWN'
}

/**
 * Get color for a sentiment value (handles both raw and normalized).
 */
export function getSentimentColor(sentiment: string | null | undefined): string {
  const normalized = normalizeSentiment(sentiment)
  return SENTIMENT_COLORS[normalized]
}

/**
 * Get icon for a sentiment value (handles both raw and normalized).
 */
export function getSentimentIcon(sentiment: string | null | undefined): string {
  const normalized = normalizeSentiment(sentiment)
  return SENTIMENT_ICONS[normalized]
}

// =============================================================================
// Source Type Mappings
// =============================================================================

/**
 * Facet value source types.
 */
export type FacetSourceType =
  | 'DOCUMENT'
  | 'MANUAL'
  | 'PYSIS'
  | 'SMART_QUERY'
  | 'AI_ASSISTANT'
  | 'IMPORT'
  | 'ATTACHMENT'

/**
 * Vuetify color mappings for source types.
 */
export const SOURCE_TYPE_COLORS: Record<string, string> = {
  document: 'blue',
  manual: 'purple',
  pysis: 'deep-purple',
  smart_query: 'green',
  ai_assistant: 'indigo',
  import: 'teal',
  attachment: 'orange',
}

/**
 * MDI icon mappings for source types.
 */
export const SOURCE_TYPE_ICONS: Record<string, string> = {
  document: 'mdi-file-document',
  manual: 'mdi-hand-pointing-right',
  pysis: 'mdi-database-cog',
  smart_query: 'mdi-code-tags',
  ai_assistant: 'mdi-robot',
  import: 'mdi-import',
  attachment: 'mdi-paperclip',
}

/**
 * Normalize source type for lookup.
 */
function normalizeSourceType(sourceType: string | null | undefined): string {
  return (sourceType || 'document').toLowerCase()
}

/**
 * Get color for a source type.
 */
export function getSourceTypeColor(sourceType: string | null | undefined): string {
  return SOURCE_TYPE_COLORS[normalizeSourceType(sourceType)] || 'grey'
}

/**
 * Get icon for a source type.
 */
export function getSourceTypeIcon(sourceType: string | null | undefined): string {
  return SOURCE_TYPE_ICONS[normalizeSourceType(sourceType)] || 'mdi-file-document'
}

// =============================================================================
// Confidence Score Mappings
// =============================================================================

/**
 * Confidence score thresholds.
 */
export const CONFIDENCE_THRESHOLDS = {
  HIGH: 0.8,
  MEDIUM: 0.5,
} as const

/**
 * Get color for a confidence score.
 */
export function getConfidenceColor(score: number | null | undefined): string {
  if (!score) return 'grey'
  if (score >= CONFIDENCE_THRESHOLDS.HIGH) return 'success'
  if (score >= CONFIDENCE_THRESHOLDS.MEDIUM) return 'warning'
  return 'error'
}

// =============================================================================
// Default FacetType Configurations
// =============================================================================

/**
 * Default icons for facet types by slug.
 */
export const DEFAULT_FACET_TYPE_ICONS: Record<string, string> = {
  pain_point: 'mdi-alert-circle',
  positive_signal: 'mdi-lightbulb-on',
  contact: 'mdi-account',
  summary: 'mdi-text-box',
}

/**
 * Default colors for facet types by slug.
 */
export const DEFAULT_FACET_TYPE_COLORS: Record<string, string> = {
  pain_point: '#F44336',
  positive_signal: '#4CAF50',
  contact: '#2196F3',
  summary: '#9E9E9E',
}

/**
 * Get default icon for a facet type.
 */
export function getDefaultFacetTypeIcon(slug: string): string {
  return DEFAULT_FACET_TYPE_ICONS[slug] || 'mdi-tag'
}

/**
 * Get default color for a facet type.
 */
export function getDefaultFacetTypeColor(slug: string): string {
  return DEFAULT_FACET_TYPE_COLORS[slug] || '#757575'
}
