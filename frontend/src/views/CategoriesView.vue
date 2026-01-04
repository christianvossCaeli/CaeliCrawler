<template>
  <div>
    <!-- Skeleton/Content Transition -->
    <transition name="fade" mode="out-in">
      <!-- Skeleton Loader for initial load -->
      <CategoriesSkeleton v-if="loading && initialLoad" key="skeleton" />

      <!-- Main Content -->
      <div v-else key="content">
    <PageHeader
      :title="$t('categories.title')"
      :subtitle="$t('categories.subtitle')"
      icon="mdi-folder-multiple"
      :count="totalCategories"
    >
      <template #actions>
        <v-btn v-if="canEdit" variant="tonal" color="primary" @click="openCreateDialog">
          <v-icon left>mdi-plus</v-icon>
          {{ $t('categories.actions.create') }}
        </v-btn>
      </template>
    </PageHeader>

    <!-- Filters Toolbar -->
    <CategoriesToolbar
      :filters="categoryFilters"
      :status-options="statusFilterOptions"
      :document-options="documentFilterOptions"
      :language-options="languageFilterOptions"
      @update:filters="handleFiltersUpdate"
      @search="handleSearchSubmit"
    />

    <!-- Categories Table -->
    <CategoriesTree
      :categories="categories"
      :loading="loading"
      :language-options="languageFilterOptions"
      :total="totalCategories"
      :page="categoryPage"
      :items-per-page="categoryPerPage"
      :sort-by="categorySortBy"
      :sort-order="categorySortOrder"
      :can-edit="canEdit"
      :can-admin="canAdmin"
      @update:options="handleTableOptionsUpdate"
      @edit="openEditDialog"
      @delete="confirmDelete"
      @view-sources="showSourcesForCategory"
      @start-crawl="openCrawlerDialog"
      @create-summary="openSummaryDialog"
      @reanalyze="confirmReanalyze"
    />

    <!-- Create/Edit Dialog -->
    <CategoryEditForm
      v-if="canEdit"
      v-model="dialog"
      :edit-mode="editMode"
      :category="selectedCategory"
      :form-data="formData"
      :available-languages="availableLanguages"
      :data-sources-state="dataSourcesTab"
      :get-status-color="getStatusColor"
      :get-source-type-icon="getSourceTypeIcon"
      @update:form-data="formData = $event"
      @update:data-sources-state="handleDataSourcesStateUpdate"
      @save="saveCategory"
      @assign-sources="handleAssignSources"
    />

    <!-- Delete Confirmation -->
    <ConfirmDialog
      v-if="canAdmin"
      v-model="deleteDialog"
      :title="$t('categories.dialog.delete')"
      :message="$t('categories.dialog.deleteConfirm', { name: selectedCategory?.name })"
      :confirm-text="$t('common.delete')"
      @confirm="handleDeleteCategory"
    />

    <!-- Reanalyze Confirmation -->
    <CategoryReanalyzeDialog
      v-if="canAdmin"
      v-model="reanalyzeDialog"
      v-model:reanalyze-all="reanalyzeAll"
      :category-name="selectedCategory?.name || ''"
      @confirm="handleReanalyzeDocuments"
    />

    <!-- Sources for Category Dialog -->
    <CategorySourcesDialog
      v-if="canEdit"
      v-model="sourcesDialog"
      :category="selectedCategoryForSources"
      :sources="categorySources"
      :total="categorySourcesTotal"
      :stats="categorySourcesStats"
      :loading="categorySourcesLoading"
      :page="categorySourcesPage"
      :per-page="categorySourcesPerPage"
      :search="categorySourcesSearch"
      @update:page="handleSourcesPageChange"
      @update:per-page="handleSourcesPerPageChange"
      @update:search="handleSourcesSearch"
      @navigate-to-sources="navigateToSourcesFiltered"
    />

    <!-- Start Crawler Dialog -->
    <CategoryCrawlerDialog
      v-if="canEdit"
      v-model="crawlerDialog"
      :category="selectedCategoryForCrawler"
      :filter="crawlerFilter"
      :filtered-count="crawlerFilteredCount"
      :starting="startingCrawler"
      @update:filter="handleCrawlerFilterUpdate"
      @reset-filters="resetCrawlerFilters"
      @start="handleStartFilteredCrawl"
    />

    <!-- AI Setup Preview Dialog -->
    <CategoryAiPreviewDialog
      v-if="canEdit"
      v-model="aiPreviewDialog"
      :loading="aiPreviewLoading"
      :saving="savingWithAi"
      :preview-data="adaptedAiPreviewData"
      :selected-entity-type-option="selectedEntityTypeOption"
      :selected-facet-types="selectedFacetTypes"
      :extraction-prompt="editableExtractionPrompt"
      @update:selected-entity-type-option="selectedEntityTypeOption = $event"
      @update:extraction-prompt="editableExtractionPrompt = $event"
      @update-facet-type="handleFacetTypeUpdate"
      @save-without-ai="saveWithoutAiSetup"
      @save-with-ai="saveWithAiSetup"
    />

    <!-- Summary Create Dialog -->
    <SummaryCreateDialog
      v-if="canEdit"
      v-model="summaryCreateDialog"
      :initial-prompt="summaryInitialPrompt"
      @created="handleSummaryCreated"
    />

      </div>
    </transition>

    <!-- Snackbar for feedback -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="3000">
      {{ snackbar.text }}
    </v-snackbar>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { adminApi } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import {
  useCategoriesView,
  useCategoryCrawler,
  useCategoryDataSources,
  type CategoryFormData,
  type Category,
  type DataSourcesTabState,
} from '@/composables/useCategoriesView'
import {
  type CategoryAiPreviewData,
  type AdaptedCategoryAiPreviewData,
  adaptCategoryAiPreviewData,
} from '@/types/category'
import { useLogger } from '@/composables/useLogger'
import { getErrorMessage } from '@/utils/errorMessage'
import { usePageContextProvider, PAGE_FEATURES, PAGE_ACTIONS } from '@/composables/usePageContext'
import type { PageContextData } from '@/composables/assistant/types'
import PageHeader from '@/components/common/PageHeader.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import CategoriesToolbar from '@/components/categories/CategoriesToolbar.vue'
import CategoriesTree from '@/components/categories/CategoriesTree.vue'
import CategoryEditForm from '@/components/categories/CategoryEditForm.vue'
import CategorySourcesDialog from '@/components/categories/CategorySourcesDialog.vue'
import CategoryCrawlerDialog from '@/components/categories/CategoryCrawlerDialog.vue'
import CategoryAiPreviewDialog from '@/components/categories/CategoryAiPreviewDialog.vue'
import CategoryReanalyzeDialog from '@/components/categories/CategoryReanalyzeDialog.vue'
import SummaryCreateDialog from '@/components/summaries/SummaryCreateDialog.vue'
import CategoriesSkeleton from '@/components/categories/CategoriesSkeleton.vue'

