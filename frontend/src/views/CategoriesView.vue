<template>
  <div>
    <PageHeader
      :title="$t('categories.title')"
      :subtitle="$t('categories.subtitle')"
      icon="mdi-folder-multiple"
      :count="filteredCategories.length"
    >
      <template #actions>
        <v-btn variant="tonal" color="primary" @click="openCreateDialog">
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
      @update:filters="categoryFilters = $event"
    />

    <!-- Categories Table -->
    <CategoriesTree
      :categories="filteredCategories"
      :loading="loading"
      :language-options="languageFilterOptions"
      @edit="openEditDialog"
      @delete="confirmDelete"
      @view-sources="showSourcesForCategory"
      @start-crawl="openCrawlerDialog"
      @create-summary="openSummaryDialog"
      @reanalyze="confirmReanalyze"
    />

    <!-- Create/Edit Dialog -->
    <CategoryEditForm
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
      v-model="deleteDialog"
      :title="$t('categories.dialog.delete')"
      :message="$t('categories.dialog.deleteConfirm', { name: selectedCategory?.name })"
      :confirm-text="$t('common.delete')"
      @confirm="handleDeleteCategory"
    />

    <!-- Reanalyze Confirmation -->
    <CategoryReanalyzeDialog
      v-model="reanalyzeDialog"
      :category-name="selectedCategory?.name || ''"
      v-model:reanalyze-all="reanalyzeAll"
      @confirm="handleReanalyzeDocuments"
    />

    <!-- Sources for Category Dialog -->
    <CategorySourcesDialog
      v-model="sourcesDialog"
      :category="selectedCategoryForSources"
      :sources="categorySources"
      :stats="categorySourcesStats"
      @navigate-to-sources="navigateToSourcesFiltered"
    />

    <!-- Start Crawler Dialog -->
    <CategoryCrawlerDialog
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
      v-model="aiPreviewDialog"
      :loading="aiPreviewLoading"
      :saving="savingWithAi"
      :preview-data="aiPreviewData"
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
      v-model="summaryCreateDialog"
      :initial-prompt="summaryInitialPrompt"
      @created="handleSummaryCreated"
    />

    <!-- Snackbar for feedback -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="3000">
      {{ snackbar.text }}
    </v-snackbar>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { adminApi } from '@/services/api'
import {
  useCategoriesView,
  useCategoryCrawler,
  useCategoryDataSources,
  type CategoryFormData,
  type Category,
} from '@/composables/useCategoriesView'
import { useLogger } from '@/composables/useLogger'
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

const logger = useLogger('CategoriesView')
const { t } = useI18n()
const router = useRouter()

// Main state from composables
const {
  loading,
  categories,
  selectedCategory,
  categorySources,
  categoryFilters,
  snackbar,
  filteredCategories,
  statusFilterOptions,
  documentFilterOptions,
  languageFilterOptions,
  availableLanguages,
  categorySourcesStats,
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
  availableTags,
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

// Summary states
const summaryInitialPrompt = ref('')
const summaryTriggerCategory = ref<Category | null>(null)

// AI Preview states
const aiPreviewLoading = ref(false)
const aiPreviewData = ref<any>(null)
const savingWithAi = ref(false)
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
  ai_extraction_prompt: '',
  is_active: true,
})

// Methods
const openCreateDialog = () => {
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
    ai_extraction_prompt: '',
    is_active: true,
  }
  dialog.value = true
}

const openEditDialog = async (category: Category) => {
  editMode.value = true
  selectedCategory.value = category
  formData.value = {
    ...category,
    search_terms: category.search_terms || [],
    document_types: category.document_types || [],
    languages: category.languages || ['de'],
    url_include_patterns: category.url_include_patterns || [],
    url_exclude_patterns: category.url_exclude_patterns || [],
  }
  resetDataSourcesTab()
  dialog.value = true
  await loadAvailableTags()
}

const saveCategory = async () => {
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
    selectedFacetTypes.value = response.data.suggested_facet_types.map((ft: any) => ft.selected !== false)
    selectedEntityTypeOption.value = response.data.suggested_entity_type.is_new ? 'new' : (response.data.suggested_entity_type.id || 'new')
  } catch (error: any) {
    logger.error('Failed to get AI preview:', error)
    aiPreviewDialog.value = false
    dialog.value = true

    const errorMessage = error.response?.data?.detail || t('categories.aiPreview.error')
    showSnackbar(errorMessage, 'error')
  } finally {
    aiPreviewLoading.value = false
  }
}

const saveWithoutAiSetup = async () => {
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
  selectedCategory.value = category
  deleteDialog.value = true
}

const handleDeleteCategory = async () => {
  if (selectedCategory.value) {
    const success = await deleteCategory(selectedCategory.value.id)
    if (success) {
      deleteDialog.value = false
    }
  }
}

const confirmReanalyze = (category: Category) => {
  selectedCategory.value = category
  reanalyzeAll.value = false
  reanalyzeDialog.value = true
}

const handleReanalyzeDocuments = async () => {
  if (selectedCategory.value) {
    const success = await reanalyzeDocuments(selectedCategory.value.id, reanalyzeAll.value)
    if (success) {
      reanalyzeDialog.value = false
    }
  }
}

const showSourcesForCategory = async (category: Category) => {
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
  const result = await startFilteredCrawl()
  if (result) {
    showSnackbar(result.message, result.success ? 'success' : 'error')
  }
}

const handleFacetTypeUpdate = (payload: { index: number; value: boolean }) => {
  selectedFacetTypes.value[payload.index] = payload.value
}

const handleDataSourcesStateUpdate = (newState: any) => {
  const oldTags = dataSourcesTab.value.selectedTags
  dataSourcesTab.value = newState

  // Trigger search if tags changed
  if (selectedCategory.value && JSON.stringify(oldTags) !== JSON.stringify(newState.selectedTags)) {
    searchSourcesByTags(selectedCategory.value.id, categorySources.value)
  }
}

const handleAssignSources = async () => {
  if (!selectedCategory.value) return

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

// Lifecycle
onMounted(() => {
  loadCategories()
})
</script>

<style scoped>
/* Styles moved to child components */
</style>
