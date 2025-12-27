/**
 * Smart Query Module
 *
 * This module provides all Smart Query composables and types.
 * Import from here for a clean API:
 *
 * ```ts
 * import { useSmartQuery, useSmartQueryAttachments } from '@/composables/smartquery'
 * import type { QueryMode, SmartQueryResults } from '@/composables/smartquery'
 * ```
 */

// Main composable (default export for backward compatibility)
export { useSmartQuery } from './useSmartQueryCore'

// Specialized composables
export { useSmartQueryAttachments } from './useSmartQueryAttachments'

// Types
export type {
  QueryMode,
  AttachmentInfo,
  SmartQueryVisualization,
  SmartQueryAction,
  SmartQueryInterpretation,
  CreatedItem,
  SmartQueryResults,
  SmartQueryPreview,
  LoadingPhase,
  LoadingState,
} from './types'

// Constants and utility functions
export {
  getErrorDetail,
  DEFAULT_LOADING_STATE,
  LOADING_PHASE_MESSAGES,
} from './types'
