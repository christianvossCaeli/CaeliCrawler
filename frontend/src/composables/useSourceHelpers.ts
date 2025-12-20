import { useI18n } from 'vue-i18n'

/**
 * Composable for source type and status helpers
 * Provides consistent colors, icons, and labels across components
 */
export function useSourceHelpers() {
  const { t } = useI18n()

  // Type helpers
  const typeColors: Record<string, string> = {
    WEBSITE: 'primary',
    OPARL_API: 'success',
    RSS: 'info',
    CUSTOM_API: 'warning',
  }

  const typeIcons: Record<string, string> = {
    WEBSITE: 'mdi-web',
    OPARL_API: 'mdi-api',
    RSS: 'mdi-rss',
    CUSTOM_API: 'mdi-code-json',
  }

  const getTypeColor = (type: string | null): string => {
    return type ? typeColors[type] || 'grey' : 'grey'
  }

  const getTypeIcon = (type: string | null): string => {
    return type ? typeIcons[type] || 'mdi-help-circle' : 'mdi-help-circle'
  }

  const getTypeLabel = (type: string | null): string => {
    if (!type) return ''
    // Try localized version first, fallback to readable format
    const key = `sources.types.${type}`
    const translated = t(key)
    if (translated !== key) {
      return translated
    }
    // Fallback: Convert OPARL_API -> OParl API, CUSTOM_API -> Custom API
    const fallbacks: Record<string, string> = {
      WEBSITE: 'Website',
      OPARL_API: 'OParl API',
      RSS: 'RSS Feed',
      CUSTOM_API: 'Custom API',
    }
    return fallbacks[type] || type
  }

  // Status helpers
  const statusColors: Record<string, string> = {
    ACTIVE: 'success',
    PENDING: 'warning',
    ERROR: 'error',
    PAUSED: 'grey',
  }

  const statusIcons: Record<string, string> = {
    ACTIVE: 'mdi-check-circle',
    PENDING: 'mdi-clock-outline',
    ERROR: 'mdi-alert-circle',
    PAUSED: 'mdi-pause-circle',
  }

  const getStatusColor = (status: string | null): string => {
    return status ? statusColors[status] || 'grey' : 'grey'
  }

  const getStatusIcon = (status: string | null): string => {
    return status ? statusIcons[status] || 'mdi-help-circle' : 'mdi-help-circle'
  }

  const getStatusLabel = (status: string | null): string => {
    if (!status) return ''
    const key = `sources.status.${status.toLowerCase()}`
    const translated = t(key)
    return translated !== key ? translated : status
  }

  return {
    // Type helpers
    getTypeColor,
    getTypeIcon,
    getTypeLabel,
    // Status helpers
    getStatusColor,
    getStatusIcon,
    getStatusLabel,
  }
}
