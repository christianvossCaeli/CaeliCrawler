<template>
  <v-dialog
    v-model="isOpen"
    max-width="1100"
    persistent
    scrollable
    :aria-labelledby="'ai-discovery-dialog-title'"
    role="dialog"
  >
    <v-card>
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
          @click="close"
          :disabled="isSearching"
          :aria-label="$t('common.close')"
          :title="$t('common.close')"
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
          @click:close="errorMessage = ''"
          role="alert"
        >
          {{ errorMessage }}
        </v-alert>

        <!-- Search Phase -->
        <template v-if="phase === 'input'">
          <!-- Prompt Input -->
          <v-textarea
            v-model="prompt"
            :label="$t('sources.aiDiscovery.prompt')"
            :placeholder="$t('sources.aiDiscovery.promptPlaceholder')"
            variant="outlined"
            rows="3"
            prepend-inner-icon="mdi-magnify"
            class="mb-4"
            auto-grow
          ></v-textarea>

          <!-- Examples -->
          <v-card variant="tonal" class="mb-4" color="info">
            <v-card-title class="text-subtitle-2 pb-2">
              <v-icon start size="small">mdi-lightbulb-outline</v-icon>
              {{ $t('sources.aiDiscovery.examples') }}
            </v-card-title>
            <v-card-text class="pt-0">
              <v-chip-group>
                <v-chip
                  v-for="example in examples"
                  :key="example.prompt"
                  size="small"
                  variant="outlined"
                  @click="prompt = example.prompt"
                >
                  {{ example.prompt }}
                </v-chip>
              </v-chip-group>
            </v-card-text>
          </v-card>

          <!-- Search Depth -->
          <v-row>
            <v-col cols="12" md="6">
              <v-select
                v-model="searchDepth"
                :items="searchDepthOptions"
                :label="$t('sources.aiDiscovery.searchDepth')"
                variant="outlined"
                density="comfortable"
              >
                <template v-slot:item="{ item, props }">
                  <v-list-item v-bind="props">
                    <template v-slot:prepend>
                      <v-icon :color="item.raw.color">{{ item.raw.icon }}</v-icon>
                    </template>
                  </v-list-item>
                </template>
              </v-select>
            </v-col>
            <v-col cols="12" md="6">
              <v-text-field
                v-model.number="maxResults"
                label="Max Results"
                type="number"
                variant="outlined"
                density="comfortable"
                :min="10"
                :max="200"
              ></v-text-field>
            </v-col>
          </v-row>
        </template>

        <!-- Searching Phase -->
        <template v-if="phase === 'searching'">
          <v-card variant="outlined" class="pa-6 text-center">
            <v-progress-circular
              indeterminate
              color="primary"
              size="64"
              class="mb-4"
            ></v-progress-circular>
            <div class="text-h6 mb-2">{{ $t('sources.aiDiscovery.searching') }}</div>
            <v-list density="compact" class="text-left mx-auto" style="max-width: 400px">
              <v-list-item v-for="(step, index) in searchSteps" :key="index">
                <template v-slot:prepend>
                  <v-icon
                    :color="step.done ? 'success' : (step.active ? 'primary' : 'grey')"
                    size="small"
                  >
                    {{ step.done ? 'mdi-check-circle' : (step.active ? 'mdi-loading mdi-spin' : 'mdi-circle-outline') }}
                  </v-icon>
                </template>
                <v-list-item-title :class="{ 'text-grey': !step.active && !step.done }">
                  {{ step.text }}
                </v-list-item-title>
              </v-list-item>
            </v-list>
          </v-card>
        </template>

        <!-- Results Phase -->
        <template v-if="phase === 'results'">
          <!-- Results Summary -->
          <v-alert
            v-if="discoveryResult"
            :type="discoveryResult.sources.length > 0 ? 'success' : 'warning'"
            variant="tonal"
            class="mb-4"
          >
            <template v-slot:prepend>
              <v-icon>{{ discoveryResult.sources.length > 0 ? 'mdi-check-circle' : 'mdi-alert' }}</v-icon>
            </template>
            {{ $t(discoveryResult.sources.length > 0 ? 'sources.aiDiscovery.discoverySuccess' : 'sources.aiDiscovery.noResults', { count: discoveryResult.sources.length }) }}
          </v-alert>

          <!-- Base Tags -->
          <div v-if="discoveryResult?.search_strategy?.base_tags?.length" class="mb-4">
            <div class="text-subtitle-2 mb-2">{{ $t('sources.aiDiscovery.baseTags') }}</div>
            <v-chip-group>
              <v-chip
                v-for="tag in discoveryResult.search_strategy.base_tags"
                :key="tag"
                size="small"
                color="primary"
              >
                {{ tag }}
              </v-chip>
            </v-chip-group>
          </div>

          <!-- Results Table -->
          <v-card variant="outlined" class="mb-4" v-if="discoveryResult?.sources?.length">
            <v-data-table
              v-model="selectedSources"
              :headers="tableHeaders"
              :items="discoveryResult.sources"
              item-value="base_url"
              show-select
              density="compact"
              :items-per-page="10"
            >
              <template v-slot:item.name="{ item }">
                <div class="font-weight-medium">{{ item.name }}</div>
              </template>
              <template v-slot:item.base_url="{ item }">
                <a
                  :href="item.base_url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-decoration-none"
                  :aria-label="`${$t('common.openInNewTab')}: ${item.name}`"
                >
                  {{ truncateUrl(item.base_url) }}
                  <v-icon size="x-small" class="ml-1" aria-hidden="true">mdi-open-in-new</v-icon>
                </a>
              </template>
              <template v-slot:item.tags="{ item }">
                <v-chip-group>
                  <v-chip
                    v-for="tag in item.tags.slice(0, 4)"
                    :key="tag"
                    size="x-small"
                    variant="outlined"
                  >
                    {{ tag }}
                  </v-chip>
                  <v-chip v-if="item.tags.length > 4" size="x-small" variant="text">
                    +{{ item.tags.length - 4 }}
                  </v-chip>
                </v-chip-group>
              </template>
              <template v-slot:item.confidence="{ item }">
                <v-chip
                  :color="getConfidenceColor(item.confidence)"
                  size="x-small"
                >
                  {{ Math.round(item.confidence * 100) }}%
                </v-chip>
              </template>
            </v-data-table>
          </v-card>

          <!-- Category Selection -->
          <v-card variant="outlined" v-if="discoveryResult?.sources?.length">
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

      <v-card-actions class="pa-4">
        <v-btn variant="text" @click="close" :disabled="isSearching">
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
          <v-btn variant="outlined" @click="phase = 'input'" class="mr-2">
            <v-icon start>mdi-arrow-left</v-icon>
            {{ $t('common.back') }}
          </v-btn>
          <v-btn
            color="primary"
            variant="elevated"
            :loading="isImporting"
            :disabled="selectedSources.length === 0"
            @click="importSources"
          >
            <v-icon start>mdi-import</v-icon>
            {{ selectedSources.length }} {{ $t('sources.aiDiscovery.importSources') }}
          </v-btn>
        </template>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { adminApi } from '@/services/api'