const logger = useLogger('CategoriesView')

// Initial load state
const initialLoad = ref(true)
const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()

const canEdit = computed(() => auth.isEditor)
const canAdmin = computed(() => auth.isAdmin)

// Main state from composables
const {
  loading,
  categories,
  selectedCategory,
  categorySources,
  categorySourcesLoading,
  categoryFilters,
  snackbar,
  totalCategories,
  categoryPage,
  categoryPerPage,
  categorySortBy,
  categorySortOrder,
  statusFilterOptions,
  documentFilterOptions,
  languageFilterOptions,
  availableLanguages,
  categorySourcesStats,
  categorySourcesTotal,
  categorySourcesPage,
  categorySourcesPerPage,
  categorySourcesSearch,
  loadCategories,
  showSnackbar,
  deleteCategory,
  reanalyzeDocuments,
  loadSourcesForCategory,
  navigateToSourcesFiltered: navigateToSourcesFilteredComposable,
  getStatusColor,
  getSourceTypeIcon,
} = useCategoriesView()

// Crawler state from composable
const {
  crawlerDialog,
  startingCrawler,
  selectedCategoryForCrawler,
  crawlerFilteredCount,
  crawlerFilter,
  handleCrawlerFilterUpdate,
  resetCrawlerFilters,
  openCrawlerDialog,
  startFilteredCrawl,
} = useCategoryCrawler()

// DataSources state from composable
const {
  dataSourcesTab,
  loadAvailableTags,
  searchSourcesByTags,
  assignSourcesByTags,
  resetDataSourcesTab,
} = useCategoryDataSources()

// Dialog states
const dialog = ref(false)
const deleteDialog = ref(false)
const reanalyzeDialog = ref(false)
const sourcesDialog = ref(false)
const summaryCreateDialog = ref(false)
const aiPreviewDialog = ref(false)

