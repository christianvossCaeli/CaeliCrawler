<template>
  <v-dialog v-model="isOpen" :max-width="DIALOG_SIZES.XL" persistent scrollable>
    <v-card>
      <v-card-title class="d-flex align-center pa-4 bg-info">
        <v-avatar color="info-darken-1" size="40" class="mr-3">
          <v-icon color="on-info">mdi-api</v-icon>
        </v-avatar>
        <div>
          <div class="text-h6">{{ $t('sources.apiImport.title') }}</div>
          <div class="text-caption opacity-80">{{ $t('sources.apiImport.subtitle') }}</div>
        </div>
      </v-card-title>

      <v-card-text class="pa-6">
        <!-- Error Alert -->
        <v-alert
          v-if="errorMessage"
          type="error"
          variant="tonal"
          closable
          class="mb-4"
          @click:close="errorMessage = ''"
        >
          {{ errorMessage }}
        </v-alert>

        <!-- API Type Selection -->
        <v-row>
          <v-col cols="12" md="6">
            <v-select
              v-model="apiType"
              :items="apiTypes"
              :label="$t('sources.apiImport.apiType')"
              variant="outlined"
              density="comfortable"
              @update:model-value="onApiTypeChange"
            >
              <template v-slot:item="{ item, props }">
                <v-list-item v-bind="props">
                  <template v-slot:prepend>
                    <v-icon :color="item.raw.color">{{ item.raw.icon }}</v-icon>
                  </template>
                </v-list-item>
              </template>
            </v-select>
          </v-col>
          <v-col cols="12" md="6">
            <v-select
              v-model="selectedTemplate"
              :items="filteredTemplates"
              item-title="name"
              item-value="id"
              :label="$t('sources.apiImport.template')"
              variant="outlined"
              density="comfortable"
              clearable
              @update:model-value="onTemplateSelect"
            >
              <template v-slot:item="{ item, props }">
                <v-list-item v-bind="props">
                  <v-list-item-subtitle>{{ item.raw.description }}</v-list-item-subtitle>
                </v-list-item>
              </template>
            </v-select>
          </v-col>
        </v-row>

        <!-- API URL -->
        <v-text-field
          v-model="apiUrl"
          :label="$t('sources.apiImport.apiUrl')"
          :hint="getApiUrlHint"
          persistent-hint
          variant="outlined"
          prepend-inner-icon="mdi-link"
          class="mb-4"
        ></v-text-field>

        <!-- API-specific Parameters -->
        <v-card v-if="apiType === 'wikidata'" variant="outlined" class="mb-4">
          <v-card-title class="text-subtitle-2 pb-2">
            <v-icon start size="small">mdi-database-search</v-icon>
            {{ $t('sources.apiImport.sparqlQuery') }}
          </v-card-title>
          <v-card-text>
            <v-textarea
              v-model="sparqlQuery"
              :placeholder="$t('sources.apiImport.sparqlPlaceholder')"
              rows="8"
              variant="outlined"
              class="sparql-textarea"
              :hint="$t('sources.apiImport.sparqlHint')"
              persistent-hint
            ></v-textarea>
          </v-card-text>
        </v-card>

        <!-- Categories Selection -->
        <v-card variant="outlined" class="mb-4">
          <v-card-title class="text-subtitle-2 pb-2">
            <v-icon start size="small">mdi-folder-multiple</v-icon>
            {{ $t('sources.form.categories') }}
          </v-card-title>
          <v-card-text>
            <v-select
              v-model="categoryIds"
              :items="categories"
              item-title="name"
              item-value="id"
              multiple
              chips
              closable-chips
              variant="outlined"
              density="comfortable"
              :rules="[v => v.length > 0 || $t('common.required')]"
            >
              <template v-slot:chip="{ item, index }">
                <v-chip
                  :color="index === 0 ? 'primary' : 'default'"
                  closable
                  @click:close="categoryIds.splice(index, 1)"
                >
                  {{ item.title }}
                  <v-icon v-if="index === 0" end size="x-small">mdi-star</v-icon>
                </v-chip>
              </template>
            </v-select>
          </v-card-text>
        </v-card>

        <!-- Default Tags -->
        <v-card variant="outlined" class="mb-4">
          <v-card-title class="text-subtitle-2 pb-2">
            <v-icon start size="small">mdi-tag-multiple</v-icon>
            {{ $t('sources.bulk.defaultTags') }}
          </v-card-title>
          <v-card-text>
            <v-combobox
              v-model="defaultTags"
              :items="availableTags"
              :label="$t('sources.bulk.defaultTagsHint')"
              multiple
              chips
              closable-chips
              variant="outlined"
              density="comfortable"
              prepend-inner-icon="mdi-tag"
            >
              <template #chip="{ props, item }">
                <v-chip
                  v-bind="props"
                  :color="getTagColor(item.value)"
                  size="small"
                >
                  {{ item.value }}
                </v-chip>
              </template>
            </v-combobox>
          </v-card-text>
        </v-card>

        <!-- Preview Button -->
        <div class="d-flex justify-center mb-4">
          <v-btn
            variant="tonal"
            color="info"
            @click="loadPreview"
            :loading="loadingPreview"
            :disabled="!canPreview"
          >
            <v-icon start>mdi-eye</v-icon>
            {{ $t('sources.bulk.loadPreview') }}
          </v-btn>
        </div>

        <!-- Preview Table -->
        <v-card v-if="preview.length > 0" variant="outlined">
          <v-card-title class="text-subtitle-2 pb-2 d-flex justify-space-between align-center">
            <span>
              <v-icon start size="small">mdi-table</v-icon>
              {{ $t('sources.bulk.preview') }} ({{ preview.length }} / {{ totalAvailable }})
            </span>
            <span class="text-caption">
              <v-chip size="x-small" color="success" class="mr-1">{{ validCount }} {{ $t('sources.bulk.valid') }}</v-chip>
              <v-chip size="x-small" color="error" v-if="errorCount > 0">{{ errorCount }} {{ $t('sources.bulk.errors') }}</v-chip>
            </span>
          </v-card-title>
          <v-card-text class="pa-0">
            <v-table density="compact" class="preview-table">
              <thead>
                <tr>
                  <th style="width: 40px;"></th>
                  <th>{{ $t('sources.columns.name') }}</th>
                  <th>{{ $t('sources.columns.url') }}</th>
                  <th>{{ $t('sources.form.tags') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, idx) in preview.slice(0, 20)" :key="item.base_url || idx" :class="{ 'bg-error-lighten-5': item.error }">
                  <td>
                    <v-icon v-if="item.error" color="error" size="small">mdi-alert-circle</v-icon>
                    <v-icon v-else color="success" size="small">mdi-check-circle</v-icon>
                  </td>
                  <td class="text-truncate" style="max-width: 200px;">{{ item.name }}</td>
                  <td class="text-truncate text-caption" style="max-width: 250px;">{{ item.base_url }}</td>
                  <td>
                    <template v-for="(tag, tagIdx) in getAllTags(item)" :key="tag">
                      <v-chip v-if="tagIdx < 3" size="x-small" :color="getTagColor(tag)" class="mr-1">{{ tag }}</v-chip>
                    </template>
                    <span v-if="getAllTags(item).length > 3" class="text-caption">+{{ getAllTags(item).length - 3 }}</span>
                  </td>
                </tr>
                <tr v-if="preview.length > 20">
                  <td colspan="4" class="text-center text-caption">
                    ... {{ preview.length - 20 }} {{ $t('sources.bulk.moreEntries') }}
                  </td>
                </tr>
              </tbody>
            </v-table>
          </v-card-text>
        </v-card>

        <!-- Options -->
        <v-switch
          v-model="skipDuplicates"
          :label="$t('sources.form.skipDuplicates')"
          color="primary"
          class="mt-4"
        ></v-switch>
      </v-card-text>

      <v-divider></v-divider>

      <v-card-actions class="pa-4">
        <v-btn variant="tonal" @click="close">{{ $t('common.cancel') }}</v-btn>
        <v-spacer></v-spacer>
        <v-btn
          variant="tonal"
          color="primary"
          @click="executeImport"
          :disabled="!canImport"
          :loading="importing"
        >
          <v-icon start>mdi-download</v-icon>
          {{ totalAvailable }} {{ $t('sources.bulk.sourcesImport') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
/**
 * ApiImportDialog - Import sources from external APIs
 *
 * Supports Wikidata SPARQL, OParl, and custom API imports.
 */
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { adminApi } from '@/services/api'
import { useSourceHelpers } from '@/composables/useSourceHelpers'
import { useLogger } from '@/composables/useLogger'
import { DIALOG_SIZES } from '@/config/sources'
import type { CategoryResponse } from '@/types/category'

const logger = useLogger('ApiImportDialog')

interface ApiTemplate {
  id: string
  name: string
  description: string
  api_type: string
  default_url?: string
  parameters: Record<string, unknown>
  default_tags: string[]
}

interface PreviewItem {
  name: string
  base_url: string
  source_type: string
  suggested_tags: string[]
  extra_data: Record<string, unknown>
  error?: string
}

// Props (non-model props only)
interface Props {
  categories: CategoryResponse[]
  availableTags: string[]
}

const props = defineProps<Props>()

// defineModel() for two-way binding (Vue 3.4+)
const isOpen = defineModel<boolean>({ default: false })

// Emits (non-model emits only)
const emit = defineEmits<{
  (e: 'imported', count: number): void
}>()

const { t } = useI18n()
const { getTagColor } = useSourceHelpers()

// State

const templates = ref<ApiTemplate[]>([])
const selectedTemplate = ref<string | null>(null)
const apiType = ref('wikidata')
const apiUrl = ref('')
const sparqlQuery = ref('')
const categoryIds = ref<string[]>([])
const defaultTags = ref<string[]>([])
const skipDuplicates = ref(true)
const preview = ref<PreviewItem[]>([])
const totalAvailable = ref(0)
const loadingPreview = ref(false)
const importing = ref(false)
const errorMessage = ref('')

// Computed
const apiTypes = computed(() => [
  { value: 'wikidata', title: t('sources.apiImport.wikidata'), icon: 'mdi-database-search', color: 'blue' },
  { value: 'oparl', title: t('sources.apiImport.oparl'), icon: 'mdi-api', color: 'green' },
  { value: 'custom', title: t('sources.apiImport.custom'), icon: 'mdi-code-json', color: 'grey' },
])
const filteredTemplates = computed(() => {
  return templates.value.filter(tmpl => tmpl.api_type === apiType.value)
})

const canPreview = computed(() => {
  if (!apiUrl.value) return false
  if (apiType.value === 'wikidata' && !sparqlQuery.value.trim()) return false
  return true
})

const canImport = computed(() => {
  return categoryIds.value.length > 0 && validCount.value > 0
})

const validCount = computed(() => {
  return preview.value.filter(item => !item.error).length
})

const errorCount = computed(() => {
  return preview.value.filter(item => item.error).length
})

const getApiUrlHint = computed(() => {
  switch (apiType.value) {
    case 'wikidata':
      return 'https://query.wikidata.org/sparql'
    case 'oparl':
      return 'https://oparl.org/api/bodies'
    default:
      return 'REST API endpoint URL'
  }
})

// Methods
const loadTemplates = async () => {
  try {
    const response = await adminApi.getApiImportTemplates()
    templates.value = response.data
  } catch (error) {
    logger.error('Failed to load templates', error)
  }
}

const onApiTypeChange = () => {
  selectedTemplate.value = null
  preview.value = []
  totalAvailable.value = 0
  errorMessage.value = ''

  // Set default URL
  switch (apiType.value) {
    case 'wikidata':
      apiUrl.value = 'https://query.wikidata.org/sparql'
      break
    case 'oparl':
      apiUrl.value = 'https://oparl.org/api/bodies'
      break
    default:
      apiUrl.value = ''
  }
}

const onTemplateSelect = (templateId: string | null) => {
  if (!templateId) return

  const template = templates.value.find(tmpl => tmpl.id === templateId)
  if (!template) return

  apiType.value = template.api_type
  apiUrl.value = template.default_url || ''
  defaultTags.value = [...template.default_tags]

  if (template.api_type === 'wikidata' && template.parameters.sparql_query) {
    sparqlQuery.value = String(template.parameters.sparql_query)
  }
}

const loadPreview = async () => {
  loadingPreview.value = true
  preview.value = []
  errorMessage.value = ''

  try {
    const params: Record<string, string> = {}
    if (apiType.value === 'wikidata') {
      params.sparql_query = sparqlQuery.value
    }

    const response = await adminApi.previewApiImport({
      api_type: apiType.value,
      api_url: apiUrl.value,
      params,
      sample_size: 20,
    })

    preview.value = response.data.items
    totalAvailable.value = response.data.total_available

    // Add suggested tags from preview
    if (response.data.suggested_tags?.length) {
      const newTags = response.data.suggested_tags.filter((tag: string) => !defaultTags.value.includes(tag))
      if (newTags.length > 0) {
        defaultTags.value = [...defaultTags.value, ...newTags]
      }
    }
  } catch (error) {
    logger.error('Failed to load preview', error)
    errorMessage.value = t('sources.apiImport.previewError')
  } finally {
    loadingPreview.value = false
  }
}

const executeImport = async () => {
  importing.value = true
  errorMessage.value = ''

  try {
    const params: Record<string, string> = {}
    if (apiType.value === 'wikidata') {
      params.sparql_query = sparqlQuery.value
    }

    const response = await adminApi.executeApiImport({
      api_type: apiType.value,
      api_url: apiUrl.value,
      params,
      category_ids: categoryIds.value,
      default_tags: defaultTags.value,
      skip_duplicates: skipDuplicates.value,
      max_items: 5000,
    })

    emit('imported', response.data.imported)
    close()
  } catch (error) {
    logger.error('API import failed', error)
    errorMessage.value = t('sources.apiImport.importError')
  } finally {
    importing.value = false
  }
}

const getAllTags = (item: PreviewItem): string[] => {
  return [...new Set([...defaultTags.value, ...(item.suggested_tags || [])])]
}

const close = () => {
  preview.value = []
  totalAvailable.value = 0
  errorMessage.value = ''
  isOpen.value = false
}

// Initialize
onMounted(() => {
  loadTemplates()
})

// Reset when dialog opens
watch(isOpen, (value) => {
  if (value) {
    apiType.value = 'wikidata'
    apiUrl.value = 'https://query.wikidata.org/sparql'
    sparqlQuery.value = ''
    categoryIds.value = []
    defaultTags.value = []
    preview.value = []
    totalAvailable.value = 0
    selectedTemplate.value = null
    errorMessage.value = ''
    loadTemplates()
  }
})
</script>

<style scoped>
.preview-table {
  font-size: 0.875rem;
}

.sparql-textarea :deep(textarea) {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 0.875rem;
}
</style>
