<template>
  <div class="crawl-presets-tab">
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
    <v-row v-else>
      <v-col
        v-for="preset in filteredPresets"
        :key="preset.id"
        cols="12"
        md="6"
        lg="4"
      >
        <v-card class="preset-card h-100" :class="{ 'border-warning': preset.is_favorite }">
          <v-card-title class="d-flex align-center">
            <v-btn
              icon
              variant="text"
              size="small"
              :color="preset.is_favorite ? 'warning' : 'default'"
              @click="toggleFavorite(preset)"
            >
              <v-icon>{{ preset.is_favorite ? 'mdi-star' : 'mdi-star-outline' }}</v-icon>
            </v-btn>
            <span class="text-truncate flex-grow-1">{{ preset.name }}</span>
            <v-chip
              v-if="preset.schedule_enabled"
              size="x-small"
              color="info"
              variant="tonal"
            >
              <v-icon size="x-small" start>mdi-clock-outline</v-icon>
              {{ t('crawlPresets.scheduled') }}
            </v-chip>
          </v-card-title>

          <v-card-text>
            <div class="text-caption text-medium-emphasis mb-2">
              {{ preset.description || preset.filter_summary }}
            </div>

            <!-- Filter Summary Chips -->
            <div class="d-flex flex-wrap gap-1 mb-3">
              <v-chip
                v-if="preset.filters.entity_type"
                size="x-small"
                color="primary"
                variant="tonal"
              >
                {{ preset.filters.entity_type }}
              </v-chip>
              <v-chip
                v-if="preset.filters.admin_level_1"
                size="x-small"
                color="success"
                variant="tonal"
              >
                {{ preset.filters.admin_level_1 }}
              </v-chip>
              <v-chip
                v-for="tag in (preset.filters.tags || []).slice(0, 2)"
                :key="tag"
                size="x-small"
                variant="tonal"
              >
                {{ tag }}
              </v-chip>
              <v-chip
                v-if="(preset.filters.tags || []).length > 2"
                size="x-small"
                variant="outlined"
              >
                +{{ preset.filters.tags!.length - 2 }}
              </v-chip>
            </div>

            <!-- Stats -->
            <div class="d-flex align-center text-caption text-medium-emphasis">
              <div v-if="preset.usage_count > 0" class="mr-3">
                <v-icon size="x-small" class="mr-1">mdi-play-circle</v-icon>
                {{ preset.usage_count }}x
              </div>
              <div v-if="preset.last_used_at">
                {{ formatRelativeTime(preset.last_used_at) }}
              </div>
              <v-spacer />
              <div v-if="preset.schedule_enabled && preset.next_run_at" class="text-info">
                <v-icon size="x-small" class="mr-1">mdi-clock-outline</v-icon>
                {{ formatNextRun(preset.next_run_at) }}
              </div>
            </div>
          </v-card-text>

          <v-card-actions>
            <v-btn
              color="primary"
              variant="tonal"
              size="small"
              prepend-icon="mdi-play"
              :loading="executingPresetId === preset.id"
              @click="executePreset(preset)"
            >
              {{ t('crawlPresets.execute') }}
            </v-btn>
            <v-spacer />
            <v-btn
              icon="mdi-pencil"
              variant="text"
              size="small"
              @click="openEditor(preset)"
            />
            <v-btn
              icon="mdi-delete"
              variant="text"
              size="small"
              color="error"
              @click="confirmDelete(preset)"
            />
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <!-- Editor Dialog -->
    <CrawlPresetEditor
      v-model="editorVisible"
      :preset="editingPreset"
      @saved="onPresetSaved"
    />

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="deleteDialog" max-width="400">
      <v-card>
        <v-card-title>{{ t('crawlPresets.delete') }}</v-card-title>
        <v-card-text>
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
import { useSnackbar } from '@/composables/useSnackbar'
import CrawlPresetEditor from './CrawlPresetEditor.vue'

const { t, locale } = useI18n()
const presetsStore = useCrawlPresetsStore()
const { showSuccess, showError } = useSnackbar()

const filterMode = ref<'all' | 'favorites' | 'scheduled'>('all')
const editorVisible = ref(false)
const editingPreset = ref<CrawlPreset | null>(null)
const deleteDialog = ref(false)
const deletingPreset = ref<CrawlPreset | null>(null)
const executingPresetId = ref<string | null>(null)

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

function formatRelativeTime(dateStr: string): string {
  const now = new Date()
  const then = new Date(dateStr)
  const diffMs = now.getTime() - then.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return t('crawlPresets.justNow')
  if (diffMins < 60) return t('crawlPresets.minutesAgo', { n: diffMins })
  if (diffHours < 24) return t('crawlPresets.hoursAgo', { n: diffHours })
  if (diffDays < 7) return t('crawlPresets.daysAgo', { n: diffDays })

  return then.toLocaleDateString(locale.value === 'de' ? 'de-DE' : 'en-US')
}

function formatNextRun(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleString(locale.value === 'de' ? 'de-DE' : 'en-US', {
    weekday: 'short',
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function openEditor(preset?: CrawlPreset) {
  editingPreset.value = preset || null
  editorVisible.value = true
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

onMounted(() => {
  presetsStore.loadPresets()
})
</script>

<style scoped lang="scss">
.preset-card {
  transition: all 0.2s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  &.border-warning {
    border-left: 3px solid rgb(var(--v-theme-warning));
  }
}
</style>
