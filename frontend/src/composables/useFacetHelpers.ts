/**
 * Facet value display helpers - extracted from EntityDetailView.vue.
 *
 * Provides formatting and display utilities for different facet types:
 * - Pain Points (structured with severity, type, quote)
 * - Positive Signals (structured with type, quote)
 * - Contacts (structured with name, role, email, phone, sentiment)
 * - Generic text facets
 */

import { formatNumber } from '@/utils/viewHelpers'

export interface FacetValue {
  id?: string
  text_representation?: string
  value: Record<string, unknown>
  confidence_score?: number
  human_verified?: boolean
  source_url?: string
  event_date?: string
}

// Attribute translations for entity display
export const attributeTranslations: Record<string, string> = {
  country: 'Land',
  state: 'Bundesland',
  county: 'Landkreis',
  population: 'Einwohner',
  area_km2: 'Flaeche (km2)',
  academic_title: 'Titel',
  first_name: 'Vorname',
  last_name: 'Nachname',
  email: 'E-Mail',
  phone: 'Telefon',
  role: 'Position',
  org_type: 'Organisationstyp',
  address: 'Adresse',
  event_date: 'Startdatum',
  event_end_date: 'Enddatum',
  location: 'Ort',
  organizer: 'Veranstalter',
  event_type: 'Veranstaltungstyp',
  description: 'Beschreibung',
}

