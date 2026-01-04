/**
 * Composable for PySis process and field management.
 *
 * Extracts all business logic from PySisTab.vue for better
 * testability and reusability.
 */
import { ref, computed, watch, onUnmounted, type Ref, type ComputedRef } from 'vue'
import { useI18n } from 'vue-i18n'
import { pysisApi } from '@/services/api'
import { useDateFormatter } from '@/composables/useDateFormatter'
import { useLogger } from '@/composables/useLogger'
import { addToSet, removeFromSet, clearSet } from '@/utils/immutableSet'

// =============================================================================
// Types
// =============================================================================

export interface PySisProcess {
  id: string
  pysis_process_id: string
  name?: string
  field_count?: number
  sync_status?: string
  last_synced_at?: string
  entity_id?: string
}

export interface PySisField {
  id: string
  internal_name: string
  pysis_field_name: string
  field_type: string
  current_value?: string
  ai_extracted_value?: string
  ai_extraction_enabled?: boolean
  ai_extraction_prompt?: string
  value_source?: string
  needs_push?: boolean
  confidence_score?: number
}

export interface PySisHistoryEntry {
  id: string
  value: string
  recorded_at: string
  source: string
  action: string
  confidence_score?: number
  created_at?: string
}

export interface PySisTemplate {
  id: string
  name?: string
  description?: string
  fields?: { internal_name: string; pysis_field_name: string; field_type: string }[]
}

export interface AvailablePySisProcess {
  process_id: string
  name?: string
  description?: string
}

export interface NewProcessForm {
  pysis_process_id: string
  name: string
  template_id: string | null
}

export interface NewFieldForm {
  internal_name: string
  pysis_field_name: string
  field_type: string
  ai_extraction_enabled: boolean
  ai_extraction_prompt: string
}

// =============================================================================
// Composable
// =============================================================================

