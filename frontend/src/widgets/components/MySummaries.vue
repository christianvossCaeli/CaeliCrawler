<template>
  <BaseWidget
    :definition="definition"
    :config="config"
    :is-editing="isEditing"
    @refresh="refresh"
  >
    <div v-if="loading" class="d-flex justify-center py-6">
      <v-progress-circular indeterminate size="32" />
    </div>

    <template v-else-if="displayedSummaries.length > 0">
      <v-list density="compact" class="summaries-list" role="list">
        <v-list-item
          v-for="summary in displayedSummaries"
          :key="summary.id"
          class="px-2 clickable-item"
          :class="{ 'non-interactive': isEditing }"
          role="button"
          :tabindex="tabIndex"
          :aria-label="summary.name"
          @click="navigateToSummary(summary)"
          @keydown="handleKeydownSummary($event, summary)"
        >
          <template #prepend>
            <v-icon
              v-if="summary.is_favorite"
              icon="mdi-star"
              color="amber-darken-2"
              size="small"
            />
            <v-icon
              v-else
              :icon="getStatusIcon(summary.status)"
              :color="getStatusColor(summary.status)"
              size="small"
            />
          </template>

          <v-list-item-title class="text-body-2 text-truncate">
            {{ summary.name }}
          </v-list-item-title>
          <v-list-item-subtitle class="text-caption">
            <span v-if="summary.last_executed_at">
              {{ t('summaries.executed') }}: {{ formatTime(summary.last_executed_at) }}
            </span>
            <span v-else class="text-medium-emphasis">
              {{ t('summaries.neverExecuted') }}
            </span>
          </v-list-item-subtitle>

          <template #append>
            <v-btn
              icon
              size="x-small"
              variant="text"
              :loading="store.isExecutingSummary(summary.id)"
              :disabled="isEditing"
              :aria-label="t('summaries.execute')"
              @click="executeSummary(summary, $event)"
            >
              <v-icon size="small">mdi-play</v-icon>
            </v-btn>
          </template>
        </v-list-item>
      </v-list>

      <!-- Actions -->
      <div class="d-flex justify-space-between mt-2">
        <div
          class="view-all-link"
          :class="{ 'non-interactive': isEditing }"
          role="button"
          :tabindex="tabIndex"
          :aria-label="t('common.viewAll')"
          @click="navigateToSummaries"
          @keydown="handleKeydownViewAll($event)"
        >
          <span class="text-caption text-primary">
            {{ t('common.viewAll') }}
          </span>
        </div>

        <div
          class="view-all-link"
          :class="{ 'non-interactive': isEditing }"
          role="button"
          :tabindex="tabIndex"
          :aria-label="t('summaries.createNew')"
          @click="navigateToCreate"
          @keydown="handleKeydownCreate($event)"
        >
          <span class="text-caption text-primary">
            <v-icon size="x-small" class="mr-1">mdi-plus</v-icon>
            {{ t('summaries.createNew') }}
          </span>
        </div>
      </div>
    </template>

    <WidgetEmptyState
      v-else
      icon="mdi-chart-box-outline"
      :message="t('summaries.noSummaries')"
    >
      <v-btn
        variant="tonal"
        color="primary"
        size="small"
        class="mt-3"
        :disabled="isEditing"
        @click="navigateToCreate"
      >
        <v-icon start size="small">mdi-plus</v-icon>
        {{ t('summaries.createFirst') }}
      </v-btn>
    </WidgetEmptyState>
  </BaseWidget>
</template>

<script setup lang="ts">
/**
 * MySummaries Widget - Shows user's custom summaries with quick access
 */

import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useCustomSummariesStore, type CustomSummary } from '@/stores/customSummaries'
import { useStatusColors } from '@/composables/useStatusColors'
import { handleKeyboardClick } from '../composables'
import BaseWidget from '../BaseWidget.vue'
import WidgetEmptyState from './WidgetEmptyState.vue'
import type { WidgetDefinition, WidgetConfig } from '../types'
import { WIDGET_DEFAULT_LIMIT } from '../types'

const props = defineProps<{
  definition: WidgetDefinition
  config?: WidgetConfig
  isEditing?: boolean
}>()

const { t } = useI18n()
const router = useRouter()
const store = useCustomSummariesStore()
const { getStatusColor, getStatusIcon } = useStatusColors()
const loading = ref(true)
const error = ref<string | null>(null)

const refresh = async () => {
  loading.value = true
  error.value = null
  try {
    await store.loadSummaries({
      per_page: WIDGET_DEFAULT_LIMIT,
      sort_by: 'updated_at',
      sort_order: 'desc',
    })
  } catch (e) {
    error.value = e instanceof Error ? e.message : t('common.loadError')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (store.summaries.length === 0) {
    refresh()
  } else {
    loading.value = false
  }
})

const isEditMode = computed(() => props.isEditing ?? false)
const tabIndex = computed(() => (isEditMode.value ? -1 : 0))

// Show favorites first, then recent
const displayedSummaries = computed(() => {
  const favorites = store.summaries.filter(s => s.is_favorite)
  const others = store.summaries.filter(s => !s.is_favorite)
  return [...favorites, ...others].slice(0, 6)
})


const formatTime = (timestamp: string | null | undefined): string => {
  if (!timestamp) return t('summaries.neverExecuted')

  const date = new Date(timestamp)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000) return t('common.justNow')
  if (diff < 3600000) return t('common.minutesAgo', { n: Math.floor(diff / 60000) })
  if (diff < 86400000) return t('common.hoursAgo', { n: Math.floor(diff / 3600000) })
  return t('common.daysAgo', { n: Math.floor(diff / 86400000) })
}

const navigateToSummary = (summary: CustomSummary) => {
  if (isEditMode.value) return
  router.push({ path: `/summaries/${summary.id}` })
}

const navigateToSummaries = () => {
  if (isEditMode.value) return
  router.push({ path: '/summaries' })
}

const navigateToCreate = () => {
  if (isEditMode.value) return
  router.push({ path: '/summaries', query: { create: 'true' } })
}

const handleKeydownSummary = (event: KeyboardEvent, summary: CustomSummary) => {
  handleKeyboardClick(event, () => navigateToSummary(summary))
}

const handleKeydownViewAll = (event: KeyboardEvent) => {
  handleKeyboardClick(event, () => navigateToSummaries())
}

const handleKeydownCreate = (event: KeyboardEvent) => {
  handleKeyboardClick(event, () => navigateToCreate())
}

const executeSummary = async (summary: CustomSummary, event: Event) => {
  event.stopPropagation()
  if (isEditMode.value || store.isExecutingSummary(summary.id)) return
  await store.executeSummary(summary.id)
}
</script>

<style scoped>
.summaries-list {
  max-height: 250px;
  overflow-y: auto;
}

.clickable-item {
  cursor: pointer;
  border-radius: 8px;
  transition: background-color 0.2s ease;
}

.clickable-item:hover {
  background-color: rgba(var(--v-theme-on-surface), 0.08);
}

.clickable-item:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}

.view-all-link {
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background-color 0.2s ease;
}

.view-all-link:hover {
  background-color: rgba(var(--v-theme-on-surface), 0.08);
}

.view-all-link:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}

.non-interactive {
  cursor: default;
  pointer-events: none;
}
</style>
