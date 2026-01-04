<template>
  <div>
    <!-- Search Bar for Facets + PySis Enrich Button -->
    <v-card v-if="facetsSummary?.facets_by_type?.length" class="mb-4" variant="outlined">
      <v-card-text class="py-2">
        <div class="d-flex align-center ga-3">
          <v-text-field
            v-model="facetSearchQuery"
            prepend-inner-icon="mdi-magnify"
            :label="t('entityDetail.searchProperties')"
            clearable
            hide-details
            density="compact"
            variant="plain"
            class="flex-grow-1"
          ></v-text-field>

          <!-- Enrichment Dropdown Menu -->
          <FacetsEnrichmentMenu
            v-model:open="enrichmentMenuOpen"
            v-model:selected-sources="selectedEnrichmentSources"
            :visible="canEdit && !!entityType?.supports_pysis"
            :sources="enrichmentSources"
            :loading="loadingEnrichmentSources"
            :starting="startingEnrichment"
            @update:open="onEnrichmentMenuOpen($event)"
            @start="handleStartEnrichment"
          />
        </div>
      </v-card-text>
    </v-card>

    <v-row>
      <v-col
        v-for="facetGroup in facetsSummary?.facets_by_type || []"
        :key="facetGroup.facet_type_id"
        cols="12"
      >
        <FacetGroupCard
          :facet-group="facetGroup"
          :entity-id="entity?.id || ''"
          :displayed-facets="getDisplayedFacets(facetGroup)"
          :selected-facet-ids="selectedFacetIds"
          :is-expanded="expandedFacets.includes(facetGroup.facet_type_slug)"
          :bulk-mode="bulkMode"
          :bulk-action-loading="bulkActionLoading"
          :can-load-more="canLoadMore(facetGroup)"
          :is-loaded-more="isExpanded(facetGroup)"
          :remaining-count="getRemainingCount(facetGroup)"
          :loading-more="loadingMoreFacets[facetGroup.facet_type_slug] || false"
          :can-edit="canEdit"
          @add-value="$emit('add-facet-value', $event)"
          @toggle-expand="toggleFacetExpand(facetGroup.facet_type_slug)"
          @toggle-selection="toggleFacetSelection($event)"
          @navigate-to-entity="navigateToTargetEntity($event)"
          @open-link-dialog="handleOpenEntityLinkDialog($event)"
          @unlink-entity="unlinkEntity($event)"
          @open-source-details="handleOpenSourceDetails($event)"
          @verify="verifyFacet($event)"
          @edit="handleOpenEditFacetDialog($event, facetGroup)"
          @delete="handleConfirmDeleteFacet($event)"
          @load-more="loadMoreFacets(facetGroup)"
          @collapse="collapseFacets(facetGroup)"
          @toggle-bulk-mode="bulkMode = !bulkMode"
          @bulk-verify="bulkVerify"
          @bulk-delete="bulkDeleteConfirm = true"
          @facets-updated="$emit('facets-updated')"
        />
      </v-col>
    </v-row>

    <!-- Empty State -->
    <FacetsEmptyState
      :has-facets="!!(facetsSummary?.facets_by_type?.length)"
      :search-query="facetSearchQuery"
      :has-search-results="hasSearchResults"
      :can-edit="canEdit"
      @add-facet="$emit('add-facet')"
      @switch-tab="$emit('switch-tab', $event)"
      @clear-search="facetSearchQuery = ''"
    />

    <!-- Bulk Delete Confirm Dialog -->
    <ConfirmDialog
      v-model="bulkDeleteConfirm"
      :title="t('entityDetail.bulkDeleteTitle')"
      :message="t('entityDetail.bulkDeleteMessage', { count: selectedFacetIds.length })"
      :confirm-text="t('common.delete')"
      confirm-color="error"
      :loading="bulkActionLoading"
      @confirm="handleBulkDelete"
    />

    <!-- Single Facet Delete Confirm Dialog -->
    <ConfirmDialog
      v-model="singleDeleteConfirm"
      :title="t('entityDetail.deleteFacetTitle')"
      :message="t('entityDetail.deleteFacetMessage')"
      :confirm-text="t('common.delete')"
      confirm-color="error"
      :loading="deletingFacet"
      @confirm="handleDeleteSingleFacet"
    />

    <!-- Edit Facet Dialog -->
    <EditFacetDialog
      v-model="editFacetDialog"
      v-model:value="editingFacetValue"
      v-model:text-value="editingFacetTextValue"
      :schema="editingFacetSchema"
      :facet-type-name="editingFacetTypeName"
      :saving="savingFacet"
      @save="handleSaveEditedFacet"
    />

    <!-- Source Details Dialog -->
    <SourceDetailsDialog
      v-model="sourceDetailsDialog"
      :source-facet="selectedSourceFacet"
    />

    <!-- Entity Link Dialog -->
    <EntityLinkDialog
      v-model="entityLinkDialog"
      :selected-entity-id="selectedTargetEntityId"
      :search-query="entitySearchQuery"
      :search-results="entitySearchResults"
      :searching="searchingEntities"
      :saving="savingEntityLink"
      @update:selected-entity-id="selectedTargetEntityId = $event"
      @search="searchEntities($event)"
      @save="handleSaveEntityLink"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, toRef } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Entity, EntityType } from '@/stores/entity'
