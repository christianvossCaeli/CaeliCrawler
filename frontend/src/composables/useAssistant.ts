import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { useEntityStore } from '@/stores/entity'
import { useQueryContextStore } from '@/stores/queryContext'
import { assistantApi } from '@/services/api'

// Types
export interface AssistantContext {
  current_route: string
  current_entity_id: string | null
  current_entity_type: string | null
  current_entity_name: string | null
  view_mode: 'dashboard' | 'list' | 'detail' | 'edit' | 'unknown'
  available_actions: string[]
  // Index signature for compatibility with API types
  [key: string]: unknown
}

export interface ConversationMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  metadata?: Record<string, unknown>
  response_type?: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  response_data?: any  // Using any for Vue template compatibility
}

export interface SuggestedAction {
  label: string
  action: string
  value: string
}

export interface SlashCommand {
  command: string
  description: string
  usage: string
  examples: string[]
}

export interface AttachmentInfo {
  id: string
  filename: string
  contentType: string
  size: number
  preview?: string // Data URL for image preview
}

export interface BatchStatus {
  batch_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  processed: number
  total: number
  errors: Array<{ entity_id?: string; entity_name?: string; error: string }>
  message: string
}

export interface BatchPreviewEntity {
  entity_id: string
  entity_name: string
  entity_type: string
}

export interface Insight {
  type: string
  icon: string
  message: string
  action: {
    type: string
    value: string
  }
  priority: number
  color: string
}

export interface WizardStepOption {
  value: string
  label: string
  description?: string
  icon?: string
}

export interface WizardStepDef {
  id: string
  question: string
  input_type: 'text' | 'textarea' | 'number' | 'date' | 'select' | 'multi_select' | 'entity_search' | 'confirm'
  options?: WizardStepOption[]
  placeholder?: string
  validation?: Record<string, any>
  entity_type?: string
  default_value?: any
  required?: boolean
  help_text?: string
}

export interface WizardState {
  wizard_id: string
  wizard_type: string
  current_step_id: string
  current_step_index: number
  total_steps: number
  answers: Record<string, any>
  completed: boolean
  cancelled: boolean
}

export interface WizardInfo {
  type: string
  name: string
  description: string
  icon?: string
}

export interface ActiveWizard {
  state: WizardState
  currentStep: WizardStepDef
  canGoBack: boolean
  progress: number
  message: string
  name: string
  icon: string
}

export interface Reminder {
  id: string
  message: string
  title?: string
  remind_at: string
  repeat: string
  status: string
  entity_id?: string
  entity_type?: string
  entity_name?: string
  created_at: string
}

export interface QueryHistoryItem {
  id: string
  query: string
  timestamp: Date
  resultCount: number
  queryType: 'read' | 'write' | 'plan'
  isFavorite: boolean
  entityType?: string
  facetTypes?: string[]
}

// Local storage keys
const STORAGE_KEY = 'assistant_conversation_history'
const QUERY_HISTORY_KEY = 'assistant_query_history'
const MAX_HISTORY_LENGTH = 50
const MAX_QUERY_HISTORY_LENGTH = 100

// Module-level interval reference for cleanup
let reminderPollInterval: ReturnType<typeof setInterval> | null = null

