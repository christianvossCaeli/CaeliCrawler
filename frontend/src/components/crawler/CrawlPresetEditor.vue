<template>
  <v-dialog v-model="dialogVisible" max-width="700" persistent @keydown="handleKeydown">
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2">mdi-content-save-cog</v-icon>
        {{ isEditing ? t('crawlPresets.edit') : t('crawlPresets.create') }}
      </v-card-title>

      <v-card-text>
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
          >
            <template #item="{ item, props: itemProps }">
              <v-list-item v-bind="itemProps">
                <template #append>
                  <v-chip size="x-small" color="grey">{{ item.raw.count }}</v-chip>
                </template>
              </v-list-item>
            </template>
          </v-autocomplete>

          <v-row>
            <v-col cols="6">
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
            <v-col cols="6">
              <v-text-field
                v-model.number="formData.filters.limit"
                :label="t('crawlPresets.limit')"
                variant="outlined"
                density="compact"
                type="number"
                min="1"
                max="10000"
              />
            </v-col>
          </v-row>

          <!-- Schedule Configuration -->
          <v-divider class="my-4" />
          <div class="text-subtitle-2 mb-2">{{ t('crawlPresets.schedule.title') }}</div>

          <v-switch
            v-model="formData.schedule_enabled"
            :label="t('crawlPresets.schedule.enabled')"
            color="primary"
            density="compact"
          />

          <v-row v-if="formData.schedule_enabled">
            <v-col cols="12">
              <ScheduleBuilder
                v-model="formData.schedule_cron"
                :disabled="saving"
                :show-advanced="true"
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
            </template>
          </v-alert>
        </v-form>
      </v-card-text>

      <v-card-actions>
        <v-btn
          variant="text"
          @click="loadPreview"
          :loading="previewLoading"
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
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCrawlPresetsStore, type CrawlPreset, type CrawlPresetFilters, cleanFilters } from '@/stores/crawlPresets'
import { crawlPresetsApi, entityApi, adminApi } from '@/services/api'
import { useSnackbar } from '@/composables/useSnackbar'
import ScheduleBuilder from '@/components/common/ScheduleBuilder.vue'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger('CrawlPresetEditor')

const { t } = useI18n()
const presetsStore = useCrawlPresetsStore()
const { showSuccess, showError } = useSnackbar()

interface Props {
  modelValue: boolean
  preset?: CrawlPreset | null
}

const props = withDefaults(defineProps<Props>(), {
  preset: null,
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  saved: [preset: CrawlPreset]
}>()

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const isEditing = computed(() => !!props.preset?.id)

const formRef = ref()
const formValid = ref(false)
const saving = ref(false)
const previewLoading = ref(false)
const previewData = ref<{ sources_count: number; sources_preview: any[]; has_more: boolean } | null>(null)

// Dynamic data from API
const entityTypes = ref<Array<{ slug: string; name: string }>>([])
const availableTags = ref<Array<{ tag: string; count: number }>>([])
const entityTypesLoading = ref(false)
const tagsLoading = ref(false)

const formData = ref({
  name: '',
  description: '',
  filters: {
    entity_type: [] as string[],
    tags: [] as string[],
    source_type: [] as string[],
    limit: undefined as number | undefined,
  } as CrawlPresetFilters,
  schedule_cron: '',
  schedule_enabled: false,
})

const sourceTypes = [
  { value: 'WEBSITE', title: 'Website' },
  { value: 'OPARL_API', title: 'OParl API' },
  { value: 'RSS', title: 'RSS Feed' },
  { value: 'CUSTOM_API', title: 'Custom API' },
  { value: 'REST_API', title: 'REST API' },
  { value: 'SPARQL_API', title: 'SPARQL API' },
]

// Load dynamic data on mount
onMounted(async () => {
  // Load entity types
  entityTypesLoading.value = true
  try {
    const response = await entityApi.getEntityTypes({ per_page: 100 })
    entityTypes.value = response.data.items.map((et: any) => ({
      slug: et.slug,
      name: et.name,
    }))
  } catch (error) {
    logger.error('Failed to load entity types:', error)
  } finally {
    entityTypesLoading.value = false
  }

  // Load available tags
  tagsLoading.value = true
  try {
    const response = await adminApi.getAvailableTags()
    availableTags.value = response.data.tags || []
  } catch (error) {
    logger.error('Failed to load tags:', error)
  } finally {
    tagsLoading.value = false
  }
})

/** Debounce delay for auto-preview in milliseconds */
const AUTO_PREVIEW_DELAY = 500
let previewDebounceTimer: ReturnType<typeof setTimeout> | null = null

watch(
  () => formData.value.schedule_enabled,
  (enabled) => {
    if (enabled && !formData.value.schedule_cron) {
      formData.value.schedule_cron = '0 6 * * *'
    }
  }
)

// Reset form when dialog opens
watch(() => props.modelValue, (visible) => {
  if (visible) {
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

      formData.value = {
        name: props.preset.name,
        description: props.preset.description || '',
        filters: filters,
        schedule_cron: props.preset.schedule_cron || '',
        schedule_enabled: props.preset.schedule_enabled,
      }
    } else {
      formData.value = {
        name: '',
        description: '',
        filters: {
          entity_type: [],
          tags: [],
          source_type: [],
          limit: undefined,
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
    }, AUTO_PREVIEW_DELAY)
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
