<template>
  <div class="crawl-presets-tab">
    <!-- Collapsible Info Box -->
    <v-alert
      v-if="!infoHidden"
      type="info"
      variant="tonal"
      density="compact"
      class="mb-4"
      closable
      @click:close="hideInfo"
    >
      <template #prepend>
        <v-icon>mdi-information-outline</v-icon>
      </template>
      <div>
        <strong>{{ t('crawlPresets.info.overview') }}</strong>
        <div class="text-caption mt-1">{{ t('crawlPresets.info.overviewDetails') }}</div>
      </div>
    </v-alert>
    <v-btn
      v-else
      variant="text"
      size="x-small"
      color="info"
      class="mb-2"
      prepend-icon="mdi-information-outline"
      @click="showInfo"
    >
      {{ t('crawlPresets.info.showInfo') }}
    </v-btn>

    <!-- Header Actions -->
    <div class="d-flex align-center mb-4">
      <v-btn-toggle v-model="filterMode" color="primary" mandatory density="compact">
        <v-btn value="all">{{ t('crawlPresets.all') }}</v-btn>
        <v-btn value="favorites">
          <v-icon size="small" class="mr-1">mdi-star</v-icon>
          {{ t('crawlPresets.favorites') }}
        </v-btn>
        <v-btn value="scheduled">
          <v-icon size="small" class="mr-1">mdi-clock-outline</v-icon>
          {{ t('crawlPresets.scheduled') }}
        </v-btn>
      </v-btn-toggle>

      <v-spacer />

      <v-btn
        color="primary"
        prepend-icon="mdi-plus"
        @click="openEditor()"
      >
        {{ t('crawlPresets.create') }}
      </v-btn>
    </div>

    <!-- Loading State -->
    <v-progress-linear v-if="presetsStore.isLoading" indeterminate color="primary" class="mb-4" />

    <!-- Empty State -->
    <v-card v-if="!presetsStore.isLoading && filteredPresets.length === 0" class="pa-8 text-center" variant="outlined">
      <v-icon size="64" color="grey-lighten-1">mdi-content-save-cog-outline</v-icon>
      <div class="text-h6 mt-4 text-medium-emphasis">{{ t('crawlPresets.empty') }}</div>
      <div class="text-body-2 text-medium-emphasis mb-4">{{ t('crawlPresets.emptyHint') }}</div>
      <v-btn color="primary" variant="tonal" @click="openEditor()">
        {{ t('crawlPresets.createFirst') }}
      </v-btn>
    </v-card>

    <!-- Presets List -->
    <div v-else class="presets-list">
      <v-card
        v-for="preset in filteredPresets"
        :key="preset.id"
        class="preset-card mb-3"
        :class="{ 'preset-card--favorite': preset.is_favorite }"
      >
        <div class="d-flex">
          <!-- Main Content -->
          <div class="flex-grow-1 pa-4">
            <!-- Header Row -->
            <div class="d-flex align-center mb-2">
              <v-btn
                icon
                variant="text"
                size="small"
                :color="preset.is_favorite ? 'warning' : 'grey'"
                class="mr-2"
                :title="preset.is_favorite ? t('crawlPresets.removeFromFavorites') : t('crawlPresets.addToFavorites')"
                :aria-label="preset.is_favorite ? t('crawlPresets.removeFromFavorites') : t('crawlPresets.addToFavorites')"
                @click="toggleFavorite(preset)"
              >
                <v-icon>{{ preset.is_favorite ? 'mdi-star' : 'mdi-star-outline' }}</v-icon>
              </v-btn>
              <h3 class="text-subtitle-1 font-weight-medium flex-grow-1">
                {{ preset.name }}
              </h3>
              <v-chip
                v-if="preset.schedule_enabled"
                size="small"
                color="info"
                variant="tonal"
                class="ml-2"
              >
                <v-icon size="small" start>mdi-clock-outline</v-icon>
                {{ t('crawlPresets.scheduled') }}
              </v-chip>
            </div>

            <!-- Description -->
            <p v-if="preset.description" class="text-body-2 text-medium-emphasis mb-3">
              {{ preset.description }}
            </p>

            <!-- Filter Details - Clear readable format -->
            <div class="filter-details mb-3">
              <div v-if="getFilterDetails(preset).length === 0" class="text-body-2 text-medium-emphasis">
                {{ t('crawlPresets.noFiltersConfigured') }}
              </div>
              <div
                v-for="(detail, idx) in getFilterDetails(preset)"
                :key="idx"
                class="filter-detail-row d-flex align-center mb-1"
              >
                <v-icon size="small" :color="detail.color" class="mr-2">{{ detail.icon }}</v-icon>
                <span class="text-body-2">
                  <strong>{{ detail.label }}:</strong> {{ detail.value }}
                </span>
              </div>
            </div>

            <!-- Stats Row -->
            <div class="d-flex align-center text-caption text-medium-emphasis">
              <div v-if="preset.usage_count > 0" class="mr-4 d-flex align-center">
                <v-icon size="x-small" class="mr-1">mdi-play-circle-outline</v-icon>
                {{ t('crawlPresets.usedTimes', { count: preset.usage_count }) }}
              </div>
              <div v-if="preset.last_used_at" class="d-flex align-center">
                <v-icon size="x-small" class="mr-1">mdi-history</v-icon>
                {{ formatRelativeTime(preset.last_used_at) }}
              </div>
              <v-spacer />
              <div v-if="preset.schedule_enabled && preset.next_run_at" class="text-info d-flex align-center">
                <v-icon size="x-small" class="mr-1">mdi-calendar-clock</v-icon>
                {{ t('crawlPresets.nextRun') }}: {{ formatNextRun(preset.next_run_at) }}
              </div>
            </div>
          </div>

          <!-- Action Buttons - Vertical on right side -->
          <div class="preset-actions d-flex flex-column justify-center pa-2">
            <v-btn
              color="primary"
              variant="tonal"
              size="small"
              class="mb-2"
              :loading="executingPresetId === preset.id"
              :title="t('crawlPresets.execute')"
              :aria-label="`${t('crawlPresets.execute')} ${preset.name}`"
              @click="executePreset(preset)"
            >
              <v-icon start aria-hidden="true">mdi-play</v-icon>
              {{ t('crawlPresets.execute') }}
            </v-btn>
            <v-btn
              variant="outlined"
              size="small"
              class="mb-2"
              :title="t('crawlPresets.edit')"
              :aria-label="`${t('common.edit')} ${preset.name}`"
              @click="openEditor(preset)"
            >
              <v-icon start aria-hidden="true">mdi-pencil</v-icon>
              {{ t('common.edit') }}
            </v-btn>
            <v-btn
              variant="text"
              size="small"
              class="mb-2"
              :title="t('crawlPresets.duplicate')"
              :aria-label="`${t('crawlPresets.duplicate')} ${preset.name}`"
              @click="duplicatePreset(preset)"
            >
              <v-icon start aria-hidden="true">mdi-content-copy</v-icon>
              {{ t('crawlPresets.duplicate') }}
            </v-btn>
            <v-btn
              variant="text"
              size="small"
              color="error"
              :title="t('crawlPresets.delete')"
              :aria-label="`${t('common.delete')} ${preset.name}`"
              @click="confirmDelete(preset)"
            >
              <v-icon start aria-hidden="true">mdi-delete-outline</v-icon>
              {{ t('common.delete') }}
            </v-btn>
          </div>
        </div>
      </v-card>
    </div>

    <!-- Editor Dialog -->
    <CrawlPresetEditor
      v-model="editorVisible"
      :preset="editingPreset"
      @saved="onPresetSaved"
    />

    <!-- Delete Confirmation Dialog -->
    <v-dialog
      v-model="deleteDialog"
      :max-width="DIALOG_SIZES.XS"
      aria-labelledby="delete-dialog-title"
    >
      <v-card role="alertdialog" aria-modal="true" aria-describedby="delete-dialog-description">
        <v-card-title id="delete-dialog-title" class="d-flex align-center">
          <v-icon color="error" class="mr-2" aria-hidden="true">mdi-alert-circle</v-icon>
          {{ t('crawlPresets.delete') }}
        </v-card-title>
        <v-card-text id="delete-dialog-description">
          {{ t('crawlPresets.deleteConfirm', { name: deletingPreset?.name }) }}
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="deleteDialog = false">
            {{ t('common.cancel') }}
          </v-btn>
          <v-btn color="error" variant="tonal" @click="deletePreset">
            {{ t('common.delete') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCrawlPresetsStore, type CrawlPreset } from '@/stores/crawlPresets'
import { useCategoriesStore } from '@/stores/categories'
import { useSnackbar } from '@/composables/useSnackbar'
import { useDialogFocus, useDateFormatter } from '@/composables'
import CrawlPresetEditor from './CrawlPresetEditor.vue'
import { DIALOG_SIZES } from '@/config/ui'
import { SOURCE_TYPE_LABELS, CRAWL_PRESETS } from '@/config/sources'

const { t } = useI18n()
const presetsStore = useCrawlPresetsStore()
const categoriesStore = useCategoriesStore()
const { showSuccess, showError } = useSnackbar()
const { formatDateTime, formatRelativeTime } = useDateFormatter()

const filterMode = ref<'all' | 'favorites' | 'scheduled'>('all')
const editorVisible = ref(false)
const editingPreset = ref<CrawlPreset | null>(null)
const deleteDialog = ref(false)
const deletingPreset = ref<CrawlPreset | null>(null)
const executingPresetId = ref<string | null>(null)

// Info box visibility (persisted in localStorage)
const infoHidden = ref(localStorage.getItem(CRAWL_PRESETS.STORAGE_KEYS.INFO_HIDDEN) === 'true')

function hideInfo() {
  infoHidden.value = true
  localStorage.setItem(CRAWL_PRESETS.STORAGE_KEYS.INFO_HIDDEN, 'true')
}

function showInfo() {
  infoHidden.value = false
  localStorage.removeItem(CRAWL_PRESETS.STORAGE_KEYS.INFO_HIDDEN)
}

// Focus management for accessibility (WCAG 2.1)
useDialogFocus({ isOpen: deleteDialog })

/**
 * Get category name by ID from the store
 */
function getCategoryName(categoryId: string): string {
  const category = categoriesStore.categories.find(c => c.id === categoryId)
  return category?.name || categoryId
}

const filteredPresets = computed(() => {
  switch (filterMode.value) {
    case 'favorites':
      return presetsStore.favorites
    case 'scheduled':
      return presetsStore.scheduledPresets
    default:
      return presetsStore.activePresets
  }
})

interface FilterDetail {
  icon: string
  label: string
  value: string
  color: string
}

/**
 * Get human-readable filter details for a preset
 */
function getFilterDetails(preset: CrawlPreset): FilterDetail[] {
  const details: FilterDetail[] = []
  const filters = preset.filters

  // Entity Types
  if (filters.entity_type) {
    const types = Array.isArray(filters.entity_type)
      ? filters.entity_type
      : [filters.entity_type]
    if (types.length > 0) {
      details.push({
        icon: 'mdi-shape-outline',
        label: t('crawlPresets.filterLabels.entityTypes'),
        value: types.length === 1 ? types[0] : `${types.length} ${t('crawlPresets.filterLabels.types')}`,
        color: 'primary',
      })
    }
  }

  // Category
  if (filters.category_id) {
    details.push({
      icon: 'mdi-folder-outline',
      label: t('crawlPresets.category'),
      value: getCategoryName(filters.category_id),
      color: 'secondary',
    })
  }

  // Source Types
  if (filters.source_type) {
    const sources = Array.isArray(filters.source_type)
      ? filters.source_type
      : [filters.source_type]
    if (sources.length > 0) {
      const sourceLabels = sources.map(s => getSourceTypeLabel(s))
      details.push({
        icon: 'mdi-database-outline',
        label: t('crawlPresets.filterLabels.sourceTypes'),
        value: sourceLabels.join(', '),
        color: 'info',
      })
    }
  }

  // Tags
  if (filters.tags && filters.tags.length > 0) {
    const tagDisplay = filters.tags.length <= 3
      ? filters.tags.join(', ')
      : `${filters.tags.slice(0, 3).join(', ')} (+${filters.tags.length - 3})`
    details.push({
      icon: 'mdi-tag-multiple-outline',
      label: t('crawlPresets.filterLabels.tags'),
      value: tagDisplay,
      color: 'success',
    })
  }

  // Status
  if (filters.status) {
    details.push({
      icon: 'mdi-pulse',
      label: t('crawlPresets.status'),
      value: filters.status,
      color: 'teal',
    })
  }

  // Search
  if (filters.search) {
    details.push({
      icon: 'mdi-magnify',
      label: t('crawlPresets.search'),
      value: filters.search,
      color: 'blue-grey',
    })
  }

  // Limit
  if (filters.limit) {
    details.push({
      icon: 'mdi-counter',
      label: t('crawlPresets.filterLabels.limit'),
      value: String(filters.limit),
      color: 'warning',
    })
  }

  return details
}

/**
 * Get localized source type label from centralized config
 */
function getSourceTypeLabel(sourceType: string): string {
  return SOURCE_TYPE_LABELS[sourceType] || sourceType
}

// formatRelativeTime is now from useDateFormatter

function formatNextRun(dateStr: string): string {
  const date = new Date(dateStr)
  return formatDateTime(date)
}

function openEditor(preset?: CrawlPreset) {
  editingPreset.value = preset || null
  editorVisible.value = true
}

/**
 * Duplicate a preset by creating a copy with modified name
 */
function duplicatePreset(preset: CrawlPreset) {
  // Create a copy with modified name (no ID = new preset)
  const duplicatedPreset: CrawlPreset = {
    ...preset,
    id: '', // Clear ID to create new preset
    name: `${preset.name} ${t('crawlPresets.duplicateSuffix')}`,
    usage_count: 0,
    last_used_at: null,
    is_favorite: false,
  }
  editingPreset.value = duplicatedPreset
  editorVisible.value = true
  // Toast after modal opens for better UX
  setTimeout(() => showSuccess(t('crawlPresets.duplicateSuccess')), 100)
}

function onPresetSaved() {
  presetsStore.loadPresets()
}

async function toggleFavorite(preset: CrawlPreset) {
  const newState = await presetsStore.toggleFavorite(preset.id)
  showSuccess(newState ? t('crawlPresets.addedToFavorites') : t('crawlPresets.removedFromFavorites'))
}

async function executePreset(preset: CrawlPreset) {
  executingPresetId.value = preset.id
  try {
    const result = await presetsStore.executePreset(preset.id)
    if (result) {
      showSuccess(t('crawlPresets.messages.executed', { count: result.jobs_created }))
    }
  } catch {
    showError(t('crawlPresets.messages.executeFailed'))
  } finally {
    executingPresetId.value = null
  }
}

function confirmDelete(preset: CrawlPreset) {
  deletingPreset.value = preset
  deleteDialog.value = true
}

async function deletePreset() {
  if (!deletingPreset.value) return

  const success = await presetsStore.deletePreset(deletingPreset.value.id)
  if (success) {
    showSuccess(t('crawlPresets.messages.deleted'))
  } else {
    showError(t('common.error'))
  }
  deleteDialog.value = false
  deletingPreset.value = null
}

onMounted(async () => {
  // Load presets and categories in parallel
  await Promise.all([
    presetsStore.loadPresets(),
    categoriesStore.fetchCategories(),
  ])
})
</script>

<style scoped lang="scss">
.presets-list {
  max-height: calc(100vh - 200px);
  overflow-y: auto;
}

.preset-card {
  transition: all 0.2s ease;
  border-left: 4px solid transparent;

  &:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  &--favorite {
    border-left-color: rgb(var(--v-theme-warning));
    background: linear-gradient(90deg, rgba(var(--v-theme-warning), 0.03) 0%, transparent 100%);
  }
}

.preset-actions {
  min-width: 130px;
  border-left: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.filter-details {
  background: rgba(var(--v-theme-on-surface), 0.03);
  border-radius: 8px;
  padding: 12px;
}

.filter-detail-row {
  &:last-child {
    margin-bottom: 0 !important;
  }
}
</style>
