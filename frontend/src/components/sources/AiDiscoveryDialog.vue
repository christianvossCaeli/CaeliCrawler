<template>
  <v-dialog
    v-model="isOpen"
    :max-width="DIALOG_SIZES.XL"
    persistent
    scrollable
    :aria-labelledby="'ai-discovery-dialog-title'"
    role="dialog"
  >
    <v-card>
      <!-- Header -->
      <v-card-title class="d-flex align-center pa-4 bg-primary">
        <v-avatar color="primary-darken-1" size="40" class="mr-3" aria-hidden="true">
          <v-icon color="on-primary">mdi-robot</v-icon>
        </v-avatar>
        <div>
          <div id="ai-discovery-dialog-title" class="text-h6">{{ $t('sources.aiDiscovery.title') }}</div>
          <div class="text-caption opacity-80">{{ $t('sources.aiDiscovery.subtitle') }}</div>
        </div>
        <v-spacer />
        <v-btn
          icon
          variant="text"
          :disabled="isSearching"
          :aria-label="$t('common.close')"
          @click="close"
        >
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text class="pa-6">
        <!-- Error Alert -->
        <v-alert
          v-if="errorMessage"
          type="error"
          variant="tonal"
          class="mb-4"
          closable
          role="alert"
          @click:close="errorMessage = ''"
        >
          {{ errorMessage }}
        </v-alert>

        <!-- Input Phase -->
        <AiDiscoveryInputPhase
          v-if="phase === 'input'"
          v-model:prompt="prompt"
          v-model:search-depth="searchDepth"
          v-model:max-results="maxResults"
          v-model:skip-api-discovery="skipApiDiscovery"
          :examples="examples"
          :min-results="AI_DISCOVERY.MAX_RESULTS_MIN"
          :max-results-limit="AI_DISCOVERY.MAX_RESULTS_MAX"
        />

        <!-- Searching Phase -->
        <AiDiscoverySearchingPhase
          v-if="phase === 'searching'"
          :steps="searchSteps"
        />

        <!-- Results Phase -->
        <template v-if="phase === 'results'">
          <!-- Results Summary -->
          <AiDiscoveryResultsSummary :result="discoveryResult" />

          <!-- Tabs for API vs Web Results -->
          <v-tabs v-model="resultsTab" class="mb-4" color="primary">
            <v-tab value="api" :disabled="!discoveryResult?.api_sources?.length">
              <v-icon start>mdi-api</v-icon>
              {{ $t('sources.aiDiscovery.apiSources') }}
              <v-chip v-if="discoveryResult?.api_sources?.length" size="x-small" class="ml-2" color="success">
                {{ discoveryResult.api_sources.length }}
              </v-chip>
            </v-tab>
            <v-tab value="web" :disabled="!discoveryResult?.web_sources?.length">
              <v-icon start>mdi-web</v-icon>
              {{ $t('sources.aiDiscovery.webSources') }}
              <v-chip v-if="discoveryResult?.web_sources?.length" size="x-small" class="ml-2">
                {{ discoveryResult.web_sources.length }}
              </v-chip>
            </v-tab>
            <v-tab value="suggestions">
              <v-icon start>mdi-lightbulb</v-icon>
              {{ $t('sources.aiDiscovery.apiSuggestions') }}
              <v-chip v-if="discoveryResult?.api_validations?.length" size="x-small" class="ml-2">
                {{ discoveryResult.api_validations.length }}
              </v-chip>
            </v-tab>
          </v-tabs>

          <v-window v-model="resultsTab">
            <!-- API Sources Tab -->
            <v-window-item value="api">
              <AiDiscoveryApiResults
                v-model:selected-indices="selectedApiSources"
                :sources="discoveryResult?.api_sources || []"
                @save-template="saveAsTemplate"
              />
            </v-window-item>

            <!-- Web Sources Tab -->
            <v-window-item value="web">
              <AiDiscoveryWebResults
                v-model:selected-urls="selectedWebSources"
                :sources="discoveryResult?.web_sources || []"
              />
            </v-window-item>

            <!-- API Validations Tab -->
            <v-window-item value="suggestions">
              <AiDiscoveryValidations
                :validations="discoveryResult?.api_validations || []"
              />
            </v-window-item>
          </v-window>

          <!-- Category Selection -->
          <v-card v-if="hasResults" variant="outlined" class="mt-4">
            <v-card-title class="text-subtitle-2 pb-2">
              <v-icon start size="small">mdi-folder-multiple</v-icon>
              {{ $t('sources.aiDiscovery.targetCategories') }}
            </v-card-title>
            <v-card-text>
              <v-select
                v-model="categoryIds"
                :items="categories"
                item-title="name"
                item-value="id"
                multiple
                chips
                closable-chips
                variant="outlined"
                density="comfortable"
                :placeholder="$t('sources.aiDiscovery.noCategory')"
              ></v-select>
            </v-card-text>
          </v-card>
        </template>
      </v-card-text>

      <v-divider />

      <!-- Footer Actions -->
      <v-card-actions class="pa-4">
        <v-btn variant="text" :disabled="isSearching" @click="close">
          {{ $t('common.cancel') }}
        </v-btn>
        <v-spacer />
        <template v-if="phase === 'input'">
          <v-btn
            color="primary"
            variant="elevated"
            :loading="isSearching"
            :disabled="!prompt.trim()"
            @click="startDiscovery"
          >
            <v-icon start>mdi-magnify</v-icon>
            {{ $t('sources.aiDiscovery.startSearch') }}
          </v-btn>
        </template>
        <template v-if="phase === 'results'">
          <v-btn variant="outlined" class="mr-2" @click="phase = 'input'">
            <v-icon start>mdi-arrow-left</v-icon>
            {{ $t('common.back') }}
          </v-btn>
          <v-btn
            color="primary"
            variant="elevated"
            :loading="isImporting"
            :disabled="!canImport"
            @click="importSources"
          >
            <v-icon start>mdi-import</v-icon>
            {{ importButtonText }}
          </v-btn>
        </template>
      </v-card-actions>
    </v-card>

    <!-- Save as Template Dialog -->
    <AiDiscoverySaveTemplateDialog
      v-model="showTemplateDialog"
      :form="templateForm"
      :saving="isSavingTemplate"
      @update:form="templateForm = $event"
      @confirm="confirmSaveTemplate"
    />
  </v-dialog>