// Edit mode states
const editMode = ref(false)
const reanalyzeAll = ref(false)
const selectedCategoryForSources = ref<Category | null>(null)

// Page Context Provider for AI Assistant awareness
usePageContextProvider(
  '/categories',
  (): PageContextData => ({
    // Category context
    category_id: selectedCategory.value?.id || undefined,
    category_name: selectedCategory.value?.name || undefined,
    category_entity_count: selectedCategory.value?.document_count || 0,
    crawl_status: selectedCategoryForCrawler.value ? 'running' : 'idle',

    // List context
    total_count: totalCategories.value,
    filters: categoryFilters.value ? {
      search_query: categoryFilters.value.search || undefined
    } : undefined,

    // Features and actions
    available_features: [...PAGE_FEATURES.category],
    available_actions: [
      ...PAGE_ACTIONS.base,
      ...PAGE_ACTIONS.category
    ]
  })
)

// Summary states
const summaryInitialPrompt = ref('')
const summaryTriggerCategory = ref<Category | null>(null)

// AI Preview states - using types from @/types/category
const aiPreviewLoading = ref(false)
const aiPreviewData = ref<CategoryAiPreviewData | null>(null)
const savingWithAi = ref(false)

// Adapted preview data using imported helper function
const adaptedAiPreviewData = computed<AdaptedCategoryAiPreviewData | null>(() =>
  adaptCategoryAiPreviewData(aiPreviewData.value)
)
const selectedEntityTypeOption = ref<string>('new')
const selectedFacetTypes = ref<boolean[]>([])
const editableExtractionPrompt = ref('')

// Form state
const formData = ref<CategoryFormData>({
  name: '',
  description: '',
  purpose: '',
  search_terms: [],
  document_types: [],
  languages: ['de'],
  url_include_patterns: [],
  url_exclude_patterns: [],
  schedule_cron: '0 2 * * *',
  schedule_enabled: false,
  ai_extraction_prompt: '',
  is_active: true,
  extraction_handler: 'default',
  is_public: false,
  target_entity_type_id: null,
})

// Methods
const openCreateDialog = () => {
  if (!canEdit.value) {
    showSnackbar(t('common.forbidden'), 'error')
    return
  }
  editMode.value = false
  formData.value = {
    name: '',
    description: '',
    purpose: '',
    search_terms: [],
    document_types: [],
    languages: ['de'],
    url_include_patterns: [],
    url_exclude_patterns: [],
    schedule_cron: '0 2 * * *',
    schedule_enabled: false,
    ai_extraction_prompt: '',
    is_active: true,
    extraction_handler: 'default',
    is_public: false,
    target_entity_type_id: null,
  }
  dialog.value = true
}

const openEditDialog = async (category: Category) => {
  if (!canEdit.value) {
    showSnackbar(t('common.forbidden'), 'error')
    return
  }
  editMode.value = true
  selectedCategory.value = category
  formData.value = {
    name: category.name,
    description: category.description || '',
    purpose: category.purpose,
    search_terms: category.search_terms || [],
    document_types: category.document_types || [],
    languages: category.languages || ['de'],
    url_include_patterns: category.url_include_patterns || [],
    url_exclude_patterns: category.url_exclude_patterns || [],
    schedule_cron: category.schedule_cron || '0 2 * * *',
    schedule_enabled: category.schedule_enabled ?? false,
    ai_extraction_prompt: category.ai_extraction_prompt || '',
    is_active: category.is_active,
    extraction_handler: category.extraction_handler || 'default',
    is_public: category.is_public ?? false,
    target_entity_type_id: category.target_entity_type_id || null,
  }
  resetDataSourcesTab()
  dialog.value = true
  await loadAvailableTags()
}

const saveCategory = async () => {
  if (!canEdit.value) {
    showSnackbar(t('common.forbidden'), 'error')
    return
  }
  try {
    if (editMode.value && selectedCategory.value) {
      await adminApi.updateCategory(selectedCategory.value.id, formData.value)
      dialog.value = false
      await loadCategories()
      showSnackbar(t('categories.messages.updated'), 'success')
    } else {
      dialog.value = false
      await showAiPreview()
    }
  } catch (error) {
    logger.error('Failed to save category:', error)
    showSnackbar(t('categories.messages.saveError'), 'error')
  }
}

