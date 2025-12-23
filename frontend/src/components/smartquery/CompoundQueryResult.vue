<template>
  <div
    class="compound-query-result"
    role="region"
    :aria-label="t('compoundQuery.ariaLabel')"
  >
    <!-- Compound Query Header -->
    <header class="compound-header mb-4">
      <h3 class="text-h6 font-weight-bold">{{ t('compoundQuery.results') }}</h3>
      <span class="text-body-2 text-medium-emphasis" aria-live="polite">
        {{ t('compoundQuery.visualizationsCount', { count: visualizations.length }) }}
      </span>
    </header>

    <!-- Visualization Grid -->
    <v-row class="visualization-grid" role="list">
      <v-col
        v-for="viz in visualizations"
        :key="viz.id"
        :cols="12"
        :md="getColSize(visualizations.length)"
        role="listitem"
      >
        <v-card
          class="visualization-card h-100"
          variant="outlined"
          :aria-labelledby="`viz-title-${viz.id}`"
        >
          <v-card-title
            :id="`viz-title-${viz.id}`"
            class="visualization-card__header"
          >
            <v-icon
              v-if="getVisualizationIcon(viz.visualization?.type)"
              class="mr-2"
              size="small"
              :aria-hidden="true"
            >
              {{ getVisualizationIcon(viz.visualization?.type) }}
            </v-icon>
            <span>{{ viz.title }}</span>
            <v-chip
              v-if="viz.data?.length"
              size="x-small"
              class="ml-2"
              color="primary"
              variant="tonal"
            >
              {{ viz.data.length }}
            </v-chip>
          </v-card-title>
          <v-card-text class="visualization-card__content">
            <SmartQueryResult
              :data="viz.data"
              :visualization="viz.visualization"
              :source-info="viz.source_info"
              :explanation="viz.explanation"
              :suggested-actions="[]"
              @action="(action, params) => emit('action', action, { ...params, vizId: viz.id })"
            />
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Combined Explanation -->
    <v-alert
      v-if="explanation"
      type="info"
      variant="tonal"
      density="compact"
      class="mt-4"
    >
      <v-icon start size="small">mdi-information-outline</v-icon>
      {{ explanation }}
    </v-alert>

    <!-- Combined Suggested Actions -->
    <div v-if="suggestedActions && suggestedActions.length > 0" class="mt-4">
      <SuggestedActionsBar
        :actions="suggestedActions"
        :data="allData"
        @action="handleAction"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import SmartQueryResult from './visualizations/SmartQueryResult.vue'
import SuggestedActionsBar from './visualizations/common/SuggestedActionsBar.vue'
import {
  type VisualizationWithData,
  type SuggestedAction,
  getVisualizationIcon,
} from './visualizations/types'

const { t } = useI18n()

const props = defineProps<{
  visualizations: VisualizationWithData[]
  explanation?: string
  suggestedActions?: SuggestedAction[]
}>()

const emit = defineEmits<{
  action: [action: string, params: Record<string, any>]
}>()

// Combine all data from visualizations for export purposes
const allData = computed(() => {
  return props.visualizations.flatMap(v => v.data || [])
})

/**
 * Calculate responsive column size based on number of visualizations.
 * - 1 visualization: full width (12 cols)
 * - 2 visualizations: half width each (6 cols)
 * - 3+ visualizations: third width each (4 cols)
 */
function getColSize(count: number): number {
  if (count === 1) return 12
  if (count === 2) return 6
  return 4
}

function handleAction(action: string, params: Record<string, any>) {
  emit('action', action, params)
}
</script>

<style scoped>
.compound-query-result {
  background: rgb(var(--v-theme-surface));
  border-radius: 12px;
  padding: 20px;
}

.compound-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.1);
  padding-bottom: 16px;
}

.visualization-grid {
  margin: -8px;
}

.visualization-card {
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.visualization-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.visualization-card__header {
  font-size: 1rem;
  font-weight: 600;
  padding: 16px;
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.08);
}

.visualization-card__content {
  padding: 16px;
}

/* Remove nested card background */
.visualization-card__content :deep(.smart-query-result) {
  background: transparent;
  padding: 0;
}

/* Adjust nested header */
.visualization-card__content :deep(.result-header) {
  display: none; /* Hide nested header since we have card title */
}

@media (max-width: 960px) {
  .visualization-grid .v-col {
    flex-basis: 100% !important;
    max-width: 100% !important;
  }
}
</style>
