/**
 * Entity Components Barrel Export
 *
 * Provides centralized exports for all entity-related components.
 * Import from '@/components/entity' for cleaner imports.
 *
 * @example
 * ```typescript
 * import { EntityFacetsTab, AddFacetDialog } from '@/components/entity'
 * ```
 */

// Dialogs
export { default as AddFacetDialog } from './AddFacetDialog.vue'
export { default as AddRelationDialog } from './AddRelationDialog.vue'
export { default as EntityEditDialog } from './EntityEditDialog.vue'
export { default as EntityExportDialog } from './EntityExportDialog.vue'
export { default as EntityNotesDialog } from './EntityNotesDialog.vue'
export { default as EntityPysisEnrichmentDialog } from './EntityPysisEnrichmentDialog.vue'
export { default as FacetDetailsDialog } from './FacetDetailsDialog.vue'
export { default as LinkDataSourceDialog } from './LinkDataSourceDialog.vue'
export { default as SourceDetailsDialog } from './SourceDetailsDialog.vue'
export { default as EntityDialogsManager } from './EntityDialogsManager.vue'

// Tabs
export { default as EntityApiDataTab } from './EntityApiDataTab.vue'
export { default as EntityAttachmentsTab } from './EntityAttachmentsTab.vue'
export { default as EntityConnectionsTab } from './EntityConnectionsTab.vue'
export { default as EntityDocumentsTab } from './EntityDocumentsTab.vue'
export { default as EntityExtractionsTab } from './EntityExtractionsTab.vue'
export { default as EntityFacetsTab } from './EntityFacetsTab.vue'
export { default as EntityReferencedByTab } from './EntityReferencedByTab.vue'
export { default as EntitySourcesTab } from './EntitySourcesTab.vue'

// Layout & Navigation
export { default as EntityBreadcrumbs } from './EntityBreadcrumbs.vue'
export { default as EntityDetailHeader } from './EntityDetailHeader.vue'
export { default as EntityTabsNavigation } from './EntityTabsNavigation.vue'

// Managers & Utilities
export { default as EntityDataSourceManager } from './EntityDataSourceManager.vue'
export { default as EntityDetailSkeleton } from './EntityDetailSkeleton.vue'
export { default as EntityLoadingOverlay } from './EntityLoadingOverlay.vue'
