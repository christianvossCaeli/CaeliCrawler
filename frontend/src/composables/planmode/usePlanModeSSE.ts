/**
 * Plan Mode SSE Composable
 *
 * Handles Server-Sent Events (SSE) streaming for Plan Mode responses.
 */

import { ref, type Ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useLogger } from '@/composables/useLogger'
import type { PlanMessage, PlanModeResult, SSEEvent } from './types'
import { MAX_CONVERSATION_MESSAGES, TRIM_THRESHOLD, TRIM_TARGET, getErrorDetail, asAxiosError } from './types'

const logger = useLogger('usePlanModeSSE')

export interface UsePlanModeSSEOptions {
  conversation: Ref<PlanMessage[]>
  loading: Ref<boolean>
  streaming: Ref<boolean>
  error: Ref<string | null>
  results: Ref<PlanModeResult | null>
}

/**
 * Composable for SSE streaming in Plan Mode
 */
export function usePlanModeSSE(options: UsePlanModeSSEOptions) {
  const { t } = useI18n()
  const { conversation, loading, streaming, error, results } = options

  const abortController = ref<AbortController | null>(null)

  /**
   * Trim conversation to prevent memory leaks
   */
  function trimConversation(): void {
    if (conversation.value.length > TRIM_THRESHOLD) {
      const firstMessage = conversation.value[0]
      const recentMessages = conversation.value.slice(-(TRIM_TARGET - 1))
      conversation.value = [firstMessage, ...recentMessages]
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
    abortController.value = new AbortController()

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

      // Add placeholder for streaming assistant message
      const assistantMessageIndex = conversation.value.length
      conversation.value.push({
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        isStreaming: true,
      })

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
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const eventData: SSEEvent = JSON.parse(line.slice(6))

              switch (eventData.event) {
                case 'start':
                  break

                case 'chunk':
                  if (eventData.data) {
                    fullContent += eventData.data
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
                  if (eventData.partial && fullContent.length > 0) {
                    if (conversation.value[assistantMessageIndex]) {
                      conversation.value[assistantMessageIndex].isStreaming = false
                      conversation.value[assistantMessageIndex].content =
                        fullContent + '\n\n⚠️ *Antwort wurde aufgrund eines Timeouts abgebrochen*'
                    }
                    error.value = t(
                      'smartQueryView.errors.partialResponse',
                      'Die Antwort wurde nicht vollständig empfangen.'
                    )
                    return true
                  }
                  throw new Error(eventData.data || 'Unknown streaming error')
              }
            } catch (parseError) {
              logger.warn('Failed to parse SSE event:', line)
            }
          }
        }
      }

      return true
    } catch (e: unknown) {
      const lastMessage = conversation.value[conversation.value.length - 1]
      const hasPartialContent = Boolean(
        lastMessage?.role === 'assistant' && lastMessage?.content && lastMessage.content.length > 0
      )

      if (hasPartialContent && lastMessage) {
        lastMessage.isStreaming = false
        lastMessage.content += '\n\n⚠️ *Antwort wurde aufgrund eines Fehlers abgebrochen*'
      } else {
        if (lastMessage?.role === 'assistant' && lastMessage?.isStreaming) {
          conversation.value.pop()
        }
        const prevMessage = conversation.value[conversation.value.length - 1]
        if (prevMessage?.role === 'user' && prevMessage?.content === question) {
          conversation.value.pop()
        }
      }

      const axiosErr = asAxiosError(e)
      const errName = e instanceof Error ? e.name : undefined
      if (errName === 'AbortError') {
        if (hasPartialContent) {
          error.value = t('smartQueryView.errors.cancelledPartial', 'Anfrage abgebrochen - Teilantwort angezeigt')
          return true
        }
        error.value = t('smartQueryView.errors.cancelled', 'Anfrage abgebrochen')
        return false
      }

      if (axiosErr?.message?.includes('429')) {
        error.value = t('smartQueryView.errors.rateLimited', 'Zu viele Anfragen. Bitte warte einen Moment.')
      } else if (axiosErr?.message?.includes('5')) {
        error.value = t('smartQueryView.errors.serverError', 'Der Server ist momentan nicht erreichbar.')
      } else {
        error.value = getErrorDetail(e) || t('smartQueryView.errors.queryError', 'Fehler bei der Anfrage')
      }

      return hasPartialContent
    } finally {
      loading.value = false
      streaming.value = false
      abortController.value = null
    }
  }

  /**
   * Cancel ongoing streaming request
   */
  function cancelStream(): void {
    if (abortController.value) {
      abortController.value.abort()
      abortController.value = null
    }
  }

  return {
    abortController,
    executePlanQueryStream,
    cancelStream,
    analyzeResponseForPrompt,
  }
}