const showAiPreview = async () => {
  if (!canEdit.value) {
    showSnackbar(t('common.forbidden'), 'error')
    return
  }
  aiPreviewDialog.value = true
  aiPreviewLoading.value = true
  aiPreviewData.value = null

  try {
    const response = await adminApi.previewCategoryAiSetup({
      name: formData.value.name,
      purpose: formData.value.purpose,
      description: formData.value.description || undefined,
    })

    aiPreviewData.value = response.data
    editableExtractionPrompt.value = response.data.suggested_extraction_prompt || ''
    selectedFacetTypes.value = (response.data.suggested_facet_types || []).map((ft: { selected?: boolean }) => ft.selected !== false)
    const entityType = response.data.suggested_entity_type
    selectedEntityTypeOption.value = entityType?.is_new ? 'new' : (entityType?.id || 'new')
  } catch (error) {
    logger.error('Failed to get AI preview:', error)
    aiPreviewDialog.value = false
    dialog.value = true

    const errorMessage = getErrorMessage(error) || t('categories.aiPreview.error')
    showSnackbar(errorMessage, 'error')
  } finally {
    aiPreviewLoading.value = false
  }
}

const saveWithoutAiSetup = async () => {
  if (!canEdit.value) {
    showSnackbar(t('common.forbidden'), 'error')
    return
  }
  try {
    await adminApi.createCategory(formData.value)
    aiPreviewDialog.value = false
    await loadCategories()
    showSnackbar(t('categories.messages.created'), 'success')
  } catch (error) {
    logger.error('Failed to save category:', error)
    showSnackbar(t('categories.messages.saveError'), 'error')
  }
}

const saveWithAiSetup = async () => {
  if (!aiPreviewData.value) return
  if (!canEdit.value) {
    showSnackbar(t('common.forbidden'), 'error')
    return
  }

  savingWithAi.value = true
  try {
    const categoryData: Record<string, unknown> = {
      ...formData.value,
      ai_extraction_prompt: editableExtractionPrompt.value,
      search_terms: formData.value.search_terms?.length
        ? formData.value.search_terms
        : aiPreviewData.value.suggested_search_terms,
      url_include_patterns: formData.value.url_include_patterns?.length
        ? formData.value.url_include_patterns
        : aiPreviewData.value.suggested_url_include_patterns,
      url_exclude_patterns: formData.value.url_exclude_patterns?.length
        ? formData.value.url_exclude_patterns
        : aiPreviewData.value.suggested_url_exclude_patterns,
    }

    if (selectedEntityTypeOption.value !== 'new') {
      categoryData.target_entity_type_id = selectedEntityTypeOption.value
    }

    await adminApi.createCategory(categoryData)
    aiPreviewDialog.value = false
    await loadCategories()
    showSnackbar(t('categories.messages.createdWithAi'), 'success')
  } catch (error) {
    logger.error('Failed to save category with AI setup:', error)
    showSnackbar(t('categories.messages.saveError'), 'error')
  } finally {
    savingWithAi.value = false
  }
}

const confirmDelete = (category: Category) => {
  if (!canAdmin.value) {
    showSnackbar(t('common.forbidden'), 'error')
    return
  }
  selectedCategory.value = category
  deleteDialog.value = true
}

const handleDeleteCategory = async () => {
  if (selectedCategory.value) {
    if (!canAdmin.value) {
      showSnackbar(t('common.forbidden'), 'error')
      return
    }
    const success = await deleteCategory(selectedCategory.value.id)
    if (success) {
      deleteDialog.value = false
    }
  }
}

const confirmReanalyze = (category: Category) => {
  if (!canAdmin.value) {
    showSnackbar(t('common.forbidden'), 'error')
    return
  }
  selectedCategory.value = category
  reanalyzeAll.value = false
  reanalyzeDialog.value = true
}

const handleReanalyzeDocuments = async () => {
  if (selectedCategory.value) {
    if (!canAdmin.value) {
      showSnackbar(t('common.forbidden'), 'error')
      return
    }
    const success = await reanalyzeDocuments(selectedCategory.value.id, reanalyzeAll.value)
    if (success) {
      reanalyzeDialog.value = false
    }
  }
}

const showSourcesForCategory = async (category: Category) => {
  if (!canEdit.value) {
    showSnackbar(t('common.forbidden'), 'error')
    return
  }
  selectedCategoryForSources.value = category
  sourcesDialog.value = true
  await loadSourcesForCategory(category.id)
}

