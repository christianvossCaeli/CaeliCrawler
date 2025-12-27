<template>
  <div>
    <!-- Skeleton Loader for initial load -->
    <ResultsSkeleton v-if="loading && initialLoad" />

    <!-- Main Content -->
    <template v-else>
    <PageHeader
      :title="$t('results.title')"
      :subtitle="$t('results.subtitle')"
      icon="mdi-chart-box"
    >
      <template #actions>
        <!-- Bulk Actions -->
        <v-btn
          v-if="canVerify && selectedResults.length > 0"
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
          class="cursor-pointer"
          @click="toggleVerifiedFilter(true)"
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
              @keyup.enter="loadData"
            />
          </v-col>
          <v-col v-if="showLocationFilter" cols="6" md="2">
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
              <template #thumb-label="{ modelValue }">{{ modelValue }}%</template>
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
        :show-select="canVerify"
        item-value="id"
        @update:options="onTableOptionsUpdate"
      >
        <template #item.document="{ item }">
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

        <template #item.extraction_type="{ item }">
          <v-chip size="small" color="primary" variant="tonal">{{ item.raw?.extraction_type || item.extraction_type }}</v-chip>
        </template>

        <!-- Dynamic Entity Reference Columns -->
        <template
          v-for="entityType in entityReferenceColumns"
          :key="`entity-${entityType}`"
          #[`item.entity_references.${entityType}`]="{ item }"
        >
          <div class="entity-references">
            <template v-for="(entityRef, idx) in getEntityReferencesByType(item.raw || item, entityType)" :key="idx">
              <div
                class="entity-ref-text cursor-pointer text-info"
                :title="entityRef.entity_name"
                @click="filterByEntityReference(entityType, entityRef.entity_name)"
              >
                {{ entityRef.entity_name }}
              </div>
            </template>
            <span v-if="!getEntityReferencesByType(item.raw || item, entityType).length" class="text-medium-emphasis">-</span>
          </div>
        </template>

        <template #item.confidence_score="{ item }">
          <v-chip :color="getConfidenceColor(item.raw?.confidence_score ?? item.confidence_score)" size="small">
            {{ (item.raw?.confidence_score ?? item.confidence_score) != null ? (((item.raw?.confidence_score ?? item.confidence_score) as number) * 100).toFixed(0) + '%' : '-' }}
          </v-chip>
        </template>

        <template #item.human_verified="{ item }">
          <v-icon v-if="item.raw?.human_verified ?? item.human_verified" color="success" size="small">mdi-check-circle</v-icon>
          <v-icon v-else color="grey" size="small">mdi-circle-outline</v-icon>
        </template>

        <template #item.created_at="{ item }">
          <div class="text-caption">{{ formatDate(item.raw?.created_at || item.created_at) }}</div>
        </template>

        <template #item.actions="{ item }">
          <div class="table-actions d-flex justify-end ga-1">
            <v-btn icon="mdi-eye" size="small" variant="tonal" :title="$t('common.details')" :aria-label="$t('common.details')" @click="showDetails(item.raw || item)"></v-btn>
            <v-btn
              v-if="canVerify"
              :icon="(item.raw?.human_verified ?? item.human_verified) ? 'mdi-check-circle' : 'mdi-check'"
              size="small"
              variant="tonal"
              :color="(item.raw?.human_verified ?? item.human_verified) ? 'success' : 'grey'"
              :title="(item.raw?.human_verified ?? item.human_verified) ? $t('results.actions.verified') : $t('results.actions.verify')"
              :aria-label="(item.raw?.human_verified ?? item.human_verified) ? $t('results.actions.verified') : $t('results.actions.verify')"
              @click="verifyResult(item.raw || item)"
            ></v-btn>
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
                    v-for="(entityRef, idx) in selectedResult.entity_references"
                    :key="idx"
                    :color="getEntityTypeColor(entityRef.entity_type)"
                    size="small"
                    :to="entityRef.entity_id ? `/entity/${entityRef.entity_id}` : undefined"
                  >
                    <v-icon start size="x-small">{{ getEntityTypeIcon(entityRef.entity_type) }}</v-icon>
                    {{ entityRef.entity_name }}
                    <v-tooltip v-if="entityRef.role !== 'secondary'" activator="parent" location="top">
                      {{ entityRef.role }} ({{ Math.round((entityRef.confidence ?? 0) * 100) }}%)
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
              <v-card-title class="text-subtitle-1"><v-icon size="small" class="mr-2">mdi-alert-circle</v-icon>{{ $t('results.detail.painPoints') }} ({{ getContent(selectedResult).pain_points?.length ?? 0 }})</v-card-title>
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
              <v-card-title class="text-subtitle-1"><v-icon size="small" class="mr-2">mdi-lightbulb-on</v-icon>{{ $t('results.detail.positiveSignals') }} ({{ getContent(selectedResult).positive_signals?.length ?? 0 }})</v-card-title>
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
              <v-card-title class="text-subtitle-1"><v-icon size="small" class="mr-2">mdi-account-group</v-icon>{{ $t('results.detail.decisionMakers') }} ({{ getContent(selectedResult).decision_makers?.length ?? 0 }})</v-card-title>
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
                <div v-if="getContent(selectedResult).outreach_recommendation?.priority">
                  <strong>{{ $t('results.detail.priority') }}:</strong>
                  <v-chip :color="getPriorityColor(getContent(selectedResult).outreach_recommendation?.priority ?? '')" size="small" class="ml-2">
                    {{ getContent(selectedResult).outreach_recommendation?.priority }}
                  </v-chip>
                </div>
                <div v-if="getContent(selectedResult).outreach_recommendation?.reason" class="mt-2">
                  <strong>{{ $t('results.detail.reason') }}:</strong> {{ getContent(selectedResult).outreach_recommendation?.reason }}
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
    </template>
  </div>
