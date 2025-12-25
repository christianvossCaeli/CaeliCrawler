/**
 * Composable for entity detail helper functions
 * Contains utility functions used across entity detail components
 */

/**
 * Structured value that can contain different field types
 */
interface StructuredValue {
  description?: string
  text?: string
  name?: string
  [key: string]: unknown
}

/**
 * Build text representation from structured value
 */
export function buildTextRepresentation(value: Record<string, unknown>, _facetType?: string): string {
  const structuredValue = value as StructuredValue
  if (!structuredValue || Object.keys(structuredValue).length === 0) return ''

  // If there's a description field, use it as primary text
  if (structuredValue.description) return structuredValue.description
  if (structuredValue.text) return structuredValue.text
  if (structuredValue.name) return structuredValue.name

  // Otherwise concatenate all string values
  const parts: string[] = []
  for (const [, val] of Object.entries(structuredValue)) {
    if (typeof val === 'string' && val.trim()) {
      parts.push(val)
    } else if (Array.isArray(val)) {
      parts.push(val.join(', '))
    }
  }
  return parts.join(' - ')
}

/**
 * Facet structure with optional text representation
 */
interface Facet {
  text_representation?: string
  value?: string | FacetValue
}

/**
 * Structured facet value
 */
interface FacetValue {
  description?: string
  text?: string
  concern?: string
  opportunity?: string
  type?: string
  severity?: string
  [key: string]: unknown
}

/**
 * Type guard to check if value is a FacetValue object
 */
function isFacetValue(value: unknown): value is FacetValue {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/**
 * Get structured description from facet value
 */
export function getStructuredDescription(facet: Facet): string {
  // Try text_representation first
  if (facet.text_representation) return facet.text_representation
  // Then try value.description or value.text
  const val = facet.value
  if (!val) return ''
  if (typeof val === 'string') return val
  if (isFacetValue(val)) {
    return val.description || val.text || val.concern || val.opportunity || ''
  }
  return ''
}

/**
 * Get structured type from facet value
 */
export function getStructuredType(facet: Facet): string | null {
  const val = facet.value
  if (!val || typeof val === 'string') return null
  if (isFacetValue(val)) {
    return val.type || null
  }
  return null
}

/**
 * Get structured severity from facet value
 */
export function getStructuredSeverity(facet: Facet): string | null {
  const val = facet.value
  if (!val || typeof val === 'string') return null
  if (isFacetValue(val)) {
    return val.severity || null
  }
  return null
}

/**
 * Escape CSV value
 */
export function escapeCSV(value: string): string {
  if (value.includes(',') || value.includes('"') || value.includes('\n')) {
    return `"${value.replace(/"/g, '""')}"`
  }
  return value
}

/**
 * Download file helper
 */
export function downloadFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/**
 * Cached data entry with timestamp
 */
interface CacheEntry<T = unknown> {
  data: T
  timestamp: number
}

/**
 * Entity cache helper
 */
const entityCache = new Map<string, CacheEntry>()
const CACHE_TTL = 5 * 60 * 1000 // 5 minutes

/**
 * Get cached data with type parameter
 * @template T - The expected type of the cached data
 */
export function getCachedData<T = unknown>(key: string): T | null {
  const cached = entityCache.get(key)
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    return cached.data as T
  }
  return null
}

/**
 * Set cached data
 * @template T - The type of the data being cached
 */
export function setCachedData<T = unknown>(key: string, data: T): void {
  entityCache.set(key, { data, timestamp: Date.now() })
}

export function clearCachedData(key: string) {
  entityCache.delete(key)
}

export function clearAllCachedData() {
  entityCache.clear()
}
