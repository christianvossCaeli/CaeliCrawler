<template>
  <div>
    <!-- Loading State -->
    <EntityLoadingOverlay :loading="loading" />

    <!-- Breadcrumbs -->
    <EntityBreadcrumbs
      :entity="entity"
      :entity-type="entityType"
      :type-slug="typeSlug"
    />

    <!-- Entity Header -->
    <EntityDetailHeader
      v-if="entity"
      :entity="entity"
      :entity-type="entityType"
      :facet-groups="facetsSummary?.facets_by_type || []"
      :notes-count="notes.length"
      :verified-count="facetsSummary?.verified_count || 0"
      :data-sources-count="dataSources.length"
      :children-count="childrenCount"
      :can-edit="canEdit"
      @open-notes="notesDialog = true"
      @open-export="exportDialog = true"
      @open-edit="openEditDialog"
      @add-facet="openAddFacetDialog"
      @add-facet-value="handleOpenAddFacetValueDialog"
    />

    <!-- Tabs for Content -->
    <EntityTabsNavigation
      v-model:active-tab="activeTab"
      :facets-summary="facetsSummary"
      :total-connections-count="totalConnectionsCount"
      :data-sources-count="dataSources.length"
      :attachment-count="attachmentCount"
      :supports-pysis="entityType?.supports_pysis || false"
      :has-external-data="externalData?.has_external_data || false"
      :referenced-by-count="referencedByCount"
    />

    <v-window v-model="activeTab">
      <!-- Facets Tab -->
      <v-window-item value="facets">
        <EntityFacetsTab
          :entity="entity"
          :entity-type="entityType"
          :facets-summary="facetsSummary"
          :can-edit="canEdit"
          @facets-updated="refreshFacetsSummary"
          @add-facet="openAddFacetDialog"
          @add-facet-value="handleOpenAddFacetValueDialog"
          @switch-tab="activeTab = $event"
          @enrichment-started="enrichmentHandlers.onEnrichmentStarted"
        />
      </v-window-item>

      <!-- Relations Tab -->
      <v-window-item value="connections">
        <EntityConnectionsTab
          :entity="entity"
          :entity-type="entityType"
          :type-slug="typeSlug || ''"
          :relations="relations"
          :children="children"
          :children-count="childrenCount"
          :children-page="childrenPage"
          :children-total-pages="childrenTotalPages"
          :children-search-query="childrenSearchQuery"
          :loading-relations="loadingRelations"
          :loading-children="loadingChildren"
          :hierarchy-enabled="flags.entityHierarchyEnabled"
          :can-edit="canEdit"
          @add-relation="openAddRelationDialog"
          @edit-relation="openEditRelationDialog"
          @delete-relation="confirmDeleteRelation"
          @navigate-relation="navigateToRelatedEntity"
          @load-children="loadChildren"
          @update:children-page="childrenPage = $event"
          @update:children-search-query="childrenSearchQuery = $event"
        />
      </v-window-item>

      <!-- Data Sources Tab -->
      <v-window-item value="sources">
        <EntitySourcesTab
          :data-sources="dataSources"
          :loading="loadingDataSources"
          :starting-crawl-id="startingCrawl"
          :api-configuration-id="entity?.api_configuration_id"
          :external-source-name="entity?.external_source_name"
          :external-id="entity?.external_id"
          :can-edit="canEdit"
          @link-source="openLinkSourceDialog"
          @edit-source="openEditSourceDialog"
          @start-crawl="startCrawl"
          @unlink-source="confirmUnlinkSource"
          @delete-source="confirmDeleteSource"
        />
      </v-window-item>

      <!-- Documents Tab -->
      <v-window-item value="documents">
        <EntityDocumentsTab :documents="documents" :loading="loadingDocuments" />
      </v-window-item>

      <!-- PySis Tab -->
      <v-window-item v-if="entityType?.supports_pysis" value="pysis" eager>
        <PySisTab v-if="entity" :municipality="entity.name" />
      </v-window-item>

      <!-- External API Data Tab -->
      <v-window-item v-if="externalData?.has_external_data" value="api-data">
        <EntityApiDataTab :external-data="externalData" />
      </v-window-item>

      <!-- Attachments Tab -->
      <v-window-item value="attachments">
        <EntityAttachmentsTab
          v-if="entity"
          :entity-id="entity.id"
          :can-edit="canEdit"
          @attachments-changed="loadAttachmentCount"
        />
      </v-window-item>

      <!-- Referenced By Tab (shows facets that reference this entity) -->
      <v-window-item v-if="referencedByCount > 0" value="referenced-by">
        <EntityReferencedByTab
          v-if="entity"
          :entity-id="entity.id"
          :entity-name="entity.name"
        />
      </v-window-item>
    </v-window>

    <!-- All Dialogs -->
    <EntityDialogsManager
      v-model:add-facet-dialog="addFacetDialog"
      v-model:facet-details-dialog="facetDetailsDialog"
      v-model:edit-dialog="editDialog"
      v-model:add-relation-dialog="addRelationDialog"
      v-model:delete-relation-confirm="deleteRelationConfirm"
      v-model:export-dialog="exportDialog"
      v-model:link-data-source-dialog="linkDataSourceDialog"
      v-model:source-details-dialog="sourceDetailsDialog"
      v-model:notes-dialog="notesDialog"
      v-model:single-delete-confirm="singleDeleteConfirm"
      v-model:edit-facet-dialog="editFacetDialog"
      :can-edit="canEdit"
      :facet-type-id="newFacet.facet_type_id"
      :facet-types="applicableFacetTypes"
      :selected-facet-type="selectedFacetTypeForForm ?? null"
      :facet-value="newFacet.value"
      :text-representation="newFacet.text_representation"
      :source-url="newFacet.source_url"
      :confidence-score="newFacet.confidence_score"
      :saving="savingFacet"
      :facet-group="selectedFacetGroup"
      :facet-values="facetDetails"
      :entity-name="editForm.name"
      :entity-external-id="editForm.external_id"
      :entity-type-name="entityType?.name"
      :saving-entity="savingEntity"
      :editing="!!editingRelation"
      :relation-type-id="newRelation.relation_type_id"
      :direction="newRelation.direction"
      :target-entity-id="newRelation.target_entity_id"
      :attributes-json="newRelation.attributes_json"
      :relation-types="relationTypes"
      :target-entities="targetEntities"
      :loading-relation-types="loadingRelationTypes"
      :searching-entities="searchingEntities"
      :search-query="entitySearchQuery"
      :saving-relation="savingRelation"
      :relation-to-delete="relationToDelete"
      :deleting-relation="deletingRelation"
      :export-format="exportFormat"
      :export-options="exportOptions"
      :exporting="exporting"
      :selected-source="selectedSourceToLink"
      :available-sources="availableSourcesForLink"
      :searching="searchingSourcesForLink"
      :source-search-query="sourceSearchQuery"
      :linking="linkingSource"
      :source-facet="selectedSourceFacet"
      :notes="notes"
      :new-note="newNote"
      :saving-note="savingNote"
      :deleting-facet="deletingFacet"
      :editing-facet="editingFacet"
      :editing-facet-schema="editingFacetSchema"
      :editing-facet-value="editingFacetValue"
      :editing-facet-text-value="editingFacetTextValue"
      :saving-facet="savingFacet"
      @update:facet-type-id="onFacetTypeChange"
      @update:value="newFacet.value = $event"
      @update:text-representation="newFacet.text_representation = $event"
      @update:source-url="newFacet.value.source_url = $event"
      @update:confidence-score="newFacet.value.confidence_score = $event"
      @update:facet-target-entity-id="newFacet.target_entity_id = $event"
      @save-facet="handleSaveFacetValue"
      @close-facet-dialog="closeAddFacetDialog"
      @verify-facet="verifyFacet"
      @copy-email="copyToClipboard"
      @update:entity-name="editForm.name = $event"
      @update:entity-external-id="editForm.external_id = $event"
      @save-entity="saveEntity"
      @update:relation-type-id="newRelation.relation_type_id = $event"
      @update:direction="newRelation.direction = $event"
      @update:target-entity-id="newRelation.target_entity_id = $event"
      @update:attributes-json="newRelation.attributes_json = $event"
      @save-relation="saveRelation"
      @close-relation-dialog="relationHandlers.closeRelationDialog"
      @search-entities="relationHandlers.searchEntities"
      @delete-relation="deleteRelation"
      @update:export-format="exportFormat = $event"
      @update:export-options="exportOptions = $event"
      @export="handleExport"
      @update:selected-source="selectedSourceToLink = $event"
      @search-sources="dataSourceHandlers.searchSourcesForLink"
      @link-source="handleLinkSource"
      @create-new-source="goToSourcesWithEntity"
      @update:new-note="newNote = $event"
      @save-note="noteHandlers.saveNote"
      @delete-note="noteHandlers.deleteNote"
      @delete-single-facet="handleDeleteSingleFacet"
      @update:editing-facet-value="editingFacetValue = $event"
      @update:editing-facet-text-value="editingFacetTextValue = $event"
      @save-edited-facet="handleSaveEditedFacet"
    />

    <!-- Data Source Management Dialogs -->
    <EntityDataSourceManager
      v-if="entity"
      v-model:show-edit-dialog="editSourceDialog"
      v-model:show-delete-dialog="deleteSourceConfirm"
      v-model:show-unlink-dialog="unlinkSourceConfirm"
      :entity-id="entity.id"
      :source-to-edit="editingSource"
      :source-to-delete="sourceToDelete"
      :source-to-unlink="sourceToUnlink"
      @source-updated="onSourceUpdated"
      @source-deleted="onSourceDeleted"
      @source-unlinked="onSourceUnlinked"
    />

    <!-- PySis Enrichment Dialogs -->
    <EntityPysisEnrichmentDialog
      v-if="entity"
      v-model:show-dialog="showEnrichFromPysisDialog"
      v-model:overwrite="enrichPysisOverwrite"
      :entity-id="entity.id"
      :entity-name="entity.name"
      @enrichment-completed="onPysisEnrichmentCompleted"
    />

    <!-- Facet Enrichment Review Modal -->
    <FacetEnrichmentReview
      v-model="showEnrichmentReviewDialog"
      :task-id="enrichmentTaskId"
      :task-status="enrichmentTaskStatus"
      :preview-data="enrichmentPreviewData"
      @close="enrichmentHandlers.onEnrichmentReviewClose"
      @minimize="enrichmentHandlers.onEnrichmentReviewMinimize"
      @applied="onEnrichmentApplied"
    />

    <!-- Minimized Task Toast/Snackbar -->
    <v-snackbar
      v-model="showMinimizedTaskSnackbar"
      :timeout="-1"
      color="info"
      location="bottom end"
    >
      <div class="d-flex align-center" style="cursor: pointer" @click="enrichmentHandlers.reopenEnrichmentReview">
        <v-icon class="mr-2">mdi-cog-sync</v-icon>
        {{ t('facetEnrichment.taskMinimized') }}
        <v-btn variant="text" size="small" class="ml-2">
          {{ t('facetEnrichment.clickToReturn') }}
        </v-btn>
      </div>
    </v-snackbar>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useEntityStore, type Entity, type EntityType } from '@/stores/entity'
