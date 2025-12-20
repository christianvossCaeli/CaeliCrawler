<template>
  <div>
    <h1 class="text-h4 mb-6">{{ t('exportView.title') }}</h1>

    <v-row>
      <!-- Export Options -->
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-download</v-icon>
            {{ t('exportView.download') }}
          </v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="12" md="6">
                <v-select
                  v-model="exportOptions.country"
                  :items="countries"
                  item-title="name"
                  item-value="code"
                  :label="t('exportView.countryOptional')"
                  clearable
                  density="comfortable"
                ></v-select>
              </v-col>
              <v-col cols="12" md="6">
                <v-autocomplete
                  v-model="exportOptions.location_name"
                  :items="locations"
                  :label="t('exportView.locationOptional')"
                  clearable
                  density="comfortable"
                ></v-autocomplete>
              </v-col>
            </v-row>

            <v-select
              v-model="exportOptions.category_id"
              :items="categories"
              item-title="name"
              item-value="id"
              :label="t('exportView.categoryOptional')"
              clearable
            ></v-select>

            <v-slider
              v-model="exportOptions.min_confidence"
              :label="t('exportView.minConfidence')"
              :min="0"
              :max="1"
              :step="0.1"
              thumb-label
            ></v-slider>

            <v-switch
              v-model="exportOptions.human_verified_only"
              :label="t('exportView.verifiedOnly')"
              color="success"
            ></v-switch>

            <v-divider class="my-4"></v-divider>

            <div class="d-flex gap-2">
              <v-btn color="primary" @click="exportJson" :loading="exporting">
                <v-icon left>mdi-code-json</v-icon>
                {{ t('exportView.jsonExport') }}
              </v-btn>
              <v-btn color="success" @click="exportCsv" :loading="exporting">
                <v-icon left>mdi-file-delimited</v-icon>
                {{ t('exportView.csvExport') }}
              </v-btn>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- API Info -->
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-api</v-icon>
            {{ t('exportView.apiEndpoints') }}
          </v-card-title>
          <v-card-text>
            <v-list>
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
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Webhook Configuration -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-webhook</v-icon>
            {{ t('exportView.webhookTest') }}
          </v-card-title>
          <v-card-text>
            <v-text-field
              v-model="webhookUrl"
              :label="t('exportView.webhookUrl')"
              placeholder="https://your-endpoint.com/webhook"
            ></v-text-field>
            <v-btn color="primary" @click="testWebhook" :loading="testingWebhook">
              <v-icon left>mdi-send</v-icon>
              {{ t('exportView.testWebhook') }}
            </v-btn>

            <v-alert
              v-if="webhookResult"
              :type="webhookResult.success ? 'success' : 'error'"
              class="mt-4"
            >
              <strong>{{ t('common.status') }}:</strong> {{ webhookResult.status_code || t('common.error') }}<br>
              <span v-if="webhookResult.error">{{ webhookResult.error }}</span>
              <span v-else>{{ webhookResult.response }}</span>
            </v-alert>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Changes Feed -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-history</v-icon>
            {{ t('exportView.recentChanges') }}
          </v-card-title>
          <v-card-text>
            <v-data-table
              :headers="changeHeaders"
              :items="changes"
              :loading="loadingChanges"
              :items-per-page="10"
            >
              <template v-slot:item.change_type="{ item }">
                <v-chip :color="getChangeColor(item.change_type)" size="small">
                  {{ t(`exportView.changeTypes.${item.change_type}`) }}
                </v-chip>
              </template>
              <template v-slot:item.detected_at="{ item }">
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
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { adminApi, exportApi, dataApi } from '@/services/api'
import { format } from 'date-fns'
import { de, enUS } from 'date-fns/locale'
import { useSnackbar } from '@/composables/useSnackbar'

const { t, locale } = useI18n()
const { showSuccess, showError } = useSnackbar()

const dateLocale = computed(() => locale.value === 'de' ? de : enUS)

const categories = ref<any[]>([])
const countries = ref<any[]>([])
const locations = ref<string[]>([])
const exporting = ref(false)
const testingWebhook = ref(false)
const loadingChanges = ref(false)
const webhookUrl = ref('')
const webhookResult = ref<any>(null)
const changes = ref<any[]>([])

const exportOptions = ref({
  category_id: null as string | null,
  min_confidence: 0,
  human_verified_only: false,
  country: null as string | null,
  location_name: null as string | null,
})

const changeHeaders = computed(() => [
  { title: t('common.type'), key: 'change_type' },
  { title: 'URL', key: 'affected_url', maxWidth: '400px' },
  { title: t('exportView.detected'), key: 'detected_at' },
])

const getChangeColor = (type: string) => {
  const colors: Record<string, string> = {
    NEW_DOCUMENT: 'success',
    CONTENT_CHANGED: 'info',
    REMOVED: 'error',
    METADATA_CHANGED: 'warning',
  }
  return colors[type] || 'grey'
}

const formatDate = (dateStr: string) => {
  return format(new Date(dateStr), 'dd.MM.yyyy HH:mm', { locale: dateLocale.value })
}

const loadCategories = async () => {
  const response = await adminApi.getCategories({ per_page: 100 })
  categories.value = response.data.items
}

const loadCountries = async () => {
  try {
    const response = await dataApi.getExtractionCountries()
    countries.value = response.data
  } catch (e) {
    console.error('Failed to load countries:', e)
    countries.value = []
  }
}

const loadLocations = async () => {
  try {
    const response = await dataApi.getExtractionLocations()
    locations.value = response.data
  } catch (e) {
    console.error('Failed to load locations:', e)
    locations.value = []
  }
}

const loadChanges = async () => {
  loadingChanges.value = true
  try {
    const response = await exportApi.getChangesFeed({ limit: 500 })
    changes.value = response.data.changes
  } finally {
    loadingChanges.value = false
  }
}

const exportJson = async () => {
  exporting.value = true
  try {
    const response = await exportApi.exportJson(exportOptions.value)
    downloadBlob(response.data, 'caelichrawler_export.json', 'application/json')
    showSuccess(t('exportView.messages.jsonSuccess'))
  } catch (error: any) {
    showError(error.response?.data?.error || t('exportView.messages.jsonError'))
  } finally {
    exporting.value = false
  }
}

const exportCsv = async () => {
  exporting.value = true
  try {
    const response = await exportApi.exportCsv(exportOptions.value)
    downloadBlob(response.data, 'caelichrawler_export.csv', 'text/csv')
    showSuccess(t('exportView.messages.csvSuccess'))
  } catch (error: any) {
    showError(error.response?.data?.error || t('exportView.messages.csvError'))
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
  if (!webhookUrl.value) return
  testingWebhook.value = true
  webhookResult.value = null
  try {
    const response = await exportApi.testWebhook(webhookUrl.value)
    webhookResult.value = response.data
    if (response.data.success) {
      showSuccess(t('exportView.messages.webhookSuccess'))
    } else {
      showError(t('exportView.messages.webhookError'))
    }
  } catch (error: any) {
    webhookResult.value = { success: false, error: error.message }
    showError(t('exportView.messages.webhookError') + ': ' + error.message)
  } finally {
    testingWebhook.value = false
  }
}

onMounted(() => {
  loadCategories()
  loadCountries()
  loadLocations()
  loadChanges()
})
</script>
