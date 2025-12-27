import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { format } from 'date-fns'
import { de, enUS } from 'date-fns/locale'

export function useDateFormatter() {
  const { locale } = useI18n()
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

  return {
    dateLocale,
    formatDate,
  }
}