export function usePySisProcess(
  municipality: Ref<string>,
  options: {
    onProcessCountChange?: (count: number) => void
    onUpdated?: () => void
  } = {},
) {
  const logger = useLogger('usePySisProcess')
  const { t } = useI18n()
  const { formatDate: formatLocaleDate } = useDateFormatter()

  // ==========================================================================
  // State
  // ==========================================================================

  const loading = ref(false)
  const syncing = ref(false)
  const generating = ref(false)
  const processes = ref<PySisProcess[]>([])
  const selectedProcess = ref<PySisProcess | null>(null)
  const fields = ref<PySisField[]>([])
  const templates = ref<PySisTemplate[]>([])
  const availableProcesses = ref<AvailablePySisProcess[]>([])
  const loadingAvailableProcesses = ref(false)

  // Track fields currently being generated
  const generatingFieldIds = ref<Set<string>>(new Set())

  // Polling state
  const pollingIntervals = new Map<string, number>()
  const pendingTimeouts = new Set<number>()

  // History
  const historyEntries = ref<PySisHistoryEntry[]>([])
  const loadingHistory = ref(false)
  const historyField = ref<PySisField | null>(null)

  // PySis-Facets State
  const analyzingForFacets = ref(false)
  const enrichingFacets = ref(false)

  // Field Editor
  const editingField = ref<PySisField | null>(null)
  const editingFieldSettings = ref<PySisField | null>(null)

  // ==========================================================================
  // Computed
  // ==========================================================================

  const sortedFields: ComputedRef<PySisField[]> = computed(() => {
    return [...fields.value].sort((a, b) => {
      // AI-enabled fields first
      if (a.ai_extraction_enabled && !b.ai_extraction_enabled) return -1
      if (!a.ai_extraction_enabled && b.ai_extraction_enabled) return 1
      // Then sort by internal name
      return (a.internal_name || '').localeCompare(b.internal_name || '')
    })
  })

  const fieldTypes = computed(() => [
    { title: t('pysis.fieldTypes.text'), value: 'text' },
    { title: t('pysis.fieldTypes.number'), value: 'number' },
    { title: t('pysis.fieldTypes.date'), value: 'date' },
    { title: t('pysis.fieldTypes.boolean'), value: 'boolean' },
    { title: t('pysis.fieldTypes.list'), value: 'list' },
  ])

  // ==========================================================================
  // Utility Functions
  // ==========================================================================

  const formatDate = (dateStr: string | null | undefined): string => {
    if (!dateStr) return t('results.never')
    return formatLocaleDate(dateStr, 'dd.MM.yyyy HH:mm')
  }

  const getSyncStatusColor = (status?: string): string => {
    if (!status) return 'grey'
    const colors: Record<string, string> = {
      SYNCED: 'success',
      PENDING: 'warning',
      ERROR: 'error',
      NEVER: 'grey',
    }
    return colors[status] || 'grey'
  }

  const getSyncStatusIcon = (status?: string): string => {
    if (!status) return 'mdi-help-circle'
    const icons: Record<string, string> = {
      SYNCED: 'mdi-check-circle',
      PENDING: 'mdi-clock',
      ERROR: 'mdi-alert-circle',
      NEVER: 'mdi-help-circle',
    }
    return icons[status] || 'mdi-help-circle'
  }

  const getSourceColor = (source?: string): string => {
    if (!source) return 'grey'
    const colors: Record<string, string> = {
      AI: 'info',
      MANUAL: 'primary',
      PYSIS: 'purple',
    }
    return colors[source] || 'grey'
  }

  const getConfidenceColor = (score?: number): string => {
    if (!score) return 'grey'
    if (score >= 0.8) return 'success'
    if (score >= 0.5) return 'warning'
    return 'error'
  }

  const truncateValue = (value: string | null | undefined, maxLength = 100): string | null => {
    if (!value) return null
    if (value.length <= maxLength) return value
    return value.substring(0, maxLength) + '...'
  }

  // ==========================================================================
  // History Utilities
  // ==========================================================================

  const getHistoryActionIcon = (action: string): string => {
    const icons: Record<string, string> = {
      accepted: 'mdi-check-circle',
      rejected: 'mdi-close-circle',
      replaced: 'mdi-swap-horizontal',
      restored: 'mdi-restore',
      manual_edit: 'mdi-pencil',
      generated: 'mdi-auto-fix',
      pulled: 'mdi-download',
      pushed: 'mdi-upload',
    }
    return icons[action] || 'mdi-circle'
  }

  const getHistoryActionColor = (action: string): string => {
    const colors: Record<string, string> = {
      accepted: 'success',
      rejected: 'error',
      replaced: 'grey',
      restored: 'info',
      manual_edit: 'primary',
      generated: 'info',
      pulled: 'purple',
      pushed: 'success',
    }
    return colors[action] || 'grey'
  }

  const formatHistoryAction = (action: string): string => {
    const key = `pysis.historyActions.${action}`
    const translated = t(key)
    return translated !== key ? translated : action
  }

  const getHistoryItemClass = (action: string): string => {
    if (action === 'rejected') return 'bg-red-lighten-5'
    if (action === 'accepted') return 'bg-green-lighten-5'
    return ''
  }

  // ==========================================================================
  // API Functions - Load Data
  // ==========================================================================

  const loadProcesses = async (): Promise<void> => {
    if (!municipality.value) return
    try {
      const response = await pysisApi.getProcesses(municipality.value)
      processes.value = response.data.items || []
      options.onProcessCountChange?.(processes.value.length)
    } catch (error) {
      logger.error('Failed to load processes', error)
      options.onProcessCountChange?.(0)
    }
  }

  const loadTemplates = async (): Promise<void> => {
    try {
      const response = await pysisApi.getTemplates({ is_active: true })
      templates.value = response.data.items || []
    } catch (error) {
      logger.error('Failed to load templates', error)
    }
  }

  const loadAvailableProcesses = async (): Promise<void> => {
    if (loadingAvailableProcesses.value) return
    loadingAvailableProcesses.value = true
    try {
      const response = await pysisApi.getAvailableProcesses()
      availableProcesses.value = response.data.items || []
      if (response.data.error) {
        logger.warn('PySis API error:', response.data.error)
      }
    } catch (error) {
      logger.error('Failed to load available processes', error)
      availableProcesses.value = []
    } finally {
      loadingAvailableProcesses.value = false
    }
  }

  const loadFields = async (): Promise<void> => {
    if (!selectedProcess.value) return
    try {
      const response = await pysisApi.getFields(selectedProcess.value.id)
      fields.value = response.data || []
    } catch (error) {
      logger.error('Failed to load fields', error)
    }
  }

  const loadHistory = async (field: PySisField): Promise<void> => {
    historyField.value = field
    historyEntries.value = []
    loadingHistory.value = true
    try {
      const response = await pysisApi.getFieldHistory(field.id, 20)
      historyEntries.value = response.data.items || []
    } catch (error) {
      logger.error('Failed to load history', error)
      throw error
    } finally {
      loadingHistory.value = false
    }
  }

  // ==========================================================================
  // API Functions - CRUD
  // ==========================================================================

  const selectProcess = async (process: PySisProcess): Promise<void> => {
    selectedProcess.value = process
    await loadFields()
  }

  const createProcess = async (data: NewProcessForm): Promise<void> => {
    if (!data.pysis_process_id) {
      throw new Error(t('pysis.enterProcessId'))
    }
    loading.value = true
    try {
      await pysisApi.createProcess(municipality.value, data)
      await loadProcesses()
      options.onUpdated?.()
    } finally {
      loading.value = false
    }
  }

  const deleteProcess = async (process: PySisProcess): Promise<void> => {
    await pysisApi.deleteProcess(process.id)
    if (selectedProcess.value?.id === process.id) {
      selectedProcess.value = null
      fields.value = []
    }
    await loadProcesses()
    options.onUpdated?.()
  }

  const createField = async (data: NewFieldForm): Promise<void> => {
    if (!selectedProcess.value || !data.internal_name || !data.pysis_field_name) {
      throw new Error(t('pysis.fillRequired'))
    }
    loading.value = true
    try {
      await pysisApi.createField(selectedProcess.value.id, data)
      await loadFields()
      await loadProcesses()
    } finally {
      loading.value = false
    }
  }

  const toggleAiExtraction = async (field: PySisField): Promise<void> => {
    try {
      await pysisApi.updateField(field.id, { ai_extraction_enabled: field.ai_extraction_enabled })
    } catch (error) {
      // Revert on error
      field.ai_extraction_enabled = !field.ai_extraction_enabled
      throw error
    }
  }

  const updateFieldSettings = async (fieldSettings: Pick<PySisField, 'id' | 'internal_name' | 'field_type' | 'ai_extraction_enabled' | 'ai_extraction_prompt'>): Promise<void> => {
    loading.value = true
    try {
      await pysisApi.updateField(fieldSettings.id, {
        internal_name: fieldSettings.internal_name,
        field_type: fieldSettings.field_type,
        ai_extraction_enabled: fieldSettings.ai_extraction_enabled,
        ai_extraction_prompt: fieldSettings.ai_extraction_prompt || undefined,
      })

      // Update the field in the local list
      const field = fields.value.find((f) => f.id === fieldSettings.id)
      if (field) {
        field.internal_name = fieldSettings.internal_name
        field.field_type = fieldSettings.field_type
        field.ai_extraction_enabled = fieldSettings.ai_extraction_enabled
        field.ai_extraction_prompt = fieldSettings.ai_extraction_prompt
      }
    } finally {
      loading.value = false
    }
  }

  const deleteField = async (field: PySisField): Promise<void> => {
    await pysisApi.deleteField(field.id)
    await loadFields()
    await loadProcesses()
  }

  const saveFieldValue = async (field: PySisField, value: string | undefined): Promise<void> => {
    await pysisApi.updateFieldValue(field.id, { value, source: 'MANUAL' })
    // Update in list
    const f = fields.value.find((fld) => fld.id === field.id)
    if (f) {
      f.current_value = value
      f.value_source = 'MANUAL'
      f.needs_push = true
    }
  }

  const restoreFromHistory = async (entry: PySisHistoryEntry): Promise<void> => {
    if (!historyField.value) return
    const response = await pysisApi.restoreFromHistory(historyField.value.id, entry.id)
    if (response.data.success) {
      const field = fields.value.find((f) => f.id === historyField.value?.id)
      if (field) {
        field.current_value = response.data.accepted_value
        field.value_source = 'MANUAL'
        field.needs_push = true
      }
    } else {
      throw new Error(response.data.message || t('pysis.error'))
    }
  }

  // ==========================================================================
  // API Functions - Template
  // ==========================================================================

  const applyTemplate = async (templateId: string, overwriteExisting: boolean): Promise<void> => {
    if (!selectedProcess.value || !templateId) return
    loading.value = true
    try {
      await pysisApi.applyTemplate(selectedProcess.value.id, {
        template_id: templateId,
        overwrite_existing: overwriteExisting,
      })
      await loadFields()
      await loadProcesses()
    } finally {
      loading.value = false
    }
  }

  // ==========================================================================
  // API Functions - Sync
  // ==========================================================================

  const pullFromPySis = async (): Promise<{ created: number; updated: number } | null> => {
    if (!selectedProcess.value) return null
    syncing.value = true
    try {
      const response = await pysisApi.pullFromPySis(selectedProcess.value.id)
      if (response.data.success) {
        await loadFields()
        await loadProcesses()
        return {
          created: response.data.fields_created || 0,
          updated: response.data.fields_updated || 0,
        }
      } else {
        throw new Error(response.data.errors?.join(', ') || t('pysis.error'))
      }
    } finally {
      syncing.value = false
    }
  }

  const pushToPySis = async (): Promise<number> => {
    if (!selectedProcess.value) return 0
    syncing.value = true
    try {
      const response = await pysisApi.pushToPySis(selectedProcess.value.id)
      if (response.data.success) {
        await loadFields()
        await loadProcesses()
        return response.data.fields_synced || 0
      } else {
        throw new Error(response.data.errors?.join(', ') || t('pysis.error'))
      }
    } finally {
      syncing.value = false
    }
  }

  const pushFieldToPySis = async (field: PySisField): Promise<void> => {
    const response = await pysisApi.pushFieldToPySis(field.id)
    if (response.data.success) {
      await loadFields()
    } else {
      throw new Error(response.data.errors?.join(', ') || t('pysis.error'))
    }
  }

  // ==========================================================================
  // API Functions - AI Generation
  // ==========================================================================

  const generateAllFields = async (): Promise<number> => {
    if (!selectedProcess.value) return 0
    generating.value = true
    try {
      const response = await pysisApi.generateFields(selectedProcess.value.id)
      if (response.data.success) {
        // Poll for updates after a delay
        const timeoutId = setTimeout(() => {
          pendingTimeouts.delete(timeoutId as unknown as number)
          loadFields()
        }, 5000) as unknown as number
        pendingTimeouts.add(timeoutId)
        return response.data.fields_generated || 0
      } else {
        throw new Error(response.data.errors?.join(', ') || t('pysis.error'))
      }
    } finally {
      generating.value = false
    }
  }

  const generateField = async (field: PySisField): Promise<void> => {
    const response = await pysisApi.generateField(field.id)
    if (response.data.success) {
      generatingFieldIds.value = addToSet(generatingFieldIds.value, field.id)
      pollForFieldCompletion(field.id, field.internal_name)
    } else {
      throw new Error(response.data.errors?.join(', ') || t('pysis.error'))
    }
  }

  const acceptAiSuggestion = async (field: PySisField): Promise<void> => {
    const response = await pysisApi.acceptAiSuggestion(field.id)
    if (response.data.success) {
      field.current_value = response.data.accepted_value
      field.value_source = 'AI'
      field.ai_extracted_value = undefined
      field.needs_push = true
    } else {
      throw new Error(response.data.message || t('pysis.error'))
    }
  }

  const rejectAiSuggestion = async (field: PySisField): Promise<void> => {
    const response = await pysisApi.rejectAiSuggestion(field.id)
    if (response.data.success) {
      field.ai_extracted_value = undefined
      field.confidence_score = undefined
    } else {
      throw new Error(response.data.message || t('pysis.error'))
    }
  }

  // ==========================================================================
  // API Functions - PySis-Facets Integration
  // ==========================================================================

  const analyzeForFacets = async (options: {
    includeEmpty: boolean
    minConfidence: number
  }): Promise<string> => {
    if (!selectedProcess.value?.entity_id) {
      throw new Error(t('pysis.facets.needsEntity'))
    }
    analyzingForFacets.value = true
    try {
      const response = await pysisApi.analyzeForFacets({
        entity_id: selectedProcess.value.entity_id,
        process_id: selectedProcess.value.id,
        include_empty: options.includeEmpty,
        min_confidence: options.minConfidence,
      })
      if (response.data.success) {
        return response.data.task_id || ''
      } else {
        throw new Error(response.data.message || t('pysis.error'))
      }
    } finally {
      analyzingForFacets.value = false
    }
  }

  const enrichFacetsFromPysis = async (overwrite: boolean): Promise<string> => {
    if (!selectedProcess.value?.entity_id) {
      throw new Error(t('pysis.facets.needsEntity'))
    }
    enrichingFacets.value = true
    try {
      const response = await pysisApi.enrichFacetsFromPysis({
        entity_id: selectedProcess.value.entity_id,
        overwrite,
      })
      if (response.data.success) {
        return response.data.task_id || ''
      } else {
        throw new Error(response.data.message || t('pysis.error'))
      }
    } finally {
      enrichingFacets.value = false
    }
  }

  // ==========================================================================
  // Polling Logic
  // ==========================================================================

  const pollForFieldCompletion = (fieldId: string, fieldName: string): void => {
    // Clear any existing interval for this field
    if (pollingIntervals.has(fieldId)) {
      clearInterval(pollingIntervals.get(fieldId))
    }

    const checkField = async () => {
      if (!generatingFieldIds.value.has(fieldId) || !selectedProcess.value) {
        stopGenerating(fieldId)
        return
      }

      try {
        const response = await pysisApi.getFields(selectedProcess.value.id)
        const updatedFields = response.data || []
        const updatedField = updatedFields.find((f: PySisField) => f.id === fieldId)

        if (updatedField?.ai_extracted_value) {
          stopGenerating(fieldId)
          fields.value = updatedFields
          // Return field name for snackbar message
          return fieldName
        }
      } catch (error) {
        logger.error('Polling error', error)
      }
    }

    // Start polling every 2 seconds
    const intervalId = setInterval(checkField, 2000) as unknown as number
    pollingIntervals.set(fieldId, intervalId)

    // Also check immediately after a short delay
    const initialTimeoutId = setTimeout(() => {
      pendingTimeouts.delete(initialTimeoutId as unknown as number)
      checkField()
    }, 1500) as unknown as number
    pendingTimeouts.add(initialTimeoutId)
  }

  const stopGenerating = (fieldId: string): void => {
    generatingFieldIds.value = removeFromSet(generatingFieldIds.value, fieldId)
    if (pollingIntervals.has(fieldId)) {
      clearInterval(pollingIntervals.get(fieldId))
      pollingIntervals.delete(fieldId)
    }
  }

  const stopAllGenerating = (): void => {
    pollingIntervals.forEach((intervalId) => clearInterval(intervalId))
    pollingIntervals.clear()
    pendingTimeouts.forEach((timeoutId) => clearTimeout(timeoutId))
    pendingTimeouts.clear()
    generatingFieldIds.value = clearSet()
  }

  // ==========================================================================
  // Field Editor
  // ==========================================================================

  const openFieldEditor = (field: PySisField): void => {
    editingField.value = { ...field }
  }

  const closeFieldEditor = (): void => {
    editingField.value = null
  }

  const openFieldSettings = (field: PySisField): void => {
    editingFieldSettings.value = {
      id: field.id,
      internal_name: field.internal_name,
      pysis_field_name: field.pysis_field_name,
      field_type: field.field_type,
      ai_extraction_enabled: field.ai_extraction_enabled,
      ai_extraction_prompt: field.ai_extraction_prompt || '',
    }
  }

  const closeFieldSettings = (): void => {
    editingFieldSettings.value = null
  }

  // ==========================================================================
  // Watchers
  // ==========================================================================

  watch(municipality, () => {
    selectedProcess.value = null
    fields.value = []
    loadProcesses()
  })

  // ==========================================================================
  // Cleanup
  // ==========================================================================

  onUnmounted(() => {
    stopAllGenerating()
  })

  // ==========================================================================
  // Return
  // ==========================================================================

  return {
    // State
    loading,
    syncing,
    generating,
    processes,
    selectedProcess,
    fields,
    templates,
    availableProcesses,
    loadingAvailableProcesses,
    generatingFieldIds,
    historyEntries,
    loadingHistory,
    historyField,
    analyzingForFacets,
    enrichingFacets,
    editingField,
    editingFieldSettings,

    // Computed
    sortedFields,
    fieldTypes,

    // Utilities
    formatDate,
    getSyncStatusColor,
    getSyncStatusIcon,
    getSourceColor,
    getConfidenceColor,
    truncateValue,
    getHistoryActionIcon,
    getHistoryActionColor,
    formatHistoryAction,
    getHistoryItemClass,

    // API - Load
    loadProcesses,
    loadTemplates,
    loadAvailableProcesses,
    loadFields,
    loadHistory,

    // API - CRUD
    selectProcess,
    createProcess,
    deleteProcess,
    createField,
    toggleAiExtraction,
    updateFieldSettings,
    deleteField,
    saveFieldValue,
    restoreFromHistory,

    // API - Template
    applyTemplate,

    // API - Sync
    pullFromPySis,
    pushToPySis,
    pushFieldToPySis,

    // API - AI
    generateAllFields,
    generateField,
    acceptAiSuggestion,
    rejectAiSuggestion,

    // API - Facets
    analyzeForFacets,
    enrichFacetsFromPysis,

    // Polling
    stopGenerating,
    stopAllGenerating,

    // Field Editor
    openFieldEditor,
    closeFieldEditor,
    openFieldSettings,
    closeFieldSettings,
  }
}
