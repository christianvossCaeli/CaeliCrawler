<script setup lang="ts">
/**
 * StatsCrawler Widget - Shows crawler statistics
 */

import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useDashboardStore } from '@/stores/dashboard'
import { handleKeyboardClick } from '../composables'
import BaseWidget from '../BaseWidget.vue'
import type { WidgetDefinition, WidgetConfig } from '../types'

const props = defineProps<{
  definition: WidgetDefinition
  config?: WidgetConfig
  isEditing?: boolean
}>()

const router = useRouter()
const store = useDashboardStore()
const loading = ref(true)
const error = ref<string | null>(null)

// Computed for reactive isEditing check
const isEditMode = computed(() => props.isEditing ?? false)
const tabIndex = computed(() => (isEditMode.value ? -1 : 0))

const refresh = async () => {
  loading.value = true
  error.value = null
  try {
    await store.loadStats()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load'
  } finally {
    loading.value = false
  }
}

const navigateTo = (status?: string) => {
  if (isEditMode.value) return
  const query: Record<string, string> = {}
  if (status) query.status = status
  router.push({ path: '/crawler', query })
}

const handleKeydown = (event: KeyboardEvent, status?: string) => {
  handleKeyboardClick(event, () => navigateTo(status))
}

onMounted(() => {
  if (!store.stats) {
    refresh()
  } else {
    loading.value = false
  }
})
</script>

<template>
  <BaseWidget
    :definition="definition"
    :config="config"
    :is-editing="isEditing"
    @refresh="refresh"
  >
    <div class="stats-content text-center">
      <div v-if="loading" class="py-4">
        <v-progress-circular indeterminate size="32" />
      </div>

      <template v-else-if="store.stats?.crawler">
        <div
          class="text-h3 font-weight-bold clickable-stat"
          :class="[
            store.stats.crawler.running_jobs > 0 ? 'text-success' : 'text-medium-emphasis',
            { 'non-interactive': isEditMode }
          ]"
          role="button"
          :tabindex="tabIndex"
          :aria-label="$t('dashboard.widgets.statsCrawler.running') + ': ' + store.stats.crawler.running_jobs"
          @click="navigateTo('RUNNING')"
          @keydown="handleKeydown($event, 'RUNNING')"
        >
          {{ store.stats.crawler.running_jobs }}
        </div>
        <div class="text-caption text-medium-emphasis mt-1">
          {{ $t('dashboard.widgets.statsCrawler.running') }}
        </div>

        <v-divider class="my-3" />

        <div class="d-flex justify-space-around text-body-2" role="group" aria-label="Crawler job status breakdown">
          <div
            class="text-center clickable-stat"
            :class="{ 'non-interactive': isEditMode }"
            role="button"
            :tabindex="tabIndex"
            :aria-label="$t('common.completed') + ': ' + store.stats.crawler.completed_jobs"
            @click="navigateTo('COMPLETED')"
            @keydown="handleKeydown($event, 'COMPLETED')"
          >
            <div class="font-weight-medium text-success">
              {{ store.stats.crawler.completed_jobs.toLocaleString() }}
            </div>
            <div class="text-caption text-medium-emphasis">
              {{ $t('common.completed') }}
            </div>
          </div>
          <div
            class="text-center clickable-stat"
            :class="{ 'non-interactive': isEditMode }"
            role="button"
            :tabindex="tabIndex"
            :aria-label="$t('common.failed') + ': ' + store.stats.crawler.failed_jobs"
            @click="navigateTo('FAILED')"
            @keydown="handleKeydown($event, 'FAILED')"
          >
            <div class="font-weight-medium text-error">
              {{ store.stats.crawler.failed_jobs.toLocaleString() }}
            </div>
            <div class="text-caption text-medium-emphasis">
              {{ $t('common.failed') }}
            </div>
          </div>
        </div>
      </template>

      <div v-else class="text-medium-emphasis py-4">
        {{ $t('common.noData') }}
      </div>
    </div>
  </BaseWidget>
</template>

<style scoped>
.stats-content {
  min-height: 100px;
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

.clickable-stat.non-interactive {
  cursor: default;
  pointer-events: none;
}
</style>
