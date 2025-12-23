/**
 * CSV Parser Utility for Bulk Import
 *
 * Consolidated CSV parsing logic for sources bulk import.
 * This module handles:
 * - CSV/text parsing with multiple delimiters (;, ,, |, tab)
 * - URL validation
 * - Source type detection
 * - Duplicate detection
 * - Size and line count validation
 */

import { BULK_IMPORT } from '@/config/sources'
import type { BulkImportPreviewItem, SourceType } from '@/types/sources'
import { isSourceType } from '@/types/sources'

/**
 * Result of CSV validation
 */
export interface CsvValidationResult {
  valid: boolean
  error?: string
  lineCount?: number
  byteSize?: number
}

/**
 * Result of CSV parsing
 *
 * Note: There are two types of errors:
 * - `parseError`: Critical error that prevents parsing (empty input, file too large, etc.)
 * - `invalidLineCount`: Number of individual lines with validation errors (invalid URLs, etc.)
 *
 * Check `parseError` first - if set, the entire parse failed.
 * If not set, check `invalidLineCount` for per-line issues.
 */
export interface CsvParseResult {
  /** Parsed items (may include items with errors) */
  items: BulkImportPreviewItem[]
  /** Number of valid items ready for import */
  validCount: number
  /** Number of duplicate items detected */
  duplicateCount: number
  /** Number of items with validation errors (invalid URL, etc.) */
  invalidLineCount: number
  /** @deprecated Use invalidLineCount instead */
  errorCount: number
  /** Critical parse error (empty input, file too large) - if set, parsing failed completely */
  parseError?: string
  /** @deprecated Use parseError instead */
  error?: string
}

/**
 * Options for CSV parsing
 */
export interface CsvParseOptions {
  defaultTags?: string[]
  existingUrls?: string[]
  skipDuplicates?: boolean
}

/**
 * Validate CSV input before parsing
 *
 * @param text - CSV text content
 * @returns Validation result
 */
export function validateCsvInput(text: string): CsvValidationResult {
  if (!text || !text.trim()) {
    return { valid: false, error: 'CSV content is empty' }
  }

  const byteSize = new Blob([text]).size
  if (byteSize > BULK_IMPORT.MAX_FILE_SIZE) {
    return {
      valid: false,
      error: `CSV file too large. Maximum size: ${Math.round(BULK_IMPORT.MAX_FILE_SIZE / 1024 / 1024)}MB`,
      byteSize,
    }
  }

  const lines = text.trim().split('\n')
  if (lines.length > BULK_IMPORT.MAX_LINES) {
    return {
      valid: false,
      error: `Too many lines. Maximum: ${BULK_IMPORT.MAX_LINES.toLocaleString()} lines`,
      lineCount: lines.length,
    }
  }

  return { valid: true, lineCount: lines.length, byteSize }
}

/**
 * Detect the delimiter used in CSV content
 *
 * @param text - CSV text content
 * @returns Detected delimiter
 */
export function detectDelimiter(text: string): string {
  const firstLine = text.split('\n')[0] || ''

  // Count occurrences of each delimiter
  const delimiters = [';', ',', '|', '\t']
  let maxCount = 0
  let detected = ';'

  for (const d of delimiters) {
    const count = (firstLine.match(new RegExp(`\\${d}`, 'g')) || []).length
    if (count > maxCount) {
      maxCount = count
      detected = d
    }
  }

  return detected
}

/**
 * Check if a string is a valid URL
 *
 * @param url - URL string to validate
 * @returns True if valid URL with proper hostname
 */
export function isValidUrl(url: string): boolean {
  if (!url) return false
  try {
    const parsed = new URL(url)
    // Must have http(s) protocol
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
      return false
    }
    // Hostname must contain at least one dot (e.g., example.com)
    // This prevents auto-prefixed strings like "invalid-url" from being valid
    if (!parsed.hostname.includes('.')) {
      return false
    }
    return true
  } catch {
    return false
  }
}

/**
 * Normalize URL (lowercase, trim, ensure protocol)
 *
 * @param url - URL string to normalize
 * @returns Normalized URL
 */
export function normalizeUrl(url: string): string {
  let normalized = url.trim().toLowerCase()

  // Add protocol if missing
  if (normalized && !normalized.startsWith('http://') && !normalized.startsWith('https://')) {
    normalized = `https://${normalized}`
  }

  return normalized
}

/**
 * Parse source type from string
 *
 * @param typeStr - Source type string
 * @returns Validated SourceType or default 'WEBSITE'
 */
export function parseSourceType(typeStr: string | undefined): SourceType {
  if (!typeStr) return 'WEBSITE'

  const normalized = typeStr.trim().toUpperCase()

  // Map common variations
  const typeMap: Record<string, SourceType> = {
    'WEBSITE': 'WEBSITE',
    'WEB': 'WEBSITE',
    'RSS': 'RSS',
    'RSS_FEED': 'RSS',
    'RSS-FEED': 'RSS',
    'FEED': 'RSS',
    'API': 'CUSTOM_API',
    'CUSTOM_API': 'CUSTOM_API',
    'OPARL': 'OPARL_API',
    'OPARL_API': 'OPARL_API',
    'SHAREPOINT': 'SHAREPOINT',
  }

  const mapped = typeMap[normalized]
  if (mapped) return mapped

  // Check if it's a valid source type
  if (isSourceType(normalized)) {
    return normalized
  }

  return 'WEBSITE'
}

