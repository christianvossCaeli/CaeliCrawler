/**
 * Help components package - Modularized help view components.
 *
 * This package provides:
 * - HelpCard: Generic section wrapper with title, icon, and color
 * - HelpTableOfContents: Navigation sidebar
 * - HelpApiTable: API endpoint documentation table
 * - HelpApiSection: Complete API reference section
 * - HelpSecuritySection: Security & authentication documentation
 * - HelpTroubleshootingSection: Troubleshooting guide
 *
 * Data exports:
 * - helpSections: Section metadata (id, title, icon, color)
 * - apiGroups: API endpoint groups for documentation
 * - methodColors: HTTP method color mapping
 */

// Components
export { default as HelpCard } from './HelpCard.vue'
export { default as HelpTableOfContents } from './HelpTableOfContents.vue'
export { default as HelpApiTable } from './HelpApiTable.vue'
export { default as HelpApiSection } from './HelpApiSection.vue'
export { default as HelpSecuritySection } from './HelpSecuritySection.vue'
export { default as HelpTroubleshootingSection } from './HelpTroubleshootingSection.vue'

// Data and types
export {
  helpSections,
  apiGroups,
  methodColors,
  type HelpSection,
  type ApiEndpoint,
  type ApiGroup,
} from './helpSections'
