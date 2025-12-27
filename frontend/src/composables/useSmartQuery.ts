/**
 * Smart Query Composable
 *
 * This file re-exports all Smart Query functionality from the smartquery submodule
 * for backward compatibility. New code should import directly from:
 *
 * ```ts
 * import { useSmartQuery, useSmartQueryAttachments } from '@/composables/smartquery'
 * import type { QueryMode, SmartQueryResults } from '@/composables/smartquery'
 * ```
 *
 * The smartquery submodule provides better organization:
 * - smartquery/types.ts: Shared type definitions
 * - smartquery/useSmartQueryAttachments.ts: File attachment handling
 * - smartquery/useSmartQueryCore.ts: Main composable logic
 */

// Re-export everything from the smartquery module for backward compatibility
export {
  useSmartQuery,
  useSmartQueryAttachments,
  getErrorDetail,
} from './smartquery'

export type {
  QueryMode,
  AttachmentInfo,
  SmartQueryVisualization,
  SmartQueryAction,
  SmartQueryInterpretation,
  CreatedItem,
  SmartQueryResults,
  SmartQueryPreview,
} from './smartquery'