import { useAuthStore } from '@/stores/auth'
import { entityApi, attachmentApi, facetApi } from '@/services/api'
import { useSnackbar } from '@/composables/useSnackbar'
import { extractErrorMessage } from '@/utils/errorMessage'
import { useFeatureFlags } from '@/composables/useFeatureFlags'
import { useEntityExport } from '@/composables/useEntityExport'
import { useEntityNotes } from '@/composables/useEntityNotes'
import { useEntityRelations, type Relation } from '@/composables/useEntityRelations'
import { useEntityDataSources, type DataSource } from '@/composables/useEntityDataSources'
import { useEntityEnrichment } from '@/composables/useEntityEnrichment'
import { useEntityFacets, type FacetGroup } from '@/composables/useEntityFacets'
import { usePageContextProvider } from '@/composables/usePageContext'
import type { PageContextData, FacetSummary } from '@/composables/assistant/types'
import type {
  FacetValue,
  EntityDocument,
} from '@/types/entity'
import type { EntityFacetsSummary } from '@/stores/types/entity'

// Components
import PySisTab from '@/components/PySisTab.vue'
import FacetEnrichmentReview from '@/components/FacetEnrichmentReview.vue'
import EntityAttachmentsTab from '@/components/entity/EntityAttachmentsTab.vue'
import EntityDetailHeader from '@/components/entity/EntityDetailHeader.vue'
import EntityConnectionsTab from '@/components/entity/EntityConnectionsTab.vue'
import EntitySourcesTab from '@/components/entity/EntitySourcesTab.vue'
import EntityApiDataTab from '@/components/entity/EntityApiDataTab.vue'
import EntityDocumentsTab from '@/components/entity/EntityDocumentsTab.vue'
import EntityFacetsTab from '@/components/entity/EntityFacetsTab.vue'
import EntityPysisEnrichmentDialog from '@/components/entity/EntityPysisEnrichmentDialog.vue'
import EntityDataSourceManager from '@/components/entity/EntityDataSourceManager.vue'
import EntityLoadingOverlay from '@/components/entity/EntityLoadingOverlay.vue'
import EntityBreadcrumbs from '@/components/entity/EntityBreadcrumbs.vue'
import EntityTabsNavigation from '@/components/entity/EntityTabsNavigation.vue'
import EntityDialogsManager from '@/components/entity/EntityDialogsManager.vue'
import EntityReferencedByTab from '@/components/entity/EntityReferencedByTab.vue'
import { useLogger } from '@/composables/useLogger'

