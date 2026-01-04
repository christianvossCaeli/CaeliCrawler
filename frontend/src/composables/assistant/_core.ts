/**
 * Assistant Core Composable
 *
 * The main useAssistant composable implementation that combines all sub-composables.
 */

import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { useEntityStore } from '@/stores/entity'
import { useQueryContextStore } from '@/stores/queryContext'
import { assistantApi } from '@/services/api'
import { extractErrorMessage } from '@/utils/errorMessage'
import { useLogger } from '@/composables/useLogger'
import type { AssistantAction } from '@/types/assistant'

// Import sub-composables
import { useAssistantHistory } from './useAssistantHistory'
import { useAssistantAttachments } from './useAssistantAttachments'
import { useAssistantBatch } from './useAssistantBatch'
import { useAssistantWizard } from './useAssistantWizard'
import { useAssistantReminders } from './useAssistantReminders'
import { useAssistantInsights } from './useAssistantInsights'
import { useCurrentPageContext } from '@/composables/usePageContext'

// Import types for internal use
import type {
  AssistantContext,
  ConversationMessage,
  SuggestedAction,
  ResponseData,
} from './types'

// Import validation
import { validateStreamEvent } from './validation'

const logger = useLogger('useAssistant')

/**
 * Main Assistant Composable
 *
 * Combines all sub-composables into a single, cohesive interface.
 */
