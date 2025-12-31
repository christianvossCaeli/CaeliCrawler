import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { format } from 'date-fns'
import { de, enUS } from 'date-fns/locale'

export function useDateFormatter() {
  const { locale, t } = useI18n()
  const dateLocale = computed(() => (locale.value === 'de' ? de : enUS))

  function formatDate(
    dateValue: string | Date | null | undefined,
    formatStr = 'dd.MM.yyyy HH:mm'
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
   * Format a date as relative time (e.g., "2 hours ago")
   */
  function formatRelativeTime(dateStr: string | null | undefined): string {
    if (!dateStr) return ''
    try {
      const date = new Date(dateStr)
      const now = new Date()
      const diffMs = now.getTime() - date.getTime()
      const diffMins = Math.floor(diffMs / 60000)
      const diffHours = Math.floor(diffMs / 3600000)
      const diffDays = Math.floor(diffMs / 86400000)

      if (diffMins < 1) return t('common.justNow', 'just now')
      if (diffMins < 60) return t('common.minutesAgo', { count: diffMins }, `${diffMins} min ago`)
      if (diffHours < 24) return t('common.hoursAgo', { count: diffHours }, `${diffHours}h ago`)
      if (diffDays < 7) return t('common.daysAgo', { count: diffDays }, `${diffDays}d ago`)
      return formatDate(dateStr, 'dd.MM.yyyy')
    } catch {
      return dateStr
    }
  }

  return {
    dateLocale,
    formatDate,
    formatRelativeTime,
  }
}
