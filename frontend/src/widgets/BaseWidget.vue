<script setup lang="ts">
/**
 * BaseWidget - Wrapper component for all dashboard widgets
 *
 * Provides consistent styling, loading states, error handling,
 * and refresh functionality for all widget types.
 */

import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { WidgetDefinition, WidgetConfig } from './types'

const props = defineProps<{
  definition: WidgetDefinition
  config?: WidgetConfig
  isEditing?: boolean
}>()

const emit = defineEmits<{
  refresh: []
  configure: []
}>()

const { t } = useI18n()

// State
const loading = ref(false)
const error = ref<string | null>(null)
const lastRefresh = ref<Date | null>(null)
let refreshTimer: ReturnType<typeof setInterval> | null = null

// Computed
const widgetTitle = computed(() => t(props.definition.name))
const widgetDescription = computed(() => t(props.definition.description))

const hasRefreshInterval = computed(
  () => props.definition.refreshInterval && props.definition.refreshInterval > 0
)

const timeSinceRefresh = computed(() => {
  if (!lastRefresh.value) return null
  const seconds = Math.floor(
    (Date.now() - lastRefresh.value.getTime()) / 1000
  )
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  return `${minutes}m`
})

// Methods
const refresh = async () => {
  loading.value = true
  error.value = null
  try {
    emit('refresh')
    lastRefresh.value = new Date()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Unknown error'
  } finally {
    loading.value = false
  }
}

const setupAutoRefresh = () => {
  if (hasRefreshInterval.value && props.definition.refreshInterval) {
    refreshTimer = setInterval(refresh, props.definition.refreshInterval)
  }
}

const clearAutoRefresh = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

// Lifecycle
onMounted(() => {
  setupAutoRefresh()
})

onUnmounted(() => {
  clearAutoRefresh()
})

// Watch for changes in refresh interval
watch(
  () => props.definition.refreshInterval,
  () => {
    clearAutoRefresh()
    setupAutoRefresh()
  }
)

// Expose methods for parent components
defineExpose({
  refresh,
  setLoading: (value: boolean) => {
    loading.value = value
  },
  setError: (message: string | null) => {
    error.value = message
  },
})
</script>

<template>
  <v-card
    :class="['widget-card', { 'widget-editing': isEditing }]"
    :elevation="isEditing ? 4 : 1"
    rounded="lg"
  >
    <v-card-title class="d-flex align-center py-2 px-3">
      <v-icon :icon="definition.icon" size="small" class="mr-2" />
      <span class="text-subtitle-2 font-weight-medium">{{ widgetTitle }}</span>

      <v-spacer />

      <v-tooltip v-if="timeSinceRefresh" location="bottom">
        <template #activator="{ props: tooltipProps }">
          <v-chip
            v-bind="tooltipProps"
            size="x-small"
            variant="text"
            class="text-caption text-medium-emphasis"
          >
            {{ timeSinceRefresh }}
          </v-chip>
        </template>
        {{ $t('dashboard.lastUpdated') }}
      </v-tooltip>

      <v-btn
        icon
        size="x-small"
        variant="text"
        :loading="loading"
        @click="refresh"
      >
        <v-icon size="small">mdi-refresh</v-icon>
      </v-btn>

      <v-btn
        v-if="definition.configurable"
        icon
        size="x-small"
        variant="text"
        @click="emit('configure')"
      >
        <v-icon size="small">mdi-cog</v-icon>
      </v-btn>
    </v-card-title>

    <v-divider />

    <v-card-text class="widget-content pa-3">
      <!-- Loading State -->
      <div v-if="loading && !$slots.default" class="d-flex justify-center py-4">
        <v-progress-circular indeterminate size="32" />
      </div>

      <!-- Error State -->
      <v-alert
        v-else-if="error"
        type="error"
        density="compact"
        variant="tonal"
        class="mb-0"
      >
        {{ error }}
        <template #append>
          <v-btn size="small" variant="text" @click="refresh">
            {{ $t('common.retry') }}
          </v-btn>
        </template>
      </v-alert>

      <!-- Content -->
      <slot v-else :loading="loading" :refresh="refresh" />
    </v-card-text>

    <!-- Edit Mode Overlay -->
    <v-overlay
      v-if="isEditing"
      :model-value="true"
      contained
      persistent
      class="align-center justify-center edit-overlay"
    >
      <v-icon size="32" class="text-medium-emphasis">mdi-drag</v-icon>
    </v-overlay>
  </v-card>
</template>

<style scoped>
.widget-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: box-shadow 0.2s ease;
}

.widget-card:hover {
  box-shadow: 0 4px 12px rgba(var(--v-theme-on-surface), 0.15);
}

.widget-editing {
  cursor: grab;
  border: 2px dashed rgba(var(--v-theme-primary), 0.3);
}

.widget-editing:active {
  cursor: grabbing;
}

.widget-content {
  flex: 1;
  overflow: auto;
  min-height: 100px;
}

.edit-overlay :deep(.v-overlay__scrim) {
  background-color: rgba(var(--v-theme-surface), 0.7);
}
</style>