// Local type aliases (using shared types from entity.ts)
type DataSourceLocal = DataSource
type RelationLocal = Relation

// Local interfaces (view-specific types not shared elsewhere)
interface ExternalData {
  has_external_data: boolean
  [key: string]: unknown
}

const logger = useLogger('EntityDetailView')

const { t } = useI18n()
const { flags } = useFeatureFlags()
const { showSuccess, showError } = useSnackbar()
const route = useRoute()
const router = useRouter()
const store = useEntityStore()
const auth = useAuthStore()
const canEdit = computed(() => auth.isEditor)

// Route params
const typeSlug = computed(() => route.params.typeSlug as string | undefined)
const entitySlug = computed(() => route.params.entitySlug as string | undefined)
const entityId = computed(() => route.params.id as string | undefined)

// Core entity data
const loading = ref(true)
const activeTab = ref('facets')
const entity = computed<Entity | null>(() => store.selectedEntity)
const entityType = computed<EntityType | null>(() => store.selectedEntityType)
const facetsSummary = ref<EntityFacetsSummary | null>(null)
const documents = ref<EntityDocument[]>([])
const externalData = ref<ExternalData | null>(null)
const attachmentCount = ref(0)
const referencedByCount = ref(0)

// Async function for facet summary refresh
async function refreshFacetsSummary() {
  if (entity.value) {
    facetsSummary.value = await store.fetchEntityFacetsSummary(entity.value.id)
  }
}