export function useFacetHelpers() {
  /**
   * Format attribute key for display
   */
  function formatAttributeKey(key: string, schema?: { properties?: Record<string, { title?: string }> }): string {
    // First try to get title from entity type's attribute_schema
    if (schema?.properties?.[key]?.title) {
      return schema.properties[key].title
    }
    // Then try the translation map
    if (attributeTranslations[key]) {
      return attributeTranslations[key]
    }
    // Finally, fallback to basic formatting
    return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  /**
   * Format attribute value for display
   */
  function formatAttributeValue(value: unknown): string {
    if (typeof value === 'number') {
      return formatNumber(value)
    }
    return String(value)
  }

  /**
   * Format facet value for display (generic)
   */
  function formatFacetValue(facet: FacetValue): string {
    if (facet.text_representation) return facet.text_representation
    if (typeof facet.value === 'string') return facet.value
    if (typeof facet.value?.text === 'string') return facet.value.text
    return JSON.stringify(facet.value)
  }

  /**
   * Get confidence score color
   */
  function getConfidenceColor(score: number | null | undefined): string {
    if (!score) return 'grey'
    if (score >= 0.8) return 'success'
    if (score >= 0.5) return 'warning'
    return 'error'
  }

  // --- Structured Facet Value Helpers ---

  /**
   * Get description from structured facet (pain_point, positive_signal)
   */
  function getStructuredDescription(facet: FacetValue): string {
    if (facet.text_representation) return facet.text_representation
    const val = facet.value
    if (!val) return ''
    if (typeof val === 'string') return val
    const desc = val.description ?? val.text ?? val.concern ?? val.opportunity
    return typeof desc === 'string' ? desc : ''
  }

  /**
   * Get type from structured facet
   */
  function getStructuredType(facet: FacetValue): string | null {
    const val = facet.value
    if (!val || typeof val === 'string') return null
    return typeof val.type === 'string' ? val.type : null
  }

  /**
   * Get severity from structured facet (pain_point)
   */
  function getStructuredSeverity(facet: FacetValue): string | null {
    const val = facet.value
    if (!val || typeof val === 'string') return null
    return typeof val.severity === 'string' ? val.severity : null
  }

  /**
   * Get quote from structured facet
   */
  function getStructuredQuote(facet: FacetValue): string | null {
    const val = facet.value
    if (!val || typeof val === 'string') return null
    return typeof val.quote === 'string' ? val.quote : null
  }

  /**
   * Get severity color
   */
  function getSeverityColor(severity: string | null): string {
    if (!severity) return 'grey'
    const s = severity.toLowerCase()
    if (s === 'hoch' || s === 'high') return 'error'
    if (s === 'mittel' || s === 'medium') return 'warning'
    if (s === 'niedrig' || s === 'low') return 'success'
    return 'grey'
  }

  /**
   * Get severity icon
   */
  function getSeverityIcon(severity: string | null): string {
    if (!severity) return 'mdi-minus'
    const s = severity.toLowerCase()
    if (s === 'hoch' || s === 'high') return 'mdi-alert'
    if (s === 'mittel' || s === 'medium') return 'mdi-alert-circle-outline'
    if (s === 'niedrig' || s === 'low') return 'mdi-information-outline'
    return 'mdi-minus'
  }

  // --- Contact Helpers ---

  /**
   * Get contact name
   */
  function getContactName(facet: FacetValue): string {
    if (facet.text_representation) return facet.text_representation
    const val = facet.value
    if (!val) return ''
    if (typeof val === 'string') return val
    return typeof val.name === 'string' ? val.name : ''
  }

  /**
   * Get contact role/position
   */
  function getContactRole(facet: FacetValue): string | null {
    const val = facet.value
    if (!val || typeof val === 'string') return null
    const role = val.role ?? val.position
    return typeof role === 'string' ? role : null
  }

  /**
   * Get contact email
   */
  function getContactEmail(facet: FacetValue): string | null {
    const val = facet.value
    if (!val || typeof val === 'string') return null
    return typeof val.email === 'string' ? val.email : null
  }

  /**
   * Get contact phone
   */
  function getContactPhone(facet: FacetValue): string | null {
    const val = facet.value
    if (!val || typeof val === 'string') return null
    const phone = val.phone ?? val.telefon
    return typeof phone === 'string' ? phone : null
  }

  /**
   * Get contact sentiment
   */
  function getContactSentiment(facet: FacetValue): string | null {
    const val = facet.value
    if (!val || typeof val === 'string') return null
    return typeof val.sentiment === 'string' ? val.sentiment : null
  }

  /**
   * Get contact statement/quote
   */
  function getContactStatement(facet: FacetValue): string | null {
    const val = facet.value
    if (!val || typeof val === 'string') return null
    const stmt = val.statement ?? val.quote
    return typeof stmt === 'string' ? stmt : null
  }

  /**
   * Get sentiment color
   */
  function getSentimentColor(sentiment: string | null): string {
    if (!sentiment) return 'grey'
    const s = sentiment.toLowerCase()
    if (s === 'positiv' || s === 'positive') return 'success'
    if (s === 'negativ' || s === 'negative') return 'error'
    return 'grey'
  }

  // --- Source Status Helpers ---

  /**
   * Get data source status color
   */
  function getSourceStatusColor(status: string): string {
    const colors: Record<string, string> = {
      ACTIVE: 'success',
      INACTIVE: 'grey',
      ERROR: 'error',
      PENDING: 'warning',
    }
    return colors[status] || 'grey'
  }

  /**
   * Get data source status icon
   */
  function getSourceStatusIcon(status: string): string {
    const icons: Record<string, string> = {
      ACTIVE: 'mdi-check-circle',
      INACTIVE: 'mdi-pause-circle',
      ERROR: 'mdi-alert-circle',
      PENDING: 'mdi-clock',
    }
    return icons[status] || 'mdi-help-circle'
  }

  /**
   * Copy text to clipboard
   */
  function copyToClipboard(text: string): void {
    navigator.clipboard.writeText(text)
  }

  return {
    // Attribute helpers
    formatAttributeKey,
    formatAttributeValue,

    // Generic facet helpers
    formatFacetValue,
    getConfidenceColor,

    // Structured facet helpers
    getStructuredDescription,
    getStructuredType,
    getStructuredSeverity,
    getStructuredQuote,
    getSeverityColor,
    getSeverityIcon,

    // Contact helpers
    getContactName,
    getContactRole,
    getContactEmail,
    getContactPhone,
    getContactSentiment,
    getContactStatement,
    getSentimentColor,

    // Source helpers
    getSourceStatusColor,
    getSourceStatusIcon,

    // Utility
    copyToClipboard,
  }
}
