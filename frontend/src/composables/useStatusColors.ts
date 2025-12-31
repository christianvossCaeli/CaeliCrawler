/**
 * Centralized status color and icon mappings.
 *
 * This composable provides consistent status colors across the application,
 * reducing code duplication and ensuring visual consistency.
 */

/**
 * Common status color mappings used across different domains.
 * Maps status strings to Vuetify color names.
 */
export const STATUS_COLORS: Record<string, string> = {
  // Success states
  success: 'success',
  completed: 'success',
  COMPLETED: 'success',
  active: 'success',
  ACTIVE: 'success',
  healthy: 'success',
  extracted: 'success',
  EXTRACTED: 'success',
  enabled: 'success',
  true: 'success',

  // Warning states
  warning: 'warning',
  pending: 'warning',
  PENDING: 'warning',
  processing: 'warning',
  PROCESSING: 'info',
  queued: 'warning',
  QUEUED: 'warning',
  skipped: 'warning',
  SKIPPED: 'warning',

  // Info states
  info: 'info',
  running: 'info',
  RUNNING: 'info',
  in_progress: 'info',
  scheduled: 'info',
  SCHEDULED: 'info',
  new: 'info',
  NEW: 'info',
  analyzing: 'info',
  ANALYZING: 'info',

  // Error states
  error: 'error',
  ERROR: 'error',
  failed: 'error',
  FAILED: 'error',
  unhealthy: 'error',
  false: 'error',

  // Neutral states
  inactive: 'grey',
  INACTIVE: 'grey',
  paused: 'warning',
  PAUSED: 'warning',
  cancelled: 'grey',
  CANCELLED: 'grey',
  draft: 'grey',
  unknown: 'grey',
  disabled: 'grey',
  archived: 'error',
  ARCHIVED: 'error',
  filtered: 'grey',
  FILTERED: 'grey',
}

/**
 * Status icon mappings.
 */
export const STATUS_ICONS: Record<string, string> = {
  // Success states
  success: 'mdi-check-circle',
  completed: 'mdi-check-circle',
  COMPLETED: 'mdi-check-circle',
  active: 'mdi-check-circle',
  ACTIVE: 'mdi-check-circle',
  healthy: 'mdi-heart-pulse',
  extracted: 'mdi-check-circle',
  EXTRACTED: 'mdi-check-circle',
  enabled: 'mdi-check-circle',
  true: 'mdi-check-circle',

  // Warning states
  warning: 'mdi-alert',
  pending: 'mdi-clock-outline',
  PENDING: 'mdi-clock-outline',
  processing: 'mdi-progress-clock',
  PROCESSING: 'mdi-progress-clock',
  queued: 'mdi-tray-full',
  QUEUED: 'mdi-tray-full',
  skipped: 'mdi-skip-next',
  SKIPPED: 'mdi-skip-next',

  // Info states
  info: 'mdi-information',
  running: 'mdi-play-circle',
  RUNNING: 'mdi-sync mdi-spin',
  in_progress: 'mdi-progress-clock',
  scheduled: 'mdi-calendar-clock',
  SCHEDULED: 'mdi-calendar-clock',
  new: 'mdi-new-box',
  NEW: 'mdi-new-box',
  analyzing: 'mdi-magnify-scan',
  ANALYZING: 'mdi-magnify-scan',

  // Error states
  error: 'mdi-alert-circle',
  ERROR: 'mdi-alert-circle',
  failed: 'mdi-close-circle',
  FAILED: 'mdi-close-circle',
  unhealthy: 'mdi-heart-broken',
  false: 'mdi-close-circle',

  // Neutral states
  inactive: 'mdi-minus-circle',
  INACTIVE: 'mdi-minus-circle',
  paused: 'mdi-pause-circle',
  PAUSED: 'mdi-pause-circle',
  cancelled: 'mdi-cancel',
  CANCELLED: 'mdi-cancel',
  draft: 'mdi-file-edit',
  unknown: 'mdi-help-circle',
  disabled: 'mdi-minus-circle',
  archived: 'mdi-archive',
  ARCHIVED: 'mdi-archive',
  filtered: 'mdi-filter-remove',
  FILTERED: 'mdi-filter-remove',
}

/**
 * Get the color for a given status string.
 *
 * @param status - The status string (case-insensitive for common statuses)
 * @param defaultColor - Color to return if status is unknown (default: 'grey')
 * @returns Vuetify color name
 *
 * @example
 * getStatusColor('active')     // 'success'
 * getStatusColor('PENDING')    // 'warning'
 * getStatusColor('failed')     // 'error'
 * getStatusColor('unknown_status') // 'grey'
 */
export function getStatusColor(status: string | null | undefined, defaultColor = 'grey'): string {
  if (!status) return defaultColor

  // Try exact match first
  if (STATUS_COLORS[status]) {
    return STATUS_COLORS[status]
  }

  // Try lowercase match
  const lowerStatus = status.toLowerCase()
  if (STATUS_COLORS[lowerStatus]) {
    return STATUS_COLORS[lowerStatus]
  }

  return defaultColor
}

/**
 * Get the icon for a given status string.
 *
 * @param status - The status string
 * @param defaultIcon - Icon to return if status is unknown
 * @returns MDI icon name
 */
export function getStatusIcon(status: string | null | undefined, defaultIcon = 'mdi-help-circle'): string {
  if (!status) return defaultIcon

  if (STATUS_ICONS[status]) {
    return STATUS_ICONS[status]
  }

  const lowerStatus = status.toLowerCase()
  if (STATUS_ICONS[lowerStatus]) {
    return STATUS_ICONS[lowerStatus]
  }

  return defaultIcon
}

/**
 * Vue composable for status colors and icons.
 *
 * @example
 * const { getStatusColor, getStatusIcon } = useStatusColors()
 *
 * const color = getStatusColor(item.status)
 * const icon = getStatusIcon(item.status)
 */
export function useStatusColors() {
  return {
    getStatusColor,
    getStatusIcon,
    STATUS_COLORS,
    STATUS_ICONS,
  }
}
