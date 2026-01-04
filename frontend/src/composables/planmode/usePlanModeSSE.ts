/**
 * Plan Mode SSE Composable
 *
 * Handles Server-Sent Events (SSE) streaming for Plan Mode responses.
 * Uses the shared useSSEStream composable for streaming logic.
 */

import { type Ref, type ComputedRef } from 'vue'
import { useI18n } from 'vue-i18n'
import { useLogger } from '@/composables/useLogger'
import { useSSEStream, SSE_PRESETS, type BaseSSEEvent } from '@/composables/shared'
import type { PlanMessage, PlanModeResult } from './types'
import { MAX_CONVERSATION_MESSAGES, trimConversationArray } from './types'
import type { PageContextData } from '@/composables/assistant/types'

const logger = useLogger('usePlanModeSSE')

/**
 * Plan Mode specific SSE Event
 */
interface PlanModeSSEEvent extends BaseSSEEvent {
  event?: 'start' | 'chunk' | 'done' | 'error'
  data?: string
  partial?: boolean
}

export interface UsePlanModeSSEOptions {
  conversation: Ref<PlanMessage[]>
  loading: Ref<boolean>
  streaming: Ref<boolean>
  error: Ref<string | null>
  results: Ref<PlanModeResult | null>
  pageContext?: ComputedRef<PageContextData | undefined>
}

/**
 * Composable for SSE streaming in Plan Mode
 */
export function usePlanModeSSE(options: UsePlanModeSSEOptions) {
  const { t } = useI18n()
  const { conversation, loading, streaming, error, results, pageContext } = options

  // Use shared SSE streaming
  const { stream, cancel, abortController } = useSSEStream<PlanModeSSEEvent>()

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
   * Analyze response text to detect generated prompts
   */
  function analyzeResponseForPrompt(responseText: string): void {
    if (responseText.includes('**Fertiger Prompt:**') || responseText.includes('**Modus:**')) {
      const promptMatch = responseText.match(/>\s*(.+?)(?:\n\n|\n\*\*)/s)
      const generatedPromptText = promptMatch ? promptMatch[1].trim() : null

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
   * Execute a plan mode query with streaming response
   */
  async function executePlanQueryStream(question: string): Promise<boolean> {
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
    streaming.value = true
    error.value = null

    // Prepare conversation history
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

    // Add placeholder for streaming assistant message
    const assistantMessageIndex = conversation.value.length
    conversation.value.push({
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true,
    })

    let fullContent = ''

    try {
      // Build page context for the request
      const pageContextPayload = pageContext?.value
        ? {
            current_route: pageContext.value.current_route || window.location.pathname,
            view_mode: pageContext.value.view_mode || 'unknown',
            available_features: pageContext.value.available_features || [],
            entity_type: pageContext.value.entity_type,
            entity_id: pageContext.value.entity_id,
            summary_id: pageContext.value.summary_id,
            widget_ids: pageContext.value.widgets?.map((w) => w.id) || [],
            filter_state: pageContext.value.filters
              ? {
                  entity_type: pageContext.value.filters.entity_type,
                  facet_filters: pageContext.value.filters.facet_filters,
                  search_query: pageContext.value.filters.search_query,
                }
              : undefined,
          }
        : undefined

      const result = await stream('/api/v1/analysis/smart-query/stream', {
        body: {
          question,
          conversation_history: conversationHistory,
          page_context: pageContextPayload,
        },
        callbacks: {
          onEvent: (event) => {
            // Normalize event type (Plan Mode uses 'event' field)
            const eventType = event.event || event.type

            switch (eventType) {
              case 'start':
                break

              case 'chunk':
                if (event.data) {
                  fullContent += event.data
                  if (conversation.value[assistantMessageIndex]) {
                    conversation.value[assistantMessageIndex].content = fullContent
                  }
                }
                break

              case 'done':
                if (conversation.value[assistantMessageIndex]) {
                  conversation.value[assistantMessageIndex].isStreaming = false
                }
                analyzeResponseForPrompt(fullContent)
                break

              case 'error':
                if (event.partial && fullContent.length > 0) {
                  if (conversation.value[assistantMessageIndex]) {
                    conversation.value[assistantMessageIndex].isStreaming = false
                    conversation.value[assistantMessageIndex].content =
                      fullContent + '\n\n⚠️ *Antwort wurde aufgrund eines Timeouts abgebrochen*'
                  }
                  error.value = t(
                    'smartQueryView.errors.partialResponse',
                    'Die Antwort wurde nicht vollständig empfangen.'
                  )
                } else {
                  throw new Error(event.data?.toString() || 'Unknown streaming error')
                }
                break
            }
          },
          onError: (err) => {
            logger.error('Streaming error:', err)
          },
        },
        config: SSE_PRESETS.planMode,
      })

      if (result.aborted) {
        const hasPartialContent = fullContent.length > 0

        if (hasPartialContent && conversation.value[assistantMessageIndex]) {
          conversation.value[assistantMessageIndex].isStreaming = false
          conversation.value[assistantMessageIndex].content +=
            '\n\n⚠️ *Antwort wurde aufgrund eines Fehlers abgebrochen*'
        } else {
          // Remove empty assistant message
          if (conversation.value[assistantMessageIndex]?.role === 'assistant') {
            conversation.value.pop()
          }
          // Remove user message
          if (conversation.value[conversation.value.length - 1]?.role === 'user') {
            conversation.value.pop()
          }
        }

        if (result.timedOut) {
          error.value = hasPartialContent
            ? t('smartQueryView.errors.timeoutPartial', 'Zeitüberschreitung - Teilantwort angezeigt')
            : t('smartQueryView.errors.timeout', 'Zeitüberschreitung bei der Anfrage')
        } else {
          error.value = hasPartialContent
            ? t('smartQueryView.errors.cancelledPartial', 'Anfrage abgebrochen - Teilantwort angezeigt')
            : t('smartQueryView.errors.cancelled', 'Anfrage abgebrochen')
        }

        return hasPartialContent
      }

      if (!result.success && result.error) {
        const errMessage = result.error
        if (errMessage.includes('429')) {
          error.value = t('smartQueryView.errors.rateLimited', 'Zu viele Anfragen. Bitte warte einen Moment.')
        } else if (errMessage.includes('5')) {
          error.value = t('smartQueryView.errors.serverError', 'Der Server ist momentan nicht erreichbar.')
        } else {
          error.value = errMessage || t('smartQueryView.errors.queryError', 'Fehler bei der Anfrage')
        }

        // Clean up messages on error
        if (conversation.value[assistantMessageIndex]?.role === 'assistant') {
          conversation.value.pop()
        }
        if (conversation.value[conversation.value.length - 1]?.role === 'user') {
          conversation.value.pop()
        }

        return false
      }

      return true
    } finally {
      loading.value = false
      streaming.value = false
    }
  }

  /**
   * Cancel ongoing streaming request
   */
  function cancelStream(): void {
    cancel()
  }

  return {
    abortController,
    executePlanQueryStream,
    cancelStream,
    analyzeResponseForPrompt,
  }
}