// Composable instances
const exportHandlers = useEntityExport()
const noteHandlers = useEntityNotes(computed(() => entity.value?.id))
const relationHandlers = useEntityRelations(entity.value)
const dataSourceHandlers = useEntityDataSources(computed(() => entity.value?.id))
const enrichmentHandlers = useEntityEnrichment()
const facetHandlers = useEntityFacets(entity.value, entityType.value, refreshFacetsSummary)

// Page Context Provider for AI Assistant awareness
const { updateContext } = usePageContextProvider(
  '/entities/',
  (): PageContextData => ({
    // Entity identification
    entity_id: entity.value?.id || undefined,
    entity_type: typeSlug.value || undefined,
    entity_name: entity.value?.name || undefined,

    // Current view state
    active_tab: activeTab.value as PageContextData['active_tab'],

    // Facets summary
    facets: facetsSummary.value?.facets_by_type?.map((group): FacetSummary => ({
      facet_type_slug: group.facet_type_slug,
      facet_type_name: group.facet_type_name,
      value_count: group.value_count || 0,
      sample_values: group.sample_values?.slice(0, 3).map(v => String(v.value ?? '')) || []
    })) || [],
    facet_count: facetsSummary.value?.total_facet_values || 0,

    // Relations count
    relation_count: relationHandlers.relations.value?.length || 0,

    // PySis status
    pysis_status: entityType.value?.supports_pysis
      ? (enrichmentHandlers.enrichmentTaskStatus.value?.status === 'completed' ? 'ready' : 'none')
      : undefined,

    // Available features for this view
    available_features: [
      'view_facets',
      'edit_facets',
      'view_relations',
      'add_relations',
      'view_documents',
      ...(entityType.value?.supports_pysis ? ['pysis_analysis', 'enrich_facets'] : []),
      'start_crawl'
    ],

    // Available actions based on context
    available_actions: [
      'summarize',
      'edit_entity',
      ...(activeTab.value === 'facets' ? ['add_facet', 'edit_facet'] : []),
      ...(activeTab.value === 'connections' ? ['add_relation'] : []),
      ...(entityType.value?.supports_pysis ? ['enrich_facets'] : [])
    ]
  })
)

