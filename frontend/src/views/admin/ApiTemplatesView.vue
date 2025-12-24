<template>
  <v-container fluid>
    <!-- Header -->
    <PageHeader
      :title="t('admin.apiTemplates.title')"
      :subtitle="t('admin.apiTemplates.subtitle')"
      icon="mdi-api"
    >
      <template #actions>
        <v-btn variant="tonal" color="primary" @click="openCreateDialog">
          <v-icon start>mdi-plus</v-icon>
          {{ t('admin.apiTemplates.actions.create') }}
        </v-btn>
      </template>
    </PageHeader>

    <!-- Filters -->
    <v-card class="mb-4">
      <v-card-text>
        <v-row align="center">
          <v-col cols="12" md="4">
            <v-text-field
              v-model="search"
              :label="t('common.search')"
              prepend-inner-icon="mdi-magnify"
              clearable
              hide-details
              @update:model-value="debouncedFetch"
            />
          </v-col>
          <v-col cols="12" md="3">
            <v-select
              v-model="statusFilter"
              :label="t('admin.apiTemplates.filters.status')"
              :items="statusOptions"
              clearable
              hide-details
              @update:model-value="fetchTemplates"
            />
          </v-col>
          <v-col cols="12" md="3">
            <v-select
              v-model="apiTypeFilter"
              :label="t('admin.apiTemplates.filters.apiType')"
              :items="apiTypeOptions"
              clearable
              hide-details
              @update:model-value="fetchTemplates"
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Templates Table -->
    <v-card>
      <v-data-table-server
        v-model:page="page"
        v-model:items-per-page="perPage"
        :headers="headers"
        :items="templates"
        :items-length="totalTemplates"
        :loading="loading"
        @update:page="fetchTemplates"
        @update:items-per-page="fetchTemplates"
      >
        <!-- Name Column -->
        <template #item.name="{ item }">
          <div class="font-weight-medium">{{ item.name }}</div>
          <div class="text-caption text-medium-emphasis">{{ item.description || '-' }}</div>
        </template>

        <!-- API Type Column -->
        <template #item.api_type="{ item }">
          <v-chip :color="getApiTypeColor(item.api_type)" size="small" label>
            {{ item.api_type }}
          </v-chip>
        </template>

        <!-- URL Column -->
        <template #item.base_url="{ item }">
          <code class="text-caption">{{ truncateUrl(joinUrl(item.base_url, item.endpoint)) }}</code>
        </template>

        <!-- Status Column -->
        <template #item.status="{ item }">
          <v-chip :color="getStatusColor(item.status)" size="small">
            <v-icon start size="small">{{ getStatusIcon(item.status) }}</v-icon>
            {{ item.status }}
          </v-chip>
        </template>

        <!-- Keywords Column -->
        <template #item.keywords="{ item }">
          <v-chip-group v-if="item.keywords?.length">
            <v-chip
              v-for="keyword in item.keywords.slice(0, 3)"
              :key="keyword"
              size="x-small"
              variant="outlined"
            >
              {{ keyword }}
            </v-chip>
            <v-chip v-if="item.keywords.length > 3" size="x-small" variant="text">
              +{{ item.keywords.length - 3 }}
            </v-chip>
          </v-chip-group>
          <span v-else class="text-medium-emphasis">-</span>
        </template>

        <!-- Usage Column -->
        <template #item.usage_count="{ item }">
          <v-tooltip :text="item.last_used ? t('admin.apiTemplates.lastUsed', { date: formatDate(item.last_used) }) : t('admin.apiTemplates.neverUsed')">
            <template v-slot:activator="{ props }">
              <v-chip v-bind="props" size="small" variant="text">
                {{ item.usage_count }}x
              </v-chip>
            </template>
          </v-tooltip>
        </template>

        <!-- Last Validated Column -->
        <template #item.last_validated="{ item }">
          <div v-if="item.last_validated">
            <div class="text-caption">{{ formatDate(item.last_validated) }}</div>
            <div v-if="item.validation_item_count" class="text-caption text-success">
              {{ item.validation_item_count }} {{ t('admin.apiTemplates.items') }}
            </div>
          </div>
          <span v-else class="text-medium-emphasis">-</span>
        </template>

        <!-- Actions Column -->
        <template #item.actions="{ item }">
          <div class="d-flex justify-end ga-1">
            <v-btn
              icon="mdi-play-circle"
              size="small"
              variant="tonal"
              color="success"
              :loading="testingId === item.id"
              :title="t('admin.apiTemplates.actions.test')"
              @click="testTemplate(item)"
            />
            <v-btn
              icon="mdi-pencil"
              size="small"
              variant="tonal"
              :title="t('common.edit')"
              @click="openEditDialog(item)"
            />
            <v-btn
              icon="mdi-delete"
              size="small"
              variant="tonal"
              color="error"
              :title="t('common.delete')"
              @click="confirmDelete(item)"
            />
          </div>
        </template>
      </v-data-table-server>
    </v-card>

    <!-- Create/Edit Dialog -->
    <v-dialog v-model="dialogOpen" max-width="700" scrollable>
      <v-card>
        <v-card-title class="d-flex align-center pa-4 bg-primary">
          <v-avatar color="primary-darken-1" size="40" class="mr-3">
            <v-icon color="on-primary">{{ editingTemplate ? 'mdi-pencil' : 'mdi-plus' }}</v-icon>
          </v-avatar>
          <div>
            <div class="text-h6">
              {{ editingTemplate ? t('admin.apiTemplates.dialog.editTitle') : t('admin.apiTemplates.dialog.createTitle') }}
            </div>
          </div>
        </v-card-title>
        <v-card-text class="pa-6">
          <v-form ref="formRef" @submit.prevent="saveTemplate">
            <v-row>
              <v-col cols="12">
                <v-text-field
                  v-model="formData.name"
                  :label="t('common.name')"
                  :rules="[required]"
                  variant="outlined"
                  prepend-inner-icon="mdi-label"
                />
              </v-col>
              <v-col cols="12">
                <v-textarea
                  v-model="formData.description"
                  :label="t('common.description')"
                  variant="outlined"
                  rows="2"
                />
              </v-col>
              <v-col cols="12" md="6">
                <v-select
                  v-model="formData.api_type"
                  :label="t('admin.apiTemplates.form.apiType')"
                  :items="apiTypeOptions"
                  :rules="[required]"
                  variant="outlined"
                />
              </v-col>
              <v-col cols="12" md="6">
                <v-select
                  v-model="formData.status"
                  :label="t('common.status')"
                  :items="statusOptions"
                  :rules="[required]"
                  variant="outlined"
                />
              </v-col>
              <v-col cols="12">
                <v-text-field
                  v-model="formData.base_url"
                  :label="t('admin.apiTemplates.form.baseUrl')"
                  :rules="[required, urlRule]"
                  variant="outlined"
                  placeholder="https://api.example.com"
                  prepend-inner-icon="mdi-link"
                />
              </v-col>
              <v-col cols="12">
                <v-text-field
                  v-model="formData.endpoint"
                  :label="t('admin.apiTemplates.form.endpoint')"
                  :rules="[required]"
                  variant="outlined"
                  placeholder="/v1/data"
                  prepend-inner-icon="mdi-api"
                />
              </v-col>
              <v-col cols="12">
                <v-text-field
                  v-model="formData.documentation_url"
                  :label="t('admin.apiTemplates.form.documentationUrl')"
                  variant="outlined"
                  placeholder="https://docs.example.com"
                  prepend-inner-icon="mdi-book-open-variant"
                />
              </v-col>
              <v-col cols="12">
                <v-switch
                  v-model="formData.auth_required"
                  :label="t('admin.apiTemplates.form.authRequired')"
                  color="primary"
                  hide-details
                />
              </v-col>
              <v-col cols="12">
                <v-combobox
                  v-model="formData.keywords"
                  :label="t('admin.apiTemplates.form.keywords')"
                  :hint="t('admin.apiTemplates.form.keywordsHint')"
                  variant="outlined"
                  chips
                  multiple
                  closable-chips
                />
              </v-col>
              <v-col cols="12">
                <v-combobox
                  v-model="formData.default_tags"
                  :label="t('admin.apiTemplates.form.defaultTags')"
                  :hint="t('admin.apiTemplates.form.defaultTagsHint')"
                  variant="outlined"
                  chips
                  multiple
                  closable-chips
                />
              </v-col>
            </v-row>
          </v-form>
        </v-card-text>
        <v-divider />
        <v-card-actions class="pa-4">
          <v-btn variant="text" @click="dialogOpen = false">
            {{ t('common.cancel') }}
          </v-btn>
          <v-spacer />
          <v-btn color="primary" variant="elevated" :loading="saving" @click="saveTemplate">
            {{ t('common.save') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Test Result Dialog -->
    <v-dialog v-model="testResultDialog" max-width="600">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon
            :color="testResult?.is_valid ? 'success' : 'error'"
            class="mr-2"
          >
            {{ testResult?.is_valid ? 'mdi-check-circle' : 'mdi-close-circle' }}
          </v-icon>
          {{ testResult?.is_valid ? t('admin.apiTemplates.testSuccess') : t('admin.apiTemplates.testFailed') }}
        </v-card-title>
        <v-card-text v-if="testResult">
          <v-list density="compact">
            <v-list-item>
              <v-list-item-title>{{ t('admin.apiTemplates.statusCode') }}</v-list-item-title>
              <template v-slot:append>
                <v-chip :color="testResult.status_code === 200 ? 'success' : 'warning'" size="small">
                  {{ testResult.status_code }}
                </v-chip>
              </template>
            </v-list-item>
            <v-list-item v-if="testResult.item_count !== undefined">
              <v-list-item-title>{{ t('admin.apiTemplates.itemCount') }}</v-list-item-title>
              <template v-slot:append>
                <span class="font-weight-bold">{{ testResult.item_count }}</span>
              </template>
            </v-list-item>
            <v-list-item v-if="testResult.error_message">
              <v-list-item-title class="text-error">{{ testResult.error_message }}</v-list-item-title>
            </v-list-item>
          </v-list>
          <v-expansion-panels v-if="testResult.sample_items?.length" class="mt-4">
            <v-expansion-panel>
              <v-expansion-panel-title>
                {{ t('admin.apiTemplates.sampleData') }} ({{ testResult.sample_items.length }})
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <pre class="text-caption overflow-auto" style="max-height: 300px">{{ JSON.stringify(testResult.sample_items, null, 2) }}</pre>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="testResultDialog = false">
            {{ t('common.close') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="deleteDialog" max-width="400">
      <v-card>
        <v-card-title>{{ t('admin.apiTemplates.dialog.deleteTitle') }}</v-card-title>
        <v-card-text>
          {{ t('admin.apiTemplates.dialog.deleteConfirm', { name: templateToDelete?.name }) }}
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="deleteDialog = false">
            {{ t('common.cancel') }}
          </v-btn>
          <v-btn color="error" variant="elevated" :loading="deleting" @click="deleteTemplate">
            {{ t('common.delete') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Snackbar -->
    <v-snackbar v-model="snackbar" :color="snackbarColor" :timeout="3000">
      {{ snackbarText }}
    </v-snackbar>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { adminApi } from '@/services/api'
import { useDebounce, DEBOUNCE_DELAYS } from '@/composables/useDebounce'
import PageHeader from '@/components/common/PageHeader.vue'

// ============================================================================
// Types
// ============================================================================

interface ApiTemplate {
  id: string
  name: string
  description?: string
  api_type: string
  base_url: string
  endpoint: string
  documentation_url?: string
  auth_required: boolean
  auth_config?: Record<string, unknown>
  field_mapping: Record<string, string>
  keywords: string[]
  default_tags: string[]
  status: string
  last_validated?: string
  last_validation_error?: string
  validation_item_count?: number
  usage_count: number
  last_used?: string
  confidence: number
  source: string
  created_at: string
  updated_at: string
}

interface TestResult {
  is_valid: boolean
  status_code?: number
  item_count?: number
  sample_items?: Record<string, unknown>[]
  error_message?: string
  validation_time_ms?: number
}

// ============================================================================
// Composables
// ============================================================================

const { t, locale } = useI18n()

// ============================================================================
// State
// ============================================================================

const loading = ref(false)
const saving = ref(false)
const deleting = ref(false)
const testingId = ref<string | null>(null)

const templates = ref<ApiTemplate[]>([])
const totalTemplates = ref(0)
const page = ref(1)
const perPage = ref(10)
const search = ref('')
const statusFilter = ref<string | null>(null)
const apiTypeFilter = ref<string | null>(null)

const dialogOpen = ref(false)
const editingTemplate = ref<ApiTemplate | null>(null)
const formRef = ref()
const formData = ref({
  name: '',
  description: '',
  api_type: 'REST' as 'REST' | 'GRAPHQL' | 'SPARQL' | 'OPARL',
  base_url: '',
  endpoint: '',
  documentation_url: '',
  auth_required: false,
  keywords: [] as string[],
  default_tags: [] as string[],
  status: 'PENDING' as 'ACTIVE' | 'INACTIVE' | 'FAILED' | 'PENDING',
})

const deleteDialog = ref(false)
const templateToDelete = ref<ApiTemplate | null>(null)

const testResultDialog = ref(false)
const testResult = ref<TestResult | null>(null)

const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('success')

// ============================================================================
// Options
// ============================================================================

const statusOptions = [
  { title: 'ACTIVE', value: 'ACTIVE' },
  { title: 'INACTIVE', value: 'INACTIVE' },
  { title: 'FAILED', value: 'FAILED' },
  { title: 'PENDING', value: 'PENDING' },
]

const apiTypeOptions = [
  { title: 'REST', value: 'REST' },
  { title: 'GraphQL', value: 'GRAPHQL' },
  { title: 'SPARQL', value: 'SPARQL' },
  { title: 'OParl', value: 'OPARL' },
]

const headers = computed(() => [
  { title: t('common.name'), key: 'name', sortable: true },
  { title: t('admin.apiTemplates.columns.apiType'), key: 'api_type', sortable: true, width: '100px' },
  { title: 'URL', key: 'base_url', sortable: false },
  { title: t('common.status'), key: 'status', sortable: true, width: '120px' },
  { title: t('admin.apiTemplates.columns.keywords'), key: 'keywords', sortable: false },
  { title: t('admin.apiTemplates.columns.usage'), key: 'usage_count', sortable: true, width: '80px' },
  { title: t('admin.apiTemplates.columns.lastValidated'), key: 'last_validated', sortable: true, width: '150px' },
  { title: t('common.actions'), key: 'actions', sortable: false, align: 'end' as const, width: '140px' },
])

// ============================================================================
// Validation Rules
// ============================================================================

const required = (v: string) => !!v || t('validation.required')
const urlRule = (v: string) => {
  if (!v) return true
  try {
    new URL(v)
    return true
  } catch {
    return t('validation.invalidUrl')
  }
}

// ============================================================================
// Methods
// ============================================================================

const fetchTemplates = async () => {
  loading.value = true
  try {
    const params: Record<string, unknown> = {
      limit: perPage.value,
      offset: (page.value - 1) * perPage.value,
    }
    if (search.value) params.search = search.value
    if (statusFilter.value) params.status = statusFilter.value
    if (apiTypeFilter.value) params.api_type = apiTypeFilter.value

    const response = await adminApi.getApiTemplates(params as Parameters<typeof adminApi.getApiTemplates>[0])
    templates.value = response.data.templates
    totalTemplates.value = response.data.total
  } catch (error) {
    console.error('Failed to fetch templates:', error)
    showSnackbar(t('admin.apiTemplates.errors.loadFailed'), 'error')
  } finally {
    loading.value = false
  }
}

// Debounce search - uses composable with automatic cleanup
const { debouncedFn: debouncedFetch } = useDebounce(
  () => fetchTemplates(),
  { delay: DEBOUNCE_DELAYS.SEARCH }
)

const openCreateDialog = () => {
  editingTemplate.value = null
  formData.value = {
    name: '',
    description: '',
    api_type: 'REST',
    base_url: '',
    endpoint: '',
    documentation_url: '',
    auth_required: false,
    keywords: [],
    default_tags: [],
    status: 'PENDING',
  }
  dialogOpen.value = true
}

const openEditDialog = (template: ApiTemplate) => {
  editingTemplate.value = template
  formData.value = {
    name: template.name,
    description: template.description || '',
    api_type: template.api_type as 'REST' | 'GRAPHQL' | 'SPARQL' | 'OPARL',
    base_url: template.base_url,
    endpoint: template.endpoint,
    documentation_url: template.documentation_url || '',
    auth_required: template.auth_required,
    keywords: [...template.keywords],
    default_tags: [...template.default_tags],
    status: template.status as 'ACTIVE' | 'INACTIVE' | 'FAILED' | 'PENDING',
  }
  dialogOpen.value = true
}

const saveTemplate = async () => {
  const { valid } = await formRef.value.validate()
  if (!valid) return

  saving.value = true
  try {
    if (editingTemplate.value) {
      await adminApi.updateApiTemplate(editingTemplate.value.id, formData.value)
      showSnackbar(t('admin.apiTemplates.messages.updated'), 'success')
    } else {
      await adminApi.createApiTemplate(formData.value)
      showSnackbar(t('admin.apiTemplates.messages.created'), 'success')
    }
    dialogOpen.value = false
    fetchTemplates()
  } catch (error) {
    console.error('Failed to save template:', error)
    showSnackbar(t('admin.apiTemplates.errors.saveFailed'), 'error')
  } finally {
    saving.value = false
  }
}

const confirmDelete = (template: ApiTemplate) => {
  templateToDelete.value = template
  deleteDialog.value = true
}

const deleteTemplate = async () => {
  if (!templateToDelete.value) return

  deleting.value = true
  try {
    await adminApi.deleteApiTemplate(templateToDelete.value.id)
    showSnackbar(t('admin.apiTemplates.messages.deleted'), 'success')
    deleteDialog.value = false
    fetchTemplates()
  } catch (error) {
    console.error('Failed to delete template:', error)
    showSnackbar(t('admin.apiTemplates.errors.deleteFailed'), 'error')
  } finally {
    deleting.value = false
  }
}

const testTemplate = async (template: ApiTemplate) => {
  testingId.value = template.id
  try {
    const response = await adminApi.testApiTemplate(template.id)
    testResult.value = response.data
    testResultDialog.value = true
    fetchTemplates() // Refresh to show updated validation status
  } catch (error) {
    console.error('Failed to test template:', error)
    showSnackbar(t('admin.apiTemplates.errors.testFailed'), 'error')
  } finally {
    testingId.value = null
  }
}

const showSnackbar = (text: string, color: string) => {
  snackbarText.value = text
  snackbarColor.value = color
  snackbar.value = true
}

const formatDate = (dateStr: string) => {
  const localeStr = locale.value === 'de' ? 'de-DE' : 'en-US'
  return new Date(dateStr).toLocaleDateString(localeStr, {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const joinUrl = (base: string, path: string): string => {
  const cleanBase = base.replace(/\/+$/, '')
  const cleanPath = path.replace(/^\/+/, '')
  return `${cleanBase}/${cleanPath}`
}

const truncateUrl = (url: string) => {
  if (url.length > 50) {
    return url.substring(0, 47) + '...'
  }
  return url
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'ACTIVE': return 'success'
    case 'INACTIVE': return 'grey'
    case 'FAILED': return 'error'
    case 'PENDING': return 'warning'
    default: return 'grey'
  }
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'ACTIVE': return 'mdi-check-circle'
    case 'INACTIVE': return 'mdi-pause-circle'
    case 'FAILED': return 'mdi-alert-circle'
    case 'PENDING': return 'mdi-clock'
    default: return 'mdi-help-circle'
  }
}

const getApiTypeColor = (type: string) => {
  switch (type) {
    case 'REST': return 'primary'
    case 'GRAPHQL': return 'purple'
    case 'SPARQL': return 'orange'
    case 'OPARL': return 'teal'
    default: return 'grey'
  }
}

// ============================================================================
// Lifecycle
// ============================================================================

onMounted(() => {
  fetchTemplates()
})
// Note: useDebounce handles cleanup automatically via onUnmounted
</script>
