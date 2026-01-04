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

      <template v-else-if="store.stats?.facets">
        <div
          class="text-h3 font-weight-bold text-info clickable-stat"
          :class="{ 'non-interactive': isEditMode }"
          role="button"
          :tabindex="tabIndex"
          :aria-label="$t('dashboard.widgets.statsFacets.total') + ': ' + store.stats.facets.total"
          @click="navigateTo()"
          @keydown="handleKeydown($event)"
        >
          {{ formatNumber(store.stats.facets.total) }}
        </div>
        <div class="text-caption text-medium-emphasis mt-1">
          {{ $t('dashboard.widgets.statsFacets.total') }}
        </div>

        <v-divider class="my-3" />

        <div class="d-flex justify-center ga-4" role="group" aria-label="Facet status breakdown">
          <div
            class="text-center clickable-stat"
            :class="{ 'non-interactive': isEditing }"
            role="button"
            :tabindex="isEditing ? -1 : 0"
            :aria-label="$t('dashboard.widgets.statsFacets.verified') + ': ' + store.stats.facets.verified"
            @click="navigateTo(true)"
            @keydown="handleKeydown($event, true)"
          >
            <div class="text-h6 font-weight-medium text-success">
              {{ formatNumber(store.stats.facets.verified) }}
            </div>
            <div class="text-caption text-medium-emphasis">
              {{ $t('dashboard.widgets.statsFacets.verified') }}
            </div>
          </div>
          <div
            class="text-center clickable-stat"
            :class="{ 'non-interactive': isEditMode }"
            role="button"
            :tabindex="tabIndex"
            :aria-label="$t('dashboard.widgets.statsFacets.unverified') + ': ' + unverifiedCount"
            @click="navigateTo(false)"
            @keydown="handleKeydown($event, false)"
          >
            <div class="text-h6 font-weight-medium text-warning">
              {{ formatNumber(unverifiedCount) }}
            </div>
            <div class="text-caption text-medium-emphasis">
              {{ $t('dashboard.widgets.statsFacets.unverified') }}
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
 * StatsFacets Widget - Shows facet value statistics
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

// Computed for unverified count
const unverifiedCount = computed(() => {
  if (!store.stats?.facets) return 0
  return store.stats.facets.total - store.stats.facets.verified
})

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

const navigateTo = (verified?: boolean) => {
  if (isEditMode.value) return
  const query: Record<string, string> = {}
  if (verified !== undefined) query.verified = String(verified)
  router.push({ path: '/results', query })
}

const handleKeydown = (event: KeyboardEvent, verified?: boolean) => {
  handleKeyboardClick(event, () => navigateTo(verified))
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
