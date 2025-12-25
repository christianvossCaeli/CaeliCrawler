<template>
  <div>
    <!-- Loading Overlay -->
    <v-overlay :model-value="loading && initialLoad" class="align-center justify-center" persistent >
      <v-card class="pa-8 text-center" min-width="320" elevation="24">
        <v-progress-circular indeterminate size="80" width="6" color="primary" class="mb-4"></v-progress-circular>
        <div class="text-h6 mb-2">{{ $t('results.loading.title') }}</div>
        <div class="text-body-2 text-medium-emphasis">{{ $t('results.loading.subtitle') }}</div>
      </v-card>
    </v-overlay>

    <PageHeader
      :title="$t('results.title')"
      :subtitle="$t('results.subtitle')"
      icon="mdi-chart-box"
    >
      <template #actions>
        <!-- Bulk Actions -->
        <v-btn
          v-if="selectedResults.length > 0"
          color="success"
          variant="outlined"
          prepend-icon="mdi-check-all"
          :loading="bulkVerifying"
          @click="bulkVerify"
        >
          {{ selectedResults.length }} {{ $t('results.actions.bulkVerify') }}
        </v-btn>
        <v-btn
          color="success"
          variant="outlined"
          prepend-icon="mdi-download"
          @click="exportCsv"
        >
          {{ $t('results.actions.csvExport') }}
        </v-btn>
        <v-btn
          color="primary"
          variant="outlined"
          prepend-icon="mdi-refresh"
          :loading="loading"
          @click="loadData"
        >
          {{ $t('results.actions.refresh') }}
        </v-btn>
      </template>
    </PageHeader>

    <!-- Statistics Bar -->
    <v-row class="mb-4">
      <v-col cols="6" sm="3">
        <v-card variant="outlined">
          <v-card-text class="text-center py-3">
            <div class="text-h5 text-primary">{{ stats.total }}</div>
            <div class="text-caption">{{ $t('results.stats.total') }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6" sm="3">
        <v-card
          :variant="verifiedFilter === true ? 'elevated' : 'outlined'"
          :color="verifiedFilter === true ? 'success' : undefined"
          @click="toggleVerifiedFilter(true)"
          class="cursor-pointer"
        >
          <v-card-text class="text-center py-3">
            <div class="text-h5 text-success">{{ stats.verified }}</div>
            <div class="text-caption">{{ $t('results.stats.verified') }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6" sm="3">
        <v-card variant="outlined">
          <v-card-text class="text-center py-3">
            <div class="text-h5 text-info">{{ stats.high_confidence_count }}</div>
            <div class="text-caption">{{ $t('results.stats.highConfidence') }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6" sm="3">
        <v-card variant="outlined">
          <v-card-text class="text-center py-3">
            <div class="text-h5">{{ stats.avg_confidence ? (stats.avg_confidence * 100).toFixed(0) + '%' : '-' }}</div>
            <div class="text-caption">{{ $t('results.stats.avgConfidence') }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Filters -->
    <v-card class="mb-4">
      <v-card-text>
        <v-row align="center">
          <v-col cols="12" md="3">
            <v-text-field
              v-model="searchQuery"
              prepend-inner-icon="mdi-magnify"
              :label="$t('results.filters.fulltext')"
              clearable
              hide-details
              :placeholder="$t('results.filters.fulltextPlaceholder')"
              @update:model-value="debouncedLoadData"
            />
          </v-col>
          <v-col cols="6" md="2">
            <v-autocomplete
              v-model="locationFilter"
              :items="locations"
              :label="$t('results.filters.location')"
              clearable
              hide-details
              @update:model-value="loadData"
            />
          </v-col>
          <v-col cols="6" md="2">
            <v-select
              v-model="extractionTypeFilter"
              :items="extractionTypes"
              :label="$t('results.filters.analysisType')"
              clearable
              hide-details
              @update:model-value="loadData"
            />
          </v-col>
          <v-col cols="6" md="2">
            <v-select
              v-model="categoryFilter"
              :items="categories"
              item-title="name"
              item-value="id"
              :label="$t('results.filters.category')"
              clearable
              hide-details
              @update:model-value="loadData"
            />
          </v-col>
          <v-col cols="6" md="3">
            <v-slider
              v-model="minConfidence"
              :min="0"
              :max="100"
              :step="5"
              :label="$t('results.filters.minConfidence')"
              thumb-label="always"
              hide-details
              @update:model-value="debouncedLoadData"
            >
              <template v-slot:thumb-label="{ modelValue }">{{ modelValue }}%</template>
            </v-slider>
          </v-col>
        </v-row>
        <v-row align="center" class="mt-2">
          <v-col cols="6" md="2">
            <v-text-field
              v-model="dateFrom"
              type="date"
              :label="$t('results.filters.dateFrom')"
              clearable
              hide-details
              @update:model-value="loadData"
            />
          </v-col>
          <v-col cols="6" md="2">
            <v-text-field
              v-model="dateTo"
              type="date"
              :label="$t('results.filters.dateTo')"
              clearable
              hide-details
              @update:model-value="loadData"
            />
          </v-col>
          <v-col cols="12" md="8" class="d-flex align-center">
            <v-btn v-if="hasActiveFilters" variant="tonal" color="primary" size="small" @click="clearFilters">
              <v-icon size="small" class="mr-1">mdi-filter-off</v-icon>
              {{ $t('results.filters.resetFilters') }}
            </v-btn>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Results Table -->
    <v-card>
      <v-data-table-server
        v-model="selectedResults"
        v-model:items-per-page="perPage"
        v-model:page="page"
        v-model:sort-by="sortBy"
        :headers="headers"
        :items="results"
        :items-length="totalResults"
        :loading="loading"
        show-select
        item-value="id"
        @update:options="onTableOptionsUpdate"
      >
        <template v-slot:item.document="{ item }">
          <div class="py-2">
            <div class="font-weight-medium text-truncate" style="max-width: 220px;" :title="(item.raw?.document_title || item.document_title) || (item.raw?.document_url || item.document_url)">
              {{ (item.raw?.document_title || item.document_title) || t('results.detail.noTitle') }}
            </div>
            <div class="text-caption text-medium-emphasis">
              <router-link :to="`/documents?search=${encodeURIComponent((item.raw?.document_title || item.document_title) || '')}`" class="text-decoration-none">
                <v-icon size="x-small" class="mr-1">mdi-file-document</v-icon>{{ $t('results.columns.document') }}
              </router-link>
            </div>
          </div>
        </template>

        <template v-slot:item.extraction_type="{ item }">
          <v-chip size="small" color="primary" variant="tonal">{{ item.raw?.extraction_type || item.extraction_type }}</v-chip>
        </template>

        <!-- Dynamic Entity Reference Columns -->
        <template
          v-for="entityType in entityReferenceColumns"
          :key="`entity-${entityType}`"
          v-slot:[`item.entity_references.${entityType}`]="{ item }"
        >
          <div class="entity-references">
            <template v-for="(ref, idx) in getEntityReferencesByType(item.raw || item, entityType)" :key="idx">
              <div
                class="entity-ref-text cursor-pointer text-info"
                @click="filterByEntityReference(entityType, ref.entity_name)"
                :title="ref.entity_name"
              >
                {{ ref.entity_name }}
              </div>
            </template>
            <span v-if="!getEntityReferencesByType(item.raw || item, entityType).length" class="text-medium-emphasis">-</span>
          </div>
        </template>

        <template v-slot:item.confidence_score="{ item }">
          <v-chip :color="getConfidenceColor(item.raw?.confidence_score ?? item.confidence_score)" size="small">
            {{ (item.raw?.confidence_score ?? item.confidence_score) ? ((item.raw?.confidence_score ?? item.confidence_score) * 100).toFixed(0) + '%' : '-' }}
          </v-chip>
        </template>

        <template v-slot:item.human_verified="{ item }">
          <v-icon v-if="item.raw?.human_verified ?? item.human_verified" color="success" size="small">mdi-check-circle</v-icon>
          <v-icon v-else color="grey" size="small">mdi-circle-outline</v-icon>
        </template>

        <template v-slot:item.created_at="{ item }">
          <div class="text-caption">{{ formatDate(item.raw?.created_at || item.created_at) }}</div>
        </template>

        <template v-slot:item.actions="{ item }">
          <div class="table-actions d-flex justify-end ga-1">
            <v-btn icon="mdi-eye" size="small" variant="tonal" :title="$t('common.details')" :aria-label="$t('common.details')" @click="showDetails(item.raw || item)"></v-btn>
            <v-btn :icon="(item.raw?.human_verified ?? item.human_verified) ? 'mdi-check-circle' : 'mdi-check'" size="small" variant="tonal" :color="(item.raw?.human_verified ?? item.human_verified) ? 'success' : 'grey'" :title="(item.raw?.human_verified ?? item.human_verified) ? $t('results.actions.verified') : $t('results.actions.verify')" :aria-label="(item.raw?.human_verified ?? item.human_verified) ? $t('results.actions.verified') : $t('results.actions.verify')" @click="verifyResult(item.raw || item)"></v-btn>
            <v-btn icon="mdi-file-document" size="small" variant="tonal" color="info" :title="$t('results.actions.goToDocument')" :aria-label="$t('results.actions.goToDocument')" :to="`/documents?search=${encodeURIComponent((item.raw?.document_title || item.document_title) || '')}`"></v-btn>
            <v-btn icon="mdi-code-json" size="small" variant="tonal" :title="$t('results.actions.exportJson')" :aria-label="$t('results.actions.exportJson')" @click="exportJson(item.raw || item)"></v-btn>
          </div>
        </template>
      </v-data-table-server>
    </v-card>

    <!-- Details Dialog -->
    <v-dialog v-model="detailsDialog" max-width="950" scrollable>
      <v-card v-if="selectedResult">
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2">mdi-brain</v-icon>
          {{ $t('results.detail.title') }}
          <v-spacer />
          <v-chip :color="getConfidenceColor(selectedResult.confidence_score)" class="mr-2">
            {{ selectedResult.confidence_score ? (selectedResult.confidence_score * 100).toFixed(0) + '%' : '-' }}
          </v-chip>
          <v-chip v-if="selectedResult.human_verified" color="success">
            <v-icon size="small" class="mr-1">mdi-check</v-icon>{{ $t('results.columns.verified') }}
          </v-chip>
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-4" style="max-height: 70vh; overflow-y: auto;">
          <!-- Document Info -->
          <v-card variant="outlined" class="mb-4">
            <v-card-title class="text-subtitle-1 d-flex align-center">
              <v-icon size="small" class="mr-2">mdi-file-document</v-icon>
              {{ $t('results.detail.sourceDocument') }}
              <v-spacer />
              <v-btn size="small" variant="tonal" color="primary" :to="`/documents?search=${encodeURIComponent(selectedResult.document_title || '')}`">
                <v-icon size="small" class="mr-1">mdi-open-in-new</v-icon>{{ $t('results.detail.goToDocument') }}
              </v-btn>
            </v-card-title>
            <v-card-text>
              <div><strong>{{ $t('results.detail.title') }}:</strong> {{ selectedResult.document_title || t('results.detail.noTitle') }}</div>
              <div v-if="selectedResult.document_url"><strong>{{ $t('results.detail.url') }}:</strong> <a :href="selectedResult.document_url" target="_blank">{{ selectedResult.document_url }}</a></div>
              <div><strong>{{ $t('results.detail.source') }}:</strong> {{ selectedResult.source_name || '-' }}</div>
            </v-card-text>
          </v-card>

          <!-- Extracted Content -->
          <template v-if="selectedResult.final_content || selectedResult.extracted_content">
            <!-- Entity References (Dynamic) -->
            <v-card v-if="selectedResult.entity_references?.length" variant="outlined" class="mb-4">
              <v-card-title class="text-subtitle-1">
                <v-icon size="small" class="mr-2">mdi-link-variant</v-icon>
                {{ $t('results.detail.entityReferences') }}
              </v-card-title>
              <v-card-text>
                <div class="d-flex flex-wrap ga-2">
                  <v-chip
                    v-for="(ref, idx) in selectedResult.entity_references"
                    :key="idx"
                    :color="getEntityTypeColor(ref.entity_type)"
                    size="small"
                    :to="ref.entity_id ? `/entities/${ref.entity_id}` : undefined"
                  >
                    <v-icon start size="x-small">{{ getEntityTypeIcon(ref.entity_type) }}</v-icon>
                    {{ ref.entity_name }}
                    <v-tooltip v-if="ref.role !== 'secondary'" activator="parent" location="top">
                      {{ ref.role }} ({{ Math.round(ref.confidence * 100) }}%)
                    </v-tooltip>
                  </v-chip>
                </div>
              </v-card-text>
            </v-card>

            <v-row class="mb-4">
              <v-col cols="12">
                <v-card variant="outlined" height="100%">
                  <v-card-title class="text-subtitle-1"><v-icon size="small" class="mr-2">mdi-check-circle</v-icon>{{ $t('results.detail.relevance') }}</v-card-title>
                  <v-card-text>
                    <v-chip :color="getContent(selectedResult).is_relevant ? 'success' : 'grey'">
                      {{ getContent(selectedResult).is_relevant ? t('results.detail.relevant') : t('results.detail.notRelevant') }}
                    </v-chip>
                    <span v-if="getContent(selectedResult).relevanz" class="ml-2 text-caption">{{ $t('results.detail.level') }}: {{ getContent(selectedResult).relevanz }}</span>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>

            <!-- Summary -->
            <v-card v-if="getContent(selectedResult).summary" variant="outlined" class="mb-4">
              <v-card-title class="text-subtitle-1"><v-icon size="small" class="mr-2">mdi-text</v-icon>{{ $t('results.detail.summary') }}</v-card-title>
              <v-card-text>{{ getContent(selectedResult).summary }}</v-card-text>
            </v-card>

            <!-- Pain Points -->
            <v-card v-if="getContent(selectedResult).pain_points?.length" variant="outlined" class="mb-4" color="error">
              <v-card-title class="text-subtitle-1"><v-icon size="small" class="mr-2">mdi-alert-circle</v-icon>{{ $t('results.detail.painPoints') }} ({{ getContent(selectedResult).pain_points.length }})</v-card-title>
              <v-card-text>
                <div class="d-flex flex-column ga-3">
                  <v-card
                    v-for="(pp, idx) in getContent(selectedResult).pain_points"
                    :key="idx"
                    variant="tonal"
                    color="error"
                    class="pa-3"
                  >
                    <template v-if="typeof pp === 'string'">
                      <div class="d-flex align-start ga-2">
                        <v-icon size="small" color="error" class="mt-1">mdi-alert-circle</v-icon>
                        <div class="text-body-1">{{ pp }}</div>
                      </div>
                    </template>
                    <template v-else>
                      <div class="d-flex align-start ga-2">
                        <v-icon size="small" color="error" class="mt-1">mdi-alert-circle</v-icon>
                        <div class="flex-grow-1">
                          <div class="text-body-1">{{ pp.description || pp.text || pp.concern || '' }}</div>
                          <div v-if="pp.type || pp.severity" class="d-flex flex-wrap ga-2 mt-2">
                            <v-chip v-if="pp.type" size="small" variant="outlined" color="error">{{ pp.type }}</v-chip>
                            <v-chip v-if="pp.severity" size="small" :color="getSeverityColor(pp.severity)">
                              <v-icon start size="x-small">{{ getSeverityIcon(pp.severity) }}</v-icon>
                              {{ pp.severity }}
                            </v-chip>
                          </div>
                          <div v-if="pp.quote" class="mt-2 pa-2 rounded bg-surface-variant">
                            <v-icon size="small" class="mr-1">mdi-format-quote-open</v-icon>
                            <span class="text-body-2 font-italic">{{ pp.quote }}</span>
                          </div>
                          <div v-if="pp.source || pp.source_url" class="mt-2">
                            <v-chip
                              size="small"
                              variant="outlined"
                              :href="pp.source_url || pp.source"
                              :target="pp.source_url || pp.source?.startsWith('http') ? '_blank' : undefined"
                              :tag="pp.source_url || pp.source?.startsWith('http') ? 'a' : 'span'"
                            >
                              <v-icon start size="x-small">mdi-link</v-icon>
                              {{ pp.source_url ? t('results.detail.source') : pp.source }}
                            </v-chip>
                          </div>
                        </div>
                      </div>
                    </template>
                  </v-card>
                </div>
              </v-card-text>
            </v-card>

            <!-- Positive Signals -->
            <v-card v-if="getContent(selectedResult).positive_signals?.length" variant="outlined" class="mb-4" color="success">
              <v-card-title class="text-subtitle-1"><v-icon size="small" class="mr-2">mdi-lightbulb-on</v-icon>{{ $t('results.detail.positiveSignals') }} ({{ getContent(selectedResult).positive_signals.length }})</v-card-title>
              <v-card-text>
                <div class="d-flex flex-column ga-3">
                  <v-card
                    v-for="(ps, idx) in getContent(selectedResult).positive_signals"
                    :key="idx"
                    variant="tonal"
                    color="success"
                    class="pa-3"
                  >
                    <template v-if="typeof ps === 'string'">
                      <div class="d-flex align-start ga-2">
                        <v-icon size="small" color="success" class="mt-1">mdi-lightbulb-on</v-icon>
                        <div class="text-body-1">{{ ps }}</div>
                      </div>
                    </template>
                    <template v-else>
                      <div class="d-flex align-start ga-2">
                        <v-icon size="small" color="success" class="mt-1">mdi-lightbulb-on</v-icon>
                        <div class="flex-grow-1">
                          <div class="text-body-1">{{ ps.description || ps.text || ps.opportunity || '' }}</div>
                          <div v-if="ps.type" class="d-flex flex-wrap ga-2 mt-2">
                            <v-chip size="small" variant="outlined" color="success">{{ ps.type }}</v-chip>
                          </div>
                          <div v-if="ps.quote" class="mt-2 pa-2 rounded bg-surface-variant">
                            <v-icon size="small" class="mr-1">mdi-format-quote-open</v-icon>
                            <span class="text-body-2 font-italic">{{ ps.quote }}</span>
                          </div>
                          <div v-if="ps.source || ps.source_url" class="mt-2">
                            <v-chip
                              size="small"
                              variant="outlined"
                              :href="ps.source_url || ps.source"
                              :target="ps.source_url || ps.source?.startsWith('http') ? '_blank' : undefined"
                              :tag="ps.source_url || ps.source?.startsWith('http') ? 'a' : 'span'"
                            >
                              <v-icon start size="x-small">mdi-link</v-icon>
                              {{ ps.source_url ? t('results.detail.source') : ps.source }}
                            </v-chip>
                          </div>
                        </div>
                      </div>
                    </template>
                  </v-card>
                </div>
              </v-card-text>
            </v-card>

            <!-- Decision Makers -->
            <v-card v-if="getContent(selectedResult).decision_makers?.length" variant="outlined" class="mb-4" color="info">
              <v-card-title class="text-subtitle-1"><v-icon size="small" class="mr-2">mdi-account-group</v-icon>{{ $t('results.detail.decisionMakers') }} ({{ getContent(selectedResult).decision_makers.length }})</v-card-title>
              <v-card-text>
                <div class="d-flex flex-column ga-3">
                  <v-card
                    v-for="(dm, idx) in getContent(selectedResult).decision_makers"
                    :key="idx"
                    variant="tonal"
                    color="info"
                    class="pa-3"
                  >
                    <template v-if="typeof dm === 'string'">
                      <div class="d-flex align-start ga-2">
                        <v-avatar color="info" size="36">
                          <v-icon color="on-info" size="small">mdi-account</v-icon>
                        </v-avatar>
                        <div class="text-body-1 font-weight-medium align-self-center">{{ dm }}</div>
                      </div>
                    </template>
                    <template v-else>
                      <div class="d-flex align-start ga-2">
                        <v-avatar color="info" size="36">
                          <v-icon color="on-info" size="small">mdi-account</v-icon>
                        </v-avatar>
                        <div class="flex-grow-1">
                          <div class="text-body-1 font-weight-medium">{{ dm.name || dm.person }}</div>
                          <div v-if="dm.role || dm.position" class="text-body-2 text-medium-emphasis">{{ dm.role || dm.position }}</div>
                          <div class="d-flex flex-wrap ga-2 mt-2">
                            <v-chip v-if="dm.email || dm.contact" size="small" variant="outlined" @click.stop="copyToClipboard(dm.email || dm.contact)">
                              <v-icon start size="small">mdi-email</v-icon>
                              {{ dm.email || dm.contact }}
                            </v-chip>
                            <v-chip v-if="dm.phone || dm.telefon" size="small" variant="outlined">
                              <v-icon start size="small">mdi-phone</v-icon>
                              {{ dm.phone || dm.telefon }}
                            </v-chip>
                            <v-chip v-if="dm.sentiment" size="small" :color="getSentimentColor(dm.sentiment)">
                              {{ dm.sentiment }}
                            </v-chip>
                          </div>
                          <div v-if="dm.statement || dm.quote" class="mt-2 pa-2 rounded bg-surface-variant">
                            <v-icon size="small" class="mr-1">mdi-format-quote-open</v-icon>
                            <span class="text-body-2 font-italic">{{ dm.statement || dm.quote }}</span>
                          </div>
                          <div v-if="dm.source || dm.source_url" class="mt-2">
                            <v-chip
                              size="small"
                              variant="outlined"
                              :href="dm.source_url || dm.source"
                              :target="dm.source_url || dm.source?.startsWith('http') ? '_blank' : undefined"
                              :tag="dm.source_url || dm.source?.startsWith('http') ? 'a' : 'span'"
                            >
                              <v-icon start size="x-small">mdi-link</v-icon>
                              {{ dm.source_url ? t('results.detail.source') : dm.source }}
                            </v-chip>
                          </div>
                        </div>
                      </div>
                    </template>
                  </v-card>
                </div>
              </v-card-text>
            </v-card>

            <!-- Outreach Recommendation -->
            <v-card v-if="getContent(selectedResult).outreach_recommendation" variant="outlined" class="mb-4" color="info">
              <v-card-title class="text-subtitle-1"><v-icon size="small" class="mr-2">mdi-bullhorn</v-icon>{{ $t('results.detail.outreachRecommendation') }}</v-card-title>
              <v-card-text>
                <div v-if="getContent(selectedResult).outreach_recommendation.priority">
                  <strong>{{ $t('results.detail.priority') }}:</strong>
                  <v-chip :color="getPriorityColor(getContent(selectedResult).outreach_recommendation.priority)" size="small" class="ml-2">
                    {{ getContent(selectedResult).outreach_recommendation.priority }}
                  </v-chip>
                </div>
                <div v-if="getContent(selectedResult).outreach_recommendation.reason" class="mt-2">
                  <strong>{{ $t('results.detail.reason') }}:</strong> {{ getContent(selectedResult).outreach_recommendation.reason }}
                </div>
              </v-card-text>
            </v-card>
          </template>

          <!-- Raw JSON -->
          <v-expansion-panels class="mb-4">
            <v-expansion-panel>
              <v-expansion-panel-title><v-icon size="small" class="mr-2">mdi-code-json</v-icon>{{ $t('results.detail.rawData') }}</v-expansion-panel-title>
              <v-expansion-panel-text>
                <pre class="json-viewer pa-3 rounded">{{ JSON.stringify(getContent(selectedResult), null, 2) }}</pre>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>

          <!-- AI Metadata -->
          <v-card variant="outlined">
            <v-card-title class="text-subtitle-1"><v-icon size="small" class="mr-2">mdi-robot</v-icon>{{ $t('results.detail.aiMetadata') }}</v-card-title>
            <v-card-text>
              <v-row>
                <v-col cols="6"><div><strong>{{ $t('results.columns.type') }}:</strong> {{ selectedResult.extraction_type }}</div></v-col>
                <v-col cols="6"><div><strong>{{ $t('results.detail.model') }}:</strong> {{ selectedResult.ai_model_used || '-' }}</div></v-col>
                <v-col cols="6"><div><strong>{{ $t('results.columns.created') }}:</strong> {{ formatDate(selectedResult.created_at) }}</div></v-col>
                <v-col cols="6"><div><strong>{{ $t('results.detail.tokens') }}:</strong> {{ selectedResult.tokens_used || '-' }}</div></v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-card-text>
        <v-divider />
        <v-card-actions>
          <v-btn color="primary" variant="outlined" prepend-icon="mdi-code-json" @click="exportJson(selectedResult)">{{ $t('results.actions.exportJson') }}</v-btn>
          <v-spacer />
          <v-btn v-if="!selectedResult.human_verified" variant="tonal" color="success" prepend-icon="mdi-check" @click="verifyResult(selectedResult); detailsDialog = false">{{ $t('results.actions.verify') }}</v-btn>
          <v-btn variant="tonal" @click="detailsDialog = false">{{ $t('common.close') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { dataApi, adminApi } from '@/services/api'
import { format } from 'date-fns'
import { de } from 'date-fns/locale'
import { useSnackbar } from '@/composables/useSnackbar'
import { useDebounce, DEBOUNCE_DELAYS } from '@/composables/useDebounce'
import PageHeader from '@/components/common/PageHeader.vue'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger('ResultsView')

const { t } = useI18n()

const route = useRoute()
const { showSuccess, showError } = useSnackbar()

// Loading state
const loading = ref(true)
const initialLoad = ref(true)
const bulkVerifying = ref(false)

// Data
const results = ref<any[]>([])
const totalResults = ref(0)
const locations = ref<string[]>([])
const categories = ref<any[]>([])
const extractionTypes = ref<string[]>([])
const selectedResults = ref<string[]>([])

// Statistics
const stats = ref({
  total: 0,
  verified: 0,
  unverified: 0,
  avg_confidence: null as number | null,
  high_confidence_count: 0,
  low_confidence_count: 0,
})

// Filters
const searchQuery = ref('')
const locationFilter = ref<string | null>(null)
const extractionTypeFilter = ref<string | null>(null)
const categoryFilter = ref<string | null>(null)
const minConfidence = ref(0)
const verifiedFilter = ref<boolean | null>(null)
const dateFrom = ref<string | null>(null)
const dateTo = ref<string | null>(null)
const page = ref(1)
const perPage = ref(20)
const sortBy = ref<any[]>([{ key: 'created_at', order: 'desc' }])

// Dialog
const detailsDialog = ref(false)
const selectedResult = ref<any>(null)

// Default headers when no category-specific config is available
const getDefaultHeaders = () => [
  { title: t('results.columns.document'), key: 'document', sortable: false, width: '220px' },
  { title: t('results.columns.type'), key: 'extraction_type', width: '140px', sortable: true },
  { title: t('results.columns.confidence'), key: 'confidence_score', width: '110px', sortable: true },
  { title: t('results.columns.verified'), key: 'human_verified', width: '90px', sortable: true },
  { title: t('results.columns.created'), key: 'created_at', width: '100px', sortable: true },
  { title: t('results.columns.actions'), key: 'actions', sortable: false, align: 'end' as const },
]

// Dynamic headers - loaded from category's display_fields config (initialized with defaults)
const headers = ref<any[]>(getDefaultHeaders())
const entityReferenceColumns = ref<string[]>([])

// Load display config for the selected category
const loadDisplayConfig = async (categoryId: string | null) => {
  if (!categoryId) {
    // No category selected - use default headers
    headers.value = getDefaultHeaders()
    entityReferenceColumns.value = []
    return
  }

  try {
    const response = await dataApi.getDisplayConfig(categoryId)
    const config = response.data

    // Build headers from config
    const dynamicHeaders: any[] = []

    for (const col of config.columns || []) {
      const header: any = {
        title: col.label,
        key: col.key,
        sortable: col.sortable !== false, // Default to sortable
      }
      if (col.width) header.width = col.width
      if (col.key === 'actions') header.align = 'end'
      dynamicHeaders.push(header)
    }

    // Always ensure actions column is present
    if (!dynamicHeaders.find(h => h.key === 'actions')) {
      dynamicHeaders.push({
        title: t('results.columns.actions'),
        key: 'actions',
        sortable: false,
        align: 'end' as const,
      })
    }

    headers.value = dynamicHeaders
    entityReferenceColumns.value = config.entity_reference_columns || []

  } catch (error) {
    logger.error('Failed to load display config:', error)
    // Fallback to default headers
    headers.value = getDefaultHeaders()
    entityReferenceColumns.value = []
  }
}

const hasActiveFilters = computed(() =>
  searchQuery.value || locationFilter.value || extractionTypeFilter.value ||
  categoryFilter.value || minConfidence.value > 0 || verifiedFilter.value !== null ||
  dateFrom.value || dateTo.value
)

// Helpers
const getConfidenceColor = (score: number | null) => {
  if (!score) return 'grey'
  if (score >= 0.8) return 'success'
  if (score >= 0.6) return 'warning'
  return 'error'
}

const getSeverityColor = (severity: string) => {
  const colors: Record<string, string> = { hoch: 'error', mittel: 'warning', niedrig: 'info', high: 'error', medium: 'warning', low: 'info' }
  return colors[severity.toLowerCase()] || 'grey'
}

const getSeverityIcon = (severity: string) => {
  const s = severity.toLowerCase()
  if (s === 'hoch' || s === 'high') return 'mdi-alert'
  if (s === 'mittel' || s === 'medium') return 'mdi-alert-circle-outline'
  if (s === 'niedrig' || s === 'low') return 'mdi-information-outline'
  return 'mdi-minus'
}

const getSentimentColor = (sentiment: string) => {
  if (!sentiment) return 'grey'
  const s = sentiment.toLowerCase()
  if (s === 'positiv' || s === 'positive') return 'success'
  if (s === 'negativ' || s === 'negative') return 'error'
  if (s === 'neutral') return 'grey'
  return 'grey'
}

const copyToClipboard = (text: string) => {
  navigator.clipboard.writeText(text)
  showSuccess(t('results.messages.copiedToClipboard'))
}

const getPriorityColor = (priority: string) => {
  const colors: Record<string, string> = { hoch: 'error', mittel: 'warning', niedrig: 'info', high: 'error', medium: 'warning', low: 'info' }
  return colors[priority.toLowerCase()] || 'grey'
}

// Generic entity reference helpers
const getEntityReferencesByType = (item: any, entityType: string): any[] => {
  if (!item.entity_references || !Array.isArray(item.entity_references)) {
    return []
  }
  return item.entity_references.filter((ref: any) => ref.entity_type === entityType)
}

const filterByEntityReference = (_entityType: string, entityName: string) => {
  // Set filter to search for this entity (entityType reserved for future filtering)
  searchQuery.value = entityName
  page.value = 1
  loadData()
}

// Entity type display helpers (configurable via category in future)
const getEntityTypeColor = (entityType: string): string => {
  const colors: Record<string, string> = {
    'territorial-entity': 'primary',
    'person': 'info',
    'organization': 'secondary',
    'event': 'warning',
  }
  return colors[entityType] || 'grey'
}

const getEntityTypeIcon = (entityType: string): string => {
  const icons: Record<string, string> = {
    'territorial-entity': 'mdi-map-marker',
    'person': 'mdi-account',
    'organization': 'mdi-domain',
    'event': 'mdi-calendar',
  }
  return icons[entityType] || 'mdi-tag'
}

const getContent = (item: any) => {
  return item.final_content || item.extracted_content || {}
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return '-'
  return format(new Date(dateStr), 'dd.MM.yy HH:mm', { locale: de })
}

// Track last loaded category for display config
let lastLoadedCategoryId: string | null = null

// Data loading
const loadData = async () => {
  loading.value = true
  try {
    // Load display config if category changed
    if (categoryFilter.value !== lastLoadedCategoryId) {
      await loadDisplayConfig(categoryFilter.value)
      lastLoadedCategoryId = categoryFilter.value
    }

    const params: any = { page: page.value, per_page: perPage.value }
    if (searchQuery.value) params.search = searchQuery.value
    if (locationFilter.value) params.location_name = locationFilter.value
    if (extractionTypeFilter.value) params.extraction_type = extractionTypeFilter.value
    if (categoryFilter.value) params.category_id = categoryFilter.value
    if (minConfidence.value > 0) params.min_confidence = minConfidence.value / 100
    if (verifiedFilter.value !== null) params.human_verified = verifiedFilter.value
    if (dateFrom.value) params.created_from = dateFrom.value
    if (dateTo.value) params.created_to = dateTo.value
    if (sortBy.value.length > 0) {
      params.sort_by = sortBy.value[0].key
      params.sort_order = sortBy.value[0].order
    }

    const [dataRes, statsRes] = await Promise.all([
      dataApi.getExtractedData(params),
      dataApi.getExtractionStats({ category_id: categoryFilter.value }),
    ])

    // Data comes with entity_references from API
    results.value = dataRes.data.items
    totalResults.value = dataRes.data.total
    stats.value = statsRes.data

    // Extract unique extraction types from by_type stats
    if (statsRes.data.by_type) {
      extractionTypes.value = Object.keys(statsRes.data.by_type)
    }
  } catch (error) {
    logger.error('Failed to load data:', error)
    showError(t('results.messages.errorLoading'))
  } finally {
    loading.value = false
    initialLoad.value = false
  }
}

const loadFilters = async () => {
  try {
    const [locationsRes, categoriesRes] = await Promise.all([
      dataApi.getExtractionLocations(),
      adminApi.getCategories(),
    ])
    locations.value = locationsRes.data
    categories.value = categoriesRes.data.items || categoriesRes.data
  } catch (error) {
    logger.error('Failed to load filters:', error)
  }
}

// Debounce search - uses composable with automatic cleanup
const { debouncedFn: debouncedLoadData } = useDebounce(
  () => loadData(),
  { delay: DEBOUNCE_DELAYS.SEARCH }
)

const toggleVerifiedFilter = (value: boolean) => {
  verifiedFilter.value = verifiedFilter.value === value ? null : value
  page.value = 1
  loadData()
}

const onTableOptionsUpdate = (options: any) => {
  page.value = options.page
  perPage.value = options.itemsPerPage
  if (options.sortBy && options.sortBy.length > 0) {
    sortBy.value = options.sortBy
  }
  loadData()
}

const clearFilters = () => {
  searchQuery.value = ''
  locationFilter.value = null
  extractionTypeFilter.value = null
  categoryFilter.value = null
  minConfidence.value = 0
  verifiedFilter.value = null
  dateFrom.value = null
  dateTo.value = null
  page.value = 1
  loadData()
}


// Actions
const showDetails = (item: any) => {
  selectedResult.value = item
  detailsDialog.value = true
}

const verifyResult = async (item: any) => {
  try {
    await dataApi.verifyExtraction(item.id, { verified: true, verified_by: 'user' })
    showSuccess(t('results.messages.verified'))

    // Update the item locally instead of reloading the entire table
    const index = results.value.findIndex((r: any) => r.id === item.id)
    if (index !== -1) {
      results.value[index] = { ...results.value[index], human_verified: true }
    }

    // Also update stats
    stats.value.verified = (stats.value.verified || 0) + 1
    stats.value.unverified = Math.max(0, (stats.value.unverified || 0) - 1)
  } catch (error: any) {
    showError(error.response?.data?.detail || t('results.messages.errorVerifying'))
  }
}

const bulkVerify = async () => {
  bulkVerifying.value = true
  try {
    const verifiedIds = [...selectedResults.value]
    for (const id of verifiedIds) {
      await dataApi.verifyExtraction(id, { verified: true, verified_by: 'user' })
    }
    showSuccess(`${verifiedIds.length} ${t('results.messages.bulkVerified')}`)

    // Update items locally
    let verifiedCount = 0
    for (const id of verifiedIds) {
      const index = results.value.findIndex((r: any) => r.id === id)
      if (index !== -1 && !results.value[index].human_verified) {
        results.value[index] = { ...results.value[index], human_verified: true }
        verifiedCount++
      }
    }

    // Update stats
    stats.value.verified = (stats.value.verified || 0) + verifiedCount
    stats.value.unverified = Math.max(0, (stats.value.unverified || 0) - verifiedCount)

    selectedResults.value = []
  } catch (error: any) {
    showError(error.response?.data?.detail || t('results.messages.errorBulkVerifying'))
  } finally {
    bulkVerifying.value = false
  }
}

const exportJson = (item: any) => {
  const data = {
    id: item.id,
    document_title: item.document_title,
    document_url: item.document_url,
    source_name: item.source_name,
    extraction_type: item.extraction_type,
    confidence_score: item.confidence_score,
    human_verified: item.human_verified,
    created_at: item.created_at,
    content: item.final_content || item.extracted_content,
  }
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `extraction-${item.id}.json`
  a.click()
  URL.revokeObjectURL(url)
  showSuccess(t('results.messages.jsonExported'))
}

const exportCsv = () => {
  const csvHeaders = [
    t('results.columns.document'),
    t('results.detail.url'),
    t('results.columns.type'),
    t('results.columns.municipality'),
    t('results.columns.confidence'),
    t('results.columns.verified'),
    t('results.columns.created'),
    t('results.detail.summary')
  ]
  const csvRows = results.value.map(r => {
    const content = r.final_content || r.extracted_content || {}
    return [
      `"${(r.document_title || '').replace(/"/g, '""')}"`,
      `"${r.document_url || ''}"`,
      r.extraction_type,
      `"${content.municipality || ''}"`,
      r.confidence_score ? (r.confidence_score * 100).toFixed(0) + '%' : '',
      r.human_verified ? t('common.yes') : t('common.no'),
      r.created_at,
      `"${(content.summary || '').replace(/"/g, '""').substring(0, 200)}"`
    ]
  })

  const csv = [csvHeaders.join(','), ...csvRows.map(r => r.join(','))].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `ergebnisse-${format(new Date(), 'yyyy-MM-dd')}.csv`
  a.click()
  URL.revokeObjectURL(url)
  showSuccess(t('results.messages.csvExported'))
}

// Init with URL params
onMounted(async () => {
  // Check for document_id in query params
  if (route.query.document_id) {
    // Could filter by document_id if API supports it
  }
  // Check for verified filter from dashboard widget
  if (route.query.verified !== undefined) {
    verifiedFilter.value = route.query.verified === 'true'
  }
  await Promise.all([loadData(), loadFilters()])
})
</script>

<style scoped>
/* Generic entity reference cell styling */
.entity-ref-text {
  font-size: 0.8125rem;
  line-height: 1.3;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  word-break: break-word;
}

.entity-ref-text:hover {
  text-decoration: underline;
  color: rgb(var(--v-theme-info-darken-1));
}

.entity-references {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.json-viewer {
  overflow-x: auto;
  font-size: 0.75rem;
  background: rgb(var(--v-theme-surface-variant));
  max-height: 400px;
  white-space: pre-wrap;
}
</style>
