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
          <v-menu
            v-if="canEdit && entityType?.supports_pysis"
            v-model="enrichmentMenuOpen"
            :close-on-content-click="false"
            location="bottom end"
            @update:model-value="onEnrichmentMenuOpen"
          >
            <template #activator="{ props: activatorProps }">
              <v-btn
                v-bind="activatorProps"
                color="secondary"
                size="small"
                variant="tonal"
                :loading="loadingEnrichmentSources"
              >
                <v-icon start>mdi-auto-fix</v-icon>
                {{ t('entityDetail.enrichment.buttonLabel') }}
                <v-icon end>mdi-chevron-down</v-icon>
              </v-btn>
            </template>

            <v-card min-width="380" max-width="450">
              <v-card-title class="text-subtitle-1 pb-0">
                {{ t('entityDetail.enrichment.dropdownTitle') }}
              </v-card-title>

              <v-card-text v-if="enrichmentSources" class="pb-2">
                <!-- PySIS Source -->
                <v-checkbox
                  v-if="enrichmentSources.pysis?.available"
                  v-model="selectedEnrichmentSources"
                  value="pysis"
                  hide-details
                  density="compact"
                  class="mb-1"
                >
                  <template #label>
                    <div class="d-flex align-center justify-space-between w-100">
                      <span class="d-flex align-center">
                        <v-icon start size="small" color="deep-purple">mdi-database</v-icon>
                        {{ t('entityDetail.enrichment.sourcePysis') }}
                        <v-chip size="x-small" class="ml-2">{{ enrichmentSources.pysis.count }}</v-chip>
                      </span>
                      <span v-if="enrichmentSources.pysis.last_updated" class="text-caption text-medium-emphasis ml-2">
                        {{ formatEnrichmentDate(enrichmentSources.pysis.last_updated) }}
                      </span>
                    </div>
                  </template>
                </v-checkbox>

                <!-- Relations Source -->
                <v-checkbox
                  v-if="enrichmentSources.relations?.available"
                  v-model="selectedEnrichmentSources"
                  value="relations"
                  hide-details
                  density="compact"
                  class="mb-1"
                >
                  <template #label>
                    <div class="d-flex align-center justify-space-between w-100">
                      <span class="d-flex align-center">
                        <v-icon start size="small" color="blue">mdi-link-variant</v-icon>
                        {{ t('entityDetail.enrichment.sourceRelations') }}
                        <v-chip size="x-small" class="ml-2">{{ enrichmentSources.relations.count }}</v-chip>
                      </span>
                      <span v-if="enrichmentSources.relations.last_updated" class="text-caption text-medium-emphasis ml-2">
                        {{ formatEnrichmentDate(enrichmentSources.relations.last_updated) }}
                      </span>
                    </div>
                  </template>
                </v-checkbox>

                <!-- Documents Source -->
                <v-checkbox
                  v-if="enrichmentSources.documents?.available"
                  v-model="selectedEnrichmentSources"
                  value="documents"
                  hide-details
                  density="compact"
                  class="mb-1"
                >
                  <template #label>
                    <div class="d-flex align-center justify-space-between w-100">
                      <span class="d-flex align-center">
                        <v-icon start size="small" color="orange">mdi-file-document-multiple</v-icon>
                        {{ t('entityDetail.enrichment.sourceDocuments') }}
                        <v-chip size="x-small" class="ml-2">{{ enrichmentSources.documents.count }}</v-chip>
                      </span>
                      <span v-if="enrichmentSources.documents.last_updated" class="text-caption text-medium-emphasis ml-2">
                        {{ formatEnrichmentDate(enrichmentSources.documents.last_updated) }}
                      </span>
                    </div>
                  </template>
                </v-checkbox>

                <!-- Extractions Source -->
                <v-checkbox
                  v-if="enrichmentSources.extractions?.available"
                  v-model="selectedEnrichmentSources"
                  value="extractions"
                  hide-details
                  density="compact"
                  class="mb-1"
                >
                  <template #label>
                    <div class="d-flex align-center justify-space-between w-100">
                      <span class="d-flex align-center">
                        <v-icon start size="small" color="teal">mdi-brain</v-icon>
                        {{ t('entityDetail.enrichment.sourceExtractions') }}
                        <v-chip size="x-small" class="ml-2">{{ enrichmentSources.extractions.count }}</v-chip>
                      </span>
                      <span v-if="enrichmentSources.extractions.last_updated" class="text-caption text-medium-emphasis ml-2">
                        {{ formatEnrichmentDate(enrichmentSources.extractions.last_updated) }}
                      </span>
                    </div>
                  </template>
                </v-checkbox>

                <!-- Attachments Source -->
                <v-checkbox
                  v-if="enrichmentSources.attachments?.available"
                  v-model="selectedEnrichmentSources"
                  value="attachments"
                  hide-details
                  density="compact"
                  class="mb-1"
                >
                  <template #label>
                    <div class="d-flex align-center justify-space-between w-100">
                      <span class="d-flex align-center">
                        <v-icon start size="small" color="deep-purple">mdi-paperclip</v-icon>
                        {{ t('entityDetail.enrichment.sourceAttachments') }}
                        <v-chip size="x-small" class="ml-2">{{ enrichmentSources.attachments.count }}</v-chip>
                      </span>
                      <span v-if="enrichmentSources.attachments.last_updated" class="text-caption text-medium-emphasis ml-2">
                        {{ formatEnrichmentDate(enrichmentSources.attachments.last_updated) }}
                      </span>
                    </div>
                  </template>
                </v-checkbox>

                <!-- No sources available message -->
                <v-alert
                  v-if="!hasAnyEnrichmentSource"
                  type="info"
                  variant="tonal"
                  density="compact"
                >
                  {{ t('entityDetail.enrichment.noSourcesAvailable') }}
                </v-alert>
              </v-card-text>

              <v-card-text v-else class="text-center py-4">
                <v-progress-circular indeterminate size="24"></v-progress-circular>
              </v-card-text>

              <v-divider></v-divider>

              <v-card-actions class="px-4 py-2">
                <v-chip size="small" variant="tonal">
                  {{ t('entityDetail.enrichment.existingFacets', { count: enrichmentSources?.existing_facets || 0 }) }}
                </v-chip>
                <v-spacer></v-spacer>
                <v-btn
                  variant="tonal"
                  color="primary"
                  :disabled="selectedEnrichmentSources.length === 0"
                  :loading="startingEnrichment"
                  @click="startEnrichmentAnalysis"
                >
                  <v-icon start>mdi-play</v-icon>
                  {{ t('entityDetail.enrichment.startAnalysis') }}
                </v-btn>
              </v-card-actions>
            </v-card>
          </v-menu>
        </div>
      </v-card-text>
    </v-card>

    <v-row>
      <v-col
        v-for="facetGroup in facetsSummary?.facets_by_type || []"
        :key="facetGroup.facet_type_id"
        cols="12"
      >
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon :icon="facetGroup.facet_type_icon" :color="facetGroup.facet_type_color" class="mr-2"></v-icon>
            {{ facetGroup.facet_type_name }}
            <v-chip size="small" class="ml-2">{{ facetGroup.value_count }}</v-chip>
            <v-chip v-if="facetGroup.verified_count" size="x-small" color="success" class="ml-1">
              {{ facetGroup.verified_count }} {{ t('entityDetail.verified') }}
            </v-chip>
            <v-spacer></v-spacer>
            <!-- Add Value Button -->
            <v-btn
              v-if="canEdit"
              size="small"
              color="primary"
              variant="tonal"
              class="mr-2"
              @click.stop="openAddFacetValueDialog(facetGroup)"
            >
              <v-icon start size="small">mdi-plus</v-icon>
              {{ t('common.add') }}
            </v-btn>
            <v-btn size="small" variant="tonal" @click="toggleFacetExpand(facetGroup.facet_type_slug)">
              <v-icon>{{ expandedFacets.includes(facetGroup.facet_type_slug) ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
            </v-btn>
          </v-card-title>

          <v-expand-transition>
            <v-card-text v-show="expandedFacets.includes(facetGroup.facet_type_slug)">
              <!-- History Facet Type - Show Chart -->
              <template v-if="facetGroup.facet_type_value_type === 'history'">
                <FacetHistoryChart
                  :entity-id="entity?.id || ''"
                  :facet-type-id="facetGroup.facet_type_id"
                  :facet-type="facetGroup"
                  :can-edit="canEdit"
                  @updated="$emit('facets-updated')"
                />
              </template>

              <!-- Regular Facet Values List -->
              <div v-else-if="getDisplayedFacets(facetGroup).length" class="mb-4">
                <div
                  v-for="(sample, idx) in getDisplayedFacets(facetGroup)"
                  :key="sample.id || idx"
                  class="mb-3 pa-3 rounded-lg facet-item border"
                  :class="{
                    'selected': selectedFacetIds.includes(sample.id),
                    'bg-surface-light': !$vuetify.theme.current.dark,
                    'bg-grey-darken-4': $vuetify.theme.current.dark
                  }"
                >
                  <!-- Checkbox for bulk selection -->
                  <div class="d-flex align-start">
                    <v-checkbox
                      v-if="canEdit && bulkMode"
                      :model-value="selectedFacetIds.includes(sample.id)"
                      hide-details
                      density="compact"
                      class="mr-2 mt-0"
                      @update:model-value="toggleFacetSelection(sample.id)"
                    ></v-checkbox>
                    <div class="flex-grow-1">
                      <!-- Generic Facet Value Display -->
                      <GenericFacetValueRenderer
                        :value="normalizeValue(sample.value)"
                        :facet-type="facetGroupToFacetType(facetGroup)"
                        show-icon
                      />

                      <!-- Entity Link Controls for Contact Types -->
                      <div v-if="facetGroup.facet_type_slug === 'contact' && (sample.target_entity_id || canEdit)" class="d-flex align-center ga-2 mt-2">
                        <!-- Link to referenced entity -->
                        <v-chip
                          v-if="sample.target_entity_id"
                          size="small"
                          variant="tonal"
                          color="primary"
                          class="cursor-pointer"
                          @click.stop="navigateToTargetEntity(sample)"
                        >
                          <v-icon start size="small">mdi-link-variant</v-icon>
                          {{ sample.target_entity_name || t('entityDetail.viewEntity') }}
                        </v-chip>
                        <!-- Entity Link Management Menu -->
                        <v-menu v-if="canEdit" location="bottom">
                          <template #activator="{ props: menuProps }">
                            <v-btn
                              icon
                              size="x-small"
                              variant="text"
                              v-bind="menuProps"
                              @click.stop
                            >
                              <v-icon size="small">mdi-dots-vertical</v-icon>
                            </v-btn>
                          </template>
                          <v-list density="compact">
                            <v-list-item
                              v-if="!sample.target_entity_id"
                              prepend-icon="mdi-link-plus"
                              :title="t('entityDetail.facets.linkToEntity', 'Mit Entity verknüpfen')"
                              @click="openEntityLinkDialog(sample)"
                            ></v-list-item>
                            <v-list-item
                              v-if="sample.target_entity_id"
                              prepend-icon="mdi-link-off"
                              :title="t('entityDetail.facets.unlinkEntity', 'Verknüpfung entfernen')"
                              @click="unlinkEntity(sample)"
                            ></v-list-item>
                            <v-list-item
                              v-if="sample.target_entity_id"
                              prepend-icon="mdi-swap-horizontal"
                              :title="t('entityDetail.facets.changeEntityLink', 'Andere Entity verknüpfen')"
                              @click="openEntityLinkDialog(sample)"
                            ></v-list-item>
                          </v-list>
                        </v-menu>
                      </div>

                      <!-- Footer: Meta Info & Actions -->
                      <div class="facet-footer mt-3 pt-3 border-t">
                        <!-- Meta Information Row -->
                        <div class="d-flex align-center flex-wrap ga-3 mb-2">
                          <!-- Source Badge (Clickable - opens details modal) -->
                          <v-chip
                            size="small"
                            variant="tonal"
                            :color="getFacetSourceColor(sample.source_type)"
                            class="cursor-pointer"
                            @click.stop="openSourceDetails(sample)"
                          >
                            <v-icon start size="small">{{ getFacetSourceIcon(sample.source_type) }}</v-icon>
                            {{ t('entityDetail.source') }}
                          </v-chip>

                          <!-- Confidence Score -->
                          <div v-if="sample.confidence_score" class="d-flex align-center ga-2">
                            <span class="text-caption text-medium-emphasis">{{ t('entityDetail.confidence') }}:</span>
                            <v-progress-linear
                              :model-value="sample.confidence_score * 100"
                              :color="getConfidenceColor(sample.confidence_score)"
                              height="6"
                              rounded
                              style="width: 60px;"
                            ></v-progress-linear>
                            <span class="text-caption font-weight-medium">{{ Math.round(sample.confidence_score * 100) }}%</span>
                          </div>

                          <!-- Created Date -->
                          <span v-if="sample.created_at" class="text-caption text-medium-emphasis">
                            <v-icon size="small" class="mr-1">mdi-clock-outline</v-icon>
                            {{ formatDate(sample.created_at) }}
                          </span>

                          <!-- Verified Badge -->
                          <v-chip v-if="sample.human_verified" size="small" color="success" variant="flat">
                            <v-icon start size="small">mdi-check-circle</v-icon>
                            {{ t('entityDetail.verifiedLabel') }}
                          </v-chip>
                        </div>

                        <!-- Action Buttons Row -->
                        <div v-if="sample.id && canEdit" class="d-flex align-center ga-2">
                          <!-- Verify button -->
                          <v-btn
                            v-if="!sample.human_verified"
                            size="small"
                            color="success"
                            variant="tonal"
                            @click.stop="verifyFacet(sample.id)"
                          >
                            <v-icon start size="small">mdi-check</v-icon>
                            {{ t('entityDetail.verifyAction') }}
                          </v-btn>
                          <!-- Edit button -->
                          <v-btn
                            size="small"
                            color="primary"
                            variant="tonal"
                            @click.stop="openEditFacetDialog(sample, facetGroup)"
                          >
                            <v-icon start size="small">mdi-pencil</v-icon>
                            {{ t('common.edit') }}
                          </v-btn>
                          <!-- Delete button -->
                          <v-btn
                            size="small"
                            color="error"
                            variant="tonal"
                            @click.stop="confirmDeleteFacet(sample)"
                          >
                            <v-icon start size="small">mdi-delete</v-icon>
                            {{ t('common.delete') }}
                          </v-btn>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Load More / Show Less Buttons -->
              <div class="d-flex align-center ga-2 flex-wrap">
                <v-btn
                  v-if="canLoadMore(facetGroup)"
                  variant="tonal"
                  size="small"
                  :loading="loadingMoreFacets[facetGroup.facet_type_slug]"
                  @click="loadMoreFacets(facetGroup)"
                >
                  <v-icon start>mdi-plus</v-icon>
                  {{ t('entityDetail.loadMore', { count: getRemainingCount(facetGroup) }) }}
                </v-btn>
                <v-btn
                  v-if="isExpanded(facetGroup)"
                  variant="tonal"
                  size="small"
                  @click="collapseFacets(facetGroup)"
                >
                  <v-icon start>mdi-chevron-up</v-icon>
                  {{ t('entityDetail.showLess') }}
                </v-btn>
                <v-spacer></v-spacer>
                <!-- Bulk Mode Toggle -->
                <v-btn
                  v-if="canEdit && getDisplayedFacets(facetGroup).length > 1"
                  variant="tonal"
                  size="small"
                  @click="bulkMode = !bulkMode"
                >
                  <v-icon start>{{ bulkMode ? 'mdi-close' : 'mdi-checkbox-multiple-marked' }}</v-icon>
                  {{ bulkMode ? t('common.cancel') : t('entityDetail.multiSelect') }}
                </v-btn>
              </div>

              <!-- Bulk Actions Bar -->
              <v-slide-y-transition>
                <div v-if="canEdit && bulkMode && selectedFacetIds.length > 0" class="mt-3 pa-3 rounded bg-primary-lighten-5">
                  <div class="d-flex align-center ga-2">
                    <span class="text-body-2">{{ t('entityDetail.selected', { count: selectedFacetIds.length }) }}</span>
                    <v-spacer></v-spacer>
                    <v-btn
                      size="small"
                      color="success"
                      variant="tonal"
                      :loading="bulkActionLoading"
                      @click="bulkVerify"
                    >
                      <v-icon start>mdi-check-all</v-icon>
                      {{ t('entityDetail.verifyAll') }}
                    </v-btn>
                    <v-btn
                      size="small"
                      color="error"
                      variant="tonal"
                      :loading="bulkActionLoading"
                      @click="bulkDeleteConfirm = true"
                    >
                      <v-icon start>mdi-delete</v-icon>
                      {{ t('common.delete') }}
                    </v-btn>
                  </div>
                </div>
              </v-slide-y-transition>
            </v-card-text>
          </v-expand-transition>
        </v-card>
      </v-col>
    </v-row>

    <!-- Empty State for Facets -->
    <v-card v-if="!facetsSummary?.facets_by_type?.length" class="mt-4 text-center pa-8" variant="outlined">
      <v-icon size="80" color="grey-lighten-1" class="mb-4">mdi-tag-off-outline</v-icon>
      <h3 class="text-h6 mb-2">{{ t('entityDetail.emptyState.noProperties') }}</h3>
      <p class="text-body-2 text-medium-emphasis mb-4">
        {{ t('entityDetail.emptyState.noPropertiesDesc') }}
      </p>
      <div class="d-flex justify-center ga-2">
        <v-btn v-if="canEdit" variant="tonal" color="primary" @click="$emit('add-facet')">
          <v-icon start>mdi-plus</v-icon>
          {{ t('entityDetail.emptyState.addManually') }}
        </v-btn>
        <v-btn variant="outlined" @click="$emit('switch-tab', 'sources')">
          <v-icon start>mdi-web</v-icon>
          {{ t('entityDetail.emptyState.checkDataSources') }}
        </v-btn>
      </div>
    </v-card>

    <!-- No Search Results -->
    <v-card v-else-if="facetSearchQuery && !hasSearchResults" class="mt-4 text-center pa-6" variant="outlined">
      <v-icon size="60" color="grey-lighten-1" class="mb-3">mdi-magnify-close</v-icon>
      <h3 class="text-h6 mb-2">{{ t('entityDetail.noSearchResults', { query: facetSearchQuery }) }}</h3>
      <p class="text-body-2 text-medium-emphasis mb-3">
        {{ t('entityDetail.noSearchResultsDesc') }}
      </p>
      <v-btn variant="tonal" @click="facetSearchQuery = ''">
        <v-icon start>mdi-close</v-icon>
        {{ t('entityDetail.clearSearch') }}
      </v-btn>
    </v-card>

    <!-- Bulk Delete Confirm Dialog -->
    <ConfirmDialog
      v-model="bulkDeleteConfirm"
      :title="t('entityDetail.bulkDeleteTitle')"
      :message="t('entityDetail.bulkDeleteMessage', { count: selectedFacetIds.length })"
      :confirm-text="t('common.delete')"
      confirm-color="error"
      :loading="bulkActionLoading"
      @confirm="bulkDelete"
    />

    <!-- Single Facet Delete Confirm Dialog -->
    <ConfirmDialog
      v-model="singleDeleteConfirm"
      :title="t('entityDetail.deleteFacetTitle')"
      :message="t('entityDetail.deleteFacetMessage')"
      :confirm-text="t('common.delete')"
      confirm-color="error"
      :loading="deletingFacet"
      @confirm="deleteSingleFacet"
    />

    <!-- Edit Facet Dialog -->
    <v-dialog v-model="editFacetDialog" max-width="800" scrollable>
      <v-card min-height="400">
        <v-card-title class="d-flex align-center">
          <v-icon start>mdi-pencil</v-icon>
          {{ t('entityDetail.dialog.editFacet') }}
          <span v-if="editingFacetTypeName" class="text-body-2 text-medium-emphasis ml-2">
            ({{ editingFacetTypeName }})
          </span>
        </v-card-title>
        <v-card-text>
          <!-- Structured Form -->
          <DynamicSchemaForm
            v-if="editingFacetSchema"
            v-model="editingFacetValue"
            :schema="editingFacetSchema"
          />
          <!-- Simple Text Field -->
          <v-textarea
            v-else
            v-model="editingFacetTextValue"
            :label="t('entityDetail.dialog.facetValue')"
            rows="8"
            variant="outlined"
            auto-grow
            :hint="t('entityDetail.dialog.facetValueHint')"
            persistent-hint
          ></v-textarea>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="editFacetDialog = false">{{ t('common.cancel') }}</v-btn>
          <v-btn color="primary" variant="tonal" :loading="savingFacet" @click="saveEditedFacet">{{ t('common.save') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Source Details Dialog -->
    <SourceDetailsDialog
      v-model="sourceDetailsDialog"
      :source-facet="selectedSourceFacet"
    />

    <!-- Entity Link Dialog for Facets -->
    <v-dialog v-model="entityLinkDialog" max-width="600" scrollable>
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon start>mdi-link-plus</v-icon>
          {{ t('entityDetail.facets.linkEntityTitle', 'Facet mit Entity verknüpfen') }}
        </v-card-title>
        <v-card-text>
          <v-alert type="info" variant="tonal" class="mb-4">
            {{ t('entityDetail.facets.linkEntityDescription', 'Suchen Sie nach einer Entity, um dieses Facet zu verknüpfen.') }}
          </v-alert>

          <v-autocomplete
            v-model="selectedTargetEntityId"
            v-model:search="entitySearchQuery"
            :items="entitySearchResults"
            :loading="searchingEntities"
            item-title="name"
            item-value="id"
            :label="t('entityDetail.facets.searchEntity', 'Entity suchen...')"
            prepend-inner-icon="mdi-magnify"
            variant="outlined"
            clearable
            no-filter
            @update:search="searchEntities"
          >
            <template #item="{ item, props: itemProps }">
              <v-list-item v-bind="itemProps">
                <template #prepend>
                  <v-avatar size="32" :color="item.raw.entity_type_color || 'primary'">
                    <v-icon size="small" color="white">{{ item.raw.entity_type_icon || 'mdi-folder' }}</v-icon>
                  </v-avatar>
                </template>
                <template #subtitle>
                  {{ item.raw.entity_type_name }}
                </template>
              </v-list-item>
            </template>
          </v-autocomplete>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="entityLinkDialog = false">{{ t('common.cancel') }}</v-btn>
          <v-btn
            color="primary"
            variant="tonal"
            :loading="savingEntityLink"
            :disabled="!selectedTargetEntityId"
            @click="saveEntityLink"
          >
            {{ t('common.save') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useEntityStore, type Entity, type EntityType } from '@/stores/entity'
import type { FacetValue, FacetGroup, FacetsSummary } from '@/types/entity'
import { facetApi, entityDataApi, entityApi } from '@/services/api'
import { formatDistanceToNow } from 'date-fns'
import { useSnackbar } from '@/composables/useSnackbar'
import FacetHistoryChart from '@/components/facets/FacetHistoryChart.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import DynamicSchemaForm from '@/components/DynamicSchemaForm.vue'
import SourceDetailsDialog from '@/components/entity/SourceDetailsDialog.vue'
import { GenericFacetValueRenderer } from '@/components/facets'
import { useLogger } from '@/composables/useLogger'
import { useDateFormatter } from '@/composables/useDateFormatter'
import { useFacetTypeRenderer } from '@/composables/useFacetTypeRenderer'

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

const logger = useLogger('EntityFacetsTab')
const { dateLocale, formatDate: formatLocaleDate } = useDateFormatter()
const { facetGroupToFacetType, normalizeValue } = useFacetTypeRenderer()

// =============================================================================
// Types (local-only types that aren't shared)
// =============================================================================

interface EnrichmentSources {
  pysis: { available: boolean; count: number; last_updated: string | null }
  relations: { available: boolean; count: number; last_updated: string | null }
  documents: { available: boolean; count: number; last_updated: string | null }
  extractions: { available: boolean; count: number; last_updated: string | null }
  attachments: { available: boolean; count: number; last_updated: string | null }
  existing_facets: number
}

// Compatible type for SourceDetailsDialog
interface SourceFacet {
  source_type: string
  source_url?: string | null
  document_title?: string | null
  document_url?: string | null
  verified_by?: string | null
  ai_model_used?: string | null
  confidence_score?: number | null
  created_at?: string | null
  verified_at?: string | null
  human_verified?: boolean
  value?: Record<string, unknown> | null
}

// =============================================================================
// Composables
// =============================================================================

const { t } = useI18n()
const router = useRouter()
const store = useEntityStore()
const { showSuccess, showError } = useSnackbar()

// =============================================================================
// State
// =============================================================================

// Facet Search & Expanded State
const facetSearchQuery = ref('')
const expandedFacets = ref<string[]>([])
const expandedFacetValues = ref<Record<string, FacetValue[]>>({})
const loadingMoreFacets = ref<Record<string, boolean>>({})

// Bulk Mode
const bulkMode = ref(false)
const selectedFacetIds = ref<string[]>([])
const bulkDeleteConfirm = ref(false)
const bulkActionLoading = ref(false)

// Single Facet Edit/Delete
const singleDeleteConfirm = ref(false)
const deletingFacet = ref(false)
const facetToDelete = ref<FacetValue | null>(null)
const editFacetDialog = ref(false)
const editingFacet = ref<FacetValue | null>(null)
const editingFacetGroup = ref<FacetGroup | null>(null)
const editingFacetValue = ref<Record<string, unknown>>({})
const editingFacetTextValue = ref('')
const editingFacetSchema = ref<Record<string, unknown> | null>(null)
const savingFacet = ref(false)
const editingFacetTypeName = computed(() => editingFacetGroup.value?.facet_type_name || '')

// Source Details
const sourceDetailsDialog = ref(false)
const selectedSourceFacet = ref<SourceFacet | null>(null)

// Entity Linking for Facets
const entityLinkDialog = ref(false)
const facetToLink = ref<FacetValue | null>(null)
const selectedTargetEntityId = ref<string | null>(null)
const entitySearchQuery = ref('')
const entitySearchResults = ref<Array<{
  id: string
  name: string
  entity_type_name: string
  entity_type_icon?: string
  entity_type_color?: string
}>>([])
const searchingEntities = ref(false)
const savingEntityLink = ref(false)

// Enrichment System
const enrichmentMenuOpen = ref(false)
const loadingEnrichmentSources = ref(false)
const startingEnrichment = ref(false)
const selectedEnrichmentSources = ref<string[]>([])
const enrichmentSources = ref<EnrichmentSources | null>(null)
const enrichmentTaskPolling = ref<ReturnType<typeof setInterval> | null>(null)

// =============================================================================
// Computed
// =============================================================================

// Check if any enrichment source is available
const hasAnyEnrichmentSource = computed(() => {
  if (!enrichmentSources.value) return false
  return (
    enrichmentSources.value.pysis?.available ||
    enrichmentSources.value.relations?.available ||
    enrichmentSources.value.documents?.available ||
    enrichmentSources.value.extractions?.available ||
    enrichmentSources.value.attachments?.available
  )
})

// Check if search has results
const hasSearchResults = computed(() => {
  if (!facetSearchQuery.value) return true
  const query = facetSearchQuery.value.toLowerCase()
  for (const group of props.facetsSummary?.facets_by_type || []) {
    const facets = getDisplayedFacets(group)
    if (facets.some((f: FacetValue) => matchesFacetSearch(f, query))) {
      return true
    }
  }
  return false
})

// =============================================================================
// FACET DISPLAY & SEARCH FUNCTIONS
// =============================================================================

function getDisplayedFacets(facetGroup: FacetGroup): FacetValue[] {
  const slug = facetGroup.facet_type_slug
  // If we have loaded more, use those; otherwise use sample_values
  const allFacets = expandedFacetValues.value[slug] || facetGroup.sample_values || []

  // Apply search filter
  if (facetSearchQuery.value) {
    const query = facetSearchQuery.value.toLowerCase()
    return allFacets.filter((f: FacetValue) => matchesFacetSearch(f, query))
  }

  return allFacets
}

function matchesFacetSearch(facet: FacetValue, query: string): boolean {
  // Search in text_representation
  const textRepr = facet.text_representation || ''
  if (textRepr.toLowerCase().includes(query)) return true
  // Search in value object
  const val = facet.value
  if (typeof val === 'string' && val.toLowerCase().includes(query)) return true
  if (typeof val === 'object' && val) {
    const v = val as Record<string, unknown>
    if ((v.description as string)?.toLowerCase().includes(query)) return true
    if ((v.text as string)?.toLowerCase().includes(query)) return true
    if ((v.name as string)?.toLowerCase().includes(query)) return true
    if ((v.type as string)?.toLowerCase().includes(query)) return true
    if ((v.quote as string)?.toLowerCase().includes(query)) return true
  }
  return false
}

function canLoadMore(facetGroup: FacetGroup): boolean {
  const slug = facetGroup.facet_type_slug
  const loaded = expandedFacetValues.value[slug]?.length || facetGroup.sample_values?.length || 0
  return loaded < (facetGroup.value_count ?? 0)
}

function getRemainingCount(facetGroup: FacetGroup): number {
  const slug = facetGroup.facet_type_slug
  const loaded = expandedFacetValues.value[slug]?.length || facetGroup.sample_values?.length || 0
  return Math.min(10, (facetGroup.value_count ?? 0) - loaded)
}

function isExpanded(facetGroup: FacetGroup): boolean {
  const slug = facetGroup.facet_type_slug
  return !!expandedFacetValues.value[slug]
}

async function loadMoreFacets(facetGroup: FacetGroup) {
  if (!props.entity) return
  const slug = facetGroup.facet_type_slug
  loadingMoreFacets.value[slug] = true

  try {
    const currentCount = expandedFacetValues.value[slug]?.length || facetGroup.sample_values?.length || 0
    const response = await facetApi.getFacetValues({
      entity_id: props.entity.id,
      facet_type_slug: slug,
      page: 1,
      per_page: currentCount + 10,
    })

    expandedFacetValues.value[slug] = response.data.items || []
  } catch (e) {
    logger.error('Failed to load more facets', e)
    showError(t('entityDetail.messages.loadMoreError'))
  } finally {
    loadingMoreFacets.value[slug] = false
  }
}

function collapseFacets(facetGroup: FacetGroup) {
  const slug = facetGroup.facet_type_slug
  delete expandedFacetValues.value[slug]
}

function toggleFacetExpand(slug: string) {
  const idx = expandedFacets.value.indexOf(slug)
  if (idx >= 0) {
    expandedFacets.value.splice(idx, 1)
  } else {
    expandedFacets.value.push(slug)
  }
}

// =============================================================================
// BULK ACTIONS
// =============================================================================

function toggleFacetSelection(id: string) {
  const idx = selectedFacetIds.value.indexOf(id)
  if (idx >= 0) {
    selectedFacetIds.value.splice(idx, 1)
  } else {
    selectedFacetIds.value.push(id)
  }
}

async function bulkVerify() {
  if (!props.canEdit) return
  if (selectedFacetIds.value.length === 0) return
  bulkActionLoading.value = true

  try {
    await Promise.all(
      selectedFacetIds.value.map(id => store.verifyFacetValue(id, true))
    )

    showSuccess(t('entityDetail.messages.facetsVerified', { count: selectedFacetIds.value.length }))

    // Reset selection and refresh
    selectedFacetIds.value = []
    bulkMode.value = false
    emit('facets-updated')
  } catch (e) {
    showError(t('entityDetail.messages.verifyError'))
  } finally {
    bulkActionLoading.value = false
  }
}

async function bulkDelete() {
  if (!props.canEdit) return
  if (selectedFacetIds.value.length === 0) return
  bulkActionLoading.value = true

  try {
    await Promise.all(
      selectedFacetIds.value.map(id => facetApi.deleteFacetValue(id))
    )

    showSuccess(t('entityDetail.messages.facetsDeleted', { count: selectedFacetIds.value.length }))

    // Reset selection and refresh
    selectedFacetIds.value = []
    bulkMode.value = false
    bulkDeleteConfirm.value = false
    expandedFacetValues.value = {} // Reset expanded state

    emit('facets-updated')
  } catch (e) {
    showError(t('entityDetail.messages.deleteError'))
  } finally {
    bulkActionLoading.value = false
  }
}

// =============================================================================
// SINGLE FACET ACTIONS
// =============================================================================

async function verifyFacet(facetValueId: string) {
  if (!props.canEdit) return
  try {
    await store.verifyFacetValue(facetValueId, true)
    showSuccess(t('entityDetail.messages.facetVerified'))
    emit('facets-updated')
  } catch (e) {
    showError(t('entityDetail.messages.verifyError'))
  }
}

function openAddFacetValueDialog(facetGroup: FacetGroup) {
  if (!props.canEdit) return
  emit('add-facet-value', facetGroup)
}

function openSourceDetails(facet: FacetValue) {
  // Convert FacetValue to SourceFacet format
  selectedSourceFacet.value = {
    source_type: facet.source_type || 'DOCUMENT',
    source_url: facet.source_url,
    document_title: facet.document_title,
    document_url: facet.document_url,
    verified_by: facet.verified_by,
    ai_model_used: facet.ai_model_used,
    confidence_score: facet.confidence_score,
    created_at: facet.created_at,
    verified_at: facet.verified_at,
    human_verified: facet.human_verified,
    value: facet.value as Record<string, unknown> | null,
  }
  sourceDetailsDialog.value = true
}

function openEditFacetDialog(facet: FacetValue, facetGroup: FacetGroup) {
  if (!props.canEdit) return
  editingFacet.value = facet
  editingFacetGroup.value = facetGroup
  editingFacetValue.value = { ...(facet.value as Record<string, unknown>) }
  editingFacetTextValue.value = facet.text_representation || ''
  editingFacetSchema.value = facetGroup.value_schema || null
  editFacetDialog.value = true
}

async function saveEditedFacet() {
  if (!props.canEdit) return
  if (!editingFacet.value) return

  savingFacet.value = true
  try {
    const updateData = {
      value: editingFacetSchema.value ? editingFacetValue.value : { text: editingFacetTextValue.value },
      text_representation: editingFacetSchema.value
        ? Object.values(editingFacetValue.value).filter(v => v).join(' - ').substring(0, 500)
        : editingFacetTextValue.value,
    }
    await facetApi.updateFacetValue(editingFacet.value.id, updateData)
    showSuccess(t('entityDetail.messages.facetUpdated'))
    editFacetDialog.value = false
    emit('facets-updated')
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    showError(err.response?.data?.detail || t('entityDetail.messages.facetSaveError'))
  } finally {
    savingFacet.value = false
  }
}

function confirmDeleteFacet(facet: FacetValue) {
  if (!props.canEdit) return
  facetToDelete.value = facet
  singleDeleteConfirm.value = true
}

async function deleteSingleFacet() {
  if (!props.canEdit) return
  if (!facetToDelete.value) return

  deletingFacet.value = true
  try {
    await facetApi.deleteFacetValue(facetToDelete.value.id)
    showSuccess(t('entityDetail.messages.facetDeleted'))
    singleDeleteConfirm.value = false
    facetToDelete.value = null
    emit('facets-updated')
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    showError(err.response?.data?.detail || t('entityDetail.messages.deleteError'))
  } finally {
    deletingFacet.value = false
  }
}

// =============================================================================
// ENRICHMENT FUNCTIONS
// =============================================================================

async function onEnrichmentMenuOpen(isOpen: boolean) {
  if (isOpen && !enrichmentSources.value) {
    await loadEnrichmentSources()
  }
}

async function loadEnrichmentSources() {
  if (!props.entity) return

  loadingEnrichmentSources.value = true
  try {
    const response = await entityDataApi.getEnrichmentSources(props.entity.id)
    enrichmentSources.value = response.data

    // Pre-select available sources
    selectedEnrichmentSources.value = []
    if (response.data.pysis?.available) selectedEnrichmentSources.value.push('pysis')
    if (response.data.relations?.available) selectedEnrichmentSources.value.push('relations')
    if (response.data.documents?.available) selectedEnrichmentSources.value.push('documents')
    if (response.data.extractions?.available) selectedEnrichmentSources.value.push('extractions')
  } catch (e) {
    logger.error('Failed to load enrichment sources', e)
    showError(t('entityDetail.enrichment.noSourcesAvailable'))
  } finally {
    loadingEnrichmentSources.value = false
  }
}

function formatEnrichmentDate(dateStr: string | null): string {
  if (!dateStr) return '-'
  try {
    return formatDistanceToNow(new Date(dateStr), { addSuffix: true, locale: dateLocale.value })
  } catch {
    return dateStr
  }
}

async function startEnrichmentAnalysis() {
  if (!props.canEdit) return
  if (!props.entity || selectedEnrichmentSources.value.length === 0) return

  startingEnrichment.value = true
  try {
    const response = await entityDataApi.analyzeForFacets({
      entity_id: props.entity.id,
      source_types: selectedEnrichmentSources.value,
    })

    // Close dropdown
    enrichmentMenuOpen.value = false

    // Notify parent about the started task
    emit('enrichment-started', response.data.task_id)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    showError(err.response?.data?.detail || t('entityDetail.messages.enrichError'))
  } finally {
    startingEnrichment.value = false
  }
}

function stopEnrichmentTaskPolling() {
  if (enrichmentTaskPolling.value) {
    clearInterval(enrichmentTaskPolling.value)
    enrichmentTaskPolling.value = null
  }
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

function formatDate(dateStr: string): string {
  return formatLocaleDate(dateStr, 'dd.MM.yyyy HH:mm')
}

function getConfidenceColor(score: number | null): string {
  if (!score) return 'grey'
  if (score >= 0.8) return 'success'
  if (score >= 0.5) return 'warning'
  return 'error'
}

// Source Type Helpers
function normalizeSourceType(sourceType: string | null | undefined): string {
  return (sourceType || 'DOCUMENT').toLowerCase().replace('_', '_')
}

function getFacetSourceColor(sourceType: string | null | undefined): string {
  const colors: Record<string, string> = {
    document: 'blue',
    manual: 'purple',
    pysis: 'deep-purple',
    smart_query: 'green',
    ai_assistant: 'indigo',
    import: 'teal',
  }
  return colors[normalizeSourceType(sourceType)] || 'grey'
}

function getFacetSourceIcon(sourceType: string | null | undefined): string {
  const icons: Record<string, string> = {
    document: 'mdi-file-document',
    manual: 'mdi-hand-pointing-right',
    pysis: 'mdi-database-cog',
    smart_query: 'mdi-code-tags',
    ai_assistant: 'mdi-robot',
    import: 'mdi-import',
  }
  return icons[normalizeSourceType(sourceType)] || 'mdi-file-document'
}

// Navigate to a referenced (target) entity
function navigateToTargetEntity(facet: FacetValue) {
  if (!facet.target_entity_id || !facet.target_entity_slug) return

  const entityTypeSlug = facet.target_entity_type_slug || 'entity'
  router.push({
    name: 'entity-detail',
    params: {
      typeSlug: entityTypeSlug,
      entitySlug: facet.target_entity_slug,
    },
  })
}

// =============================================================================
// ENTITY LINKING FUNCTIONS
// =============================================================================

// Open the entity link dialog for a facet
function openEntityLinkDialog(facet: FacetValue) {
  if (!props.canEdit) return
  facetToLink.value = facet
  selectedTargetEntityId.value = facet.target_entity_id || null
  entitySearchQuery.value = ''
  entitySearchResults.value = []
  entityLinkDialog.value = true
}

// Search for entities to link
let searchTimeout: ReturnType<typeof setTimeout> | null = null
async function searchEntities(query: string) {
  if (searchTimeout) clearTimeout(searchTimeout)

  if (!query || query.length < 2) {
    entitySearchResults.value = []
    return
  }

  searchTimeout = setTimeout(async () => {
    searchingEntities.value = true
    try {
      const response = await entityApi.searchEntities({ q: query, per_page: 20 })
      const items = response.data.items || []
      // Don't include the current entity
      entitySearchResults.value = items
        .filter((e: { id: string }) => e.id !== props.entity?.id)
        .map((e: {
          id: string
          name: string
          entity_type_name?: string
          entity_type?: { name?: string; icon?: string; color?: string }
        }) => ({
          id: e.id,
          name: e.name,
          entity_type_name: e.entity_type_name || e.entity_type?.name || 'Entity',
          entity_type_icon: e.entity_type?.icon || 'mdi-folder',
          entity_type_color: e.entity_type?.color || 'primary',
        }))
    } catch (e) {
      logger.error('Failed to search entities', e)
      showError(t('entityDetail.messages.entitySearchError', 'Fehler bei der Entity-Suche'))
    } finally {
      searchingEntities.value = false
    }
  }, 300)
}

// Save the entity link
async function saveEntityLink() {
  if (!props.canEdit) return
  if (!facetToLink.value || !selectedTargetEntityId.value) return

  savingEntityLink.value = true
  try {
    await facetApi.updateFacetValue(facetToLink.value.id, {
      target_entity_id: selectedTargetEntityId.value,
    })
    showSuccess(t('entityDetail.facets.entityLinked', 'Entity erfolgreich verknüpft'))
    entityLinkDialog.value = false
    emit('facets-updated')
  } catch (e) {
    logger.error('Failed to link entity', e)
    showError(t('entityDetail.messages.linkError', 'Fehler beim Verknüpfen'))
  } finally {
    savingEntityLink.value = false
  }
}

// Remove the entity link from a facet
async function unlinkEntity(facet: FacetValue) {
  if (!props.canEdit) return
  try {
    await facetApi.updateFacetValue(facet.id, {
      target_entity_id: null,
    })
    showSuccess(t('entityDetail.facets.entityUnlinked', 'Verknüpfung entfernt'))
    emit('facets-updated')
  } catch (e) {
    logger.error('Failed to unlink entity', e)
    showError(t('entityDetail.messages.unlinkError', 'Fehler beim Entfernen der Verknüpfung'))
  }
}

// =============================================================================
// Lifecycle
// =============================================================================

onUnmounted(() => {
  stopEnrichmentTaskPolling()
})
</script>

<style scoped>
.cursor-pointer {
  cursor: pointer;
}

.facet-item {
  transition: all 0.2s ease;
  border: 2px solid transparent;
}

.facet-item:hover {
  border-color: rgba(var(--v-theme-primary), 0.3);
}

.facet-item.selected {
  border-color: rgb(var(--v-theme-primary));
  background-color: rgba(var(--v-theme-primary), 0.08) !important;
}

.bg-primary-lighten-5 {
  background-color: rgba(var(--v-theme-primary), 0.1);
}

.facet-footer {
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.border-t {
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
