/**
 * Results Helpers Composable
 *
 * Pure helper functions for formatting, colors, and content extraction.
 * No side effects, no state - just utility functions.
 */

import { useI18n } from 'vue-i18n'
import { useDateFormatter } from '@/composables/useDateFormatter'
import { useFacetTypeRenderer } from '@/composables/useFacetTypeRenderer'
import {
  CONFIDENCE_THRESHOLDS,
  CONFIDENCE_COLORS,
  SEVERITY_COLORS,
  SEVERITY_ICONS,
  PRIORITY_COLORS,
  SENTIMENT_COLORS,
  ENTITY_TYPE_CONFIG,
  DEFAULT_ENTITY_CONFIG,
  RESERVED_CONTENT_FIELDS,
  CHIP_DISPLAY_FIELDS,
  FIELD_ICONS,
  FIELD_COLORS,
  DEFAULT_FIELD_ICON,
  DEFAULT_FIELD_COLOR,
} from './constants'
import type {
  SearchResult,
  ExtractedContent,
  EntityReference,
  DynamicContentField,
} from './types'

export function useResultsHelpers() {
  const { t } = useI18n()
  const { formatDate: formatLocaleDate } = useDateFormatter()
  const { normalizeValue, getPrimaryValue } = useFacetTypeRenderer()

  // ===========================================================================
  // Confidence Helpers
  // ===========================================================================

  /**
   * Get color based on confidence score.
   */
  function getConfidenceColor(score?: number | null): string {
    if (score == null) return CONFIDENCE_COLORS.UNKNOWN
    if (score >= CONFIDENCE_THRESHOLDS.HIGH) return CONFIDENCE_COLORS.HIGH
    if (score >= CONFIDENCE_THRESHOLDS.MEDIUM) return CONFIDENCE_COLORS.MEDIUM
    return CONFIDENCE_COLORS.LOW
  }

  /**
   * Format confidence score as percentage string.
   */
  function formatConfidence(score?: number | null): string {
    if (score == null) return '-'
    return `${(score * 100).toFixed(0)}%`
  }

  // ===========================================================================
  // Severity & Priority Helpers
  // ===========================================================================

  function getSeverityColor(severity?: string): string {
    if (!severity) return 'grey'
    return SEVERITY_COLORS[severity.toLowerCase()] || 'grey'
  }

  function getSeverityIcon(severity: string): string {
    const key = severity.toLowerCase()
    return SEVERITY_ICONS[key] || 'mdi-minus'
  }

  function getPriorityColor(priority: string): string {
    return PRIORITY_COLORS[priority.toLowerCase()] || 'grey'
  }

  function getSentimentColor(sentiment: string): string {
    if (!sentiment) return 'grey'
    return SENTIMENT_COLORS[sentiment.toLowerCase()] || 'grey'
  }

  // ===========================================================================
  // Entity Type Helpers
  // ===========================================================================

  function getEntityTypeColor(entityType: string): string {
    return ENTITY_TYPE_CONFIG[entityType]?.color || DEFAULT_ENTITY_CONFIG.color
  }

  function getEntityTypeIcon(entityType: string): string {
    return ENTITY_TYPE_CONFIG[entityType]?.icon || DEFAULT_ENTITY_CONFIG.icon
  }

  // ===========================================================================
  // Content Extraction Helpers
  // ===========================================================================

  /**
   * Get the final content from a search result (prefers final_content over extracted_content).
   */
  function getContent(item: SearchResult): ExtractedContent {
    return item.final_content || item.extracted_content || {}
  }

  /**
   * Get entity references filtered by type.
   */
  function getEntityReferencesByType(item: SearchResult, entityType: string): EntityReference[] {
    if (!item.entity_references || !Array.isArray(item.entity_references)) {
      return []
    }
    return item.entity_references.filter((ref) => ref.entity_type === entityType)
  }

  /**
   * Get the primary entity reference (role='primary').
   */
  function getPrimaryEntityRef(item: SearchResult): EntityReference | null {
    if (!item.entity_references || !Array.isArray(item.entity_references)) {
      return null
    }
    return item.entity_references.find((ref) => ref.role === 'primary') || null
  }

  // ===========================================================================
  // Date Formatting
  // ===========================================================================

  function formatDate(dateStr: string): string {
    if (!dateStr) return '-'
    return formatLocaleDate(dateStr, 'dd.MM.yy HH:mm') || '-'
  }

  function formatDateShort(dateStr: string): string {
    if (!dateStr) return '-'
    return formatLocaleDate(dateStr, 'dd.MM.yy') || '-'
  }

  // ===========================================================================
  // Dynamic Content Field Helpers
  // ===========================================================================

  /**
   * Format a field key to a human-readable label.
   * e.g., "pain_points" → "Pain Points"
   */
  function formatFieldLabel(key: string): string {
    return key
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  /**
   * Get icon for a dynamic field based on its name.
   */
  function getFieldIcon(key: string): string {
    return FIELD_ICONS[key] || DEFAULT_FIELD_ICON
  }

  /**
   * Get color for a dynamic field based on its name.
   */
  function getFieldColor(key: string): string {
    return FIELD_COLORS[key] || DEFAULT_FIELD_COLOR
  }

  /**
   * Extract all dynamic array/object fields from extracted_content.
   */
  function getDynamicContentFields(content: ExtractedContent): DynamicContentField[] {
    if (!content || typeof content !== 'object') return []

    const dynamicFields: DynamicContentField[] = []

    for (const [key, value] of Object.entries(content)) {
      // Skip reserved fields
      if (RESERVED_CONTENT_FIELDS.has(key)) continue

      // Skip null/undefined values
      if (value === null || value === undefined) continue

      // Determine display type based on field semantics
      const displayType = CHIP_DISPLAY_FIELDS.has(key) ? 'chips' : 'list'

      // Handle arrays
      if (Array.isArray(value) && value.length > 0) {
        dynamicFields.push({
          key,
          label: formatFieldLabel(key),
          values: value,
          icon: getFieldIcon(key),
          color: getFieldColor(key),
          displayType,
        })
      }
      // Handle single objects
      else if (typeof value === 'object' && Object.keys(value).length > 0) {
        const hasContent = Object.values(value).some(
          (v) => v !== null && v !== undefined && v !== ''
        )
        if (hasContent) {
          dynamicFields.push({
            key,
            label: formatFieldLabel(key),
            values: [value],
            icon: getFieldIcon(key),
            color: getFieldColor(key),
            displayType,
          })
        }
      }
      // Handle non-empty strings
      else if (typeof value === 'string' && value.trim().length > 0 && key !== 'summary') {
        dynamicFields.push({
          key,
          label: formatFieldLabel(key),
          values: [{ text: value }],
          icon: getFieldIcon(key),
          color: getFieldColor(key),
          displayType: 'list',
        })
      }
    }

    return dynamicFields
  }

  /**
   * Get the primary display text from a dynamic field value.
   */
  function getValueText(value: unknown): string {
    if (typeof value === 'string') return value
    if (typeof value === 'boolean') return value ? t('common.yes') : t('common.no')
    if (typeof value === 'number') return String(value)
    if (value && typeof value === 'object') {
      const normalized = normalizeValue(value)
      const defaultConfig = {
        primaryField: 'description',
        chipFields: [],
        severityColors: {},
        layout: 'card' as const,
        labels: {},
      }
      return getPrimaryValue(normalized, defaultConfig)
    }
    return ''
  }

  // ===========================================================================
  // Return
  // ===========================================================================

  return {
    // Confidence
    getConfidenceColor,
    formatConfidence,

    // Severity & Priority
    getSeverityColor,
    getSeverityIcon,
    getPriorityColor,
    getSentimentColor,

    // Entity Types
    getEntityTypeColor,
    getEntityTypeIcon,

    // Content Extraction
    getContent,
    getEntityReferencesByType,
    getPrimaryEntityRef,

    // Date Formatting
    formatDate,
    formatDateShort,

    // Dynamic Content
    formatFieldLabel,
    getFieldIcon,
    getFieldColor,
    getDynamicContentFields,
    getValueText,
  }
}