// ============================================================================
// TypeScript Interfaces
// ============================================================================

/** Discovered source from AI discovery */
interface DiscoverySource {
  name: string
  base_url: string
  source_type: string
  tags: string[]
  metadata: Record<string, unknown>
  confidence: number
}

/** Search strategy generated by AI */
interface SearchStrategy {
  search_queries: string[]
  expected_data_type: string
  preferred_sources: string[]
  entity_schema: Record<string, string>
  base_tags: string[]
}

/** Discovery statistics */
interface DiscoveryStats {
  pages_searched: number
  sources_extracted: number
  duplicates_removed: number
  sources_validated: number
}

/** Full discovery result from API */
interface DiscoveryResult {
  sources: DiscoverySource[]
  search_strategy: SearchStrategy | null
  stats: DiscoveryStats
  warnings: string[]
}

/** Example prompt */
interface DiscoveryExample {
  prompt: string
  description?: string
  expected_tags?: string[]
}

/** Category for import */
interface Category {
  id: string
  name: string
}

/** Search step for progress display */
interface SearchStep {
  text: string
  done: boolean
  active: boolean
}

// ============================================================================
// Props & Emits
// ============================================================================

const props = defineProps<{
  modelValue: boolean
  categories: Category[]
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'imported', count: number): void
}>()

const { t } = useI18n()

// ============================================================================
// State
// ============================================================================

const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const phase = ref<'input' | 'searching' | 'results'>('input')
const prompt = ref('')
const searchDepth = ref<'quick' | 'standard' | 'deep'>('standard')
const maxResults = ref(50)
const isSearching = ref(false)
const isImporting = ref(false)
const discoveryResult = ref<DiscoveryResult | null>(null)
const selectedSources = ref<string[]>([])
const categoryIds = ref<string[]>([])
const examples = ref<DiscoveryExample[]>([])
const errorMessage = ref('')

const searchDepthOptions = [
  { value: 'quick', title: t('sources.aiDiscovery.quick'), icon: 'mdi-speedometer', color: 'success' },
  { value: 'standard', title: t('sources.aiDiscovery.standard'), icon: 'mdi-speedometer-medium', color: 'primary' },
  { value: 'deep', title: t('sources.aiDiscovery.deep'), icon: 'mdi-speedometer-slow', color: 'warning' },
]

