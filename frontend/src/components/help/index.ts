/**
 * Help components package - Modularized help view components.
 *
 * This package provides:
 * - HelpCard: Generic section wrapper with title, icon, and color
 * - HelpTableOfContents: Navigation sidebar
 * - HelpApiTable: API endpoint documentation table
 * - Section components for each help topic
 *
 * Data exports:
 * - helpSections: Section metadata (id, title, icon, color)
 * - apiGroups: API endpoint groups for documentation
 * - methodColors: HTTP method color mapping
 */

// Core Components
export { default as HelpCard } from './HelpCard.vue'
export { default as HelpTableOfContents } from './HelpTableOfContents.vue'
export { default as HelpApiTable } from './HelpApiTable.vue'

// Section Components
export { default as HelpIntroSection } from './HelpIntroSection.vue'
export { default as HelpQuickstartSection } from './HelpQuickstartSection.vue'
export { default as HelpDashboardSection } from './HelpDashboardSection.vue'
export { default as HelpSmartQuerySection } from './HelpSmartQuerySection.vue'
export { default as HelpCategoriesSection } from './HelpCategoriesSection.vue'
export { default as HelpSourcesSection } from './HelpSourcesSection.vue'
export { default as HelpCrawlerSection } from './HelpCrawlerSection.vue'
export { default as HelpDocumentsSection } from './HelpDocumentsSection.vue'
export { default as HelpMunicipalitiesSection } from './HelpMunicipalitiesSection.vue'
export { default as HelpEntityFacetSection } from './HelpEntityFacetSection.vue'
export { default as HelpFacetTypeAdminSection } from './HelpFacetTypeAdminSection.vue'
export { default as HelpResultsSection } from './HelpResultsSection.vue'
export { default as HelpExportSection } from './HelpExportSection.vue'
export { default as HelpNotificationsSection } from './HelpNotificationsSection.vue'
export { default as HelpFavoritesSection } from './HelpFavoritesSection.vue'
export { default as HelpApiSection } from './HelpApiSection.vue'
export { default as HelpTipsSection } from './HelpTipsSection.vue'
export { default as HelpSecuritySection } from './HelpSecuritySection.vue'
export { default as HelpTroubleshootingSection } from './HelpTroubleshootingSection.vue'
export { default as HelpAttachmentsSection } from './HelpAttachmentsSection.vue'
export { default as HelpAiAssistantSection } from './HelpAiAssistantSection.vue'
export { default as HelpUserManagementSection } from './HelpUserManagementSection.vue'
export { default as HelpAuditLogSection } from './HelpAuditLogSection.vue'
export { default as HelpAiSourceDiscoverySection } from './HelpAiSourceDiscoverySection.vue'
export { default as HelpDataSourceTagsSection } from './HelpDataSourceTagsSection.vue'
export { default as HelpEntityMapViewSection } from './HelpEntityMapViewSection.vue'
export { default as HelpFacetHistorySection } from './HelpFacetHistorySection.vue'

// Data and types
export {
  helpSections,
  helpSectionGroups,
  apiGroups,
  methodColors,
  type HelpSection,
  type HelpSectionGroup,
  type ApiEndpoint,
  type ApiGroup,
} from './helpSections'