// Update context when relevant data changes
watch([entity, activeTab, facetsSummary], () => {
  if (entity.value) {
    updateContext({
      entity_id: entity.value.id,
      entity_name: entity.value.name,
      active_tab: activeTab.value as PageContextData['active_tab'],
      facet_count: facetsSummary.value?.total_facet_values || 0
    })
  }
}, { deep: true })

// Destructure composable returns
const { exporting, exportFormat, exportOptions, exportData: performExport } = exportHandlers
const { notes, newNote, savingNote, loadNotes } = noteHandlers
const {
  relations,
  relationTypes,
  targetEntities,
  entitySearchQuery,
  loadingRelations,
  loadingRelationTypes,
  searchingEntities,
  savingRelation,
  deletingRelation,
  relationsLoaded,
  editingRelation,
  relationToDelete,
  newRelation,
  loadRelations,
} = relationHandlers
const {
  dataSources,
  availableSourcesForLink,
  selectedSourceToLink,
  sourceSearchQuery,
  loadingDataSources,
  searchingSourcesForLink,
  linkingSource,
  startingCrawl,
  loadDataSources,
} = dataSourceHandlers
const {
  enrichmentTaskId,
  enrichmentTaskStatus,
  enrichmentPreviewData,
  showEnrichmentReviewDialog,
  showMinimizedTaskSnackbar,
} = enrichmentHandlers
const {
  selectedFacetGroup,
  facetDetails,
  editingFacet,
  editingFacetValue,
  editingFacetTextValue,
  editingFacetSchema,
  newFacet,
  savingFacet,
  deletingFacet,
  applicableFacetTypes,
  selectedFacetTypeForForm,
  onFacetTypeChange,
  resetAddFacetForm,
  openAddFacetValueDialog,
  saveFacetValue,
  verifyFacet,
  saveEditedFacet,
  deleteSingleFacet,
} = facetHandlers

// Children state
const children = ref<Entity[]>([])
const childrenCount = ref(0)
const childrenPage = ref(1)
const childrenTotalPages = ref(1)
const childrenSearchQuery = ref('')
const loadingChildren = ref(false)
const childrenLoaded = ref(false)
const loadingDocuments = ref(false)

// Dialog states
const addFacetDialog = ref(false)
const addRelationDialog = ref(false)
const facetDetailsDialog = ref(false)
const editDialog = ref(false)
const notesDialog = ref(false)
const exportDialog = ref(false)
const linkDataSourceDialog = ref(false)
const editSourceDialog = ref(false)
const deleteSourceConfirm = ref(false)
const unlinkSourceConfirm = ref(false)
const deleteRelationConfirm = ref(false)
const singleDeleteConfirm = ref(false)
const editFacetDialog = ref(false)
const sourceDetailsDialog = ref(false)
const showEnrichFromPysisDialog = ref(false)
const enrichPysisOverwrite = ref(false)

// Form states
const editingSource = ref<DataSourceLocal | null>(null)
const sourceToDelete = ref<DataSourceLocal | null>(null)
const sourceToUnlink = ref<DataSourceLocal | null>(null)
const selectedSourceFacet = ref<FacetValue | null>(null)

const editForm = ref({
  name: '',
  external_id: '',
})

const savingEntity = ref(false)

// Computed properties
const totalConnectionsCount = computed(() => {
  const relationCount = entity.value?.relation_count || 0
  const childCount = entity.value?.children_count || childrenCount.value || 0
  const hasParent = entity.value?.parent_id ? 1 : 0
  return relationCount + childCount + hasParent
})

// Main data loading
async function loadEntityData() {
  loading.value = true
  try {
    if (entityId.value) {
      await store.fetchEntity(entityId.value)
      if (entity.value?.entity_type_id) {
        await store.fetchEntityType(entity.value.entity_type_id)
      }
    } else if (typeSlug.value && entitySlug.value) {
      await store.fetchEntityTypeBySlug(typeSlug.value)
      await store.fetchEntityBySlug(typeSlug.value, entitySlug.value)
    } else {
      showError(t('entityDetail.messages.entityNotFound'))
      router.push('/entities')
      return
    }

    if (!entity.value) {
      showError(t('entityDetail.messages.entityNotFound'))
      router.push(typeSlug.value ? `/entities/${typeSlug.value}` : '/entities')
      return
    }

    if (store.facetTypes.length === 0) {
      await store.fetchFacetTypes()
    }

    facetsSummary.value = await store.fetchEntityFacetsSummary(entity.value.id)
    await loadNotes()
    relationsLoaded.value = false

    editForm.value = {
      name: entity.value.name,
      external_id: entity.value.external_id || '',
    }

    loadExternalData()
    loadAttachmentCount()
    loadReferencedByCount()

    if (activeTab.value === 'connections') {
      loadChildren()
    }
  } catch (e) {
    logger.error('Failed to load entity', e)
    showError(t('entityDetail.messages.loadError'))
  } finally {
    loading.value = false
  }
}

