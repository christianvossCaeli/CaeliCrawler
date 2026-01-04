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

      <template v-else-if="store.stats?.documents">
        <div
          class="text-h3 font-weight-bold text-warning clickable-stat"
          :class="{ 'non-interactive': isEditMode }"
          role="button"
          :tabindex="tabIndex"
          :aria-label="$t('dashboard.widgets.statsDocuments.total') + ': ' + store.stats.documents.total"
          @click="navigateTo()"
          @keydown="handleKeydown($event)"
        >
          {{ formatNumber(store.stats.documents.total) }}
        </div>
        <div class="text-caption text-medium-emphasis mt-1">
          {{ $t('dashboard.widgets.statsDocuments.total') }}
        </div>

        <v-divider class="my-3" />

        <!-- Status breakdown -->
        <div class="d-flex justify-center ga-4" role="group" aria-label="Document status breakdown">
          <!-- Completed -->
          <div
            class="text-center clickable-stat"
            :class="{ 'non-interactive': isEditing }"
            role="button"
            :tabindex="isEditing ? -1 : 0"
            :aria-label="$t('dashboard.widgets.statsDocuments.processed') + ': ' + (store.stats.documents.by_status?.COMPLETED || 0)"
            @click="navigateTo('COMPLETED')"
            @keydown="handleKeydown($event, 'COMPLETED')"
          >
            <div class="text-h6 font-weight-medium text-success">
              {{ formatNumber(store.stats.documents.by_status?.COMPLETED) || 0 }}
            </div>
            <div class="text-caption text-medium-emphasis">
              {{ $t('dashboard.widgets.statsDocuments.processed') }}
            </div>
          </div>

          <!-- Filtered (if any) -->
          <div
            v-if="store.stats.documents.by_status?.FILTERED"
            class="text-center clickable-stat"
            :class="{ 'non-interactive': isEditing }"
            role="button"
            :tabindex="isEditing ? -1 : 0"
            :aria-label="$t('dashboard.widgets.statsDocuments.filtered') + ': ' + store.stats.documents.by_status.FILTERED"
            @click="navigateTo('FILTERED')"
            @keydown="handleKeydown($event, 'FILTERED')"
          >
            <div class="text-h6 font-weight-medium text-grey">
              {{ formatNumber(store.stats.documents.by_status.FILTERED) }}
            </div>
            <div class="text-caption text-medium-emphasis">
              {{ $t('dashboard.widgets.statsDocuments.filtered') }}
            </div>
          </div>

          <!-- Pending (if any) -->
          <div
            v-if="store.stats.documents.by_status?.PENDING"
            class="text-center clickable-stat"
            :class="{ 'non-interactive': isEditing }"
            role="button"
            :tabindex="isEditing ? -1 : 0"
            :aria-label="$t('dashboard.widgets.statsDocuments.pending') + ': ' + store.stats.documents.by_status.PENDING"
            @click="navigateTo('PENDING')"
            @keydown="handleKeydown($event, 'PENDING')"
          >
            <div class="text-h6 font-weight-medium text-warning">
              {{ formatNumber(store.stats.documents.by_status.PENDING) }}
            </div>
            <div class="text-caption text-medium-emphasis">
              {{ $t('dashboard.widgets.statsDocuments.pending') }}
            </div>
          </div>

          <!-- Failed (if any) -->
          <div
            v-if="store.stats.documents.by_status?.FAILED"
            class="text-center clickable-stat"
            :class="{ 'non-interactive': isEditing }"
            role="button"
            :tabindex="isEditing ? -1 : 0"
            :aria-label="$t('dashboard.widgets.statsDocuments.failed') + ': ' + store.stats.documents.by_status.FAILED"
            @click="navigateTo('FAILED')"
            @keydown="handleKeydown($event, 'FAILED')"
          >
            <div class="text-h6 font-weight-medium text-error">
              {{ formatNumber(store.stats.documents.by_status.FAILED) }}
            </div>
            <div class="text-caption text-medium-emphasis">
              {{ $t('dashboard.widgets.statsDocuments.failed') }}
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

<script setup lang="ts">
/**
 * StatsDocuments Widget - Shows document processing statistics
 */

import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useDashboardStore } from '@/stores/dashboard'
import { useDateFormatter } from '@/composables'
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
const { formatNumber } = useDateFormatter()
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
  if (status) query.processing_status = status
  router.push({ path: '/documents', query })
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

<style scoped>
.stats-content {
  min-height: 100px;
}

.clickable-stat {
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 8px;
  transition: background-color 0.2s ease, outline 0.2s ease;
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
