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
    <v-card v-if="entity" class="mb-6">
      <v-card-text>
        <div class="d-flex align-center">
          <v-icon :icon="entityType?.icon || 'mdi-folder'" :color="entityType?.color" size="48" class="mr-4"></v-icon>
          <div class="flex-grow-1">
            <div class="d-flex align-center mb-1">
              <h1 class="text-h4 mr-3">{{ entity.name }}</h1>
              <v-chip v-if="entity.external_id" size="small" variant="tonal" color="info">
                <span class="text-caption font-weight-medium">ID:</span>
                <span class="ml-1">{{ entity.external_id }}</span>
              </v-chip>
            </div>
            <div v-if="entity.hierarchy_path" class="text-body-2 text-medium-emphasis">
              {{ entity.hierarchy_path }}
            </div>
          </div>
          <div class="d-flex ga-2">
            <FavoriteButton
              v-if="entity"
              :entity-id="entity.id"
              size="default"
              variant="tonal"
              show-tooltip
            />
            <v-btn variant="tonal" @click="notesDialog = true" :title="t('entityDetail.notes')">
              <v-icon>mdi-note-text</v-icon>
              <v-badge v-if="notes.length" :content="notes.length" color="primary" floating></v-badge>
            </v-btn>
            <v-btn variant="tonal" @click="exportDialog = true" :title="t('entityDetail.export')">
              <v-icon>mdi-export</v-icon>
            </v-btn>
            <v-btn variant="outlined" @click="editDialog = true">
              <v-icon start>mdi-pencil</v-icon>
              {{ t('entityDetail.edit') }}
            </v-btn>
            <v-menu>
              <template v-slot:activator="{ props }">
                <v-btn variant="tonal" color="primary" v-bind="props">
                  <v-icon start>mdi-plus</v-icon>
                  {{ t('entityDetail.addFacet') }}
                  <v-icon end>mdi-chevron-down</v-icon>
                </v-btn>
              </template>
              <v-list>
                <v-list-item
                  v-for="facetGroup in facetsSummary?.facets_by_type || []"
                  :key="facetGroup.facet_type_id"
                  @click="openAddFacetValueDialog(facetGroup)"
                >
                  <template v-slot:prepend>
                    <v-icon :icon="facetGroup.facet_type_icon" :color="facetGroup.facet_type_color" size="small"></v-icon>
                  </template>
                  <v-list-item-title>{{ facetGroup.facet_type_name }}</v-list-item-title>
                  <template v-slot:append>
                    <v-chip size="x-small" variant="text">{{ facetGroup.value_count }}</v-chip>
                  </template>
                </v-list-item>
                <v-divider v-if="facetsSummary?.facets_by_type?.length" class="my-1"></v-divider>
                <v-list-item @click="addFacetDialog = true">
                  <template v-slot:prepend>
                    <v-icon icon="mdi-tag-plus" color="grey" size="small"></v-icon>
                  </template>
                  <v-list-item-title class="text-medium-emphasis">{{ t('entities.facet.title') }}</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>
          </div>
        </div>

        <!-- Stats Row -->
        <v-row class="mt-4">
          <v-col cols="6" sm="3" md="2">
            <div class="text-center">
              <div class="text-h5">{{ entity.facet_count || 0 }}</div>
              <div class="text-caption text-medium-emphasis">{{ t('entityDetail.stats.facetValues') }}</div>
            </div>
          </v-col>
          <v-col cols="6" sm="3" md="2">
            <div class="text-center">
              <div class="text-h5">{{ entity.relation_count || 0 }}</div>
              <div class="text-caption text-medium-emphasis">{{ t('entityDetail.stats.relations') }}</div>
            </div>
          </v-col>
          <v-col cols="6" sm="3" md="2">
            <div class="text-center">
              <div class="text-h5">{{ facetsSummary?.verified_count || 0 }}</div>
              <div class="text-caption text-medium-emphasis">{{ t('entityDetail.stats.verified') }}</div>
            </div>
          </v-col>
          <v-col cols="6" sm="3" md="2">
            <div class="text-center">
              <div class="text-h5">{{ dataSources.length }}</div>
              <div class="text-caption text-medium-emphasis">{{ t('entityDetail.stats.dataSources') }}</div>
            </div>
          </v-col>
          <v-col v-if="entity.latitude && entity.longitude" cols="12" sm="6" md="4">
            <div class="text-center">
              <v-chip size="small" color="info">
                <v-icon start size="small">mdi-map-marker</v-icon>
                {{ entity.latitude.toFixed(4) }}, {{ entity.longitude.toFixed(4) }}
              </v-chip>
            </div>
          </v-col>
        </v-row>

        <!-- Core Attributes -->
        <div v-if="hasAttributes" class="d-flex flex-wrap ga-1 mt-2">
          <v-chip v-for="(value, key) in entity.core_attributes" :key="key" size="small" variant="tonal">
            <strong class="mr-1">{{ formatAttributeKey(key) }}:</strong>
            {{ formatAttributeValue(value) }}
          </v-chip>
        </div>
      </v-card-text>
    </v-card>

    <!-- Tabs for Content -->
    <v-tabs v-model="activeTab" color="primary" class="mb-4">
      <v-tab value="facets">
        <v-icon start>mdi-tag-multiple</v-icon>
        {{ t('entityDetail.tabs.properties') }}
        <v-chip v-if="facetsSummary" size="x-small" class="ml-2">{{ facetsSummary.total_facet_values }}</v-chip>
      </v-tab>
      <v-tab value="relations">
        <v-icon start>mdi-link</v-icon>
        {{ t('entityDetail.tabs.relations') }}
        <v-chip v-if="relations.length" size="x-small" class="ml-2">{{ relations.length }}</v-chip>
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
      <v-tab v-if="entityType?.slug === 'municipality'" value="pysis">
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
      <v-tab v-if="flags.entityHierarchyEnabled && entityType?.supports_hierarchy" value="children">
        <v-icon start>mdi-file-tree</v-icon>
        {{ t('entityDetail.tabs.children', 'Untergeordnete') }}
        <v-chip v-if="childrenCount" size="x-small" class="ml-2">{{ childrenCount }}</v-chip>
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
                v-if="entityType?.slug === 'municipality'"
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
                  <!-- Facet Values List -->
                  <div v-if="getDisplayedFacets(facetGroup).length" class="mb-4">
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
                          :color="getSourceTypeColor(sample.source_type)"
                          class="cursor-pointer"
                          @click.stop="openSourceDetails(sample)"
                        >
                          <v-icon start size="x-small">{{ getSourceTypeIcon(sample.source_type) }}</v-icon>
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
      <v-window-item value="relations">
        <v-card>
          <v-card-text>
            <!-- Loading State -->
            <div v-if="loadingRelations" class="text-center pa-8">
              <v-progress-circular indeterminate color="primary" size="48"></v-progress-circular>
              <p class="mt-4 text-medium-emphasis">{{ t('entityDetail.loadingRelations') }}</p>
            </div>
            <div v-else-if="relations.length">
              <!-- Add button at top when relations exist -->
              <div class="d-flex justify-end mb-2">
                <v-btn variant="tonal" color="primary" size="small" @click="openAddRelationDialog">
                  <v-icon start>mdi-link-plus</v-icon>
                  {{ t('entityDetail.addRelation') }}
                </v-btn>
              </div>
              <v-list>
                <v-list-item
                  v-for="rel in relations"
                  :key="rel.id"
                  class="cursor-pointer"
                >
                  <template v-slot:prepend>
                    <v-icon :color="rel.relation_type_color || 'primary'">mdi-link-variant</v-icon>
                  </template>
                  <v-list-item-title @click="navigateToRelatedEntity(rel)" class="cursor-pointer">
                    <span v-if="rel.source_entity_id === entity?.id">
                      {{ rel.relation_type_name }}: <strong>{{ rel.target_entity_name }}</strong>
                    </span>
                    <span v-else>
                      {{ rel.relation_type_name_inverse || rel.relation_type_name }}: <strong>{{ rel.source_entity_name }}</strong>
                    </span>
                  </v-list-item-title>
                  <v-list-item-subtitle v-if="rel.attributes && Object.keys(rel.attributes).length">
                    <v-chip v-for="(val, key) in rel.attributes" :key="key" size="x-small" class="mr-1">
                      {{ key }}: {{ val }}
                    </v-chip>
                  </v-list-item-subtitle>
                  <template v-slot:append>
                    <div class="d-flex align-center ga-2">
                      <v-chip v-if="rel.human_verified" size="x-small" color="success">
                        <v-icon size="x-small">mdi-check</v-icon>
                      </v-chip>
                      <v-btn icon size="small" variant="text" @click.stop="editRelation(rel)">
                        <v-icon size="small">mdi-pencil</v-icon>
                        <v-tooltip activator="parent" location="top">{{ t('common.edit') }}</v-tooltip>
                      </v-btn>
                      <v-btn icon size="small" variant="text" color="error" @click.stop="confirmDeleteRelation(rel)">
                        <v-icon size="small">mdi-delete</v-icon>
                        <v-tooltip activator="parent" location="top">{{ t('common.delete') }}</v-tooltip>
                      </v-btn>
                      <v-icon @click="navigateToRelatedEntity(rel)">mdi-chevron-right</v-icon>
                    </div>
                  </template>
                </v-list-item>
              </v-list>
            </div>
            <!-- Empty State for Relations -->
            <div v-else class="text-center pa-8">
              <v-icon size="80" color="grey-lighten-1" class="mb-4">mdi-link-off</v-icon>
              <h3 class="text-h6 mb-2">{{ t('entityDetail.emptyState.noRelations') }}</h3>
              <p class="text-body-2 text-medium-emphasis mb-4">
                {{ t('entityDetail.emptyState.noRelationsDesc') }}
              </p>
              <v-btn variant="tonal" color="primary" @click="openAddRelationDialog">
                <v-icon start>mdi-link-plus</v-icon>
                {{ t('entityDetail.addRelation') }}
              </v-btn>
            </div>
          </v-card-text>
        </v-card>
      </v-window-item>

      <!-- Data Sources Tab -->
      <v-window-item value="sources">
        <v-card>
          <v-card-text>
            <div v-if="loadingDataSources" class="text-center pa-4">
              <v-progress-circular indeterminate></v-progress-circular>
            </div>
            <div v-else-if="dataSources.length">
              <v-list>
                <v-list-item
                  v-for="source in dataSources"
                  :key="source.id"
                >
                  <template v-slot:prepend>
                    <v-icon :color="getSourceStatusColor(source.status)">
                      {{ getSourceStatusIcon(source.status) }}
                    </v-icon>
                  </template>
                  <v-list-item-title>
                    {{ source.name }}
                    <v-chip v-if="source.hasRunningJob" size="x-small" color="info" class="ml-2">
                      {{ t('entityDetail.running') }}
                    </v-chip>
                  </v-list-item-title>
                  <v-list-item-subtitle>
                    <a :href="source.base_url" target="_blank" class="text-decoration-none">
                      {{ source.base_url }}
                    </a>
                  </v-list-item-subtitle>
                  <template v-slot:append>
                    <v-btn
                      v-if="!source.hasRunningJob"
                      size="small"
                      color="primary"
                      variant="tonal"
                      @click="startCrawl(source)"
                      :loading="startingCrawl === source.id"
                    >
                      <v-icon start>mdi-play</v-icon>
                      {{ t('entityDetail.crawl') }}
                    </v-btn>
                  </template>
                </v-list-item>
              </v-list>
            </div>
            <!-- Empty State for Data Sources -->
            <div v-else class="text-center pa-8">
              <v-icon size="80" color="grey-lighten-1" class="mb-4">mdi-web-off</v-icon>
              <h3 class="text-h6 mb-2">{{ t('entityDetail.emptyState.noDataSources') }}</h3>
              <p class="text-body-2 text-medium-emphasis mb-4">
                {{ t('entityDetail.emptyState.noDataSourcesDesc') }}
              </p>
              <v-btn variant="tonal" color="primary" @click="goToSources">
                <v-icon start>mdi-plus</v-icon>
                {{ t('entityDetail.addDataSource') }}
              </v-btn>
            </div>
          </v-card-text>
        </v-card>
      </v-window-item>

      <!-- Documents Tab -->
      <v-window-item value="documents">
        <v-card>
          <v-card-text>
            <div v-if="loadingDocuments" class="text-center pa-4">
              <v-progress-circular indeterminate></v-progress-circular>
            </div>
            <v-data-table
              v-else
              :headers="documentHeaders"
              :items="documents"
              :items-per-page="10"
            >
              <template v-slot:item.title="{ item }">
                <a :href="item.url" target="_blank" class="text-decoration-none">
                  {{ item.title || t('entityDetail.document') }}
                </a>
              </template>
              <template v-slot:item.created_at="{ item }">
                {{ formatDate(item.created_at) }}
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-window-item>

      <!-- PySis Tab (only for municipalities) -->
      <v-window-item v-if="entityType?.slug === 'municipality'" value="pysis" eager>
        <PySisTab
          v-if="entity"
          :municipality="entity.name"
        />
      </v-window-item>

      <!-- External API Data Tab -->
      <v-window-item v-if="externalData?.has_external_data" value="api-data">
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon start color="primary">mdi-api</v-icon>
            {{ t('entityDetail.apiData.title', 'Externe API-Daten') }}
          </v-card-title>
          <v-card-text>
            <!-- Source Info -->
            <v-alert type="info" variant="tonal" class="mb-4">
              <div class="d-flex align-center">
                <v-icon start>mdi-cloud-sync</v-icon>
                <div>
                  <strong>{{ externalData.external_source?.name }}</strong>
                  <div class="text-caption">
                    {{ t('entityDetail.apiData.externalId', 'Externe ID') }}: {{ externalData.sync_record?.external_id }}
                    <span v-if="externalData.sync_record?.last_seen_at" class="ml-2">
                      | {{ t('entityDetail.apiData.lastSync', 'Letzter Sync') }}: {{ formatDate(externalData.sync_record.last_seen_at) }}
                    </span>
                  </div>
                </div>
              </div>
            </v-alert>

            <!-- Raw JSON Data -->
            <v-expansion-panels>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon start>mdi-code-json</v-icon>
                  {{ t('entityDetail.apiData.rawResponse', 'Rohe API-Antwort') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <pre class="json-viewer pa-3 rounded">{{ JSON.stringify(externalData.raw_data, null, 2) }}</pre>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>

            <!-- Field Overview -->
            <v-card variant="outlined" class="mt-4">
              <v-card-title class="text-subtitle-1">
                <v-icon start size="small">mdi-format-list-bulleted</v-icon>
                {{ t('entityDetail.apiData.fields', 'Verfügbare Felder') }}
              </v-card-title>
              <v-card-text>
                <v-table density="compact">
                  <thead>
                    <tr>
                      <th>{{ t('entityDetail.apiData.fieldName', 'Feldname') }}</th>
                      <th>{{ t('entityDetail.apiData.fieldType', 'Typ') }}</th>
                      <th>{{ t('entityDetail.apiData.fieldValue', 'Wert') }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(value, key) in externalData.raw_data" :key="key">
                      <td class="font-weight-medium">{{ key }}</td>
                      <td>
                        <v-chip size="x-small" :color="getFieldTypeColor(value)">
                          {{ getFieldType(value) }}
                        </v-chip>
                      </td>
                      <td class="text-truncate" style="max-width: 400px;">
                        <template v-if="typeof value === 'object'">
                          <v-chip size="x-small" variant="outlined">
                            {{ Array.isArray(value) ? `Array[${value.length}]` : 'Object' }}
                          </v-chip>
                        </template>
                        <template v-else>{{ formatFieldValue(value) }}</template>
                      </td>
                    </tr>
                  </tbody>
                </v-table>
              </v-card-text>
            </v-card>
          </v-card-text>
        </v-card>
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
      <v-window-item v-if="flags.entityHierarchyEnabled && entityType?.supports_hierarchy" value="children">
        <v-card>
          <v-card-text>
            <!-- Loading State -->
            <div v-if="loadingChildren" class="d-flex justify-center py-8">
              <v-progress-circular indeterminate></v-progress-circular>
            </div>

            <!-- Empty State -->
            <v-alert v-else-if="children.length === 0" type="info" variant="tonal" class="mb-0">
              <v-alert-title>{{ t('entityDetail.children.empty', 'Keine untergeordneten Entities') }}</v-alert-title>
              {{ t('entityDetail.children.emptyHint', 'Diese Entity hat keine untergeordneten Einträge.') }}
            </v-alert>

            <!-- Children List -->
            <template v-else>
              <v-text-field
                v-if="children.length > 5"
                v-model="childrenSearchQuery"
                prepend-inner-icon="mdi-magnify"
                :label="t('common.search')"
                clearable
                hide-details
                density="compact"
                variant="outlined"
                class="mb-4"
              ></v-text-field>

              <v-list lines="two">
                <v-list-item
                  v-for="child in filteredChildren"
                  :key="child.id"
                  :to="`/entities/${typeSlug}/${child.slug}`"
                  class="mb-1"
                  rounded
                >
                  <template v-slot:prepend>
                    <v-avatar :color="entityType?.color || 'primary'" size="40">
                      <v-icon :icon="entityType?.icon || 'mdi-folder'" color="white" size="small"></v-icon>
                    </v-avatar>
                  </template>
                  <v-list-item-title class="font-weight-medium">{{ child.name }}</v-list-item-title>
                  <v-list-item-subtitle>
                    <span v-if="child.external_id" class="mr-3">
                      <v-icon size="x-small" class="mr-1">mdi-identifier</v-icon>
                      {{ child.external_id }}
                    </span>
                    <span v-if="child.facet_count" class="mr-3">
                      <v-icon size="x-small" class="mr-1">mdi-tag</v-icon>
                      {{ child.facet_count }} {{ t('entityDetail.stats.facetValues') }}
                    </span>
                    <span v-if="child.children_count">
                      <v-icon size="x-small" class="mr-1">mdi-file-tree</v-icon>
                      {{ child.children_count }} {{ t('entityDetail.children.subEntities', 'Untergeordnete') }}
                    </span>
                  </v-list-item-subtitle>
                  <template v-slot:append>
                    <v-icon>mdi-chevron-right</v-icon>
                  </template>
                </v-list-item>
              </v-list>

              <!-- Pagination -->
              <div v-if="childrenTotalPages > 1" class="d-flex justify-center mt-4">
                <v-pagination
                  v-model="childrenPage"
                  :length="childrenTotalPages"
                  :total-visible="5"
                  @update:model-value="loadChildren"
                ></v-pagination>
              </div>
            </template>
          </v-card-text>
        </v-card>
      </v-window-item>
    </v-window>

    <!-- Add Facet Dialog -->
    <v-dialog v-model="addFacetDialog" max-width="700" scrollable>
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon start>mdi-plus-circle</v-icon>
          {{ t('entityDetail.dialog.addFacet') }}
        </v-card-title>
        <v-card-text>
          <v-form ref="addFacetForm" @submit.prevent="saveFacetValue">
            <!-- Facet Type Selection -->
            <v-select
              v-model="newFacet.facet_type_id"
              :items="applicableFacetTypes"
              item-title="name"
              item-value="id"
              :label="t('entityDetail.dialog.facetType')"
              :rules="[v => !!v || t('entityDetail.dialog.facetTypeRequired')]"
              variant="outlined"
              density="comfortable"
              class="mb-4"
              @update:model-value="onFacetTypeChange"
            >
              <template v-slot:item="{ item, props }">
                <v-list-item v-bind="props">
                  <template v-slot:prepend>
                    <v-icon :icon="item.raw.icon" :color="item.raw.color" size="small"></v-icon>
                  </template>
                </v-list-item>
              </template>
              <template v-slot:selection="{ item }">
                <v-icon :icon="item.raw.icon" :color="item.raw.color" size="small" class="mr-2"></v-icon>
                {{ item.raw.name }}
              </template>
            </v-select>

            <!-- Dynamic Schema Form (when facet type has a schema) -->
            <template v-if="selectedFacetTypeForForm?.value_schema">
              <v-divider class="mb-4"></v-divider>
              <div class="text-subtitle-2 mb-3 text-medium-emphasis-darken-1">
                {{ t('entityDetail.dialog.facetDetails') }}
              </div>
              <DynamicSchemaForm
                v-model="newFacet.value"
                :schema="selectedFacetTypeForForm.value_schema"
              />
            </template>

            <!-- Simple text input (when no schema) -->
            <template v-else-if="newFacet.facet_type_id">
              <v-textarea
                v-model="newFacet.text_representation"
                :label="t('entityDetail.dialog.facetValue')"
                :rules="[v => !!v || t('entityDetail.dialog.facetValueRequired')]"
                rows="3"
                variant="outlined"
                density="comfortable"
                class="mb-3"
              ></v-textarea>
            </template>

            <v-divider class="my-4"></v-divider>

            <!-- Source URL -->
            <v-text-field
              v-model="newFacet.source_url"
              :label="t('entityDetail.dialog.sourceUrl')"
              placeholder="https://..."
              variant="outlined"
              density="comfortable"
              class="mb-3"
              prepend-inner-icon="mdi-link"
            ></v-text-field>

            <!-- Confidence Score -->
            <div class="d-flex align-center ga-4">
              <span class="text-body-2">{{ t('entityDetail.dialog.confidence') }}:</span>
              <v-slider
                v-model="newFacet.confidence_score"
                :min="0"
                :max="1"
                :step="0.1"
                thumb-label
                :color="getConfidenceColor(newFacet.confidence_score)"
                hide-details
                class="flex-grow-1"
              ></v-slider>
              <v-chip size="small" :color="getConfidenceColor(newFacet.confidence_score)">
                {{ Math.round(newFacet.confidence_score * 100) }}%
              </v-chip>
            </div>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="closeAddFacetDialog">{{ t('common.cancel') }}</v-btn>
          <v-btn
            color="primary"
            :loading="savingFacet"
            :disabled="!canSaveFacet"
            @click="saveFacetValue"
          >
            <v-icon start>mdi-check</v-icon>
            {{ t('common.save') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Facet Details Dialog -->
    <v-dialog v-model="facetDetailsDialog" max-width="800" scrollable>
      <v-card v-if="selectedFacetGroup">
        <v-card-title class="d-flex align-center">
          <v-icon :icon="selectedFacetGroup.facet_type_icon" :color="selectedFacetGroup.facet_type_color" class="mr-2"></v-icon>
          {{ selectedFacetGroup.facet_type_name }}
          <v-spacer></v-spacer>
          <v-btn icon="mdi-close" variant="tonal" @click="facetDetailsDialog = false" :aria-label="t('common.close')"></v-btn>
        </v-card-title>
        <v-card-text>
          <div class="d-flex flex-column ga-3">
            <v-card
              v-for="fv in facetDetails"
              :key="fv.id"
              variant="outlined"
              class="pa-3"
            >
              <!-- Pain Point Display -->
              <template v-if="selectedFacetGroup.facet_type_slug === 'pain_point'">
                <div class="d-flex align-start ga-2">
                  <v-icon color="error">mdi-alert-circle</v-icon>
                  <div class="flex-grow-1">
                    <div class="text-body-1">{{ getStructuredDescription(fv) }}</div>
                    <div class="d-flex flex-wrap ga-2 mt-2">
                      <v-chip v-if="getStructuredType(fv)" size="small" variant="outlined" color="error">
                        {{ getStructuredType(fv) }}
                      </v-chip>
                      <v-chip
                        v-if="getStructuredSeverity(fv)"
                        size="small"
                        :color="getSeverityColor(getStructuredSeverity(fv))"
                      >
                        <v-icon start size="x-small">{{ getSeverityIcon(getStructuredSeverity(fv)) }}</v-icon>
                        {{ getStructuredSeverity(fv) }}
                      </v-chip>
                    </div>
                    <div v-if="getStructuredQuote(fv)" class="mt-2 pa-2 rounded bg-surface-variant">
                      <v-icon size="small" class="mr-1">mdi-format-quote-open</v-icon>
                      <span class="text-body-2 font-italic">{{ getStructuredQuote(fv) }}</span>
                    </div>
                  </div>
                </div>
              </template>

              <!-- Positive Signal Display -->
              <template v-else-if="selectedFacetGroup.facet_type_slug === 'positive_signal'">
                <div class="d-flex align-start ga-2">
                  <v-icon color="success">mdi-lightbulb-on</v-icon>
                  <div class="flex-grow-1">
                    <div class="text-body-1">{{ getStructuredDescription(fv) }}</div>
                    <div class="d-flex flex-wrap ga-2 mt-2">
                      <v-chip v-if="getStructuredType(fv)" size="small" variant="outlined" color="success">
                        {{ getStructuredType(fv) }}
                      </v-chip>
                    </div>
                    <div v-if="getStructuredQuote(fv)" class="mt-2 pa-2 rounded bg-surface-variant">
                      <v-icon size="small" class="mr-1">mdi-format-quote-open</v-icon>
                      <span class="text-body-2 font-italic">{{ getStructuredQuote(fv) }}</span>
                    </div>
                  </div>
                </div>
              </template>

              <!-- Contact Display -->
              <template v-else-if="selectedFacetGroup.facet_type_slug === 'contact'">
                <div class="d-flex align-start ga-2">
                  <v-avatar color="primary" size="40">
                    <v-icon color="on-primary">mdi-account</v-icon>
                  </v-avatar>
                  <div class="flex-grow-1">
                    <div class="text-body-1 font-weight-medium">{{ getContactName(fv) }}</div>
                    <div v-if="getContactRole(fv)" class="text-body-2 text-medium-emphasis">{{ getContactRole(fv) }}</div>
                    <div class="d-flex flex-wrap ga-2 mt-2">
                      <v-chip v-if="getContactEmail(fv)" size="small" variant="outlined" @click.stop="copyToClipboard(getContactEmail(fv)!)">
                        <v-icon start size="small">mdi-email</v-icon>
                        {{ getContactEmail(fv) }}
                      </v-chip>
                      <v-chip v-if="getContactPhone(fv)" size="small" variant="outlined">
                        <v-icon start size="small">mdi-phone</v-icon>
                        {{ getContactPhone(fv) }}
                      </v-chip>
                      <v-chip
                        v-if="getContactSentiment(fv)"
                        size="small"
                        :color="getSentimentColor(getContactSentiment(fv))"
                      >
                        {{ getContactSentiment(fv) }}
                      </v-chip>
                    </div>
                    <div v-if="getContactStatement(fv)" class="mt-2 pa-2 rounded bg-surface-variant">
                      <v-icon size="small" class="mr-1">mdi-format-quote-open</v-icon>
                      <span class="text-body-2 font-italic">{{ getContactStatement(fv) }}</span>
                    </div>
                  </div>
                </div>
              </template>

              <!-- Default Display -->
              <template v-else>
                <div class="text-body-1">{{ fv.text_representation || formatFacetValue(fv) }}</div>
              </template>

              <!-- Meta Info (shown for all) -->
              <v-divider class="my-3"></v-divider>
              <div class="d-flex align-center ga-2 flex-wrap">
                <v-progress-linear
                  :model-value="(fv.confidence_score || 0) * 100"
                  :color="getConfidenceColor(fv.confidence_score)"
                  height="4"
                  style="max-width: 80px;"
                ></v-progress-linear>
                <span class="text-caption">{{ Math.round((fv.confidence_score || 0) * 100) }}%</span>
                <v-chip v-if="fv.human_verified" size="x-small" color="success">
                  <v-icon start size="x-small">mdi-check</v-icon>
                  {{ t('entityDetail.verified') }}
                </v-chip>
                <v-chip v-if="fv.source_url" size="x-small" variant="outlined" :href="fv.source_url" target="_blank" tag="a">
                  <v-icon start size="x-small">mdi-link</v-icon>
                  {{ t('entityDetail.source') }}
                </v-chip>
                <v-spacer></v-spacer>
                <v-btn
                  v-if="!fv.human_verified"
                  size="small"
                  color="success"
                  variant="tonal"
                  @click="verifyFacet(fv.id)"
                >
                  <v-icon start size="small">mdi-check</v-icon>
                  {{ t('entityDetail.verify') }}
                </v-btn>
              </div>

              <!-- Timestamps / History -->
              <div v-if="fv.created_at || fv.updated_at" class="mt-2 d-flex align-center ga-3 text-caption text-medium-emphasis">
                <span v-if="fv.created_at">
                  <v-icon size="x-small" class="mr-1">mdi-clock-plus-outline</v-icon>
                  {{ t('entityDetail.created') }}: {{ formatDate(fv.created_at) }}
                </span>
                <span v-if="fv.updated_at && fv.updated_at !== fv.created_at">
                  <v-icon size="x-small" class="mr-1">mdi-clock-edit-outline</v-icon>
                  {{ t('entityDetail.updated') }}: {{ formatDate(fv.updated_at) }}
                </span>
              </div>
            </v-card>
          </div>
        </v-card-text>
      </v-card>
    </v-dialog>

    <!-- Edit Entity Dialog -->
    <v-dialog v-model="editDialog" max-width="500">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2">mdi-pencil</v-icon>
          {{ t('entityDetail.dialog.editEntity', { type: entityType?.name }) }}
        </v-card-title>
        <v-card-text>
          <v-form @submit.prevent="saveEntity">
            <v-text-field
              v-model="editForm.name"
              :label="t('entityDetail.dialog.name')"
              :rules="[v => !!v || t('entityDetail.dialog.nameRequired')]"
            ></v-text-field>
            <v-text-field
              v-model="editForm.external_id"
              :label="t('entityDetail.dialog.externalId')"
            ></v-text-field>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="editDialog = false">{{ t('common.cancel') }}</v-btn>
          <v-btn variant="tonal" color="primary" :loading="savingEntity" @click="saveEntity">
            {{ t('common.save') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Bulk Delete Confirmation Dialog -->
    <v-dialog v-model="bulkDeleteConfirm" max-width="400">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon color="error" class="mr-2">mdi-alert</v-icon>
          {{ t('entityDetail.dialog.deleteFacets') }}
        </v-card-title>
        <v-card-text>
          <p>{{ t('entityDetail.dialog.deleteFacetsConfirm', { count: selectedFacetIds.length }) }}</p>
          <p class="text-caption text-medium-emphasis mt-2">{{ t('entityDetail.dialog.cannotUndo') }}</p>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="bulkDeleteConfirm = false">{{ t('common.cancel') }}</v-btn>
          <v-btn variant="tonal" color="error" :loading="bulkActionLoading" @click="bulkDelete">
            <v-icon start>mdi-delete</v-icon>
            {{ t('common.delete') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Single Facet Delete Confirmation Dialog -->
    <v-dialog v-model="singleDeleteConfirm" max-width="400">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon color="error" class="mr-2">mdi-alert</v-icon>
          {{ t('entityDetail.dialog.deleteFacets') }}
        </v-card-title>
        <v-card-text>
          <p>{{ t('entityDetail.dialog.deleteFacetsConfirm', { count: 1 }) }}</p>
          <p class="text-caption text-medium-emphasis mt-2">{{ t('entityDetail.dialog.cannotUndo') }}</p>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="singleDeleteConfirm = false">{{ t('common.cancel') }}</v-btn>
          <v-btn variant="tonal" color="error" :loading="deletingFacet" @click="deleteSingleFacet">
            <v-icon start>mdi-delete</v-icon>
            {{ t('common.delete') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

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
    <v-dialog v-model="addRelationDialog" max-width="600" scrollable>
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon start>{{ editingRelation ? 'mdi-pencil' : 'mdi-link-plus' }}</v-icon>
          {{ editingRelation ? t('entityDetail.dialog.editRelation') : t('entityDetail.dialog.addRelation') }}
        </v-card-title>
        <v-card-text>
          <v-form ref="relationForm" @submit.prevent="saveRelation">
            <!-- Relation Type Selection -->
            <v-select
              v-model="newRelation.relation_type_id"
              :items="relationTypes"
              item-title="name"
              item-value="id"
              :label="t('entityDetail.dialog.relationType')"
              :rules="[v => !!v || t('common.required')]"
              variant="outlined"
              density="comfortable"
              class="mb-3"
              :loading="loadingRelationTypes"
            >
              <template v-slot:item="{ item, props }">
                <v-list-item v-bind="props">
                  <template v-slot:prepend>
                    <v-icon :color="item.raw.color || 'primary'">mdi-link-variant</v-icon>
                  </template>
                  <v-list-item-subtitle v-if="item.raw.description">
                    {{ item.raw.description }}
                  </v-list-item-subtitle>
                </v-list-item>
              </template>
            </v-select>

            <!-- Direction Selection -->
            <v-radio-group
              v-model="newRelation.direction"
              :label="t('entityDetail.dialog.relationDirection')"
              inline
              class="mb-3"
            >
              <v-radio :label="t('entityDetail.dialog.outgoing')" value="outgoing"></v-radio>
              <v-radio :label="t('entityDetail.dialog.incoming')" value="incoming"></v-radio>
            </v-radio-group>

            <!-- Target Entity Selection -->
            <v-autocomplete
              v-model="newRelation.target_entity_id"
              :items="targetEntities"
              item-title="name"
              item-value="id"
              :label="t('entityDetail.dialog.targetEntity')"
              :rules="[v => !!v || t('common.required')]"
              variant="outlined"
              density="comfortable"
              :loading="searchingEntities"
              :search-input.sync="entitySearchQuery"
              @update:search="searchEntities"
              no-filter
              class="mb-3"
            >
              <template v-slot:item="{ item, props }">
                <v-list-item v-bind="props">
                  <template v-slot:prepend>
                    <v-icon color="grey">mdi-domain</v-icon>
                  </template>
                  <v-list-item-subtitle>
                    {{ item.raw.entity_type_name }}
                  </v-list-item-subtitle>
                </v-list-item>
              </template>
              <template v-slot:no-data>
                <v-list-item>
                  <v-list-item-title>
                    {{ entitySearchQuery?.length >= 2 ? t('entityDetail.dialog.noEntitiesFound') : t('entityDetail.dialog.typeToSearch') }}
                  </v-list-item-title>
                </v-list-item>
              </template>
            </v-autocomplete>

            <!-- Optional Attributes (JSON) -->
            <v-textarea
              v-model="newRelation.attributes_json"
              :label="t('entityDetail.dialog.relationAttributes')"
              :hint="t('entityDetail.dialog.relationAttributesHint')"
              persistent-hint
              variant="outlined"
              rows="2"
              class="mb-3"
            ></v-textarea>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="closeRelationDialog">{{ t('common.cancel') }}</v-btn>
          <v-btn variant="tonal" color="primary" :loading="savingRelation" @click="saveRelation">
            {{ t('common.save') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Relation Confirmation -->
    <v-dialog v-model="deleteRelationConfirm" max-width="400">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon color="error" class="mr-2">mdi-alert</v-icon>
          {{ t('entityDetail.dialog.deleteRelation') }}
        </v-card-title>
        <v-card-text>
          <p>{{ t('entityDetail.dialog.deleteRelationConfirm') }}</p>
          <p v-if="relationToDelete" class="text-caption text-medium-emphasis mt-2">
            {{ relationToDelete.relation_type_name }}: {{ relationToDelete.target_entity_name || relationToDelete.source_entity_name }}
          </p>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="deleteRelationConfirm = false">{{ t('common.cancel') }}</v-btn>
          <v-btn variant="tonal" color="error" :loading="deletingRelation" @click="deleteRelation">
            {{ t('common.delete') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Export Dialog -->
    <v-dialog v-model="exportDialog" max-width="500">
      <v-card>
        <v-card-title>
          <v-icon start>mdi-export</v-icon>
          {{ t('entityDetail.dialog.exportData') }}
        </v-card-title>
        <v-card-text>
          <p class="mb-4">{{ t('entityDetail.dialog.selectExport') }}</p>

          <v-select
            v-model="exportFormat"
            :items="exportFormats"
            item-title="label"
            item-value="value"
            :label="t('entityDetail.dialog.format')"
            variant="outlined"
            class="mb-4"
          ></v-select>

          <v-checkbox
            v-model="exportOptions.facets"
            :label="t('entityDetail.dialog.exportProperties')"
            hide-details
          ></v-checkbox>
          <v-checkbox
            v-model="exportOptions.relations"
            :label="t('entityDetail.dialog.exportRelations')"
            hide-details
          ></v-checkbox>
          <v-checkbox
            v-model="exportOptions.dataSources"
            :label="t('entityDetail.dialog.exportDataSources')"
            hide-details
          ></v-checkbox>
          <v-checkbox
            v-model="exportOptions.notes"
            :label="t('entityDetail.dialog.exportNotes')"
            hide-details
          ></v-checkbox>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="exportDialog = false">{{ t('common.cancel') }}</v-btn>
          <v-btn variant="tonal" color="primary" :loading="exporting" @click="exportData">
            <v-icon start>mdi-download</v-icon>
            {{ t('common.export') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

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
    <v-dialog v-model="sourceDetailsDialog" max-width="600" scrollable>
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon start :color="getSourceTypeColor(selectedSourceFacet?.source_type)">
            {{ getSourceTypeIcon(selectedSourceFacet?.source_type) }}
          </v-icon>
          {{ t('entityDetail.source') }}
          <v-spacer></v-spacer>
          <v-btn icon="mdi-close" variant="tonal" @click="sourceDetailsDialog = false" :aria-label="t('common.close')"></v-btn>
        </v-card-title>
        <v-card-text v-if="selectedSourceFacet">
          <!-- Source Type Info -->
          <v-chip
            size="small"
            :color="getSourceTypeColor(selectedSourceFacet.source_type)"
            class="mb-4"
          >
            <v-icon start size="small">{{ getSourceTypeIcon(selectedSourceFacet.source_type) }}</v-icon>
            {{ getSourceTypeLabel(selectedSourceFacet.source_type) }}
          </v-chip>

          <!-- Document Source -->
          <template v-if="selectedSourceFacet.source_type === 'DOCUMENT'">
            <div v-if="selectedSourceFacet.document_title" class="mb-3">
              <div class="text-caption text-medium-emphasis mb-1">{{ t('entityDetail.document') }}</div>
              <div class="text-body-1">{{ selectedSourceFacet.document_title }}</div>
            </div>
            <div v-if="selectedSourceFacet.document_url" class="mb-3">
              <v-btn
                :href="selectedSourceFacet.document_url"
                target="_blank"
                color="primary"
                variant="tonal"
                size="small"
              >
                <v-icon start>mdi-file-document</v-icon>
                {{ t('common.openDocument') }}
              </v-btn>
            </div>
          </template>

          <!-- PySis Source -->
          <template v-else-if="selectedSourceFacet.source_type === 'PYSIS'">
            <v-alert type="info" variant="tonal" density="compact" class="mb-3">
              {{ t('entityDetail.sourceTypes.pysis') }}
            </v-alert>

            <!-- PySis Process Info -->
            <div v-if="getPysisSourceInfo(selectedSourceFacet)" class="mb-3">
              <div v-if="getPysisSourceInfo(selectedSourceFacet)?.processTitle" class="mb-2">
                <div class="text-caption text-medium-emphasis">Prozess</div>
                <div class="text-body-1">{{ getPysisSourceInfo(selectedSourceFacet)?.processTitle }}</div>
              </div>
              <div v-if="getPysisSourceInfo(selectedSourceFacet)?.processId" class="mb-2">
                <div class="text-caption text-medium-emphasis">Prozess-ID</div>
                <code class="text-body-2">{{ getPysisSourceInfo(selectedSourceFacet)?.processId }}</code>
              </div>
              <div v-if="getPysisSourceInfo(selectedSourceFacet)?.fieldNames?.length" class="mb-2">
                <div class="text-caption text-medium-emphasis mb-1">Feldname(n)</div>
                <div class="d-flex flex-wrap ga-1">
                  <v-chip
                    v-for="fieldName in getPysisSourceInfo(selectedSourceFacet)?.fieldNames || []"
                    :key="fieldName"
                    size="small"
                    variant="outlined"
                    color="secondary"
                  >
                    {{ fieldName }}
                  </v-chip>
                </div>
              </div>
            </div>

            <!-- PySis Field Values -->
            <div v-if="selectedSourceFacet.value?.pysis_fields" class="mb-3">
              <div class="text-caption text-medium-emphasis mb-2">Feldwerte</div>
              <v-list density="compact" class="bg-surface-variant rounded">
                <v-list-item
                  v-for="(fieldValue, fieldName) in selectedSourceFacet.value.pysis_fields"
                  :key="fieldName"
                >
                  <v-list-item-title class="text-caption font-weight-medium">{{ fieldName }}</v-list-item-title>
                  <v-list-item-subtitle>{{ fieldValue }}</v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </div>
          </template>

          <!-- Manual Source -->
          <template v-else-if="selectedSourceFacet.source_type === 'MANUAL'">
            <v-alert type="success" variant="tonal" density="compact" class="mb-3">
              {{ t('entityDetail.sourceTypes.manual') }}
            </v-alert>
            <div v-if="selectedSourceFacet.verified_by" class="text-body-2">
              {{ t('common.createdBy') }}: {{ selectedSourceFacet.verified_by }}
            </div>
          </template>

          <!-- Smart Query Source -->
          <template v-else-if="selectedSourceFacet.source_type === 'SMART_QUERY'">
            <v-alert type="info" variant="tonal" density="compact" class="mb-3">
              {{ t('entityDetail.sourceTypes.smartQuery') }}
            </v-alert>
          </template>

          <!-- AI Assistant Source -->
          <template v-else-if="selectedSourceFacet.source_type === 'AI_ASSISTANT'">
            <v-alert color="info" variant="tonal" density="compact" class="mb-3">
              {{ t('entityDetail.sourceTypes.aiAssistant') }}
            </v-alert>
            <div v-if="selectedSourceFacet.ai_model_used" class="text-body-2 mb-2">
              Model: {{ selectedSourceFacet.ai_model_used }}
            </div>
          </template>

          <!-- Import Source -->
          <template v-else-if="selectedSourceFacet.source_type === 'IMPORT'">
            <v-alert type="warning" variant="tonal" density="compact" class="mb-3">
              {{ t('entityDetail.sourceTypes.import') }}
            </v-alert>
          </template>

          <!-- Source URL (shown for web URLs, excluding PySis which shows structured info above) -->
          <div v-if="selectedSourceFacet.source_url && isValidWebUrl(selectedSourceFacet.source_url) && selectedSourceFacet.source_type !== 'PYSIS'" class="mt-4">
            <div class="text-caption text-medium-emphasis mb-1">{{ t('entities.facet.sourceUrl') }}</div>
            <v-btn
              :href="selectedSourceFacet.source_url"
              target="_blank"
              color="primary"
              variant="tonal"
              size="small"
              class="text-none"
            >
              <v-icon start size="small">mdi-open-in-new</v-icon>
              {{ selectedSourceFacet.source_url }}
            </v-btn>
          </div>

          <!-- Confidence & Dates -->
          <v-divider class="my-4"></v-divider>
          <div class="d-flex flex-wrap ga-4">
            <div v-if="selectedSourceFacet.confidence_score != null">
              <div class="text-caption text-medium-emphasis">{{ t('entities.facet.confidence') }}</div>
              <div class="text-body-2">{{ Math.round(selectedSourceFacet.confidence_score * 100) }}%</div>
            </div>
            <div v-if="selectedSourceFacet.created_at">
              <div class="text-caption text-medium-emphasis">{{ t('entityDetail.created') }}</div>
              <div class="text-body-2">{{ formatDate(selectedSourceFacet.created_at) }}</div>
            </div>
            <div v-if="selectedSourceFacet.human_verified">
              <div class="text-caption text-medium-emphasis">{{ t('entityDetail.verifiedLabel') }}</div>
              <div class="text-body-2">
                <v-icon color="success" size="small">mdi-check-circle</v-icon>
                {{ selectedSourceFacet.verified_at ? formatDate(selectedSourceFacet.verified_at) : 'Yes' }}
              </div>
            </div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="sourceDetailsDialog = false">{{ t('common.close') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Notes Dialog -->
    <v-dialog v-model="notesDialog" max-width="700" scrollable>
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon start>mdi-note-text</v-icon>
          {{ t('entityDetail.notes') }}
          <v-spacer></v-spacer>
          <v-btn icon="mdi-close" variant="tonal" @click="notesDialog = false" :aria-label="t('common.close')"></v-btn>
        </v-card-title>
        <v-card-text>
          <!-- Add Note Form -->
          <v-textarea
            v-model="newNote"
            :label="t('entityDetail.dialog.addNote')"
            rows="3"
            variant="outlined"
            class="mb-4"
          ></v-textarea>
          <div class="d-flex justify-end mb-4">
            <v-btn
              color="primary"
              :disabled="!newNote.trim()"
              :loading="savingNote"
              @click="saveNote"
            >
              <v-icon start>mdi-plus</v-icon>
              {{ t('entityDetail.dialog.saveNote') }}
            </v-btn>
          </div>

          <v-divider class="mb-4"></v-divider>

          <!-- Notes List -->
          <div v-if="notes.length">
            <v-card
              v-for="note in notes"
              :key="note.id"
              variant="outlined"
              class="mb-3 pa-3"
            >
              <div class="d-flex align-start">
                <v-avatar size="32" color="primary" class="mr-3">
                  <v-icon size="small" color="on-primary">mdi-account</v-icon>
                </v-avatar>
                <div class="flex-grow-1">
                  <div class="d-flex align-center mb-1">
                    <span class="text-body-2 font-weight-medium">{{ note.author || t('entityDetail.systemAuthor') }}</span>
                    <span class="text-caption text-medium-emphasis ml-2">{{ formatDate(note.created_at) }}</span>
                    <v-spacer></v-spacer>
                    <v-btn
                      icon="mdi-delete"
                      size="x-small"
                      variant="tonal"
                      color="error"
                      @click="deleteNote(note.id)"
                    ></v-btn>
                  </div>
                  <p class="text-body-2 mb-0 text-pre-wrap">{{ note.content }}</p>
                </div>
              </div>
            </v-card>
          </div>
          <div v-else class="text-center pa-4 text-medium-emphasis">
            <v-icon size="48" color="grey-lighten-2" class="mb-2">mdi-note-off-outline</v-icon>
            <p>{{ t('entityDetail.emptyState.noNotes') }}</p>
          </div>
        </v-card-text>
      </v-card>
    </v-dialog>

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
import FavoriteButton from '@/components/FavoriteButton.vue'

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
const exportFormats = computed(() => [
  { label: t('entityDetail.formats.csvExcel'), value: 'csv' },
  { label: t('entityDetail.formats.json'), value: 'json' },
  { label: t('entityDetail.formats.pdfReport'), value: 'pdf' },
])
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

const hasAttributes = computed(() =>
  entity.value?.core_attributes && Object.keys(entity.value.core_attributes).length > 0
)

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

// Check if the form can be saved
const canSaveFacet = computed(() => {
  if (!newFacet.value.facet_type_id) return false

  const facetType = selectedFacetTypeForForm.value
  if (!facetType) return false

  // If facet type has a schema, check if required fields are filled
  if (facetType.value_schema?.properties) {
    const requiredFields = facetType.value_schema.required || []
    for (const field of requiredFields) {
      const value = newFacet.value.value[field]
      if (value === undefined || value === null || value === '') {
        return false
      }
    }
    // At least one field should be filled
    return Object.values(newFacet.value.value).some(v =>
      v !== undefined && v !== null && v !== ''
    )
  }

  // For simple text facets, check text_representation
  return !!newFacet.value.text_representation
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

const documentHeaders = computed(() => [
  { title: t('entityDetail.documentHeaders.title'), key: 'title' },
  { title: t('entityDetail.documentHeaders.type'), key: 'document_type' },
  { title: t('entityDetail.documentHeaders.date'), key: 'created_at' },
])

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
  }
}

// Helper functions for external data display
function getFieldType(value: any): string {
  if (value === null) return 'null'
  if (Array.isArray(value)) return 'array'
  if (typeof value === 'boolean') return 'boolean'
  if (typeof value === 'number') return Number.isInteger(value) ? 'integer' : 'float'
  if (typeof value === 'string') return 'string'
  if (typeof value === 'object') return 'object'
  return typeof value
}

function getFieldTypeColor(value: any): string {
  const type = getFieldType(value)
  switch (type) {
    case 'string': return 'green'
    case 'integer': return 'blue'
    case 'float': return 'indigo'
    case 'boolean': return 'orange'
    case 'array': return 'purple'
    case 'object': return 'teal'
    case 'null': return 'grey'
    default: return 'grey'
  }
}

function formatFieldValue(value: any): string {
  if (value === null) return 'null'
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  if (typeof value === 'string' && value.length > 100) return value.substring(0, 100) + '...'
  return String(value)
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
  } finally {
    loadingChildren.value = false
  }
}

// Computed: Filtered children based on search query
const filteredChildren = computed(() => {
  if (!childrenSearchQuery.value) return children.value
  const query = childrenSearchQuery.value.toLowerCase()
  return children.value.filter(
    (child) =>
      child.name.toLowerCase().includes(query) ||
      child.external_id?.toLowerCase().includes(query)
  )
})

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

function goToSources() {
  // Note: DataSources are no longer directly linked to Entities via location_name.
  // Navigate to sources view without filter - users can filter by category.
  router.push({ path: '/sources' })
}

// Attribute key translation map (fallback)
const attributeTranslations = computed<Record<string, string>>(() => ({
  population: t('entityDetail.attributes.population'),
  area_km2: t('entityDetail.attributes.area'),
  official_code: t('entityDetail.attributes.officialCode'),
  locality_type: t('entityDetail.attributes.localityType'),
  website: t('entityDetail.attributes.website'),
  academic_title: t('entityDetail.attributes.academicTitle'),
  first_name: t('entityDetail.attributes.firstName'),
  last_name: t('entityDetail.attributes.lastName'),
  email: t('entityDetail.attributes.email'),
  phone: t('entityDetail.attributes.phone'),
  role: t('entityDetail.attributes.role'),
  org_type: t('entityDetail.attributes.orgType'),
  address: t('entityDetail.attributes.address'),
  event_date: t('entityDetail.attributes.eventDate'),
  event_end_date: t('entityDetail.attributes.eventEndDate'),
  location: t('entityDetail.attributes.location'),
  organizer: t('entityDetail.attributes.organizer'),
  event_type: t('entityDetail.attributes.eventType'),
  description: t('entityDetail.attributes.description'),
}))

// Helpers
function formatAttributeKey(key: string): string {
  // First try to get title from entity type's attribute_schema
  const schema = entityType.value?.attribute_schema
  if (schema?.properties?.[key]?.title) {
    return schema.properties[key].title
  }
  // Then try the translation map
  if (attributeTranslations.value[key]) {
    return attributeTranslations.value[key]
  }
  // Finally, fallback to basic formatting
  return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

function formatAttributeValue(value: any): string {
  if (typeof value === 'number') {
    return value.toLocaleString('de-DE')
  }
  return String(value)
}

function formatFacetValue(facet: any): string {
  if (facet.text_representation) return facet.text_representation
  if (typeof facet.value === 'string') return facet.value
  if (facet.value?.text) return facet.value.text
  return JSON.stringify(facet.value)
}

function formatDate(dateStr: string): string {
  return format(new Date(dateStr), 'dd.MM.yyyy HH:mm', { locale: de })
}

function isValidWebUrl(url: string): boolean {
  if (!url) return false
  return url.startsWith('http://') || url.startsWith('https://')
}

function getPysisSourceInfo(facet: any): { processId?: string; processTitle?: string; fieldNames?: string[] } | null {
  if (!facet) return null

  const info: { processId?: string; processTitle?: string; fieldNames?: string[] } = {}

  // Extract process ID from source_url (pysis://process/{id}) if available
  if (facet.source_url?.startsWith('pysis://process/')) {
    info.processId = facet.source_url.replace('pysis://process/', '')
  }

  // Get process title and field names from value object if stored
  if (facet.value?.pysis_process_title) {
    info.processTitle = facet.value.pysis_process_title
  }
  if (facet.value?.pysis_process_id) {
    info.processId = facet.value.pysis_process_id
  }
  if (facet.value?.pysis_field_names) {
    info.fieldNames = Array.isArray(facet.value.pysis_field_names)
      ? facet.value.pysis_field_names
      : [facet.value.pysis_field_names]
  }

  // Extract field names from pysis_fields keys if available
  if (!info.fieldNames && facet.value?.pysis_fields) {
    info.fieldNames = Object.keys(facet.value.pysis_fields)
  }

  return Object.keys(info).length > 0 ? info : null
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

function getSourceTypeColor(sourceType: string | null | undefined): string {
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

function getSourceTypeIcon(sourceType: string | null | undefined): string {
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

function getSourceTypeLabel(sourceType: string | null | undefined): string {
  const labels: Record<string, string> = {
    document: t('entityDetail.sourceTypes.document'),
    manual: t('entityDetail.sourceTypes.manual'),
    pysis: t('entityDetail.sourceTypes.pysis'),
    smart_query: t('entityDetail.sourceTypes.smartQuery'),
    ai_assistant: t('entityDetail.sourceTypes.aiAssistant'),
    import: t('entityDetail.sourceTypes.import'),
  }
  return labels[normalizeSourceType(sourceType)] || t('entityDetail.sourceTypes.document')
}

function getSourceStatusColor(status: string): string {
  const colors: Record<string, string> = {
    ACTIVE: 'success',
    INACTIVE: 'grey',
    ERROR: 'error',
    PENDING: 'warning',
  }
  return colors[status] || 'grey'
}

function getSourceStatusIcon(status: string): string {
  const icons: Record<string, string> = {
    ACTIVE: 'mdi-check-circle',
    INACTIVE: 'mdi-pause-circle',
    ERROR: 'mdi-alert-circle',
    PENDING: 'mdi-clock',
  }
  return icons[status] || 'mdi-help-circle'
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

function getSeverityIcon(severity: string | null): string {
  if (!severity) return 'mdi-minus'
  const s = severity.toLowerCase()
  if (s === 'hoch' || s === 'high') return 'mdi-alert'
  if (s === 'mittel' || s === 'medium') return 'mdi-alert-circle-outline'
  if (s === 'niedrig' || s === 'low') return 'mdi-information-outline'
  return 'mdi-minus'
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
  if (!entity.value || entityType.value?.slug !== 'municipality') {
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
  if (tab === 'children' && !childrenLoaded.value) {
    loadChildren()
  }
})

// Watch for route changes
watch([typeSlug, entitySlug], () => {
  // Reset state for new entity
  bulkMode.value = false
  selectedFacetIds.value = []
  facetSearchQuery.value = ''
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
</style>