async function loadExternalData() {
  if (!entity.value) return
  try {
    const response = await entityApi.getEntityExternalData(entity.value.id)
    externalData.value = response.data
  } catch (e) {
    logger.error('Failed to load external data', e)
    externalData.value = null
  }
}

async function loadDocuments() {
  if (!entity.value) return
  loadingDocuments.value = true
  try {
    const response = await entityApi.getEntityDocuments(entity.value.id)
    documents.value = response.data.documents || []
  } catch (e) {
    logger.error('Failed to load documents', e)
    documents.value = []
    showError(t('entityDetail.messages.documentsLoadError'))
  } finally {
    loadingDocuments.value = false
  }
}

async function loadAttachmentCount() {
  if (!entity.value) return
  try {
    const response = await attachmentApi.list(entity.value.id)
    attachmentCount.value = response.data.total || 0
  } catch (e) {
    logger.error('Failed to load attachment count', e)
    attachmentCount.value = 0
  }
}

async function loadReferencedByCount() {
  if (!entity.value) return
  try {
    const response = await facetApi.getFacetsReferencingEntity(entity.value.id, { per_page: 1 })
    referencedByCount.value = response.data.total || 0
  } catch (e) {
    logger.error('Failed to load referenced-by count', e)
    referencedByCount.value = 0
  }
}

async function loadChildren() {
  if (!entity.value) return
  loadingChildren.value = true
  try {
    const response = await entityApi.getEntityChildren(entity.value.id, {
      page: childrenPage.value,
      per_page: 20,
    })
    children.value = response.data.items || []
    childrenCount.value = response.data.total || 0
    childrenTotalPages.value = response.data.pages || 1
    childrenLoaded.value = true
  } catch (e) {
    logger.error('Failed to load children', e)
    children.value = []
    childrenCount.value = 0
    showError(t('entityDetail.children.loadError'))
  } finally {
    loadingChildren.value = false
  }
}

// Facet management wrappers
function closeAddFacetDialog() {
  addFacetDialog.value = false
  resetAddFacetForm()
}

function openAddFacetDialog() {
  if (!canEdit.value) return
  addFacetDialog.value = true
}

function openEditDialog() {
  if (!canEdit.value) return
  editDialog.value = true
}

function handleOpenAddFacetValueDialog(facetGroup: FacetGroup) {
  if (!canEdit.value) return
  openAddFacetValueDialog(facetGroup)
  addFacetDialog.value = true
}

async function handleSaveFacetValue() {
  if (!canEdit.value) return
  const success = await saveFacetValue()
  if (success) {
    closeAddFacetDialog()
  }
}

async function handleSaveEditedFacet() {
  if (!canEdit.value) return
  const success = await saveEditedFacet()
  if (success) {
    editFacetDialog.value = false
  }
}

async function handleDeleteSingleFacet() {
  if (!canEdit.value) return
  const success = await deleteSingleFacet()
  if (success) {
    singleDeleteConfirm.value = false
  }
}

// Relation management
async function saveRelation() {
  if (!canEdit.value) return
  const success = await relationHandlers.saveRelation()
  if (success) {
    addRelationDialog.value = false
  }
}

async function deleteRelation() {
  if (!canEdit.value) return
  const success = await relationHandlers.deleteRelation()
  if (success) {
    deleteRelationConfirm.value = false
  }
}

function openAddRelationDialog() {
  if (!canEdit.value) return
  relationHandlers.openAddRelationDialog()
  addRelationDialog.value = true
}

function openEditRelationDialog(rel: RelationLocal) {
  if (!canEdit.value) return
  relationHandlers.editRelation(rel)
  addRelationDialog.value = true
}

function confirmDeleteRelation(rel: RelationLocal) {
  if (!canEdit.value) return
  relationHandlers.confirmDeleteRelation(rel)
}

