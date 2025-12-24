/**
 * Shared view helper utilities.
 *
 * This module provides common formatting and display utilities
 * used across multiple views to eliminate code duplication.
 */

/**
 * Format a date string for display.
 * @param dateStr - ISO date string or Date object
 * @param options - Intl.DateTimeFormat options
 * @returns Formatted date string in German locale
 */
export function formatDate(
  dateStr: string | Date | null | undefined,
  options: Intl.DateTimeFormatOptions = {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }
): string {
  if (!dateStr) return '-'
  try {
    const date = typeof dateStr === 'string' ? new Date(dateStr) : dateStr
    return date.toLocaleDateString('de-DE', options)
  } catch {
    return String(dateStr)
  }
}

/**
 * Format a date string without time.
 * @param dateStr - ISO date string or Date object
 * @returns Formatted date string (DD.MM.YYYY)
 */
export function formatDateOnly(dateStr: string | Date | null | undefined): string {
  return formatDate(dateStr, {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

/**
 * Format a relative time (e.g., "vor 2 Stunden").
 * @param dateStr - ISO date string or Date object
 * @returns Relative time string in German
 */
export function formatRelativeTime(dateStr: string | Date | null | undefined): string {
  if (!dateStr) return '-'
  try {
    const date = typeof dateStr === 'string' ? new Date(dateStr) : dateStr
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMins / 60)
    const diffDays = Math.floor(diffHours / 24)

    if (diffMins < 1) return 'gerade eben'
    if (diffMins < 60) return `vor ${diffMins} Min.`
    if (diffHours < 24) return `vor ${diffHours} Std.`
    if (diffDays < 7) return `vor ${diffDays} Tag${diffDays > 1 ? 'en' : ''}`
    return formatDateOnly(date)
  } catch {
    return String(dateStr)
  }
}

/**
 * Status color mapping for common statuses.
 */
export const STATUS_COLORS: Record<string, string> = {
  // General statuses
  ACTIVE: 'success',
  active: 'success',
  INACTIVE: 'grey',
  inactive: 'grey',
  PENDING: 'warning',
  pending: 'warning',
  ERROR: 'error',
  error: 'error',
  FAILED: 'error',
  failed: 'error',

  // Processing statuses
  COMPLETED: 'success',
  completed: 'success',
  PROCESSING: 'info',
  processing: 'info',
  RUNNING: 'info',
  running: 'info',
  QUEUED: 'warning',
  queued: 'warning',
  SCHEDULED: 'warning',
  scheduled: 'warning',
  CANCELLED: 'grey',
  cancelled: 'grey',
  SKIPPED: 'grey',
  skipped: 'grey',

  // Document statuses
  EXTRACTED: 'success',
  extracted: 'success',
  NEW: 'info',
  new: 'info',

  // Boolean-like
  true: 'success',
  false: 'error',
  enabled: 'success',
  disabled: 'grey',
}

/**
 * Get color for a status value.
 * @param status - Status string
 * @returns Vuetify color name
 */
export function getStatusColor(status: string | null | undefined): string {
  if (!status) return 'grey'
  return STATUS_COLORS[status] || 'grey'
}

/**
 * Severity color mapping.
 */
export const SEVERITY_COLORS: Record<string, string> = {
  // German
  hoch: 'error',
  mittel: 'warning',
  niedrig: 'success',
  kritisch: 'error',

  // English
  high: 'error',
  medium: 'warning',
  low: 'success',
  critical: 'error',

  // Numeric levels
  '1': 'success',
  '2': 'info',
  '3': 'warning',
  '4': 'error',
  '5': 'error',
}

/**
 * Get color for a severity level.
 * @param severity - Severity string
 * @returns Vuetify color name
 */
export function getSeverityColor(severity: string | null | undefined): string {
  if (!severity) return 'grey'
  return SEVERITY_COLORS[severity.toLowerCase()] || 'grey'
}

/**
 * Severity label mapping (German).
 */
export const SEVERITY_LABELS: Record<string, string> = {
  high: 'Hoch',
  medium: 'Mittel',
  low: 'Niedrig',
  critical: 'Kritisch',
  hoch: 'Hoch',
  mittel: 'Mittel',
  niedrig: 'Niedrig',
  kritisch: 'Kritisch',
}

/**
 * Get localized label for severity.
 * @param severity - Severity string
 * @returns German severity label
 */
export function getSeverityLabel(severity: string | null | undefined): string {
  if (!severity) return '-'
  return SEVERITY_LABELS[severity.toLowerCase()] || severity
}

/**
 * Get contrasting text color for a background color.
 * @param bgColor - Vuetify color name
 * @returns 'white' or 'black'
 */
export function getContrastColor(bgColor: string): string {
  const darkColors = ['error', 'success', 'info', 'primary', 'secondary', 'warning']
  return darkColors.includes(bgColor) ? 'white' : 'black'
}

/**
 * Format a number with locale-specific formatting.
 * @param value - Number to format
 * @param options - Intl.NumberFormat options
 * @returns Formatted number string
 */
export function formatNumber(
  value: number | null | undefined,
  options: Intl.NumberFormatOptions = {}
): string {
  if (value === null || value === undefined) return '-'
  return value.toLocaleString('de-DE', options)
}

/**
 * Format bytes to human-readable size.
 * @param bytes - Number of bytes
 * @returns Human-readable size string (e.g., "1.5 MB")
 */
export function formatBytes(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined) return '-'
  if (bytes === 0) return '0 B'

  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  const size = bytes / Math.pow(1024, i)

  return `${size.toFixed(i > 0 ? 1 : 0)} ${units[i]}`
}

/**
 * Truncate text with ellipsis.
 * @param text - Text to truncate
 * @param maxLength - Maximum length
 * @returns Truncated text
 */
export function truncateText(text: string | null | undefined, maxLength: number = 100): string {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength - 3) + '...'
}

/**
 * Escape CSV field value.
 * @param value - Value to escape
 * @returns Escaped CSV value
 */
export function escapeCSV(value: string | null | undefined): string {
  if (!value) return ''
  if (value.includes(',') || value.includes('"') || value.includes('\n')) {
    return `"${value.replace(/"/g, '""')}"`
  }
  return value
}

/**
 * Download content as a file.
 * @param content - File content
 * @param filename - File name
 * @param mimeType - MIME type
 */
export function downloadFile(content: string | Blob, filename: string, mimeType: string): void {
  const blob = content instanceof Blob ? content : new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