const navigateToSourcesFiltered = () => {
  if (selectedCategoryForSources.value) {
    sourcesDialog.value = false
    navigateToSourcesFilteredComposable(selectedCategoryForSources.value.id)
  }
}

const handleStartFilteredCrawl = async () => {
  if (!canEdit.value) {
    showSnackbar(t('common.forbidden'), 'error')
    return
  }
  const result = await startFilteredCrawl()
  if (result) {
    showSnackbar(result.message, result.success ? 'success' : 'error')
  }
}

const handleFacetTypeUpdate = (payload: { index: number; value: boolean }) => {
  selectedFacetTypes.value[payload.index] = payload.value
}

const handleDataSourcesStateUpdate = (newState: DataSourcesTabState) => {
  const oldTags = dataSourcesTab.value.selectedTags
  dataSourcesTab.value = newState

  // Trigger search if tags changed
  if (selectedCategory.value && JSON.stringify(oldTags) !== JSON.stringify(newState.selectedTags)) {
    searchSourcesByTags(selectedCategory.value.id, categorySources.value)
  }
}

const handleAssignSources = async () => {
  if (!selectedCategory.value) return
  if (!canEdit.value) {
    showSnackbar(t('common.forbidden'), 'error')
    return
  }

  const result = await assignSourcesByTags(selectedCategory.value.id)
  if (result) {
    showSnackbar(result.message, result.success ? 'success' : 'error')

    if (result.success) {
      await loadCategories()
      const updatedCategory = categories.value.find(c => c.id === selectedCategory.value?.id)
      if (updatedCategory) {
        selectedCategory.value = updatedCategory
      }
      await searchSourcesByTags(selectedCategory.value.id, categorySources.value)
    }
  }
}

const openSummaryDialog = (category: Category) => {
  if (!canEdit.value) {
    showSnackbar(t('common.forbidden'), 'error')
    return
  }
  summaryTriggerCategory.value = category
  const entityTypeName = category.target_entity_type?.name || category.name
  const purpose = category.purpose || ''
  summaryInitialPrompt.value = t('categories.summaryPromptTemplate', {
    name: category.name,
    entityType: entityTypeName,
    purpose: purpose,
  })
  summaryCreateDialog.value = true
}

const handleSummaryCreated = (result: { id: string; name: string }) => {
  showSnackbar(t('summaries.messages.created', { name: result.name }), 'success')
  router.push({ name: 'summary-dashboard', params: { id: result.id } })
}

// Filter and pagination handlers
const handleFiltersUpdate = (newFilters: typeof categoryFilters.value) => {
  categoryFilters.value = newFilters
  categoryPage.value = 1 // Reset to first page on filter change
  loadCategories()
}

const handleSearchSubmit = () => {
  categoryPage.value = 1
  loadCategories()
}

const handleTableOptionsUpdate = (options: { page: number; itemsPerPage: number; sortBy?: string; sortOrder?: 'asc' | 'desc' }) => {
  categoryPage.value = options.page
  categoryPerPage.value = options.itemsPerPage
  if (options.sortBy) categorySortBy.value = options.sortBy
  if (options.sortOrder) categorySortOrder.value = options.sortOrder
  loadCategories()
}

// Sources dialog pagination handlers
const handleSourcesPageChange = (page: number) => {
  if (selectedCategoryForSources.value) {
    loadSourcesForCategory(selectedCategoryForSources.value.id, { page })
  }
}

const handleSourcesPerPageChange = (perPage: number) => {
  if (selectedCategoryForSources.value) {
    loadSourcesForCategory(selectedCategoryForSources.value.id, { perPage, page: 1 })
  }
}

let sourcesSearchTimeout: ReturnType<typeof setTimeout> | null = null
const handleSourcesSearch = (search: string) => {
  if (sourcesSearchTimeout) clearTimeout(sourcesSearchTimeout)
  sourcesSearchTimeout = setTimeout(() => {
    if (selectedCategoryForSources.value) {
      loadSourcesForCategory(selectedCategoryForSources.value.id, { search, page: 1 })
    }
  }, 300)
}

// Lifecycle
onMounted(async () => {
  await loadCategories()
  initialLoad.value = false
})
</script>

<style scoped>
/* Styles moved to child components */
</style>