export function useAssistant() {
  const route = useRoute()
  const router = useRouter()
  const entityStore = useEntityStore()
  const queryContextStore = useQueryContextStore()
  const { locale } = useI18n()

  // State
  const isOpen = ref(false)
  const isLoading = ref(false)
  const isStreaming = ref(false)
  const streamingContent = ref('')
  const streamingStatus = ref('')
  const messages = ref<ConversationMessage[]>([])
  const error = ref<string | null>(null)
  const mode = ref<'read' | 'write' | 'plan'>('read')
  const suggestedActions = ref<SuggestedAction[]>([])
  const slashCommands = ref<SlashCommand[]>([])
  const hasUnread = ref(false)
  const pendingAction = ref<any>(null)
  const useStreaming = ref(true) // Enable streaming by default
  const pendingAttachments = ref<AttachmentInfo[]>([])
  const isUploading = ref(false)

  // Batch operations state
  const activeBatch = ref<BatchStatus | null>(null)
  const batchPreview = ref<BatchPreviewEntity[]>([])
  const isBatchDryRun = ref(false)
  const pendingBatchRequest = ref<{
    action_type: string
    target_filter: Record<string, any>
    action_data: Record<string, any>
  } | null>(null)
  let batchPollInterval: ReturnType<typeof setInterval> | null = null

  // Insights state
  const insights = ref<Insight[]>([])

  // Wizard state
  const activeWizard = ref<ActiveWizard | null>(null)
  const availableWizards = ref<WizardInfo[]>([])
  const isWizardLoading = ref(false)

  // Reminder state
  const reminders = ref<Reminder[]>([])
  const dueReminders = ref<Reminder[]>([])

  // Query history state
  const queryHistory = ref<QueryHistoryItem[]>([])

  // Detect view mode from route
  function detectViewMode(): AssistantContext['view_mode'] {
    const path = route.path

    if (path === '/' || path.includes('dashboard')) {
      return 'dashboard'
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
    const actions: string[] = ['search', 'help']

    if (route.params.entitySlug) {
      actions.push('view_details', 'edit', 'summarize')
    }
    if (route.params.typeSlug) {
      actions.push('filter', 'create')
    }

    return actions
  }

  // Computed context
  const currentContext = computed<AssistantContext>(() => ({
    current_route: route.fullPath,
    current_entity_id: entityStore.selectedEntity?.id || null,
    current_entity_type: route.params.typeSlug as string || null,
    current_entity_name: entityStore.selectedEntity?.name || null,
    view_mode: detectViewMode(),
    available_actions: getAvailableActions()
  }))

  // Load history from local storage
  function loadHistory() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        const parsed = JSON.parse(stored)
        messages.value = parsed.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp)
        }))
      }
    } catch (e) {
      console.error('Failed to load assistant history:', e)
    }
  }

  // Save history to local storage
  function saveHistory() {
    try {
      const toSave = messages.value.slice(-MAX_HISTORY_LENGTH)
      localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave))
    } catch (e) {
      console.error('Failed to save assistant history:', e)
    }
  }

  // Load query history from local storage
  function loadQueryHistory() {
    try {
      const stored = localStorage.getItem(QUERY_HISTORY_KEY)
      if (stored) {
        const parsed = JSON.parse(stored)
        queryHistory.value = parsed.map((item: any) => ({
          ...item,
          timestamp: new Date(item.timestamp)
        }))
      }
    } catch (e) {
      console.error('Failed to load query history:', e)
    }
  }

  // Save query history to local storage
  function saveQueryHistory() {
    try {
      const toSave = queryHistory.value.slice(-MAX_QUERY_HISTORY_LENGTH)
      localStorage.setItem(QUERY_HISTORY_KEY, JSON.stringify(toSave))
    } catch (e) {
      console.error('Failed to save query history:', e)
    }
  }

  // Add a query to history
  function addQueryToHistory(
    query: string,
    resultCount: number,
    queryType: 'read' | 'write' | 'plan',
    metadata?: { entityType?: string; facetTypes?: string[] }
  ) {
    // Don't add duplicate consecutive queries
    const lastQuery = queryHistory.value[queryHistory.value.length - 1]
    if (lastQuery && lastQuery.query === query) {
      // Update the timestamp and result count instead
      lastQuery.timestamp = new Date()
      lastQuery.resultCount = resultCount
      saveQueryHistory()
      return
    }

    const historyItem: QueryHistoryItem = {
      id: `qh_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      query,
      timestamp: new Date(),
      resultCount,
      queryType,
      isFavorite: false,
      entityType: metadata?.entityType,
      facetTypes: metadata?.facetTypes
    }

    queryHistory.value.push(historyItem)

    // Trim to max length (but keep favorites)
    if (queryHistory.value.length > MAX_QUERY_HISTORY_LENGTH) {
      const favorites = queryHistory.value.filter(item => item.isFavorite)
      const nonFavorites = queryHistory.value.filter(item => !item.isFavorite)
      const trimmedNonFavorites = nonFavorites.slice(-MAX_QUERY_HISTORY_LENGTH + favorites.length)
      queryHistory.value = [...favorites, ...trimmedNonFavorites].sort(
        (a, b) => a.timestamp.getTime() - b.timestamp.getTime()
      )
    }

    saveQueryHistory()
  }

  // Toggle favorite status of a query history item
  function toggleQueryFavorite(itemId: string) {
    const item = queryHistory.value.find(q => q.id === itemId)
    if (item) {
      item.isFavorite = !item.isFavorite
      saveQueryHistory()
    }
  }

  // Remove a query from history
  function removeQueryFromHistory(itemId: string) {
    queryHistory.value = queryHistory.value.filter(q => q.id !== itemId)
    saveQueryHistory()
  }

  // Clear all query history (optionally keep favorites)
  function clearQueryHistory(keepFavorites: boolean = true) {
    if (keepFavorites) {
      queryHistory.value = queryHistory.value.filter(item => item.isFavorite)
    } else {
      queryHistory.value = []
    }
    saveQueryHistory()
  }

  // Get query history, optionally filtered
  function getQueryHistory(options?: {
    favoritesOnly?: boolean
    queryType?: 'read' | 'write' | 'plan'
    limit?: number
  }): QueryHistoryItem[] {
    let result = [...queryHistory.value]

    if (options?.favoritesOnly) {
      result = result.filter(item => item.isFavorite)
    }

    if (options?.queryType) {
      result = result.filter(item => item.queryType === options.queryType)
    }

    // Sort by timestamp descending (newest first)
    result.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())

    if (options?.limit) {
      result = result.slice(0, options.limit)
    }

    return result
  }

  // Re-run a query from history
  async function rerunQuery(itemId: string) {
    const item = queryHistory.value.find(q => q.id === itemId)
    if (item) {
      // Set mode based on query type
      mode.value = item.queryType
      await send(item.query)
    }
  }

  // Clear conversation
  function clearConversation() {
    messages.value = []
    pendingAction.value = null
    suggestedActions.value = []
    localStorage.removeItem(STORAGE_KEY)
  }

  // Toggle chat open/close
  function toggleChat() {
    isOpen.value = !isOpen.value
    if (isOpen.value) {
      hasUnread.value = false
    }
  }

  // Open chat
  function openChat() {
    isOpen.value = true
    hasUnread.value = false
  }

  // Close chat
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

  // Send message to assistant
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
      const attachmentIds = pendingAttachments.value.map(a => a.id)

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
        await clearAttachments()
      }

      const data = response.data

      // Process response
      const responseData = data.response
      let assistantContent = responseData.message || 'Keine Antwort erhalten.'

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
      if (responseData.type === 'action_preview' && responseData.requires_confirmation) {
        pendingAction.value = responseData.action
      } else if (responseData.type === 'navigation') {
        // Offer to navigate
        const target = responseData.target
        if (target?.route) {
          suggestedActions.value.unshift({
            label: `Zu ${target.entity_name || 'Seite'} navigieren`,
            action: 'navigate',
            value: target.route
          })
        }
      } else if (responseData.type === 'redirect_to_smart_query') {
        // Offer to redirect
        suggestedActions.value.unshift({
          label: 'Smart Query öffnen',
          action: 'redirect',
          value: '/smart-query'
        })
      }

      // Mark as unread if chat is closed
      if (!isOpen.value) {
        hasUnread.value = true
      }

    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Fehler bei der Kommunikation'
      const errorMessage: ConversationMessage = {
        role: 'assistant',
        content: `Fehler: ${error.value}`,
        timestamp: new Date(),
        response_type: 'error'
      }
      messages.value.push(errorMessage)
    } finally {
      isLoading.value = false
      saveHistory()
    }
  }

  // Send message with streaming response
  async function sendMessageStream(text: string) {
    if (!text.trim()) return

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
      const attachmentIds = pendingAttachments.value.map(a => a.id)

      // Convert 'plan' mode to undefined for API compatibility
      const apiMode = mode.value === 'plan' ? undefined : mode.value
      const response = await assistantApi.chatStream({
        message: text.trim(),
        context: currentContext.value,
        conversation_history: buildConversationHistory(),
        mode: apiMode,
        language: lang,
        attachment_ids: attachmentIds.length > 0 ? attachmentIds : undefined
      })

      // Clear attachments after starting request
      if (attachmentIds.length > 0) {
        // Don't await, clear in background
        clearAttachments()
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
      let finalResponseData: any = null

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
              const data = JSON.parse(dataStr)

              switch (data.type) {
                case 'status':
                  streamingStatus.value = data.message
                  break

                case 'intent':
                  // Intent classified - could show in UI
                  break

                case 'token':
                  // Append token to streaming content
                  streamingContent.value += data.content
                  messages.value[assistantMessageIndex].content = streamingContent.value
                  break

                case 'item':
                  // Individual result item - could render progressively
                  break

                case 'complete':
                  // Final response data - data.data contains {success, response, suggested_actions}
                  // We need to extract the response part for message/type, but keep the full wrapper for suggested_actions
                  const completeWrapper = data.data
                  const responseData = completeWrapper?.response || completeWrapper
                  finalResponseData = {
                    ...responseData,
                    suggested_actions: completeWrapper?.suggested_actions || responseData?.suggested_actions || []
                  }
                  if (finalResponseData?.message) {
                    messages.value[assistantMessageIndex].content = finalResponseData.message
                  }
                  messages.value[assistantMessageIndex].response_type = finalResponseData?.type || 'query_result'
                  messages.value[assistantMessageIndex].response_data = finalResponseData
                  break

                case 'error':
                  error.value = data.message
                  messages.value[assistantMessageIndex].content = `Fehler: ${data.message}`
                  messages.value[assistantMessageIndex].response_type = 'error'
                  break
              }
            } catch (parseError) {
              console.error('Failed to parse SSE data:', parseError, dataStr)
            }
          }
        }
      }

      // Process final response data
      if (finalResponseData) {
        suggestedActions.value = finalResponseData.suggested_actions || []

        // Handle special response types
        if (finalResponseData.type === 'action_preview' && finalResponseData.requires_confirmation) {
          pendingAction.value = finalResponseData.action
        } else if (finalResponseData.type === 'navigation') {
          const target = finalResponseData.target
          if (target?.route) {
            suggestedActions.value.unshift({
              label: `Zu ${target.entity_name || 'Seite'} navigieren`,
              action: 'navigate',
              value: target.route
            })
          }
        } else if (finalResponseData.type === 'redirect_to_smart_query') {
          suggestedActions.value.unshift({
            label: 'Smart Query öffnen',
            action: 'redirect',
            value: '/smart-query'
          })
        }
      }

      // Mark as unread if chat is closed
      if (!isOpen.value) {
        hasUnread.value = true
      }

    } catch (e: any) {
      error.value = e.message || 'Fehler bei der Streaming-Kommunikation'
      messages.value[assistantMessageIndex].content = `Fehler: ${error.value}`
      messages.value[assistantMessageIndex].response_type = 'error'
    } finally {
      isLoading.value = false
      isStreaming.value = false
      streamingContent.value = ''
      streamingStatus.value = ''
      saveHistory()
    }
  }

  // Smart send that uses streaming when enabled
  async function send(text: string) {
    if (useStreaming.value) {
      await sendMessageStream(text)
    } else {
      await sendMessage(text)
    }
  }

  // Execute confirmed action
  async function executeAction(action: any) {
    isLoading.value = true
    error.value = null

    try {
      const response = await assistantApi.executeAction({
        action: action,
        context: currentContext.value
      })

      const result = response.data

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

    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Fehler bei der Ausführung'
      const errorMessage: ConversationMessage = {
        role: 'assistant',
        content: `Fehler: ${error.value}`,
        timestamp: new Date(),
        response_type: 'error'
      }
      messages.value.push(errorMessage)
    } finally {
      isLoading.value = false
      saveHistory()
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
    saveHistory()
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
      // Save temporary chat attachments as permanent entity attachments
      await saveAttachmentsToEntity(action.value)
    }
  }

  // Save temporary attachments to entity
  async function saveAttachmentsToEntity(actionValue: string): Promise<boolean> {
    isLoading.value = true
    error.value = null

    try {
      // Parse the action value (JSON with entity_id and attachment_ids)
      const { entity_id, attachment_ids } = JSON.parse(actionValue)

      if (!entity_id || !attachment_ids || attachment_ids.length === 0) {
        throw new Error('Keine Attachments zum Speichern')
      }

      const response = await assistantApi.saveToEntityAttachments(entity_id, attachment_ids)
      const result = response.data

      // Add result message to chat
      const resultMessage: ConversationMessage = {
        role: 'assistant',
        content: result.message,
        timestamp: new Date(),
        response_type: result.success ? 'success' : 'error',
      }
      messages.value.push(resultMessage)
      saveHistory()

      // Clear suggested actions after successful save
      if (result.success) {
        suggestedActions.value = suggestedActions.value.filter(
          a => a.action !== 'save_attachment'
        )
      }

      return result.success
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Fehler beim Speichern'
      const errorMessage: ConversationMessage = {
        role: 'assistant',
        content: `Fehler: ${error.value}`,
        timestamp: new Date(),
        response_type: 'error',
      }
      messages.value.push(errorMessage)
      saveHistory()
      return false
    } finally {
      isLoading.value = false
    }
  }

  // Upload a file attachment
  async function uploadAttachment(file: File): Promise<boolean> {
    // Validate file type
    const allowedTypes = ['image/png', 'image/jpeg', 'image/gif', 'image/webp', 'application/pdf']
    if (!allowedTypes.includes(file.type)) {
      error.value = `Nicht unterstützter Dateityp: ${file.type}`
      return false
    }

    // Validate file size (10MB max)
    const maxSize = 10 * 1024 * 1024
    if (file.size > maxSize) {
      error.value = 'Datei zu groß (max. 10MB)'
      return false
    }

    isUploading.value = true
    error.value = null

    try {
      const response = await assistantApi.uploadAttachment(file)
      const data = response.data

      // Create preview for images
      let preview: string | undefined
      if (file.type.startsWith('image/')) {
        preview = await createImagePreview(file)
      }

      pendingAttachments.value.push({
        id: data.attachment.attachment_id,
        filename: data.attachment.filename,
        contentType: data.attachment.content_type,
        size: data.attachment.size,
        preview,
      })

      return true
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Fehler beim Upload'
      return false
    } finally {
      isUploading.value = false
    }
  }

  // Create a preview image data URL
  function createImagePreview(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = (e) => resolve(e.target?.result as string)
      reader.onerror = reject
      reader.readAsDataURL(file)
    })
  }

  // Remove a pending attachment
  async function removeAttachment(attachmentId: string) {
    try {
      await assistantApi.deleteAttachment(attachmentId)
    } catch (e) {
      // Ignore delete errors
    }
    pendingAttachments.value = pendingAttachments.value.filter(a => a.id !== attachmentId)
  }

  // Clear all pending attachments
  async function clearAttachments() {
    for (const attachment of pendingAttachments.value) {
      try {
        await assistantApi.deleteAttachment(attachment.id)
      } catch (e) {
        // Ignore delete errors
      }
    }
    pendingAttachments.value = []
  }

  // Get file icon based on content type
  function getAttachmentIcon(contentType: string): string {
    if (contentType.startsWith('image/')) {
      return 'mdi-image'
    }
    if (contentType === 'application/pdf') {
      return 'mdi-file-pdf-box'
    }
    return 'mdi-file'
  }

  // Format file size for display
  function formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  // Execute a batch action (dry run first)
  async function executeBatchAction(
    actionType: string,
    targetFilter: Record<string, any>,
    actionData: Record<string, any>,
    dryRun: boolean = true
  ): Promise<boolean> {
    isLoading.value = true
    error.value = null

    try {
      const response = await assistantApi.batchAction({
        action_type: actionType,
        target_filter: targetFilter,
        action_data: actionData,
        dry_run: dryRun,
      })

      const data = response.data

      if (dryRun) {
        // Show preview
        activeBatch.value = {
          batch_id: '',
          status: 'pending',
          processed: 0,
          total: data.affected_count,
          errors: [],
          message: data.message || '',
        }
        batchPreview.value = data.preview || []
        isBatchDryRun.value = true
        pendingBatchRequest.value = { action_type: actionType, target_filter: targetFilter, action_data: actionData }
      } else {
        // Start actual batch operation
        activeBatch.value = {
          batch_id: data.batch_id,
          status: 'running',
          processed: 0,
          total: data.affected_count,
          errors: [],
          message: data.message || '',
        }
        isBatchDryRun.value = false
        batchPreview.value = data.preview || []

        // Start polling for status
        startBatchPolling(data.batch_id)
      }

      return true
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Fehler bei Batch-Operation'
      return false
    } finally {
      isLoading.value = false
    }
  }

  // Confirm and execute a pending batch action
  async function confirmBatchAction(): Promise<boolean> {
    if (!pendingBatchRequest.value) return false

    const { action_type, target_filter, action_data } = pendingBatchRequest.value
    pendingBatchRequest.value = null
    isBatchDryRun.value = false

    return await executeBatchAction(action_type, target_filter, action_data, false)
  }

  // Cancel a pending or running batch action
  async function cancelBatchAction(): Promise<void> {
    if (activeBatch.value?.batch_id && activeBatch.value.status === 'running') {
      try {
        await assistantApi.cancelBatch(activeBatch.value.batch_id)
      } catch (e) {
        console.error('Failed to cancel batch:', e)
      }
    }

    stopBatchPolling()
    activeBatch.value = null
    batchPreview.value = []
    isBatchDryRun.value = false
    pendingBatchRequest.value = null
  }

  // Start polling for batch status
  function startBatchPolling(batchId: string) {
    stopBatchPolling() // Clear any existing interval

    batchPollInterval = setInterval(async () => {
      try {
        const response = await assistantApi.getBatchStatus(batchId)
        const status = response.data

        activeBatch.value = {
          batch_id: batchId,
          status: status.status,
          processed: status.processed,
          total: status.total,
          errors: status.errors || [],
          message: status.message || '',
        }

        // Stop polling when complete
        if (['completed', 'failed', 'cancelled'].includes(status.status)) {
          stopBatchPolling()

          // Add completion message to chat
          const completionMessage: ConversationMessage = {
            role: 'assistant',
            content: getBatchCompletionMessage(status),
            timestamp: new Date(),
            response_type: status.status === 'completed' ? 'success' : 'error',
          }
          messages.value.push(completionMessage)
          saveHistory()
        }
      } catch (e) {
        console.error('Failed to poll batch status:', e)
        stopBatchPolling()
      }
    }, 2000) // Poll every 2 seconds
  }

  // Stop polling for batch status
  function stopBatchPolling() {
    if (batchPollInterval) {
      clearInterval(batchPollInterval)
      batchPollInterval = null
    }
  }

  // Get completion message for batch operation
  function getBatchCompletionMessage(status: any): string {
    if (status.status === 'completed') {
      if (status.errors?.length > 0) {
        return `Batch-Operation abgeschlossen: ${status.processed} von ${status.total} verarbeitet. ${status.errors.length} Fehler aufgetreten.`
      }
      return `Batch-Operation erfolgreich abgeschlossen: ${status.processed} Entities verarbeitet.`
    } else if (status.status === 'cancelled') {
      return `Batch-Operation abgebrochen. ${status.processed} von ${status.total} wurden bereits verarbeitet.`
    } else {
      return `Batch-Operation fehlgeschlagen: ${status.message || 'Unbekannter Fehler'}`
    }
  }

  // Close batch progress display
  function closeBatchProgress() {
    stopBatchPolling()
    activeBatch.value = null
    batchPreview.value = []
    isBatchDryRun.value = false
    pendingBatchRequest.value = null
  }

  // Load slash commands
  async function loadSlashCommands() {
    try {
      const response = await assistantApi.getCommands()
      slashCommands.value = response.data
    } catch (e) {
      console.error('Failed to load slash commands:', e)
    }
  }

  // Load context-specific suggestions from API
  async function loadSuggestions() {
    try {
      const response = await assistantApi.getSuggestions({
        route: currentContext.value.current_route,
        entity_type: currentContext.value.current_entity_type || undefined,
        entity_id: currentContext.value.current_entity_id || undefined
      })
      // Only update if we don't have user-triggered suggestions
      if (messages.value.length === 0 || !suggestedActions.value.length) {
        suggestedActions.value = response.data.suggestions?.map((s: any) => ({
          label: s.label,
          action: 'query',
          value: s.query
        })) || []
      }
    } catch (e) {
      console.error('Failed to load suggestions:', e)
    }
  }

  // Load proactive insights from API
  async function loadInsights() {
    try {
      const lang = (locale.value === 'de' || locale.value === 'en') ? locale.value : 'de'
      const response = await assistantApi.getInsights({
        route: currentContext.value.current_route,
        view_mode: currentContext.value.view_mode,
        entity_type: currentContext.value.current_entity_type || undefined,
        entity_id: currentContext.value.current_entity_id || undefined,
        language: lang
      })
      insights.value = response.data.insights || []
    } catch (e) {
      console.error('Failed to load insights:', e)
      insights.value = []
    }
  }

  // Handle insight action click
  async function handleInsightAction(action: { type: string; value: string }) {
    if (action.type === 'navigate') {
      router.push(action.value)
      closeChat()
    } else if (action.type === 'query') {
      await send(action.value)
    }
  }

  // Load available wizards
  async function loadWizards() {
    try {
      const response = await assistantApi.getWizards()
      availableWizards.value = response.data.wizards || []
    } catch (e) {
      console.error('Failed to load wizards:', e)
      availableWizards.value = []
    }
  }

  // Start a new wizard
  async function startWizard(wizardType: string): Promise<boolean> {
    isWizardLoading.value = true
    error.value = null

    try {
      const response = await assistantApi.startWizard(wizardType, {
        current_entity_id: currentContext.value.current_entity_id,
        current_entity_type: currentContext.value.current_entity_type,
      })

      const data = response.data

      // Find wizard info for name/icon
      const wizardInfo = availableWizards.value.find(w => w.type === wizardType)

      activeWizard.value = {
        state: data.wizard_state,
        currentStep: data.current_step,
        canGoBack: data.can_go_back,
        progress: data.progress,
        message: data.message,
        name: wizardInfo?.name || wizardType,
        icon: wizardInfo?.icon || 'mdi-wizard-hat',
      }

      // Add wizard start message to chat
      const wizardMessage: ConversationMessage = {
        role: 'assistant',
        content: data.message,
        timestamp: new Date(),
        response_type: 'wizard',
        metadata: { wizard_id: data.wizard_state.wizard_id },
      }
      messages.value.push(wizardMessage)
      saveHistory()

      return true
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Fehler beim Starten des Wizards'
      return false
    } finally {
      isWizardLoading.value = false
    }
  }

  // Submit wizard response
  async function submitWizardResponse(value: any): Promise<boolean> {
    if (!activeWizard.value) return false

    isWizardLoading.value = true
    error.value = null

    try {
      const response = await assistantApi.wizardRespond(
        activeWizard.value.state.wizard_id,
        value
      )

      const data = response.data
      const wizardResponse = data.wizard_response
      const result = data.result

      // Update wizard state
      if (wizardResponse.wizard_state.completed || wizardResponse.wizard_state.cancelled) {
        // Wizard finished
        const completionMessage: ConversationMessage = {
          role: 'assistant',
          content: wizardResponse.message,
          timestamp: new Date(),
          response_type: result?.success ? 'success' : (wizardResponse.wizard_state.cancelled ? 'info' : 'error'),
        }
        messages.value.push(completionMessage)
        saveHistory()

        // Handle result actions (e.g., navigation)
        if (result?.navigate_to) {
          router.push(result.navigate_to)
        }

        activeWizard.value = null
      } else {
        // Update to next step
        activeWizard.value = {
          ...activeWizard.value,
          state: wizardResponse.wizard_state,
          currentStep: wizardResponse.current_step,
          canGoBack: wizardResponse.can_go_back,
          progress: wizardResponse.progress,
          message: wizardResponse.message,
        }

        // Add step message to chat
        const stepMessage: ConversationMessage = {
          role: 'assistant',
          content: wizardResponse.message,
          timestamp: new Date(),
          response_type: 'wizard',
        }
        messages.value.push(stepMessage)
        saveHistory()
      }

      return true
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Fehler bei der Wizard-Antwort'
      return false
    } finally {
      isWizardLoading.value = false
    }
  }

  // Go back to previous wizard step
  async function wizardGoBack(): Promise<boolean> {
    if (!activeWizard.value || !activeWizard.value.canGoBack) return false

    isWizardLoading.value = true
    error.value = null

    try {
      const response = await assistantApi.wizardBack(activeWizard.value.state.wizard_id)
      const data = response.data

      activeWizard.value = {
        ...activeWizard.value,
        state: data.wizard_state,
        currentStep: data.current_step,
        canGoBack: data.can_go_back,
        progress: data.progress,
        message: data.message,
      }

      return true
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Fehler beim Zurückgehen'
      return false
    } finally {
      isWizardLoading.value = false
    }
  }

  // Cancel active wizard
  async function cancelWizard(): Promise<void> {
    if (!activeWizard.value) return

    try {
      await assistantApi.wizardCancel(activeWizard.value.state.wizard_id)
    } catch (e) {
      console.error('Failed to cancel wizard:', e)
    }

    // Add cancellation message
    const cancelMessage: ConversationMessage = {
      role: 'assistant',
      content: 'Wizard abgebrochen.',
      timestamp: new Date(),
      response_type: 'info',
    }
    messages.value.push(cancelMessage)
    saveHistory()

    activeWizard.value = null
  }

  // ============================================================================
  // Smart Query Integration
  // ============================================================================

  /**
   * Open Smart Query with context from the assistant
   */
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
    saveHistory()

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

  /**
   * Check for and handle results returned from Smart Query
   */
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
        saveHistory()

        // Open chat to show results
        if (!isOpen.value) {
          hasUnread.value = true
        }
      }
    }
  }

  // ============================================================================
  // Reminders
  // ============================================================================

  /**
   * Load reminders for the current user
   */
  async function loadReminders() {
    try {
      const response = await assistantApi.getReminders()
      reminders.value = response.data.items || []
    } catch (e) {
      console.error('Failed to load reminders:', e)
      reminders.value = []
    }
  }

  /**
   * Load due reminders (pending and past remind_at)
   */
  async function loadDueReminders() {
    try {
      const response = await assistantApi.getDueReminders()
      dueReminders.value = response.data.items || []

      // Show notification for due reminders
      if (dueReminders.value.length > 0 && !isOpen.value) {
        hasUnread.value = true
      }
    } catch (e) {
      console.error('Failed to load due reminders:', e)
      dueReminders.value = []
    }
  }

  /**
   * Create a new reminder
   */
  async function createReminder(
    message: string,
    remindAt: Date,
    options?: {
      title?: string
      repeat?: 'none' | 'daily' | 'weekly' | 'monthly'
    }
  ): Promise<boolean> {
    try {
      const response = await assistantApi.createReminder({
        message,
        remind_at: remindAt.toISOString(),
        title: options?.title,
        entity_id: currentContext.value.current_entity_id || undefined,
        entity_type: currentContext.value.current_entity_type || undefined,
        repeat: options?.repeat || 'none',
      })

      if (response.data.success) {
        // Add confirmation message
        const confirmMessage: ConversationMessage = {
          role: 'assistant',
          content: response.data.message,
          timestamp: new Date(),
          response_type: 'success',
        }
        messages.value.push(confirmMessage)
        saveHistory()

        // Reload reminders
        await loadReminders()
        return true
      }
      return false
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Fehler beim Erstellen der Erinnerung'
      return false
    }
  }

  /**
   * Dismiss a reminder
   */
  async function dismissReminder(reminderId: string): Promise<boolean> {
    try {
      await assistantApi.dismissReminder(reminderId)
      // Remove from due reminders list
      dueReminders.value = dueReminders.value.filter(r => r.id !== reminderId)
      await loadReminders()
      return true
    } catch (e) {
      console.error('Failed to dismiss reminder:', e)
      return false
    }
  }

  /**
   * Delete a reminder
   */
  async function deleteReminder(reminderId: string): Promise<boolean> {
    try {
      await assistantApi.deleteReminder(reminderId)
      reminders.value = reminders.value.filter(r => r.id !== reminderId)
      dueReminders.value = dueReminders.value.filter(r => r.id !== reminderId)
      return true
    } catch (e) {
      console.error('Failed to delete reminder:', e)
      return false
    }
  }

  /**
   * Snooze a reminder by a number of minutes
   */
  async function snoozeReminder(reminderId: string, minutes: number): Promise<boolean> {
    try {
      const newRemindAt = new Date(Date.now() + minutes * 60 * 1000)
      await assistantApi.snoozeReminder(reminderId, newRemindAt.toISOString())
      // Remove from due reminders list (will reappear when it's due again)
      dueReminders.value = dueReminders.value.filter(r => r.id !== reminderId)
      await loadReminders()
      return true
    } catch (e) {
      console.error('Failed to snooze reminder:', e)
      return false
    }
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
    loadHistory()
    loadQueryHistory()
    loadSlashCommands()
    loadSuggestions()
    loadInsights()
    loadWizards()
    loadReminders()
    loadDueReminders()
    checkSmartQueryResults() // Check for results from Smart Query
    window.addEventListener('keydown', handleKeydown)

    // Set up interval to check for due reminders every minute
    // Clear any existing interval first to prevent duplicates
    if (reminderPollInterval) {
      clearInterval(reminderPollInterval)
    }
    reminderPollInterval = setInterval(loadDueReminders, 60000)
  })

  onUnmounted(() => {
    window.removeEventListener('keydown', handleKeydown)
    stopBatchPolling() // Clean up batch polling

    // Clean up reminder polling
    if (reminderPollInterval) {
      clearInterval(reminderPollInterval)
      reminderPollInterval = null
    }
  })

  // Watch for route changes to update suggestions and insights
  watch(() => route.fullPath, async () => {
    await loadSuggestions()
    await loadInsights()
  }, { immediate: false })

  return {
    // State
    isOpen,
    isLoading,
    isStreaming,
    isUploading,
    streamingContent,
    streamingStatus,
    messages,
    error,
    mode,
    suggestedActions,
    slashCommands,
    hasUnread,
    pendingAction,
    pendingAttachments,
    currentContext,
    useStreaming,

    // Batch state
    activeBatch,
    batchPreview,
    isBatchDryRun,

    // Insights state
    insights,

    // Methods
    toggleChat,
    openChat,
    closeChat,
    send, // Smart send (uses streaming when enabled)
    sendMessage, // Non-streaming send
    sendMessageStream, // Streaming send
    executeAction,
    cancelAction,
    clearConversation,
    handleSuggestedAction,
    uploadAttachment,
    removeAttachment,
    clearAttachments,
    getAttachmentIcon,
    formatFileSize,
    saveAttachmentsToEntity,

    // Batch methods
    executeBatchAction,
    confirmBatchAction,
    cancelBatchAction,
    closeBatchProgress,

    // Insights methods
    handleInsightAction,
    loadInsights,

    // Wizard state
    activeWizard,
    availableWizards,
    isWizardLoading,

    // Wizard methods
    startWizard,
    submitWizardResponse,
    wizardGoBack,
    cancelWizard,
    loadWizards,

    // Smart Query integration
    openSmartQueryWithContext,
    checkSmartQueryResults,

    // Reminder state
    reminders,
    dueReminders,

    // Reminder methods
    loadReminders,
    loadDueReminders,
    createReminder,
    dismissReminder,
    deleteReminder,
    snoozeReminder,

    // Query history state
    queryHistory,

    // Query history methods
    addQueryToHistory,
    toggleQueryFavorite,
    removeQueryFromHistory,
    clearQueryHistory,
    getQueryHistory,
    rerunQuery,
  }
}
