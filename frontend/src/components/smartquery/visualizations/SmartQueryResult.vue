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
      <SourceInfoChip v-if="sourceInfo" :source-info="sourceInfo" />
    </header>

    <!-- Dynamic Visualization -->
    <div
      class="result-visualization"
      role="presentation"
      :aria-labelledby="headerId"
    >
      <component
        v-if="visualizationComponent"
        :is="visualizationComponent"
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
import { computed, defineAsyncComponent, type Component } from 'vue'
import { useI18n } from 'vue-i18n'
import type {
  VisualizationConfig,
  SourceInfo,
  SuggestedAction,
  VisualizationType,
} from './types'

// =============================================================================
// Visualization Components
// =============================================================================

// Always loaded (lightweight, commonly used)
import TableVisualization from './TableVisualization.vue'
import StatCardVisualization from './StatCardVisualization.vue'
import TextVisualization from './TextVisualization.vue'

// Lazy-loaded (heavy, chart.js dependency)
const BarChartVisualization = defineAsyncComponent({
  loader: () => import('./BarChartVisualization.vue'),
  delay: 100,
})

const LineChartVisualization = defineAsyncComponent({
  loader: () => import('./LineChartVisualization.vue'),
  delay: 100,
})

const PieChartVisualization = defineAsyncComponent({
  loader: () => import('./PieChartVisualization.vue'),
  delay: 100,
})

const ComparisonVisualization = defineAsyncComponent({
  loader: () => import('./ComparisonVisualization.vue'),
  delay: 100,
})

// Lazy-loaded (heavy, maplibre-gl dependency ~1MB)
const MapVisualization = defineAsyncComponent({
  loader: () => import('./MapVisualization.vue'),
  delay: 200,
  timeout: 15000,
})

// Lazy-loaded calendar (vue-cal dependency)
const CalendarVisualization = defineAsyncComponent({
  loader: () => import('./CalendarVisualization.vue'),
  delay: 100,
})

// Common Components
import SourceInfoChip from './common/SourceInfoChip.vue'
import SuggestedActionsBar from './common/SuggestedActionsBar.vue'

const { t } = useI18n()

const props = defineProps<{
  data: Record<string, any>[]
  visualization?: VisualizationConfig
  explanation?: string
  sourceInfo?: SourceInfo
  suggestedActions?: SuggestedAction[]
}>()

const emit = defineEmits<{
  action: [action: string, params: Record<string, any>]
}>()

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

function handleAction(action: string, params: Record<string, any>) {
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
</style>
