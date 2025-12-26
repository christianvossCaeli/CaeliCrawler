<template>
  <v-dialog
    :model-value="modelValue"
    max-width="900"
    persistent
    scrollable
    @update:model-value="emit('update:modelValue', $event)"
  >
    <v-card>
      <v-card-title class="d-flex align-center pa-4 bg-primary">
        <v-avatar color="primary-darken-1" size="40" class="mr-3">
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

      <v-tabs v-model="activeTab" class="dialog-tabs">
        <v-tab value="general">
          <v-icon start>mdi-form-textbox</v-icon>
          {{ $t('categories.tabs.general') }}
        </v-tab>
        <v-tab value="search">
          <v-icon start>mdi-magnify</v-icon>
          {{ $t('categories.tabs.search') }}
        </v-tab>
        <v-tab value="filters">
          <v-icon start>mdi-filter</v-icon>
          {{ $t('categories.tabs.filters') }}
          <v-icon
            v-if="!formData.url_include_patterns?.length && !formData.url_exclude_patterns?.length"
            color="warning"
            size="x-small"
            class="ml-1"
          >
            mdi-alert
          </v-icon>
        </v-tab>
        <v-tab value="ai">
          <v-icon start>mdi-robot</v-icon>
          {{ $t('categories.tabs.ai') }}
        </v-tab>
        <v-tab v-if="editMode" value="dataSources">
          <v-icon start>mdi-database</v-icon>
          {{ $t('categories.tabs.dataSources') }}
          <v-chip v-if="category?.source_count" size="x-small" color="primary" class="ml-1">
            {{ category.source_count }}
          </v-chip>
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
        <v-btn variant="tonal" @click="emit('update:modelValue', false)">
          {{ $t('common.cancel') }}
        </v-btn>
        <v-spacer />
        <v-btn variant="tonal" color="primary" @click="handleSave">
          <v-icon start>mdi-check</v-icon>
          {{ $t('common.save') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { CategoryFormData, Category, DataSourcesTabState } from '@/composables/useCategoriesView'
import CategoryFormGeneral from './CategoryFormGeneral.vue'
import CategoryFormSearch from './CategoryFormSearch.vue'
import CategoryFormFilters from './CategoryFormFilters.vue'
import CategoryFormAi from './CategoryFormAi.vue'
import CategoryDetailsPanel from './CategoryDetailsPanel.vue'

export interface CategoryEditFormProps {
  modelValue: boolean
  editMode: boolean
  category: Category | null
  formData: CategoryFormData
  availableLanguages: Array<{ code: string; name: string; flag: string }>
  dataSourcesState: DataSourcesTabState
  getStatusColor: (status: string) => string
  getSourceTypeIcon: (type: string) => string
}

export interface CategoryEditFormEmits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'update:formData', data: CategoryFormData): void
  (e: 'update:dataSourcesState', state: DataSourcesTabState): void
  (e: 'save'): void
  (e: 'assign-sources'): void
}

const props = defineProps<CategoryEditFormProps>()
const emit = defineEmits<CategoryEditFormEmits>()

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
