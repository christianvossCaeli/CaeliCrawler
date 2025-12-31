import { useI18n } from 'vue-i18n'
import type { SourceType, SourceStatus } from '@/types/sources'
import {
  getStatusColor as getGlobalStatusColor,
  getStatusIcon as getGlobalStatusIcon,
} from './useStatusColors'
import { useDateFormatter } from './useDateFormatter'

/**
 * Composable for source type and status helpers
 *
 * Provides consistent colors, icons, and labels across components
 * for data sources, statuses, tags, languages, and dates.
 *
 * Status colors and icons now use the centralized useStatusColors module
 * to ensure consistency across the application.
 *
 * @returns Object containing helper functions:
 * - Type helpers: getTypeColor, getTypeIcon, getTypeLabel
 * - Status helpers: getStatusColor, getStatusIcon, getStatusLabel
 * - Tag helpers: getTagColor, getTagIcon
 * - Language helpers: availableLanguages, getLanguageFlag, getLanguageName
 * - Date formatting: formatDate, formatRelativeDate
 * - URL helpers: isValidUrl, getHostname, truncateUrl
 *
 * @example
 * ```typescript
 * const { getTypeColor, formatDate } = useSourceHelpers()
 * const color = getTypeColor('WEBSITE') // 'primary'
 * const date = formatDate('2024-01-15') // '15.01.2024'
 * ```
 */