const searchSteps = ref<SearchStep[]>([
  { text: t('sources.aiDiscovery.strategyGenerated'), done: false, active: true },
  { text: t('sources.aiDiscovery.sourcesFound'), done: false, active: false },
  { text: t('sources.aiDiscovery.extractingData'), done: false, active: false },
  { text: t('sources.aiDiscovery.generatingTags'), done: false, active: false },
])

const tableHeaders = [
  { title: 'Name', key: 'name', sortable: true },
  { title: 'URL', key: 'base_url', sortable: true },
  { title: 'Tags', key: 'tags', sortable: false },
  { title: 'Confidence', key: 'confidence', sortable: true, width: '100px' },
]

// ============================================================================
// Methods
// ============================================================================

/**
 * Extract error message from API error response
 */
const getErrorMessage = (error: unknown): string => {
  if (error && typeof error === 'object') {
    const err = error as { response?: { data?: { detail?: string; message?: string } }; message?: string }
    return err.response?.data?.detail
      || err.response?.data?.message
      || err.message
      || t('common.unknownError')
  }
  return t('common.unknownError')
}

const loadExamples = async () => {
  try {
    const response = await adminApi.getAiDiscoveryExamples()
    examples.value = response.data as DiscoveryExample[]
  } catch (error) {
    console.error('Failed to load examples:', error)
    // Fallback examples
    examples.value = [
      { prompt: 'Alle deutschen Bundesliga-Fußballvereine' },
      { prompt: 'Gemeinden in Sachsen' },
      { prompt: 'Deutsche Universitäten' },
    ]
  }
}

const startDiscovery = async () => {
  errorMessage.value = ''
  isSearching.value = true
  phase.value = 'searching'
  resetSearchSteps()

  try {
    // Simulate step progress
    await simulateStep(0, 500)
    await simulateStep(1, 1000)
    await simulateStep(2, 1500)

    const response = await adminApi.discoverSources({
      prompt: prompt.value,
      max_results: maxResults.value,
      search_depth: searchDepth.value,
    })

    await simulateStep(3, 500)
    discoveryResult.value = response.data as DiscoveryResult

    // Pre-select all sources
    selectedSources.value = discoveryResult.value.sources.map((s) => s.base_url)

    // Show warnings if any
    if (discoveryResult.value.warnings.length > 0) {
      console.warn('Discovery warnings:', discoveryResult.value.warnings)
    }

    phase.value = 'results'
  } catch (error: unknown) {
    console.error('Discovery failed:', error)
    errorMessage.value = getErrorMessage(error)
    phase.value = 'input'
  } finally {
    isSearching.value = false
  }
}

const importSources = async () => {
  if (!discoveryResult.value) return

  errorMessage.value = ''
  isImporting.value = true

  try {
    const sourcesToImport = discoveryResult.value.sources.filter(
      (s: DiscoverySource) => selectedSources.value.includes(s.base_url)
    )

    const response = await adminApi.importDiscoveredSources({
      sources: sourcesToImport,
      category_ids: categoryIds.value,
      skip_duplicates: true,
    })

    emit('imported', response.data.imported)
    close()
  } catch (error: unknown) {
    console.error('Import failed:', error)
    errorMessage.value = getErrorMessage(error)
  } finally {
    isImporting.value = false
  }
}

const resetSearchSteps = () => {
  searchSteps.value.forEach((step, index) => {
    step.done = false
    step.active = index === 0
  })
}

const simulateStep = async (stepIndex: number, delay: number) => {
  await new Promise((resolve) => setTimeout(resolve, delay))
  if (stepIndex > 0) {
    searchSteps.value[stepIndex - 1].done = true
    searchSteps.value[stepIndex - 1].active = false
  }
  if (stepIndex < searchSteps.value.length) {
    searchSteps.value[stepIndex].active = true
  }
}

const truncateUrl = (url: string) => {
  try {
    const parsed = new URL(url)
    return parsed.hostname + (parsed.pathname !== '/' ? parsed.pathname.slice(0, 20) + '...' : '')
  } catch {
    return url.slice(0, 40) + '...'
  }
}

const getConfidenceColor = (confidence: number) => {
  if (confidence >= 0.8) return 'success'
  if (confidence >= 0.6) return 'primary'
  if (confidence >= 0.4) return 'warning'
  return 'error'
}

const close = () => {
  isOpen.value = false
  // Reset state after close animation
  setTimeout(() => {
    phase.value = 'input'
    prompt.value = ''
    discoveryResult.value = null
    selectedSources.value = []
    categoryIds.value = []
    errorMessage.value = ''
  }, 300)
}

// Load examples on mount
onMounted(() => {
  loadExamples()
})

// Reset when dialog opens
watch(isOpen, (newValue) => {
  if (newValue) {
    phase.value = 'input'
    loadExamples()
  }
})
</script>

<style scoped>
:deep(.v-data-table) {
  font-size: 0.875rem;
}
</style>
