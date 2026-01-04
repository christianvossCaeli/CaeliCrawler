/**
 * Shared Conversation State Composable
 *
 * Provides unified conversation management for Smart Query and KI-Assistant.
 * Reduces code duplication and ensures consistent behavior across features.
 *
 * @example
 * ```ts
 * const {
 *   messages,
 *   isLoading,
 *   error,
 *   addMessage,
 *   clearConversation,
 *   trimConversation,
 * } = useConversationState({ maxMessages: 20 })
 * ```
 */

import { ref, computed, watch } from 'vue'
import { useLogger } from '@/composables/useLogger'
import { getMaxMessages, type StreamingMode } from './streamingConfig'

const logger = useLogger('useConversationState')

/**
 * Base message structure
 */
export interface BaseMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  isStreaming?: boolean
  metadata?: Record<string, unknown>
}

/**
 * Configuration options
 */
export interface ConversationStateOptions {
  /** Maximum messages before trimming (default from streaming config) */
  maxMessages?: number
  /** Streaming mode for configuration */
  mode?: StreamingMode
  /** Storage key for persistence (optional) */
  storageKey?: string
  /** Auto-save to localStorage */
  autoSave?: boolean
}

/**
 * Composable for managing conversation state
 */
export function useConversationState<T extends BaseMessage = BaseMessage>(
  options: ConversationStateOptions = {}
) {
  const {
    maxMessages = getMaxMessages(options.mode ?? 'default'),
    storageKey,
    autoSave = false,
  } = options

  // Core state
  const messages = ref<T[]>([])
  const isLoading = ref(false)
  const isStreaming = ref(false)
  const error = ref<string | null>(null)

  // Computed properties
  const messageCount = computed(() => messages.value.length)
  const lastMessage = computed(() => messages.value[messages.value.length - 1] ?? null)
  const hasMessages = computed(() => messages.value.length > 0)
  const isNearLimit = computed(() => messages.value.length >= maxMessages - 2)

  /**
   * Add a message to the conversation
   */
  function addMessage(message: Omit<T, 'timestamp'> & { timestamp?: Date }): number {
    const fullMessage = {
      ...message,
      timestamp: message.timestamp ?? new Date(),
    } as T

    // Using explicit array push to satisfy Vue's reactive type system
    ;(messages.value as T[]).push(fullMessage)

    // Auto-trim if over limit
    if (messages.value.length > maxMessages) {
      trimConversation()
    }

    return messages.value.length - 1
  }

  /**
   * Update a message by index
   */
  function updateMessage(index: number, updates: Partial<T>): void {
    if (index >= 0 && index < messages.value.length) {
      messages.value[index] = { ...messages.value[index], ...updates }
    }
  }

  /**
   * Remove a message by index
   */
  function removeMessage(index: number): void {
    if (index >= 0 && index < messages.value.length) {
      messages.value.splice(index, 1)
    }
  }

  /**
   * Remove the last message
   */
  function removeLastMessage(): T | undefined {
    return (messages.value as T[]).pop()
  }

  /**
   * Trim conversation to fit within maxMessages
   * Keeps first message (context) and last N messages
   */
  function trimConversation(): void {
    if (messages.value.length <= maxMessages) return

    const before = messages.value.length

    // Keep first 2 messages for context, then the most recent
    const keep = maxMessages - 2
    if (messages.value.length > 2 + keep) {
      messages.value = [
        ...messages.value.slice(0, 2),
        ...messages.value.slice(-(keep)),
      ]
    }

    logger.info(`Trimmed conversation from ${before} to ${messages.value.length} messages`)
  }

  /**
   * Clear all messages
   */
  function clearConversation(): void {
    messages.value = []
    error.value = null
    isLoading.value = false
    isStreaming.value = false

    if (storageKey) {
      try {
        localStorage.removeItem(storageKey)
      } catch (e) {
        logger.warn('Failed to clear conversation from storage', e)
      }
    }
  }

  /**
   * Set loading state
   */
  function setLoading(loading: boolean): void {
    isLoading.value = loading
  }

  /**
   * Set streaming state
   */
  function setStreaming(streaming: boolean): void {
    isStreaming.value = streaming
  }

  /**
   * Set error state
   */
  function setError(errorMessage: string | null): void {
    error.value = errorMessage
  }

  /**
   * Build conversation history for API
   */
  function buildHistory(limit = 10): Array<{ role: string; content: string }> {
    return messages.value.slice(-limit).map((msg) => ({
      role: msg.role,
      content: msg.content,
    }))
  }

  /**
   * Load from localStorage
   */
  function loadFromStorage(): boolean {
    if (!storageKey) return false

    try {
      const stored = localStorage.getItem(storageKey)
      if (stored) {
        const parsed = JSON.parse(stored) as T[]
        messages.value = parsed.map((msg) => ({
          ...msg,
          timestamp: new Date(msg.timestamp),
        }))
        return true
      }
    } catch (e) {
      logger.warn('Failed to load conversation from storage', e)
    }
    return false
  }

  /**
   * Save to localStorage
   */
  function saveToStorage(): void {
    if (!storageKey) return

    try {
      localStorage.setItem(storageKey, JSON.stringify(messages.value))
    } catch (e) {
      logger.warn('Failed to save conversation to storage', e)
    }
  }

  // Auto-save on changes
  if (autoSave && storageKey) {
    watch(messages, saveToStorage, { deep: true })
    loadFromStorage()
  }

  return {
    // State
    messages,
    isLoading,
    isStreaming,
    error,

    // Computed
    messageCount,
    lastMessage,
    hasMessages,
    isNearLimit,

    // Actions
    addMessage,
    updateMessage,
    removeMessage,
    removeLastMessage,
    trimConversation,
    clearConversation,

    // Loading state
    setLoading,
    setStreaming,
    setError,

    // Utilities
    buildHistory,
    loadFromStorage,
    saveToStorage,
  }
}

/**
 * Type helper for extending base message
 */
export type ExtendedMessage<T extends Record<string, unknown>> = BaseMessage & T
