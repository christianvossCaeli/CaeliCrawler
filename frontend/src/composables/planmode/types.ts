/**
 * Plan Mode Type Definitions
 *
 * Shared types for the Plan Mode composables.
 */

/**
 * A message in the plan mode conversation
 */
export interface PlanMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp?: Date
  isStreaming?: boolean
}

/**
 * A generated prompt from plan mode
 */
export interface GeneratedPrompt {
  prompt: string
  suggested_mode?: 'read' | 'write'
}

/**
 * Result from a plan mode query
 */
export interface PlanModeResult {
  success: boolean
  message: string
  has_generated_prompt: boolean
  generated_prompt: string | null
  suggested_mode: 'read' | 'write' | null
  mode: 'plan'
}

/**
 * Result from prompt validation
 */
export interface ValidationResult {
  valid: boolean
  mode: string
  interpretation: Record<string, unknown> | null
  preview: string | null
  warnings: string[]
  original_prompt: string
}

/**
 * SSE Event from streaming endpoint
 */
export interface SSEEvent {
  event: 'start' | 'chunk' | 'done' | 'error'
  data?: string
  partial?: boolean
}

/**
 * Axios-like error interface for type-safe error handling
 */
export interface AxiosLikeError {
  response?: { status?: number; data?: { detail?: string } }
  message?: string
  code?: string
}

// Constants - synced with backend
export const MAX_CONVERSATION_MESSAGES = 20
export const TRIM_THRESHOLD = 25
export const TRIM_TARGET = 20

/**
 * Helper for type-safe error handling
 */
export function getErrorDetail(err: unknown): string | undefined {
  if (err && typeof err === 'object') {
    const e = err as AxiosLikeError
    return e.response?.data?.detail || e.message
  }
  return undefined
}

/**
 * Cast unknown error to AxiosLikeError
 */
export function asAxiosError(err: unknown): AxiosLikeError | null {
  if (err && typeof err === 'object') {
    return err as AxiosLikeError
  }
  return null
}