</template>

<script setup lang="ts">
/**
 * AiDiscoveryDialog - AI-powered source discovery dialog
 *
 * Multi-phase dialog for discovering and importing data sources using AI.
 * Supports API discovery, web scraping suggestions, and template matching.
 *
 * Uses modular sub-components for each phase:
 * - AiDiscoveryInputPhase: Search input and options
 * - AiDiscoverySearchingPhase: Progress indicator
 * - AiDiscoveryResultsSummary: Results overview
 * - AiDiscoveryApiResults: API sources display
 * - AiDiscoveryWebResults: Web sources table
 * - AiDiscoveryValidations: API validation results
 * - AiDiscoverySaveTemplateDialog: Template save dialog
 */
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { adminApi } from '@/services/api'
import { useLogger } from '@/composables/useLogger'
import { AI_DISCOVERY, DIALOG_SIZES } from '@/config/sources'
import {
  AiDiscoveryInputPhase,
  AiDiscoverySearchingPhase,
  AiDiscoveryResultsSummary,
  AiDiscoveryApiResults,
  AiDiscoveryWebResults,
  AiDiscoveryValidations,
  AiDiscoverySaveTemplateDialog,
} from './ai-discovery'
import type {
  DiscoveryResultV2,
  DiscoveryExample,
  Category,
  SearchStep,
  ValidatedAPISource,
  TemplateFormData,
} from './ai-discovery/types'

// defineModel() for two-way binding (Vue 3.4+)
const isOpen = defineModel<boolean>({ default: false })

// ============================================================================
// Props & Emits
// ============================================================================

defineProps<{
  categories: Category[]
}>()

const emit = defineEmits<{
  (e: 'imported', count: number): void
}>()

const logger = useLogger('AiDiscoveryDialog')

const { t } = useI18n()

// ============================================================================
// State
// ============================================================================

// Phase management
const phase = ref<'input' | 'searching' | 'results'>('input')

