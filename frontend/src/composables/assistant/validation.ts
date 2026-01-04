/**
 * Assistant Stream Validation
 *
 * Runtime validation schemas for SSE stream events using Zod.
 * Provides type-safe parsing of stream data with proper error handling.
 */

import { z } from 'zod'

/**
 * Schema for SSE stream events
 */
export const StreamEventSchema = z.discriminatedUnion('type', [
  // Status update
  z.object({
    type: z.literal('status'),
    message: z.string().optional(),
  }),

  // Intent classification
  z.object({
    type: z.literal('intent'),
    intent: z.string().optional(),
    confidence: z.number().optional(),
  }),

  // Token for streaming content
  z.object({
    type: z.literal('token'),
    content: z.string().optional(),
  }),

  // Individual result item
  z.object({
    type: z.literal('item'),
    data: z.record(z.unknown()).optional(),
  }),

  // Complete response
  z.object({
    type: z.literal('complete'),
    data: z.union([
      // Wrapped format: { response: ResponseData, suggested_actions: [...] }
      z.object({
        response: z.record(z.unknown()).optional(),
        suggested_actions: z.array(z.object({
          label: z.string(),
          action: z.string(),
          value: z.string(),
        })).optional(),
      }),
      // Direct ResponseData format
      z.record(z.unknown()),
    ]).optional(),
  }),

  // Error response
  z.object({
    type: z.literal('error'),
    message: z.string().optional(),
    error_code: z.string().optional(),
    data: z.unknown().optional(),
  }),
])

/**
 * Inferred type from the schema
 */
export type StreamEvent = z.infer<typeof StreamEventSchema>

/**
 * Validation result type
 */
export interface ValidationResult<T> {
  success: boolean
  data?: T
  error?: z.ZodError
}

/**
 * Validate a parsed stream event
 *
 * @param data - The parsed JSON data from the stream
 * @returns Validation result with typed data or error
 *
 * @example
 * ```ts
 * const result = validateStreamEvent(JSON.parse(dataStr))
 * if (result.success) {
 *   // result.data is now type-safe StreamEvent
 *   switch (result.data.type) {
 *     case 'token':
 *       streamingContent.value += result.data.content || ''
 *       break
 *     case 'complete':
 *       // Handle complete with full type safety
 *       break
 *   }
 * } else {
 *   logger.warn('Invalid stream event:', result.error)
 * }
 * ```
 */
export function validateStreamEvent(data: unknown): ValidationResult<StreamEvent> {
  const result = StreamEventSchema.safeParse(data)

  if (result.success) {
    return { success: true, data: result.data }
  }

  return { success: false, error: result.error }
}

/**
 * Schema for stored conversation messages in localStorage
 */
export const StoredMessageSchema = z.object({
  role: z.enum(['user', 'assistant']),
  content: z.string(),
  timestamp: z.string(),
  metadata: z.record(z.unknown()).optional(),
  response_type: z.string().optional(),
  response_data: z.record(z.unknown()).optional(),
})

/**
 * Schema for stored message array
 */
export const StoredMessagesArraySchema = z.array(StoredMessageSchema)

/**
 * Inferred type for stored message
 */
export type StoredMessage = z.infer<typeof StoredMessageSchema>

/**
 * Validate stored messages from localStorage
 *
 * @param data - Raw data from localStorage
 * @returns Validation result with typed data or error
 */
export function validateStoredMessages(data: unknown): ValidationResult<StoredMessage[]> {
  const result = StoredMessagesArraySchema.safeParse(data)

  if (result.success) {
    return { success: true, data: result.data }
  }

  return { success: false, error: result.error }
}

/**
 * Schema for stored query history item
 */
export const StoredQueryHistoryItemSchema = z.object({
  id: z.string(),
  query: z.string(),
  timestamp: z.string(),
  resultCount: z.number(),
  queryType: z.enum(['read', 'write', 'plan']),
  isFavorite: z.boolean(),
  entityType: z.string().optional(),
  facetTypes: z.array(z.string()).optional(),
})

/**
 * Schema for stored query history array
 */
export const StoredQueryHistoryArraySchema = z.array(StoredQueryHistoryItemSchema)

/**
 * Inferred type for stored query history item
 */
export type StoredQueryHistoryItem = z.infer<typeof StoredQueryHistoryItemSchema>

/**
 * Validate stored query history from localStorage
 *
 * @param data - Raw data from localStorage
 * @returns Validation result with typed data or error
 */
export function validateStoredQueryHistory(data: unknown): ValidationResult<StoredQueryHistoryItem[]> {
  const result = StoredQueryHistoryArraySchema.safeParse(data)

  if (result.success) {
    return { success: true, data: result.data }
  }

  return { success: false, error: result.error }
}
