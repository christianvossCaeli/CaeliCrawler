/**
 * Sources Components
 *
 * Export all source-related components for easy imports.
 *
 * ## Main Components
 * - SourcesSidebar: Filter sidebar
 * - SourceFormDialog: Create/edit source
 * - SourcesBulkImportDialog: CSV bulk import
 * - ApiImportDialog: API import wizard
 * - AiDiscoveryDialog: AI-powered discovery
 *
 * ## Utility Components
 * - SourcesActiveFilters: Active filter chips display
 * - SourcesTableActions: Row action buttons
 * - SourcesSkeleton: Loading skeleton
 * - CategoryInfoDialog: Category details modal
 *
 * ## Chip Components (from ./chips)
 * - SourceTypeChip, SourceStatusChip, TagChip, ConfidenceChip
 *
 * ## Sub-Components (from ./ai-discovery, ./source-form)
 * - AI Discovery phases and dialogs
 * - Source form sections
 */

// Main dialogs and components
export { default as SourcesSidebar } from './SourcesSidebar.vue'
export { default as SharePointConfig } from './SharePointConfig.vue'
export { default as SourceFormDialog } from './SourceFormDialog.vue'
export { default as SourcesBulkImportDialog } from './SourcesBulkImportDialog.vue'
export { default as SourcesDeleteDialog } from './SourcesDeleteDialog.vue'
export { default as ApiImportDialog } from './ApiImportDialog.vue'
export { default as AiDiscoveryDialog } from './AiDiscoveryDialog.vue'
export { default as SourcesActiveFilters } from './SourcesActiveFilters.vue'
export { default as SourcesTableActions } from './SourcesTableActions.vue'
export { default as SourcesSkeleton } from './SourcesSkeleton.vue'
export { default as CategoryInfoDialog } from './CategoryInfoDialog.vue'

// Reusable chip components
export {
  SourceTypeChip,
  SourceStatusChip,
  TagChip,
  ConfidenceChip,
} from './chips'

// AI Discovery sub-components
export * from './ai-discovery'

// Source form sub-components
export * from './source-form'
