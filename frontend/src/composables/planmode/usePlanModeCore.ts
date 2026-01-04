/**
 * Plan Mode Core Composable
 *
 * Main composable for Plan Mode functionality. Composes with usePlanModeSSE
 * for streaming support.
 */

import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '@/services/api'
import { usePlanModeSSE } from './usePlanModeSSE'
import type { PlanMessage, PlanModeResult, GeneratedPrompt, ValidationResult } from './types'
import { MAX_CONVERSATION_MESSAGES, trimConversationArray, getErrorDetail, asAxiosError } from './types'
import { useLogger } from '@/composables/useLogger'
import { useCurrentPageContext } from '@/composables/usePageContext'

const logger = useLogger('usePlanModeCore')

/**
 * Main Plan Mode composable
 */
export function usePlanMode() {
  const { t } = useI18n()

  // Core state
  const conversation = ref<PlanMessage[]>([])
  const loading = ref(false)
  const streaming = ref(false)
  const error = ref<string | null>(null)
  const results = ref<PlanModeResult | null>(null)
  const validating = ref(false)
  const validationResult = ref<ValidationResult | null>(null)

  // Get current page context for context-aware responses
  const currentPageContext = useCurrentPageContext()

  // Compose with SSE module
  const sse = usePlanModeSSE({
    conversation,
    loading,
    streaming,
    error,
    results,
    pageContext: currentPageContext,
  })

  // Computed properties
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

  const isNearLimit = computed(() => conversation.value.length >= MAX_CONVERSATION_MESSAGES - 4)

  /**
   * Trim conversation to prevent memory leaks
   */
  function trimConversation(): void {
    const before = conversation.value.length
    conversation.value = trimConversationArray(conversation.value)
    if (conversation.value.length < before) {
      logger.info(`Trimmed conversation to ${conversation.value.length} messages`)
    }
  }

  /**
   * Execute a plan mode query (non-streaming)
   */
  async function executePlanQuery(question: string): Promise<boolean> {
    if (!question.trim()) {
      error.value = t('smartQueryView.errors.emptyQuestion', 'Bitte gib eine Frage ein')
      return false
    }

    trimConversation()

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
      const conversationHistory = conversation.value.map((msg) => ({
        role: msg.role,
        content: msg.content,
      }))

      // Add user message (optimistic update)
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

      // Add assistant response
      if (data.message) {
        conversation.value.push({
          role: 'assistant',
          content: data.message,
          timestamp: new Date(),
        })
      }

      // Store results if prompt was generated
      if (data.has_generated_prompt && data.generated_prompt) {
        results.value = { ...data, mode: 'plan' }
      } else {
        results.value = null
      }

      return true
    } catch (e: unknown) {
      // Remove optimistic user message on error
      const lastMessage = conversation.value[conversation.value.length - 1]
      if (lastMessage?.role === 'user' && lastMessage?.content === question) {
        conversation.value.pop()
      }

      const axiosErr = asAxiosError(e)
      if (axiosErr?.response?.status === 429) {
        error.value = t('smartQueryView.errors.rateLimited', 'Zu viele Anfragen. Bitte warte einen Moment.')
      } else if (axiosErr?.response?.status && axiosErr.response.status >= 500) {
        error.value = t('smartQueryView.errors.serverError', 'Der Server ist momentan nicht erreichbar.')
      } else if (axiosErr?.code === 'ECONNABORTED' || axiosErr?.message?.includes('timeout')) {
        error.value = t('smartQueryView.errors.timeout', 'Die Anfrage hat zu lange gedauert.')
      } else {
        error.value = getErrorDetail(e) || t('smartQueryView.errors.queryError', 'Fehler bei der Anfrage')
      }

      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * Validate a prompt before execution
   */
  async function validatePrompt(prompt: string, mode: 'read' | 'write'): Promise<ValidationResult | null> {
    if (!prompt.trim()) {
      error.value = t('smartQueryView.errors.emptyPrompt', 'Der Prompt ist leer')
      return null
    }

    validating.value = true
    validationResult.value = null
    error.value = null

    try {
      const response = await api.post('/v1/analysis/smart-query/validate', { prompt, mode })
      const result = response.data as ValidationResult
      validationResult.value = result
      return result
    } catch (e: unknown) {
      error.value = getErrorDetail(e) || t('smartQueryView.errors.validationError', 'Fehler bei der Validierung')
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
   * Reset all state
   */
  function reset(): void {
    sse.cancelStream()
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
   * Get conversation for display
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
    executePlanQueryStream: sse.executePlanQueryStream,
    cancelStream: sse.cancelStream,
    validatePrompt,
    clearValidation,
    reset,
    clearError,
    getDisplayConversation,
  }
}
