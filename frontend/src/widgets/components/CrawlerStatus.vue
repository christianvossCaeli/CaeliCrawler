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
      <div class="d-flex justify-space-around mb-4 pa-2 stat-summary rounded" role="group" aria-label="Crawler status summary">
        <div
          class="text-center clickable-stat"
          :class="{ 'non-interactive': isEditing }"
          role="button"
          :tabindex="isEditing ? -1 : 0"
          :aria-label="$t('dashboard.workers') + ': ' + (status?.worker_count || 0)"
          @click="navigateToCrawler()"
          @keydown="handleKeydownStatus($event)"
        >
          <div class="text-h6">{{ status?.worker_count || 0 }}</div>
          <div class="text-caption">{{ $t('dashboard.workers') }}</div>
        </div>
        <v-divider vertical />
        <div
          class="text-center clickable-stat"
          :class="{ 'non-interactive': isEditing }"
          role="button"
          :tabindex="isEditing ? -1 : 0"
          :aria-label="$t('dashboard.running') + ': ' + (status?.running_jobs || 0)"
          @click="navigateToCrawler('RUNNING')"
          @keydown="handleKeydownStatus($event, 'RUNNING')"
        >
          <div class="text-h6 text-info">{{ status?.running_jobs || 0 }}</div>
          <div class="text-caption">{{ $t('dashboard.running') }}</div>
        </div>
        <v-divider vertical />
        <div
          class="text-center clickable-stat"
          :class="{ 'non-interactive': isEditing }"
          role="button"
          :tabindex="isEditing ? -1 : 0"
          :aria-label="$t('dashboard.pending') + ': ' + (status?.pending_jobs || 0)"
          @click="navigateToCrawler('PENDING')"
          @keydown="handleKeydownStatus($event, 'PENDING')"
        >
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
            class="px-2 clickable-item"
            :class="{ 'non-interactive': isEditing }"
            role="button"
            :tabindex="isEditing ? -1 : 0"
            :aria-label="job.source_name + ' - ' + (job.documents_found || 0) + ' ' + $t('common.documents')"
            @click="navigateToJob(job.id)"
            @keydown="handleKeydownJob($event, job.id)"
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
          class="px-2 clickable-item"
          :class="{ 'non-interactive': isEditing }"
          role="button"
          :tabindex="isEditing ? -1 : 0"
          :aria-label="job.source_name + ' - ' + job.status + ' - ' + (job.documents_found || 0) + ' ' + $t('common.documents')"
          @click="navigateToJob(job.id)"
          @keydown="handleKeydownJob($event, job.id)"
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

      <WidgetEmptyState
        v-else
        icon="mdi-spider-web"
        :message="$t('dashboard.noRecentJobs')"
      />
    </template>
  </BaseWidget>
</template>

<script setup lang="ts">
/**
 * CrawlerStatus Widget - Shows live crawler status and recent jobs
 * Auto-refresh is handled by BaseWidget via refreshInterval in registry
 */

import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { adminApi } from '@/services/api'
import { useStatusColors } from '@/composables'
import { handleKeyboardClick } from '../composables'
import BaseWidget from '../BaseWidget.vue'
import WidgetEmptyState from './WidgetEmptyState.vue'
import type { WidgetDefinition, WidgetConfig, CrawlerJob, CrawlerStatusData } from '../types'

const props = defineProps<{
  definition: WidgetDefinition
  config?: WidgetConfig
  isEditing?: boolean
}>()

const { t } = useI18n()
const router = useRouter()
const loading = ref(true)
const error = ref<string | null>(null)
const status = ref<CrawlerStatusData | null>(null)
const runningJobs = ref<CrawlerJob[]>([])
const recentJobs = ref<CrawlerJob[]>([])

const refresh = async () => {
  error.value = null
  const errors: string[] = []

  try {
    const [statusResult, runningResult, jobsResult] = await Promise.allSettled([
      adminApi.getCrawlerStatus(),
      adminApi.getRunningJobs(),
      adminApi.getCrawlerJobs({ per_page: 5, status: 'COMPLETED,FAILED' }),
    ])

    // Handle status result
    if (statusResult.status === 'fulfilled') {
      status.value = statusResult.value.data
    } else {
      errors.push('Status')
    }

    // Handle running jobs result
    if (runningResult.status === 'fulfilled') {
      runningJobs.value = runningResult.value.data || []
    } else {
      errors.push('Running Jobs')
    }

    // Handle recent jobs result
    if (jobsResult.status === 'fulfilled') {
      recentJobs.value = jobsResult.value.data?.items || []
    } else {
      errors.push('Recent Jobs')
    }

    // Set partial error message if some requests failed
    if (errors.length > 0 && errors.length < 3) {
      error.value = t('common.partialLoadError', { components: errors.join(', ') })
    } else if (errors.length === 3) {
      error.value = t('common.loadError')
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : t('common.loadError')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  refresh()
  // Note: Auto-refresh is handled by BaseWidget (refreshInterval: 10000 in registry)
})

const hasRunningJobs = computed(() => runningJobs.value.length > 0)

// Use centralized status colors/icons
const { getStatusColor, getStatusIcon } = useStatusColors()

const navigateToCrawler = (status?: string) => {
  if (props.isEditing) return
  const query: Record<string, string> = {}
  if (status) query.status = status
  router.push({ path: '/crawler', query })
}

const navigateToJob = (jobId: string) => {
  if (props.isEditing) return
  // Navigate to crawler page with job_id to auto-open details
  router.push({ path: '/crawler', query: { job_id: jobId } })
}

const handleKeydownStatus = (event: KeyboardEvent, status?: string) => {
  handleKeyboardClick(event, () => navigateToCrawler(status))
}

const handleKeydownJob = (event: KeyboardEvent, jobId: string) => {
  handleKeyboardClick(event, () => navigateToJob(jobId))
}
</script>

<style scoped>
.stat-summary {
  background-color: rgba(var(--v-theme-on-surface), 0.05);
}

.clickable-stat {
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 8px;
  transition: background-color 0.2s ease;
}

.clickable-stat:hover {
  background-color: rgba(var(--v-theme-on-surface), 0.08);
}

.clickable-stat:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}

.clickable-item {
  cursor: pointer;
  border-radius: 8px;
}

.clickable-item:hover {
  background-color: rgba(var(--v-theme-on-surface), 0.08);
}

.clickable-item:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}

.non-interactive {
  cursor: default;
  pointer-events: none;
}
</style>
