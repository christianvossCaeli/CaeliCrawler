/**
 * Composable for generic FacetType rendering.
 *
 * Provides utilities for:
 * - Extracting display configuration from FacetType.value_schema
 * - Mapping FacetType slugs to extracted_content field names
 * - Extracting values from extracted_content for a given FacetType
 */

import type { FacetType, FacetDisplayConfig, FacetTypeValueSchema, FacetGroup } from '@/types/entity'
import {
  SEVERITY_NORMALIZE_MAP,
  SEVERITY_COLORS,
  type SeverityLevel,
  getDefaultFacetTypeIcon,
  getDefaultFacetTypeColor,
} from '@/config/facetMappings'

/**
 * Resolved display configuration with defaults applied
 */
export interface ResolvedDisplayConfig {
  primaryField: string
  chipFields: string[]
  quoteField?: string
  severityField?: string
  severityColors: Record<string, string>
  layout: 'card' | 'inline' | 'list'
}

/**
 * Chip data for rendering
 */
export interface ChipData {
  field: string
  value: string
  color: string
}

/**
 * Build severity color map from centralized config (handles both German and English keys)
 */
const DEFAULT_SEVERITY_COLORS: Record<string, string> = Object.entries(SEVERITY_NORMALIZE_MAP).reduce(
  (acc, [key, normalized]) => {
    acc[key] = SEVERITY_COLORS[normalized as SeverityLevel]
    return acc
  },
  {} as Record<string, string>,
)

/**
 * Mapping from FacetType slug to extracted_content field name
 * Convention: slug is singular, field is plural (with exceptions)
 */
const SLUG_TO_FIELD_MAPPING: Record<string, string> = {
  pain_point: 'pain_points',
  positive_signal: 'positive_signals',
  contact: 'decision_makers',
  summary: 'summary',
}