import type { FacetValue, FacetGroup, FacetsSummary } from '@/types/entity'
import { useEntityFacets } from '@/composables/useEntityFacets'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import SourceDetailsDialog from '@/components/entity/SourceDetailsDialog.vue'
import {
  FacetGroupCard,
  FacetsEnrichmentMenu,
  FacetsEmptyState,
  EntityLinkDialog,
  EditFacetDialog,
} from '@/components/entity/facets'

// =============================================================================
// Props & Emits
// =============================================================================

const props = withDefaults(defineProps<{
  entity: Entity | null
  entityType: EntityType | null
  facetsSummary: FacetsSummary | null
  canEdit?: boolean
}>(), {
  canEdit: true,
})

const emit = defineEmits<{
  (e: 'facets-updated'): void
  (e: 'add-facet'): void
  (e: 'add-facet-value', facetGroup: FacetGroup): void
  (e: 'switch-tab', tab: string): void
  (e: 'enrichment-started', taskId: string): void
}>()

const { t } = useI18n()

// =============================================================================
// Composable
// =============================================================================

const entityRef = toRef(props, 'entity')
const entityTypeRef = toRef(props, 'entityType')

const facets = useEntityFacets(entityRef, entityTypeRef, async () => {
  emit('facets-updated')
})

// Destructure composable state and methods
const {
  // Core State
  editingFacetValue,
  editingFacetTextValue,
  editingFacetSchema,
  editingFacetTypeName,
  savingFacet,
  deletingFacet,

  // Search & Expansion State
  facetSearchQuery,
  expandedFacets,
  loadingMoreFacets,

  // Bulk Mode State
  bulkMode,
  selectedFacetIds,
  bulkActionLoading,

  // Entity Linking State
  selectedTargetEntityId,
  entitySearchQuery,
  entitySearchResults,
  searchingEntities,
  savingEntityLink,

  // Enrichment State
  enrichmentSources,
  loadingEnrichmentSources,
  startingEnrichment,
  selectedEnrichmentSources,

  // Source Details State
  selectedSourceFacet,

  // Search & Filter Functions
  getDisplayedFacets,
  canLoadMore,
  getRemainingCount,
  isExpanded,
  loadMoreFacets,
  collapseFacets,
  toggleFacetExpand,

  // Bulk Actions
  toggleFacetSelection,
  bulkVerify,
  bulkDelete,

  // Core Facet Operations
  verifyFacet,
  openEditFacetDialog,
  saveEditedFacet,
  confirmDeleteFacet,
  deleteSingleFacet,

  // Source Details
  openSourceDetails,

  // Entity Linking
  navigateToTargetEntity,
  openEntityLinkDialog,
  searchEntities,
  saveEntityLink,
  unlinkEntity,

  // Enrichment
  onEnrichmentMenuOpen,
  startEnrichmentAnalysis,
} = facets

// =============================================================================
// Dialog State (UI concerns)
// =============================================================================

const enrichmentMenuOpen = ref(false)
const bulkDeleteConfirm = ref(false)
const singleDeleteConfirm = ref(false)
const editFacetDialog = ref(false)
const sourceDetailsDialog = ref(false)
const entityLinkDialog = ref(false)

// =============================================================================
// Computed
// =============================================================================

const hasSearchResults = computed(() => {
  if (!facetSearchQuery.value) return true
  for (const group of props.facetsSummary?.facets_by_type || []) {
    if (getDisplayedFacets(group).length > 0) return true
  }
  return false
})

// =============================================================================
// Handlers
// =============================================================================

async function handleStartEnrichment() {
  const taskId = await startEnrichmentAnalysis()
  if (taskId) {
    enrichmentMenuOpen.value = false
    emit('enrichment-started', taskId)
  }
}

function handleOpenEditFacetDialog(facet: FacetValue, facetGroup: FacetGroup) {
  openEditFacetDialog(facet, facetGroup)
  editFacetDialog.value = true
}

async function handleSaveEditedFacet() {
  const success = await saveEditedFacet()
  if (success) {
    editFacetDialog.value = false
    emit('facets-updated')
  }
}

function handleConfirmDeleteFacet(facet: FacetValue) {
  confirmDeleteFacet(facet)
  singleDeleteConfirm.value = true
}

async function handleDeleteSingleFacet() {
  const success = await deleteSingleFacet()
  if (success) {
    singleDeleteConfirm.value = false
  }
}

async function handleBulkDelete() {
  await bulkDelete()
  bulkDeleteConfirm.value = false
}

function handleOpenSourceDetails(facet: FacetValue) {
  openSourceDetails(facet)
  sourceDetailsDialog.value = true
}

function handleOpenEntityLinkDialog(facet: FacetValue) {
  openEntityLinkDialog(facet)
  entityLinkDialog.value = true
}

async function handleSaveEntityLink() {
  await saveEntityLink()
  entityLinkDialog.value = false
}
</script>
