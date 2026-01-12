<template>
  <v-dialog
    :model-value="modelValue"
    :max-width="DIALOG_SIZES.XL"
    persistent
    scrollable
    role="dialog"
    :aria-labelledby="titleId"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <v-card>
      <v-card-title :id="titleId" class="d-flex align-center pa-4 bg-primary">
        <v-avatar color="primary-darken-1" size="40" class="mr-3" aria-hidden="true">
          <v-icon color="on-primary">
            {{ editMode ? 'mdi-folder-edit' : 'mdi-folder-plus' }}
          </v-icon>
        </v-avatar>
        <div>
          <div class="text-h6">
            {{ editMode ? $t('categories.dialog.edit') : $t('categories.dialog.create') }}
          </div>
          <div v-if="formData.name" class="text-caption opacity-80">
            {{ formData.name }}
          </div>
        </div>
      </v-card-title>

      <v-divider />

      <v-card-text class="pa-6 dialog-content-lg">
        <v-form ref="form">
          <v-alert type="info" variant="tonal" class="mb-6">
            <div class="text-subtitle-2">{{ $t('categories.form.info.title') }}</div>
            <div class="text-body-2">{{ $t('categories.form.info.description') }}</div>
          </v-alert>

          <CategoryAiPrefillPanel
            v-if="!editMode"
            :prompt="aiPrefillPrompt"
            :loading="aiPrefillLoading"
            :error="aiPrefillError"
            :suggestions="aiPrefillSuggestions"
            :overwrite="aiPrefillOverwrite"
            @update:prompt="emit('update:aiPrefillPrompt', $event)"
            @update:overwrite="emit('update:aiPrefillOverwrite', $event)"
            @generate="emit('generate-ai-prefill')"
            @apply="emit('apply-ai-prefill')"
          />

          <v-expansion-panels v-model="expandedPanels" multiple variant="accordion" :aria-label="$t('categories.tabs.ariaLabel')">
            <v-expansion-panel value="general">
              <v-expansion-panel-title>
                <v-icon start aria-hidden="true">mdi-form-textbox</v-icon>
                <span class="font-weight-medium">1. {{ $t('categories.tabs.general') }}</span>
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <CategoryFormGeneral
                  :form-data="formData"
                  :available-languages="availableLanguages"
                  @update:form-data="updateFormData"
                />
              </v-expansion-panel-text>
            </v-expansion-panel>

            <v-expansion-panel value="search">
              <v-expansion-panel-title>
                <v-icon start aria-hidden="true">mdi-magnify</v-icon>
                <span class="font-weight-medium">2. {{ $t('categories.tabs.search') }}</span>
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <CategoryFormSearch
                  :form-data="formData"
                  @update:form-data="updateFormData"
                />
              </v-expansion-panel-text>
            </v-expansion-panel>

            <v-expansion-panel value="filters">
              <v-expansion-panel-title>
                <v-icon start aria-hidden="true">mdi-filter</v-icon>
                <span class="font-weight-medium">3. {{ $t('categories.tabs.filters') }}</span>
                <v-icon
                  v-if="!formData.url_include_patterns?.length && !formData.url_exclude_patterns?.length"
                  color="warning"
                  size="small"
                  class="ml-2"
                  :aria-label="$t('categories.tabs.filtersWarning')"
                >
                  mdi-alert
                </v-icon>
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <CategoryFormFilters
                  :form-data="formData"
                  @update:form-data="updateFormData"
                />
              </v-expansion-panel-text>
            </v-expansion-panel>

            <v-expansion-panel value="ai">
              <v-expansion-panel-title>
                <v-icon start aria-hidden="true">mdi-robot</v-icon>
                <span class="font-weight-medium">4. {{ $t('categories.tabs.ai') }}</span>
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <CategoryFormAi
                  :form-data="formData"
                  @update:form-data="updateFormData"
                />
              </v-expansion-panel-text>
            </v-expansion-panel>

            <v-expansion-panel value="dataSources">
              <v-expansion-panel-title>
                <v-icon start aria-hidden="true">mdi-database</v-icon>
                <span class="font-weight-medium">5. {{ $t('categories.tabs.dataSources') }}</span>
                <v-chip v-if="category?.source_count" size="x-small" color="primary" class="ml-2" aria-hidden="true">
                  {{ category.source_count }}
                </v-chip>
                <span v-if="category?.source_count" class="sr-only">
                  {{ $t('categories.tabs.sourceCount', { count: category.source_count }) }}
                </span>
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <CategoryDetailsPanel
                  :selected-tags="dataSourcesState.selectedTags"
                  :match-mode="dataSourcesState.matchMode"
                  :available-tags="dataSourcesState.availableTags"
                  :found-sources="dataSourcesState.foundSources"
                  :loading="dataSourcesState.loading"
                  :assigning="dataSourcesState.assigning"
                  :current-source-count="category?.source_count"
                  :edit-mode="editMode"
                  :category="category"
                  :direct-selected-sources="dataSourcesState.directSelectedSources"
                  :source-search-results="dataSourcesState.sourceSearchResults"
                  :searching-direct-sources="dataSourcesState.searchingDirectSources"
                  :assigned-sources="dataSourcesState.assignedSources"
                  :assigned-sources-total="dataSourcesState.assignedSourcesTotal"
                  :assigned-sources-loading="dataSourcesState.assignedSourcesLoading"
                  :assigned-sources-page="dataSourcesState.assignedSourcesPage"
                  :assigned-sources-per-page="dataSourcesState.assignedSourcesPerPage"
                  :assigned-sources-search="dataSourcesState.assignedSourcesSearch"
                  :assigned-sources-tag-filter="dataSourcesState.assignedSourcesTagFilter"
                  :available-tags-in-assigned="dataSourcesState.availableTagsInAssigned"
                  :get-status-color="getStatusColor"
                  :get-source-type-icon="getSourceTypeIcon"
                  @update:selected-tags="handleTagsUpdate"
                  @update:match-mode="handleMatchModeUpdate"
                  @assign-all="emit('assign-sources')"
                  @search-sources="emit('search-sources', $event)"
                  @update:direct-selected-sources="emit('update:directSelectedSources', $event)"
                  @assign-direct="emit('assign-direct', $event)"
                  @update:assigned-sources-page="emit('update:assignedSourcesPage', $event)"
                  @update:assigned-sources-per-page="emit('update:assignedSourcesPerPage', $event)"
                  @update:assigned-sources-search="emit('update:assignedSourcesSearch', $event)"
                  @update:assigned-sources-tag-filter="emit('update:assignedSourcesTagFilter', $event)"
                  @unassign-source="emit('unassign-source', $event)"
                />
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-form>
      </v-card-text>

      <v-divider />

      <v-card-actions class="pa-4">
        <v-btn
          variant="tonal"
          :aria-label="$t('common.cancel')"
          @click="emit('update:modelValue', false)"
        >
          {{ $t('common.cancel') }}
        </v-btn>
        <v-spacer />
        <v-btn
          variant="tonal"
          color="primary"
          :aria-label="editMode ? $t('common.save') + ' ' + formData.name : $t('common.save')"
          @click="handleSave"
        >
          <v-icon start aria-hidden="true">mdi-check</v-icon>
          {{ $t('common.save') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { DIALOG_SIZES } from '@/config/ui'
import { generateAriaId } from '@/utils/dialogAccessibility'
import type { CategoryFormData, Category, DataSourcesTabState, CategorySource } from '@/composables/useCategoriesView'
import type { CategoryAiPrefillSuggestion } from '@/types/category'
import CategoryAiPrefillPanel from './CategoryAiPrefillPanel.vue'
import CategoryFormGeneral from './CategoryFormGeneral.vue'
import CategoryFormSearch from './CategoryFormSearch.vue'
import CategoryFormFilters from './CategoryFormFilters.vue'
import CategoryFormAi from './CategoryFormAi.vue'
import CategoryDetailsPanel from './CategoryDetailsPanel.vue'

const props = defineProps<CategoryEditFormProps>()

const emit = defineEmits<CategoryEditFormEmits>()

// Accessibility IDs
const titleId = generateAriaId('category-edit-title')

export interface CategoryEditFormProps {
  modelValue: boolean
  editMode: boolean
  category: Category | null
  formData: CategoryFormData
  aiPrefillPrompt: string
  aiPrefillLoading: boolean
  aiPrefillError: string | null
  aiPrefillSuggestions: CategoryAiPrefillSuggestion | null
  aiPrefillOverwrite: boolean
  availableLanguages: Array<{ code: string; name: string; flag: string }>
  dataSourcesState: DataSourcesTabState
  getStatusColor: (status?: string) => string
  getSourceTypeIcon: (type?: string) => string
}

export interface CategoryEditFormEmits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'update:formData', data: CategoryFormData): void
  (e: 'update:dataSourcesState', state: DataSourcesTabState): void
  (e: 'update:aiPrefillPrompt', value: string): void
  (e: 'update:aiPrefillOverwrite', value: boolean): void
  (e: 'generate-ai-prefill'): void
  (e: 'apply-ai-prefill'): void
  (e: 'save'): void
  (e: 'assign-sources'): void
  // Direct source selection
  (e: 'search-sources', query: string): void
  (e: 'update:directSelectedSources', sources: CategorySource[]): void
  (e: 'assign-direct', sources: CategorySource[]): void
  // Assigned sources
  (e: 'update:assignedSourcesPage', page: number): void
  (e: 'update:assignedSourcesPerPage', perPage: number): void
  (e: 'update:assignedSourcesSearch', search: string): void
  (e: 'update:assignedSourcesTagFilter', tags: string[]): void
  (e: 'unassign-source', sourceId: string): void
}

const expandedPanels = ref<string[]>([])
const form = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)

const updateFormData = (data: Partial<CategoryFormData>) => {
  emit('update:formData', {
    ...props.formData,
    ...data,
  })
}

const handleTagsUpdate = (tags: string[]) => {
  emit('update:dataSourcesState', {
    ...props.dataSourcesState,
    selectedTags: tags,
  })
}

const handleMatchModeUpdate = (mode: 'all' | 'any' | null) => {
  if (mode === null) return  // Ignore null selections
  emit('update:dataSourcesState', {
    ...props.dataSourcesState,
    matchMode: mode,
  })
}

const handleSave = async () => {
  const { valid } = await form.value?.validate() ?? { valid: false }
  if (valid) {
    emit('save')
  }
}

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    expandedPanels.value = []
  }
})
</script>