// Input state
const prompt = ref('')
const searchDepth = ref<'quick' | 'standard' | 'deep'>('standard')
const maxResults = ref(AI_DISCOVERY.MAX_RESULTS_DEFAULT)
const skipApiDiscovery = ref(false)
const examples = ref<DiscoveryExample[]>([])

// Operation states
const isSearching = ref(false)
const isImporting = ref(false)
const errorMessage = ref('')

// Results state
const discoveryResult = ref<DiscoveryResultV2 | null>(null)
const selectedApiSources = ref<number[]>([])
const selectedWebSources = ref<string[]>([])
const categoryIds = ref<string[]>([])
const resultsTab = ref('api')

// Search progress
const currentStepIndex = ref(0)

// Template dialog
const showTemplateDialog = ref(false)
const isSavingTemplate = ref(false)
const templateForm = ref<TemplateFormData>({
  name: '',
  description: '',
  keywords: [],
  source: null,
})

// Cleanup
let isMounted = true
let closeTimeoutId: ReturnType<typeof setTimeout> | null = null

// ============================================================================
// Computed
// ============================================================================

/** Search steps with i18n reactivity */
const searchSteps = computed<SearchStep[]>(() => {
  const stepTexts = [
    t('sources.aiDiscovery.checkingTemplates'),
    t('sources.aiDiscovery.generatingApiSuggestions'),
    t('sources.aiDiscovery.validatingApis'),
    t('sources.aiDiscovery.extractingData'),
  ]
  return stepTexts.map((text, index) => ({
    text,
    done: index < currentStepIndex.value,
    active: index === currentStepIndex.value,
  }))
})

/** Whether results contain any sources */
const hasResults = computed(() => {
  if (!discoveryResult.value) return false
  return discoveryResult.value.api_sources.length > 0 ||
         discoveryResult.value.web_sources.length > 0
})

/** Whether import is possible */
const canImport = computed(() => {
  return selectedApiSources.value.length > 0 || selectedWebSources.value.length > 0
})

/** Import button text */
const importButtonText = computed(() => {
  const total = selectedApiSources.value.length + selectedWebSources.value.length
  return `${total} ${t('sources.aiDiscovery.importSources')}`
})

// ============================================================================
// Methods
// ============================================================================

/** Extract error message from various error types */
const getErrorMessage = (error: unknown): string => {
  if (error && typeof error === 'object') {
    const err = error as { response?: { data?: { detail?: string; message?: string } }; message?: string }
    return err.response?.data?.detail || err.response?.data?.message || err.message || t('common.unknownError')
  }
  return t('common.unknownError')
}

/** Load example prompts from API */
const loadExamples = async () => {
  try {
    const response = await adminApi.getAiDiscoveryExamples()
    examples.value = response.data as DiscoveryExample[]
  } catch {
    // Fallback examples
    examples.value = [
      { prompt: 'Alle deutschen Bundesliga-Fußballvereine' },
      { prompt: 'Gemeinden in Sachsen' },
      { prompt: 'Deutsche Universitäten' },
    ]
  }
}

/** Start the discovery process */
const startDiscovery = async () => {
  if (isSearching.value) return

  errorMessage.value = ''
  isSearching.value = true
  phase.value = 'searching'
  currentStepIndex.value = 0

  try {
    // Simulate progress steps
    await simulateStep(0, 500)
    await simulateStep(1, 800)
    await simulateStep(2, 1000)

    const response = await adminApi.discoverSourcesV2({
      prompt: prompt.value,
      max_results: maxResults.value,
      search_depth: searchDepth.value,
      skip_api_discovery: skipApiDiscovery.value,
    })

    await simulateStep(3, 500)
    discoveryResult.value = response.data as DiscoveryResultV2

    // Pre-select all sources
    selectedApiSources.value = discoveryResult.value.api_sources.map((_, i) => i)
    selectedWebSources.value = discoveryResult.value.web_sources.map((s) => s.base_url)

    // Set active tab based on results
    resultsTab.value = discoveryResult.value.api_sources.length > 0 ? 'api' :
                       discoveryResult.value.web_sources.length > 0 ? 'web' : 'suggestions'

    phase.value = 'results'
  } catch (error: unknown) {
    logger.error('Discovery failed', error)
    errorMessage.value = getErrorMessage(error)
    phase.value = 'input'
  } finally {
    isSearching.value = false
  }
}