function navigateToRelatedEntity(rel: RelationLocal) {
  const targetId = rel.source_entity_id === entity.value?.id ? rel.target_entity_id : rel.source_entity_id
  const targetSlug = rel.source_entity_id === entity.value?.id ? rel.target_entity_type_slug : rel.source_entity_type_slug
  const targetEntitySlug = rel.source_entity_id === entity.value?.id ? rel.target_entity_slug || targetId : rel.source_entity_slug || targetId

  router.push({
    name: 'entity-detail',
    params: { typeSlug: targetSlug, entitySlug: targetEntitySlug },
  })
}

// Export
async function handleExport() {
  if (!entity.value) return
  const success = await performExport(
    entity.value,
    entityType.value,
    facetsSummary.value,
    relations.value,
    dataSources.value,
    notes.value
  )
  if (success) {
    exportDialog.value = false
  }
}

// Data source management
function openEditSourceDialog(source: DataSourceLocal) {
  if (!canEdit.value) return
  editingSource.value = source
  editSourceDialog.value = true
}

function confirmDeleteSource(source: DataSourceLocal) {
  if (!canEdit.value) return
  sourceToDelete.value = source
  deleteSourceConfirm.value = true
}

function confirmUnlinkSource(source: DataSourceLocal) {
  if (!canEdit.value) return
  sourceToUnlink.value = source
  unlinkSourceConfirm.value = true
}

function openLinkSourceDialog() {
  if (!canEdit.value) return
  linkDataSourceDialog.value = true
}

function startCrawl(source: DataSourceLocal) {
  if (!canEdit.value) return
  dataSourceHandlers.startCrawl(source)
}

async function handleLinkSource() {
  if (!canEdit.value) return
  const success = await dataSourceHandlers.linkSourceToEntity()
  if (success) {
    linkDataSourceDialog.value = false
  }
}

async function onSourceUpdated() {
  await dataSourceHandlers.reloadDataSources()
}

async function onSourceDeleted() {
  sourceToDelete.value = null
  await dataSourceHandlers.reloadDataSources()
}

async function onSourceUnlinked() {
  sourceToUnlink.value = null
  await dataSourceHandlers.reloadDataSources()
}

function goToSourcesWithEntity() {
  if (!entity.value) return
  router.push({
    name: 'sources',
    query: { linkEntity: entity.value.id },
  })
}

// Entity edit
async function saveEntity() {
  if (!canEdit.value) return
  if (!entity.value) return
  savingEntity.value = true
  try {
    await store.updateEntity(entity.value.id, {
      name: editForm.value.name,
      external_id: editForm.value.external_id || undefined,
    })
    showSuccess(t('entityDetail.messages.entityUpdated'))
    editDialog.value = false
  } catch (e: unknown) {
    showError(extractErrorMessage(e))
  } finally {
    savingEntity.value = false
  }
}

// PySis enrichment
async function onPysisEnrichmentCompleted() {
  await loadEntityData()
}

// Enrichment
async function onEnrichmentApplied(result: { created: number; updated: number }) {
  showSuccess(t('facetEnrichment.applied', result))
  await loadEntityData()
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text)
  showSuccess(t('entityDetail.messages.copiedToClipboard'))
}

// Watchers
watch(activeTab, (tab) => {
  if (tab === 'relations' && !relationsLoaded.value) {
    loadRelations()
  }
  if (tab === 'sources' && dataSources.value.length === 0) {
    loadDataSources()
  }
  if (tab === 'documents' && documents.value.length === 0) {
    loadDocuments()
  }
  if (tab === 'connections' && !childrenLoaded.value) {
    loadChildren()
  }
})

watch([typeSlug, entitySlug, entityId], () => {
  // Reset tab to default when navigating to a new entity
  activeTab.value = 'facets'
  childrenLoaded.value = false
  children.value = []
  childrenCount.value = 0
  childrenPage.value = 1
  relationsLoaded.value = false
  relations.value = []
  loadEntityData()
})

// Lifecycle
onMounted(() => {
  loadEntityData()
})

onUnmounted(() => {
  enrichmentHandlers.cleanup()
  dataSourceHandlers.cleanup()
})
</script>

<style scoped>
/* Hierarchy Tree Visualization */
.tree-node {
  transition: all 0.2s ease;
}

.tree-node:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
</style>
