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
 * Trim conversation array to prevent memory leaks.
 * Keeps first message and most recent messages up to TRIM_TARGET.
 *
 * @param messages - Array of messages to trim
 * @returns Trimmed array if above threshold, original array otherwise
 */
export function trimConversationArray<T>(messages: T[]): T[] {
  if (messages.length > TRIM_THRESHOLD) {
    const firstMessage = messages[0]
    const recentMessages = messages.slice(-(TRIM_TARGET - 1))
    return [firstMessage, ...recentMessages]
  }
  return messages
}

/**
 * Helper for type-safe error handling
 * Re-exported from centralized error utilities
 */
export { getErrorMessage as getErrorDetail } from '@/utils/errorMessage'

/**
 * Cast unknown error to AxiosLikeError
 */
export function asAxiosError(err: unknown): AxiosLikeError | null {
  if (err && typeof err === 'object') {
    return err as AxiosLikeError
  }
  return null
}