/** Import selected sources */
const importSources = async () => {
  if (!discoveryResult.value) return

  errorMessage.value = ''
  isImporting.value = true
  let totalImported = 0

  try {
    // Import API sources
    const apiImportResults = await Promise.allSettled(
      selectedApiSources.value.map(async (index) => {
        const source = discoveryResult.value?.api_sources[index]
        if (!source) return { imported: 0 }

        const response = await adminApi.importApiData({
          api_name: source.api_name,
          api_url: source.api_url,
          field_mapping: source.field_mapping,
          items: source.sample_items,
          category_ids: categoryIds.value,
          tags: source.tags,
          skip_duplicates: true,
        })
        return response.data
      })
    )

    // Count successful API imports
    for (const result of apiImportResults) {
      if (result.status === 'fulfilled' && result.value?.imported) {
        totalImported += result.value.imported
      }
    }

    // Import web sources
    if (selectedWebSources.value.length > 0) {
      const sourcesToImport = discoveryResult.value.web_sources.filter(
        (s) => selectedWebSources.value.includes(s.base_url)
      )

      if (sourcesToImport.length > 0) {
        const response = await adminApi.importDiscoveredSources({
          sources: sourcesToImport,
          category_ids: categoryIds.value,
          skip_duplicates: true,
        })
        totalImported += response.data?.imported || 0
      }
    }

    emit('imported', totalImported)
    close()
  } catch (error: unknown) {
    logger.error('Import failed', error)
    errorMessage.value = getErrorMessage(error)
  } finally {
    isImporting.value = false
  }
}

/** Open template save dialog */
const saveAsTemplate = (source: ValidatedAPISource) => {
  templateForm.value = {
    name: source.api_name,
    description: '',
    keywords: extractKeywords(prompt.value),
    source: source,
  }
  showTemplateDialog.value = true
}

/** Extract keywords from text */
const extractKeywords = (text: string): string[] => {
  const words = text.toLowerCase()
    .replace(/[^\wäöüß\s]/g, '')
    .split(/\s+/)
    .filter(w => w.length > 2)
  return [...new Set(words)]
}

/** Confirm and save template */
const confirmSaveTemplate = async () => {
  if (!templateForm.value.source) return

  isSavingTemplate.value = true
  try {
    const source = templateForm.value.source
    const url = new URL(source.api_url)
    const baseUrl = `${url.protocol}//${url.host}`
    const endpoint = url.pathname + url.search

    await adminApi.saveApiFromDiscovery({
      name: templateForm.value.name,
      description: templateForm.value.description,
      api_type: source.api_type,
      base_url: baseUrl,
      endpoint: endpoint,
      field_mapping: source.field_mapping,
      keywords: templateForm.value.keywords,
      default_tags: source.tags,
      confidence: 0.9,
      validation_item_count: source.item_count,
    })

    showTemplateDialog.value = false
  } catch (error: unknown) {
    logger.error('Failed to save template', error)
    errorMessage.value = getErrorMessage(error)
  } finally {
    isSavingTemplate.value = false
  }
}

/** Simulate step progress */
const simulateStep = async (stepIndex: number, delay: number) => {
  await new Promise((resolve) => setTimeout(resolve, delay))
  currentStepIndex.value = stepIndex
}

/** Close dialog and reset state */
const close = () => {
  isSearching.value = false
  isOpen.value = false
  closeTimeoutId = setTimeout(() => {
    if (!isMounted) return
    phase.value = 'input'
    prompt.value = ''
    discoveryResult.value = null
    selectedApiSources.value = []
    selectedWebSources.value = []
    categoryIds.value = []
    errorMessage.value = ''
    resultsTab.value = 'api'
    currentStepIndex.value = 0
  }, 300)
}

// ============================================================================
// Lifecycle
// ============================================================================

onMounted(() => {
  loadExamples()
})

onUnmounted(() => {
  isMounted = false
  if (closeTimeoutId) {
    clearTimeout(closeTimeoutId)
    closeTimeoutId = null
  }
})

watch(isOpen, (newValue) => {
  if (newValue) {
    phase.value = 'input'
    loadExamples()
  }
})
</script>
