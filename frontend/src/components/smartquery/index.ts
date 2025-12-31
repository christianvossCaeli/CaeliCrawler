/**
 * Smart Query Components Barrel Export
 *
 * Provides centralized exports for all smart query related components.
 * Import from '@/components/smartquery' for cleaner imports.
 *
 * @example
 * ```typescript
 * import { SmartQueryInput, SmartQueryResults } from '@/components/smartquery'
 * ```
 */

// Input & Interaction
export { default as SmartQueryInput } from './SmartQueryInput.vue'
export { default as SmartQueryInputCard } from './SmartQueryInputCard.vue'
export { default as SmartQueryToolbar } from './SmartQueryToolbar.vue'
export { default as SmartQueryExamples } from './SmartQueryExamples.vue'

// Results Display
export { default as SmartQueryResults } from './SmartQueryResults.vue'
export { default as SmartQueryWriteResults } from './SmartQueryWriteResults.vue'
export { default as SmartQueryPreview } from './SmartQueryPreview.vue'
export { default as CompoundQueryResult } from './CompoundQueryResult.vue'

// Layout & Navigation
export { default as SmartQueryHistoryPanel } from './SmartQueryHistoryPanel.vue'
export { default as SmartQuerySidebar } from './SmartQuerySidebar.vue'

// Progress & Feedback
export { default as SmartQueryGenerationProgress } from './SmartQueryGenerationProgress.vue'

// Plan Mode
export { default as PlanModeChat } from './PlanModeChat.vue'

// Re-export visualizations
export * from './visualizations'
