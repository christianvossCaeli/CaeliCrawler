<template>
  <div>
    <PageHeader
      :title="t('exportView.title')"
      :subtitle="t('exportView.subtitle')"
      icon="mdi-download"
    />

    <PageInfoBox :storage-key="INFO_BOX_STORAGE_KEYS.EXPORT" :title="t('exportView.info.title')">
      {{ t('exportView.info.description') }}
    </PageInfoBox>

    <v-row>
      <v-col cols="12" md="7">
        <v-card class="mb-4">
          <v-card-title class="d-flex align-center">
            <v-icon start>mdi-download</v-icon>
            {{ t('exportView.quickExportTitle') }}
            <v-spacer />
            <v-chip size="small" color="primary" variant="tonal">{{ t('exportView.instant') }}</v-chip>
          </v-card-title>
          <v-card-text>
            <div class="text-body-2 text-medium-emphasis mb-4">
              {{ t('exportView.quickExportDescription') }}
            </div>

            <div class="text-subtitle-2 mb-2">{{ t('exportView.filtersTitle') }}</div>
            <v-row>
              <v-col v-if="canEdit" cols="12" md="6">
                <v-select
                  v-model="exportOptions.category_id"
                  :items="categories"
                  item-title="name"
                  item-value="id"
                  :label="t('exportView.categoryOptional')"
                  clearable
                  :loading="loadingCategories"
                  hide-details
                />
              </v-col>
              <v-col cols="12" :md="canEdit ? 6 : 12">
                <v-slider
                  v-model="minConfidencePercent"
                  :min="0"
                  :max="100"
                  :step="5"
                  :label="t('exportView.minConfidence')"
                  thumb-label="always"
                  density="compact"
                >
                  <template #thumb-label="{ modelValue }">{{ modelValue }}%</template>
                </v-slider>
                <div class="text-caption text-medium-emphasis mt-1">
                  {{ t('exportView.minConfidenceHint') }}
                </div>
              </v-col>
            </v-row>

            <v-switch
              v-model="exportOptions.human_verified_only"
              :label="t('exportView.verifiedOnly')"
              color="success"
              density="comfortable"
              hide-details
            />

            <div class="mt-3">
              <div class="text-caption text-medium-emphasis mb-1">{{ t('exportView.filtersApplied') }}</div>
              <div v-if="quickFilterChips.length > 0" class="d-flex flex-wrap gap-2">
                <v-chip
                  v-for="chip in quickFilterChips"
                  :key="chip"
                  size="small"
                  variant="outlined"
                  color="primary"
                >
                  {{ chip }}
                </v-chip>
              </div>
              <div v-else class="text-caption text-medium-emphasis">
                {{ t('exportView.filtersNone') }}
              </div>
            </div>

            <div class="d-flex align-center justify-space-between mt-4 flex-wrap gap-4">
              <div>
                <div class="text-subtitle-2 mb-2">{{ t('exportView.formatTitle') }}</div>
                <v-btn-toggle v-model="quickFormat" color="primary" mandatory density="compact">
                  <v-btn value="json" variant="outlined">
                    <v-icon start size="small">mdi-code-json</v-icon>
                    JSON
                  </v-btn>
                  <v-btn value="csv" variant="outlined">
                    <v-icon start size="small">mdi-file-delimited</v-icon>
                    CSV
                  </v-btn>
                </v-btn-toggle>
              </div>
              <div class="d-flex align-center gap-2">
                <v-btn
                  variant="text"
                  size="small"
                  :disabled="!hasQuickFilters"
                  @click="resetQuickFilters"
                >
                  <v-icon start size="small">mdi-filter-off</v-icon>
                  {{ t('exportView.resetFilters') }}
                </v-btn>
                <v-btn
                  color="primary"
                  :loading="exporting"
                  @click="exportQuick"
                >
                  <v-icon start>mdi-download</v-icon>
                  {{ downloadLabel }}
                </v-btn>
              </div>
            </div>

            <v-alert
              type="info"
              variant="tonal"
              density="compact"
              class="mt-4"
            >
              <v-icon start size="small">mdi-information</v-icon>
              {{ t('export.largeExportHint') }}
            </v-alert>
          </v-card-text>
        </v-card>

        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon start>mdi-database-export</v-icon>
            {{ t('exportView.asyncExportTitle') }}
            <v-spacer />
            <v-chip size="small" color="secondary" variant="tonal">{{ t('exportView.backgroundJob') }}</v-chip>
          </v-card-title>
          <v-card-text>
            <div class="text-body-2 text-medium-emphasis mb-4">
              {{ t('exportView.asyncExportDescription') }}
            </div>

            <v-row>
              <v-col cols="12" md="4">
                <v-select
                  v-model="asyncExportOptions.entity_type"
                  :items="entityTypeItems"
                  :label="t('entityTypes.entityType')"
                  hide-details
                />
              </v-col>
              <v-col cols="12" md="4">
                <v-select
                  v-model="asyncExportOptions.format"
                  :items="formatItems"
                  :label="t('export.format')"
                  hide-details
                />
              </v-col>
              <v-col cols="12" md="4">
                <v-select
                  v-model="asyncExportOptions.country"
                  :items="locationOptions.countries"
                  :label="t('exportView.countryOptional')"
                  clearable
                  hide-details
                  :loading="loadingLocationOptions"
                />
              </v-col>
            </v-row>

            <v-row>
              <v-col cols="12" md="8">
                <v-combobox
                  v-model="asyncExportOptions.location_filter"
                  :items="locationOptions.admin_level_1"
                  :label="t('exportView.locationOptional')"
                  clearable
                  :loading="loadingLocationOptions"
                  :hint="t('exportView.locationHint')"
                  persistent-hint
                />
              </v-col>
              <v-col cols="12" md="4" class="d-flex align-center">
                <v-switch
                  v-model="asyncExportOptions.include_facets"
                  :label="t('entityTypes.includeFacets')"
                  color="primary"
                  density="comfortable"
                  hide-details
                />
              </v-col>
            </v-row>

            <div class="text-caption text-medium-emphasis mb-3">
              {{ t('exportView.includeFacetsHint') }}
            </div>

            <div class="d-flex align-center justify-end">
              <v-btn
                color="primary"
                :loading="startingAsyncExport"
                @click="startAsyncExport"
              >
                <v-icon start>mdi-export</v-icon>
                {{ t('export.startAsync') }}
              </v-btn>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="5">
        <ExportProgressPanel ref="exportProgressRef" class="mb-4" />

        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon start>mdi-robot</v-icon>
            {{ t('exportView.automationTitle') }}
          </v-card-title>
          <v-card-text>
            <div class="text-body-2 text-medium-emphasis mb-3">
              {{ t('exportView.automationDescription') }}
            </div>
            <v-expansion-panels variant="accordion">
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon size="small" class="mr-2">mdi-api</v-icon>
                  {{ t('exportView.apiEndpoints') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-list density="compact">
                    <v-list-item>
                      <v-list-item-title>{{ t('exportView.extractedData') }}</v-list-item-title>
                      <v-list-item-subtitle>
                        <code>GET /api/v1/data</code>
                      </v-list-item-subtitle>
                    </v-list-item>
                    <v-list-item>
                      <v-list-item-title>{{ t('documents.documents') }}</v-list-item-title>
                      <v-list-item-subtitle>
                        <code>GET /api/v1/data/documents</code>
                      </v-list-item-subtitle>
                    </v-list-item>
                    <v-list-item>
                      <v-list-item-title>{{ t('exportView.fulltextSearch') }}</v-list-item-title>
                      <v-list-item-subtitle>
                        <code>GET /api/v1/data/search?q=...</code>
                      </v-list-item-subtitle>
                    </v-list-item>
                    <v-list-item>
                      <v-list-item-title>{{ t('exportView.changesFeed') }}</v-list-item-title>
                      <v-list-item-subtitle>
                        <code>GET /api/v1/export/changes</code>
                      </v-list-item-subtitle>
                    </v-list-item>
                  </v-list>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon size="small" class="mr-2">mdi-webhook</v-icon>
                  {{ t('exportView.webhookTest') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-text-field
                    v-model="webhookUrl"
                    :label="t('exportView.webhookUrl')"
                    :placeholder="t('exportView.webhookPlaceholder')"
                    variant="outlined"
                    density="compact"
                    :hint="t('exportView.webhookUrlHint')"
                    persistent-hint
                    :error="!!webhookUrlError"
                    :aria-invalid="!!webhookUrlError"
                    :error-messages="webhookUrlError"
                  />
                  <div class="d-flex align-center gap-2">
                    <v-btn
                      variant="tonal"
                      color="primary"
                      :loading="testingWebhook"
                      :disabled="!webhookUrlValid"
                      @click="testWebhook"
                    >
                      <v-icon start>mdi-send</v-icon>
                      {{ t('exportView.testWebhook') }}
                    </v-btn>
                  </div>

                  <v-alert
                    v-if="webhookResult"
                    :type="webhookResult.success ? 'success' : 'error'"
                    class="mt-4"
                  >
                    <strong>{{ t('common.status') }}:</strong> {{ webhookResult.status_code || t('common.error') }}<br>
                    <span v-if="webhookResult.error">{{ webhookResult.error }}</span>
                    <span v-else>{{ webhookResult.response }}</span>
                  </v-alert>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon start>mdi-history</v-icon>
            {{ t('exportView.recentChanges') }}
            <v-chip v-if="changes.length" class="ml-2" size="small" variant="outlined">
              {{ changes.length }}
            </v-chip>
            <v-spacer />
            <v-btn variant="text" size="small" :loading="loadingChanges" @click="loadChanges">
              <v-icon start size="small">mdi-refresh</v-icon>
              {{ t('common.refresh') }}
            </v-btn>
          </v-card-title>
          <v-card-text>
            <div class="text-body-2 text-medium-emphasis mb-3">
              {{ t('exportView.recentChangesDescription') }}
            </div>
            <v-data-table
              :headers="changeHeaders"
              :items="changes"
              :loading="loadingChanges"
              :items-per-page="10"
              :no-data-text="t('exportView.noChanges')"
            >
              <template #item.change_type="{ item }">
                <v-chip :color="getChangeColor(item.change_type)" size="small">
                  {{ t(`exportView.changeTypes.${item.change_type}`) }}
                </v-chip>
              </template>
              <template #item.detected_at="{ item }">
                {{ formatDate(item.detected_at) }}
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { adminApi, exportApi, entityApi } from '@/services/api'
import { format } from 'date-fns'
import { de, enUS } from 'date-fns/locale'
import { useSnackbar } from '@/composables/useSnackbar'
import ExportProgressPanel from '@/components/export/ExportProgressPanel.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import PageInfoBox from '@/components/common/PageInfoBox.vue'
import { INFO_BOX_STORAGE_KEYS } from '@/config/infoBox'
import { useLogger } from '@/composables/useLogger'
import { getErrorMessage } from '@/utils/errorMessage'
import { useAuthStore } from '@/stores/auth'
import { usePageContextProvider, PAGE_ACTIONS } from '@/composables/usePageContext'
import type { PageContextData } from '@/composables/assistant/types'

const logger = useLogger('ExportView')

const { t, locale } = useI18n()
const { showSuccess, showError } = useSnackbar()
const auth = useAuthStore()
const canEdit = computed(() => auth.isEditor)

const dateLocale = computed(() => locale.value === 'de' ? de : enUS)

interface CategoryOption {
  id: string
  name: string
}

interface WebhookResult {
  success: boolean
  status_code?: number
  response_time_ms?: number
  message?: string
  error?: string
  response?: unknown
}

interface ChangeRecord {
  id: string
  entity_type?: string
  entity_name?: string
  change_type?: string
  timestamp?: string
  detected_at?: string
}

const categories = ref<CategoryOption[]>([])
const loadingCategories = ref(false)
const locationOptions = ref<{ countries: string[]; admin_level_1: string[] }>({
  countries: [],
  admin_level_1: [],
})
const loadingLocationOptions = ref(false)
const exporting = ref(false)
const testingWebhook = ref(false)
const loadingChanges = ref(false)
const webhookUrl = ref('')
const webhookResult = ref<WebhookResult | null>(null)
const changes = ref<ChangeRecord[]>([])
const startingAsyncExport = ref(false)
const exportProgressRef = ref<InstanceType<typeof ExportProgressPanel> | null>(null)

const quickFormat = ref<'json' | 'csv'>('json')

const exportOptions = ref({
  category_id: null as string | null,
  min_confidence: 0,
  human_verified_only: false,
})

const asyncExportOptions = ref({
  entity_type: 'municipality',
  format: 'json',
  location_filter: null as string | null,
  country: null as string | null,
  include_facets: true,
})

// Page Context Provider for KI-Assistant awareness
usePageContextProvider(
  '/export',
  (): PageContextData => ({
    current_route: '/export',
    view_mode: 'export',
    filters: {
      category_id: exportOptions.value.category_id || undefined,
      min_confidence: exportOptions.value.min_confidence || undefined,
      human_verified_only: exportOptions.value.human_verified_only || undefined
    },
    available_features: ['quick_export', 'async_export', 'webhook_test', 'changes_feed'],
    available_actions: [...PAGE_ACTIONS.base, 'export_json', 'export_csv', 'start_async_export', 'test_webhook']
  })
)

const minConfidencePercent = computed({
  get: () => Math.round(exportOptions.value.min_confidence * 100),
  set: (value: number) => {
    const clamped = Math.min(Math.max(value, 0), 100)
    exportOptions.value.min_confidence = clamped / 100
  },
})

const exportParams = computed(() => {
  const params: Record<string, unknown> = {}
  if (exportOptions.value.category_id) {
    params.category_id = exportOptions.value.category_id
  }
  if (exportOptions.value.min_confidence > 0) {
    params.min_confidence = exportOptions.value.min_confidence
  }
  if (exportOptions.value.human_verified_only) {
    params.human_verified_only = true
  }
  return params
})

const selectedCategory = computed(() =>
  categories.value.find(category => category.id === exportOptions.value.category_id)
)

const quickFilterChips = computed(() => {
  const chips: string[] = []
  if (selectedCategory.value) {
    chips.push(t('exportView.filters.category', { value: selectedCategory.value.name }))
  }
  if (exportOptions.value.min_confidence > 0) {
    chips.push(t('exportView.filters.minConfidence', { value: minConfidencePercent.value }))
  }
  if (exportOptions.value.human_verified_only) {
    chips.push(t('exportView.filters.verifiedOnly'))
  }
  return chips
})

const hasQuickFilters = computed(() =>
  Boolean(exportOptions.value.category_id) ||
  exportOptions.value.min_confidence > 0 ||
  exportOptions.value.human_verified_only
)

const downloadLabel = computed(() =>
  t('exportView.downloadFormat', { format: quickFormat.value.toUpperCase() })
)

const webhookUrlValid = computed(() => {
  if (!webhookUrl.value) return false
  try {
    const parsed = new URL(webhookUrl.value)
    return parsed.protocol === 'https:'
  } catch {
    return false
  }
})

const webhookUrlError = computed(() => {
  if (!webhookUrl.value) return ''
  return webhookUrlValid.value ? '' : t('exportView.webhookUrlError')
})

const entityTypeItems = computed(() => [
  { title: t('entityTypes.types.municipality'), value: 'municipality' },
  { title: t('entityTypes.types.person'), value: 'person' },
  { title: t('entityTypes.types.organization'), value: 'organization' },
  { title: t('entityTypes.types.event'), value: 'event' },
])

const formatItems = [
  { title: 'JSON', value: 'json' },
  { title: 'CSV', value: 'csv' },
  { title: 'Excel', value: 'excel' },
]

const changeHeaders = computed(() => [
  { title: t('common.type'), key: 'change_type', sortable: true },
  { title: 'URL', key: 'affected_url', maxWidth: '400px', sortable: true },
  { title: t('exportView.detected'), key: 'detected_at', sortable: true },
])

const getChangeColor = (type?: string) => {
  if (!type) return 'grey'
  const colors: Record<string, string> = {
    NEW_DOCUMENT: 'success',
    CONTENT_CHANGED: 'info',
    REMOVED: 'error',
    METADATA_CHANGED: 'warning',
  }
  return colors[type] || 'grey'
}

const formatDate = (dateStr?: string) => {
  if (!dateStr) return '-'
  return format(new Date(dateStr), 'dd.MM.yyyy HH:mm', { locale: dateLocale.value })
}

const resetQuickFilters = () => {
  exportOptions.value = {
    category_id: null,
    min_confidence: 0,
    human_verified_only: false,
  }
}

const loadCategories = async () => {
  if (!canEdit.value) return
  loadingCategories.value = true
  try {
    const response = await adminApi.getCategories({ per_page: 100 })
    categories.value = response.data.items
  } catch (error) {
    logger.error('Failed to load categories:', error)
    showError(t('exportView.messages.categoriesError'))
    categories.value = []
  } finally {
    loadingCategories.value = false
  }
}

const loadLocationOptions = async () => {
  loadingLocationOptions.value = true
  try {
    const response = await entityApi.getLocationFilterOptions({
      country: asyncExportOptions.value.country || undefined,
    })
    locationOptions.value = {
      countries: response.data.countries || [],
      admin_level_1: response.data.admin_level_1 || [],
    }
  } catch (error) {
    logger.error('Failed to load location options:', error)
    showError(t('exportView.messages.locationOptionsError'))
    locationOptions.value = { countries: [], admin_level_1: [] }
  } finally {
    loadingLocationOptions.value = false
  }
}

const loadChanges = async () => {
  loadingChanges.value = true
  try {
    const response = await exportApi.getChangesFeed({ limit: 500 })
    changes.value = response.data.changes
  } catch (error) {
    logger.error('Failed to load changes feed:', error)
    showError(t('exportView.messages.changesError'))
  } finally {
    loadingChanges.value = false
  }
}

const exportQuick = async () => {
  exporting.value = true
  try {
    const response = quickFormat.value === 'json'
      ? await exportApi.exportJson(exportParams.value)
      : await exportApi.exportCsv(exportParams.value)
    if (quickFormat.value === 'json') {
      downloadBlob(response.data, 'caelichrawler_export.json', 'application/json')
      showSuccess(t('exportView.messages.jsonSuccess'))
    } else {
      downloadBlob(response.data, 'caelichrawler_export.csv', 'text/csv')
      showSuccess(t('exportView.messages.csvSuccess'))
    }
  } catch (error) {
    if (quickFormat.value === 'json') {
      showError(getErrorMessage(error) || t('exportView.messages.jsonError'))
    } else {
      showError(getErrorMessage(error) || t('exportView.messages.csvError'))
    }
  } finally {
    exporting.value = false
  }
}

const downloadBlob = (data: Blob, filename: string, mimeType: string) => {
  const blob = new Blob([data], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

const testWebhook = async () => {
  if (!webhookUrlValid.value) {
    showError(t('exportView.messages.webhookInvalid'))
    return
  }
  testingWebhook.value = true
  webhookResult.value = null
  try {
    const response = await exportApi.testWebhook(webhookUrl.value.trim())
    webhookResult.value = response.data
    if (response.data.success) {
      showSuccess(t('exportView.messages.webhookSuccess'))
    } else {
      showError(t('exportView.messages.webhookError'))
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    webhookResult.value = { success: false, error: message }
    showError(t('exportView.messages.webhookError') + ': ' + message)
  } finally {
    testingWebhook.value = false
  }
}

const startAsyncExport = async () => {
  startingAsyncExport.value = true
  try {
    const locationFilter = asyncExportOptions.value.location_filter?.trim() || undefined
    await exportApi.startAsyncExport({
      entity_type: asyncExportOptions.value.entity_type,
      format: asyncExportOptions.value.format,
      location_filter: locationFilter,
      country: asyncExportOptions.value.country || undefined,
      include_facets: asyncExportOptions.value.include_facets,
    })
    showSuccess(t('export.messages.success'))
    exportProgressRef.value?.refreshJobs()
  } catch (error) {
    showError(getErrorMessage(error) || t('export.messages.error'))
  } finally {
    startingAsyncExport.value = false
  }
}

watch(() => asyncExportOptions.value.country, () => {
  asyncExportOptions.value.location_filter = null
  loadLocationOptions()
})

onMounted(() => {
  if (canEdit.value) {
    loadCategories()
  }
  loadLocationOptions()
  loadChanges()
})
</script>
