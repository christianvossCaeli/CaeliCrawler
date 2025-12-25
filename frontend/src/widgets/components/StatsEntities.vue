<script setup lang="ts">
/**
 * StatsEntities Widget - Shows entity statistics
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
    error.value = e instanceof Error ? e.message : 'Failed to load statistics'
  } finally {
    loading.value = false
  }
}

const navigateTo = (isActive?: boolean) => {
  if (isEditMode.value) return
  const query: Record<string, string> = {}
  if (isActive !== undefined) query.is_active = String(isActive)
  router.push({ path: '/entities', query })
}

const handleKeydown = (event: KeyboardEvent, isActive?: boolean) => {
  handleKeyboardClick(event, () => navigateTo(isActive))
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

      <template v-else-if="store.stats?.entities">
        <div
          class="text-h3 font-weight-bold text-primary clickable-stat"
          :class="{ 'non-interactive': isEditMode }"
          role="button"
          :tabindex="tabIndex"
          :aria-label="$t('dashboard.widgets.statsEntities.total') + ': ' + store.stats.entities.total"
          @click="navigateTo()"
          @keydown="handleKeydown($event)"
        >
          {{ store.stats.entities.total.toLocaleString() }}
        </div>
        <div class="text-caption text-medium-emphasis mt-1">
          {{ $t('dashboard.widgets.statsEntities.total') }}
        </div>

        <v-divider class="my-3" />

        <div class="d-flex justify-space-around text-body-2" role="group" aria-label="Entity status breakdown">
          <div
            class="text-center clickable-stat"
            :class="{ 'non-interactive': isEditing }"
            role="button"
            :tabindex="isEditing ? -1 : 0"
            :aria-label="$t('common.active') + ': ' + store.stats.entities.active"
            @click="navigateTo(true)"
            @keydown="handleKeydown($event, true)"
          >
            <div class="font-weight-medium text-success">
              {{ store.stats.entities.active.toLocaleString() }}
            </div>
            <div class="text-caption text-medium-emphasis">
              {{ $t('common.active') }}
            </div>
          </div>
          <div
            class="text-center clickable-stat"
            :class="{ 'non-interactive': isEditing }"
            role="button"
            :tabindex="isEditing ? -1 : 0"
            :aria-label="$t('common.inactive') + ': ' + store.stats.entities.inactive"
            @click="navigateTo(false)"
            @keydown="handleKeydown($event, false)"
          >
            <div class="font-weight-medium text-medium-emphasis">
              {{ store.stats.entities.inactive.toLocaleString() }}
            </div>
            <div class="text-caption text-medium-emphasis">
              {{ $t('common.inactive') }}
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
