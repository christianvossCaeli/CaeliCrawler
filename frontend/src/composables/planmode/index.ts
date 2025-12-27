/**
 * Plan Mode Module
 *
 * Provides composables for the Plan Mode feature in Smart Query.
 *
 * ```ts
 * import { usePlanMode } from '@/composables/planmode'
 * import type { PlanMessage, PlanModeResult } from '@/composables/planmode'
 * ```
 */

// Main composable
export { usePlanMode } from './usePlanModeCore'

// SSE composable (for advanced use cases)
export { usePlanModeSSE } from './usePlanModeSSE'

// Types
export type {
  PlanMessage,
  GeneratedPrompt,
  PlanModeResult,
  ValidationResult,
  SSEEvent,
  AxiosLikeError,
} from './types'

// Constants and utilities
export {
  MAX_CONVERSATION_MESSAGES,
  TRIM_THRESHOLD,
  TRIM_TARGET,
  getErrorDetail,
  asAxiosError,
} from './types'
