/**
 * Info Box Configuration
 *
 * LocalStorage keys for tracking which info boxes have been dismissed.
 */

export const INFO_BOX_STORAGE_KEYS = {
  // Main views
  DASHBOARD: 'infoBox.dashboard.hidden',
  ENTITIES: 'infoBox.entities.hidden',
  CATEGORIES: 'infoBox.categories.hidden',
  SOURCES: 'infoBox.sources.hidden',
  CRAWLER: 'infoBox.crawler.hidden',
  DOCUMENTS: 'infoBox.documents.hidden',
  RESULTS: 'infoBox.results.hidden',
  SMART_QUERY: 'infoBox.smartQuery.hidden',
  EXPORT: 'infoBox.export.hidden',
  NOTIFICATIONS: 'infoBox.notifications.hidden',
  // Types management
  ENTITY_TYPES: 'infoBox.entityTypes.hidden',
  FACET_TYPES: 'infoBox.facetTypes.hidden',
  // Utilities
  FAVORITES: 'infoBox.favorites.hidden',
  SUMMARIES: 'infoBox.summaries.hidden',
  // Admin views
  USERS: 'infoBox.users.hidden',
  AUDIT_LOG: 'infoBox.auditLog.hidden',
  LLM_USAGE: 'infoBox.llmUsage.hidden',
  MODEL_PRICING: 'infoBox.modelPricing.hidden',
  AI_CONFIG: 'infoBox.aiConfig.hidden',
} as const

export type InfoBoxStorageKey = (typeof INFO_BOX_STORAGE_KEYS)[keyof typeof INFO_BOX_STORAGE_KEYS]
