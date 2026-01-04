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

    <template v-else-if="sources.length > 0">
      <!-- Summary Bar -->
      <div class="d-flex justify-space-around mb-3 pa-2 summary-bar rounded" role="group" aria-label="Data freshness summary">
        <div class="text-center">
          <div class="text-h6 text-success">{{ summaryStats.fresh }}</div>
          <div class="text-caption">{{ t('dashboard.fresh') }}</div>
        </div>
        <v-divider vertical />
        <div class="text-center">
          <div class="text-h6 text-warning">{{ summaryStats.stale }}</div>
          <div class="text-caption">{{ t('dashboard.stale') }}</div>
        </div>
        <v-divider vertical />
        <div class="text-center">
          <div class="text-h6 text-error">{{ summaryStats.outdated }}</div>
          <div class="text-caption">{{ t('dashboard.outdated') }}</div>
        </div>
      </div>

      <!-- Source List -->
      <v-list density="compact" class="sources-list" role="list">
        <v-list-item
          v-for="source in sources"
          :key="source.id"
          class="px-2 clickable-item"
          :class="{ 'non-interactive': isEditing }"
          role="button"
          :tabindex="tabIndex"
          :aria-label="source.name + ' - ' + formatLastCrawl(source.last_crawl)"
          @click="navigateToSource(source)"
          @keydown="handleKeydownSource($event, source)"
        >
          <template #prepend>
            <v-icon
              :icon="getFreshnessIcon(source.freshness)"
              :color="getFreshnessColor(source.freshness)"
              size="small"
            />
          </template>

          <v-list-item-title class="text-body-2 text-truncate">
            {{ source.name }}
          </v-list-item-title>
          <v-list-item-subtitle class="text-caption">
            {{ formatLastCrawl(source.last_crawl) }}
            <span class="text-medium-emphasis ml-1">
              ({{ source.document_count }} {{ t('common.documents') }})
            </span>
          </v-list-item-subtitle>
        </v-list-item>
      </v-list>

      <!-- View All Link -->
      <div
        class="text-center mt-2 view-all-link"
        :class="{ 'non-interactive': isEditing }"
        role="button"
        :tabindex="tabIndex"
        :aria-label="t('common.viewAll')"
        @click="navigateToSources"
        @keydown="handleKeydownViewAll($event)"
      >
        <span class="text-caption text-primary">
          {{ t('common.viewAll') }}
        </span>
      </div>
    </template>

    <WidgetEmptyState
      v-else
      icon="mdi-database-off"
      :message="t('dashboard.noSources')"
    />
  </BaseWidget>
</template>

<script setup lang="ts">
/**
 * DataFreshness Widget - Shows data freshness per source
 */

import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { adminApi } from '@/services/api'
import { useDateFormatter } from '@/composables'
import { handleKeyboardClick } from '../composables'
import BaseWidget from '../BaseWidget.vue'
import WidgetEmptyState from './WidgetEmptyState.vue'
import type { WidgetDefinition, WidgetConfig, SourceFreshness, FreshnessLevel } from '../types'
import { FRESHNESS_THRESHOLDS, WIDGET_DEFAULT_LIMIT } from '../types'
import type { DataSourceResponse } from '@/types/sources'

const props = defineProps<{
  definition: WidgetDefinition
  config?: WidgetConfig
  isEditing?: boolean
}>()

const { t } = useI18n()
const router = useRouter()
const { formatDateShort } = useDateFormatter()
const loading = ref(true)
const error = ref<string | null>(null)
const sources = ref<SourceFreshness[]>([])

const refresh = async () => {
  loading.value = true
  error.value = null
  try {
    const response = await adminApi.getSources({
      per_page: WIDGET_DEFAULT_LIMIT,
      status: 'ACTIVE',
    })
    const items = response.data?.items || []
    sources.value = items.map((source: DataSourceResponse): SourceFreshness => ({
      id: source.id,
      name: source.name,
      last_crawl: source.last_crawl || null,
      status: source.status,
      document_count: source.document_count,
      freshness: calculateFreshness(source.last_crawl),
    }))
    // Sort by freshness priority (outdated first)
    sources.value.sort((a, b) => {
      const priority = { never: 0, outdated: 1, stale: 2, fresh: 3 }
      return priority[a.freshness] - priority[b.freshness]
    })
  } catch (e) {
    error.value = e instanceof Error ? e.message : t('common.loadError')
  } finally {
    loading.value = false
  }
}

const calculateFreshness = (lastCrawl: string | null | undefined): FreshnessLevel => {
  if (!lastCrawl) return 'never'

  const date = new Date(lastCrawl)
  // Validate date
  if (isNaN(date.getTime())) return 'never'

  const hoursSince = (Date.now() - date.getTime()) / (1000 * 60 * 60)

  // Handle future dates (clock skew) - treat as fresh
  if (hoursSince < 0) return 'fresh'

  if (hoursSince < FRESHNESS_THRESHOLDS.FRESH_HOURS) return 'fresh'
  if (hoursSince < FRESHNESS_THRESHOLDS.STALE_HOURS) return 'stale'
  return 'outdated'
}

onMounted(() => {
  refresh()
})

const isEditMode = computed(() => props.isEditing ?? false)
const tabIndex = computed(() => (isEditMode.value ? -1 : 0))

const getFreshnessColor = (freshness: string): string => {
  const colorMap: Record<string, string> = {
    fresh: 'success',
    stale: 'warning',
    outdated: 'error',
    never: 'grey',
  }
  return colorMap[freshness] || 'grey'
}

const getFreshnessIcon = (freshness: string): string => {
  const iconMap: Record<string, string> = {
    fresh: 'mdi-check-circle',
    stale: 'mdi-clock-alert',
    outdated: 'mdi-alert-circle',
    never: 'mdi-help-circle',
  }
  return iconMap[freshness] || 'mdi-help-circle'
}

const formatLastCrawl = (lastCrawl: string | null): string => {
  if (!lastCrawl) return t('dashboard.neverCrawled')

  const date = new Date(lastCrawl)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const hours = Math.floor(diff / (1000 * 60 * 60))
  const days = Math.floor(hours / 24)

  if (hours < 1) return t('common.justNow')
  if (hours < 24) return t('common.hoursAgo', { n: hours })
  if (days < 7) return t('common.daysAgo', { n: days })
  return formatDateShort(date)
}

const navigateToSource = (source: SourceFreshness) => {
  if (isEditMode.value) return
  router.push({ path: `/sources`, query: { id: source.id } })
}

const navigateToSources = () => {
  if (isEditMode.value) return
  router.push({ path: '/sources' })
}

const handleKeydownSource = (event: KeyboardEvent, source: SourceFreshness) => {
  handleKeyboardClick(event, () => navigateToSource(source))
}

const handleKeydownViewAll = (event: KeyboardEvent) => {
  handleKeyboardClick(event, () => navigateToSources())
}

// Summary stats
const summaryStats = computed(() => {
  const fresh = sources.value.filter(s => s.freshness === 'fresh').length
  const stale = sources.value.filter(s => s.freshness === 'stale').length
  const outdated = sources.value.filter(s => s.freshness === 'outdated' || s.freshness === 'never').length
  return { fresh, stale, outdated }
})
</script>

<style scoped>
.summary-bar {
  background-color: rgba(var(--v-theme-on-surface), 0.05);
}

.sources-list {
  max-height: 200px;
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
  padding: 4px;
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
