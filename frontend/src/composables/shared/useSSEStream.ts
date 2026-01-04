/**
 * Shared SSE Streaming Composable
 *
 * Centralized SSE streaming logic used by both Smart Query Plan Mode and KI-Assistant.
 * Reduces code duplication (~150 LOC) and ensures consistent streaming behavior.
 *
 * @example
 * ```ts
 * const { stream, cancel, isStreaming } = useSSEStream<MyEventType>({
 *   onEvent: (event) => handleEvent(event),
 *   onError: (error) => handleError(error),
 *   timeout: 130_000,
 * })
 *
 * await stream('/api/endpoint', { body: data })
 * ```
 */

import { ref } from 'vue'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger('useSSEStream')

/**
 * Configuration for SSE streaming
 */
export interface SSEStreamConfig {
  /** Timeout in milliseconds (default: 130000 = 130s) */
  timeout?: number
  /** Custom headers to include */
  headers?: Record<string, string>
  /** Include auth token from localStorage */
  includeAuth?: boolean
}

/**
 * Default streaming configuration
 */
export const DEFAULT_SSE_CONFIG: Required<SSEStreamConfig> = {
  timeout: 130_000,
  headers: {},
  includeAuth: true,
}

/**
 * SSE Event types for standardization
 */
export type SSEEventType =
  | 'start'
  | 'status'
  | 'intent'
  | 'chunk'
  | 'token'
  | 'item'
  | 'complete'
  | 'done'
  | 'error'

/**
 * Base SSE Event structure
 */
export interface BaseSSEEvent {
  /** Event type (start, chunk, done, error, etc.) */
  type?: SSEEventType
  /** Alternative event field (for Plan Mode compatibility) */
  event?: SSEEventType
  /** Data/content payload */
  data?: string | unknown
  /** Content field (for token events) */
  content?: string
  /** Message field (for status/error) */
  message?: string
  /** Partial flag for error recovery */
  partial?: boolean
}

/**
 * Streaming result status
 */
export interface StreamResult {
  success: boolean
  aborted: boolean
  timedOut: boolean
  hasPartialContent: boolean
  error?: string
}

/**
 * Callbacks for SSE streaming
 */
export interface SSEStreamCallbacks<T extends BaseSSEEvent = BaseSSEEvent> {
  /** Called for each SSE event */
  onEvent: (event: T) => void
  /** Called on streaming error */
  onError?: (error: Error) => void
  /** Called when streaming starts */
  onStart?: () => void
  /** Called when streaming completes */
  onComplete?: () => void
}

/**
 * Composable return type
 */
export interface UseSSEStreamReturn<T extends BaseSSEEvent = BaseSSEEvent> {
  /** Is currently streaming */
  isStreaming: ReturnType<typeof ref<boolean>>
  /** Current abort controller */
  abortController: ReturnType<typeof ref<AbortController | null>>
  /** Start streaming from URL */
  stream: (
    url: string,
    options: {
      body: unknown
      callbacks: SSEStreamCallbacks<T>
      config?: SSEStreamConfig
    }
  ) => Promise<StreamResult>
  /** Cancel ongoing stream */
  cancel: () => void
}

/**
 * Shared SSE streaming composable
 *
 * Provides a unified interface for SSE streaming with:
 * - Automatic abort controller management
 * - Configurable timeout
 * - Auth token injection
 * - Consistent error handling
 * - Event parsing and normalization
 */
export function useSSEStream<T extends BaseSSEEvent = BaseSSEEvent>(): UseSSEStreamReturn<T> {
  const isStreaming = ref(false)
  const abortController = ref<AbortController | null>(null)

  /**
   * Cancel ongoing streaming request
   */
  function cancel(): void {
    if (abortController.value) {
      abortController.value.abort()
      abortController.value = null
    }
  }

  /**
   * Parse SSE line to event object
   */
  function parseSSELine(line: string): T | null {
    if (!line.startsWith('data: ')) {
      return null
    }

    const dataStr = line.slice(6).trim()

    // Handle [DONE] signal
    if (dataStr === '[DONE]') {
      return { type: 'done' } as T
    }

    try {
      const parsed = JSON.parse(dataStr) as T

      // Normalize event/type field (Plan Mode uses 'event', Assistant uses 'type')
      if (parsed.event && !parsed.type) {
        parsed.type = parsed.event
      }

      return parsed
    } catch (parseError) {
      logger.warn('Failed to parse SSE event:', line)
      return null
    }
  }

  /**
   * Stream from URL with SSE
   */
  async function stream(
    url: string,
    options: {
      body: unknown
      callbacks: SSEStreamCallbacks<T>
      config?: SSEStreamConfig
    }
  ): Promise<StreamResult> {
    const { body, callbacks, config = {} } = options
    const mergedConfig = { ...DEFAULT_SSE_CONFIG, ...config }
    const { onEvent, onError, onStart, onComplete } = callbacks

    // Cancel any existing request
    if (abortController.value) {
      logger.debug('Cancelling previous request before starting new one')
      abortController.value.abort()
    }

    isStreaming.value = true
    abortController.value = new AbortController()

    // Set up timeout
    let timeoutId: ReturnType<typeof setTimeout> | null = null
    if (mergedConfig.timeout > 0) {
      timeoutId = setTimeout(() => {
        if (abortController.value) {
          logger.warn('Streaming timeout reached, aborting request')
          abortController.value.abort(new Error('Streaming timeout'))
        }
      }, mergedConfig.timeout)
    }

    let hasReceivedContent = false

    try {
      // Build headers
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...mergedConfig.headers,
      }

      if (mergedConfig.includeAuth) {
        const token = localStorage.getItem('access_token')
        if (token) {
          headers.Authorization = `Bearer ${token}`
        }
      }

      // Make request
      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
        signal: abortController.value.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('Response body is not readable')
      }

      onStart?.()

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          const event = parseSSELine(line)
          if (event) {
            // Track if we've received any content
            if (event.type === 'chunk' || event.type === 'token') {
              hasReceivedContent = true
            }

            onEvent(event)
          }
        }
      }

      onComplete?.()

      return {
        success: true,
        aborted: false,
        timedOut: false,
        hasPartialContent: hasReceivedContent,
      }
    } catch (e: unknown) {
      const err = e instanceof Error ? e : new Error(String(e))
      const isAbort = err.name === 'AbortError'
      const isTimeout = isAbort && err.message.includes('timeout')

      if (!isAbort) {
        onError?.(err)
      }

      return {
        success: false,
        aborted: isAbort,
        timedOut: isTimeout,
        hasPartialContent: hasReceivedContent,
        error: err.message,
      }
    } finally {
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
      isStreaming.value = false
      abortController.value = null
    }
  }

  return {
    isStreaming,
    abortController,
    stream,
    cancel,
  }
}

/**
 * Streaming configuration presets
 */
export const SSE_PRESETS = {
  /** Plan Mode configuration */
  planMode: {
    timeout: 130_000, // 130s (slightly longer than backend 120s)
    includeAuth: true,
  } satisfies SSEStreamConfig,

  /** Assistant configuration */
  assistant: {
    timeout: 0, // No timeout (handled by backend)
    includeAuth: true,
  } satisfies SSEStreamConfig,
} as const