export function useAssistant() {
  const route = useRoute()
  const router = useRouter()
  const entityStore = useEntityStore()
  const queryContextStore = useQueryContextStore()
  const { locale, t } = useI18n()

  // Get current page context from registered providers
  const currentPageContext = useCurrentPageContext()

  // Core State
  const isOpen = ref(false)
  const isLoading = ref(false)
  const isStreaming = ref(false)
  const streamingContent = ref('')
  const streamingStatus = ref('')
  const messages = ref<ConversationMessage[]>([])
  const error = ref<string | null>(null)
  const mode = ref<'read' | 'write' | 'plan'>('read')
  const suggestedActions = ref<SuggestedAction[]>([])
  const hasUnread = ref(false)
  const pendingAction = ref<AssistantAction | null>(null)
  const useStreaming = ref(true) // Enable streaming by default

  // AbortController for cancelling streaming requests
  const streamingAbortController = ref<AbortController | null>(null)

  // Detect view mode from route
  function detectViewMode(): AssistantContext['view_mode'] {
    const path = route.path

    if (path === '/' || path.includes('dashboard')) {
      return 'dashboard'
    }
    if (path.includes('/summaries') || path.includes('/summary-dashboard')) {
      return 'summary'
    }
    if (route.params.entitySlug) {
      return 'detail'
    }
    if (path.includes('/entities') || path.includes('/sources') || path.includes('/categories')) {
      return 'list'
    }
    return 'unknown'
  }

  // Get available actions for current context
  function getAvailableActions(): string[] {
    const actions: string[] = ['search', 'help', 'navigate']
    const path = route.path

    // Entity detail actions
    if (route.params.entitySlug) {
      actions.push('view_details', 'edit', 'summarize', 'add_facet', 'add_relation')
    }

    // Entity list actions
    if (route.params.typeSlug) {
      actions.push('filter', 'create', 'bulk_edit', 'export')
    }

    // Summary/Dashboard actions
    if (path.includes('/summaries') || path.includes('/summary-dashboard')) {
      actions.push('add_widget', 'edit_widget', 'configure_widget', 'refresh')
    }

    // Category actions
    if (path.includes('/categories')) {
      actions.push('start_crawl', 'view_entities', 'configure')
    }

    // Source actions
    if (path.includes('/sources')) {
      actions.push('add_source', 'test_connection')
    }

    // Smart Query actions
    if (path.includes('/smart-query')) {
      actions.push('execute_query', 'save_query', 'export_results')
    }

    // Crawler actions
    if (path.includes('/crawler')) {
      actions.push('start_job', 'pause_job', 'cancel_job')
    }

    return actions
  }

  // Computed context with page-specific data
  const currentContext = computed<AssistantContext>(() => ({
    current_route: route.fullPath,
    current_entity_id: entityStore.selectedEntity?.id || null,
    current_entity_type: route.params.typeSlug as string || null,
    current_entity_name: entityStore.selectedEntity?.name || null,
    view_mode: detectViewMode(),
    available_actions: getAvailableActions(),
    // Include page-specific context data from registered providers
    page_data: currentPageContext.value
  }))

  // Initialize sub-composables
  const history = useAssistantHistory({ messages })

  const attachments = useAssistantAttachments({
    messages,
    error,
    saveHistory: history.saveHistory,
  })

  const batch = useAssistantBatch({
    messages,
    isLoading,
    error,
    saveHistory: history.saveHistory,
  })

  // Chat control functions
  function toggleChat() {
    isOpen.value = !isOpen.value
    if (isOpen.value) {
      hasUnread.value = false
    }
  }

  function openChat() {
    isOpen.value = true
    hasUnread.value = false
  }

  function closeChat() {
    isOpen.value = false
  }

  // Build conversation history for API
  function buildConversationHistory(): Array<{ role: string; content: string; timestamp: string }> {
    return messages.value.slice(-10).map(msg => ({
      role: msg.role,
      content: msg.content,
      timestamp: msg.timestamp.toISOString()
    }))
  }

  // Send message to assistant (non-streaming)
  async function sendMessage(text: string) {
    if (!text.trim()) return

    // Add user message
    const userMessage: ConversationMessage = {
      role: 'user',
      content: text.trim(),
      timestamp: new Date()
    }
    messages.value.push(userMessage)

    isLoading.value = true
    error.value = null

    try {
      // Ensure language is valid (de or en)
      const lang = (locale.value === 'de' || locale.value === 'en') ? locale.value : 'de'

      // Collect attachment IDs
      const attachmentIds = attachments.pendingAttachments.value.map(a => a.id)

      // Convert 'plan' mode to undefined for API compatibility
      const apiMode = mode.value === 'plan' ? undefined : mode.value
      const response = await assistantApi.chat({
        message: text.trim(),
        context: currentContext.value,
        conversation_history: buildConversationHistory(),
        mode: apiMode,
        language: lang,
        attachment_ids: attachmentIds.length > 0 ? attachmentIds : undefined
      })

      // Clear attachments after successful send
      if (attachmentIds.length > 0) {
        await attachments.clearAttachments()
      }

      const data = response.data

      // Process response
      const responseData = data.response
      const assistantContent = responseData.message || 'Keine Antwort erhalten.'

      // Add assistant message
      const assistantMessage: ConversationMessage = {
        role: 'assistant',
        content: assistantContent,
        timestamp: new Date(),
        response_type: responseData.type,
        response_data: responseData
      }
      messages.value.push(assistantMessage)

      // Update suggested actions
      suggestedActions.value = data.suggested_actions || []

      // Handle special response types
      handleResponseType(responseData)

      // Mark as unread if chat is closed
      if (!isOpen.value) {
        hasUnread.value = true
      }

    } catch (e: unknown) {
      error.value = extractErrorMessage(e)
      const errorMessage: ConversationMessage = {
        role: 'assistant',
        content: `Fehler: ${error.value}`,
        timestamp: new Date(),
        response_type: 'error'
      }
      messages.value.push(errorMessage)
    } finally {
      isLoading.value = false
      history.saveHistory()
    }
  }

  // Cancel ongoing streaming request
  function cancelStreaming() {
    if (streamingAbortController.value) {
      streamingAbortController.value.abort()
      streamingAbortController.value = null
    }
  }

  // Send message with streaming response
  async function sendMessageStream(text: string) {
    if (!text.trim()) return

    // Cancel any ongoing streaming request
    cancelStreaming()

    // Add user message
    const userMessage: ConversationMessage = {
      role: 'user',
      content: text.trim(),
      timestamp: new Date()
    }
    messages.value.push(userMessage)

    isLoading.value = true
    isStreaming.value = true
    streamingContent.value = ''
    streamingStatus.value = ''
    error.value = null

    // Create a new AbortController for this request
    streamingAbortController.value = new AbortController()

    // Create a placeholder assistant message that will be updated
    const assistantMessageIndex = messages.value.length
    const assistantMessage: ConversationMessage = {
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      response_type: 'streaming'
    }
    messages.value.push(assistantMessage)

    try {
      // Ensure language is valid (de or en)
      const lang = (locale.value === 'de' || locale.value === 'en') ? locale.value : 'de'

      // Collect attachment IDs
      const attachmentIds = attachments.pendingAttachments.value.map(a => a.id)

      // Convert 'plan' mode to undefined for API compatibility
      const apiMode = mode.value === 'plan' ? undefined : mode.value
      const response = await assistantApi.chatStream(
        {
          message: text.trim(),
          context: currentContext.value,
          conversation_history: buildConversationHistory(),
          mode: apiMode,
          language: lang,
          attachment_ids: attachmentIds.length > 0 ? attachmentIds : undefined
        },
        streamingAbortController.value.signal
      )

      // Clear attachments after starting request
      if (attachmentIds.length > 0) {
        // Don't await, clear in background
        attachments.clearAttachments()
      }

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('No response body reader available')
      }

      const decoder = new TextDecoder()
      let buffer = ''
      let finalResponseData: ResponseData | null = null

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || '' // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6).trim()

            if (dataStr === '[DONE]') {
              continue
            }

            try {
              const parsed = JSON.parse(dataStr)
              const validationResult = validateStreamEvent(parsed)

              if (!validationResult.success) {
                logger.warn('Invalid stream event:', validationResult.error?.issues)
                continue
              }

              const data = validationResult.data!

              switch (data.type) {
                case 'status':
                  streamingStatus.value = data.message || ''
                  break

                case 'intent':
                  // Intent classified - could show in UI
                  break

                case 'token':
                  // Append token to streaming content
                  streamingContent.value += data.content || ''
                  messages.value[assistantMessageIndex].content = streamingContent.value
                  break

                case 'item':
                  // Individual result item - could render progressively
                  break

                case 'complete': {
                  // Final response data (type-safe access to data.data)
                  const completeWrapper = data.data as { response?: ResponseData; suggested_actions?: SuggestedAction[] } | ResponseData | undefined
                  let responseData: ResponseData | undefined
                  if (completeWrapper && typeof completeWrapper === 'object' && 'response' in completeWrapper) {
                    responseData = (completeWrapper as { response?: ResponseData }).response
                  } else {
                    responseData = completeWrapper as ResponseData | undefined
                  }
                  finalResponseData = {
                    ...(responseData || {}),
                    suggested_actions: (completeWrapper && typeof completeWrapper === 'object' && 'suggested_actions' in completeWrapper)
                      ? completeWrapper.suggested_actions || []
                      : (responseData?.suggested_actions || [])
                  } as ResponseData
                  if (finalResponseData?.message) {
                    messages.value[assistantMessageIndex].content = finalResponseData.message
                  }
                  messages.value[assistantMessageIndex].response_type = finalResponseData?.type || 'query_result'
                  messages.value[assistantMessageIndex].response_data = finalResponseData
                  break
                }

                case 'error':
                  error.value = data.message ?? null
                  messages.value[assistantMessageIndex].content = `Fehler: ${data.message || 'Unbekannter Fehler'}`
                  messages.value[assistantMessageIndex].response_type = 'error'
                  break
              }
            } catch (parseError) {
              logger.error('Failed to parse SSE data:', parseError)
            }
          }
        }
      }

      // Process final response data
      if (finalResponseData) {
        suggestedActions.value = finalResponseData.suggested_actions || []
        handleResponseType(finalResponseData)
      }

      // Mark as unread if chat is closed
      if (!isOpen.value) {
        hasUnread.value = true
      }

    } catch (e: unknown) {
      const err = e as { name?: string; message?: string }
      // Handle abort gracefully - not an error
      if (err.name === 'AbortError') {
        logger.info('Streaming request was cancelled')
        messages.value[assistantMessageIndex].content = t(
          'assistant.streamingCancelled',
          'Anfrage wurde abgebrochen'
        )
        messages.value[assistantMessageIndex].response_type = 'info'
      } else {
        error.value = err.message || 'Fehler bei der Streaming-Kommunikation'
        messages.value[assistantMessageIndex].content = `Fehler: ${error.value}`
        messages.value[assistantMessageIndex].response_type = 'error'
      }
    } finally {
      isLoading.value = false
      isStreaming.value = false
      streamingContent.value = ''
      streamingStatus.value = ''
      streamingAbortController.value = null // Clean up abort controller
      history.saveHistory()
    }
  }

  // Handle special response types
  function handleResponseType(responseData: ResponseData) {
    if (responseData.type === 'action_preview' && responseData.requires_confirmation) {
      pendingAction.value = responseData.action as AssistantAction | null
    } else if (responseData.type === 'navigation') {
      const target = responseData.target
      if (target?.route) {
        suggestedActions.value.unshift({
          label: `Zu ${target.entity_name || 'Seite'} navigieren`,
          action: 'navigate',
          value: target.route
        })
      }
    } else if (responseData.type === 'redirect_to_smart_query') {
      suggestedActions.value.unshift({
        label: 'Smart Query öffnen',
        action: 'redirect',
        value: '/smart-query'
      })
    }
  }

  // Smart send that uses streaming when enabled
  async function send(text: string) {
    // If in plan mode, redirect to Smart Query Plan Mode
    if (mode.value === 'plan') {
      // Add info message to chat
      const infoMessage: ConversationMessage = {
        role: 'assistant',
        content: t('assistant.planModeRedirect'),
        timestamp: new Date(),
        response_type: 'redirect'
      }
      messages.value.push(infoMessage)
      history.saveHistory()

      // Redirect to Smart Query with plan mode
      router.push({
        path: '/smart-query',
        query: {
          mode: 'plan',
          q: text.trim(),
          from: 'assistant'
        }
      })
      closeChat()
      return
    }

    if (useStreaming.value) {
      await sendMessageStream(text)
    } else {
      await sendMessage(text)
    }
  }

  // Execute confirmed action
  async function executeAction(action: AssistantAction) {
    isLoading.value = true
    error.value = null

    try {
      const response = await assistantApi.executeAction({
        action: action,
        context: currentContext.value
      })

      const result = response.data as { message: string; success: boolean; refresh_required?: boolean; affected_entity_id?: string }

      // Add result message
      const resultMessage: ConversationMessage = {
        role: 'assistant',
        content: result.message,
        timestamp: new Date(),
        response_type: result.success ? 'success' : 'error'
      }
      messages.value.push(resultMessage)

      // Clear pending action
      pendingAction.value = null

      // Refresh entity if needed
      if (result.refresh_required && result.affected_entity_id) {
        await entityStore.fetchEntity(result.affected_entity_id)
      }

    } catch (e: unknown) {
      error.value = extractErrorMessage(e)
      const errorMessage: ConversationMessage = {
        role: 'assistant',
        content: `Fehler: ${error.value}`,
        timestamp: new Date(),
        response_type: 'error'
      }
      messages.value.push(errorMessage)
    } finally {
      isLoading.value = false
      history.saveHistory()
    }
  }

  // Cancel pending action
  function cancelAction() {
    pendingAction.value = null
    const cancelMessage: ConversationMessage = {
      role: 'assistant',
      content: 'Aktion abgebrochen.',
      timestamp: new Date()
    }
    messages.value.push(cancelMessage)
    history.saveHistory()
  }

  // Handle suggested action click
  async function handleSuggestedAction(action: SuggestedAction) {
    if (action.action === 'navigate') {
      router.push(action.value)
      closeChat()
    } else if (action.action === 'redirect') {
      router.push(action.value)
      closeChat()
    } else if (action.action === 'query') {
      await sendMessage(action.value)
    } else if (action.action === 'edit') {
      mode.value = 'write'
      await sendMessage(action.value)
    } else if (action.action === 'save_attachment') {
      await attachments.saveAttachmentsToEntity(action.value)
    }
  }

  // Initialize wizard with proper context
  const wizard = useAssistantWizard({
    messages,
    error,
    currentContext,
    saveHistory: history.saveHistory,
  })

  // Initialize reminders with proper context
  const reminders = useAssistantReminders({
    messages,
    error,
    currentContext,
    isOpen,
    hasUnread,
    saveHistory: history.saveHistory,
  })

  // Initialize insights with proper context
  const insights = useAssistantInsights({
    currentContext,
    messages,
    suggestedActions,
    send,
    closeChat,
  })

  // ============================================================================
  // Smart Query Integration
  // ============================================================================

  function openSmartQueryWithContext(query: string, writeMode: boolean = false) {
    // Store context for Smart Query to pick up
    queryContextStore.setFromAssistant(
      query,
      writeMode ? 'write' : 'read',
      {
        entityId: currentContext.value.current_entity_id,
        entityType: currentContext.value.current_entity_type,
        entityName: currentContext.value.current_entity_name,
      }
    )

    // Add message indicating redirect
    const redirectMessage: ConversationMessage = {
      role: 'assistant',
      content: writeMode
        ? `Öffne Smart Query im Schreib-Modus für: "${query}"`
        : `Öffne Smart Query für: "${query}"`,
      timestamp: new Date(),
      response_type: 'redirect',
    }
    messages.value.push(redirectMessage)
    history.saveHistory()

    // Navigate to Smart Query
    router.push({
      path: '/smart-query',
      query: {
        q: query,
        mode: writeMode ? 'write' : 'read',
        from: 'assistant',
      },
    })

    // Close the assistant drawer
    closeChat()
  }

  function checkSmartQueryResults() {
    if (queryContextStore.hasResults) {
      const results = queryContextStore.consumeResults()
      if (results) {
        // Add result message to chat
        const resultMessage: ConversationMessage = {
          role: 'assistant',
          content: `Smart Query ${results.mode === 'write' ? 'Aktion' : 'Ergebnis'}: ${results.summary}`,
          timestamp: new Date(),
          response_type: results.success ? 'success' : 'error',
          response_data: {
            type: 'smart_query_result',
            total: results.total,
            items: results.items,
            mode: results.mode,
          },
        }
        messages.value.push(resultMessage)
        history.saveHistory()

        // Open chat to show results
        if (!isOpen.value) {
          hasUnread.value = true
        }
      }
    }
  }

  // Re-run a query from history
  async function rerunQuery(itemId: string) {
    const item = history.queryHistory.value.find(q => q.id === itemId)
    if (item) {
      // Set mode based on query type
      mode.value = item.queryType
      await send(item.query)
    }
  }

  // Clear conversation
  function clearConversation() {
    history.clearConversation()
    pendingAction.value = null
    suggestedActions.value = []
  }

  // Keyboard shortcut handler
  function handleKeydown(event: KeyboardEvent) {
    // Cmd/Ctrl + K to toggle chat
    if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
      event.preventDefault()
      toggleChat()
    }
    // Escape to close
    if (event.key === 'Escape' && isOpen.value) {
      closeChat()
    }
  }

  // Lifecycle
  onMounted(() => {
    history.loadHistory()
    history.loadQueryHistory()
    insights.loadSlashCommands()
    insights.loadSuggestions()
    insights.loadInsights()
    wizard.loadWizards()
    reminders.loadReminders()
    reminders.loadDueReminders()
    checkSmartQueryResults()
    window.addEventListener('keydown', handleKeydown)
    reminders.startReminderPolling()
  })

  onUnmounted(() => {
    window.removeEventListener('keydown', handleKeydown)
    batch.cleanup()
    reminders.stopReminderPolling()
    cancelStreaming() // Cancel any ongoing streaming request
  })

  // Watch for route changes to update suggestions and insights
  watch(() => route.fullPath, async () => {
    await insights.loadSuggestions()
    await insights.loadInsights()
  }, { immediate: false })

  return {
    // Core State
    isOpen,
    isLoading,
    isStreaming,
    isUploading: attachments.isUploading,
    streamingContent,
    streamingStatus,
    messages,
    error,
    mode,
    suggestedActions,
    slashCommands: insights.slashCommands,
    hasUnread,
    pendingAction,
    pendingAttachments: attachments.pendingAttachments,
    currentContext,
    useStreaming,

    // Batch state
    activeBatch: batch.activeBatch,
    batchPreview: batch.batchPreview,
    isBatchDryRun: batch.isBatchDryRun,

    // Insights state
    insights: insights.insights,

    // Chat methods
    toggleChat,
    openChat,
    closeChat,
    send,
    sendMessage,
    sendMessageStream,
    cancelStreaming,
    executeAction,
    cancelAction,
    clearConversation,
    handleSuggestedAction,

    // Attachment methods
    uploadAttachment: attachments.uploadAttachment,
    removeAttachment: attachments.removeAttachment,
    clearAttachments: attachments.clearAttachments,
    getAttachmentIcon: attachments.getAttachmentIcon,
    formatFileSize: attachments.formatFileSize,
    saveAttachmentsToEntity: attachments.saveAttachmentsToEntity,

    // Batch methods
    executeBatchAction: batch.executeBatchAction,
    confirmBatchAction: batch.confirmBatchAction,
    cancelBatchAction: batch.cancelBatchAction,
    closeBatchProgress: batch.closeBatchProgress,

    // Insights methods
    handleInsightAction: insights.handleInsightAction,
    loadInsights: insights.loadInsights,

    // Wizard state & methods
    activeWizard: wizard.activeWizard,
    availableWizards: wizard.availableWizards,
    isWizardLoading: wizard.isWizardLoading,
    startWizard: wizard.startWizard,
    submitWizardResponse: wizard.submitWizardResponse,
    wizardGoBack: wizard.wizardGoBack,
    cancelWizard: wizard.cancelWizard,
    loadWizards: wizard.loadWizards,

    // Smart Query integration
    openSmartQueryWithContext,
    checkSmartQueryResults,

    // Reminder state & methods
    reminders: reminders.reminders,
    dueReminders: reminders.dueReminders,
    loadReminders: reminders.loadReminders,
    loadDueReminders: reminders.loadDueReminders,
    createReminder: reminders.createReminder,
    dismissReminder: reminders.dismissReminder,
    deleteReminder: reminders.deleteReminder,
    snoozeReminder: reminders.snoozeReminder,

    // Query history state & methods
    queryHistory: history.queryHistory,
    addQueryToHistory: history.addQueryToHistory,
    toggleQueryFavorite: history.toggleQueryFavorite,
    removeQueryFromHistory: history.removeQueryFromHistory,
    clearQueryHistory: history.clearQueryHistory,
    getQueryHistory: history.getQueryHistory,
    rerunQuery,
  }
}
