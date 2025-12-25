/**
 * Composable for formatting timestamps in a human-readable relative format
 *
 * Provides consistent time formatting across all widget components.
 */

import { useI18n } from 'vue-i18n'

/** Time thresholds in milliseconds */
const MS_PER_MINUTE = 60_000
const MS_PER_HOUR = 3_600_000
const MS_PER_DAY = 86_400_000

export interface FormatTimeOptions {
  /** Show full date after this many days (default: 7) */
  fullDateAfterDays?: number
}

export function useFormatTime() {
  const { t } = useI18n()

  /**
   * Format a timestamp as a human-readable relative time
   * @param timestamp - ISO 8601 timestamp string or null
   * @param options - Optional configuration
   * @returns Formatted string like "just now", "5 minutes ago", etc.
   */
  const formatTime = (
    timestamp: string | null | undefined,
    options: FormatTimeOptions = {}
  ): string => {
    if (!timestamp) return ''

    const { fullDateAfterDays = 7 } = options

    const date = new Date(timestamp)

    // Validate date
    if (isNaN(date.getTime())) {
      return ''
    }

    const now = new Date()
    const diff = now.getTime() - date.getTime()

    // Handle future dates (clock skew protection)
    if (diff < 0) {
      return t('common.justNow')
    }

    if (diff < MS_PER_MINUTE) {
      return t('common.justNow')
    }

    if (diff < MS_PER_HOUR) {
      const minutes = Math.floor(diff / MS_PER_MINUTE)
      return t('common.minutesAgo', { n: minutes })
    }

    if (diff < MS_PER_DAY) {
      const hours = Math.floor(diff / MS_PER_HOUR)
      return t('common.hoursAgo', { n: hours })
    }

    const days = Math.floor(diff / MS_PER_DAY)
    if (days < fullDateAfterDays) {
      return t('common.daysAgo', { n: days })
    }

    // Return localized date string for older dates
    return date.toLocaleDateString()
  }

  /**
   * Format a timestamp for display with optional fallback text
   * @param timestamp - ISO 8601 timestamp string or null
   * @param fallback - Text to show when timestamp is null
   */
  const formatTimeWithFallback = (
    timestamp: string | null | undefined,
    fallback: string
  ): string => {
    if (!timestamp) return fallback
    return formatTime(timestamp)
  }

  return {
    formatTime,
    formatTimeWithFallback,
  }
}
