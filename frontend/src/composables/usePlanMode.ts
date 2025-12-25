/**
 * Plan Mode Composable
 *
 * Provides reactive state and methods for the Plan Mode feature in Smart Query.
 * Plan Mode is an interactive assistant that helps users formulate the correct
 * prompts for Smart Query operations.
 */

import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '@/services/api'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger('usePlanMode')

// Types
export interface PlanMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp?: Date
  isStreaming?: boolean
}

export interface GeneratedPrompt {
  prompt: string
  suggested_mode?: 'read' | 'write'
}

export interface PlanModeResult {
  success: boolean
  message: string
  has_generated_prompt: boolean
  generated_prompt: string | null
  suggested_mode: 'read' | 'write' | null
  mode: 'plan'
}

export interface ValidationResult {
  valid: boolean
  mode: string
  interpretation: Record<string, unknown> | null
  preview: string | null
  warnings: string[]
  original_prompt: string
}

// SSE Event Types
interface SSEEvent {
  event: 'start' | 'chunk' | 'done' | 'error'
  data?: string
  partial?: boolean // Indicates if partial content was received before error
}

// Constants - synced with backend (backend/services/smart_query/query_interpreter.py)
const MAX_CONVERSATION_MESSAGES = 20 // Maximum messages (not exchanges) - matches backend sanitize_conversation_messages
const TRIM_THRESHOLD = 25 // Trim when exceeding this to prevent constant trimming
const TRIM_TARGET = 20 // Target length after trimming

