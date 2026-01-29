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

    <template v-else>
      <!-- Overall Status -->
      <v-alert
        :color="healthColor"
        variant="tonal"
        density="compact"
        class="mb-4"
      >
        <template #prepend>
          <v-icon :icon="healthIcon" :class="{ 'icon-spin': overallHealth === 'active' }" />
        </template>
        <span class="text-subtitle-2 font-weight-medium">
          {{ $t(`dashboard.health.${overallHealth}`) }}
        </span>
      </v-alert>

      <!-- Stats Grid -->
      <v-row dense role="group" aria-label="System health statistics">
        <!-- AI Tasks -->
        <v-col cols="6">
          <div
            class="stat-box pa-2 rounded clickable-box"
            :class="{ 'non-interactive': isEditing }"
            role="button"
            :tabindex="isEditing ? -1 : 0"
            :aria-label="$t('dashboard.aiTasks') + ': ' + (aiStats?.running || 0) + ' ' + $t('common.running') + ', ' + (aiStats?.completed || 0) + ' ' + $t('common.done') + ', ' + (aiStats?.failed || 0) + ' ' + $t('common.failed')"
            @click="navigateToResults()"
            @keydown="handleKeydownResults($event)"
          >
            <div class="text-caption text-medium-emphasis mb-1">
              <v-icon size="x-small" class="mr-1">mdi-robot</v-icon>
              {{ $t('dashboard.aiTasks') }}
            </div>
            <div class="d-flex justify-space-between text-body-2">
              <span class="text-info">{{ aiStats?.running || 0 }}</span>
              <span class="text-success">{{ aiStats?.completed || 0 }}</span>
              <span class="text-error">{{ aiStats?.failed || 0 }}</span>
            </div>
            <div class="d-flex justify-space-between text-caption text-medium-emphasis">
              <span>{{ $t('common.running') }}</span>
              <span>{{ $t('common.done') }}</span>
              <span>{{ $t('common.failed') }}</span>
            </div>
          </div>
        </v-col>

        <!-- Crawler -->
        <v-col cols="6">
          <div
            class="stat-box pa-2 rounded clickable-box"
            :class="{ 'non-interactive': isEditing }"
            role="button"
            :tabindex="isEditing ? -1 : 0"
            :aria-label="$t('dashboard.crawler') + ': ' + (crawlerStats?.running_jobs || 0) + ' ' + $t('common.running') + ', ' + (crawlerStats?.completed_jobs || 0) + ' ' + $t('common.done') + ', ' + (crawlerStats?.failed_jobs || 0) + ' ' + $t('common.failed')"
            @click="navigateToCrawler()"
            @keydown="handleKeydownCrawler($event)"
          >
            <div class="text-caption text-medium-emphasis mb-1">
              <v-icon size="x-small" class="mr-1">mdi-web</v-icon>
              {{ $t('dashboard.crawler') }}
            </div>
            <div class="d-flex justify-space-between text-body-2">
              <span class="text-info">{{ crawlerStats?.running_jobs || 0 }}</span>
              <span class="text-success">{{ crawlerStats?.completed_jobs || 0 }}</span>
              <span class="text-error">{{ crawlerStats?.failed_jobs || 0 }}</span>
            </div>
            <div class="d-flex justify-space-between text-caption text-medium-emphasis">
              <span>{{ $t('common.running') }}</span>
              <span>{{ $t('common.done') }}</span>
              <span>{{ $t('common.failed') }}</span>
            </div>
          </div>
        </v-col>
      </v-row>

      <!-- Confidence Score -->
      <div v-if="aiStats?.avg_confidence" class="mt-3 text-center">
        <div class="text-caption text-medium-emphasis">
          {{ $t('dashboard.avgConfidence') }}
        </div>
        <v-progress-linear
          :model-value="aiStats.avg_confidence * 100"
          color="primary"
          height="8"
          rounded
          class="mt-1"
        />
        <div class="text-caption mt-1">
          {{ Math.round(aiStats.avg_confidence * 100) }}%
        </div>
      </div>
    </template>
  </BaseWidget>
</template>

<script setup lang="ts">
/**
 * SystemHealth Widget - Shows AI task and system health status
 */

import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useDashboardStore } from '@/stores/dashboard'
import { handleKeyboardClick } from '../composables'
import BaseWidget from '../BaseWidget.vue'
import type { WidgetDefinition, WidgetConfig } from '../types'
import { FAILURE_RATE_THRESHOLD } from '../types'

const props = defineProps<{
  definition: WidgetDefinition
  config?: WidgetConfig
  isEditing?: boolean
}>()

const { t } = useI18n()
const router = useRouter()
const store = useDashboardStore()
const loading = ref(true)
const error = ref<string | null>(null)

const refresh = async () => {
  loading.value = true
  error.value = null
  try {
    await store.loadStats()
  } catch (e) {
    error.value = e instanceof Error ? e.message : t('common.loadError')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (!store.stats) {
    refresh()
  } else {
    loading.value = false
  }
})

const aiStats = computed(() => store.stats?.ai_tasks)
const crawlerStats = computed(() => store.stats?.crawler)

const overallHealth = computed(() => {
  if (!crawlerStats.value || !aiStats.value) return 'unknown'

  const crawlerFailureRate = crawlerStats.value.completed_jobs > 0
    ? crawlerStats.value.failed_jobs / crawlerStats.value.completed_jobs
    : 0
  const aiFailureRate = aiStats.value.completed > 0
    ? aiStats.value.failed / aiStats.value.completed
    : 0

  const hasFailures = crawlerFailureRate > FAILURE_RATE_THRESHOLD || aiFailureRate > FAILURE_RATE_THRESHOLD

  if (hasFailures) return 'warning'
  if (crawlerStats.value.running_jobs > 0 || aiStats.value.running > 0) return 'active'
  return 'healthy'
})

const healthColor = computed(() => {
  const colorMap: Record<string, string> = {
    healthy: 'success',
    active: 'info',
    warning: 'warning',
    unknown: 'grey',
  }
  return colorMap[overallHealth.value] || 'grey'
})

const healthIcon = computed(() => {
  const iconMap: Record<string, string> = {
    healthy: 'mdi-check-circle',
    active: 'mdi-sync',
    warning: 'mdi-alert',
    unknown: 'mdi-help-circle',
  }
  return iconMap[overallHealth.value] || 'mdi-help-circle'
})

const navigateToCrawler = (status?: string) => {
  if (props.isEditing) return
  const query: Record<string, string> = {}
  if (status) query.status = status
  router.push({ path: '/crawler', query })
}

const navigateToResults = () => {
  if (props.isEditing) return
  router.push({ path: '/results' })
}

const handleKeydownCrawler = (event: KeyboardEvent, status?: string) => {
  handleKeyboardClick(event, () => navigateToCrawler(status))
}

const handleKeydownResults = (event: KeyboardEvent) => {
  handleKeyboardClick(event, () => navigateToResults())
}
</script>

<style scoped>
.stat-box {
  min-height: 70px;
  background-color: rgba(var(--v-theme-on-surface), 0.05);
}

.clickable-box {
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.clickable-box:hover {
  background-color: rgba(var(--v-theme-on-surface), 0.12);
}

.clickable-box:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}

.non-interactive {
  cursor: default;
  pointer-events: none;
}

.icon-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
