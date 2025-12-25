import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { api, assistantApi } from '@/services/api'
import { useQueryContextStore } from '@/stores/queryContext'
import { useSmartQueryHistoryStore } from '@/stores/smartQueryHistory'
import { useSpeechRecognition } from '@/composables/useSpeechRecognition'
import { usePlanMode } from '@/composables/usePlanMode'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger('useSmartQuery')

// Types
export type QueryMode = 'read' | 'write' | 'plan'

export interface AttachmentInfo {
  id: string
  filename: string
  contentType: string
  size: number
  preview?: string
}

export interface SmartQueryResults {
  mode: QueryMode
  success: boolean
  message?: string
  total?: number
  items?: any[]
  data?: any[]  // Legacy field for result data
  created_items?: any[]
  query_interpretation?: any
  interpretation?: any
  visualization?: any
  visualizations?: any[]
  is_compound?: boolean
  explanation?: string
  source_info?: any
  suggested_actions?: any[]
  error?: string
  grouping?: string
}

export interface SmartQueryPreview {
  mode: string
  success: boolean
  preview: any
  interpretation: any
  message?: string
}

/**
 * Shared Smart Query composable with state and logic
 * Provides centralized state management for Smart Query operations
 */
export function useSmartQuery() {
  const { t, locale } = useI18n()
  const route = useRoute()
  const router = useRouter()
  const queryContextStore = useQueryContextStore()
  const historyStore = useSmartQueryHistoryStore()

  // Core state
  const question = ref('')
  const currentMode = ref<QueryMode>('read')
  const loading = ref(false)
  const error = ref<string | null>(null)
  const results = ref<SmartQueryResults | null>(null)
  const previewData = ref<SmartQueryPreview | null>(null)
  const fromAssistant = ref(false)
  const currentStep = ref(1)

  // Attachments
  const pendingAttachments = ref<AttachmentInfo[]>([])
  const isUploading = ref(false)

  // UI state
  const showHistory = ref(false)

  // Plan mode
  const {
    conversation: planConversation,
    loading: planLoading,
    error: planError,
    generatedPrompt: planGeneratedPrompt,
    executePlanQueryStream: executePlanModeQueryStream,
    reset: resetPlanMode,
  } = usePlanMode()

  // Speech recognition
  const {
    isListening,
    hasMicrophone,
    transcript,
    interimTranscript,
    error: speechError,
    toggleListening,
    clearTranscript,
  } = useSpeechRecognition()

  // Computed
  const writeMode = computed(() => currentMode.value === 'write')
  const modeHint = computed(() => {
    const shortcut = t('smartQueryView.mode.shortcut')
    if (currentMode.value === 'plan') {
      return t('smartQueryView.mode.planHint', { shortcut })
    }
    return currentMode.value === 'write'
      ? t('smartQueryView.mode.writeHint', { shortcut })
      : t('smartQueryView.mode.readHint', { shortcut })
  })

  // Watch transcript changes
  watch(transcript, (newVal) => {
    if (newVal) {
      question.value = newVal
    }
  })

  // Watch speech errors
  watch(speechError, (newVal) => {
    if (newVal) {
      error.value = newVal
    }
  })

  // Voice input handler
  function handleVoiceInput() {
    if (isListening.value) {
      toggleListening()
    } else {
      clearTranscript()
      question.value = ''
      toggleListening()
    }
  }

  // Attachment functions
  async function uploadAttachment(file: File): Promise<boolean> {
    const allowedTypes = ['image/png', 'image/jpeg', 'image/gif', 'image/webp', 'application/pdf']
    if (!allowedTypes.includes(file.type)) {
      error.value = t('assistant.attachmentTypeError')
      return false
    }

    const maxSize = 10 * 1024 * 1024
    if (file.size > maxSize) {
      error.value = t('assistant.attachmentTooLarge')
      return false
    }

    isUploading.value = true
    error.value = null

    try {
      const response = await assistantApi.uploadAttachment(file)
      const data = response.data

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
      error.value = e.response?.data?.detail || e.message || t('assistant.attachmentError')
      return false
    } finally {
      isUploading.value = false
    }
  }

  function createImagePreview(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = (e) => resolve(e.target?.result as string)
      reader.onerror = reject
      reader.readAsDataURL(file)
    })
  }

  async function removeAttachment(attachmentId: string) {
    try {
      await assistantApi.deleteAttachment(attachmentId)
    } catch (e) {
      // Ignore delete errors
    }
    pendingAttachments.value = pendingAttachments.value.filter(a => a.id !== attachmentId)
  }

  // Query execution
  async function executePlanQuery() {
    if (!question.value.trim()) return

    const currentQuestion = question.value
    question.value = ''

    const success = await executePlanModeQueryStream(currentQuestion)

    if (!success && planError.value) {
      error.value = planError.value
    }
  }

  async function executeQuery() {
    if (currentMode.value === 'plan') {
      return executePlanQuery()
    }

    if (!question.value.trim() && pendingAttachments.value.length === 0) return

    loading.value = true
    error.value = null
    results.value = null
    previewData.value = null

    try {
      if (pendingAttachments.value.length > 0) {
        await executeWithAttachments()
      } else if (writeMode.value) {
        await executeWritePreview()
      } else {
        await executeReadQuery()
      }
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || t('smartQueryView.errors.queryError')
    } finally {
      loading.value = false
    }
  }

  async function executeWithAttachments() {
    const attachmentIds = pendingAttachments.value.map(a => a.id)
    const lang = (locale.value === 'de' || locale.value === 'en') ? locale.value : 'de'

    const response = await assistantApi.chat({
      message: question.value.trim() || 'Analysiere das Bild',
      context: {
        current_route: '/smart-query',
        current_entity_id: null,
        current_entity_type: null,
        current_entity_name: null,
        view_mode: 'unknown',
        available_actions: []
      },
      conversation_history: [],
      mode: 'read',
      language: lang,
      attachment_ids: attachmentIds
    })

    // Clean up attachments
    for (const attachment of pendingAttachments.value) {
      try {
        await assistantApi.deleteAttachment(attachment.id)
      } catch (e) {
        // Ignore cleanup errors
      }
    }
    pendingAttachments.value = []

    const data = response.data
    results.value = {
      mode: 'read',
      success: data.success,
      message: data.response?.message || 'Bildanalyse abgeschlossen',
      items: data.response?.data?.items || [],
      total: data.response?.data?.total || 0,
      interpretation: {
        operation: 'image_analysis',
        query: question.value || 'Bildanalyse'
      },
      suggested_actions: data.suggested_actions || []
    }
  }

  async function executeWritePreview() {
    const response = await api.post('/v1/analysis/smart-write', {
      question: question.value,
      preview_only: true,
      confirmed: false
    })

    if (response.data.mode === 'preview' && response.data.success) {
      previewData.value = response.data
    } else {
      error.value = response.data.message || t('smartQueryView.errors.noWriteOperation')
    }
  }

  async function executeReadQuery() {
    const response = await api.post('/v1/analysis/smart-query', {
      question: question.value,
      allow_write: false
    })
    results.value = response.data
  }

  async function confirmWrite() {
    if (!question.value.trim()) return

    loading.value = true
    error.value = null
    currentStep.value = 1

    const isAiGeneration = previewData.value?.interpretation?.operation === 'create_category_setup'
    let stepInterval: ReturnType<typeof setInterval> | null = null

    if (isAiGeneration) {
      stepInterval = setInterval(() => {
        if (currentStep.value < 4) {
          currentStep.value++
        }
      }, 2500)
    }

    try {
      const response = await api.post('/v1/analysis/smart-write', {
        question: question.value,
        preview_only: false,
        confirmed: true
      })
      results.value = response.data
      previewData.value = null
      currentStep.value = 4
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || t('smartQuery.createError')
    } finally {
      if (stepInterval) {
        clearInterval(stepInterval)
      }
      loading.value = false
    }
  }

  function cancelPreview() {
    previewData.value = null
  }

  function resetAll() {
    results.value = null
    previewData.value = null
    question.value = ''
  }

  function adoptPrompt(prompt: string, mode: 'read' | 'write') {
    question.value = prompt
    currentMode.value = mode
    resetPlanMode()
    results.value = null
  }

  function handlePlanReset() {
    resetPlanMode()
    question.value = ''
  }

  function handleVisualizationAction(action: string, params: Record<string, any>) {
    logger.debug('Visualization action', { action, params })

    switch (action) {
      case 'setup_sync':
      case 'setup_api_sync':
        currentMode.value = 'write'
        question.value = `Richte automatische Synchronisation ein für ${params.entity_type || 'Daten'}`
        break

      case 'save_to_entities':
        currentMode.value = 'write'
        question.value = `Speichere die externen Daten als Entities`
        break

      case 'change_visualization':
        // Could open a dialog to change visualization type
        break

      default:
        break
    }
  }

  function handleHistoryRerun(commandText: string, _interpretation: Record<string, any>) {
    question.value = commandText
    currentMode.value = 'write'
    showHistory.value = false
    executeQuery()
  }

  function sendResultsToAssistant() {
    if (!results.value) return

    const isWriteMode = results.value.mode === 'write'
    const summary = isWriteMode
      ? (results.value.success
        ? t('smartQueryView.assistant.elementsCreated', { count: results.value.created_items?.length || 0 })
        : results.value.message || t('smartQueryView.assistant.executionError'))
      : t('smartQueryView.assistant.resultsFound', { count: results.value.total || 0 })

    queryContextStore.setResults({
      summary,
      total: results.value.total || results.value.created_items?.length || 0,
      items: results.value.items?.slice(0, 5) || results.value.created_items?.slice(0, 5) || [],
      interpretation: results.value.query_interpretation || results.value.interpretation,
      success: results.value.success !== false,
      mode: isWriteMode ? 'write' : 'read',
    })

    router.back()
  }

  function initializeFromContext() {
    const assistantContext = queryContextStore.consumeContext()
    if (assistantContext) {
      question.value = assistantContext.query
      currentMode.value = assistantContext.mode === 'write' ? 'write' : 'read'
      fromAssistant.value = true
      return true
    }

    const urlQuery = route.query.q as string
    const urlMode = route.query.mode as string
    const urlFrom = route.query.from as string

    if (urlQuery) {
      question.value = urlQuery
      fromAssistant.value = urlFrom === 'assistant'
    }
    if (urlMode === 'write') {
      currentMode.value = 'write'
    } else if (urlMode === 'plan') {
      currentMode.value = 'plan'
    }

    return !!urlQuery
  }

  return {
    // State
    question,
    currentMode,
    loading,
    error,
    results,
    previewData,
    fromAssistant,
    currentStep,
    pendingAttachments,
    isUploading,
    showHistory,

    // Plan mode
    planConversation,
    planLoading,
    planError,
    planGeneratedPrompt,

    // Speech
    isListening,
    hasMicrophone,
    interimTranscript,

    // Computed
    writeMode,
    modeHint,

    // Stores
    historyStore,

    // Methods
    handleVoiceInput,
    uploadAttachment,
    removeAttachment,
    executeQuery,
    executePlanQuery,
    confirmWrite,
    cancelPreview,
    resetAll,
    adoptPrompt,
    handlePlanReset,
    handleVisualizationAction,
    handleHistoryRerun,
    sendResultsToAssistant,
    initializeFromContext,
  }
}
