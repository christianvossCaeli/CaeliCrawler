<template>
  <v-dialog
    v-model="isOpen"
    max-width="1200"
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

          <!-- Search Options -->
          <v-row>
            <v-col cols="12" md="4">
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
            <v-col cols="12" md="4">
              <v-text-field
                v-model.number="maxResults"
                :label="$t('sources.aiDiscovery.maxResults')"
                type="number"
                variant="outlined"
                density="comfortable"
                :min="10"
                :max="200"
              ></v-text-field>
            </v-col>
            <v-col cols="12" md="4">
              <v-switch
                v-model="skipApiDiscovery"
                :label="$t('sources.aiDiscovery.skipApiDiscovery')"
                color="warning"
                density="comfortable"
                hide-details
                class="mt-2"
              ></v-switch>
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
            :type="hasResults ? 'success' : 'warning'"
            variant="tonal"
            class="mb-4"
          >
            <template v-slot:prepend>
              <v-icon>{{ hasResults ? 'mdi-check-circle' : 'mdi-alert' }}</v-icon>
            </template>
            <div class="d-flex align-center flex-wrap ga-2">
              <span>{{ resultSummary }}</span>
              <v-chip v-if="discoveryResult.from_template" size="small" color="info" variant="outlined">
                <v-icon start size="small">mdi-bookmark</v-icon>
                {{ $t('sources.aiDiscovery.fromTemplate') }}
              </v-chip>
              <v-chip v-if="discoveryResult.used_fallback" size="small" color="warning" variant="outlined">
                <v-icon start size="small">mdi-web</v-icon>
                {{ $t('sources.aiDiscovery.serpFallback') }}
              </v-chip>
            </div>
          </v-alert>

          <!-- Tabs for API vs Web Results -->
          <v-tabs v-model="resultsTab" class="mb-4" color="primary">
            <v-tab value="api" :disabled="!discoveryResult?.api_sources?.length">
              <v-icon start>mdi-api</v-icon>
              {{ $t('sources.aiDiscovery.apiSources') }}
              <v-chip size="x-small" class="ml-2" color="success" v-if="discoveryResult?.api_sources?.length">
                {{ discoveryResult.api_sources.length }}
              </v-chip>
            </v-tab>
            <v-tab value="web" :disabled="!discoveryResult?.web_sources?.length">
              <v-icon start>mdi-web</v-icon>
              {{ $t('sources.aiDiscovery.webSources') }}
              <v-chip size="x-small" class="ml-2" v-if="discoveryResult?.web_sources?.length">
                {{ discoveryResult.web_sources.length }}
              </v-chip>
            </v-tab>
            <v-tab value="suggestions">
              <v-icon start>mdi-lightbulb</v-icon>
              {{ $t('sources.aiDiscovery.apiSuggestions') }}
              <v-chip size="x-small" class="ml-2" v-if="discoveryResult?.api_suggestions?.length">
                {{ discoveryResult.api_suggestions.length }}
              </v-chip>
            </v-tab>
          </v-tabs>

          <v-window v-model="resultsTab">
            <!-- API Sources Tab -->
            <v-window-item value="api">
              <div v-if="discoveryResult?.api_sources?.length">
                <v-card
                  v-for="(source, index) in discoveryResult.api_sources"
                  :key="index"
                  variant="outlined"
                  class="mb-4"
                >
                  <v-card-title class="d-flex align-center">
                    <v-icon color="success" class="mr-2">mdi-api</v-icon>
                    {{ source.api_name }}
                    <v-chip size="small" color="primary" class="ml-2">{{ source.api_type }}</v-chip>
                    <v-spacer />
                    <v-chip color="success" size="small">
                      {{ source.item_count }} {{ $t('sources.aiDiscovery.itemsFound') }}
                    </v-chip>
                  </v-card-title>
                  <v-card-subtitle>{{ source.api_url }}</v-card-subtitle>
                  <v-card-text>
                    <!-- Tags -->
                    <div class="mb-3">
                      <v-chip
                        v-for="tag in source.tags"
                        :key="tag"
                        size="small"
                        variant="outlined"
                        class="mr-1 mb-1"
                      >
                        {{ tag }}
                      </v-chip>
                    </div>

                    <!-- Sample Data Preview -->
                    <v-expansion-panels variant="accordion">
                      <v-expansion-panel>
                        <v-expansion-panel-title>
                          <v-icon start size="small">mdi-table</v-icon>
                          {{ $t('sources.aiDiscovery.sampleData') }} ({{ source.sample_items.length }})
                        </v-expansion-panel-title>
                        <v-expansion-panel-text>
                          <v-table density="compact" class="text-body-2">
                            <thead>
                              <tr>
                                <th v-for="key in Object.keys(source.sample_items[0] || {})" :key="key">
                                  {{ key }}
                                </th>
                              </tr>
                            </thead>
                            <tbody>
                              <tr v-for="(item, idx) in source.sample_items.slice(0, 5)" :key="idx">
                                <td v-for="key in Object.keys(item)" :key="key">
                                  {{ truncateValue(item[key]) }}
                                </td>
                              </tr>
                            </tbody>
                          </v-table>
                        </v-expansion-panel-text>
                      </v-expansion-panel>
                    </v-expansion-panels>
                  </v-card-text>
                  <v-card-actions>
                    <v-checkbox
                      v-model="selectedApiSources"
                      :value="index"
                      :label="$t('sources.aiDiscovery.selectForImport')"
                      density="compact"
                      hide-details
                    ></v-checkbox>
                    <v-spacer />
                    <v-btn
                      variant="outlined"
                      size="small"
                      color="primary"
                      @click="saveAsTemplate(source)"
                    >
                      <v-icon start size="small">mdi-bookmark-plus</v-icon>
                      {{ $t('sources.aiDiscovery.saveAsTemplate') }}
                    </v-btn>
                  </v-card-actions>
                </v-card>
              </div>
              <v-alert v-else type="info" variant="tonal">
                {{ $t('sources.aiDiscovery.noApiSources') }}
              </v-alert>
            </v-window-item>

            <!-- Web Sources Tab -->
            <v-window-item value="web">
              <v-card variant="outlined" v-if="discoveryResult?.web_sources?.length">
                <v-data-table
                  v-model="selectedWebSources"
                  :headers="tableHeaders"
                  :items="discoveryResult.web_sources"
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
                    >
                      {{ truncateUrl(item.base_url) }}
                      <v-icon size="x-small" class="ml-1">mdi-open-in-new</v-icon>
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
                    <v-chip :color="getConfidenceColor(item.confidence)" size="x-small">
                      {{ Math.round(item.confidence * 100) }}%
                    </v-chip>
                  </template>
                </v-data-table>
              </v-card>
              <v-alert v-else type="info" variant="tonal">
                {{ $t('sources.aiDiscovery.noWebSources') }}
              </v-alert>
            </v-window-item>

            <!-- API Suggestions Tab -->
            <v-window-item value="suggestions">
              <div v-if="discoveryResult?.api_validations?.length">
                <v-card
                  v-for="(validation, index) in discoveryResult.api_validations"
                  :key="index"
                  variant="outlined"
                  class="mb-3"
                  :color="validation.is_valid ? 'success' : 'error'"
                >
                  <v-card-title class="d-flex align-center text-body-1">
                    <v-icon :color="validation.is_valid ? 'success' : 'error'" class="mr-2">
                      {{ validation.is_valid ? 'mdi-check-circle' : 'mdi-close-circle' }}
                    </v-icon>
                    {{ validation.api_name }}
                    <v-spacer />
                    <v-chip
                      :color="validation.is_valid ? 'success' : 'error'"
                      size="small"
                      variant="outlined"
                    >
                      {{ validation.is_valid ? $t('sources.aiDiscovery.valid') : $t('sources.aiDiscovery.invalid') }}
                    </v-chip>
                  </v-card-title>
                  <v-card-text class="text-body-2">
                    <div v-if="validation.status_code" class="mb-1">
                      <strong>Status:</strong> {{ validation.status_code }}
                    </div>
                    <div v-if="validation.item_count" class="mb-1">
                      <strong>{{ $t('sources.aiDiscovery.itemCount') }}:</strong> {{ validation.item_count }}
                    </div>
                    <div v-if="validation.error_message" class="text-error">
                      <strong>{{ $t('common.error') }}:</strong> {{ validation.error_message }}
                    </div>
                  </v-card-text>
                </v-card>
              </div>
              <v-alert v-else type="info" variant="tonal">
                {{ $t('sources.aiDiscovery.noSuggestions') }}
              </v-alert>
            </v-window-item>
          </v-window>

          <!-- Category Selection -->
          <v-card variant="outlined" class="mt-4" v-if="hasResults">
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
    <v-dialog v-model="showTemplateDialog" max-width="500" persistent>
      <v-card>
        <v-card-title>
          <v-icon start>mdi-bookmark-plus</v-icon>
          {{ $t('sources.aiDiscovery.saveAsTemplate') }}
        </v-card-title>
        <v-card-text>
          <v-text-field
            v-model="templateForm.name"
            :label="$t('common.name')"
            variant="outlined"
            class="mb-3"
          ></v-text-field>
          <v-textarea
            v-model="templateForm.description"
            :label="$t('common.description')"
            variant="outlined"
            rows="2"
            class="mb-3"
          ></v-textarea>
          <v-combobox
            v-model="templateForm.keywords"
            :label="$t('sources.aiDiscovery.keywords')"
            variant="outlined"
            chips
            multiple
            closable-chips
            :hint="$t('sources.aiDiscovery.keywordsHint')"
          ></v-combobox>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showTemplateDialog = false">
            {{ $t('common.cancel') }}
          </v-btn>
          <v-btn
            color="primary"
            variant="elevated"
            :loading="isSavingTemplate"
            :disabled="!templateForm.name"
            @click="confirmSaveTemplate"
          >
            {{ $t('common.save') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { adminApi } from '@/services/api'

// ============================================================================
// TypeScript Interfaces
// ============================================================================

interface DiscoverySource {
  name: string
  base_url: string
  source_type: string
  tags: string[]
  metadata: Record<string, unknown>
  confidence: number
}

interface APISuggestion {
  api_name: string
  base_url: string
  endpoint: string
  description: string
  api_type: string
  auth_required: boolean
  confidence: number
  documentation_url?: string
}

interface APIValidation {
  api_name: string
  is_valid: boolean
  status_code?: number
  item_count?: number
  error_message?: string
  field_mapping: Record<string, string>
}

interface ValidatedAPISource {
  api_name: string
  api_url: string
  api_type: string
  item_count: number
  sample_items: Record<string, any>[]
  tags: string[]
  field_mapping: Record<string, string>
}

interface DiscoveryResultV2 {
  api_sources: ValidatedAPISource[]
  web_sources: DiscoverySource[]
  api_suggestions: APISuggestion[]
  api_validations: APIValidation[]
  stats: Record<string, number>
  warnings: string[]
  used_fallback: boolean
  from_template: boolean
}

interface DiscoveryExample {
  prompt: string
  description?: string
  expected_tags?: string[]
}

interface Category {
  id: string
  name: string
}

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
const skipApiDiscovery = ref(false)
const isSearching = ref(false)
const isImporting = ref(false)
const discoveryResult = ref<DiscoveryResultV2 | null>(null)
const selectedApiSources = ref<number[]>([])
const selectedWebSources = ref<string[]>([])
const categoryIds = ref<string[]>([])
const examples = ref<DiscoveryExample[]>([])
const errorMessage = ref('')
const resultsTab = ref('api')

// Cleanup state
let isMounted = true
let closeTimeoutId: ReturnType<typeof setTimeout> | null = null

// Template dialog
const showTemplateDialog = ref(false)
const isSavingTemplate = ref(false)
const templateForm = ref({
  name: '',
  description: '',
  keywords: [] as string[],
  source: null as ValidatedAPISource | null,
})

const searchDepthOptions = [
  { value: 'quick', title: t('sources.aiDiscovery.quick'), icon: 'mdi-speedometer', color: 'success' },
  { value: 'standard', title: t('sources.aiDiscovery.standard'), icon: 'mdi-speedometer-medium', color: 'primary' },
  { value: 'deep', title: t('sources.aiDiscovery.deep'), icon: 'mdi-speedometer-slow', color: 'warning' },
]

const searchSteps = ref<SearchStep[]>([
  { text: t('sources.aiDiscovery.checkingTemplates'), done: false, active: true },
  { text: t('sources.aiDiscovery.generatingApiSuggestions'), done: false, active: false },
  { text: t('sources.aiDiscovery.validatingApis'), done: false, active: false },
  { text: t('sources.aiDiscovery.extractingData'), done: false, active: false },
])

const tableHeaders = [
  { title: 'Name', key: 'name', sortable: true },
  { title: 'URL', key: 'base_url', sortable: true },
  { title: 'Tags', key: 'tags', sortable: false },
  { title: 'Confidence', key: 'confidence', sortable: true, width: '100px' },
]

// ============================================================================
// Computed
// ============================================================================

const hasResults = computed(() => {
  if (!discoveryResult.value) return false
  return discoveryResult.value.api_sources.length > 0 || discoveryResult.value.web_sources.length > 0
})

const resultSummary = computed(() => {
  if (!discoveryResult.value) return ''
  const apiCount = discoveryResult.value.api_sources.length
  const webCount = discoveryResult.value.web_sources.length
  if (apiCount > 0 && webCount > 0) {
    return t('sources.aiDiscovery.foundBoth', { api: apiCount, web: webCount })
  }
  if (apiCount > 0) {
    return t('sources.aiDiscovery.foundApis', { count: apiCount })
  }
  if (webCount > 0) {
    return t('sources.aiDiscovery.foundWeb', { count: webCount })
  }
  return t('sources.aiDiscovery.noResults')
})

const canImport = computed(() => {
  return selectedApiSources.value.length > 0 || selectedWebSources.value.length > 0
})

const importButtonText = computed(() => {
  const total = selectedApiSources.value.length + selectedWebSources.value.length
  return `${total} ${t('sources.aiDiscovery.importSources')}`
})

// ============================================================================
// Methods
// ============================================================================

const getErrorMessage = (error: unknown): string => {
  if (error && typeof error === 'object') {
    const err = error as { response?: { data?: { detail?: string; message?: string } }; message?: string }
    return err.response?.data?.detail || err.response?.data?.message || err.message || t('common.unknownError')
  }
  return t('common.unknownError')
}

const loadExamples = async () => {
  try {
    const response = await adminApi.getAiDiscoveryExamples()
    examples.value = response.data as DiscoveryExample[]
  } catch {
    examples.value = [
      { prompt: 'Alle deutschen Bundesliga-Fußballvereine' },
      { prompt: 'Gemeinden in Sachsen' },
      { prompt: 'Deutsche Universitäten' },
    ]
  }
}

const startDiscovery = async () => {
  // Prevent double-click race condition
  if (isSearching.value) return

  errorMessage.value = ''
  isSearching.value = true
  phase.value = 'searching'
  resetSearchSteps()

  try {
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

    // Pre-select all API sources
    selectedApiSources.value = discoveryResult.value.api_sources.map((_, i) => i)
    // Pre-select all web sources
    selectedWebSources.value = discoveryResult.value.web_sources.map((s) => s.base_url)

    // Set active tab based on results
    if (discoveryResult.value.api_sources.length > 0) {
      resultsTab.value = 'api'
    } else if (discoveryResult.value.web_sources.length > 0) {
      resultsTab.value = 'web'
    } else {
      resultsTab.value = 'suggestions'
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
  let totalImported = 0

  try {
    // Import API sources
    for (const index of selectedApiSources.value) {
      const source = discoveryResult.value.api_sources[index]
      const response = await adminApi.importApiData({
        api_name: source.api_name,
        api_url: source.api_url,
        field_mapping: source.field_mapping,
        items: source.sample_items, // In reality, would fetch full data
        category_ids: categoryIds.value,
        tags: source.tags,
        skip_duplicates: true,
      })
      totalImported += response.data.imported
    }

    // Import web sources
    if (selectedWebSources.value.length > 0) {
      const sourcesToImport = discoveryResult.value.web_sources.filter(
        (s) => selectedWebSources.value.includes(s.base_url)
      )
      const response = await adminApi.importDiscoveredSources({
        sources: sourcesToImport,
        category_ids: categoryIds.value,
        skip_duplicates: true,
      })
      totalImported += response.data.imported
    }

    emit('imported', totalImported)
    close()
  } catch (error: unknown) {
    console.error('Import failed:', error)
    errorMessage.value = getErrorMessage(error)
  } finally {
    isImporting.value = false
  }
}

const saveAsTemplate = (source: ValidatedAPISource) => {
  templateForm.value = {
    name: source.api_name,
    description: '',
    keywords: extractKeywords(prompt.value),
    source: source,
  }
  showTemplateDialog.value = true
}

const extractKeywords = (text: string): string[] => {
  // Extract meaningful words as keywords
  const words = text.toLowerCase()
    .replace(/[^\wäöüß\s]/g, '')
    .split(/\s+/)
    .filter(w => w.length > 2)
  return [...new Set(words)]
}

const confirmSaveTemplate = async () => {
  if (!templateForm.value.source) return

  isSavingTemplate.value = true
  try {
    const source = templateForm.value.source
    // Parse URL to get base_url and endpoint
    const url = new URL(source.api_url)
    const baseUrl = `${url.protocol}//${url.host}`
    const endpoint = url.pathname + url.search

    await adminApi.saveApiTemplateFromDiscovery({
      name: templateForm.value.name,
      description: templateForm.value.description,
      api_type: source.api_type as 'REST' | 'GRAPHQL' | 'SPARQL' | 'OPARL',
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
    console.error('Failed to save template:', error)
    errorMessage.value = getErrorMessage(error)
  } finally {
    isSavingTemplate.value = false
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

const truncateValue = (value: any): string => {
  if (value === null || value === undefined) return '-'
  const str = String(value)
  return str.length > 50 ? str.slice(0, 47) + '...' : str
}

const getConfidenceColor = (confidence: number) => {
  if (confidence >= 0.8) return 'success'
  if (confidence >= 0.6) return 'primary'
  if (confidence >= 0.4) return 'warning'
  return 'error'
}

const close = () => {
  // Stop any ongoing operations
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
  }, 300)
}

// Cleanup on component unmount
onUnmounted(() => {
  isMounted = false
  if (closeTimeoutId) {
    clearTimeout(closeTimeoutId)
    closeTimeoutId = null
  }
})

onMounted(() => {
  loadExamples()
})

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
