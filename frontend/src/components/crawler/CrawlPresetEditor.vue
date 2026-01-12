<template>
  <v-dialog
    v-model="dialogVisible"
    :max-width="DIALOG_SIZES.ML"
    persistent
    aria-labelledby="preset-editor-title"
    @keydown="handleKeydown"
  >
    <v-card role="dialog" aria-modal="true">
      <v-card-title id="preset-editor-title" class="d-flex align-center">
        <v-icon class="mr-2" aria-hidden="true">mdi-content-save-cog</v-icon>
        {{ isEditing ? t('crawlPresets.edit') : t('crawlPresets.create') }}
      </v-card-title>

      <v-card-text>
        <!-- Collapsible Info Box -->
        <v-alert
          v-if="!editorInfoHidden"
          type="info"
          variant="tonal"
          density="compact"
          class="mb-4"
          closable
          @click:close="hideEditorInfo"
        >
          <template #title>
            {{ t('crawlPresets.info.editorTitle') }}
          </template>
          <div>{{ t('crawlPresets.info.editorDescription') }}</div>
          <div class="text-caption mt-2">{{ t('crawlPresets.info.editorDetails') }}</div>
        </v-alert>
        <v-btn
          v-else
          variant="text"
          size="x-small"
          color="info"
          class="mb-3"
          prepend-icon="mdi-information-outline"
          @click="showEditorInfo"
        >
          {{ t('crawlPresets.info.showInfo') }}
        </v-btn>
        <v-form ref="formRef" v-model="formValid">
          <!-- Basic Info -->
          <v-text-field
            v-model="formData.name"
            :label="t('crawlPresets.name')"
            :rules="[v => !!v || t('common.required')]"
            variant="outlined"
            density="comfortable"
            class="mb-3"
          />

          <v-textarea
            v-model="formData.description"
            :label="t('crawlPresets.description')"
            variant="outlined"
            density="comfortable"
            rows="2"
            class="mb-4"
          />

          <!-- Filter Configuration -->
          <div class="text-subtitle-2 mb-2">{{ t('crawlPresets.filters') }}</div>

          <!-- Category: Single-Select Dropdown (Required, first position) -->
          <v-autocomplete
            v-model="formData.filters.category_id"
            :label="t('crawlPresets.category') + ' *'"
            :items="categories"
            item-title="name"
            item-value="id"
            variant="outlined"
            density="compact"
            :loading="categoriesLoading"
            :rules="[v => !!v || t('crawlPresets.categoryRequired')]"
            class="mb-3"
            :no-data-text="t('common.noData')"
          >
            <template #item="{ item, props: itemProps }">
              <v-list-item v-bind="itemProps">
                <template #append>
                  <v-chip v-if="item.raw.sources_count" size="x-small" color="grey">
                    {{ item.raw.sources_count }} {{ t('crawlPresets.sourcesMatched').split(' ')[0] }}
                  </v-chip>
                </template>
              </v-list-item>
            </template>
          </v-autocomplete>

          <!-- Entity Type: Multi-Select Dropdown -->
          <v-autocomplete
            v-model="formData.filters.entity_type"
            :label="t('crawlPresets.entityType')"
            :items="entityTypes"
            item-title="name"
            item-value="slug"
            variant="outlined"
            density="compact"
            multiple
            chips
            closable-chips
            :loading="entityTypesLoading"
            clearable
            class="mb-3"
            :no-data-text="t('common.noData')"
          />

          <!-- Tags: Multi-Select from available tags -->
          <v-autocomplete
            v-model="formData.filters.tags"
            :label="t('crawlPresets.tags')"
            :items="availableTags"
            item-title="tag"
            item-value="tag"
            variant="outlined"
            density="compact"
            multiple
            chips
            closable-chips
            :loading="tagsLoading"
            :hint="t('crawlPresets.tagsHintSelect')"
            persistent-hint
            class="mb-4"
            :no-data-text="t('common.noData')"
          >
            <template #item="{ item, props: itemProps }">
              <v-list-item v-bind="itemProps">
                <template #append>
                  <v-chip size="x-small" color="grey">{{ item.raw.count }}</v-chip>
                </template>
              </v-list-item>
            </template>
          </v-autocomplete>

          <!-- Search Text Field -->
          <v-text-field
            v-model="formData.filters.search"
            :label="t('crawlPresets.search')"
            :hint="t('crawlPresets.searchHint')"
            variant="outlined"
            density="compact"
            clearable
            prepend-inner-icon="mdi-magnify"
            class="mb-3"
          />

          <v-row>
            <v-col cols="4">
              <!-- Source Type: Multi-Select -->
              <v-select
                v-model="formData.filters.source_type"
                :label="t('crawlPresets.sourceType')"
                :items="sourceTypes"
                variant="outlined"
                density="compact"
                multiple
                chips
                closable-chips
                clearable
              />
            </v-col>
            <v-col cols="4">
              <!-- Status: Multi-Select -->
              <v-select
                v-model="formData.filters.status"
                :label="t('crawlPresets.status')"
                :items="statusOptions"
                variant="outlined"
                density="compact"
                clearable
              />
            </v-col>
            <v-col cols="4">
              <v-text-field
                v-model.number="formData.filters.limit"
                :label="t('crawlPresets.limit')"
                variant="outlined"
                density="compact"
                type="number"
                min="1"
                max="10000"
                :rules="limitRules"
              />
            </v-col>
          </v-row>

          <!-- Entity Selection (Optional) -->
          <v-divider class="my-4" />
          <v-expansion-panels variant="accordion" class="mb-4">
            <v-expansion-panel>
              <v-expansion-panel-title>
                <v-icon class="mr-2">mdi-account-group</v-icon>
                {{ t('crawlPresets.entitySelection.title') }}
                <v-chip
                  v-if="formData.filters.entity_ids && formData.filters.entity_ids.length > 0"
                  size="x-small"
                  color="primary"
                  class="ml-2"
                >
                  {{ formData.filters.entity_ids.length }}
                </v-chip>
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <v-alert
                  type="info"
                  variant="tonal"
                  density="compact"
                  class="mb-3"
                >
                  {{ t('crawlPresets.entitySelection.description') }}
                </v-alert>

                <v-radio-group
                  v-model="formData.filters.entity_selection_mode"
                  inline
                  hide-details
                  class="mb-3"
                >
                  <v-radio
                    :value="undefined"
                    :label="t('crawlPresets.entitySelection.none')"
                  />
                  <v-radio
                    value="fixed"
                    :label="t('crawlPresets.entitySelection.fixed')"
                  />
                  <v-radio
                    value="dynamic"
                    :label="t('crawlPresets.entitySelection.dynamic')"
                  />
                </v-radio-group>

                <p class="text-caption text-medium-emphasis mb-3">
                  <template v-if="!formData.filters.entity_selection_mode">
                    {{ t('crawlPresets.entitySelection.noneHint') }}
                  </template>
                  <template v-else-if="formData.filters.entity_selection_mode === 'fixed'">
                    {{ t('crawlPresets.entitySelection.fixedHint') }}
                  </template>
                  <template v-else>
                    {{ t('crawlPresets.entitySelection.dynamicHint') }}
                  </template>
                </p>

                <EntitySelector
                  v-if="formData.filters.entity_selection_mode === 'fixed'"
                  :model-value="formData.filters.entity_ids ?? []"
                  @update:model-value="formData.filters.entity_ids = $event"
                />
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>

          <!-- Schedule Configuration -->
          <v-divider class="my-4" />
          <div class="text-subtitle-2 mb-2">{{ t('crawlPresets.schedule.title') }}</div>

          <v-switch
            v-model="formData.schedule_enabled"
            :label="t('crawlPresets.schedule.enabled')"
            color="primary"
            density="compact"
          />

          <v-alert
            v-if="formData.schedule_enabled"
            type="info"
            variant="tonal"
            density="compact"
            class="mb-3"
          >
            <div class="text-caption">{{ t('crawlPresets.info.scheduleHint') }}</div>
          </v-alert>

          <v-row v-if="formData.schedule_enabled">
            <v-col cols="12">
              <ScheduleBuilder
                v-model="formData.schedule_cron"
                :disabled="saving"
                show-advanced
              />
            </v-col>
          </v-row>

          <!-- Preview -->
          <v-alert
            v-if="previewLoading || previewData"
            :type="(previewData?.sources_count ?? 0) > 0 ? 'info' : 'warning'"
            variant="tonal"
            class="mt-4"
          >
            <template v-if="previewLoading">
              <v-progress-circular indeterminate size="16" class="mr-2" />
              {{ t('crawlPresets.loadingPreview') }}
            </template>
            <template v-else-if="previewData">
              <strong>{{ previewData.sources_count }}</strong> {{ t('crawlPresets.sourcesMatched') }}
              <div v-if="previewData.sources_preview?.length" class="text-caption mt-1">
                {{ previewData.sources_preview.map(s => s.name).slice(0, 3).join(', ') }}
                <span v-if="previewData.has_more">...</span>
              </div>
              <div v-if="previewData.sources_count === 0" class="text-caption mt-1">
                {{ t('crawlPresets.info.previewHint') }}
              </div>
            </template>
          </v-alert>
        </v-form>
      </v-card-text>

      <v-card-actions>
        <v-btn
          variant="text"
          :loading="previewLoading"
          @click="loadPreview"
        >
          {{ t('crawlPresets.preview') }}
        </v-btn>
        <v-spacer />
        <v-btn variant="text" @click="close">
          {{ t('common.cancel') }}
        </v-btn>
        <v-btn
          color="primary"
          variant="tonal"
          :disabled="!formValid"
          :loading="saving"
          @click="save"
        >
          {{ isEditing ? t('common.save') : t('common.create') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { DIALOG_SIZES } from '@/config/ui'
import { SOURCE_TYPE_OPTIONS, CRAWL_PRESETS } from '@/config/sources'
import { useCrawlPresetsStore, type CrawlPreset, type CrawlPresetFilters, cleanFilters } from '@/stores/crawlPresets'
import { crawlPresetsApi, entityApi, adminApi } from '@/services/api'
import { categoryApi } from '@/services/api/categories'
import { useSnackbar } from '@/composables/useSnackbar'
import ScheduleBuilder from '@/components/common/ScheduleBuilder.vue'
import EntitySelector from '@/components/entities/EntitySelector.vue'
import { useLogger } from '@/composables/useLogger'

interface Props {
  modelValue: boolean
  preset?: CrawlPreset | null
  /** Initial entity IDs to pre-fill (for creating preset from entity selection) */
  initialEntityIds?: string[]
  /** Initial category ID to pre-fill */
  initialCategoryId?: string
}

const props = withDefaults(defineProps<Props>(), {
  preset: null,
  initialEntityIds: () => [],
  initialCategoryId: undefined,
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  saved: [preset: CrawlPreset]
}>()

const logger = useLogger('CrawlPresetEditor')

const { t } = useI18n()
const presetsStore = useCrawlPresetsStore()
const { showSuccess, showError } = useSnackbar()

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const isEditing = computed(() => !!props.preset?.id)

const formRef = ref()
const formValid = ref(false)
const saving = ref(false)
const previewLoading = ref(false)
const previewData = ref<{ sources_count: number; sources_preview: Array<{ id: string; name: string; status?: string }>; has_more: boolean } | null>(null)

// Info box visibility (persisted in localStorage)
const editorInfoHidden = ref(localStorage.getItem(CRAWL_PRESETS.STORAGE_KEYS.EDITOR_INFO_HIDDEN) === 'true')

function hideEditorInfo() {
  editorInfoHidden.value = true
  localStorage.setItem(CRAWL_PRESETS.STORAGE_KEYS.EDITOR_INFO_HIDDEN, 'true')
}

function showEditorInfo() {
  editorInfoHidden.value = false
  localStorage.removeItem(CRAWL_PRESETS.STORAGE_KEYS.EDITOR_INFO_HIDDEN)
}

// Dynamic data from API
const entityTypes = ref<Array<{ slug: string; name: string }>>([])
const categories = ref<Array<{ id: string; name: string; sources_count?: number }>>([])
const availableTags = ref<Array<{ tag: string; count: number }>>([])
const entityTypesLoading = ref(false)
const categoriesLoading = ref(false)
const tagsLoading = ref(false)

const formData = ref({
  name: '',
  description: '',
  filters: {
    entity_type: [] as string[],
    category_id: undefined as string | undefined,
    tags: [] as string[],
    source_type: [] as string[],
    status: undefined as string | undefined,
    search: undefined as string | undefined,
    limit: undefined as number | undefined,
    entity_ids: [] as string[],
    entity_selection_mode: undefined as 'fixed' | 'dynamic' | undefined,
  } as CrawlPresetFilters,
  schedule_cron: '',
  schedule_enabled: false,
})

// Source types from centralized config
const sourceTypes = SOURCE_TYPE_OPTIONS

// Source status options
const statusOptions = [
  { value: 'PENDING', title: 'Pending' },
  { value: 'ACTIVE', title: 'Active' },
  { value: 'PAUSED', title: 'Paused' },
  { value: 'ERROR', title: 'Error' },
]

// Validation rules for limit field
const limitRules = [
  (v: number | undefined) => v === undefined || v === null || v >= 1 || t('validation.min', { min: 1 }),
  (v: number | undefined) => v === undefined || v === null || v <= 10000 || t('validation.max', { max: 10000 }),
]

// Track if data has been loaded
const dataLoaded = ref(false)

// Load dynamic data (called when dialog opens)
async function loadDropdownData() {
  if (dataLoaded.value) return // Only load once

  // Set all loading states
  entityTypesLoading.value = true
  categoriesLoading.value = true
  tagsLoading.value = true

  // Load all data in parallel
  const [entityTypesResult, categoriesResult, tagsResult] = await Promise.allSettled([
    entityApi.getEntityTypes({ per_page: 100 }),
    categoryApi.list({ per_page: 100 }),
    adminApi.getAvailableTags(),
  ])

  // Process entity types result
  if (entityTypesResult.status === 'fulfilled') {
    entityTypes.value = entityTypesResult.value.data.items.map((et: { slug: string; name: string }) => ({
      slug: et.slug,
      name: et.name,
    }))
  } else {
    logger.error('Failed to load entity types:', entityTypesResult.reason)
  }
  entityTypesLoading.value = false

  // Process categories result
  if (categoriesResult.status === 'fulfilled') {
    categories.value = categoriesResult.value.data.items.map((cat: { id: string; name: string; sources_count?: number }) => ({
      id: cat.id,
      name: cat.name,
      sources_count: cat.sources_count,
    }))
  } else {
    logger.error('Failed to load categories:', categoriesResult.reason)
  }
  categoriesLoading.value = false

  // Process tags result
  if (tagsResult.status === 'fulfilled') {
    availableTags.value = tagsResult.value.data.tags || []
  } else {
    logger.error('Failed to load tags:', tagsResult.reason)
  }
  tagsLoading.value = false

  dataLoaded.value = true
}

let previewDebounceTimer: ReturnType<typeof setTimeout> | null = null

watch(
  () => formData.value.schedule_enabled,
  (enabled) => {
    if (enabled && !formData.value.schedule_cron) {
      formData.value.schedule_cron = CRAWL_PRESETS.DEFAULT_CRON
    }
  }
)

// Clear entity_ids when selection mode changes away from "fixed"
watch(
  () => formData.value.filters.entity_selection_mode,
  (newMode) => {
    if (newMode !== 'fixed') {
      formData.value.filters.entity_ids = []
    }
  }
)

// Reset form when dialog opens
watch(() => props.modelValue, async (visible) => {
  if (visible) {
    // Load dropdown data first (ensures categories are available for display)
    await loadDropdownData()

    if (props.preset) {
      // Copy filters and ensure backwards compatibility (convert strings to arrays)
      const filters = { ...props.preset.filters }

      // entity_type: convert string to array if needed
      if (typeof filters.entity_type === 'string') {
        filters.entity_type = filters.entity_type ? [filters.entity_type] : []
      }
      filters.entity_type = filters.entity_type || []

      // source_type: convert string to array if needed
      if (typeof filters.source_type === 'string') {
        filters.source_type = filters.source_type ? [filters.source_type] : []
      }
      filters.source_type = filters.source_type || []

      // tags: ensure array
      filters.tags = filters.tags || []

      // category_id: keep as-is (string or undefined)
      filters.category_id = filters.category_id || undefined

      // Generic filter fields: keep as-is (string or undefined)
      filters.status = filters.status || undefined
      filters.search = filters.search || undefined

      formData.value = {
        name: props.preset.name,
        description: props.preset.description || '',
        filters: filters,
        schedule_cron: props.preset.schedule_cron || '',
        schedule_enabled: props.preset.schedule_enabled,
      }
    } else {
      // Check if we have initial values (e.g., from entity selection)
      const hasInitialEntities = props.initialEntityIds && props.initialEntityIds.length > 0
      formData.value = {
        name: '',
        description: '',
        filters: {
          entity_type: [],
          category_id: props.initialCategoryId || undefined,
          tags: [],
          source_type: [],
          status: undefined,
          search: undefined,
          limit: undefined,
          entity_ids: hasInitialEntities ? [...props.initialEntityIds] : [],
          entity_selection_mode: hasInitialEntities ? 'fixed' : undefined,
        },
        schedule_cron: '',
        schedule_enabled: false,
      }
    }
    previewData.value = null
  }
})

// Auto-preview on filter changes (debounced)
watch(
  () => formData.value.filters,
  () => {
    // Only auto-preview for new presets (not editing existing ones)
    if (props.preset?.id) return

    // Clear previous timer
    if (previewDebounceTimer) {
      clearTimeout(previewDebounceTimer)
    }

    // Set new timer for debounced preview
    previewDebounceTimer = setTimeout(() => {
      // Only load preview if filters have meaningful values
      const filters = cleanFilters(formData.value.filters)
      if (Object.keys(filters).length > 0) {
        loadPreview()
      }
    }, CRAWL_PRESETS.AUTO_PREVIEW_DELAY_MS)
  },
  { deep: true }
)

// Cleanup debounce timer on unmount
onUnmounted(() => {
  if (previewDebounceTimer) {
    clearTimeout(previewDebounceTimer)
  }
})

async function loadPreview() {
  previewLoading.value = true
  try {
    if (props.preset?.id) {
      // For existing presets, use the store method
      const result = await presetsStore.previewPreset(props.preset.id)
      previewData.value = result
    } else {
      // For new presets, use the filters preview endpoint
      const response = await crawlPresetsApi.previewFilters(cleanFilters(formData.value.filters))
      previewData.value = response.data
    }
  } catch (error) {
    logger.error('Failed to load preview:', error)
    previewData.value = {
      sources_count: 0,
      sources_preview: [],
      has_more: false,
    }
  } finally {
    previewLoading.value = false
  }
}

async function save() {
  if (!formRef.value?.validate()) return

  saving.value = true
  try {
    const data = {
      name: formData.value.name,
      description: formData.value.description || undefined,
      filters: cleanFilters(formData.value.filters),
      schedule_cron: formData.value.schedule_enabled ? formData.value.schedule_cron : undefined,
      schedule_enabled: formData.value.schedule_enabled,
    }

    let result: CrawlPreset | null
    if (isEditing.value && props.preset) {
      result = await presetsStore.updatePreset(props.preset.id, data)
    } else {
      result = await presetsStore.createPreset(data)
    }

    if (result) {
      showSuccess(isEditing.value ? t('crawlPresets.messages.updated') : t('crawlPresets.messages.created'))
      emit('saved', result)
      close()
    } else {
      showError(t('common.error'))
    }
  } finally {
    saving.value = false
  }
}

function close() {
  dialogVisible.value = false
}

/**
 * Handle keyboard shortcuts for the dialog
 * - Escape: Close dialog
 * - Ctrl/Cmd + Enter: Save (if form is valid)
 */
function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    event.preventDefault()
    close()
  } else if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
    event.preventDefault()
    if (formValid.value && !saving.value) {
      save()
    }
  }
}
</script>
