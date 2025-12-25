<template>
  <v-card class="mb-4" :color="results.success ? 'success' : 'error'" variant="tonal">
    <v-card-title>
      <v-icon left>{{ results.success ? 'mdi-check-circle' : 'mdi-alert-circle' }}</v-icon>
      {{ results.success ? t('smartQueryView.results.successfullyCreated') : t('common.error') }}
    </v-card-title>
    <v-card-text>
      <div class="text-body-1 mb-3">{{ results.message }}</div>

      <!-- Created Items -->
      <template v-if="(results.created_items?.length ?? 0) > 0">
        <div class="text-subtitle-2 mb-2">{{ t('smartQueryView.results.createdItems') }}</div>
        <v-list density="compact" class="bg-transparent">
          <v-list-item
            v-for="item in results.created_items"
            :key="item.id"
            :title="item.name || item.type"
            :subtitle="`${item.type}${item.entity_type ? ' (' + item.entity_type + ')' : ''}${item.slug ? ' [' + item.slug + ']' : ''} - ID: ${item.id.substring(0, 8)}...`"
          >
            <template v-slot:prepend>
              <v-icon :color="getItemTypeColor(item.type)">
                {{ getItemTypeIcon(item.type) }}
              </v-icon>
            </template>
          </v-list-item>
        </v-list>
      </template>

      <!-- Crawl Information -->
      <template v-if="results.sources_count || (results.crawl_jobs?.length ?? 0) > 0">
        <v-divider class="my-3" />
        <div class="text-subtitle-2 mb-2">
          <v-icon left size="small">mdi-spider-web</v-icon>
          {{ t('smartQueryView.results.crawlDetails') }}
        </div>
        <v-chip v-if="results.sources_count" class="mr-2 mb-2" color="info" size="small">
          {{ t('smartQueryView.results.dataSources', { count: results.sources_count }) }}
        </v-chip>
        <v-chip v-if="(results.crawl_jobs?.length ?? 0) > 0" class="mr-2 mb-2" color="success" size="small">
          {{ t('smartQueryView.results.jobsStarted', { count: results.crawl_jobs?.length ?? 0 }) }}
        </v-chip>
      </template>

      <!-- Linked Sources -->
      <template v-if="results.linked_sources_count">
        <v-divider class="my-3" />
        <div class="text-subtitle-2 mb-2">
          <v-icon left size="small">mdi-link-variant</v-icon>
          {{ t('smartQueryView.results.dataSourcesLink') }}
        </div>
        <v-chip color="primary" size="small">
          {{ t('smartQueryView.results.dataSourcesLinked', { count: results.linked_sources_count }) }}
        </v-chip>
      </template>

      <!-- AI Generation Steps -->
      <template v-if="(results.steps?.length ?? 0) > 0">
        <v-divider class="my-3" />
        <div class="text-subtitle-2 mb-2">
          <v-icon left size="small">mdi-robot</v-icon>
          {{ t('smartQueryView.results.aiGenerationSteps') }}
        </div>
        <v-timeline density="compact" side="end">
          <v-timeline-item
            v-for="(step, idx) in results.steps"
            :key="idx"
            :dot-color="step.success !== false ? 'success' : 'error'"
            size="x-small"
          >
            <div>
              <div class="d-flex align-center">
                <v-icon :color="step.success !== false ? 'success' : 'error'" size="small" class="mr-2">
                  {{ step.success !== false ? 'mdi-check' : 'mdi-close' }}
                </v-icon>
                <span class="text-body-2 font-weight-medium">{{ t('smartQueryView.results.step', { current: step.step, total: step.total }) }}</span>
              </div>
              <div class="text-caption text-medium-emphasis ml-6">{{ step.message }}</div>
              <div v-if="step.result" class="text-caption text-success ml-6">{{ step.result }}</div>
            </div>
          </v-timeline-item>
        </v-timeline>
      </template>

      <!-- AI-Generated Search Terms -->
      <template v-if="(results.search_terms?.length ?? 0) > 0">
        <v-divider class="my-3" />
        <div class="text-subtitle-2 mb-2">
          <v-icon left size="small">mdi-magnify</v-icon>
          {{ t('smartQueryView.results.aiSearchTerms') }}
        </div>
        <v-chip
          v-for="term in results.search_terms"
          :key="term"
          size="small"
          class="mr-1 mb-1"
          color="info"
          variant="outlined"
        >
          {{ term }}
        </v-chip>
      </template>

      <!-- AI-Generated URL Patterns -->
      <template v-if="(results.url_patterns?.include?.length ?? 0) > 0 || (results.url_patterns?.exclude?.length ?? 0) > 0">
        <v-divider class="my-3" />
        <div class="text-subtitle-2 mb-2">
          <v-icon left size="small">mdi-web</v-icon>
          {{ t('smartQueryView.results.urlPatternConfig') }}
        </div>
        <div v-if="results.url_patterns?.reasoning" class="text-caption text-medium-emphasis mb-3">
          {{ results.url_patterns.reasoning }}
        </div>
        <div v-if="(results.url_patterns?.include?.length ?? 0) > 0" class="mb-2">
          <div class="text-caption text-success mb-1">{{ t('smartQueryView.results.includePatterns') }}</div>
          <v-chip
            v-for="pattern in results.url_patterns?.include ?? []"
            :key="pattern"
            size="small"
            class="mr-1 mb-1"
            color="success"
            variant="tonal"
          >
            <code>{{ pattern }}</code>
          </v-chip>
        </div>
        <div v-if="(results.url_patterns?.exclude?.length ?? 0) > 0">
          <div class="text-caption text-error mb-1">{{ t('smartQueryView.results.excludePatterns') }}</div>
          <v-chip
            v-for="pattern in results.url_patterns?.exclude ?? []"
            :key="pattern"
            size="small"
            class="mr-1 mb-1"
            color="error"
            variant="tonal"
          >
            <code>{{ pattern }}</code>
          </v-chip>
        </div>
      </template>

      <!-- AI Extraction Prompt -->
      <template v-if="results.ai_extraction_prompt">
        <v-divider class="my-3" />
        <v-expansion-panels variant="accordion">
          <v-expansion-panel>
            <v-expansion-panel-title>
              <v-icon left size="small" class="mr-2">mdi-brain</v-icon>
              {{ t('smartQueryView.results.aiExtractionPrompt') }}
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <pre class="text-caption text-pre-wrap">{{ results.ai_extraction_prompt }}</pre>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </template>

      <!-- Combined Operation Results -->
      <template v-if="(results.operation_results?.length ?? 0) > 0">
        <v-divider class="my-3" />
        <div class="text-subtitle-2 mb-2">
          <v-icon left size="small">mdi-format-list-checks</v-icon>
          {{ t('smartQueryView.results.executedOperations') }}
        </div>
        <v-list density="compact" class="bg-transparent">
          <v-list-item
            v-for="(opResult, idx) in results.operation_results"
            :key="idx"
            :title="opResult.operation"
            :subtitle="opResult.message"
          >
            <template v-slot:prepend>
              <v-icon :color="opResult.success ? 'success' : 'error'" size="small">
                {{ opResult.success ? 'mdi-check' : 'mdi-close' }}
              </v-icon>
            </template>
          </v-list-item>
        </v-list>
      </template>

      <!-- Interpretation -->
      <v-expansion-panels variant="accordion" class="mt-3">
        <v-expansion-panel :title="t('smartQueryView.results.interpretation')">
          <v-expansion-panel-text>
            <pre class="text-caption">{{ JSON.stringify(results.interpretation, null, 2) }}</pre>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-card-text>
    <v-card-actions>
      <v-btn variant="tonal" @click="$emit('newCommand')">{{ t('smartQueryView.results.newCommand') }}</v-btn>
      <v-spacer />
      <v-btn
        v-if="showBackToAssistant"
        color="primary"
        variant="elevated"
        @click="$emit('backToAssistant')"
      >
        <v-icon start>mdi-arrow-left</v-icon>
        {{ t('smartQueryView.results.backToAssistant') }}
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

