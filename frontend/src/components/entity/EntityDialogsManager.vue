<template>
  <div>
    <!-- Add Facet Dialog -->
    <AddFacetDialog
      v-model="internalAddFacetDialog"
      :facet-type-id="facetTypeId"
      :facet-types="facetTypes"
      :selected-facet-type="selectedFacetType"
      :value="facetValue"
      :text-representation="textRepresentation"
      :source-url="sourceUrl"
      :confidence-score="confidenceScore"
      :saving="saving"
      @update:facet-type-id="$emit('update:facet-type-id', $event)"
      @update:value="$emit('update:value', $event)"
      @update:text-representation="$emit('update:text-representation', $event)"
      @update:source-url="$emit('update:source-url', $event)"
      @update:confidence-score="$emit('update:confidence-score', $event)"
      @save="$emit('save-facet')"
      @close="$emit('close-facet-dialog')"
    />

    <!-- Facet Details Dialog -->
    <FacetDetailsDialog
      v-model="internalFacetDetailsDialog"
      :facet-group="facetGroup"
      :facet-values="facetValues"
      @verify="$emit('verify-facet', $event)"
      @copy-email="$emit('copy-email', $event)"
    />

    <!-- Edit Entity Dialog -->
    <EntityEditDialog
      v-model="internalEditDialog"
      :name="entityName"
      :external-id="entityExternalId"
      :entity-type-name="entityTypeName"
      :saving="savingEntity"
      @update:name="$emit('update:entity-name', $event)"
      @update:external-id="$emit('update:entity-external-id', $event)"
      @save="$emit('save-entity')"
    />

    <!-- Add/Edit Relation Dialog -->
    <AddRelationDialog
      v-model="internalAddRelationDialog"
      :editing="editing"
      :relation-type-id="relationTypeId"
      :direction="direction"
      :target-entity-id="targetEntityId"
      :attributes-json="attributesJson"
      :relation-types="relationTypes"
      :target-entities="targetEntities"
      :loading-relation-types="loadingRelationTypes"
      :searching-entities="searchingEntities"
      :search-query="searchQuery"
      :saving="savingRelation"
      @update:relation-type-id="$emit('update:relation-type-id', $event)"
      @update:direction="$emit('update:direction', $event)"
      @update:target-entity-id="$emit('update:target-entity-id', $event)"
      @update:attributes-json="$emit('update:attributes-json', $event)"
      @save="$emit('save-relation')"
      @close="$emit('close-relation-dialog')"
      @search="$emit('search-entities', $event)"
    />

    <!-- Delete Relation Confirmation -->
    <ConfirmDialog
      v-model="internalDeleteRelationConfirm"
      :title="t('entityDetail.dialog.deleteRelation')"
      :message="t('entityDetail.dialog.deleteRelationConfirm')"
      :subtitle="relationDeleteSubtitle"
      :confirm-text="t('common.delete')"
      :loading="deletingRelation"
      @confirm="$emit('delete-relation')"
    />

    <!-- Export Dialog -->
    <EntityExportDialog
      v-model="internalExportDialog"
      :format="exportFormat"
      :options="exportOptions"
      :exporting="exporting"
      @update:format="$emit('update:export-format', $event)"
      @update:options="$emit('update:export-options', $event)"
      @export="$emit('export')"
    />

    <!-- Link Data Source Dialog -->
    <LinkDataSourceDialog
      v-model="internalLinkDataSourceDialog"
      :selected-source="selectedSource"
      :available-sources="availableSources"
      :searching="searching"
      :search-query="sourceSearchQuery"
      :linking="linking"
      @update:selected-source="$emit('update:selected-source', $event)"
      @search="$emit('search-sources', $event)"
      @link="$emit('link-source')"
      @create-new="$emit('create-new-source')"
    />

    <!-- Source Details Dialog -->
    <SourceDetailsDialog
      v-model="internalSourceDetailsDialog"
      :source-facet="sourceFacet"
    />

    <!-- Notes Dialog -->
    <EntityNotesDialog
      v-model="internalNotesDialog"
      :notes="notes"
      :new-note="newNote"
      :saving-note="savingNote"
      @update:new-note="$emit('update:new-note', $event)"
      @save-note="$emit('save-note')"
      @delete-note="$emit('delete-note', $event)"
    />

    <!-- Single Facet Delete Confirmation Dialog -->
    <ConfirmDialog
      v-model="internalSingleDeleteConfirm"
      :title="t('entityDetail.dialog.deleteFacets')"
      :message="t('entityDetail.dialog.deleteFacetsConfirm', { count: 1 })"
      :subtitle="t('entityDetail.dialog.cannotUndo')"
      :confirm-text="t('common.delete')"
      confirm-icon="mdi-delete"
      :loading="deletingFacet"
      @confirm="$emit('delete-single-facet')"
    />

    <!-- Edit Facet Dialog -->
    <v-dialog v-model="internalEditFacetDialog" max-width="800">
      <v-card>
        <v-card-title>
          <v-icon start>mdi-pencil</v-icon>
          {{ t('entityDetail.dialog.editFacet') }}
        </v-card-title>
        <v-card-text v-if="editingFacet">
          <DynamicSchemaForm
            v-if="editingFacetSchema"
            :model-value="editingFacetValue"
            :schema="editingFacetSchema"
            @update:model-value="$emit('update:editing-facet-value', $event)"
          />
          <v-textarea
            v-else
            :model-value="editingFacetTextValue"
            :label="t('entities.facet.value')"
            rows="3"
            variant="outlined"
            class="mt-2"
            @update:model-value="$emit('update:editing-facet-text-value', $event)"
          ></v-textarea>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="internalEditFacetDialog = false">{{ t('common.cancel') }}</v-btn>
          <v-btn variant="tonal" color="primary" :loading="savingFacet" @click="$emit('save-edited-facet')">
            {{ t('common.save') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import AddFacetDialog from './AddFacetDialog.vue'
import FacetDetailsDialog from './FacetDetailsDialog.vue'
import EntityEditDialog from './EntityEditDialog.vue'
import AddRelationDialog from './AddRelationDialog.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import EntityExportDialog from './EntityExportDialog.vue'
import LinkDataSourceDialog from './LinkDataSourceDialog.vue'
import SourceDetailsDialog from './SourceDetailsDialog.vue'
import EntityNotesDialog from './EntityNotesDialog.vue'
import DynamicSchemaForm from '@/components/DynamicSchemaForm.vue'

const props = defineProps<{
  // Add Facet Dialog
  addFacetDialog: boolean
  facetTypeId: string
  facetTypes: any[]
  selectedFacetType: any | null
  facetValue: Record<string, any>
  textRepresentation: string
  sourceUrl: string
  confidenceScore: number
  saving: boolean

  // Facet Details Dialog
  facetDetailsDialog: boolean
  facetGroup: any
  facetValues: any[]

  // Edit Entity Dialog
  editDialog: boolean
  entityName: string
  entityExternalId: string
  entityTypeName?: string
  savingEntity: boolean

  // Relation Dialog
  addRelationDialog: boolean
  editing: boolean
  relationTypeId: string
  direction: 'outgoing' | 'incoming'
  targetEntityId: string
  attributesJson: string
  relationTypes: any[]
  targetEntities: any[]
  loadingRelationTypes: boolean
  searchingEntities: boolean
  searchQuery: string
  savingRelation: boolean

  // Delete Relation
  deleteRelationConfirm: boolean
  relationToDelete: any
  deletingRelation: boolean

  // Export Dialog
  exportDialog: boolean
  exportFormat: string
  exportOptions: any
  exporting: boolean

  // Link Data Source Dialog
  linkDataSourceDialog: boolean
  selectedSource: any
  availableSources: any[]
  searching: boolean
  sourceSearchQuery: string
  linking: boolean

  // Source Details Dialog
  sourceDetailsDialog: boolean
  sourceFacet: any

  // Notes Dialog
  notesDialog: boolean
  notes: any[]
  newNote: string
  savingNote: boolean

  // Single Delete Confirm
  singleDeleteConfirm: boolean
  deletingFacet: boolean

  // Edit Facet Dialog
  editFacetDialog: boolean
  editingFacet: any
  editingFacetSchema: any
  editingFacetValue: Record<string, any>
  editingFacetTextValue: string
  savingFacet: boolean
}>()

const emit = defineEmits<{
  'update:add-facet-dialog': [value: boolean]
  'update:facet-type-id': [value: string]
  'update:value': [value: Record<string, any>]
  'update:text-representation': [value: string]
  'update:source-url': [value: string]
  'update:confidence-score': [value: number]
  'save-facet': []
  'close-facet-dialog': []
  'update:facet-details-dialog': [value: boolean]
  'verify-facet': [facetValueId: string]
  'copy-email': [text: string]
  'update:edit-dialog': [value: boolean]
  'update:entity-name': [value: string]
  'update:entity-external-id': [value: string]
  'save-entity': []
  'update:add-relation-dialog': [value: boolean]
  'update:relation-type-id': [value: string]
  'update:direction': [value: 'outgoing' | 'incoming']
  'update:target-entity-id': [value: string]
  'update:attributes-json': [value: string]
  'save-relation': []
  'close-relation-dialog': []
  'search-entities': [query: string]
  'update:delete-relation-confirm': [value: boolean]
  'delete-relation': []
  'update:export-dialog': [value: boolean]
  'update:export-format': [value: string]
  'update:export-options': [value: any]
  'export': []
  'update:link-data-source-dialog': [value: boolean]
  'update:selected-source': [value: any]
  'search-sources': [query: string]
  'link-source': []
  'create-new-source': []
  'update:source-details-dialog': [value: boolean]
  'update:notes-dialog': [value: boolean]
  'update:new-note': [value: string]
  'save-note': []
  'delete-note': [noteId: string]
  'update:single-delete-confirm': [value: boolean]
  'delete-single-facet': []
  'update:edit-facet-dialog': [value: boolean]
  'update:editing-facet-value': [value: Record<string, any>]
  'update:editing-facet-text-value': [value: string]
  'save-edited-facet': []
}>()

const { t } = useI18n()

// Two-way binding computed properties
const internalAddFacetDialog = computed({
  get: () => props.addFacetDialog,
  set: (value) => emit('update:add-facet-dialog', value)
})

const internalFacetDetailsDialog = computed({
  get: () => props.facetDetailsDialog,
  set: (value) => emit('update:facet-details-dialog', value)
})

const internalEditDialog = computed({
  get: () => props.editDialog,
  set: (value) => emit('update:edit-dialog', value)
})

const internalAddRelationDialog = computed({
  get: () => props.addRelationDialog,
  set: (value) => emit('update:add-relation-dialog', value)
})

const internalDeleteRelationConfirm = computed({
  get: () => props.deleteRelationConfirm,
  set: (value) => emit('update:delete-relation-confirm', value)
})

const internalExportDialog = computed({
  get: () => props.exportDialog,
  set: (value) => emit('update:export-dialog', value)
})

const internalLinkDataSourceDialog = computed({
  get: () => props.linkDataSourceDialog,
  set: (value) => emit('update:link-data-source-dialog', value)
})

const internalSourceDetailsDialog = computed({
  get: () => props.sourceDetailsDialog,
  set: (value) => emit('update:source-details-dialog', value)
})

const internalNotesDialog = computed({
  get: () => props.notesDialog,
  set: (value) => emit('update:notes-dialog', value)
})

const internalSingleDeleteConfirm = computed({
  get: () => props.singleDeleteConfirm,
  set: (value) => emit('update:single-delete-confirm', value)
})

const internalEditFacetDialog = computed({
  get: () => props.editFacetDialog,
  set: (value) => emit('update:edit-facet-dialog', value)
})

const relationDeleteSubtitle = computed(() => {
  if (!props.relationToDelete) return undefined
  return `${props.relationToDelete.relation_type_name}: ${props.relationToDelete.target_entity_name || props.relationToDelete.source_entity_name}`
})
</script>
