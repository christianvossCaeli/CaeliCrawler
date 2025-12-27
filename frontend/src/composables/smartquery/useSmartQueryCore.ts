/**
 * Smart Query Core Composable
 *
 * Main composable for Smart Query functionality. Provides centralized
 * state management and query execution logic.
 *
 * Composes with:
 * - useSmartQueryAttachments: File attachment handling
 * - usePlanMode: Interactive guide mode
 * - useSpeechRecognition: Voice input
 */

import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { api, assistantApi } from '@/services/api'
import { useQueryContextStore } from '@/stores/queryContext'
import { useSmartQueryHistoryStore } from '@/stores/smartQueryHistory'
import { useSpeechRecognition } from '@/composables/useSpeechRecognition'
import { usePlanMode } from '@/composables/usePlanMode'
import { useLogger } from '@/composables/useLogger'
import { useSmartQueryAttachments } from './useSmartQueryAttachments'
import type { QueryMode, SmartQueryResults, SmartQueryPreview, LoadingState, LoadingPhase } from './types'
import { getErrorDetail, DEFAULT_LOADING_STATE, LOADING_PHASE_MESSAGES } from './types'

const logger = useLogger('useSmartQueryCore')

/**
 * Main Smart Query composable
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

  // Granular loading state
  const loadingState = ref<LoadingState>({ ...DEFAULT_LOADING_STATE })

  // UI state
  const showHistory = ref(false)

  /**
   * Set loading phase with optional message
   */
  function setLoadingPhase(phase: LoadingPhase, progress?: number): void {
    loadingState.value = {
      isLoading: phase !== 'idle',
      phase,
      progress,
      message: LOADING_PHASE_MESSAGES[phase],
    }
    loading.value = phase !== 'idle'
  }

  // Compose with attachments
  const attachments = useSmartQueryAttachments()

  // Compose with plan mode
  const planMode = usePlanMode()

  // Compose with speech recognition
  const speech = useSpeechRecognition()

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

  // Watch transcript changes from speech recognition
  watch(speech.transcript, (newVal) => {
    if (newVal) {
      question.value = newVal
    }
  })

  // Watch speech errors
  watch(speech.error, (newVal) => {
    if (newVal) {
      error.value = newVal
    }
  })

  /**
   * Handle voice input toggle
   */
  function handleVoiceInput() {
    if (speech.isListening.value) {
      speech.toggleListening()
    } else {
      speech.clearTranscript()
      question.value = ''
      speech.toggleListening()
    }
  }

  /**
   * Execute plan mode query
   */
  async function executePlanQuery() {
    if (!question.value.trim()) return

    const currentQuestion = question.value
    question.value = ''

    const success = await planMode.executePlanQueryStream(currentQuestion)

    if (!success && planMode.error.value) {
      error.value = planMode.error.value
    }
  }

  /**
   * Execute the current query based on mode
   */
  async function executeQuery() {
    if (currentMode.value === 'plan') {
      return executePlanQuery()
    }

    if (!question.value.trim() && !attachments.hasAttachments()) return

    setLoadingPhase('validating')
    error.value = null
    results.value = null
    previewData.value = null

    try {
      setLoadingPhase('interpreting', 20)

      if (attachments.hasAttachments()) {
        setLoadingPhase('executing', 40)
        await executeWithAttachments()
      } else if (writeMode.value) {
        setLoadingPhase('executing', 40)
        await executeWritePreview()
      } else {
        setLoadingPhase('executing', 40)
        await executeReadQuery()
      }

      setLoadingPhase('processing', 90)
    } catch (e: unknown) {
      error.value = getErrorDetail(e) || t('smartQueryView.errors.queryError')
    } finally {
      setLoadingPhase('idle')
    }
  }

  /**
   * Execute query with attachments (image analysis)
   */
  async function executeWithAttachments() {
    const attachmentIds = attachments.getAttachmentIds()
    const lang = locale.value === 'de' || locale.value === 'en' ? locale.value : 'de'

    const response = await assistantApi.chat({
      message: question.value.trim() || 'Analysiere das Bild',
      context: {
        current_route: '/smart-query',
        current_entity_id: null,
        current_entity_type: null,
        current_entity_name: null,
        view_mode: 'unknown',
        available_actions: [],
      },
      conversation_history: [],
      mode: 'read',
      language: lang,
      attachment_ids: attachmentIds,
    })

    // Clean up attachments
    await attachments.clearAttachments()

    const data = response.data
    results.value = {
      mode: 'read',
      success: data.success,
      message: data.response?.message || 'Bildanalyse abgeschlossen',
      items: data.response?.data?.items || [],
      total: data.response?.data?.total || 0,
      interpretation: {
        operation: 'image_analysis',
        query: question.value || 'Bildanalyse',
      },
      suggested_actions: data.suggested_actions || [],
    }
  }

  /**
   * Execute write preview (dry run)
   */
  async function executeWritePreview() {
    const response = await api.post('/v1/analysis/smart-write', {
      question: question.value,
      preview_only: true,
      confirmed: false,
    })

    if (response.data.mode === 'preview' && response.data.success) {
      previewData.value = response.data
    } else {
      error.value = response.data.message || t('smartQueryView.errors.noWriteOperation')
    }
  }

  /**
   * Execute read-only query
   */
  async function executeReadQuery() {
    const response = await api.post('/v1/analysis/smart-query', {
      question: question.value,
      allow_write: false,
    })
    results.value = response.data
  }

  /**
   * Confirm and execute write operation
   */
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
        confirmed: true,
      })
      results.value = response.data
      previewData.value = null
      currentStep.value = 4
    } catch (e: unknown) {
      error.value = getErrorDetail(e) || t('smartQuery.createError')
    } finally {
      if (stepInterval) {
        clearInterval(stepInterval)
      }
      loading.value = false
    }
  }

  /**
   * Cancel write preview
   */
  function cancelPreview() {
    previewData.value = null
  }

  /**
   * Reset all state
   */
  function resetAll() {
    results.value = null
    previewData.value = null
    question.value = ''
  }

  /**
   * Adopt a prompt from plan mode
   */
  function adoptPrompt(prompt: string, mode: 'read' | 'write') {
    question.value = prompt
    currentMode.value = mode
    planMode.reset()
    results.value = null
  }

  /**
   * Handle plan mode reset
   */
  function handlePlanReset() {
    planMode.reset()
    question.value = ''
  }

  /**
   * Handle visualization actions
   */
  function handleVisualizationAction(action: string, params: Record<string, unknown>) {
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

  /**
   * Handle history rerun
   */
  function handleHistoryRerun(commandText: string, _interpretation: Record<string, unknown>) {
    question.value = commandText
    currentMode.value = 'write'
    showHistory.value = false
    executeQuery()
  }

  /**
   * Send results to assistant context
   */
  function sendResultsToAssistant() {
    if (!results.value) return

    const isWriteMode = results.value.mode === 'write'
    const summary = isWriteMode
      ? results.value.success
        ? t('smartQueryView.assistant.elementsCreated', {
            count: results.value.created_items?.length || 0,
          })
        : results.value.message || t('smartQueryView.assistant.executionError')
      : t('smartQueryView.assistant.resultsFound', { count: results.value.total || 0 })

    queryContextStore.setResults({
      summary,
      total: results.value.total || results.value.created_items?.length || 0,
      items:
        results.value.items?.slice(0, 5) || results.value.created_items?.slice(0, 5) || [],
      interpretation: results.value.query_interpretation || results.value.interpretation,
      success: results.value.success !== false,
      mode: isWriteMode ? 'write' : 'read',
    })

    router.back()
  }

  /**
   * Initialize from context or URL
   */
  function initializeFromContext(): boolean {
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
    // Core state
    question,
    currentMode,
    loading,
    loadingState,
    error,
    results,
    previewData,
    fromAssistant,
    currentStep,
    showHistory,

    // Attachments (from composed module)
    pendingAttachments: attachments.pendingAttachments,
    isUploading: attachments.isUploading,
    uploadAttachment: attachments.uploadAttachment,
    removeAttachment: attachments.removeAttachment,

    // Plan mode (from composed module)
    planConversation: planMode.conversation,
    planLoading: planMode.loading,
    planError: planMode.error,
    planGeneratedPrompt: planMode.generatedPrompt,

    // Speech (from composed module)
    isListening: speech.isListening,
    hasMicrophone: speech.hasMicrophone,
    interimTranscript: speech.interimTranscript,

    // Computed
    writeMode,
    modeHint,

    // Stores
    historyStore,

    // Methods
    handleVoiceInput,
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
