<script setup lang="ts">
/**
 * CrawlerStatus Widget - Shows live crawler status and recent jobs
 */

import { ref, onMounted, onUnmounted, computed } from 'vue'
import { adminApi } from '@/services/api'
import BaseWidget from '../BaseWidget.vue'
import type { WidgetDefinition, WidgetConfig } from '../types'

const props = defineProps<{
  definition: WidgetDefinition
  config?: WidgetConfig
  isEditing?: boolean
}>()

const loading = ref(true)
const status = ref<any>(null)
const runningJobs = ref<any[]>([])
const recentJobs = ref<any[]>([])
let refreshInterval: ReturnType<typeof setInterval> | null = null

const refresh = async () => {
  try {
    const [statusRes, runningRes, jobsRes] = await Promise.all([
      adminApi.getCrawlerStatus(),
      adminApi.getRunningJobs(),
      adminApi.getCrawlerJobs({ per_page: 5, status: 'COMPLETED,FAILED' }),
    ])
    status.value = statusRes.data
    runningJobs.value = runningRes.data || []
    recentJobs.value = jobsRes.data?.items || []
  } catch (e) {
    console.error('Failed to load crawler status:', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  refresh()
  // Auto-refresh every 10 seconds
  refreshInterval = setInterval(refresh, 10000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})

const hasRunningJobs = computed(() => runningJobs.value.length > 0)

const getStatusColor = (jobStatus: string): string => {
  const colorMap: Record<string, string> = {
    RUNNING: 'info',
    COMPLETED: 'success',
    FAILED: 'error',
    CANCELLED: 'warning',
    PENDING: 'grey',
  }
  return colorMap[jobStatus] || 'grey'
}

const getStatusIcon = (jobStatus: string): string => {
  const iconMap: Record<string, string> = {
    RUNNING: 'mdi-sync mdi-spin',
    COMPLETED: 'mdi-check-circle',
    FAILED: 'mdi-alert-circle',
    CANCELLED: 'mdi-cancel',
    PENDING: 'mdi-clock-outline',
  }
  return iconMap[jobStatus] || 'mdi-help-circle'
}
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
      <!-- Status Summary -->
      <div class="d-flex justify-space-around mb-4 pa-2 stat-summary rounded">
        <div class="text-center">
          <div class="text-h6">{{ status?.worker_count || 0 }}</div>
          <div class="text-caption">{{ $t('dashboard.workers') }}</div>
        </div>
        <v-divider vertical />
        <div class="text-center">
          <div class="text-h6 text-info">{{ status?.running_jobs || 0 }}</div>
          <div class="text-caption">{{ $t('dashboard.running') }}</div>
        </div>
        <v-divider vertical />
        <div class="text-center">
          <div class="text-h6">{{ status?.pending_jobs || 0 }}</div>
          <div class="text-caption">{{ $t('dashboard.pending') }}</div>
        </div>
      </div>

      <!-- Running Jobs -->
      <template v-if="hasRunningJobs">
        <div class="text-subtitle-2 mb-2">
          {{ $t('dashboard.activeJobs') }}
        </div>
        <v-list density="compact" class="mb-3">
          <v-list-item
            v-for="job in runningJobs"
            :key="job.id"
            class="px-2"
          >
            <template #prepend>
              <v-icon icon="mdi-sync mdi-spin" color="info" size="small" />
            </template>
            <v-list-item-title class="text-body-2">
              {{ job.source_name }}
            </v-list-item-title>
            <v-list-item-subtitle class="text-caption">
              {{ job.documents_found || 0 }} {{ $t('common.documents') }}
            </v-list-item-subtitle>
          </v-list-item>
        </v-list>
      </template>

      <!-- Recent Jobs -->
      <div class="text-subtitle-2 mb-2">
        {{ $t('dashboard.recentJobs') }}
      </div>
      <v-list v-if="recentJobs.length > 0" density="compact">
        <v-list-item
          v-for="job in recentJobs"
          :key="job.id"
          class="px-2"
        >
          <template #prepend>
            <v-icon
              :icon="getStatusIcon(job.status)"
              :color="getStatusColor(job.status)"
              size="small"
            />
          </template>
          <v-list-item-title class="text-body-2">
            {{ job.source_name }}
          </v-list-item-title>
          <v-list-item-subtitle class="text-caption">
            {{ job.documents_found || 0 }} {{ $t('common.documents') }}
          </v-list-item-subtitle>
        </v-list-item>
      </v-list>

      <div v-else class="text-center text-medium-emphasis py-4">
        {{ $t('dashboard.noRecentJobs') }}
      </div>
    </template>
  </BaseWidget>
</template>

<style scoped>
.stat-summary {
  background-color: rgba(var(--v-theme-on-surface), 0.05);
}
</style>