</template>

<script setup lang="ts">
/**
 * ResultsView - Extracted Data Results
 *
 * Displays extracted data from documents with filtering, sorting, and export capabilities.
 * Uses useResultsView composable for all state and logic.
 */
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useResultsView } from '@/composables/useResultsView'
import PageHeader from '@/components/common/PageHeader.vue'
import ResultsSkeleton from '@/components/results/ResultsSkeleton.vue'

const { t } = useI18n()

// Initialize composable with all state and methods
const {
  // State
  loading,
  initialLoad,
  bulkVerifying,
  results,
  totalResults,
  locations,
  categories,
  extractionTypes,
  selectedResults,
  stats,

  // Filters
  searchQuery,
  locationFilter,
  extractionTypeFilter,
  categoryFilter,
  minConfidence,
  verifiedFilter,
  dateFrom,
  dateTo,

  // Pagination
  page,
  perPage,
  sortBy,

  // Dialog
  detailsDialog,
  selectedResult,

  // Headers
  headers,
  entityReferenceColumns,

  // Computed
  showLocationFilter,
  hasActiveFilters,
  canVerify,

  // Helper Functions
  getConfidenceColor,
  getSeverityColor,
  getSeverityIcon,
  getSentimentColor,
  getPriorityColor,
  getEntityTypeColor,
  getEntityTypeIcon,
  getContent,
  getEntityReferencesByType,
  formatDate,
  copyToClipboard,

  // Data Loading
  loadData,
  debouncedLoadData,

  // Filter Actions
  toggleVerifiedFilter,
  clearFilters,
  filterByEntityReference,
  onTableOptionsUpdate,

  // Result Actions
  showDetails,
  verifyResult,
  bulkVerify,

  // Export Actions
  exportJson,
  exportCsv,

  // Initialization
  initialize,
} = useResultsView()

// Initialize on mount
onMounted(() => initialize())
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