interface WriteResults {
  success: boolean
  message?: string
  created_items?: Array<{
    id: string
    name?: string
    type: string
    entity_type?: string
    slug?: string
  }>
  sources_count?: number
  crawl_jobs?: Array<{ id: string }>
  linked_sources_count?: number
  steps?: Array<{
    step: number
    total: number
    success?: boolean
    message: string
    result?: string
  }>
  search_terms?: string[]
  url_patterns?: {
    include?: string[]
    exclude?: string[]
    reasoning?: string
  }
  ai_extraction_prompt?: string
  operation_results?: Array<{
    operation: string
    success: boolean
    message: string
  }>
  interpretation?: Record<string, unknown>
}

defineProps<{
  results: WriteResults
  showBackToAssistant: boolean
}>()

defineEmits<{
  newCommand: []
  backToAssistant: []
}>()

const { t } = useI18n()

// Helper functions
function getItemTypeIcon(type: string): string {
  const icons: Record<string, string> = {
    entity: 'mdi-shape',
    entity_type: 'mdi-folder-multiple',
    facet_value: 'mdi-tag',
    relation: 'mdi-arrow-right-bold',
    category: 'mdi-shape-outline',
    crawl_job: 'mdi-spider-web',
  }
  return icons[type] || 'mdi-check'
}

function getItemTypeColor(type: string): string {
  const colors: Record<string, string> = {
    entity: 'primary',
    entity_type: 'purple',
    facet_value: 'secondary',
    relation: 'info',
    category: 'orange',
    crawl_job: 'success',
  }
  return colors[type] || 'grey'
}
</script>

<style scoped>
.text-pre-wrap {
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
