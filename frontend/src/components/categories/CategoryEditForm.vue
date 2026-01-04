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

      <v-tabs v-model="activeTab" class="dialog-tabs" role="tablist" :aria-label="$t('categories.tabs.ariaLabel')">
        <v-tab value="general" role="tab" :aria-selected="activeTab === 'general'">
          <v-icon start aria-hidden="true">mdi-form-textbox</v-icon>
          {{ $t('categories.tabs.general') }}
        </v-tab>
        <v-tab value="search" role="tab" :aria-selected="activeTab === 'search'">
          <v-icon start aria-hidden="true">mdi-magnify</v-icon>
          {{ $t('categories.tabs.search') }}
        </v-tab>
        <v-tab value="filters" role="tab" :aria-selected="activeTab === 'filters'">
          <v-icon start aria-hidden="true">mdi-filter</v-icon>
          {{ $t('categories.tabs.filters') }}
          <v-icon
            v-if="!formData.url_include_patterns?.length && !formData.url_exclude_patterns?.length"
            color="warning"
            size="x-small"
            class="ml-1"
            :aria-label="$t('categories.tabs.filtersWarning')"
          >
            mdi-alert
          </v-icon>
        </v-tab>
        <v-tab value="ai" role="tab" :aria-selected="activeTab === 'ai'">
          <v-icon start aria-hidden="true">mdi-robot</v-icon>
          {{ $t('categories.tabs.ai') }}
        </v-tab>
        <v-tab v-if="editMode" value="dataSources" role="tab" :aria-selected="activeTab === 'dataSources'">
          <v-icon start aria-hidden="true">mdi-database</v-icon>
          {{ $t('categories.tabs.dataSources') }}
          <v-chip v-if="category?.source_count" size="x-small" color="primary" class="ml-1" aria-hidden="true">
            {{ category.source_count }}
          </v-chip>
          <span v-if="category?.source_count" class="sr-only">
            {{ $t('categories.tabs.sourceCount', { count: category.source_count }) }}
          </span>
        </v-tab>
      </v-tabs>

      <v-card-text class="pa-6 dialog-content-lg">
        <v-form ref="form">
          <v-window v-model="activeTab">
            <!-- General Tab -->
            <v-window-item value="general">
              <CategoryFormGeneral
                :form-data="formData"
                :available-languages="availableLanguages"
                @update:form-data="updateFormData"
              />
            </v-window-item>

            <!-- Search Tab -->
            <v-window-item value="search">
              <CategoryFormSearch
                :form-data="formData"
                @update:form-data="updateFormData"
              />
            </v-window-item>

            <!-- Filters Tab -->
            <v-window-item value="filters">
              <CategoryFormFilters
                :form-data="formData"
                @update:form-data="updateFormData"
              />
            </v-window-item>

            <!-- AI Tab -->
            <v-window-item value="ai">
              <CategoryFormAi
                :form-data="formData"
                @update:form-data="updateFormData"
              />
            </v-window-item>

            <!-- DataSources Tab -->
            <v-window-item v-if="editMode" value="dataSources">
              <CategoryDetailsPanel
                :selected-tags="dataSourcesState.selectedTags"
                :match-mode="dataSourcesState.matchMode"
                :available-tags="dataSourcesState.availableTags"
                :found-sources="dataSourcesState.foundSources"
                :loading="dataSourcesState.loading"
                :assigning="dataSourcesState.assigning"
                :current-source-count="category?.source_count"
                :get-status-color="getStatusColor"
                :get-source-type-icon="getSourceTypeIcon"
                @update:selected-tags="handleTagsUpdate"
                @update:match-mode="handleMatchModeUpdate"
                @assign-all="emit('assign-sources')"
              />
            </v-window-item>
          </v-window>
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
import type { CategoryFormData, Category, DataSourcesTabState } from '@/composables/useCategoriesView'
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
  availableLanguages: Array<{ code: string; name: string; flag: string }>
  dataSourcesState: DataSourcesTabState
  getStatusColor: (status?: string) => string
  getSourceTypeIcon: (type?: string) => string
}

export interface CategoryEditFormEmits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'update:formData', data: CategoryFormData): void
  (e: 'update:dataSourcesState', state: DataSourcesTabState): void
  (e: 'save'): void
  (e: 'assign-sources'): void
}

const activeTab = ref('general')
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
    activeTab.value = 'general'
  }
})
</script>

<style scoped>
.dialog-tabs {
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
