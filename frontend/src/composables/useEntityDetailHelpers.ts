/**
 * Composable for entity detail helper functions
 * Contains utility functions used across entity detail components
 */

/**
 * Build text representation from structured value
 */
export function buildTextRepresentation(value: Record<string, any>, _facetType?: any): string {
  if (!value || Object.keys(value).length === 0) return ''

  // If there's a description field, use it as primary text
  if (value.description) return value.description
  if (value.text) return value.text
  if (value.name) return value.name

  // Otherwise concatenate all string values
  const parts: string[] = []
  for (const [, val] of Object.entries(value)) {
    if (typeof val === 'string' && val.trim()) {
      parts.push(val)
    } else if (Array.isArray(val)) {
      parts.push(val.join(', '))
    }
  }
  return parts.join(' - ')
}

/**
 * Get structured description from facet value
 */
export function getStructuredDescription(facet: any): string {
  // Try text_representation first
  if (facet.text_representation) return facet.text_representation
  // Then try value.description or value.text
  const val = facet.value
  if (!val) return ''
  if (typeof val === 'string') return val
  return val.description || val.text || val.concern || val.opportunity || ''
}

/**
 * Get structured type from facet value
 */
export function getStructuredType(facet: any): string | null {
  const val = facet.value
  if (!val || typeof val === 'string') return null
  return val.type || null
}

/**
 * Get structured severity from facet value
 */
export function getStructuredSeverity(facet: any): string | null {
  const val = facet.value
  if (!val || typeof val === 'string') return null
  return val.severity || null
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
 * Entity cache helper
 */
const entityCache = new Map<string, { data: any; timestamp: number }>()
const CACHE_TTL = 5 * 60 * 1000 // 5 minutes

export function getCachedData(key: string): any | null {
  const cached = entityCache.get(key)
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    return cached.data
  }
  return null
}

export function setCachedData(key: string, data: any) {
  entityCache.set(key, { data, timestamp: Date.now() })
}

export function clearCachedData(key: string) {
  entityCache.delete(key)
}

export function clearAllCachedData() {
  entityCache.clear()
}
