<template>
  <div
    class="smart-query-result"
    role="region"
    :aria-label="visualization?.title || t('result.defaultTitle')"
  >
    <!-- Header with title and source -->
    <header class="result-header mb-4">
      <div class="result-header__title">
        <h3
          :id="headerId"
          class="text-h6 font-weight-bold"
        >
          {{ visualization?.title || t('result.defaultTitle') }}
        </h3>
        <span
          v-if="visualization?.subtitle"
          class="text-body-2 text-medium-emphasis"
          aria-live="polite"
        >
          {{ visualization.subtitle }}
        </span>
      </div>
      <div class="result-header__actions">
        <AiProviderBadge purpose="plan_mode" compact variant="tonal" />
        <SourceInfoChip v-if="sourceInfo" :source-info="sourceInfo" />
      </div>
    </header>

    <!-- Dynamic Visualization with Error Boundary -->
    <div
      class="result-visualization"
      role="presentation"
      :aria-labelledby="headerId"
    >
      <!-- Error fallback when visualization fails -->
      <div
        v-if="renderError"
        class="result-visualization__error"
        role="alert"
        aria-live="assertive"
      >
        <v-icon size="48" color="error" aria-hidden="true">mdi-alert-circle-outline</v-icon>
        <p class="text-body-1 font-weight-medium mt-2">
          {{ t('visualization.errorTitle', 'Visualisierung konnte nicht geladen werden') }}
        </p>
        <p class="text-body-2 text-medium-emphasis mt-1">
          {{ t('visualization.errorDescription', 'Die Daten werden stattdessen als Tabelle angezeigt.') }}
        </p>
        <v-btn
          variant="outlined"
          size="small"
          class="mt-3"
          @click="resetError"
        >
          <v-icon start size="small">mdi-refresh</v-icon>
          {{ t('visualization.retry', 'Erneut versuchen') }}
        </v-btn>
        <!-- Fallback to table visualization -->
        <div class="mt-4">
          <TableVisualization
            :data="data"
            :config="visualization"
          />
        </div>
      </div>
      <!-- Normal visualization rendering -->
      <component
        :is="visualizationComponent"
        v-else-if="visualizationComponent"
        :data="data"
        :config="visualization"
      />
      <div
        v-else
        class="result-visualization__fallback"
        role="status"
        aria-live="polite"
      >
        <v-icon size="48" color="grey-lighten-1" aria-hidden="true">mdi-table</v-icon>
        <p class="text-body-2 text-medium-emphasis mt-2">
          {{ t('visualization.noVisualization') }}
        </p>
      </div>
    </div>

    <!-- Explanation -->
    <v-alert
      v-if="explanation"
      type="info"
      variant="tonal"
      density="compact"
      class="mt-4"
      role="status"
      aria-live="polite"
    >
      <v-icon start size="small" aria-hidden="true">mdi-information-outline</v-icon>
      {{ explanation }}
    </v-alert>

    <!-- Suggested Actions -->
    <SuggestedActionsBar
      v-if="suggestedActions.length > 0"
      :actions="suggestedActions"
      :data="data"
      class="mt-4"
      @action="handleAction"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, ref, onErrorCaptured, type Component } from 'vue'
import { useI18n } from 'vue-i18n'
import { useLogger } from '@/composables/useLogger'
import type {
  VisualizationConfig,
  SourceInfo,
  SuggestedAction,
  VisualizationType,
} from './types'

const props = defineProps<{
  data: Record<string, unknown>[]
  visualization?: VisualizationConfig
  explanation?: string
  sourceInfo?: SourceInfo
  suggestedActions?: SuggestedAction[]
}>()

const emit = defineEmits<{
  action: [action: string, params: Record<string, unknown>]
}>()

const logger = useLogger('SmartQueryResult')

// =============================================================================
// Visualization Components
// =============================================================================

// Always loaded (lightweight, commonly used)
import TableVisualization from './TableVisualization.vue'
import StatCardVisualization from './StatCardVisualization.vue'
import TextVisualization from './TextVisualization.vue'

// Error boundary state
const renderError = ref<Error | null>(null)

// Error handler for async component loading failures
function handleAsyncError(error: Error, _retry: () => void, fail: () => void) {
  logger.error('Failed to load visualization component:', error)
  renderError.value = error
  fail() // Don't retry automatically
}

// Lazy-loaded (heavy, chart.js dependency) with error handling
const BarChartVisualization = defineAsyncComponent({
  loader: () => import('./BarChartVisualization.vue'),
  delay: 100,
  onError: handleAsyncError,
})

const LineChartVisualization = defineAsyncComponent({
  loader: () => import('./LineChartVisualization.vue'),
  delay: 100,
  onError: handleAsyncError,
})

const PieChartVisualization = defineAsyncComponent({
  loader: () => import('./PieChartVisualization.vue'),
  delay: 100,
  onError: handleAsyncError,
})

const ComparisonVisualization = defineAsyncComponent({
  loader: () => import('./ComparisonVisualization.vue'),
  delay: 100,
  onError: handleAsyncError,
})

// Lazy-loaded (heavy, maplibre-gl dependency ~1MB)
const MapVisualization = defineAsyncComponent({
  loader: () => import('./MapVisualization.vue'),
  delay: 200,
  timeout: 15000,
  onError: handleAsyncError,
})

// Lazy-loaded calendar (vue-cal dependency)
const CalendarVisualization = defineAsyncComponent({
  loader: () => import('./CalendarVisualization.vue'),
  delay: 100,
  onError: handleAsyncError,
})

// Capture errors from child components (error boundary)
onErrorCaptured((error, _instance, info) => {
  logger.error('Visualization render error:', { error, info })
  renderError.value = error
  return false // Prevent error from propagating
})

// Common Components
import SourceInfoChip from './common/SourceInfoChip.vue'
import SuggestedActionsBar from './common/SuggestedActionsBar.vue'
import AiProviderBadge from '@/components/common/AiProviderBadge.vue'

const { t } = useI18n()

// Generate unique ID for accessibility
const headerId = computed(() => {
  const title = props.visualization?.title || 'result'
  const slug = title.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 30)
  return `viz-header-${slug}-${Math.random().toString(36).slice(2, 8)}`
})

// Map visualization types to components
const visualizationComponents: Record<VisualizationType, Component> = {
  table: TableVisualization,
  bar_chart: BarChartVisualization,
  line_chart: LineChartVisualization,
  pie_chart: PieChartVisualization,
  stat_card: StatCardVisualization,
  text: TextVisualization,
  comparison: ComparisonVisualization,
  map: MapVisualization,
  calendar: CalendarVisualization,
  heatmap: TableVisualization, // Fallback to table for now
}

const visualizationComponent = computed(() => {
  const type = props.visualization?.type || 'table'
  return visualizationComponents[type] || TableVisualization
})

const suggestedActions = computed(() => props.suggestedActions || [])

// Reset error state to retry visualization
function resetError() {
  renderError.value = null
}

function handleAction(action: string, params: Record<string, unknown>) {
  emit('action', action, params)
}
</script>

<style scoped>
.smart-query-result {
  background: rgb(var(--v-theme-surface));
  border-radius: 12px;
  padding: 20px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 12px;
}

.result-header__title {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.result-header__actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.result-visualization {
  min-height: 200px;
}

.result-visualization__fallback {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  background: rgba(var(--v-theme-surface-variant), 0.3);
  border-radius: 8px;
}

.result-visualization__error {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 24px;
  background: rgba(var(--v-theme-error), 0.05);
  border: 1px solid rgba(var(--v-theme-error), 0.2);
  border-radius: 8px;
}
</style>