export function useFacetTypeRenderer() {
  /**
   * Extract display configuration from FacetType.value_schema
   * with sensible defaults applied
   */
  function getDisplayConfig(facetType: FacetType): ResolvedDisplayConfig {
    const schema = facetType.value_schema as FacetTypeValueSchema | null
    const display = schema?.display as FacetDisplayConfig | undefined

    return {
      primaryField: display?.primary_field || 'description',
      chipFields: display?.chip_fields || [],
      quoteField: display?.quote_field,
      severityField: display?.severity_field,
      severityColors: {
        ...DEFAULT_SEVERITY_COLORS,
        ...(display?.severity_colors || {}),
      },
      layout: display?.layout || 'card',
    }
  }

  /**
   * Map FacetType slug to the corresponding extracted_content field name
   */
  function getFieldNameForFacetType(slug: string): string {
    // Check explicit mapping first
    if (SLUG_TO_FIELD_MAPPING[slug]) {
      return SLUG_TO_FIELD_MAPPING[slug]
    }

    // Default: pluralize by adding 's'
    return `${slug}s`
  }

  /**
   * Extract values from extracted_content for a given FacetType
   */
  function getValuesForFacetType(
    content: Record<string, unknown>,
    facetType: FacetType
  ): unknown[] {
    const fieldName = getFieldNameForFacetType(facetType.slug)
    const values = content[fieldName]

    if (Array.isArray(values)) {
      return values
    }

    // Handle single value case (e.g., summary)
    if (values && typeof values === 'object') {
      return [values]
    }

    if (values && typeof values === 'string') {
      return [{ text: values, description: values }]
    }

    return []
  }

  /**
   * Normalize a value to a consistent object format
   */
  function normalizeValue(value: unknown): Record<string, unknown> {
    if (typeof value === 'string') {
      return { description: value, text: value }
    }
    if (typeof value === 'object' && value !== null) {
      return value as Record<string, unknown>
    }
    return {}
  }

  /**
   * Get the primary display value from a facet value
   */
  function getPrimaryValue(
    value: Record<string, unknown>,
    config: ResolvedDisplayConfig
  ): string {
    // Try primary field first
    const primary = value[config.primaryField]
    if (primary && typeof primary === 'string') {
      return primary
    }

    // Fallback to common field names (extended list for various data structures)
    const fallbacks = [
      'description', 'text', 'name', 'title', 'content',
      // German field names commonly used
      'beschreibung', 'aenderungen', 'bezeichnung',
      // Boolean/simple value wrapper
      'value',
    ]
    for (const field of fallbacks) {
      const fallbackValue = value[field]
      if (fallbackValue && typeof fallbackValue === 'string') {
        return fallbackValue
      }
      // Handle boolean values
      if (typeof fallbackValue === 'boolean') {
        return String(fallbackValue)
      }
    }

    // Last resort: return first string value found or JSON representation
    const stringValue = Object.values(value).find(v => typeof v === 'string' && v.length > 0)
    if (stringValue) {
      return stringValue as string
    }

    // For boolean or simple values, try to create a readable string
    if (Object.keys(value).length === 1) {
      const [key, val] = Object.entries(value)[0]
      if (typeof val === 'boolean' || typeof val === 'number') {
        return `${key}: ${val}`
      }
    }

    return ''
  }

  /**
   * Get chip data for rendering from a facet value
   */
  function getChips(
    value: Record<string, unknown>,
    config: ResolvedDisplayConfig
  ): ChipData[] {
    return config.chipFields
      .filter((field) => {
        const fieldValue = value[field]
        return fieldValue !== null && fieldValue !== undefined && fieldValue !== ''
      })
      .map((field) => {
        const fieldValue = String(value[field])
        let color = 'default'

        // Apply severity color if this is the severity field
        if (field === config.severityField && config.severityColors[fieldValue]) {
          color = config.severityColors[fieldValue]
        }

        return {
          field,
          value: fieldValue,
          color,
        }
      })
  }

  /**
   * Get quote value if configured
   */
  function getQuote(
    value: Record<string, unknown>,
    config: ResolvedDisplayConfig
  ): string | null {
    if (!config.quoteField) {
      return null
    }

    const quoteValue = value[config.quoteField]
    if (quoteValue && typeof quoteValue === 'string') {
      return quoteValue
    }

    return null
  }

  /**
   * Check if a FacetType has values in the given content
   */
  function hasValues(
    content: Record<string, unknown>,
    facetType: FacetType
  ): boolean {
    const values = getValuesForFacetType(content, facetType)
    return values.length > 0
  }

  /**
   * Get default icon for a FacetType if not specified
   * @see {@link @/config/facetMappings} for centralized configuration
   */
  function getIcon(facetType: FacetType): string {
    if (facetType.icon) {
      return facetType.icon
    }
    return getDefaultFacetTypeIcon(facetType.slug)
  }

  /**
   * Get default color for a FacetType if not specified
   * @see {@link @/config/facetMappings} for centralized configuration
   */
  function getColor(facetType: FacetType): string {
    if (facetType.color) {
      return facetType.color
    }
    return getDefaultFacetTypeColor(facetType.slug)
  }

  /**
   * Convert a FacetGroup (from API summary) to a minimal FacetType
   * for use with rendering components
   */
  function facetGroupToFacetType(group: FacetGroup): FacetType {
    return {
      id: group.facet_type_id,
      slug: group.facet_type_slug,
      name: group.facet_type_name,
      icon: group.facet_type_icon || group.icon,
      color: group.facet_type_color || group.color,
      value_schema: group.value_schema,
      // Fill in other required fields with defaults
      name_plural: group.facet_type_name,
      value_type: group.facet_type_value_type || group.value_type || 'object',
      is_active: true,
      ai_extraction_enabled: true,
    } as FacetType
  }

  return {
    getDisplayConfig,
    getFieldNameForFacetType,
    getValuesForFacetType,
    normalizeValue,
    getPrimaryValue,
    getChips,
    getQuote,
    hasValues,
    getIcon,
    getColor,
    facetGroupToFacetType,
  }
}
