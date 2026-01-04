/**
 * Composable for Category AI Setup functionality
 *
 * Handles AI-powered category setup preview, entity type suggestions,
 * facet type suggestions, and extraction prompt generation.
 */
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { categoryApi } from '@/services/api/categories'
import { useLogger } from '@/composables/useLogger'
import { getErrorMessage } from '@/utils/errorMessage'
import type {
  CategoryAiPreviewData,
  AdaptedCategoryAiPreviewData,
  CategoryFormData,
} from '@/types/category'
import { adaptCategoryAiPreviewData } from '@/types/category'

const logger = useLogger('useCategoryAiSetup')

/**
 * AI Setup state
 */
export interface AiSetupState {
  /** Whether AI preview is loading */
  loading: boolean
  /** Whether saving with AI is in progress */
  saving: boolean
  /** Raw AI preview data */
  previewData: CategoryAiPreviewData | null
  /** Selected entity type option ('new' or existing ID) */
  selectedEntityType: string
  /** Selected facet types (boolean array matching suggested types) */
  selectedFacetTypes: boolean[]
  /** Editable extraction prompt */
  extractionPrompt: string
}

/**
 * Default AI setup state
 */
export const DEFAULT_AI_SETUP_STATE: AiSetupState = {
  loading: false,
  saving: false,
  previewData: null,
  selectedEntityType: 'new',
  selectedFacetTypes: [],
  extractionPrompt: '',
}

/**
 * Composable for managing AI-powered category setup
 */
export function useCategoryAiSetup() {
  const { t } = useI18n()

  // AI Setup state
  const loading = ref(false)
  const saving = ref(false)
  const previewData = ref<CategoryAiPreviewData | null>(null)
  const selectedEntityType = ref<string>('new')
  const selectedFacetTypes = ref<boolean[]>([])
  const extractionPrompt = ref('')

  // AbortController for request cancellation
  let abortController: AbortController | null = null

  /**
   * Adapted preview data with required fields
   */
  const adaptedPreviewData = computed<AdaptedCategoryAiPreviewData | null>(() =>
    adaptCategoryAiPreviewData(previewData.value)
  )

  /**
   * Check if preview data is available
   */
  const hasPreviewData = computed(() => previewData.value !== null)

  /**
   * Reset AI setup state to defaults
   */
  function resetState() {
    loading.value = false
    saving.value = false
    previewData.value = null
    selectedEntityType.value = 'new'
    selectedFacetTypes.value = []
    extractionPrompt.value = ''
  }

  /**
   * Cancel ongoing AI preview request
   */
  function cancelRequest() {
    if (abortController) {
      abortController.abort()
      abortController = null
    }
  }

  /**
   * Fetch AI preview for category setup
   */
  async function fetchPreview(formData: CategoryFormData): Promise<{
    success: boolean
    error?: string
  }> {
    // Cancel any ongoing request
    cancelRequest()

    loading.value = true
    previewData.value = null

    try {
      abortController = new AbortController()

      const response = await categoryApi.previewAiSetup({
        name: formData.name,
        purpose: formData.purpose,
        description: formData.description || undefined,
      })

      previewData.value = response.data

      // Initialize selection states from response
      extractionPrompt.value = response.data.suggested_extraction_prompt || ''
      selectedFacetTypes.value = (response.data.suggested_facet_types || []).map(
        (ft: { selected?: boolean }) => ft.selected !== false
      )

      const entityType = response.data.suggested_entity_type
      selectedEntityType.value = entityType?.is_new
        ? 'new'
        : entityType?.id || 'new'

      return { success: true }
    } catch (error) {
      // Ignore abort errors
      if ((error as Error).name === 'AbortError') {
        return { success: false, error: 'cancelled' }
      }

      logger.error('Failed to get AI preview:', error)
      const errorMessage =
        getErrorMessage(error) || t('categories.aiPreview.error')

      return { success: false, error: errorMessage }
    } finally {
      loading.value = false
      abortController = null
    }
  }

  /**
   * Update selected facet type at index
   */
  function updateFacetTypeSelection(index: number, selected: boolean) {
    if (index >= 0 && index < selectedFacetTypes.value.length) {
      selectedFacetTypes.value[index] = selected
    }
  }

  /**
   * Get category data merged with AI suggestions
   */
  function getMergedCategoryData(
    formData: CategoryFormData
  ): Record<string, unknown> {
    if (!previewData.value) {
      return { ...formData }
    }

    const categoryData: Record<string, unknown> = {
      ...formData,
      ai_extraction_prompt: extractionPrompt.value,
      // Use form data if provided, otherwise fall back to AI suggestions
      search_terms: formData.search_terms?.length
        ? formData.search_terms
        : previewData.value.suggested_search_terms,
      url_include_patterns: formData.url_include_patterns?.length
        ? formData.url_include_patterns
        : previewData.value.suggested_url_include_patterns,
      url_exclude_patterns: formData.url_exclude_patterns?.length
        ? formData.url_exclude_patterns
        : previewData.value.suggested_url_exclude_patterns,
    }

    // Set target entity type if not creating new
    if (selectedEntityType.value !== 'new') {
      categoryData.target_entity_type_id = selectedEntityType.value
    }

    return categoryData
  }

  /**
   * Get selected facet types from preview data
   */
  function getSelectedFacetTypes() {
    if (!previewData.value?.suggested_facet_types) {
      return []
    }

    return previewData.value.suggested_facet_types.filter(
      (_, index) => selectedFacetTypes.value[index]
    )
  }

  return {
    // State
    loading,
    saving,
    previewData,
    selectedEntityType,
    selectedFacetTypes,
    extractionPrompt,

    // Computed
    adaptedPreviewData,
    hasPreviewData,

    // Actions
    resetState,
    cancelRequest,
    fetchPreview,
    updateFacetTypeSelection,
    getMergedCategoryData,
    getSelectedFacetTypes,
  }
}

export default useCategoryAiSetup
