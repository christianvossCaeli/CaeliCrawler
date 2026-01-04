/**
 * Shared Composables
 *
 * Common composables used across multiple features.
 * These provide centralized, reusable logic to reduce code duplication.
 */

export {
  useSSEStream,
  DEFAULT_SSE_CONFIG,
  SSE_PRESETS,
  type SSEStreamConfig,
  type SSEEventType,
  type BaseSSEEvent,
  type StreamResult,
  type SSEStreamCallbacks,
  type UseSSEStreamReturn,
} from './useSSEStream'

export {
  STREAMING_CONFIG,
  STREAMING_ENDPOINTS,
  getStreamingConfig,
  getStreamingTimeout,
  getMaxMessages,
  getStreamingEndpoint,
  type StreamingMode,
  type StreamingConfig,
} from './streamingConfig'

export {
  useConversationState,
  type BaseMessage,
  type ConversationStateOptions,
  type ExtendedMessage,
} from './useConversationState'
