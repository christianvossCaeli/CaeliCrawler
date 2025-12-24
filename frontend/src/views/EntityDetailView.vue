<template>
  <div>
    <!-- Loading State -->
    <v-overlay :model-value="loading" class="align-center justify-center" persistent >
      <v-card class="pa-8 text-center" min-width="320" elevation="24">
        <v-progress-circular indeterminate size="80" width="6" color="primary" class="mb-4"></v-progress-circular>
        <div class="text-h6 mb-2">{{ t('entityDetail.loading') }}</div>
      </v-card>
    </v-overlay>

    <!-- Breadcrumbs -->
    <v-breadcrumbs :items="breadcrumbs" class="px-0">
      <template v-slot:prepend>
        <v-icon icon="mdi-home" size="small"></v-icon>
      </template>
    </v-breadcrumbs>

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
      @open-notes="notesDialog = true"
      @open-export="exportDialog = true"
      @open-edit="editDialog = true"
      @add-facet="addFacetDialog = true"
      @add-facet-value="openAddFacetValueDialog"
    />

    <!-- Tabs for Content -->
    <v-tabs v-model="activeTab" color="primary" class="mb-4">
      <v-tab value="facets">
        <v-icon start>mdi-tag-multiple</v-icon>
        {{ t('entityDetail.tabs.properties') }}
        <v-chip v-if="facetsSummary" size="x-small" class="ml-2">{{ facetsSummary.total_facet_values }}</v-chip>
      </v-tab>
      <v-tab value="connections">
        <v-icon start>mdi-sitemap</v-icon>
        {{ t('entityDetail.tabs.connections', 'Verknüpfungen') }}
        <v-chip v-if="totalConnectionsCount" size="x-small" class="ml-2">{{ totalConnectionsCount }}</v-chip>
      </v-tab>
      <v-tab value="sources">
        <v-icon start>mdi-web</v-icon>
        {{ t('entityDetail.tabs.dataSources') }}
        <v-chip v-if="dataSources.length" size="x-small" class="ml-2">{{ dataSources.length }}</v-chip>
      </v-tab>
      <v-tab value="documents">
        <v-icon start>mdi-file-document-multiple</v-icon>
        {{ t('entityDetail.tabs.documents') }}
      </v-tab>
      <v-tab v-if="entityType?.supports_pysis" value="pysis">
        <v-icon start>mdi-database-sync</v-icon>
        {{ t('entityDetail.tabs.pysis') }}
      </v-tab>
      <v-tab v-if="externalData?.has_external_data" value="api-data">
        <v-icon start>mdi-code-json</v-icon>
        {{ t('entityDetail.tabs.apiData', 'API-Daten') }}
      </v-tab>
      <v-tab value="attachments">
        <v-icon start>mdi-paperclip</v-icon>
        {{ t('entityDetail.tabs.attachments') }}
        <v-chip v-if="attachmentCount" size="x-small" class="ml-2">{{ attachmentCount }}</v-chip>
      </v-tab>
    </v-tabs>

    <v-window v-model="activeTab">
      <!-- Facets Tab -->
      <v-window-item value="facets">
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
                v-if="entityType?.supports_pysis"
                v-model="enrichmentMenuOpen"
                :close-on-content-click="false"
                location="bottom end"
                @update:model-value="onEnrichmentMenuOpen"
              >
                <template v-slot:activator="{ props }">
                  <v-btn
                    v-bind="props"
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
                      <template v-slot:label>
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
                      <template v-slot:label>
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
                      <template v-slot:label>
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
                      <template v-slot:label>
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
                      <template v-slot:label>
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
                      @updated="refreshFacetsSummary"
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
                          v-if="bulkMode"
                          :model-value="selectedFacetIds.includes(sample.id)"
                          @update:model-value="toggleFacetSelection(sample.id)"
                          hide-details
                          density="compact"
                          class="mr-2 mt-0"
                        ></v-checkbox>
                        <div class="flex-grow-1">
                      <!-- Structured Value Display for Pain Points -->
                      <template v-if="facetGroup.facet_type_slug === 'pain_point'">
                        <div class="d-flex align-start ga-2 mb-2">
                          <v-icon size="small" color="error">mdi-alert-circle</v-icon>
                          <div class="flex-grow-1">
                            <div class="text-body-1">{{ getStructuredDescription(sample) }}</div>
                            <div class="d-flex flex-wrap ga-2 mt-2">
                              <v-chip v-if="getStructuredType(sample)" size="small" variant="outlined" color="error">
                                {{ getStructuredType(sample) }}
                              </v-chip>
                              <v-chip
                                v-if="getStructuredSeverity(sample)"
                                size="small"
                                :color="getSeverityColor(getStructuredSeverity(sample))"
                              >
                                {{ getStructuredSeverity(sample) }}
                              </v-chip>
                            </div>
                            <div v-if="getStructuredQuote(sample)" class="mt-2 pa-2 rounded bg-surface-variant">
                              <v-icon size="small" class="mr-1">mdi-format-quote-open</v-icon>
                              <span class="text-body-2 font-italic">{{ getStructuredQuote(sample) }}</span>
                            </div>
                          </div>
                        </div>
                      </template>

                      <!-- Structured Value Display for Positive Signals -->
                      <template v-else-if="facetGroup.facet_type_slug === 'positive_signal'">
                        <div class="d-flex align-start ga-2 mb-2">
                          <v-icon size="small" color="success">mdi-lightbulb-on</v-icon>
                          <div class="flex-grow-1">
                            <div class="text-body-1">{{ getStructuredDescription(sample) }}</div>
                            <div class="d-flex flex-wrap ga-2 mt-2">
                              <v-chip v-if="getStructuredType(sample)" size="small" variant="outlined" color="success">
                                {{ getStructuredType(sample) }}
                              </v-chip>
                            </div>
                            <div v-if="getStructuredQuote(sample)" class="mt-2 pa-2 rounded bg-surface-variant">
                              <v-icon size="small" class="mr-1">mdi-format-quote-open</v-icon>
                              <span class="text-body-2 font-italic">{{ getStructuredQuote(sample) }}</span>
                            </div>
                          </div>
                        </div>
                      </template>

                      <!-- Structured Value Display for Contacts -->
                      <template v-else-if="facetGroup.facet_type_slug === 'contact'">
                        <div class="d-flex align-start ga-2 mb-2">
                          <v-icon size="small" color="primary">mdi-account-tie</v-icon>
                          <div class="flex-grow-1">
                            <div class="text-body-1 font-weight-medium">{{ getContactName(sample) }}</div>
                            <div v-if="getContactRole(sample)" class="text-body-2 text-medium-emphasis">{{ getContactRole(sample) }}</div>
                            <div class="d-flex flex-wrap ga-2 mt-2">
                              <v-chip v-if="getContactEmail(sample)" size="small" variant="outlined" @click.stop="copyToClipboard(getContactEmail(sample)!)">
                                <v-icon start size="small">mdi-email</v-icon>
                                {{ getContactEmail(sample) }}
                              </v-chip>
                              <v-chip v-if="getContactPhone(sample)" size="small" variant="outlined">
                                <v-icon start size="small">mdi-phone</v-icon>
                                {{ getContactPhone(sample) }}
                              </v-chip>
                              <v-chip
                                v-if="getContactSentiment(sample)"
                                size="small"
                                :color="getSentimentColor(getContactSentiment(sample))"
                              >
                                {{ getContactSentiment(sample) }}
                              </v-chip>
                            </div>
                            <div v-if="getContactStatement(sample)" class="mt-2 pa-2 rounded bg-surface-variant">
                              <v-icon size="small" class="mr-1">mdi-format-quote-open</v-icon>
                              <span class="text-body-2 font-italic">{{ getContactStatement(sample) }}</span>
                            </div>
                          </div>
                        </div>
                      </template>

                      <!-- Default/Text Display -->
                      <template v-else>
                        <div class="text-body-1">{{ formatFacetValue(sample) }}</div>
                      </template>

                      <!-- Source & Confidence Info (shown for all types) -->
                      <div class="d-flex align-center flex-wrap ga-2 mt-2">
                        <!-- Source Badge (Clickable - opens details modal) -->
                        <v-chip
                          size="x-small"
                          variant="tonal"
                          :color="getFacetSourceColor(sample.source_type)"
                          class="cursor-pointer"
                          @click.stop="openSourceDetails(sample)"
                        >
                          <v-icon start size="x-small">{{ getFacetSourceIcon(sample.source_type) }}</v-icon>
                          {{ t('entityDetail.source') }}
                        </v-chip>

                        <!-- Confidence Score -->
                        <div v-if="sample.confidence_score" class="d-flex align-center">
                          <v-progress-linear
                            :model-value="sample.confidence_score * 100"
                            :color="getConfidenceColor(sample.confidence_score)"
                            height="4"
                            class="mr-2"
                            style="max-width: 80px;"
                          ></v-progress-linear>
                          <span class="text-caption text-medium-emphasis">{{ Math.round(sample.confidence_score * 100) }}%</span>
                        </div>

                        <!-- Created Date -->
                        <span v-if="sample.created_at" class="text-caption text-medium-emphasis">
                          <v-icon size="x-small" class="mr-1">mdi-clock-outline</v-icon>
                          {{ formatDate(sample.created_at) }}
                        </span>

                        <!-- Verified Badge -->
                        <v-chip v-if="sample.human_verified" size="x-small" color="success" variant="flat">
                          <v-icon start size="x-small">mdi-check-circle</v-icon>
                          {{ t('entityDetail.verifiedLabel') }}
                        </v-chip>

                        <v-spacer></v-spacer>

                        <!-- Action buttons -->
                        <div class="d-flex ga-1">
                          <!-- Verify button -->
                          <v-btn
                            v-if="!sample.human_verified && sample.id"
                            size="x-small"
                            color="success"
                            variant="tonal"
                            @click.stop="verifyFacet(sample.id)"
                            :title="t('entityDetail.verifyAction')"
                          >
                            <v-icon size="small">mdi-check</v-icon>
                          </v-btn>
                          <!-- Edit button -->
                          <v-btn
                            v-if="sample.id"
                            size="x-small"
                            color="primary"
                            variant="tonal"
                            @click.stop="openEditFacetDialog(sample, facetGroup)"
                            :title="t('common.edit')"
                          >
                            <v-icon size="small">mdi-pencil</v-icon>
                          </v-btn>
                          <!-- Delete button -->
                          <v-btn
                            v-if="sample.id"
                            size="x-small"
                            color="error"
                            variant="tonal"
                            @click.stop="confirmDeleteFacet(sample)"
                            :title="t('common.delete')"
                          >
                            <v-icon size="small">mdi-delete</v-icon>
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
                      v-if="getDisplayedFacets(facetGroup).length > 1"
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
                    <div v-if="bulkMode && selectedFacetIds.length > 0" class="mt-3 pa-3 rounded bg-primary-lighten-5">
                      <div class="d-flex align-center ga-2">
                        <span class="text-body-2">{{ t('entityDetail.selected', { count: selectedFacetIds.length }) }}</span>
                        <v-spacer></v-spacer>
                        <v-btn
                          size="small"
                          color="success"
                          variant="tonal"
                          @click="bulkVerify"
                          :loading="bulkActionLoading"
                        >
                          <v-icon start>mdi-check-all</v-icon>
                          {{ t('entityDetail.verifyAll') }}
                        </v-btn>
                        <v-btn
                          size="small"
                          color="error"
                          variant="tonal"
                          @click="bulkDeleteConfirm = true"
                          :loading="bulkActionLoading"
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
            <v-btn variant="tonal" color="primary" @click="addFacetDialog = true">
              <v-icon start>mdi-plus</v-icon>
              {{ t('entityDetail.emptyState.addManually') }}
            </v-btn>
            <v-btn variant="outlined" @click="activeTab = 'sources'">
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
      </v-window-item>

      <!-- Relations Tab -->
      <v-window-item value="connections">
        <EntityConnectionsTab
          :entity="entity"
          :entity-type="entityType"
          :type-slug="typeSlug"
          :relations="relations"
          :children="children"
          :children-count="childrenCount"
          :children-page="childrenPage"
          :children-total-pages="childrenTotalPages"
          :children-search-query="childrenSearchQuery"
          :loading-relations="loadingRelations"
          :loading-children="loadingChildren"
          :hierarchy-enabled="flags.entityHierarchyEnabled"
          @add-relation="openAddRelationDialog"
          @edit-relation="editRelation"
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
          @link-source="linkDataSourceDialog = true"
          @edit-source="openEditSourceDialog"
          @start-crawl="startCrawl"
          @unlink-source="confirmUnlinkSource"
          @delete-source="confirmDeleteSource"
        />
      </v-window-item>

      <!-- Documents Tab -->
      <v-window-item value="documents">
        <EntityDocumentsTab
          :documents="documents"
          :loading="loadingDocuments"
        />
      </v-window-item>

      <!-- PySis Tab (only for municipalities) -->
      <v-window-item v-if="entityType?.supports_pysis" value="pysis" eager>
        <PySisTab
          v-if="entity"
          :municipality="entity.name"
        />
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
          @attachments-changed="loadAttachmentCount"
        />
      </v-window-item>

      <!-- Children Tab (Untergeordnete Entities) -->
    </v-window>

    <!-- Add Facet Dialog -->
    <AddFacetDialog
      v-model="addFacetDialog"
      :facet-type-id="newFacet.facet_type_id"
      :facet-types="applicableFacetTypes"
      :selected-facet-type="selectedFacetTypeForForm ?? null"
      :value="newFacet.value"
      :text-representation="newFacet.text_representation"
      :source-url="newFacet.source_url"
      :confidence-score="newFacet.confidence_score"
      :saving="savingFacet"
      @update:facet-type-id="onFacetTypeChange"
      @update:value="newFacet.value = $event"
      @update:text-representation="newFacet.text_representation = $event"
      @update:source-url="newFacet.source_url = $event"
      @update:confidence-score="newFacet.confidence_score = $event"
      @save="saveFacetValue"
      @close="closeAddFacetDialog"
    />

    <!-- Facet Details Dialog -->
    <FacetDetailsDialog
      v-model="facetDetailsDialog"
      :facet-group="selectedFacetGroup"
      :facet-values="facetDetails"
      @verify="verifyFacet"
      @copy-email="copyToClipboard"
    />

    <!-- Edit Entity Dialog -->
    <EntityEditDialog
      v-model="editDialog"
      :name="editForm.name"
      :external-id="editForm.external_id"
      :entity-type-name="entityType?.name"
      :saving="savingEntity"
      @update:name="editForm.name = $event"
      @update:external-id="editForm.external_id = $event"
      @save="saveEntity"
    />

    <!-- Bulk Delete Confirmation Dialog -->
    <ConfirmDialog
      v-model="bulkDeleteConfirm"
      :title="t('entityDetail.dialog.deleteFacets')"
      :message="t('entityDetail.dialog.deleteFacetsConfirm', { count: selectedFacetIds.length })"
      :subtitle="t('entityDetail.dialog.cannotUndo')"
      :confirm-text="t('common.delete')"
      confirm-icon="mdi-delete"
      :loading="bulkActionLoading"
      @confirm="bulkDelete"
    />

    <!-- Single Facet Delete Confirmation Dialog -->
    <ConfirmDialog
      v-model="singleDeleteConfirm"
      :title="t('entityDetail.dialog.deleteFacets')"
      :message="t('entityDetail.dialog.deleteFacetsConfirm', { count: 1 })"
      :subtitle="t('entityDetail.dialog.cannotUndo')"
      :confirm-text="t('common.delete')"
      confirm-icon="mdi-delete"
      :loading="deletingFacet"
      @confirm="deleteSingleFacet"
    />

    <!-- Edit Facet Dialog -->
    <v-dialog v-model="editFacetDialog" max-width="800">
      <v-card>
        <v-card-title>
          <v-icon start>mdi-pencil</v-icon>
          {{ t('entityDetail.dialog.editFacet') }}
        </v-card-title>
        <v-card-text v-if="editingFacet">
          <DynamicSchemaForm
            v-if="editingFacetSchema"
            v-model="editingFacetValue"
            :schema="editingFacetSchema"
          />
          <v-textarea
            v-else
            v-model="editingFacetTextValue"
            :label="t('entities.facet.value')"
            rows="3"
            variant="outlined"
            class="mt-2"
          ></v-textarea>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="editFacetDialog = false">{{ t('common.cancel') }}</v-btn>
          <v-btn variant="tonal" color="primary" :loading="savingFacet" @click="saveEditedFacet">
            {{ t('common.save') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Add/Edit Relation Dialog -->
    <AddRelationDialog
      v-model="addRelationDialog"
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
      :saving="savingRelation"
      @update:relation-type-id="newRelation.relation_type_id = $event"
      @update:direction="newRelation.direction = $event"
      @update:target-entity-id="newRelation.target_entity_id = $event"
      @update:attributes-json="newRelation.attributes_json = $event"
      @save="saveRelation"
      @close="closeRelationDialog"
      @search="searchEntities"
    />

    <!-- Delete Relation Confirmation -->
    <ConfirmDialog
      v-model="deleteRelationConfirm"
      :title="t('entityDetail.dialog.deleteRelation')"
      :message="t('entityDetail.dialog.deleteRelationConfirm')"
      :subtitle="relationToDelete ? `${relationToDelete.relation_type_name}: ${relationToDelete.target_entity_name || relationToDelete.source_entity_name}` : undefined"
      :confirm-text="t('common.delete')"
      :loading="deletingRelation"
      @confirm="deleteRelation"
    />

    <!-- Export Dialog -->
    <EntityExportDialog
      v-model="exportDialog"
      :format="exportFormat"
      :options="exportOptions"
      :exporting="exporting"
      @update:format="exportFormat = $event"
      @update:options="exportOptions = $event"
      @export="exportData"
    />

    <!-- Link Data Source Dialog -->
    <LinkDataSourceDialog
      v-model="linkDataSourceDialog"
      :selected-source="selectedSourceToLink"
      :available-sources="availableSourcesForLink"
      :searching="searchingSourcesForLink"
      :search-query="sourceSearchQuery"
      :linking="linkingSource"
      @update:selected-source="selectedSourceToLink = $event"
      @search="searchSourcesForLink"
      @link="linkSourceToEntity"
      @create-new="goToSourcesWithEntity"
    />

    <!-- Edit Data Source Dialog -->
    <v-dialog v-model="editSourceDialog" max-width="800" persistent scrollable>
      <v-card>
        <v-card-title class="d-flex align-center pa-4 bg-primary">
          <v-avatar color="primary-darken-1" size="40" class="mr-3">
            <v-icon color="on-primary">mdi-database-edit</v-icon>
          </v-avatar>
          <div>
            <div class="text-h6">{{ t('entityDetail.editSourceTitle') }}</div>
            <div v-if="editingSource" class="text-caption opacity-80">{{ editingSource.name }}</div>
          </div>
        </v-card-title>
        <v-card-text class="pa-4">
          <v-form ref="sourceForm" v-model="sourceFormValid">
            <v-text-field
              v-model="sourceFormData.name"
              :label="t('sources.form.name')"
              :rules="[(v: string) => !!v || t('sources.validation.nameRequired')]"
              variant="outlined"
              prepend-inner-icon="mdi-database"
              class="mb-3"
            ></v-text-field>

            <v-text-field
              v-model="sourceFormData.base_url"
              :label="t('sources.form.baseUrl')"
              :rules="[(v: string) => !!v || t('sources.validation.urlRequired')]"
              variant="outlined"
              prepend-inner-icon="mdi-link"
              class="mb-3"
            ></v-text-field>

            <v-row>
              <v-col cols="6">
                <v-number-input
                  v-model="sourceFormData.crawl_config.max_depth"
                  :label="t('sources.form.maxDepth')"
                  :min="1"
                  :max="10"
                  variant="outlined"
                  control-variant="stacked"
                ></v-number-input>
              </v-col>
              <v-col cols="6">
                <v-number-input
                  v-model="sourceFormData.crawl_config.max_pages"
                  :label="t('sources.form.maxPages')"
                  :min="1"
                  :max="10000"
                  variant="outlined"
                  control-variant="stacked"
                ></v-number-input>
              </v-col>
            </v-row>

            <v-switch
              v-model="sourceFormData.crawl_config.render_javascript"
              :label="t('sources.form.renderJs')"
              color="primary"
              class="mt-2"
            ></v-switch>
          </v-form>
        </v-card-text>
        <v-card-actions class="pa-4">
          <v-btn variant="tonal" @click="editSourceDialog = false">{{ t('common.cancel') }}</v-btn>
          <v-spacer></v-spacer>
          <v-btn
            variant="tonal"
            color="primary"
            :disabled="!sourceFormValid"
            :loading="savingSource"
            @click="saveEditedSource"
          >
            <v-icon start>mdi-check</v-icon>
            {{ t('common.save') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Source Confirmation -->
    <v-dialog v-model="deleteSourceConfirm" max-width="450">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon color="error" class="mr-2">mdi-alert</v-icon>
          {{ t('entityDetail.deleteSourceTitle') }}
        </v-card-title>
        <v-card-text>
          <p>{{ t('entityDetail.deleteSourceConfirm') }}</p>
          <p v-if="sourceToDelete" class="font-weight-medium mt-2">{{ sourceToDelete.name }}</p>
          <v-alert type="warning" variant="tonal" density="compact" class="mt-3">
            {{ t('entityDetail.deleteSourceWarning') }}
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="deleteSourceConfirm = false">{{ t('common.cancel') }}</v-btn>
          <v-btn variant="tonal" color="error" :loading="deletingSource" @click="deleteSource">
            {{ t('common.delete') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Unlink Source Confirmation -->
    <ConfirmDialog
      v-model="unlinkSourceConfirm"
      :title="t('entityDetail.unlinkSourceTitle')"
      :message="t('entityDetail.unlinkSourceConfirm')"
      :subtitle="sourceToUnlink?.name"
      icon="mdi-link-off"
      icon-color="warning"
      confirm-color="warning"
      :confirm-text="t('entityDetail.unlink')"
      :loading="unlinkingSource"
      @confirm="unlinkSource"
    />

    <!-- Enrich from PySis Dialog -->
    <v-dialog v-model="showEnrichFromPysisDialog" max-width="500">
      <v-card>
        <v-card-title>
          <v-icon start color="secondary">mdi-database-arrow-up</v-icon>
          {{ t('entityDetail.enrichFromPysisTitle') }}
        </v-card-title>
        <v-card-text>
          <v-alert type="info" variant="tonal" density="compact" class="mb-4">
            {{ t('entityDetail.enrichFromPysisDescription') }}
          </v-alert>
          <v-checkbox
            v-model="enrichPysisOverwrite"
            :label="t('entityDetail.enrichOverwrite')"
            density="compact"
            hide-details
            color="warning"
          ></v-checkbox>
          <v-alert v-if="enrichPysisOverwrite" type="warning" variant="tonal" density="compact" class="mt-3">
            {{ t('entityDetail.enrichOverwriteWarning') }}
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="showEnrichFromPysisDialog = false">{{ t('common.cancel') }}</v-btn>
          <v-btn variant="tonal" color="secondary" @click="enrichFromPysis" :loading="enrichingFromPysis">
            <v-icon start>mdi-database-arrow-up</v-icon>
            {{ t('entityDetail.startEnrichment') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Enrich Task Started Dialog -->
    <v-dialog v-model="showEnrichTaskStartedDialog" max-width="500" persistent>
      <v-card>
        <v-card-title>
          <v-icon
            start
            :color="enrichTaskStatus?.status === 'COMPLETED' ? 'success' : enrichTaskStatus?.status === 'FAILED' ? 'error' : 'primary'"
          >
            {{
              enrichTaskStatus?.status === 'COMPLETED' ? 'mdi-check-circle' :
              enrichTaskStatus?.status === 'FAILED' ? 'mdi-alert-circle' :
              'mdi-cog-sync'
            }}
          </v-icon>
          {{
            enrichTaskStatus?.status === 'COMPLETED' ? t('entityDetail.enrichCompleted') :
            enrichTaskStatus?.status === 'FAILED' ? t('entityDetail.enrichFailed') :
            enrichTaskStatus?.status === 'RUNNING' ? t('entityDetail.enrichRunning') :
            t('entityDetail.taskStarted')
          }}
        </v-card-title>
        <v-card-text>
          <!-- Running state with progress -->
          <template v-if="enrichTaskStatus?.status === 'RUNNING'">
            <v-progress-linear
              :model-value="enrichTaskStatus.progress_percent"
              :indeterminate="enrichTaskStatus.progress_total === 0"
              color="primary"
              class="mb-3"
              rounded
            ></v-progress-linear>
            <p v-if="enrichTaskStatus.current_item" class="text-body-2 mb-1">
              {{ t('entityDetail.processing') }}: {{ enrichTaskStatus.current_item }}
            </p>
            <p v-if="enrichTaskStatus.progress_total > 0" class="text-caption text-medium-emphasis">
              {{ enrichTaskStatus.progress_current }} / {{ enrichTaskStatus.progress_total }}
            </p>
          </template>

          <!-- Completed state -->
          <template v-else-if="enrichTaskStatus?.status === 'COMPLETED'">
            <p class="text-success">
              {{ t('entityDetail.enrichSuccessMessage', { count: enrichTaskStatus.fields_extracted || 0 }) }}
            </p>
          </template>

          <!-- Failed state -->
          <template v-else-if="enrichTaskStatus?.status === 'FAILED'">
            <p class="text-error">
              {{ enrichTaskStatus.error_message || t('entityDetail.messages.enrichError') }}
            </p>
          </template>

          <!-- Initial state (waiting for first poll) -->
          <template v-else>
            <p>{{ t('entityDetail.enrichTaskStartedMessage') }}</p>
            <v-progress-linear indeterminate color="primary" class="mt-3"></v-progress-linear>
          </template>

          <p class="text-caption text-medium-emphasis mt-3">
            {{ t('entityDetail.taskId') }}: <code>{{ enrichTaskId }}</code>
          </p>
        </v-card-text>
        <v-card-actions v-if="!enrichTaskStatus || ['COMPLETED', 'FAILED', 'CANCELLED'].includes(enrichTaskStatus.status)">
          <v-spacer></v-spacer>
          <v-btn variant="tonal" color="primary" @click="showEnrichTaskStartedDialog = false; enrichTaskStatus = null">
            {{ t('common.close') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Source Details Dialog -->
    <SourceDetailsDialog
      v-model="sourceDetailsDialog"
      :source-facet="selectedSourceFacet"
    />

    <!-- Notes Dialog -->
    <EntityNotesDialog
      v-model="notesDialog"
      :notes="notes"
      :new-note="newNote"
      :saving-note="savingNote"
      @update:new-note="newNote = $event"
      @save-note="saveNote"
      @delete-note="deleteNote"
    />

    <!-- Facet Enrichment Review Modal -->
    <FacetEnrichmentReview
      v-model="showEnrichmentReviewDialog"
      :task-id="enrichmentTaskId"
      :task-status="enrichmentTaskStatus"
      :preview-data="enrichmentPreviewData"
      @close="onEnrichmentReviewClose"
      @minimize="onEnrichmentReviewMinimize"
      @applied="onEnrichmentApplied"
    />

    <!-- Minimized Task Toast/Snackbar -->
    <v-snackbar
      v-model="showMinimizedTaskSnackbar"
      :timeout="-1"
      color="info"
      location="bottom end"
    >
      <div class="d-flex align-center" @click="reopenEnrichmentReview" style="cursor: pointer">
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
import { useEntityStore, type FacetValue, type Entity, type EntityType } from '@/stores/entity'
import { adminApi, entityApi, facetApi, pysisApi, aiTasksApi, entityDataApi, attachmentApi, relationApi } from '@/services/api'
import { format, formatDistanceToNow } from 'date-fns'
import { de } from 'date-fns/locale'
import { useSnackbar } from '@/composables/useSnackbar'
import { useFeatureFlags } from '@/composables/useFeatureFlags'
import PySisTab from '@/components/PySisTab.vue'
import FacetEnrichmentReview from '@/components/FacetEnrichmentReview.vue'
import DynamicSchemaForm from '@/components/DynamicSchemaForm.vue'
import EntityAttachmentsTab from '@/components/entity/EntityAttachmentsTab.vue'
import EntityDetailHeader from '@/components/entity/EntityDetailHeader.vue'
import EntityConnectionsTab from '@/components/entity/EntityConnectionsTab.vue'
import EntitySourcesTab from '@/components/entity/EntitySourcesTab.vue'
import EntityApiDataTab from '@/components/entity/EntityApiDataTab.vue'
import EntityNotesDialog from '@/components/entity/EntityNotesDialog.vue'
import EntityExportDialog from '@/components/entity/EntityExportDialog.vue'
import EntityDocumentsTab from '@/components/entity/EntityDocumentsTab.vue'
import EntityEditDialog from '@/components/entity/EntityEditDialog.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import FacetHistoryChart from '@/components/facets/FacetHistoryChart.vue'
import FacetDetailsDialog from '@/components/entity/FacetDetailsDialog.vue'
import AddFacetDialog from '@/components/entity/AddFacetDialog.vue'
import AddRelationDialog from '@/components/entity/AddRelationDialog.vue'
import LinkDataSourceDialog from '@/components/entity/LinkDataSourceDialog.vue'
import SourceDetailsDialog from '@/components/entity/SourceDetailsDialog.vue'

const { t } = useI18n()
const { flags } = useFeatureFlags()

// ============================================================================
// Local Types
// ============================================================================

interface FacetGroup {
  facet_type_id: string
  facet_type_slug: string
  facet_type_name: string
  facet_type_icon: string
  facet_type_color: string
  facet_type_value_type?: string
  value_count: number
  verified_count: number
  sample_values: FacetValue[]
}

interface FacetsSummary {
  total_facet_values: number
  verified_count: number
  facets_by_type: FacetGroup[]
}

interface Relation {
  id: string
  relation_type_id: string
  source_entity_id: string
  source_entity_name: string
  source_entity_slug: string
  source_entity_type_slug: string
  target_entity_id: string
  target_entity_name: string
  target_entity_slug: string
  target_entity_type_slug: string
  relation_type_name: string
  relation_type_name_inverse: string | null
  relation_type_color: string | null
  attributes: Record<string, any>
  human_verified: boolean
}

interface DataSource {
  id: string
  name: string
  base_url: string
  status: string
  source_type?: string
  is_direct_link?: boolean
  document_count?: number
  last_crawl?: string
  hasRunningJob?: boolean
}

interface Note {
  id: string
  content: string
  author: string
  created_at: string
}

// ============================================================================
// Entity Cache (for performance)
// ============================================================================
const entityCache = new Map<string, { data: any; timestamp: number }>()
const CACHE_TTL = 5 * 60 * 1000 // 5 minutes

function getCachedData(key: string): any | null {
  const cached = entityCache.get(key)
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    return cached.data
  }
  return null
}

function setCachedData(key: string, data: any) {
  entityCache.set(key, { data, timestamp: Date.now() })
}

const { showSuccess, showError } = useSnackbar()
const route = useRoute()
const router = useRouter()
const store = useEntityStore()

// Route params
const typeSlug = computed(() => route.params.typeSlug as string)
const entitySlug = computed(() => route.params.entitySlug as string)

// State
const loading = ref(true)
const activeTab = ref('facets')
const expandedFacets = ref<string[]>([])

// Entity data
const entity = computed<Entity | null>(() => store.selectedEntity)
const entityType = computed<EntityType | null>(() => store.selectedEntityType)
const facetsSummary = ref<FacetsSummary | null>(null)
const relations = ref<Relation[]>([])
const dataSources = ref<DataSource[]>([])
const documents = ref<any[]>([])
const externalData = ref<any>(null)
const attachmentCount = ref(0)

// Children (Untergeordnete Entities) state
const children = ref<Entity[]>([])
const childrenCount = ref(0)
const childrenPage = ref(1)
const childrenTotalPages = ref(1)
const childrenSearchQuery = ref('')
const loadingChildren = ref(false)
const childrenLoaded = ref(false)

// Loading states
const loadingDataSources = ref(false)
const loadingDocuments = ref(false)
const startingCrawl = ref<string | null>(null)

// Data Source Management State
const linkDataSourceDialog = ref(false)
const editSourceDialog = ref(false)
const deleteSourceConfirm = ref(false)
const unlinkSourceConfirm = ref(false)
const selectedSourceToLink = ref<any>(null)
const availableSourcesForLink = ref<any[]>([])
const searchingSourcesForLink = ref(false)
const sourceSearchQuery = ref('')
const editingSource = ref<any>(null)
const sourceToDelete = ref<any>(null)
const sourceToUnlink = ref<any>(null)
const sourceFormValid = ref(false)
const savingSource = ref(false)
const deletingSource = ref(false)
const unlinkingSource = ref(false)
const linkingSource = ref(false)
const sourceFormData = ref({
  name: '',
  base_url: '',
  crawl_config: {
    max_depth: 3,
    max_pages: 100,
    render_javascript: false,
  },
})

// Dialogs
const addFacetDialog = ref(false)
const addRelationDialog = ref(false)
const facetDetailsDialog = ref(false)
const editDialog = ref(false)
const selectedFacetGroup = ref<any>(null)
const facetDetails = ref<any[]>([])

// Forms
const newFacet = ref({
  facet_type_id: '',
  text_representation: '',
  source_url: '',
  confidence_score: 0.8,
  value: {} as Record<string, any>,
})

// Relation CRUD State
const relationTypes = ref<any[]>([])
const loadingRelationTypes = ref(false)
const editingRelation = ref<Relation | null>(null)
const newRelation = ref({
  relation_type_id: '',
  target_entity_id: '',
  direction: 'outgoing' as 'outgoing' | 'incoming',
  attributes_json: '',
})
const targetEntities = ref<any[]>([])
const searchingEntities = ref(false)
const entitySearchQuery = ref('')
const savingRelation = ref(false)
const deleteRelationConfirm = ref(false)
const relationToDelete = ref<Relation | null>(null)
const deletingRelation = ref(false)

const editForm = ref({
  name: '',
  external_id: '',
})

const savingFacet = ref(false)
const savingEntity = ref(false)

// Facet Search & Expanded State
const facetSearchQuery = ref('')
const expandedFacetValues = ref<Record<string, any[]>>({}) // Stores loaded facets per type
const loadingMoreFacets = ref<Record<string, boolean>>({})

// Bulk Mode
const bulkMode = ref(false)
const selectedFacetIds = ref<string[]>([])
const bulkDeleteConfirm = ref(false)
const bulkActionLoading = ref(false)

// Single Facet Edit/Delete
const singleDeleteConfirm = ref(false)
const deletingFacet = ref(false)
const facetToDelete = ref<any>(null)
const editFacetDialog = ref(false)
const editingFacet = ref<any>(null)
const editingFacetGroup = ref<any>(null)
const editingFacetValue = ref<Record<string, any>>({})
const editingFacetTextValue = ref('')
const editingFacetSchema = ref<any>(null)

// Source Details
const sourceDetailsDialog = ref(false)
const selectedSourceFacet = ref<any>(null)

// Export
const exportDialog = ref(false)
const exportFormat = ref('csv')
const exportOptions = ref({
  facets: true,
  relations: true,
  dataSources: false,
  notes: false,
})
const exporting = ref(false)

// Notes
const notesDialog = ref(false)
const notes = ref<Note[]>([])
const newNote = ref('')
const savingNote = ref(false)

// Relations Lazy Loading
const loadingRelations = ref(false)
const relationsLoaded = ref(false)

// PySis-Facets Enrichment
const hasPysisProcesses = ref(false)
const showEnrichFromPysisDialog = ref(false)
const showEnrichTaskStartedDialog = ref(false)
const enrichPysisOverwrite = ref(false)
const enrichingFromPysis = ref(false)
const enrichTaskId = ref('')

// Task Polling (legacy PySIS)
const enrichTaskPolling = ref<ReturnType<typeof setInterval> | null>(null)
const enrichTaskStatus = ref<{
  status: string
  progress_current: number
  progress_total: number
  progress_percent: number
  current_item: string | null
  error_message: string | null
  fields_extracted: number
} | null>(null)

// New Enrichment System
const enrichmentMenuOpen = ref(false)
const loadingEnrichmentSources = ref(false)
const startingEnrichment = ref(false)
const selectedEnrichmentSources = ref<string[]>([])
const enrichmentSources = ref<{
  pysis: { available: boolean; count: number; last_updated: string | null }
  relations: { available: boolean; count: number; last_updated: string | null }
  documents: { available: boolean; count: number; last_updated: string | null }
  extractions: { available: boolean; count: number; last_updated: string | null }
  attachments: { available: boolean; count: number; last_updated: string | null }
  existing_facets: number
} | null>(null)

// Enrichment Review Modal
const showEnrichmentReviewDialog = ref(false)
const enrichmentTaskId = ref<string | null>(null)
const enrichmentTaskPolling = ref<ReturnType<typeof setInterval> | null>(null)
const enrichmentTaskStatus = ref<{
  status: string
  progress_current?: number
  progress_total?: number
  current_item?: string
  error_message?: string
} | null>(null)
const enrichmentPreviewData = ref<{
  new_facets?: any[]
  updates?: any[]
  analysis_summary?: any
} | null>(null)
const showMinimizedTaskSnackbar = ref(false)

// Computed: Check if any enrichment source is available
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

// Computed
const breadcrumbs = computed(() => [
  { title: t('nav.dashboard'), to: '/' },
  { title: entityType.value?.name_plural || t('nav.entities'), to: `/entities/${typeSlug.value}` },
  { title: entity.value?.name || '...', disabled: true },
])

/// Total connections count: relations + children + parent
const totalConnectionsCount = computed(() => {
  const relationCount = entity.value?.relation_count || 0
  // Use children_count from API response (always available), fall back to loaded childrenCount
  const childCount = entity.value?.children_count || childrenCount.value || 0
  const hasParent = entity.value?.parent_id ? 1 : 0
  return relationCount + childCount + hasParent
})

// Filter facet types applicable to current entity type
const applicableFacetTypes = computed(() => {
  const entityTypeSlug = entityType.value?.slug
  if (!entityTypeSlug) return store.activeFacetTypes

  return store.activeFacetTypes.filter(ft => {
    // If no applicable types specified, facet applies to all entity types
    if (!ft.applicable_entity_type_slugs || ft.applicable_entity_type_slugs.length === 0) {
      return true
    }
    // Otherwise check if current entity type is in the list
    return ft.applicable_entity_type_slugs.includes(entityTypeSlug)
  })
})

// Get the selected facet type for the form
const selectedFacetTypeForForm = computed(() => {
  if (!newFacet.value.facet_type_id) return null
  return store.facetTypes.find(ft => ft.id === newFacet.value.facet_type_id)
})

// Check if search has results
const hasSearchResults = computed(() => {
  if (!facetSearchQuery.value) return true
  const query = facetSearchQuery.value.toLowerCase()
  for (const group of facetsSummary.value?.facets_by_type || []) {
    const facets = getDisplayedFacets(group)
    if (facets.some((f: any) => matchesFacetSearch(f, query))) {
      return true
    }
  }
  return false
})


// Methods
async function loadEntityData() {
  loading.value = true
  try {
    // Load entity type first
    await store.fetchEntityTypeBySlug(typeSlug.value)

    // Load entity
    await store.fetchEntityBySlug(typeSlug.value, entitySlug.value)

    if (!entity.value) {
      showError(t('entityDetail.messages.entityNotFound'))
      router.push(`/entities/${typeSlug.value}`)
      return
    }

    // Load facet types if not loaded
    if (store.facetTypes.length === 0) {
      await store.fetchFacetTypes()
    }

    // Load facets summary
    facetsSummary.value = await store.fetchEntityFacetsSummary(entity.value.id)

    // Expand first facet group by default
    if (facetsSummary.value?.facets_by_type?.length) {
      expandedFacets.value = [facetsSummary.value.facets_by_type[0].facet_type_slug]
    }

    // Load notes (from localStorage for now)
    await loadNotes()

    // Reset lazy loading flags
    relationsLoaded.value = false
    expandedFacetValues.value = {}

    // Populate edit form
    editForm.value = {
      name: entity.value.name,
      external_id: entity.value.external_id || '',
    }

    // Check if entity has PySis processes (for municipalities)
    await checkPysisProcesses()

    // Load external API data (non-blocking)
    loadExternalData()

    // Load attachment count (non-blocking)
    loadAttachmentCount()

    // If connections tab is active, load children
    if (activeTab.value === 'connections') {
      loadChildren()
    }
  } catch (e) {
    console.error('Failed to load entity', e)
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
    console.error('Failed to load external data', e)
    externalData.value = null
    showError(t('entityDetail.messages.externalDataLoadError'))
  }
}

async function loadRelations() {
  if (!entity.value || relationsLoaded.value) return

  // Check cache first
  const cacheKey = `relations_${entity.value.id}`
  const cached = getCachedData(cacheKey)
  if (cached) {
    relations.value = cached
    relationsLoaded.value = true
    return
  }

  loadingRelations.value = true
  try {
    const result = await store.fetchEntityRelations({
      entity_id: entity.value.id,
    })
    relations.value = result.items || []
    relationsLoaded.value = true

    // Cache the result
    setCachedData(cacheKey, relations.value)
  } catch (e) {
    console.error('Failed to load relations', e)
    showError(t('entityDetail.messages.relationsLoadError'))
  } finally {
    loadingRelations.value = false
  }
}

// =============================================================================
// FACET DISPLAY & SEARCH FUNCTIONS
// =============================================================================

function getDisplayedFacets(facetGroup: any): any[] {
  const slug = facetGroup.facet_type_slug
  // If we have loaded more, use those; otherwise use sample_values
  // API already returns sorted: verified first, then by confidence desc, then by created_at desc
  const allFacets = expandedFacetValues.value[slug] || facetGroup.sample_values || []

  // Apply search filter
  if (facetSearchQuery.value) {
    const query = facetSearchQuery.value.toLowerCase()
    return allFacets.filter((f: any) => matchesFacetSearch(f, query))
  }

  return allFacets
}

function matchesFacetSearch(facet: any, query: string): boolean {
  // Search in text_representation (handle both old 'text' and new 'text_representation' formats)
  const textRepr = facet.text_representation || facet.text || ''
  if (textRepr.toLowerCase().includes(query)) return true
  // Search in value object
  const val = facet.value
  if (typeof val === 'string' && val.toLowerCase().includes(query)) return true
  if (typeof val === 'object' && val) {
    if (val.description?.toLowerCase().includes(query)) return true
    if (val.text?.toLowerCase().includes(query)) return true
    if (val.name?.toLowerCase().includes(query)) return true
    if (val.type?.toLowerCase().includes(query)) return true
    if (val.quote?.toLowerCase().includes(query)) return true
  }
  return false
}

function canLoadMore(facetGroup: any): boolean {
  const slug = facetGroup.facet_type_slug
  const loaded = expandedFacetValues.value[slug]?.length || facetGroup.sample_values?.length || 0
  return loaded < facetGroup.value_count
}

function getRemainingCount(facetGroup: any): number {
  const slug = facetGroup.facet_type_slug
  const loaded = expandedFacetValues.value[slug]?.length || facetGroup.sample_values?.length || 0
  return Math.min(10, facetGroup.value_count - loaded)
}

function isExpanded(facetGroup: any): boolean {
  const slug = facetGroup.facet_type_slug
  return !!expandedFacetValues.value[slug]
}

async function loadMoreFacets(facetGroup: any) {
  if (!entity.value) return
  const slug = facetGroup.facet_type_slug
  loadingMoreFacets.value[slug] = true

  try {
    const currentCount = expandedFacetValues.value[slug]?.length || facetGroup.sample_values?.length || 0
    const response = await facetApi.getFacetValues({
      entity_id: entity.value.id,
      facet_type_slug: slug,
      page: 1,
      per_page: currentCount + 10, // Load 10 more
    })

    expandedFacetValues.value[slug] = response.data.items || []
  } catch (e) {
    console.error('Failed to load more facets', e)
    showError(t('entityDetail.messages.loadMoreError'))
  } finally {
    loadingMoreFacets.value[slug] = false
  }
}

function collapseFacets(facetGroup: any) {
  const slug = facetGroup.facet_type_slug
  delete expandedFacetValues.value[slug]
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
  if (selectedFacetIds.value.length === 0) return
  bulkActionLoading.value = true

  try {
    // Verify all selected facets
    await Promise.all(
      selectedFacetIds.value.map(id => store.verifyFacetValue(id, true))
    )

    showSuccess(t('entityDetail.messages.facetsVerified', { count: selectedFacetIds.value.length }))

    // Reset selection and refresh
    selectedFacetIds.value = []
    bulkMode.value = false
    if (entity.value) {
      facetsSummary.value = await store.fetchEntityFacetsSummary(entity.value.id)
    }
  } catch (e) {
    showError(t('entityDetail.messages.verifyError'))
  } finally {
    bulkActionLoading.value = false
  }
}

async function bulkDelete() {
  if (selectedFacetIds.value.length === 0) return
  bulkActionLoading.value = true

  try {
    // Delete all selected facets
    await Promise.all(
      selectedFacetIds.value.map(id => facetApi.deleteFacetValue(id))
    )

    showSuccess(t('entityDetail.messages.facetsDeleted', { count: selectedFacetIds.value.length }))

    // Reset selection and refresh
    selectedFacetIds.value = []
    bulkMode.value = false
    bulkDeleteConfirm.value = false
    expandedFacetValues.value = {} // Reset expanded state

    if (entity.value) {
      facetsSummary.value = await store.fetchEntityFacetsSummary(entity.value.id)
    }
  } catch (e) {
    showError(t('entityDetail.messages.deleteError'))
  } finally {
    bulkActionLoading.value = false
  }
}

// =============================================================================
// EXPORT FUNCTIONS
// =============================================================================

async function exportData() {
  if (!entity.value) return
  exporting.value = true

  try {
    const data: any = {
      entity: {
        id: entity.value.id,
        name: entity.value.name,
        type: entityType.value?.name,
        external_id: entity.value.external_id,
        attributes: entity.value.core_attributes,
      },
    }

    // Collect selected data
    if (exportOptions.value.facets && facetsSummary.value?.facets_by_type) {
      data.facets = {}
      for (const group of facetsSummary.value.facets_by_type) {
        // Load all facets for this type
        const response = await facetApi.getFacetValues({
          entity_id: entity.value.id,
          facet_type_slug: group.facet_type_slug,
          per_page: 10000,
        })
        data.facets[group.facet_type_name] = (response.data.items || []).map((f: any) => ({
          value: f.text_representation || getStructuredDescription(f),
          type: getStructuredType(f),
          severity: getStructuredSeverity(f),
          verified: f.human_verified,
          confidence: f.confidence_score,
          source_url: f.source_url,
        }))
      }
    }

    if (exportOptions.value.relations) {
      data.relations = relations.value.map(r => ({
        type: r.relation_type_name,
        target: r.source_entity_id === entity.value?.id ? r.target_entity_name : r.source_entity_name,
        verified: r.human_verified,
      }))
    }

    if (exportOptions.value.dataSources) {
      data.dataSources = dataSources.value.map(s => ({
        name: s.name,
        url: s.base_url,
        status: s.status,
      }))
    }

    if (exportOptions.value.notes) {
      data.notes = notes.value.map(n => ({
        content: n.content,
        author: n.author,
        date: n.created_at,
      }))
    }

    // Generate export file
    if (exportFormat.value === 'json') {
      downloadFile(
        JSON.stringify(data, null, 2),
        `${entity.value.name}_export.json`,
        'application/json'
      )
    } else if (exportFormat.value === 'csv') {
      const csv = generateCSV(data)
      downloadFile(csv, `${entity.value.name}_export.csv`, 'text/csv')
    } else if (exportFormat.value === 'pdf') {
      // For PDF, we'd need a library like jsPDF or generate on backend
      // For now, show message
      showError(t('entityDetail.messages.pdfNotAvailable'))
      exporting.value = false
      return
    }

    showSuccess(t('entityDetail.messages.exportSuccess'))
    exportDialog.value = false
  } catch (e) {
    console.error('Export failed', e)
    showError(t('entityDetail.messages.exportError'))
  } finally {
    exporting.value = false
  }
}

function generateCSV(data: any): string {
  const lines: string[] = []

  // Entity info
  lines.push(`# ${t('entityDetail.csv.entityInformation')}`)
  lines.push(`${t('entityDetail.csv.name')},${escapeCSV(data.entity.name)}`)
  lines.push(`${t('entityDetail.csv.type')},${escapeCSV(data.entity.type || '')}`)
  lines.push(`${t('entityDetail.csv.externalId')},${escapeCSV(data.entity.external_id || '')}`)
  lines.push('')

  // Facets
  if (data.facets) {
    for (const [typeName, facets] of Object.entries(data.facets)) {
      lines.push(`# ${typeName}`)
      lines.push(`${t('entityDetail.csv.value')},${t('entityDetail.csv.type')},${t('entityDetail.csv.severity')},${t('entityDetail.csv.verified')},${t('entityDetail.csv.confidence')}`)
      for (const f of facets as any[]) {
        lines.push([
          escapeCSV(f.value || ''),
          escapeCSV(f.type || ''),
          escapeCSV(f.severity || ''),
          f.verified ? t('common.yes') : t('common.no'),
          f.confidence ? `${Math.round(f.confidence * 100)}%` : '',
        ].join(','))
      }
      lines.push('')
    }
  }

  // Relations
  if (data.relations?.length) {
    lines.push(`# ${t('entityDetail.csv.relations')}`)
    lines.push(`${t('entityDetail.csv.type')},${t('entityDetail.csv.target')},${t('entityDetail.csv.verified')}`)
    for (const r of data.relations) {
      lines.push([
        escapeCSV(r.type),
        escapeCSV(r.target),
        r.verified ? t('common.yes') : t('common.no'),
      ].join(','))
    }
    lines.push('')
  }

  // Notes
  if (data.notes?.length) {
    lines.push(`# ${t('entityDetail.csv.notes')}`)
    lines.push(`${t('entityDetail.csv.date')},${t('entityDetail.csv.author')},${t('entityDetail.csv.content')}`)
    for (const n of data.notes) {
      lines.push([
        escapeCSV(n.date || ''),
        escapeCSV(n.author || ''),
        escapeCSV(n.content || ''),
      ].join(','))
    }
  }

  return lines.join('\n')
}

function escapeCSV(value: string): string {
  if (value.includes(',') || value.includes('"') || value.includes('\n')) {
    return `"${value.replace(/"/g, '""')}"`
  }
  return value
}

function downloadFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

// =============================================================================
// NOTES FUNCTIONS
// =============================================================================

async function loadNotes() {
  if (!entity.value) return
  try {
    // Notes are stored as a special facet type or in a separate endpoint
    // For now, we'll store them in localStorage as a simple solution
    const key = `entity_notes_${entity.value.id}`
    const stored = localStorage.getItem(key)
    notes.value = stored ? JSON.parse(stored) : []
  } catch (e) {
    console.error('Failed to load notes', e)
    notes.value = []
  }
}

async function saveNote() {
  if (!entity.value || !newNote.value.trim()) return
  savingNote.value = true

  try {
    const note = {
      id: crypto.randomUUID(),
      content: newNote.value.trim(),
      author: t('entityDetail.currentUser'), // Would come from auth
      created_at: new Date().toISOString(),
    }

    notes.value.unshift(note)

    // Save to localStorage (would be API in production)
    const key = `entity_notes_${entity.value.id}`
    localStorage.setItem(key, JSON.stringify(notes.value))

    newNote.value = ''
    showSuccess(t('entityDetail.messages.noteSaved'))
  } catch (e) {
    showError(t('entityDetail.messages.noteSaveError'))
  } finally {
    savingNote.value = false
  }
}

async function deleteNote(noteId: string) {
  if (!entity.value) return

  try {
    notes.value = notes.value.filter(n => n.id !== noteId)

    // Save to localStorage
    const key = `entity_notes_${entity.value.id}`
    localStorage.setItem(key, JSON.stringify(notes.value))

    showSuccess(t('entityDetail.messages.noteDeleted'))
  } catch (e) {
    showError(t('entityDetail.messages.noteDeleteError'))
  }
}

async function loadDataSources() {
  if (!entity.value) return

  // Check cache first
  const cacheKey = `datasources_${entity.value.id}`
  const cached = getCachedData(cacheKey)
  if (cached) {
    dataSources.value = cached
    return
  }

  loadingDataSources.value = true
  try {
    // Get sources via the new traceability endpoint:
    // Entity -> FacetValues -> Documents -> DataSources
    const response = await entityApi.getEntitySources(entity.value.id)
    dataSources.value = response.data.sources || []

    // Cache the result
    setCachedData(cacheKey, dataSources.value)
  } catch (e) {
    console.error('Failed to load data sources', e)
    dataSources.value = []
    showError(t('entityDetail.messages.dataSourcesLoadError'))
  } finally {
    loadingDataSources.value = false
  }
}

async function loadDocuments() {
  if (!entity.value) return
  loadingDocuments.value = true
  try {
    // Get documents via the traceability endpoint:
    // Entity -> FacetValues -> Documents
    const response = await entityApi.getEntityDocuments(entity.value.id)
    documents.value = response.data.documents || []
  } catch (e) {
    console.error('Failed to load documents', e)
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
    console.error('Failed to load attachment count', e)
    attachmentCount.value = 0
  }
}

// ============================================================================
// Data Source Management Functions
// ============================================================================

let sourceSearchTimeout: ReturnType<typeof setTimeout> | null = null

async function searchSourcesForLink(query: string) {
  sourceSearchQuery.value = query
  if (!query || query.length < 2) {
    availableSourcesForLink.value = []
    return
  }

  if (sourceSearchTimeout) clearTimeout(sourceSearchTimeout)
  sourceSearchTimeout = setTimeout(async () => {
    searchingSourcesForLink.value = true
    try {
      const response = await adminApi.getSources({ search: query, per_page: 20 })
      // Filter out already linked sources
      const linkedIds = new Set(dataSources.value.map((s: any) => s.id))
      availableSourcesForLink.value = (response.data.items || []).filter(
        (s: any) => !linkedIds.has(s.id)
      )
    } catch (e) {
      console.error('Failed to search sources:', e)
      availableSourcesForLink.value = []
      showError(t('entityDetail.messages.sourceSearchError'))
    } finally {
      searchingSourcesForLink.value = false
    }
  }, 300)
}

async function linkSourceToEntity() {
  if (!selectedSourceToLink.value || !entity.value) return

  linkingSource.value = true
  try {
    // Update the source's extra_data to add this entity to entity_ids (N:M)
    const sourceId = selectedSourceToLink.value.id
    const currentExtraData = selectedSourceToLink.value.extra_data || {}

    // Support legacy entity_id and new entity_ids array
    const existingEntityIds = currentExtraData.entity_ids ||
      (currentExtraData.entity_id ? [currentExtraData.entity_id] : [])

    // Add new entity if not already linked
    const newEntityIds = existingEntityIds.includes(entity.value.id)
      ? existingEntityIds
      : [...existingEntityIds, entity.value.id]

    await adminApi.updateSource(sourceId, {
      extra_data: {
        ...currentExtraData,
        entity_ids: newEntityIds,
        // Remove legacy field
        entity_id: undefined,
      },
    })

    showSuccess(t('entityDetail.messages.sourceLinkSuccess'))
    linkDataSourceDialog.value = false
    selectedSourceToLink.value = null

    // Invalidate cache and reload
    entityCache.delete(`datasources_${entity.value.id}`)
    await loadDataSources()
  } catch (e) {
    console.error('Failed to link source:', e)
    showError(t('entityDetail.messages.sourceLinkError'))
  } finally {
    linkingSource.value = false
  }
}

function openEditSourceDialog(source: any) {
  editingSource.value = source
  sourceFormData.value = {
    name: source.name || '',
    base_url: source.base_url || '',
    crawl_config: {
      max_depth: source.crawl_config?.max_depth || 3,
      max_pages: source.crawl_config?.max_pages || 100,
      render_javascript: source.crawl_config?.render_javascript || false,
    },
  }
  editSourceDialog.value = true
}

async function saveEditedSource() {
  if (!editingSource.value) return

  savingSource.value = true
  try {
    await adminApi.updateSource(editingSource.value.id, {
      name: sourceFormData.value.name,
      base_url: sourceFormData.value.base_url,
      crawl_config: {
        ...editingSource.value.crawl_config,
        ...sourceFormData.value.crawl_config,
      },
    })

    showSuccess(t('entityDetail.messages.sourceUpdateSuccess'))
    editSourceDialog.value = false

    // Invalidate cache and reload
    if (entity.value) {
      entityCache.delete(`datasources_${entity.value.id}`)
    }
    await loadDataSources()
  } catch (e) {
    console.error('Failed to update source:', e)
    showError(t('entityDetail.messages.sourceUpdateError'))
  } finally {
    savingSource.value = false
  }
}

function confirmDeleteSource(source: any) {
  sourceToDelete.value = source
  deleteSourceConfirm.value = true
}

async function deleteSource() {
  if (!sourceToDelete.value) return

  deletingSource.value = true
  try {
    await adminApi.deleteSource(sourceToDelete.value.id)

    showSuccess(t('entityDetail.messages.sourceDeleteSuccess'))
    deleteSourceConfirm.value = false
    sourceToDelete.value = null

    // Invalidate cache and reload
    if (entity.value) {
      entityCache.delete(`datasources_${entity.value.id}`)
    }
    await loadDataSources()
  } catch (e) {
    console.error('Failed to delete source:', e)
    showError(t('entityDetail.messages.sourceDeleteError'))
  } finally {
    deletingSource.value = false
  }
}

function confirmUnlinkSource(source: any) {
  sourceToUnlink.value = source
  unlinkSourceConfirm.value = true
}

async function unlinkSource() {
  if (!sourceToUnlink.value || !entity.value) return

  unlinkingSource.value = true
  try {
    // Remove this entity from entity_ids array (N:M)
    const currentExtraData = sourceToUnlink.value.extra_data || {}

    // Support both legacy entity_id and new entity_ids
    let entityIds = currentExtraData.entity_ids ||
      (currentExtraData.entity_id ? [currentExtraData.entity_id] : [])

    // Remove current entity from the array
    entityIds = entityIds.filter((id: string) => id !== entity.value!.id)

    // Clean up legacy field and update
    const { entity_id, ...restExtraData } = currentExtraData

    await adminApi.updateSource(sourceToUnlink.value.id, {
      extra_data: {
        ...restExtraData,
        entity_ids: entityIds,
      },
    })

    showSuccess(t('entityDetail.messages.sourceUnlinkSuccess'))
    unlinkSourceConfirm.value = false
    sourceToUnlink.value = null

    // Invalidate cache and reload
    entityCache.delete(`datasources_${entity.value.id}`)
    await loadDataSources()
  } catch (e) {
    console.error('Failed to unlink source:', e)
    showError(t('entityDetail.messages.sourceUnlinkError'))
  } finally {
    unlinkingSource.value = false
  }
}

function goToSourcesWithEntity() {
  if (!entity.value) return
  // Navigate to sources page with entity pre-selected
  router.push({
    name: 'sources',
    query: { linkEntity: entity.value.id },
  })
}

// Children (Untergeordnete Entities) functions
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
    console.error('Failed to load children', e)
    children.value = []
    childrenCount.value = 0
    showError(t('entityDetail.children.loadError'))
  } finally {
    loadingChildren.value = false
  }
}

function toggleFacetExpand(slug: string) {
  const idx = expandedFacets.value.indexOf(slug)
  if (idx >= 0) {
    expandedFacets.value.splice(idx, 1)
  } else {
    expandedFacets.value.push(slug)
  }
}

async function openFacetDetails(facetGroup: any) {
  selectedFacetGroup.value = facetGroup
  facetDetailsDialog.value = true

  try {
    const response = await facetApi.getFacetValues({
      entity_id: entity.value?.id,
      facet_type_slug: facetGroup.facet_type_slug,
      per_page: 10000,
    })
    facetDetails.value = response.data.items || []
  } catch (e) {
    console.error('Failed to load facet details', e)
    facetDetails.value = []
    showError(t('entityDetail.messages.facetDetailsLoadError'))
  }
}

// Handle facet type change in the add dialog
function onFacetTypeChange() {
  // Reset the value when facet type changes
  newFacet.value.value = {}
  newFacet.value.text_representation = ''
}

// Close the add facet dialog and reset form
function closeAddFacetDialog() {
  addFacetDialog.value = false
  resetAddFacetForm()
}

// Open add facet value dialog with pre-selected facet type
function openAddFacetValueDialog(facetGroup: any) {
  resetAddFacetForm()
  // Pre-select the facet type from the group
  newFacet.value.facet_type_id = facetGroup.facet_type_id
  addFacetDialog.value = true
}

// Reset the add facet form
function resetAddFacetForm() {
  newFacet.value = {
    facet_type_id: '',
    text_representation: '',
    source_url: '',
    confidence_score: 0.8,
    value: {},
  }
}

// Build text representation from structured value
function buildTextRepresentation(value: Record<string, any>, _facetType?: any): string {
  if (!value || Object.keys(value).length === 0) return ''

  // If there's a description field, use it as primary text
  if (value.description) return value.description
  if (value.text) return value.text
  if (value.name) return value.name

  // Otherwise concatenate all string values
  const parts: string[] = []
  for (const [, val] of Object.entries(value)) {
    if (typeof val === 'string' && val.trim()) {
      parts.push(val)
    } else if (Array.isArray(val)) {
      parts.push(val.join(', '))
    }
  }
  return parts.join(' - ')
}

async function saveFacetValue() {
  if (!newFacet.value.facet_type_id) return
  if (!entity.value) return

  const facetType = selectedFacetTypeForForm.value
  if (!facetType) return

  // Determine value and text representation based on facet type
  let valueToSave: Record<string, any>
  let textRepresentation: string

  if (facetType.value_schema?.properties) {
    // Structured facet - use the dynamic form value
    valueToSave = { ...newFacet.value.value }
    textRepresentation = buildTextRepresentation(valueToSave, facetType)
  } else {
    // Simple text facet
    if (!newFacet.value.text_representation) return
    valueToSave = { text: newFacet.value.text_representation }
    textRepresentation = newFacet.value.text_representation
  }

  if (!textRepresentation) {
    showError(t('entityDetail.messages.facetValueRequired'))
    return
  }

  savingFacet.value = true
  try {
    await facetApi.createFacetValue({
      entity_id: entity.value.id,
      facet_type_id: newFacet.value.facet_type_id,
      value: valueToSave,
      text_representation: textRepresentation,
      source_url: newFacet.value.source_url || null,
      confidence_score: newFacet.value.confidence_score,
    })

    showSuccess(t('entityDetail.messages.facetAdded'))
    closeAddFacetDialog()

    // Reload facets summary
    facetsSummary.value = await store.fetchEntityFacetsSummary(entity.value.id)

    // Clear expanded facet values to force reload
    expandedFacetValues.value = {}
  } catch (e: any) {
    showError(e.response?.data?.detail || t('entityDetail.messages.facetSaveError'))
  } finally {
    savingFacet.value = false
  }
}

async function verifyFacet(facetValueId: string) {
  try {
    await store.verifyFacetValue(facetValueId, true)
    showSuccess(t('entityDetail.messages.facetVerified'))
    // Reload details
    if (selectedFacetGroup.value) {
      await openFacetDetails(selectedFacetGroup.value)
    }
    // Reload summary
    if (entity.value) {
      facetsSummary.value = await store.fetchEntityFacetsSummary(entity.value.id)
    }
  } catch (e) {
    showError(t('entityDetail.messages.verifyError'))
  }
}

/**
 * Refresh the facets summary - called by child components when facet data changes
 */
async function refreshFacetsSummary() {
  if (entity.value) {
    facetsSummary.value = await store.fetchEntityFacetsSummary(entity.value.id)
  }
}

// Open source details dialog
function openSourceDetails(facet: any) {
  selectedSourceFacet.value = facet
  sourceDetailsDialog.value = true
}

// Open edit dialog for a single facet
function openEditFacetDialog(facet: any, facetGroup: any) {
  editingFacet.value = facet
  editingFacetGroup.value = facetGroup
  editingFacetValue.value = { ...facet.value }
  // Handle both old format (text) and new format (text_representation)
  editingFacetTextValue.value = facet.text_representation || facet.text || ''
  // Get schema from facet type if available
  editingFacetSchema.value = facetGroup.value_schema || null
  editFacetDialog.value = true
}

// Save edited facet
async function saveEditedFacet() {
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
    // Reload facet details
    if (selectedFacetGroup.value) {
      await openFacetDetails(selectedFacetGroup.value)
    }
  } catch (e: any) {
    showError(e.response?.data?.detail || t('entityDetail.messages.facetSaveError'))
  } finally {
    savingFacet.value = false
  }
}

// Confirm delete single facet
function confirmDeleteFacet(facet: any) {
  facetToDelete.value = facet
  singleDeleteConfirm.value = true
}

// Delete single facet
async function deleteSingleFacet() {
  if (!facetToDelete.value) return

  deletingFacet.value = true
  try {
    await facetApi.deleteFacetValue(facetToDelete.value.id)
    showSuccess(t('entityDetail.messages.facetDeleted'))
    singleDeleteConfirm.value = false
    facetToDelete.value = null
    // Reload facet details
    if (selectedFacetGroup.value) {
      await openFacetDetails(selectedFacetGroup.value)
    }
    // Reload summary
    if (entity.value) {
      facetsSummary.value = await store.fetchEntityFacetsSummary(entity.value.id)
    }
  } catch (e: any) {
    showError(e.response?.data?.detail || t('entityDetail.messages.deleteError'))
  } finally {
    deletingFacet.value = false
  }
}

// =============================================================================
// Relation CRUD Functions
// =============================================================================

async function loadRelationTypes() {
  if (relationTypes.value.length > 0) return // Already loaded

  loadingRelationTypes.value = true
  try {
    const response = await relationApi.getRelationTypes()
    relationTypes.value = response.data.items || response.data || []
  } catch (e) {
    console.error('Failed to load relation types', e)
    showError(t('entityDetail.messages.relationTypesLoadError'))
  } finally {
    loadingRelationTypes.value = false
  }
}

async function searchEntities(query: string) {
  if (!query || query.length < 2) {
    targetEntities.value = []
    return
  }

  searchingEntities.value = true
  try {
    const response = await entityApi.searchEntities({ q: query, per_page: 20 })
    // Filter out the current entity from results
    targetEntities.value = (response.data.items || []).filter(
      (e: any) => e.id !== entity.value?.id
    )
  } catch (e) {
    console.error('Failed to search entities', e)
    targetEntities.value = []
    showError(t('entityDetail.messages.entitySearchError'))
  } finally {
    searchingEntities.value = false
  }
}

function openAddRelationDialog() {
  editingRelation.value = null
  newRelation.value = {
    relation_type_id: '',
    target_entity_id: '',
    direction: 'outgoing',
    attributes_json: '',
  }
  targetEntities.value = []
  entitySearchQuery.value = ''
  addRelationDialog.value = true
  loadRelationTypes()
}

function editRelation(rel: Relation) {
  editingRelation.value = rel
  // Determine direction based on whether current entity is source or target
  const isSource = rel.source_entity_id === entity.value?.id
  newRelation.value = {
    relation_type_id: rel.relation_type_id || '',
    target_entity_id: isSource ? rel.target_entity_id : rel.source_entity_id,
    direction: isSource ? 'outgoing' : 'incoming',
    attributes_json: rel.attributes ? JSON.stringify(rel.attributes, null, 2) : '',
  }
  // Pre-populate the target entities list with the current target
  targetEntities.value = [{
    id: isSource ? rel.target_entity_id : rel.source_entity_id,
    name: isSource ? rel.target_entity_name : rel.source_entity_name,
    entity_type_name: isSource ? rel.target_entity_type_slug : rel.source_entity_type_slug,
  }]
  addRelationDialog.value = true
  loadRelationTypes()
}

function closeRelationDialog() {
  addRelationDialog.value = false
  editingRelation.value = null
  newRelation.value = {
    relation_type_id: '',
    target_entity_id: '',
    direction: 'outgoing',
    attributes_json: '',
  }
}

async function saveRelation() {
  if (!entity.value || !newRelation.value.relation_type_id || !newRelation.value.target_entity_id) {
    return
  }

  savingRelation.value = true
  try {
    // Parse attributes JSON if provided
    let attributes = {}
    if (newRelation.value.attributes_json.trim()) {
      try {
        attributes = JSON.parse(newRelation.value.attributes_json)
      } catch (e) {
        showError(t('entityDetail.messages.invalidJson'))
        savingRelation.value = false
        return
      }
    }

    // Determine source and target based on direction
    const sourceId = newRelation.value.direction === 'outgoing'
      ? entity.value.id
      : newRelation.value.target_entity_id
    const targetId = newRelation.value.direction === 'outgoing'
      ? newRelation.value.target_entity_id
      : entity.value.id

    const data = {
      relation_type_id: newRelation.value.relation_type_id,
      source_entity_id: sourceId,
      target_entity_id: targetId,
      attributes: Object.keys(attributes).length > 0 ? attributes : null,
    }

    if (editingRelation.value) {
      await relationApi.updateRelation(editingRelation.value.id, data)
      showSuccess(t('entityDetail.messages.relationUpdated'))
    } else {
      await relationApi.createRelation(data)
      showSuccess(t('entityDetail.messages.relationCreated'))
    }

    closeRelationDialog()
    // Reload relations
    relationsLoaded.value = false
    await loadRelations()
  } catch (e: any) {
    showError(e.response?.data?.detail || t('entityDetail.messages.relationSaveError'))
  } finally {
    savingRelation.value = false
  }
}

function confirmDeleteRelation(rel: Relation) {
  relationToDelete.value = rel
  deleteRelationConfirm.value = true
}

async function deleteRelation() {
  if (!relationToDelete.value) return

  deletingRelation.value = true
  try {
    await relationApi.deleteRelation(relationToDelete.value.id)
    showSuccess(t('entityDetail.messages.relationDeleted'))
    deleteRelationConfirm.value = false
    relationToDelete.value = null
    // Reload relations
    relationsLoaded.value = false
    await loadRelations()
  } catch (e: any) {
    showError(e.response?.data?.detail || t('entityDetail.messages.deleteError'))
  } finally {
    deletingRelation.value = false
  }
}

async function saveEntity() {
  if (!entity.value) return

  savingEntity.value = true
  try {
    await store.updateEntity(entity.value.id, {
      name: editForm.value.name,
      external_id: editForm.value.external_id || null,
    })
    showSuccess(t('entityDetail.messages.entityUpdated'))
    editDialog.value = false
  } catch (e: any) {
    showError(e.response?.data?.detail || t('entityDetail.messages.entitySaveError'))
  } finally {
    savingEntity.value = false
  }
}

async function startCrawl(source: any) {
  startingCrawl.value = source.id
  try {
    await adminApi.startCrawl({ source_ids: [source.id] })
    showSuccess(t('entityDetail.messages.crawlStarted', { name: source.name }))
    source.hasRunningJob = true
  } catch (e: any) {
    showError(e.response?.data?.detail || t('entityDetail.messages.crawlStartError'))
  } finally {
    startingCrawl.value = null
  }
}

function navigateToRelatedEntity(rel: any) {
  const targetId = rel.source_entity_id === entity.value?.id
    ? rel.target_entity_id
    : rel.source_entity_id
  const targetSlug = rel.source_entity_id === entity.value?.id
    ? rel.target_entity_type_slug
    : rel.source_entity_type_slug
  const targetEntitySlug = rel.source_entity_id === entity.value?.id
    ? rel.target_entity_slug || targetId
    : rel.source_entity_slug || targetId

  router.push({
    name: 'entity-detail',
    params: { typeSlug: targetSlug, entitySlug: targetEntitySlug },
  })
}

// Helpers
function formatFacetValue(facet: any): string {
  if (facet.text_representation) return facet.text_representation
  if (typeof facet.value === 'string') return facet.value
  if (facet.value?.text) return facet.value.text
  return JSON.stringify(facet.value)
}

function formatDate(dateStr: string): string {
  return format(new Date(dateStr), 'dd.MM.yyyy HH:mm', { locale: de })
}

function getConfidenceColor(score: number | null): string {
  if (!score) return 'grey'
  if (score >= 0.8) return 'success'
  if (score >= 0.5) return 'warning'
  return 'error'
}

// Source Type Helpers for Facet Values
function normalizeSourceType(sourceType: string | null | undefined): string {
  // Convert to lowercase for consistent lookup (DB stores uppercase, display uses lowercase keys)
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

// Structured Facet Value Helpers
function getStructuredDescription(facet: any): string {
  // Try text_representation first
  if (facet.text_representation) return facet.text_representation
  // Then try value.description or value.text
  const val = facet.value
  if (!val) return ''
  if (typeof val === 'string') return val
  return val.description || val.text || val.concern || val.opportunity || ''
}

function getStructuredType(facet: any): string | null {
  const val = facet.value
  if (!val || typeof val === 'string') return null
  return val.type || null
}

function getStructuredSeverity(facet: any): string | null {
  const val = facet.value
  if (!val || typeof val === 'string') return null
  return val.severity || null
}

function getStructuredQuote(facet: any): string | null {
  const val = facet.value
  if (!val || typeof val === 'string') return null
  return val.quote || null
}

function getSeverityColor(severity: string | null): string {
  if (!severity) return 'grey'
  const s = severity.toLowerCase()
  if (s === 'hoch' || s === 'high') return 'error'
  if (s === 'mittel' || s === 'medium') return 'warning'
  if (s === 'niedrig' || s === 'low') return 'success'
  return 'grey'
}

// Contact Helpers
function getContactName(facet: any): string {
  if (facet.text_representation) return facet.text_representation
  const val = facet.value
  if (!val) return ''
  if (typeof val === 'string') return val
  return val.name || ''
}

function getContactRole(facet: any): string | null {
  const val = facet.value
  if (!val || typeof val === 'string') return null
  return val.role || val.position || null
}

function getContactEmail(facet: any): string | null {
  const val = facet.value
  if (!val || typeof val === 'string') return null
  return val.email || null
}

function getContactPhone(facet: any): string | null {
  const val = facet.value
  if (!val || typeof val === 'string') return null
  return val.phone || val.telefon || null
}

function getContactSentiment(facet: any): string | null {
  const val = facet.value
  if (!val || typeof val === 'string') return null
  return val.sentiment || null
}

function getContactStatement(facet: any): string | null {
  const val = facet.value
  if (!val || typeof val === 'string') return null
  return val.statement || val.quote || null
}

function getSentimentColor(sentiment: string | null): string {
  if (!sentiment) return 'grey'
  const s = sentiment.toLowerCase()
  if (s === 'positiv' || s === 'positive') return 'success'
  if (s === 'negativ' || s === 'negative') return 'error'
  return 'grey'
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text)
  showSuccess(t('entityDetail.messages.copiedToClipboard'))
}

// =============================================================================
// PYSIS-FACETS ENRICHMENT
// =============================================================================

async function checkPysisProcesses() {
  if (!entity.value || !entityType.value?.supports_pysis) {
    hasPysisProcesses.value = false
    return
  }

  try {
    const response = await pysisApi.getProcesses(entity.value.name)
    hasPysisProcesses.value = (response.data.items?.length || 0) > 0
  } catch (e) {
    console.error('Failed to check PySis processes', e)
    hasPysisProcesses.value = false
  }
}

async function enrichFromPysis() {
  if (!entity.value) return

  enrichingFromPysis.value = true
  try {
    const response = await pysisApi.enrichFacetsFromPysis({
      entity_id: entity.value.id,
      overwrite: enrichPysisOverwrite.value,
    })

    if (response.data.success) {
      enrichTaskId.value = response.data.task_id
      showEnrichFromPysisDialog.value = false
      showEnrichTaskStartedDialog.value = true
      // Start polling for task status
      startEnrichTaskPolling(response.data.task_id)
    } else {
      showError(response.data.message || t('entityDetail.messages.enrichError'))
    }
  } catch (e: any) {
    showError(e.response?.data?.error || t('entityDetail.messages.enrichError'))
  } finally {
    enrichingFromPysis.value = false
  }
}

// Task polling functions
function startEnrichTaskPolling(taskId: string) {
  // Clear existing polling
  stopEnrichTaskPolling()

  enrichTaskPolling.value = setInterval(async () => {
    try {
      const response = await aiTasksApi.getStatus(taskId)
      enrichTaskStatus.value = response.data

      // Check if task is completed or failed
      if (['COMPLETED', 'FAILED', 'CANCELLED'].includes(response.data.status)) {
        stopEnrichTaskPolling()

        if (response.data.status === 'COMPLETED') {
          showSuccess(t('entityDetail.messages.enrichSuccess', {
            count: response.data.fields_extracted || 0
          }))
          // Refresh facets data
          await loadEntityData()
        } else if (response.data.status === 'FAILED') {
          showError(response.data.error_message || t('entityDetail.messages.enrichError'))
        }

        // Close dialog after a short delay
        setTimeout(() => {
          showEnrichTaskStartedDialog.value = false
          enrichTaskStatus.value = null
        }, 2000)
      }
    } catch (e) {
      console.error('Failed to poll task status', e)
    }
  }, 2000) // Poll every 2 seconds
}

function stopEnrichTaskPolling() {
  if (enrichTaskPolling.value) {
    clearInterval(enrichTaskPolling.value)
    enrichTaskPolling.value = null
  }
}

// ========================================
// New Enrichment System Functions
// ========================================

async function onEnrichmentMenuOpen(isOpen: boolean) {
  if (isOpen && !enrichmentSources.value) {
    await loadEnrichmentSources()
  }
}

async function loadEnrichmentSources() {
  if (!entity.value) return

  loadingEnrichmentSources.value = true
  try {
    const response = await entityDataApi.getEnrichmentSources(entity.value.id)
    enrichmentSources.value = response.data

    // Pre-select available sources
    selectedEnrichmentSources.value = []
    if (response.data.pysis?.available) selectedEnrichmentSources.value.push('pysis')
    if (response.data.relations?.available) selectedEnrichmentSources.value.push('relations')
    if (response.data.documents?.available) selectedEnrichmentSources.value.push('documents')
    if (response.data.extractions?.available) selectedEnrichmentSources.value.push('extractions')
  } catch (e) {
    console.error('Failed to load enrichment sources', e)
    showError(t('entityDetail.enrichment.noSourcesAvailable'))
  } finally {
    loadingEnrichmentSources.value = false
  }
}

function formatEnrichmentDate(dateStr: string | null): string {
  if (!dateStr) return '-'
  try {
    return formatDistanceToNow(new Date(dateStr), { addSuffix: true, locale: de })
  } catch {
    return dateStr
  }
}

async function startEnrichmentAnalysis() {
  if (!entity.value || selectedEnrichmentSources.value.length === 0) return

  startingEnrichment.value = true
  try {
    const response = await entityDataApi.analyzeForFacets({
      entity_id: entity.value.id,
      source_types: selectedEnrichmentSources.value,
    })

    enrichmentTaskId.value = response.data.task_id
    enrichmentTaskStatus.value = { status: 'PENDING' }
    enrichmentPreviewData.value = null

    // Close dropdown, open review modal
    enrichmentMenuOpen.value = false
    showEnrichmentReviewDialog.value = true
    showMinimizedTaskSnackbar.value = false

    // Start polling for task status
    startEnrichmentTaskPolling(response.data.task_id)
  } catch (e: any) {
    showError(e.response?.data?.detail || t('entityDetail.messages.enrichError'))
  } finally {
    startingEnrichment.value = false
  }
}

function startEnrichmentTaskPolling(taskId: string) {
  stopEnrichmentTaskPolling()

  enrichmentTaskPolling.value = setInterval(async () => {
    try {
      const response = await aiTasksApi.getStatus(taskId)
      enrichmentTaskStatus.value = response.data

      // Check if task is completed
      if (response.data.status === 'COMPLETED') {
        stopEnrichmentTaskPolling()

        // Fetch the preview data
        try {
          const previewResponse = await entityDataApi.getAnalysisPreview(taskId)
          enrichmentPreviewData.value = previewResponse.data
        } catch (e) {
          console.error('Failed to fetch preview', e)
        }
      } else if (response.data.status === 'FAILED' || response.data.status === 'CANCELLED') {
        stopEnrichmentTaskPolling()
      }
    } catch (e) {
      console.error('Failed to poll task status', e)
    }
  }, 2000)
}

function stopEnrichmentTaskPolling() {
  if (enrichmentTaskPolling.value) {
    clearInterval(enrichmentTaskPolling.value)
    enrichmentTaskPolling.value = null
  }
}

function onEnrichmentReviewClose() {
  stopEnrichmentTaskPolling()
  showMinimizedTaskSnackbar.value = false
  enrichmentTaskId.value = null
  enrichmentTaskStatus.value = null
  enrichmentPreviewData.value = null
}

function onEnrichmentReviewMinimize() {
  showEnrichmentReviewDialog.value = false
  // Show minimized snackbar only if task is still running
  if (enrichmentTaskStatus.value?.status === 'RUNNING' || enrichmentTaskStatus.value?.status === 'PENDING') {
    showMinimizedTaskSnackbar.value = true
  }
}

function reopenEnrichmentReview() {
  showMinimizedTaskSnackbar.value = false
  showEnrichmentReviewDialog.value = true
}

async function onEnrichmentApplied(result: { created: number; updated: number }) {
  showSuccess(t('facetEnrichment.applied', result))
  // Refresh entity data
  await loadEntityData()
}

// Cleanup on unmount
onUnmounted(() => {
  stopEnrichTaskPolling()
  stopEnrichmentTaskPolling()
  // Clear any pending search timeout
  if (sourceSearchTimeout) {
    clearTimeout(sourceSearchTimeout)
    sourceSearchTimeout = null
  }
})

// Watch for tab changes to load data lazily
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

// Watch for route changes
watch([typeSlug, entitySlug], () => {
  // Reset state for new entity
  bulkMode.value = false
  selectedFacetIds.value = []
  facetSearchQuery.value = ''
  // Reset children/relations for new entity
  childrenLoaded.value = false
  children.value = []
  childrenCount.value = 0
  childrenPage.value = 1
  relationsLoaded.value = false
  relations.value = []
  loadEntityData()
})

// Init
onMounted(() => {
  loadEntityData()
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

/* Hierarchy Tree Visualization */
.hierarchy-tree {
  text-align: center;
}

.tree-level {
  position: relative;
}

.tree-connector {
  width: 2px;
  background: rgb(var(--v-theme-primary));
  margin: 0 auto;
}

.tree-connector-vertical {
  height: 24px;
}

.tree-connector-down-from-current {
  height: 32px;
}

.tree-node {
  transition: all 0.2s ease;
}

.tree-node:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.tree-node-current {
  border-radius: 12px;
}

.tree-children-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
  max-width: 1200px;
  margin: 0 auto;
}

.tree-node-child {
  border-radius: 8px;
}

.relations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 12px;
}

.relation-card {
  border-radius: 8px;
  transition: all 0.2s ease;
}

.relation-card:hover {
  border-color: rgb(var(--v-theme-primary));
  background: rgba(var(--v-theme-primary), 0.04);
}

/* Dark mode adjustments for tree view */
.v-theme--dark .tree-node-child,
.v-theme--dark .tree-node-parent {
  border-color: rgba(255, 255, 255, 0.12);
}

.v-theme--dark .tree-node-child:hover,
.v-theme--dark .tree-node-parent:hover {
  border-color: rgb(var(--v-theme-primary));
  background: rgba(var(--v-theme-primary), 0.08);
}

.v-theme--dark .relation-card {
  border-color: rgba(255, 255, 255, 0.12);
}

.v-theme--dark .relation-card:hover {
  background: rgba(var(--v-theme-primary), 0.08);
}
</style>
