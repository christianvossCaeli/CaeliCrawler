/**
 * Smart Query Visualization Components
 *
 * This module exports all visualization components for Smart Query results.
 * Components are dynamically selected based on the visualization type returned
 * by the backend's VisualizationSelector.
 */

// Main result container
export { default as SmartQueryResult } from './SmartQueryResult.vue'

// Visualization types
export { default as TableVisualization } from './TableVisualization.vue'
export { default as BarChartVisualization } from './BarChartVisualization.vue'
export { default as LineChartVisualization } from './LineChartVisualization.vue'
export { default as PieChartVisualization } from './PieChartVisualization.vue'
export { default as StatCardVisualization } from './StatCardVisualization.vue'
export { default as TextVisualization } from './TextVisualization.vue'
export { default as ComparisonVisualization } from './ComparisonVisualization.vue'
export { default as MapVisualization } from './MapVisualization.vue'
export { default as CalendarVisualization } from './CalendarVisualization.vue'

// Common components
export { default as SourceInfoChip } from './common/SourceInfoChip.vue'
export { default as SuggestedActionsBar } from './common/SuggestedActionsBar.vue'

// Types
export * from './types'
