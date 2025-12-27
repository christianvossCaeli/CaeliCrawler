/**
 * Plan Mode Composable
 *
 * This file re-exports all Plan Mode functionality from the planmode submodule
 * for backward compatibility. New code should import directly from:
 *
 * ```ts
 * import { usePlanMode } from '@/composables/planmode'
 * import type { PlanMessage, PlanModeResult } from '@/composables/planmode'
 * ```
 *
 * The planmode submodule provides better organization:
 * - planmode/types.ts: Type definitions and constants
 * - planmode/usePlanModeSSE.ts: SSE streaming logic
 * - planmode/usePlanModeCore.ts: Main composable
 */

// Re-export everything from the planmode module for backward compatibility
export {
  usePlanMode,
  usePlanModeSSE,
  MAX_CONVERSATION_MESSAGES,
  TRIM_THRESHOLD,
  TRIM_TARGET,
  getErrorDetail,
  asAxiosError,
} from './planmode'

export type {
  PlanMessage,
  GeneratedPrompt,
  PlanModeResult,
  ValidationResult,
  SSEEvent,
  AxiosLikeError,
} from './planmode'
