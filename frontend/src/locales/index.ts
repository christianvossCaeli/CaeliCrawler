/**
 * Vue I18n Configuration for CaeliCrawler
 *
 * Supports German (default) and English locales.
 * Language preference is stored per user in the database.
 */

import { createI18n } from 'vue-i18n'

// Deep merge helper for nested objects
function deepMerge<T extends Record<string, unknown>>(...objects: T[]): T {
  const result = {} as T
  for (const obj of objects) {
    for (const key in obj) {
      if (Object.prototype.hasOwnProperty.call(obj, key)) {
        const value = obj[key]
        if (value && typeof value === 'object' && !Array.isArray(value)) {
          result[key] = deepMerge(
            (result[key] || {}) as Record<string, unknown>,
            value as Record<string, unknown>
          ) as T[Extract<keyof T, string>]
        } else {
          result[key] = value as T[Extract<keyof T, string>]
        }
      }
    }
  }
  return result
}

// German locale modules
import deCommon from './de/common.json'
import deDashboard from './de/dashboard.json'
import deCrawler from './de/crawler.json'
import deDocuments from './de/documents.json'
import deResults from './de/results.json'
import deSources from './de/sources.json'
import deCategories from './de/categories.json'
import deEntities from './de/entities.json'
import deExport from './de/export.json'
import deSmartQuery from './de/smartQuery.json'
import deNotifications from './de/notifications.json'
import deAdmin from './de/admin.json'
import deHelpIntro from './de/help/intro.json'
import deHelpViews from './de/help/views.json'
import deHelpFeatures from './de/help/features.json'
import deHelpAdvanced from './de/help/advanced.json'
import deHelpUi from './de/help/ui.json'
import deAssistant from './de/assistant.json'
import deMisc from './de/misc.json'
import deFavorites from './de/favorites.json'
import deCrawlPresets from './de/crawlPresets.json'
import deSummaries from './de/summaries.json'

// English locale modules
import enCommon from './en/common.json'
import enDashboard from './en/dashboard.json'
import enCrawler from './en/crawler.json'
import enDocuments from './en/documents.json'
import enResults from './en/results.json'
import enSources from './en/sources.json'
import enCategories from './en/categories.json'
import enEntities from './en/entities.json'
import enExport from './en/export.json'
import enSmartQuery from './en/smartQuery.json'
import enNotifications from './en/notifications.json'
import enAdmin from './en/admin.json'
import enHelpIntro from './en/help/intro.json'
import enHelpViews from './en/help/views.json'
import enHelpFeatures from './en/help/features.json'
import enHelpAdvanced from './en/help/advanced.json'
import enHelpUi from './en/help/ui.json'
import enAssistant from './en/assistant.json'
import enMisc from './en/misc.json'
import enFavorites from './en/favorites.json'
import enCrawlPresets from './en/crawlPresets.json'
import enSummaries from './en/summaries.json'

// Merge German modules
const de = {
  ...deCommon,
  ...deDashboard,
  ...deCrawler,
  ...deDocuments,
  ...deResults,
  ...deSources,
  ...deCategories,
  ...deEntities,
  ...deExport,
  ...deSmartQuery,
  ...deNotifications,
  ...deAdmin,
  // Merge help sub-modules using deep merge to preserve nested objects
  help: deepMerge<Record<string, unknown>>(
    (deHelpIntro.help || {}) as Record<string, unknown>,
    (deHelpViews.help || {}) as Record<string, unknown>,
    (deHelpFeatures.help || {}) as Record<string, unknown>,
    (deHelpAdvanced.help || {}) as Record<string, unknown>,
    (deHelpUi.help || {}) as Record<string, unknown>,
  ),
  ...deAssistant,
  ...deMisc,
  ...deFavorites,
  ...deCrawlPresets,
  ...deSummaries,
}

// Merge English modules
const en = {
  ...enCommon,
  ...enDashboard,
  ...enCrawler,
  ...enDocuments,
  ...enResults,
  ...enSources,
  ...enCategories,
  ...enEntities,
  ...enExport,
  ...enSmartQuery,
  ...enNotifications,
  ...enAdmin,
  // Merge help sub-modules using deep merge to preserve nested objects
  help: deepMerge<Record<string, unknown>>(
    (enHelpIntro.help || {}) as Record<string, unknown>,
    (enHelpViews.help || {}) as Record<string, unknown>,
    (enHelpFeatures.help || {}) as Record<string, unknown>,
    (enHelpAdvanced.help || {}) as Record<string, unknown>,
    (enHelpUi.help || {}) as Record<string, unknown>,
  ),
  ...enAssistant,
  ...enMisc,
  ...enFavorites,
  ...enCrawlPresets,
  ...enSummaries,
}

export type SupportedLocale = 'de' | 'en'

export const SUPPORTED_LOCALES: SupportedLocale[] = ['de', 'en']
export const DEFAULT_LOCALE: SupportedLocale = 'de'

export const LOCALE_NAMES: Record<SupportedLocale, string> = {
  de: 'Deutsch',
  en: 'English',
}

/**
 * Get the initial locale from localStorage or use default
 */
function getInitialLocale(): SupportedLocale {
  const saved = localStorage.getItem('caeli-language')
  if (saved && SUPPORTED_LOCALES.includes(saved as SupportedLocale)) {
    return saved as SupportedLocale
  }
  return DEFAULT_LOCALE
}

export const i18n = createI18n({
  legacy: false, // Use Composition API mode
  locale: getInitialLocale(),
  fallbackLocale: DEFAULT_LOCALE,
  messages: {
    de,
    en,
  },
  // Missing translation warnings only in development
  missingWarn: import.meta.env.DEV,
  fallbackWarn: import.meta.env.DEV,
})

/**
 * Set the current locale and persist to localStorage
 */
export function setLocale(locale: SupportedLocale): void {
  if (SUPPORTED_LOCALES.includes(locale)) {
    i18n.global.locale.value = locale
    localStorage.setItem('caeli-language', locale)
    // Set HTML lang attribute for accessibility
    document.documentElement.lang = locale
  }
}

/**
 * Get the current locale
 */
export function getLocale(): SupportedLocale {
  return i18n.global.locale.value as SupportedLocale
}

export default i18n
