<template>
  <v-dialog
    v-model="dialogOpen"
    :max-width="DIALOG_SIZES.LG"
    persistent
    scrollable
    role="dialog"
    aria-modal="true"
    :aria-labelledby="dialogTitleId"
  >
    <v-card>
      <v-card-title :id="dialogTitleId" class="d-flex align-center pa-4 bg-primary">
        <v-avatar color="primary-darken-1" size="40" class="mr-3">
          <v-icon color="on-primary" aria-hidden="true">{{ editMode ? 'mdi-database-edit' : 'mdi-database-plus' }}</v-icon>
        </v-avatar>
        <div>
          <div class="text-h6">{{ editMode ? $t('sources.dialog.edit') : $t('sources.dialog.create') }}</div>
          <div v-if="formData.name" class="text-caption opacity-80">{{ formData.name }}</div>
        </div>
      </v-card-title>

      <v-tabs v-model="currentTab" class="dialog-tabs">
        <v-tab value="general">
          <v-icon start>mdi-form-textbox</v-icon>
          {{ $t('sources.tabs.general') }}
        </v-tab>
        <v-tab value="crawl">
          <v-icon start>mdi-cog</v-icon>
          {{ $t('sources.tabs.crawl') }}
        </v-tab>
      </v-tabs>

      <v-card-text class="pa-6 dialog-content-md">
        <v-form ref="formRef" v-model="formValid" :disabled="saving" @submit.prevent="save">
          <v-window v-model="currentTab">
            <!-- General Tab -->
            <v-window-item value="general">
              <!-- Name & Source Type -->
              <v-row>
                <v-col cols="12" md="8">
                  <v-text-field
                    v-model="formData.name"
                    :label="$t('sources.form.name')"
                    :rules="nameRules"
                    required
                    variant="outlined"
                    prepend-inner-icon="mdi-database"
                  />
                </v-col>
                <v-col cols="12" md="4">
                  <v-select
                    v-model="formData.source_type"
                    :items="sourceTypeOptions"
                    item-title="label"
                    item-value="value"
                    :label="$t('sources.form.sourceType')"
                    :rules="[v => !!v || $t('sources.validation.sourceTypeRequired')]"
                    required
                    variant="outlined"
                  >
                    <template #item="{ item, props: itemProps }">
                      <v-list-item v-bind="itemProps">
                        <template #prepend>
                          <v-icon :color="getTypeColor(item.raw.value)">{{ item.raw.icon }}</v-icon>
                        </template>
                      </v-list-item>
                    </template>
                  </v-select>
                </v-col>
              </v-row>

              <!-- Base URL (not for SharePoint) -->
              <v-text-field
                v-if="formData.source_type !== 'SHAREPOINT'"
                v-model="formData.base_url"
                :label="$t('sources.form.baseUrl')"
                :rules="urlRules"
                required
                variant="outlined"
                :hint="$t('sources.form.baseUrlHint')"
                persistent-hint
                prepend-inner-icon="mdi-link"
              />

              <!-- API Endpoint (for API types) -->
              <v-text-field
                v-if="formData.source_type === 'OPARL_API' || formData.source_type === 'CUSTOM_API'"
                v-model="formData.api_endpoint"
                :label="$t('sources.form.apiEndpoint')"
                variant="outlined"
                prepend-inner-icon="mdi-api"
                class="mt-3"
              />

              <!-- SharePoint Configuration -->
              <SharePointConfig
                v-if="formData.source_type === 'SHAREPOINT'"
                v-model="formData.crawl_config"
              />

              <!-- Categories -->
              <v-card variant="outlined" class="mt-4">
                <v-card-title class="text-subtitle-2 pb-2">
                  <v-icon start size="small">mdi-folder-multiple</v-icon>
                  {{ $t('sources.form.categories') }}
                </v-card-title>
                <v-card-text>
                  <p class="text-caption text-medium-emphasis mb-3">{{ $t('sources.form.categoriesHint') }}</p>
                  <div class="d-flex align-center">
                    <v-select
                      v-model="formData.category_ids"
                      :items="categories"
                      item-title="name"
                      item-value="id"
                      multiple
                      chips
                      closable-chips
                      class="flex-grow-1"
                      variant="outlined"
                      density="comfortable"
                    >
                      <template #chip="{ item, index }">
                        <v-chip
                          :color="index === 0 ? 'primary' : 'default'"
                          closable
                          @click:close="formData.category_ids.splice(index, 1)"
                        >
                          {{ item.title }}
                          <v-icon v-if="index === 0" end size="x-small">mdi-star</v-icon>
                        </v-chip>
                      </template>
                    </v-select>
                    <v-btn
                      v-if="formData.category_ids.length > 0"
                      icon="mdi-information-outline"
                      variant="text"
                      size="small"
                      color="primary"
                      class="ml-2"
                      :title="$t('sources.form.primaryCategory')"
                      @click="$emit('show-category-info', formData.category_ids[0])"
                    />
                  </div>
                </v-card-text>
              </v-card>

              <!-- Tags -->
              <v-card variant="outlined" class="mt-4">
                <v-card-title class="text-subtitle-2 pb-2">
                  <v-icon start size="small">mdi-tag-multiple</v-icon>
                  {{ $t('sources.form.tags') }}
                </v-card-title>
                <v-card-text>
                  <v-combobox
                    v-model="formData.tags"
                    :items="tagSuggestions"
                    :label="$t('sources.form.tagsLabel')"
                    :hint="$t('sources.form.tagsHint')"
                    persistent-hint
                    multiple
                    chips
                    closable-chips
                    variant="outlined"
                    density="comfortable"
                    prepend-inner-icon="mdi-tag"
                  >
                    <template #chip="{ props: chipProps, item }">
                      <v-chip
                        v-bind="chipProps"
                        :color="getTagColor(item.value)"
                        size="small"
                      >
                        {{ item.value }}
                      </v-chip>
                    </template>
                  </v-combobox>
                </v-card-text>
              </v-card>

              <!-- Linked Entities (N:M) -->
              <v-card variant="outlined" class="mt-4">
                <v-card-title class="text-subtitle-2 pb-2">
                  <v-icon start size="small">mdi-link-variant</v-icon>
                  {{ $t('sources.form.linkedEntities') }}
                </v-card-title>
                <v-card-text>
                  <p class="text-caption text-medium-emphasis mb-3">{{ $t('sources.form.linkedEntitiesHint') }}</p>

                  <!-- Selected Entities -->
                  <div v-if="selectedEntities.length > 0" class="mb-3">
                    <v-chip
                      v-for="entity in selectedEntities"
                      :key="entity.id"
                      closable
                      color="primary"
                      variant="tonal"
                      class="mr-2 mb-2"
                      @click:close="removeEntity(entity.id)"
                    >
                      <v-icon start size="small">mdi-domain</v-icon>
                      {{ entity.name }}
                      <span v-if="entity.entity_type_name" class="text-caption ml-1 opacity-70">
                        ({{ entity.entity_type_name }})
                      </span>
                    </v-chip>
                    <v-btn
                      icon="mdi-close-circle"
                      variant="text"
                      size="x-small"
                      color="grey"
                      @click="clearAllEntities"
                    />
                  </div>

                  <!-- Entity Search -->
                  <v-autocomplete
                    v-model="entitySearchQuery"
                    v-model:search="entitySearchText"
                    :items="entitySearchResults"
                    :loading="searchingEntities"
                    :label="$t('sources.form.searchEntity')"
                    item-title="name"
                    item-value="id"
                    return-object
                    clearable
                    hide-no-data
                    variant="outlined"
                    density="comfortable"
                    prepend-inner-icon="mdi-magnify"
                    @update:search="searchEntities"
                    @update:model-value="onEntitySelect"
                  >
                    <template #item="{ item, props: itemProps }">
                      <v-list-item v-bind="itemProps">
                        <template #prepend>
                          <v-icon color="primary">mdi-domain</v-icon>
                        </template>
                        <template #subtitle>
                          <span v-if="item.raw.entity_type_name">{{ item.raw.entity_type_name }}</span>
                          <span v-if="item.raw.hierarchy_path" class="text-caption ml-2">{{ item.raw.hierarchy_path }}</span>
                        </template>
                      </v-list-item>
                    </template>
                    <template #no-data>
                      <v-list-item>
                        <v-list-item-title>
                          {{ entitySearchText?.length < 2 ? $t('sources.form.typeToSearch') : $t('sources.form.noEntitiesFound') }}
                        </v-list-item-title>
                      </v-list-item>
                    </template>
                  </v-autocomplete>
                </v-card-text>
              </v-card>
            </v-window-item>

            <!-- Crawl Settings Tab -->
            <v-window-item value="crawl">
              <v-card variant="outlined" class="mb-4">
                <v-card-title class="text-subtitle-2 pb-2">
                  <v-icon start size="small">mdi-cog</v-icon>
                  {{ $t('sources.form.advancedSettings') }}
                </v-card-title>
                <v-card-text>
                  <v-row>
                    <v-col cols="12" md="6">
                      <v-number-input
                        v-model="formData.crawl_config.max_depth"
                        :label="$t('sources.form.maxDepth')"
                        :hint="$t('sources.form.maxDepthHint')"
                        :min="1"
                        :max="10"
                        variant="outlined"
                        control-variant="stacked"
                        persistent-hint
                      />
                    </v-col>
                    <v-col cols="12" md="6">
                      <v-number-input
                        v-model="formData.crawl_config.max_pages"
                        :label="$t('sources.form.maxPages')"
                        :hint="$t('sources.form.maxPagesHint')"
                        :min="1"
                        :max="10000"
                        variant="outlined"
                        control-variant="stacked"
                        persistent-hint
                      />
                    </v-col>
                  </v-row>

                  <v-switch
                    v-model="formData.crawl_config.render_javascript"
                    :label="$t('sources.form.renderJs')"
                    :hint="$t('sources.form.renderJsHint')"
                    persistent-hint
                    color="primary"
                    class="mt-4"
                  />
                </v-card-text>
              </v-card>

              <!-- URL Filters -->
              <v-card variant="outlined" class="mb-4" color="success">
                <v-card-title class="text-subtitle-2 pb-2">
                  <v-icon start size="small" color="success">mdi-check-circle</v-icon>
                  {{ $t('sources.form.includePatterns') }}
                </v-card-title>
                <v-card-text class="pt-4">
                  <v-combobox
                    v-model="formData.crawl_config.url_include_patterns"
                    :hint="$t('sources.form.includeHint')"
                    persistent-hint
                    multiple
                    chips
                    closable-chips
                    clearable
                    variant="outlined"
                    density="comfortable"
                    :error="hasInvalidIncludePatterns"
                    :error-messages="invalidIncludePatternsMessage"
                  >
                    <template #chip="{ item, props: chipProps }">
                      <v-chip
                        v-bind="chipProps"
                        :color="isValidRegexPattern(item.raw) ? 'success' : 'error'"
                        variant="tonal"
                      >
                        <v-icon start size="small">{{ isValidRegexPattern(item.raw) ? 'mdi-check' : 'mdi-alert' }}</v-icon>
                        {{ item.raw }}
                      </v-chip>
                    </template>
                  </v-combobox>
                </v-card-text>
              </v-card>

              <v-card variant="outlined" color="error">
                <v-card-title class="text-subtitle-2 pb-2">
                  <v-icon start size="small" color="error">mdi-close-circle</v-icon>
                  {{ $t('sources.form.excludePatterns') }}
                </v-card-title>
                <v-card-text class="pt-4">
                  <v-combobox
                    v-model="formData.crawl_config.url_exclude_patterns"
                    :hint="$t('sources.form.excludeHint')"
                    persistent-hint
                    multiple
                    chips
                    closable-chips
                    clearable
                    variant="outlined"
                    density="comfortable"
                    :error="hasInvalidExcludePatterns"
                    :error-messages="invalidExcludePatternsMessage"
                  >
                    <template #chip="{ item, props: chipProps }">
                      <v-chip
                        v-bind="chipProps"
                        :color="isValidRegexPattern(item.raw) ? 'error' : 'warning'"
                        variant="tonal"
                      >
                        <v-icon start size="small">{{ isValidRegexPattern(item.raw) ? 'mdi-close' : 'mdi-alert' }}</v-icon>
                        {{ item.raw }}
                      </v-chip>
                    </template>
                  </v-combobox>
                </v-card-text>
              </v-card>
            </v-window-item>
          </v-window>
        </v-form>
      </v-card-text>

      <v-divider />

      <v-card-actions class="pa-4">
        <v-btn variant="tonal" @click="close">{{ $t('common.cancel') }}</v-btn>
        <v-spacer />
        <v-btn
          variant="tonal"
          color="primary"
          :disabled="!formValid"
          :loading="saving"
          @click="save"
        >
          <v-icon start>mdi-check</v-icon>
          {{ $t('common.save') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import { entityApi } from '@/services/api'
import { useSourceHelpers } from '@/composables/useSourceHelpers'
import { useFormValidation } from '@/composables/useFormValidation'
import { useLogger } from '@/composables/useLogger'
import { ENTITY_SEARCH, DIALOG_SIZES } from '@/config/sources'
import { isValidRegexPattern } from '@/utils/csvParser'
import SharePointConfig from './SharePointConfig.vue'
import type { VForm } from 'vuetify/components'
import {
  SOURCE_TYPE_OPTIONS,
  type DataSourceFormData,
} from '@/types/sources'
import type { CategoryResponse } from '@/types/category'
import type { EntityBrief } from '@/stores/entity'

// defineModel() for two-way binding (Vue 3.4+)
const dialogOpen = defineModel<boolean>({ default: false })

const formData = defineModel<DataSourceFormData>('formData', { required: true })

const selectedEntities = defineModel<EntityBrief[]>('selectedEntities', { default: () => [] })

const props = withDefaults(defineProps<Props>(), {
  editMode: false,
  saving: false,
})

// Emits (non-model emits only)
const emit = defineEmits<{
  (e: 'save'): void
  (e: 'show-category-info', categoryId: string): void
}>()

const logger = useLogger('SourceFormDialog')

// Props (non-model props only)
interface Props {
  editMode?: boolean
  categories: CategoryResponse[]
  tagSuggestions: string[]
  saving?: boolean
}

const { getTypeColor, getTagColor } = useSourceHelpers()
const { createRules, usePatternListValidation } = useFormValidation()

// Accessibility: unique dialog title ID
const dialogTitleId = `source-dialog-title-${Math.random().toString(36).substr(2, 9)}`

// Form state
const formRef = ref<VForm | null>(null)
const formValid = ref(false)
const currentTab = ref('general')

// Source type options (from centralized config)
const sourceTypeOptions = SOURCE_TYPE_OPTIONS

// Validation rules (using composable)
const nameRules = createRules.name({ min: 2, max: 200 })
const urlRules = createRules.url()

// Pattern list validation (using composable)
const {
  hasInvalidPatterns: hasInvalidIncludePatterns,
  getInvalidPatternsMessage: invalidIncludePatternsMessage,
} = usePatternListValidation(() => formData.value.crawl_config?.url_include_patterns || [])

const {
  hasInvalidPatterns: hasInvalidExcludePatterns,
  getInvalidPatternsMessage: invalidExcludePatternsMessage,
} = usePatternListValidation(() => formData.value.crawl_config?.url_exclude_patterns || [])

// Entity search
const entitySearchQuery = ref<EntityBrief | null>(null)
const entitySearchText = ref('')
const entitySearchResults = ref<EntityBrief[]>([])
const searchingEntities = ref(false)

/** Internal search function - called by debounced wrapper */
async function performEntitySearch(query: string): Promise<void> {
  searchingEntities.value = true
  try {
    const response = await entityApi.searchEntities({
      q: query,
      per_page: ENTITY_SEARCH.MAX_RESULTS,
    })
    const selectedIds = new Set(selectedEntities.value.map((e) => e.id))
    entitySearchResults.value = (response.data.items || []).filter(
      (e: EntityBrief) => !selectedIds.has(e.id)
    )
  } catch (e) {
    logger.error('Failed to search entities', e)
    entitySearchResults.value = []
  } finally {
    searchingEntities.value = false
  }
}

/** Debounced entity search using VueUse (auto-cleanup on unmount) */
const debouncedEntitySearch = useDebounceFn(performEntitySearch, ENTITY_SEARCH.DEBOUNCE_MS)

/** Search entities with debouncing to reduce API calls */
function searchEntities(query: string) {
  if (!query || query.length < ENTITY_SEARCH.MIN_QUERY_LENGTH) {
    entitySearchResults.value = []
    return
  }
  debouncedEntitySearch(query)
}

function onEntitySelect(entity: EntityBrief | null) {
  if (entity && !selectedEntities.value.find((e) => e.id === entity.id)) {
    selectedEntities.value = [...selectedEntities.value, entity]
    formData.value.extra_data.entity_ids = selectedEntities.value.map((e) => e.id)
  }
  entitySearchQuery.value = null
  entitySearchText.value = ''
  entitySearchResults.value = []
}

function removeEntity(entityId: string) {
  selectedEntities.value = selectedEntities.value.filter((e) => e.id !== entityId)
  formData.value.extra_data.entity_ids = selectedEntities.value.map((e) => e.id)
}

function clearAllEntities() {
  selectedEntities.value = []
  formData.value.extra_data.entity_ids = []
}

// Actions
async function save() {
  if (formRef.value) {
    try {
      const { valid } = await formRef.value.validate()
      if (!valid) return
    } catch (error) {
      logger.error('Form validation error', error)
      return
    }
  }
  emit('save')
}

function close() {
  dialogOpen.value = false
}

// Reset tab when dialog opens
watch(dialogOpen, (open) => {
  if (open) {
    currentTab.value = 'general'
  }
})

// Keyboard shortcuts (Escape to close, Ctrl/Cmd+Enter to save)
const handleKeydown = (e: KeyboardEvent) => {
  if (!dialogOpen.value) return

  if (e.key === 'Escape') {
    e.preventDefault()
    close()
  }

  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
    e.preventDefault()
    if (formValid.value && !props.saving) {
      save()
    }
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})

// Note: VueUse's useDebounceFn handles cleanup automatically on unmount
</script>

<style scoped>
.dialog-tabs {
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
