/**
 * Streaming Configuration
 *
 * Centralized configuration for all streaming features in the application.
 * Used by Smart Query, Plan Mode, and KI-Assistant.
 *
 * @example
 * ```ts
 * import { STREAMING_CONFIG, getStreamingConfig } from '@/composables/shared/streamingConfig'
 *
 * const config = getStreamingConfig('planMode')
 * console.log(config.timeout) // 130000
 * ```
 */

/**
 * Streaming mode identifiers
 */
export type StreamingMode = 'planMode' | 'assistant' | 'smartQuery' | 'default'

/**
 * Configuration for streaming operations
 */
export interface StreamingConfig {
  /** Timeout in milliseconds (0 = no timeout) */
  timeout: number
  /** Maximum messages in conversation before trimming */
  maxMessages: number
  /** Auto-scroll behavior */
  autoScroll: boolean
  /** Retry configuration */
  retry: {
    enabled: boolean
    maxAttempts: number
    baseDelayMs: number
  }
}

/**
 * Centralized streaming configuration
 */
export const STREAMING_CONFIG: Record<StreamingMode, StreamingConfig> = {
  /**
   * Plan Mode - AI-assisted query planning
   * Longer timeout due to complex reasoning tasks
   */
  planMode: {
    timeout: 130_000, // 130s (slightly longer than backend 120s)
    maxMessages: 20,
    autoScroll: true,
    retry: {
      enabled: true,
      maxAttempts: 2,
      baseDelayMs: 1000,
    },
  },

  /**
   * Assistant - Interactive chat interface
   * Larger conversation history allowed, with frontend timeout as safety net
   */
  assistant: {
    timeout: 180_000, // 180s (3 min) - frontend safety net for stalled connections
    maxMessages: 50,
    autoScroll: true,
    retry: {
      enabled: true,
      maxAttempts: 2,
      baseDelayMs: 1000,
    },
  },

  /**
   * Smart Query - Data retrieval queries
   * Balanced configuration
   */
  smartQuery: {
    timeout: 120_000, // 120s
    maxMessages: 30,
    autoScroll: true,
    retry: {
      enabled: true,
      maxAttempts: 2,
      baseDelayMs: 1000,
    },
  },

  /**
   * Default configuration for new streaming features
   */
  default: {
    timeout: 60_000, // 60s
    maxMessages: 25,
    autoScroll: true,
    retry: {
      enabled: false,
      maxAttempts: 0,
      baseDelayMs: 0,
    },
  },
} as const

/**
 * Get streaming configuration for a specific mode
 */
export function getStreamingConfig(mode: StreamingMode = 'default'): StreamingConfig {
  return STREAMING_CONFIG[mode] ?? STREAMING_CONFIG.default
}

/**
 * Get timeout value for a specific mode
 */
export function getStreamingTimeout(mode: StreamingMode = 'default'): number {
  return getStreamingConfig(mode).timeout
}

/**
 * Get max messages for a specific mode
 */
export function getMaxMessages(mode: StreamingMode = 'default'): number {
  return getStreamingConfig(mode).maxMessages
}

/**
 * API endpoint paths for streaming
 */
export const STREAMING_ENDPOINTS = {
  planMode: '/api/v1/analysis/smart-query/stream',
  assistant: '/api/v1/assistant/chat/stream',
  smartQuery: '/api/v1/analysis/smart-query/stream',
} as const

/**
 * Get streaming endpoint for a mode
 */
export function getStreamingEndpoint(mode: Exclude<StreamingMode, 'default'>): string {
  return STREAMING_ENDPOINTS[mode]
}