export function usePlanMode() {
  const { t } = useI18n()

  // State
  const conversation = ref<PlanMessage[]>([])
  const loading = ref(false)
  const streaming = ref(false)
  const error = ref<string | null>(null)
  const results = ref<PlanModeResult | null>(null)
  const abortController = ref<AbortController | null>(null)
  const validating = ref(false)
  const validationResult = ref<ValidationResult | null>(null)

  // Computed
  const hasConversation = computed(() => conversation.value.length > 0)

  const generatedPrompt = computed<GeneratedPrompt | null>(() => {
    if (results.value?.has_generated_prompt && results.value?.generated_prompt) {
      return {
        prompt: results.value.generated_prompt,
        suggested_mode: results.value.suggested_mode ?? undefined,
      }
    }
    return null
  })

  const conversationLength = computed(() => conversation.value.length)

  /**
   * Check if conversation is near the limit
   */
  const isNearLimit = computed(() => conversation.value.length >= MAX_CONVERSATION_MESSAGES - 4)

  /**
   * Trim conversation to prevent memory leaks
   * Keeps first message (context) and last (TRIM_TARGET - 1) messages
   */
  function trimConversation(): void {
    if (conversation.value.length > TRIM_THRESHOLD) {
      const firstMessage = conversation.value[0]
      const recentMessages = conversation.value.slice(-(TRIM_TARGET - 1))
      conversation.value = [firstMessage, ...recentMessages]
      logger.info(`[usePlanMode] Trimmed conversation from ${conversation.value.length + TRIM_THRESHOLD - TRIM_TARGET} to ${conversation.value.length} messages`)
    }
  }

  /**
   * Execute a plan mode query
   */
  async function executePlanQuery(question: string): Promise<boolean> {
    if (!question.trim()) {
      error.value = t('smartQueryView.errors.emptyQuestion', 'Bitte gib eine Frage ein')
      return false
    }

    // Trim conversation proactively to prevent memory leaks
    trimConversation()

    // Enforce conversation length limit
    if (conversation.value.length >= MAX_CONVERSATION_MESSAGES) {
      error.value = t(
        'smartQueryView.errors.conversationTooLong',
        'Die Konversation ist zu lang. Bitte starte eine neue Konversation.'
      )
      return false
    }

    loading.value = true
    error.value = null

    try {
      // Build conversation history (excluding the current question)
      const conversationHistory = conversation.value.map((msg) => ({
        role: msg.role,
        content: msg.content,
      }))

      // Add user message to conversation (optimistic update)
      const userMessage: PlanMessage = {
        role: 'user',
        content: question,
        timestamp: new Date(),
      }
      conversation.value.push(userMessage)

      const response = await api.post('/v1/analysis/smart-query', {
        question,
        allow_write: false,
        mode: 'plan',
        conversation_history: conversationHistory,
      })

      const data = response.data as PlanModeResult

      // Add assistant response to conversation
      if (data.message) {
        conversation.value.push({
          role: 'assistant',
          content: data.message,
          timestamp: new Date(),
        })
      }

      // Store results if a prompt was generated
      if (data.has_generated_prompt && data.generated_prompt) {
        results.value = {
          ...data,
          mode: 'plan',
        }
      } else {
        results.value = null
      }

      return true
    } catch (e: any) {
      // Remove the optimistic user message on error
      const lastMessage = conversation.value[conversation.value.length - 1]
      if (lastMessage?.role === 'user' && lastMessage?.content === question) {
        conversation.value.pop()
      }

      // Set specific error messages based on error type
      if (e.response?.status === 429) {
        error.value = t(
          'smartQueryView.errors.rateLimited',
          'Zu viele Anfragen. Bitte warte einen Moment.'
        )
      } else if (e.response?.status >= 500) {
        error.value = t(
          'smartQueryView.errors.serverError',
          'Der Server ist momentan nicht erreichbar. Bitte versuche es später erneut.'
        )
      } else if (e.code === 'ECONNABORTED' || e.message?.includes('timeout')) {
        error.value = t(
          'smartQueryView.errors.timeout',
          'Die Anfrage hat zu lange gedauert. Bitte versuche es erneut.'
        )
      } else {
        error.value =
          e.response?.data?.detail ||
          e.message ||
          t('smartQueryView.errors.queryError', 'Fehler bei der Anfrage')
      }

      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * Execute a plan mode query with streaming response
   * This provides real-time updates as the AI generates the response
   */
  async function executePlanQueryStream(question: string): Promise<boolean> {
    if (!question.trim()) {
      error.value = t('smartQueryView.errors.emptyQuestion', 'Bitte gib eine Frage ein')
      return false
    }

    // Trim conversation proactively to prevent memory leaks
    trimConversation()

    // Enforce conversation length limit
    if (conversation.value.length >= MAX_CONVERSATION_MESSAGES) {
      error.value = t(
        'smartQueryView.errors.conversationTooLong',
        'Die Konversation ist zu lang. Bitte starte eine neue Konversation.'
      )
      return false
    }

    loading.value = true
    streaming.value = true
    error.value = null

    // Create abort controller for cancellation
    abortController.value = new AbortController()

    try {
      // Build conversation history (excluding the current question)
      const conversationHistory = conversation.value.map((msg) => ({
        role: msg.role,
        content: msg.content,
      }))

      // Add user message to conversation (optimistic update)
      const userMessage: PlanMessage = {
        role: 'user',
        content: question,
        timestamp: new Date(),
      }
      conversation.value.push(userMessage)

      // Add placeholder for streaming assistant message
      const assistantMessageIndex = conversation.value.length
      conversation.value.push({
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        isStreaming: true,
      })

      // Get auth token from api instance
      const token = localStorage.getItem('access_token')

      const response = await fetch('/api/v1/analysis/smart-query/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          question,
          conversation_history: conversationHistory,
        }),
        signal: abortController.value.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('Response body is not readable')
      }

      const decoder = new TextDecoder()
      let buffer = ''
      let fullContent = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // Process SSE events from buffer
        const lines = buffer.split('\n')
        buffer = lines.pop() || '' // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const eventData: SSEEvent = JSON.parse(line.slice(6))

              switch (eventData.event) {
                case 'start':
                  // Stream started
                  break

                case 'chunk':
                  if (eventData.data) {
                    fullContent += eventData.data
                    // Update the assistant message with accumulated content
                    if (conversation.value[assistantMessageIndex]) {
                      conversation.value[assistantMessageIndex].content = fullContent
                    }
                  }
                  break

                case 'done':
                  // Stream completed
                  if (conversation.value[assistantMessageIndex]) {
                    conversation.value[assistantMessageIndex].isStreaming = false
                  }

                  // Check if a prompt was generated
                  analyzeResponseForPrompt(fullContent)
                  break

                case 'error':
                  // Handle error with partial content support
                  if (eventData.partial && fullContent.length > 0) {
                    // Keep partial content but mark as incomplete
                    if (conversation.value[assistantMessageIndex]) {
                      conversation.value[assistantMessageIndex].isStreaming = false
                      // Add timeout indicator to partial content
                      conversation.value[assistantMessageIndex].content =
                        fullContent + '\n\n⚠️ *Antwort wurde aufgrund eines Timeouts abgebrochen*'
                    }
                    // Set warning error instead of throwing
                    error.value = t(
                      'smartQueryView.errors.partialResponse',
                      'Die Antwort wurde nicht vollständig empfangen.'
                    )
                    return true // Return success since we have partial content
                  }
                  throw new Error(eventData.data || 'Unknown streaming error')
              }
            } catch (parseError) {
              // Ignore JSON parse errors for malformed events
              logger.warn('Failed to parse SSE event:', line)
            }
          }
        }
      }

      return true
    } catch (e: any) {
      // Check if we have partial content in the assistant message
      const lastMessage = conversation.value[conversation.value.length - 1]
      const hasPartialContent = Boolean(
        lastMessage?.role === 'assistant' && lastMessage?.content && lastMessage.content.length > 0
      )

      if (hasPartialContent) {
        // Keep partial content but mark as incomplete
        lastMessage!.isStreaming = false
        lastMessage!.content += '\n\n⚠️ *Antwort wurde aufgrund eines Fehlers abgebrochen*'
      } else {
        // Remove empty optimistic messages on error
        if (lastMessage?.role === 'assistant' && lastMessage?.isStreaming) {
          conversation.value.pop()
        }
        const prevMessage = conversation.value[conversation.value.length - 1]
        if (prevMessage?.role === 'user' && prevMessage?.content === question) {
          conversation.value.pop()
        }
      }

      // Handle abort
      if (e.name === 'AbortError') {
        // For abort, we might want to keep partial content
        if (hasPartialContent) {
          error.value = t('smartQueryView.errors.cancelledPartial', 'Anfrage abgebrochen - Teilantwort angezeigt')
          return true // Return true since we have partial content
        }
        error.value = t('smartQueryView.errors.cancelled', 'Anfrage abgebrochen')
        return false
      }

      // Set specific error messages
      if (e.message?.includes('429')) {
        error.value = t(
          'smartQueryView.errors.rateLimited',
          'Zu viele Anfragen. Bitte warte einen Moment.'
        )
      } else if (e.message?.includes('5')) {
        error.value = t(
          'smartQueryView.errors.serverError',
          'Der Server ist momentan nicht erreichbar. Bitte versuche es später erneut.'
        )
      } else {
        error.value = e.message || t('smartQueryView.errors.queryError', 'Fehler bei der Anfrage')
      }

      // Return true if we have partial content to display
      return hasPartialContent
    } finally {
      loading.value = false
      streaming.value = false
      abortController.value = null
    }
  }

  /**
   * Analyze the response text to detect if a prompt was generated
   */
  function analyzeResponseForPrompt(responseText: string): void {
    // Look for the "Fertiger Prompt:" pattern in the response
    if (responseText.includes('**Fertiger Prompt:**') || responseText.includes('**Modus:**')) {
      // Extract the prompt (between > markers or after "Fertiger Prompt:")
      const promptMatch = responseText.match(/>\s*(.+?)(?:\n\n|\n\*\*)/s)
      const generatedPromptText = promptMatch ? promptMatch[1].trim() : null

      // Detect suggested mode
      let suggestedMode: 'read' | 'write' | null = null
      if (responseText.includes('Lese-Modus') || responseText.includes('Read')) {
        suggestedMode = 'read'
      } else if (responseText.includes('Schreib-Modus') || responseText.includes('Write')) {
        suggestedMode = 'write'
      }

      if (generatedPromptText) {
        results.value = {
          success: true,
          message: responseText,
          has_generated_prompt: true,
          generated_prompt: generatedPromptText,
          suggested_mode: suggestedMode,
          mode: 'plan',
        }
      }
    } else {
      results.value = null
    }
  }

  /**
   * Cancel an ongoing streaming request
   */
  function cancelStream(): void {
    if (abortController.value) {
      abortController.value.abort()
      abortController.value = null
    }
  }

  /**
   * Validate a prompt before execution (smoke test)
   * This calls the backend to test if the prompt will be correctly interpreted
   */
  async function validatePrompt(
    prompt: string,
    mode: 'read' | 'write'
  ): Promise<ValidationResult | null> {
    if (!prompt.trim()) {
      error.value = t('smartQueryView.errors.emptyPrompt', 'Der Prompt ist leer')
      return null
    }

    validating.value = true
    validationResult.value = null
    error.value = null

    try {
      const response = await api.post('/v1/analysis/smart-query/validate', {
        prompt,
        mode,
      })

      const result = response.data as ValidationResult
      validationResult.value = result

      return result
    } catch (e: any) {
      error.value =
        e.response?.data?.detail ||
        e.message ||
        t('smartQueryView.errors.validationError', 'Fehler bei der Validierung')
      return null
    } finally {
      validating.value = false
    }
  }

  /**
   * Clear validation result
   */
  function clearValidation(): void {
    validationResult.value = null
  }

  /**
   * Reset the plan mode state
   */
  function reset(): void {
    cancelStream()
    conversation.value = []
    results.value = null
    error.value = null
    loading.value = false
    streaming.value = false
    validating.value = false
    validationResult.value = null
  }

  /**
   * Clear error state
   */
  function clearError(): void {
    error.value = null
  }

  /**
   * Get the conversation for display (with optional message limit)
   */
  function getDisplayConversation(limit?: number): PlanMessage[] {
    if (limit && limit > 0) {
      return conversation.value.slice(-limit)
    }
    return conversation.value
  }

  return {
    // State
    conversation,
    loading,
    streaming,
    error,
    results,
    validating,
    validationResult,

    // Computed
    hasConversation,
    generatedPrompt,
    conversationLength,
    isNearLimit,

    // Methods
    executePlanQuery,
    executePlanQueryStream,
    cancelStream,
    validatePrompt,
    clearValidation,
    reset,
    clearError,
    getDisplayConversation,
  }
}