export function useSourceHelpers() {
  const { t } = useI18n()
  const { formatDate: formatDateBase, formatRelativeTime } = useDateFormatter()

  // ==========================================================================
  // Type Helpers
  // ==========================================================================

  /** Color mapping for source types (Vuetify color names) */
  const typeColors: Record<string, string> = {
    WEBSITE: 'primary',
    OPARL_API: 'success',
    RSS: 'info',
    CUSTOM_API: 'warning',
    SHAREPOINT: 'teal',
    REST_API: 'purple',
    SPARQL_API: 'deep-purple',
  }

  /** Icon mapping for source types (MDI icon names) */
  const typeIcons: Record<string, string> = {
    WEBSITE: 'mdi-web',
    OPARL_API: 'mdi-api',
    RSS: 'mdi-rss',
    CUSTOM_API: 'mdi-code-json',
    SHAREPOINT: 'mdi-microsoft-sharepoint',
    REST_API: 'mdi-cloud-sync',
    SPARQL_API: 'mdi-database-search',
  }

  /** Get Vuetify color for source type */
  const getTypeColor = (type: SourceType | string | null): string => {
    return type ? typeColors[type] || 'grey' : 'grey'
  }

  /** Get MDI icon name for source type */
  const getTypeIcon = (type: SourceType | string | null): string => {
    return type ? typeIcons[type] || 'mdi-help-circle' : 'mdi-help-circle'
  }

  /** Get localized label for source type */
  const getTypeLabel = (type: SourceType | string | null): string => {
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
      SHAREPOINT: 'SharePoint',
      REST_API: 'REST API',
      SPARQL_API: 'SPARQL API',
    }
    return fallbacks[type] || type
  }

  // ==========================================================================
  // Status Helpers (delegating to centralized useStatusColors)
  // ==========================================================================

  /** Get Vuetify color for source status - uses centralized status colors */
  const getStatusColor = (status: SourceStatus | string | null): string => {
    return getGlobalStatusColor(status)
  }

  /** Get MDI icon name for source status - uses centralized status icons */
  const getStatusIcon = (status: SourceStatus | string | null): string => {
    return getGlobalStatusIcon(status)
  }

  /** Get localized label for source status */
  const getStatusLabel = (status: SourceStatus | string | null): string => {
    if (!status) return ''
    const key = `sources.status.${status.toLowerCase()}`
    const translated = t(key)
    return translated !== key ? translated : status
  }

  // ==========================================================================
  // Tag Helpers
  // ==========================================================================

  /**
   * Geographic regions (German states)
   */
  const GEOGRAPHIC_TAGS = new Set([
    'nrw',
    'bayern',
    'baden-württemberg',
    'niedersachsen',
    'hessen',
    'sachsen',
    'rheinland-pfalz',
    'berlin',
    'schleswig-holstein',
    'brandenburg',
    'sachsen-anhalt',
    'thüringen',
    'hamburg',
    'mecklenburg-vorpommern',
    'saarland',
    'bremen',
    'nordrhein-westfalen',
  ])

  /**
   * Country tags
   */
  const COUNTRY_TAGS = new Set([
    'deutschland',
    'österreich',
    'schweiz',
    'de',
    'at',
    'ch',
  ])

  /**
   * Administrative level tags
   */
  const ADMIN_TAGS = new Set([
    'kommunal',
    'gemeinde',
    'stadt',
    'landkreis',
    'landesebene',
    'kreis',
  ])

  /**
   * Get color for a tag based on its category
   */
  const getTagColor = (tag: string): string => {
    const tagLower = tag?.toLowerCase() || ''
    // Geographic regions (German states)
    if (GEOGRAPHIC_TAGS.has(tagLower)) {
      return 'blue'
    }
    // Countries
    if (COUNTRY_TAGS.has(tagLower)) {
      return 'indigo'
    }
    // Source types / administrative levels
    if (ADMIN_TAGS.has(tagLower)) {
      return 'green'
    }
    return 'grey' // Default for custom tags
  }

  /**
   * Get icon for a tag
   */
  const getTagIcon = (tag: string): string => {
    const tagLower = tag?.toLowerCase() || ''
    if (GEOGRAPHIC_TAGS.has(tagLower)) {
      return 'mdi-map-marker'
    }
    if (COUNTRY_TAGS.has(tagLower)) {
      return 'mdi-flag'
    }
    if (ADMIN_TAGS.has(tagLower)) {
      return 'mdi-office-building'
    }
    return 'mdi-tag'
  }

  // ==========================================================================
  // Language Helpers
  // ==========================================================================

  interface LanguageInfo {
    code: string
    name: string
    flag: string
  }

  const availableLanguages: LanguageInfo[] = [
    { code: 'de', name: 'Deutsch', flag: '🇩🇪' },
    { code: 'en', name: 'English', flag: '🇬🇧' },
    { code: 'fr', name: 'Français', flag: '🇫🇷' },
    { code: 'nl', name: 'Nederlands', flag: '🇳🇱' },
    { code: 'it', name: 'Italiano', flag: '🇮🇹' },
    { code: 'es', name: 'Español', flag: '🇪🇸' },
    { code: 'pl', name: 'Polski', flag: '🇵🇱' },
    { code: 'da', name: 'Dansk', flag: '🇩🇰' },
    { code: 'pt', name: 'Português', flag: '🇵🇹' },
    { code: 'sv', name: 'Svenska', flag: '🇸🇪' },
    { code: 'no', name: 'Norsk', flag: '🇳🇴' },
    { code: 'fi', name: 'Suomi', flag: '🇫🇮' },
    { code: 'cs', name: 'Čeština', flag: '🇨🇿' },
    { code: 'hu', name: 'Magyar', flag: '🇭🇺' },
    { code: 'ro', name: 'Română', flag: '🇷🇴' },
    { code: 'bg', name: 'Български', flag: '🇧🇬' },
    { code: 'el', name: 'Ελληνικά', flag: '🇬🇷' },
    { code: 'tr', name: 'Türkçe', flag: '🇹🇷' },
    { code: 'ru', name: 'Русский', flag: '🇷🇺' },
    { code: 'uk', name: 'Українська', flag: '🇺🇦' },
    { code: 'ar', name: 'العربية', flag: '🇸🇦' },
    { code: 'zh', name: '中文', flag: '🇨🇳' },
    { code: 'ja', name: '日本語', flag: '🇯🇵' },
    { code: 'ko', name: '한국어', flag: '🇰🇷' },
  ]

  /**
   * Get flag emoji for a language code
   */
  const getLanguageFlag = (code: string): string => {
    const lang = availableLanguages.find((l) => l.code === code)
    return lang?.flag || code.toUpperCase()
  }

  /**
   * Get language name for a language code
   */
  const getLanguageName = (code: string): string => {
    const lang = availableLanguages.find((l) => l.code === code)
    return lang?.name || code.toUpperCase()
  }

  // ==========================================================================
  // Date Formatting (delegating to centralized useDateFormatter)
  // ==========================================================================

  /**
   * Format a date string - uses centralized date formatter
   */
  const formatDate = (dateStr: string | null | undefined, formatStr = 'dd.MM.yyyy HH:mm'): string => {
    return formatDateBase(dateStr, formatStr)
  }

  /**
   * Format a date as relative time (e.g., "2 hours ago") - uses centralized formatter
   */
  const formatRelativeDate = (dateStr: string | null | undefined): string => {
    return formatRelativeTime(dateStr)
  }

  // ==========================================================================
  // URL Helpers
  // ==========================================================================

  /**
   * Validate URL format
   */
  const isValidUrl = (url: string): boolean => {
    if (!url) return false
    try {
      const parsed = new URL(url)
      return ['http:', 'https:'].includes(parsed.protocol)
    } catch {
      return false
    }
  }

  /**
   * Extract hostname from URL
   */
  const getHostname = (url: string): string => {
    try {
      return new URL(url).hostname
    } catch {
      return url
    }
  }

  /**
   * Truncate URL for display
   */
  const truncateUrl = (url: string, maxLength = 50): string => {
    if (!url || url.length <= maxLength) return url
    try {
      const parsed = new URL(url)
      const path = parsed.pathname + parsed.search
      if (path.length > maxLength - parsed.hostname.length - 5) {
        return `${parsed.hostname}/...`
      }
      return url.substring(0, maxLength - 3) + '...'
    } catch {
      return url.substring(0, maxLength - 3) + '...'
    }
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
    // Tag helpers
    getTagColor,
    getTagIcon,
    // Language helpers
    availableLanguages,
    getLanguageFlag,
    getLanguageName,
    // Date formatting
    formatDate,
    formatRelativeDate,
    // URL helpers
    isValidUrl,
    getHostname,
    truncateUrl,
  }
}
