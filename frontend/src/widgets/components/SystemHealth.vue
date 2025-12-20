<script setup lang="ts">
/**
 * SystemHealth Widget - Shows AI task and system health status
 */

import { ref, onMounted, computed } from 'vue'
import { useDashboardStore } from '@/stores/dashboard'
import BaseWidget from '../BaseWidget.vue'
import type { WidgetDefinition, WidgetConfig } from '../types'

const props = defineProps<{
  definition: WidgetDefinition
  config?: WidgetConfig
  isEditing?: boolean
}>()

const store = useDashboardStore()
const loading = ref(true)

const refresh = async () => {
  loading.value = true
  try {
    await store.loadStats()
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

  const hasFailures = (crawlerStats.value.failed_jobs > crawlerStats.value.completed_jobs * 0.1) ||
                      (aiStats.value.failed > aiStats.value.completed * 0.1)

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
    active: 'mdi-sync mdi-spin',
    warning: 'mdi-alert',
    unknown: 'mdi-help-circle',
  }
  return iconMap[overallHealth.value] || 'mdi-help-circle'
})
</script>

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
          <v-icon :icon="healthIcon" />
        </template>
        <span class="text-subtitle-2 font-weight-medium">
          {{ $t(`dashboard.health.${overallHealth}`) }}
        </span>
      </v-alert>

      <!-- Stats Grid -->
      <v-row dense>
        <!-- AI Tasks -->
        <v-col cols="6">
          <div class="stat-box pa-2 rounded">
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
          <div class="stat-box pa-2 rounded">
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

<style scoped>
.stat-box {
  min-height: 70px;
  background-color: rgba(var(--v-theme-on-surface), 0.05);
}
</style>
