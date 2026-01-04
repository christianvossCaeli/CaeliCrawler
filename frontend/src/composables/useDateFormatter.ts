/**
 * Date Formatting Composable
 *
 * Centralized date formatting with locale support using date-fns.
 * Use this composable for all date formatting needs in the application.
 *
 * @example
 * ```ts
 * const { formatDate, formatDateTime, formatDateShort, formatTime } = useDateFormatter()
 *
 * formatDate('2024-01-15T10:30:00Z')      // '15.01.2024' (date only)
 * formatDateTime('2024-01-15T10:30:00Z')  // '15.01.2024 10:30' (date + time)
 * formatTime('2024-01-15T10:30:00Z')      // '10:30' (time only)
 * formatRelativeTime('2024-01-15T10:30:00Z') // 'vor 2 Stunden' (relative)
 * ```
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { format } from 'date-fns'
import { de, enUS } from 'date-fns/locale'

// Common format patterns
const FORMATS = {
  date: 'dd.MM.yyyy',
  dateTime: 'dd.MM.yyyy HH:mm',
  dateTimeFull: 'dd.MM.yyyy HH:mm:ss',
  time: 'HH:mm',
  timeFull: 'HH:mm:ss',
  iso: "yyyy-MM-dd'T'HH:mm:ss",
} as const

export function useDateFormatter() {
  const { locale, t } = useI18n()
  const dateLocale = computed(() => (locale.value === 'de' ? de : enUS))

  /**
   * Core format function with custom format string
   */
  function formatDate(
    dateValue: string | Date | null | undefined,
    formatStr: string = FORMATS.date
  ): string {
    if (!dateValue) return ''
    try {
      const normalized = dateValue instanceof Date ? dateValue : new Date(dateValue)
      return format(normalized, formatStr, { locale: dateLocale.value })
    } catch {
      return String(dateValue)
    }
  }

  /**
   * Format as date + time (dd.MM.yyyy HH:mm)
   */
  function formatDateTime(dateValue: string | Date | null | undefined): string {
    return formatDate(dateValue, FORMATS.dateTime)
  }

  /**
   * Format as date + time + seconds (dd.MM.yyyy HH:mm:ss)
   */
  function formatDateTimeFull(dateValue: string | Date | null | undefined): string {
    return formatDate(dateValue, FORMATS.dateTimeFull)
  }

  /**
   * Format as date only (dd.MM.yyyy)
   */
  function formatDateShort(dateValue: string | Date | null | undefined): string {
    return formatDate(dateValue, FORMATS.date)
  }

  /**
   * Format as time only (HH:mm)
   */
  function formatTime(dateValue: string | Date | null | undefined): string {
    return formatDate(dateValue, FORMATS.time)
  }

  /**
   * Format as time with seconds (HH:mm:ss)
   */
  function formatTimeFull(dateValue: string | Date | null | undefined): string {
    return formatDate(dateValue, FORMATS.timeFull)
  }

  /**
   * Format a date as relative time (e.g., "2 hours ago", "vor 2 Stunden")
   */
  function formatRelativeTime(dateStr: string | Date | null | undefined): string {
    if (!dateStr) return ''
    try {
      const date = dateStr instanceof Date ? dateStr : new Date(dateStr)
      const now = new Date()
      const diffMs = now.getTime() - date.getTime()
      const diffMins = Math.floor(diffMs / 60000)
      const diffHours = Math.floor(diffMs / 3600000)
      const diffDays = Math.floor(diffMs / 86400000)

      if (diffMins < 1) return t('common.justNow', 'just now')
      if (diffMins < 60) return t('common.minutesAgo', { count: diffMins }, `${diffMins} min ago`)
      if (diffHours < 24) return t('common.hoursAgo', { count: diffHours }, `${diffHours}h ago`)
      if (diffDays < 7) return t('common.daysAgo', { count: diffDays }, `${diffDays}d ago`)
      return formatDateShort(dateStr)
    } catch {
      return String(dateStr)
    }
  }

  /**
   * Format a number with locale-aware separators
   *
   * @example
   * ```ts
   * formatNumber(1234567.89) // '1.234.567,89' (de) or '1,234,567.89' (en)
   * formatNumber(0.123, { style: 'percent' }) // '12,3 %' (de) or '12.3%' (en)
   * formatNumber(1234.5, { maximumFractionDigits: 0 }) // '1.235' (de) or '1,235' (en)
   * ```
   */
  function formatNumber(
    value: number | null | undefined,
    options?: Intl.NumberFormatOptions
  ): string {
    if (value === null || value === undefined) return ''
    try {
      const localeCode = locale.value === 'de' ? 'de-DE' : 'en-US'
      return new Intl.NumberFormat(localeCode, options).format(value)
    } catch {
      return String(value)
    }
  }

  /**
   * Format a number as currency
   *
   * @example
   * ```ts
   * formatCurrency(1234.56, 'EUR') // '1.234,56 €' (de) or '€1,234.56' (en)
   * formatCurrency(99.99, 'USD') // '99,99 $' (de) or '$99.99' (en)
   * ```
   */
  function formatCurrency(
    value: number | null | undefined,
    currency: string = 'EUR'
  ): string {
    return formatNumber(value, { style: 'currency', currency })
  }

  /**
   * Format a number as percentage
   *
   * @example
   * ```ts
   * formatPercent(0.1234) // '12,34 %' (de) or '12.34%' (en)
   * formatPercent(0.5, { maximumFractionDigits: 0 }) // '50 %' (de) or '50%' (en)
   * ```
   */
  function formatPercent(
    value: number | null | undefined,
    options?: Omit<Intl.NumberFormatOptions, 'style'>
  ): string {
    return formatNumber(value, { style: 'percent', ...options })
  }

  /**
   * Format bytes as human-readable file size
   *
   * @example
   * ```ts
   * formatFileSize(1024) // '1 KB'
   * formatFileSize(1536) // '1,5 KB' (de) or '1.5 KB' (en)
   * formatFileSize(1048576) // '1 MB'
   * ```
   */
  function formatFileSize(bytes: number | null | undefined): string {
    if (bytes === null || bytes === undefined) return ''
    const units = ['B', 'KB', 'MB', 'GB', 'TB']
    let unitIndex = 0
    let size = bytes

    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024
      unitIndex++
    }

    return `${formatNumber(size, { maximumFractionDigits: unitIndex === 0 ? 0 : 1 })} ${units[unitIndex]}`
  }

  return {
    // Locale
    dateLocale,
    // Format patterns (for custom formatting)
    FORMATS,
    // Date formatting functions
    formatDate,
    formatDateTime,
    formatDateTimeFull,
    formatDateShort,
    formatTime,
    formatTimeFull,
    formatRelativeTime,
    // Number formatting functions
    formatNumber,
    formatCurrency,
    formatPercent,
    formatFileSize,
  }
}
