/**
 * Facets Composables Index
 *
 * Re-exports all facet-related composables and provides a facade
 * for backwards compatibility with the original useEntityFacets.
 */

import { type Ref, type ComputedRef } from 'vue'
import type { Entity, EntityType } from '@/stores/entity'

// Re-export individual composables
export { useFacetCrud } from './useFacetCrud'
export { useFacetSearch } from './useFacetSearch'
export { useFacetBulkOps } from './useFacetBulkOps'
export { useFacetEntityLinking } from './useFacetEntityLinking'
export { useFacetEnrichment } from './useFacetEnrichment'
export { useFacetSourceDetails } from './useFacetSourceDetails'
export { useFacetHelpers } from './useFacetHelpers'

// Re-export types
export * from './types'

// Import for facade
import { useFacetCrud } from './useFacetCrud'
import { useFacetSearch } from './useFacetSearch'
import { useFacetBulkOps } from './useFacetBulkOps'
import { useFacetEntityLinking } from './useFacetEntityLinking'
import { useFacetEnrichment } from './useFacetEnrichment'
import { useFacetSourceDetails } from './useFacetSourceDetails'
import { useFacetHelpers } from './useFacetHelpers'

/**
 * Facade composable for backwards compatibility.
 * Combines all facet-related composables into a single interface.
 *
 * @deprecated Consider using individual composables for better modularity.
 */
export function useEntityFacets(
  entity: Ref<Entity | null> | ComputedRef<Entity | null> | Entity | null,
  entityType: Ref<EntityType | null> | ComputedRef<EntityType | null> | EntityType | null,
  onFacetsSummaryUpdate: () => Promise<void>,
) {
  // Initialize all sub-composables
  const crud = useFacetCrud(entity, entityType, onFacetsSummaryUpdate)
  const search = useFacetSearch(entity)
  const bulk = useFacetBulkOps(onFacetsSummaryUpdate, () => {
    search.expandedFacetValues.value = {}
  })
  const entityLinking = useFacetEntityLinking(entity, onFacetsSummaryUpdate)
  const enrichment = useFacetEnrichment(entity)
  const sourceDetails = useFacetSourceDetails()
  const helpers = useFacetHelpers()

  // Return combined interface for backwards compatibility
  return {
    // Core State (from crud)
    selectedFacetGroup: crud.selectedFacetGroup,
    facetDetails: crud.facetDetails,
    facetToDelete: crud.facetToDelete,
    editingFacet: crud.editingFacet,
    editingFacetValue: crud.editingFacetValue,
    editingFacetTextValue: crud.editingFacetTextValue,
    editingFacetSchema: crud.editingFacetSchema,
    editingFacetTypeName: crud.editingFacetTypeName,
    newFacet: crud.newFacet,
    savingFacet: crud.savingFacet,
    deletingFacet: crud.deletingFacet,

    // Search & Expansion State (from search)
    facetSearchQuery: search.facetSearchQuery,
    expandedFacets: search.expandedFacets,
    expandedFacetValues: search.expandedFacetValues,
    loadingMoreFacets: search.loadingMoreFacets,

    // Bulk Mode State (from bulk)
    bulkMode: bulk.bulkMode,
    selectedFacetIds: bulk.selectedFacetIds,
    bulkActionLoading: bulk.bulkActionLoading,

    // Entity Linking State (from entityLinking)
    facetToLink: entityLinking.facetToLink,
    selectedTargetEntityId: entityLinking.selectedTargetEntityId,
    entitySearchQuery: entityLinking.entitySearchQuery,
    entitySearchResults: entityLinking.entitySearchResults,
    searchingEntities: entityLinking.searchingEntities,
    savingEntityLink: entityLinking.savingEntityLink,

    // Enrichment State (from enrichment)
    enrichmentSources: enrichment.enrichmentSources,
    loadingEnrichmentSources: enrichment.loadingEnrichmentSources,
    startingEnrichment: enrichment.startingEnrichment,
    selectedEnrichmentSources: enrichment.selectedEnrichmentSources,
    hasAnyEnrichmentSource: enrichment.hasAnyEnrichmentSource,

    // Source Details State (from sourceDetails)
    selectedSourceFacet: sourceDetails.selectedSourceFacet,

    // Computed (from crud)
    applicableFacetTypes: crud.applicableFacetTypes,
    selectedFacetTypeForForm: crud.selectedFacetTypeForForm,

    // Helper Functions (from helpers)
    formatDate: helpers.formatDate,
    formatEnrichmentDate: helpers.formatEnrichmentDate,
    getConfidenceColor: helpers.getConfidenceColor,
    getFacetSourceColor: helpers.getFacetSourceColor,
    getFacetSourceIcon: helpers.getFacetSourceIcon,

    // Search & Filter Functions (from search)
    getDisplayedFacets: search.getDisplayedFacets,
    canLoadMore: search.canLoadMore,
    getRemainingCount: search.getRemainingCount,
    isExpanded: search.isExpanded,
    loadMoreFacets: search.loadMoreFacets,
    collapseFacets: search.collapseFacets,
    toggleFacetExpand: search.toggleFacetExpand,

    // Bulk Actions (from bulk)
    toggleFacetSelection: bulk.toggleFacetSelection,
    bulkVerify: bulk.bulkVerify,
    bulkDelete: bulk.bulkDelete,
    resetBulkMode: bulk.resetBulkMode,

    // Core Facet Operations (from crud)
    onFacetTypeChange: crud.onFacetTypeChange,
    resetAddFacetForm: crud.resetAddFacetForm,
    openAddFacetValueDialog: crud.openAddFacetValueDialog,
    saveFacetValue: crud.saveFacetValue,
    verifyFacet: crud.verifyFacet,
    loadFacetDetails: crud.loadFacetDetails,
    openEditFacetDialog: crud.openEditFacetDialog,
    saveEditedFacet: crud.saveEditedFacet,
    confirmDeleteFacet: crud.confirmDeleteFacet,
    deleteSingleFacet: crud.deleteSingleFacet,

    // Source Details (from sourceDetails)
    openSourceDetails: sourceDetails.openSourceDetails,
    closeSourceDetails: sourceDetails.closeSourceDetails,

    // Entity Linking (from entityLinking)
    navigateToTargetEntity: entityLinking.navigateToTargetEntity,
    openEntityLinkDialog: entityLinking.openEntityLinkDialog,
    closeEntityLinkDialog: entityLinking.closeEntityLinkDialog,
    searchEntities: entityLinking.searchEntities,
    saveEntityLink: entityLinking.saveEntityLink,
    unlinkEntity: entityLinking.unlinkEntity,

    // Enrichment (from enrichment)
    loadEnrichmentSources: enrichment.loadEnrichmentSources,
    onEnrichmentMenuOpen: enrichment.onEnrichmentMenuOpen,
    startEnrichmentAnalysis: enrichment.startEnrichmentAnalysis,
    stopEnrichmentTaskPolling: enrichment.stopEnrichmentTaskPolling,
  }
}