/**
 * Parse tags from string (comma or semicolon separated)
 *
 * @param tagsStr - Tags string
 * @returns Array of trimmed tags
 */
export function parseTags(tagsStr: string | undefined): string[] {
  if (!tagsStr) return []

  // Split by comma (but not if inside quotes)
  return tagsStr
    .split(/[,;]/)
    .map(t => t.trim())
    .filter(t => t.length > 0)
}

/**
 * Parse a single CSV line
 *
 * @param line - CSV line
 * @param delimiter - Field delimiter
 * @param options - Parse options
 * @param existingUrlsSet - Set of existing URLs for duplicate detection
 * @returns Parsed preview item or null if invalid
 */
export function parseCsvLine(
  line: string,
  delimiter: string,
  options: CsvParseOptions,
  existingUrlsSet: Set<string>
): BulkImportPreviewItem | null {
  const trimmed = line.trim()
  if (!trimmed) return null

  // Skip header line
  const headerIndicators = ['name', 'url', 'base_url', 'type', 'source_type', 'tags']
  const lowerLine = trimmed.toLowerCase()
  if (headerIndicators.some(h => lowerLine.startsWith(h))) {
    return null
  }

  const parts = trimmed.split(delimiter).map(p => p.trim())

  let name: string
  let url: string
  let sourceType: SourceType = 'WEBSITE'
  let tags: string[] = []

  if (parts.length === 1) {
    // Only URL provided - extract name from URL
    url = normalizeUrl(parts[0])
    try {
      const parsed = new URL(url)
      name = parsed.hostname.replace('www.', '')
    } catch {
      name = parts[0]
    }
  } else if (parts.length === 2) {
    // Name | URL format
    name = parts[0]
    url = normalizeUrl(parts[1])
  } else if (parts.length >= 3) {
    // Name | URL | Type | Tags format
    name = parts[0]
    url = normalizeUrl(parts[1])
    sourceType = parseSourceType(parts[2])
    if (parts.length >= 4) {
      tags = parseTags(parts[3])
    }
  } else {
    return null
  }

  // Validate URL
  if (!isValidUrl(url)) {
    return {
      name: name || 'Invalid',
      base_url: url,
      source_type: sourceType,
      tags,
      allTags: [...(options.defaultTags || []), ...tags],
      error: 'Invalid URL format',
    }
  }

  // Check for duplicates
  const isDuplicate = existingUrlsSet.has(url.toLowerCase())

  return {
    name,
    base_url: url,
    source_type: sourceType,
    tags,
    allTags: [...(options.defaultTags || []), ...tags],
    duplicate: isDuplicate,
  }
}

/**
 * Parse CSV content into preview items
 *
 * @param text - CSV text content
 * @param options - Parse options
 * @returns Parse result with items and counts
 */
export function parseCsv(text: string, options: CsvParseOptions = {}): CsvParseResult {
  // Validate input first
  const validation = validateCsvInput(text)
  if (!validation.valid) {
    return {
      items: [],
      validCount: 0,
      duplicateCount: 0,
      invalidLineCount: 0,
      errorCount: 0, // deprecated
      parseError: validation.error,
      error: validation.error, // deprecated
    }
  }

  const delimiter = detectDelimiter(text)
  const lines = text.trim().split('\n')

  // Create set of existing URLs for fast lookup
  const existingUrlsSet = new Set(
    (options.existingUrls || []).map(u => u.toLowerCase())
  )

  const items: BulkImportPreviewItem[] = []
  let validCount = 0
  let duplicateCount = 0
  let invalidLineCount = 0

  for (const line of lines) {
    const item = parseCsvLine(line, delimiter, options, existingUrlsSet)
    if (!item) continue

    items.push(item)

    if (item.error) {
      invalidLineCount++
    } else if (item.duplicate) {
      duplicateCount++
      // Still count as valid if not skipping duplicates
      if (!options.skipDuplicates) {
        validCount++
      }
    } else {
      validCount++
    }

    // Add to existing URLs to detect duplicates within the same import
    existingUrlsSet.add(item.base_url.toLowerCase())
  }

  return {
    items,
    validCount,
    duplicateCount,
    invalidLineCount,
    errorCount: invalidLineCount, // deprecated - kept for backwards compatibility
  }
}

/**
 * Validate a regex pattern
 *
 * @param pattern - Regex pattern string
 * @returns True if valid regex
 */
export function isValidRegexPattern(pattern: string): boolean {
  if (!pattern) return true // Empty is valid (no filter)
  try {
    new RegExp(pattern)
    return true
  } catch {
    return false
  }
}

/**
 * Validate multiple regex patterns
 *
 * @param patterns - Array of pattern strings
 * @returns Object with valid flag and invalid patterns
 */
export function validateRegexPatterns(patterns: string[]): {
  valid: boolean
  invalidPatterns: string[]
} {
  const invalidPatterns: string[] = []

  for (const pattern of patterns) {
    if (!isValidRegexPattern(pattern)) {
      invalidPatterns.push(pattern)
    }
  }

  return {
    valid: invalidPatterns.length === 0,
    invalidPatterns,
  }
}
