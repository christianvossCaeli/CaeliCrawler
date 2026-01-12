<template>
  <v-dialog v-model="modelValue" :max-width="DIALOG_SIZES.XXL" scrollable>
    <v-card v-if="result">
      <!-- Header -->
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2">mdi-brain</v-icon>
        {{ $t('results.detail.title') }}
        <v-spacer />
        <v-chip v-if="result.is_rejected" color="error" variant="outlined" class="mr-2">
          <v-icon start size="small">mdi-close-circle</v-icon>
          {{ $t('results.status.rejected') }}
        </v-chip>
        <v-chip :color="getConfidenceColor(result.confidence_score)" class="mr-2">
          {{ formatConfidence(result.confidence_score) }}
        </v-chip>
        <v-chip v-if="result.human_verified" color="success">
          <v-icon size="small" class="mr-1">mdi-check</v-icon>
          {{ $t('results.columns.verified') }}
        </v-chip>
      </v-card-title>

      <!-- Tabs -->
      <v-tabs v-model="activeTab" color="primary" class="border-b">
        <v-tab value="content">
          <v-icon start size="small">mdi-file-document-outline</v-icon>
          {{ $t('results.detail.contentTab') }}
        </v-tab>
        <v-tab value="facets">
          <v-icon start size="small">mdi-tag-multiple</v-icon>
          {{ $t('results.detail.facetsTab') }}
        </v-tab>
        <v-tab value="metadata">
          <v-icon start size="small">mdi-robot</v-icon>
          {{ $t('results.detail.metadataTab') }}
        </v-tab>
      </v-tabs>

      <!-- Tab Content -->
      <v-tabs-window v-model="activeTab">
        <!-- Content Tab -->
        <v-tabs-window-item value="content">
          <v-card-text class="pa-4 dialog-content">
            <!-- Document Info Section -->
            <v-card variant="outlined" class="mb-4">
              <v-card-title class="text-subtitle-1 d-flex align-center">
            <v-icon size="small" class="mr-2">mdi-file-document</v-icon>
            {{ $t('results.detail.sourceDocument') }}
            <v-spacer />
            <v-btn
              size="small"
              variant="tonal"
              color="primary"
              :to="`/documents?search=${encodeURIComponent(result.document_title || '')}`"
            >
              <v-icon size="small" class="mr-1">mdi-open-in-new</v-icon>
              {{ $t('results.detail.goToDocument') }}
            </v-btn>
          </v-card-title>
          <v-card-text>
            <div>
              <strong>{{ $t('results.detail.title') }}:</strong>
              {{ result.document_title || $t('results.detail.noTitle') }}
            </div>
            <div v-if="result.document_url">
              <strong>{{ $t('results.detail.url') }}:</strong>
              <a :href="result.document_url" target="_blank" rel="noopener">
                {{ result.document_url }}
              </a>
            </div>
            <div>
              <strong>{{ $t('results.detail.source') }}:</strong>
              {{ result.source_name || '-' }}
            </div>
          </v-card-text>
        </v-card>

        <!-- Entity References Section -->
        <v-card
          variant="tonal"
          class="mb-4 entity-references-card"
          :color="hasEntityReferences ? 'primary' : 'grey'"
        >
          <v-card-title class="text-subtitle-1 d-flex align-center">
            <v-icon size="small" class="mr-2">mdi-domain</v-icon>
            {{ $t('results.detail.relevantEntities') }}
            <v-chip
              v-if="hasEntityReferences"
              size="x-small"
              class="ml-2"
              color="primary"
              variant="flat"
            >
              {{ result.entity_references?.length }}
            </v-chip>
          </v-card-title>
          <v-card-text>
            <template v-if="hasEntityReferences">
              <div class="d-flex flex-wrap ga-2">
                <v-chip
                  v-for="(entityRef, idx) in result.entity_references"
                  :key="idx"
                  :color="entityRef.entity_id ? getEntityTypeColor(entityRef.entity_type) : 'grey'"
                  size="large"
                  :variant="entityRef.entity_id ? 'elevated' : 'outlined'"
                  :to="entityRef.entity_id ? `/entity/${entityRef.entity_id}` : undefined"
                  :class="[
                    'entity-chip',
                    { 'entity-chip--clickable': entityRef.entity_id },
                    { 'entity-chip--unlinked': !entityRef.entity_id },
                  ]"
                >
                  <v-icon start size="small">{{ getEntityTypeIcon(entityRef.entity_type) }}</v-icon>
                  <span class="font-weight-medium">{{ entityRef.entity_name }}</span>

                  <v-chip
                    v-if="entityRef.role === 'primary'"
                    size="x-small"
                    class="ml-1"
                    color="warning"
                    variant="flat"
                  >
                    {{ $t('results.detail.primary') }}
                  </v-chip>

                  <v-icon
                    v-if="entityRef.entity_id"
                    end
                    size="x-small"
                    class="ml-1"
                  >
                    mdi-open-in-new
                  </v-icon>
                  <v-icon
                    v-else
                    end
                    size="x-small"
                    class="ml-1"
                    color="warning"
                  >
                    mdi-link-off
                  </v-icon>

                  <v-tooltip activator="parent" location="top">
                    <div>
                      <strong>{{ $t('results.detail.entityType') }}:</strong>
                      {{ entityRef.entity_type }}
                    </div>
                    <div>
                      <strong>{{ $t('results.detail.role') }}:</strong>
                      {{ entityRef.role }}
                    </div>
                    <div>
                      <strong>{{ $t('results.detail.confidence') }}:</strong>
                      {{ Math.round((entityRef.confidence ?? 0) * 100) }}%
                    </div>
                    <div v-if="entityRef.entity_id" class="text-info">
                      {{ $t('results.detail.clickToView') }}
                    </div>
                    <div v-else class="text-warning">
                      {{ $t('results.detail.notLinked') }}
                    </div>
                  </v-tooltip>
                </v-chip>
              </div>
            </template>
            <template v-else>
              <div class="text-medium-emphasis d-flex align-center">
                <v-icon size="small" class="mr-2">mdi-information-outline</v-icon>
                {{ $t('results.detail.noEntityReferences') }}
              </div>
            </template>
          </v-card-text>
        </v-card>

        <!-- Extracted Content Section -->
        <template v-if="content">
          <!-- Relevance -->
          <v-row class="mb-4">
            <v-col cols="12">
              <v-card variant="outlined" height="100%">
                <v-card-title class="text-subtitle-1">
                  <v-icon size="small" class="mr-2">mdi-check-circle</v-icon>
                  {{ $t('results.detail.relevance') }}
                </v-card-title>
                <v-card-text>
                  <v-chip :color="content.is_relevant ? 'success' : 'grey'">
                    {{ content.is_relevant ? $t('results.detail.relevant') : $t('results.detail.notRelevant') }}
                  </v-chip>
                  <span v-if="content.relevanz" class="ml-2 text-caption">
                    {{ $t('results.detail.level') }}: {{ content.relevanz }}
                  </span>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>

          <!-- Summary -->
          <v-card v-if="content.summary" variant="outlined" class="mb-4">
            <v-card-title class="text-subtitle-1">
              <v-icon size="small" class="mr-2">mdi-text</v-icon>
              {{ $t('results.detail.summary') }}
            </v-card-title>
            <v-card-text>{{ content.summary }}</v-card-text>
          </v-card>

          <!-- FacetType-based display -->
          <template v-if="facetTypes.length > 0">
            <GenericFacetCard
              v-for="facetType in facetTypes"
              :key="facetType.slug"
              :facet-type="facetType"
              :values="getValuesForFacetType(content, facetType)"
            />
          </template>

          <!-- Dynamic Fields Fallback -->
          <template v-else>
            <DynamicContentCard
              v-for="field in dynamicFields"
              :key="field.key"
              :field="field"
            />
          </template>

          <!-- Outreach Recommendation -->
          <v-card
            v-if="content.outreach_recommendation"
            variant="outlined"
            class="mb-4"
            color="info"
          >
            <v-card-title class="text-subtitle-1">
              <v-icon size="small" class="mr-2">mdi-bullhorn</v-icon>
              {{ $t('results.detail.outreachRecommendation') }}
            </v-card-title>
            <v-card-text>
              <div v-if="content.outreach_recommendation?.priority">
                <strong>{{ $t('results.detail.priority') }}:</strong>
                <v-chip
                  :color="getPriorityColor(content.outreach_recommendation?.priority ?? '')"
                  size="small"
                  class="ml-2"
                >
                  {{ content.outreach_recommendation?.priority }}
                </v-chip>
              </div>
              <div v-if="content.outreach_recommendation?.reason" class="mt-2">
                <strong>{{ $t('results.detail.reason') }}:</strong>
                {{ content.outreach_recommendation?.reason }}
              </div>
            </v-card-text>
          </v-card>
        </template>

          </v-card-text>
        </v-tabs-window-item>

        <!-- Facets Tab -->
        <v-tabs-window-item value="facets">
          <v-card-text class="pa-4 dialog-content">
            <ResultFacetsTab
              :extraction-id="result.id"
              :can-edit="canVerify"
            />
          </v-card-text>
        </v-tabs-window-item>

        <!-- Metadata Tab -->
        <v-tabs-window-item value="metadata">
          <v-card-text class="pa-4 dialog-content">
            <!-- AI Metadata Section -->
            <v-card variant="outlined" class="mb-4">
              <v-card-title class="text-subtitle-1">
                <v-icon size="small" class="mr-2">mdi-robot</v-icon>
                {{ $t('results.detail.aiMetadata') }}
              </v-card-title>
              <v-card-text>
                <v-row>
                  <v-col cols="6">
                    <div>
                      <strong>{{ $t('results.columns.type') }}:</strong>
                      {{ result.extraction_type }}
                    </div>
                  </v-col>
                  <v-col cols="6">
                    <div>
                      <strong>{{ $t('results.detail.model') }}:</strong>
                      {{ result.ai_model_used || '-' }}
                    </div>
                  </v-col>
                  <v-col cols="6">
                    <div>
                      <strong>{{ $t('results.columns.created') }}:</strong>
                      {{ formatDate(result.created_at) }}
                    </div>
                  </v-col>
                  <v-col cols="6">
                    <div>
                      <strong>{{ $t('results.detail.tokens') }}:</strong>
                      {{ result.tokens_used || '-' }}
                    </div>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>

            <!-- Raw JSON Section -->
            <v-expansion-panels>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon size="small" class="mr-2">mdi-code-json</v-icon>
                  {{ $t('results.detail.rawData') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <pre class="json-viewer pa-3 rounded">{{ JSON.stringify(content, null, 2) }}</pre>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </v-card-text>
        </v-tabs-window-item>
      </v-tabs-window>

      <v-divider />

      <!-- Actions -->
      <v-card-actions>
        <v-btn
          color="primary"
          variant="outlined"
          prepend-icon="mdi-code-json"
          @click="$emit('export-json', result)"
        >
          {{ $t('results.actions.exportJson') }}
        </v-btn>
        <v-spacer />
        <v-btn
          v-if="canVerify && !result.human_verified"
          variant="tonal"
          color="success"
          prepend-icon="mdi-check"
          @click="handleVerify"
        >
          {{ $t('results.actions.verify') }}
        </v-btn>
        <v-btn variant="tonal" @click="close">
          {{ $t('common.close') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
/**
 * ResultDetailDialog - Detailed view of an extraction result
 *
 * Shows document info, entity references, extracted content,
 * facet management, and AI metadata in a tabbed interface.
 */
import { computed, ref } from 'vue'
import { DIALOG_SIZES } from '@/config/ui'
import { GenericFacetCard } from '@/components/facets'
import DynamicContentCard from './DynamicContentCard.vue'
import ResultFacetsTab from './ResultFacetsTab.vue'
import {
  useResultsHelpers,
  type SearchResult,
  type ExtractedContent,
} from '@/composables/results'
import { useFacetTypeRenderer } from '@/composables/useFacetTypeRenderer'
import type { FacetType } from '@/types/entity'

const props = defineProps<{
  modelValue: boolean
  result: SearchResult | null
  canVerify: boolean
  facetTypes: FacetType[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'verify': [item: SearchResult]
  'export-json': [item: SearchResult]
}>()

const {
  getConfidenceColor,
  formatConfidence,
  formatDate,
  getEntityTypeColor,
  getEntityTypeIcon,
  getPriorityColor,
  getContent,
  getDynamicContentFields,
} = useResultsHelpers()

const { getValuesForFacetType } = useFacetTypeRenderer()

// Two-way binding for dialog visibility
const modelValue = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

// Active tab state
const activeTab = ref('content')

// Extracted content
const content = computed<ExtractedContent>(() => {
  if (!props.result) return {}
  return getContent(props.result)
})

// Entity references
const hasEntityReferences = computed(() => {
  return (props.result?.entity_references?.length ?? 0) > 0
})

// Dynamic content fields
const dynamicFields = computed(() => {
  return getDynamicContentFields(content.value)
})

function close(): void {
  emit('update:modelValue', false)
}

function handleVerify(): void {
  if (props.result) {
    emit('verify', props.result)
    close()
  }
}
</script>

<style scoped>
.dialog-content {
  max-height: 70vh;
  overflow-y: auto;
}

.entity-references-card {
  border-left: 4px solid rgb(var(--v-theme-primary));
}

.entity-chip {
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.entity-chip--clickable {
  cursor: pointer;
}

.entity-chip--clickable:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.entity-chip--unlinked {
  opacity: 0.75;
  border-style: dashed;
}

.json-viewer {
  overflow-x: auto;
  font-size: 0.75rem;
  max-height: 400px;
  white-space: pre-wrap;
  font-family: 'Fira Code', 'Consolas', 'Monaco', monospace;
  background-color: #1a2f2e;
  color: #b8d4ce;
  border: 1px solid #2a4544;
  border-radius: 8px;
}

:deep(.v-theme--caeliLight) .json-viewer {
  background-color: #f5f5f5;
  color: #333;
  border-color: #e0e0e0;
}
</style>
