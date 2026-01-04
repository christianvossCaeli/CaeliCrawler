/**
 * Results Module Constants
 *
 * Centralized configuration for the Results/Extracted Data module.
 * Eliminates magic numbers and provides consistent theming.
 */

// =============================================================================
// Confidence Thresholds
// =============================================================================

export const CONFIDENCE_THRESHOLDS = {
  HIGH: 0.8,
  MEDIUM: 0.6,
  LOW: 0.5,
} as const

export const CONFIDENCE_COLORS = {
  HIGH: 'success',
  MEDIUM: 'warning',
  LOW: 'error',
  UNKNOWN: 'grey',
} as const

// =============================================================================
// Severity/Priority Configuration
// =============================================================================

export const SEVERITY_COLORS: Record<string, string> = {
  hoch: 'error',
  high: 'error',
  mittel: 'warning',
  medium: 'warning',
  niedrig: 'info',
  low: 'info',
}

export const SEVERITY_ICONS: Record<string, string> = {
  hoch: 'mdi-alert',
  high: 'mdi-alert',
  mittel: 'mdi-alert-circle-outline',
  medium: 'mdi-alert-circle-outline',
  niedrig: 'mdi-information-outline',
  low: 'mdi-information-outline',
}

export const PRIORITY_COLORS = SEVERITY_COLORS

export const SENTIMENT_COLORS: Record<string, string> = {
  positiv: 'success',
  positive: 'success',
  negativ: 'error',
  negative: 'error',
  neutral: 'grey',
}

// =============================================================================
// Entity Type Configuration
// =============================================================================

export const ENTITY_TYPE_CONFIG: Record<string, { color: string; icon: string }> = {
  'territorial-entity': { color: 'primary', icon: 'mdi-map-marker' },
  'person': { color: 'info', icon: 'mdi-account' },
  'organization': { color: 'secondary', icon: 'mdi-domain' },
  'event': { color: 'warning', icon: 'mdi-calendar' },
}

export const DEFAULT_ENTITY_CONFIG = { color: 'grey', icon: 'mdi-tag' }

// =============================================================================
// Dynamic Field Configuration
// =============================================================================

export const RESERVED_CONTENT_FIELDS = new Set([
  'is_relevant',
  'relevanz',
  'summary',
  'outreach_recommendation',
  'municipality',
])

export const CHIP_DISPLAY_FIELDS = new Set([
  'decision_makers',
  'contacts',
  'entscheider',
  'ansprechpartner',
])

export const FIELD_ICONS: Record<string, string> = {
  pain_points: 'mdi-alert-circle',
  positive_signals: 'mdi-lightbulb-on',
  decision_makers: 'mdi-account-group',
  contacts: 'mdi-account',
  flaechenausweisung: 'mdi-map-marker-radius',
  windenergie: 'mdi-wind-turbine',
  solar: 'mdi-solar-panel',
  timeline: 'mdi-timeline-clock',
  events: 'mdi-calendar-star',
  documents: 'mdi-file-document-multiple',
}

export const FIELD_COLORS: Record<string, string> = {
  pain_points: 'warning',
  positive_signals: 'success',
  decision_makers: 'info',
  contacts: 'primary',
}

export const DEFAULT_FIELD_ICON = 'mdi-tag'
export const DEFAULT_FIELD_COLOR = 'blue-grey'

// =============================================================================
// Pagination Defaults
// =============================================================================

export const RESULTS_PAGINATION = {
  DEFAULT_PAGE: 1,
  DEFAULT_PER_PAGE: 20,
  DEFAULT_SORT_BY: 'created_at',
  DEFAULT_SORT_ORDER: 'desc' as const,
}

// =============================================================================
// Export Configuration
// =============================================================================

export const EXPORT_CONFIG = {
  JSON_INDENT: 2,
  CSV_MAX_SUMMARY_LENGTH: 200,
  CSV_DATE_FORMAT: 'yyyy-MM-dd',
}
