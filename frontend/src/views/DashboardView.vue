<template>
  <div>
    <h1 class="text-h4 mb-6">Dashboard</h1>

    <!-- Stats Cards -->
    <v-row>
      <v-col cols="12" md="3">
        <v-card>
          <v-card-text class="text-center">
            <v-icon size="48" color="primary" class="mb-2">mdi-folder-multiple</v-icon>
            <div class="text-h4">{{ stats.categories }}</div>
            <div class="text-subtitle-1">Kategorien</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="3">
        <v-card>
          <v-card-text class="text-center">
            <v-icon size="48" color="success" class="mb-2">mdi-web</v-icon>
            <div class="text-h4">{{ stats.sources }}</div>
            <div class="text-subtitle-1">Datenquellen</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="3">
        <v-card>
          <v-card-text class="text-center">
            <v-icon size="48" color="info" class="mb-2">mdi-file-document-multiple</v-icon>
            <div class="text-h4">{{ stats.documents }}</div>
            <div class="text-subtitle-1">Dokumente</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="3">
        <v-card>
          <v-card-text class="text-center">
            <v-icon size="48" color="warning" class="mb-2">mdi-robot</v-icon>
            <div class="text-h4">{{ crawlerStatus.running_jobs }}</div>
            <div class="text-subtitle-1">Aktive Crawler</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Active Crawlers (Live) -->
    <v-row class="mt-4" v-if="runningJobs.length > 0">
      <v-col cols="12">
        <v-card class="active-crawler-card" variant="outlined">
          <v-progress-linear indeterminate color="info" height="3"></v-progress-linear>
          <v-card-title class="d-flex align-center">
            <v-icon left color="info" class="mdi-spin">mdi-loading</v-icon>
            <span class="ml-2">Aktive Crawler</span>
            <v-spacer></v-spacer>
            <v-chip size="small" color="info" variant="tonal">Auto-Update aktiv</v-chip>
          </v-card-title>
          <v-card-text>
            <v-list>
              <v-list-item
                v-for="job in runningJobs"
                :key="job.id"
                class="mb-2 rounded active-crawler-item"
              >
                <template v-slot:prepend>
                  <v-icon color="info" class="mdi-spin">mdi-web-sync</v-icon>
                </template>
                <v-list-item-title class="font-weight-bold">{{ job.source_name }}</v-list-item-title>
                <v-list-item-subtitle>
                  <div class="d-flex align-center flex-wrap mt-1 ga-1">
                    <v-chip size="x-small" color="primary" variant="tonal">
                      <v-icon size="small" start>mdi-file-document</v-icon>
                      {{ job.documents_found }} Dokumente
                    </v-chip>
                    <v-chip size="x-small" color="success" variant="tonal">
                      <v-icon size="small" start>mdi-new-box</v-icon>
                      {{ job.documents_new }} neu
                    </v-chip>
                    <v-chip size="x-small" color="warning" variant="tonal" v-if="job.error_count > 0">
                      <v-icon size="small" start>mdi-alert</v-icon>
                      {{ job.error_count }} Fehler
                    </v-chip>
                  </div>
                  <div class="text-caption text-medium-emphasis mt-1">
                    Gestartet: {{ formatTime(job.started_at) }} |
                    Laufzeit: {{ getRuntime(job.started_at) }}
                  </div>
                </v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Crawler Status & Recent Activity -->
    <v-row class="mt-4">
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-robot</v-icon>
            Crawler Status
          </v-card-title>
          <v-card-text>
            <v-list>
              <v-list-item>
                <template v-slot:prepend>
                  <v-icon color="success">mdi-circle</v-icon>
                </template>
                <v-list-item-title>Aktive Workers</v-list-item-title>
                <template v-slot:append>
                  <span class="text-h6">{{ crawlerStatus.worker_count }}</span>
                </template>
              </v-list-item>
              <v-list-item>
                <template v-slot:prepend>
                  <v-icon color="info">mdi-run</v-icon>
                </template>
                <v-list-item-title>Laufende Jobs</v-list-item-title>
                <template v-slot:append>
                  <span class="text-h6">{{ crawlerStatus.running_jobs }}</span>
                </template>
              </v-list-item>
              <v-list-item>
                <template v-slot:prepend>
                  <v-icon color="warning">mdi-clock-outline</v-icon>
                </template>
                <v-list-item-title>Wartende Jobs</v-list-item-title>
                <template v-slot:append>
                  <span class="text-h6">{{ crawlerStatus.pending_jobs }}</span>
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-history</v-icon>
            Letzte Crawl-Jobs
          </v-card-title>
          <v-card-text>
            <v-list v-if="recentJobs.length > 0">
              <v-list-item
                v-for="job in recentJobs"
                :key="job.id"
              >
                <template v-slot:prepend>
                  <v-icon :color="getStatusColor(job.status)">
                    {{ getStatusIcon(job.status) }}
                  </v-icon>
                </template>
                <v-list-item-title>{{ job.source_name }}</v-list-item-title>
                <v-list-item-subtitle>
                  {{ job.documents_found }} Dokumente gefunden
                </v-list-item-subtitle>
              </v-list-item>
            </v-list>
            <div v-else class="text-center py-4">
              <v-icon size="48" color="grey">mdi-information-outline</v-icon>
              <p class="text-subtitle-1 mt-2">Noch keine Crawl-Jobs vorhanden</p>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Quick Actions -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>Schnellaktionen</v-card-title>
          <v-card-text>
            <v-btn color="primary" class="mr-2" to="/categories">
              <v-icon left>mdi-plus</v-icon>
              Neue Kategorie
            </v-btn>
            <v-btn color="success" class="mr-2" to="/sources">
              <v-icon left>mdi-web-plus</v-icon>
              Neue Datenquelle
            </v-btn>
            <v-btn color="warning" class="mr-2" @click="showStartCrawlerDialog = true">
              <v-icon left>mdi-play</v-icon>
              Crawler starten
            </v-btn>
            <v-btn color="info" to="/export">
              <v-icon left>mdi-export</v-icon>
              Daten exportieren
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Start Crawler Dialog -->
    <v-dialog v-model="showStartCrawlerDialog" max-width="650">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2">mdi-spider-web</v-icon>
          Crawler starten
        </v-card-title>
        <v-card-text>
          <!-- Estimated count -->
          <v-alert :type="filteredSourceCount > 100 ? 'warning' : 'info'" class="mb-4">
            <div class="d-flex align-center justify-space-between">
              <span>
                <strong>{{ filteredSourceCount.toLocaleString() }}</strong> Datenquellen werden gecrawlt
              </span>
              <v-btn
                v-if="hasAnyFilter"
                size="small"
                variant="text"
                @click="resetCrawlerFilters"
              >
                Filter zurücksetzen
              </v-btn>
            </div>
          </v-alert>

          <v-row>
            <v-col cols="12" md="6">
              <v-select
                v-model="crawlerFilter.category_id"
                :items="crawlerCategories"
                item-title="name"
                item-value="id"
                label="Kategorie"
                clearable
                density="comfortable"
                @update:model-value="updateFilteredCount"
              ></v-select>
            </v-col>
            <v-col cols="12" md="6">
              <v-select
                v-model="crawlerFilter.country"
                :items="countryOptions"
                item-title="label"
                item-value="value"
                label="Land"
                clearable
                density="comfortable"
                @update:model-value="updateFilteredCount"
              ></v-select>
            </v-col>
          </v-row>

          <v-row>
            <v-col cols="12" md="6">
              <v-text-field
                v-model="crawlerFilter.search"
                label="Suche (Name/URL)"
                prepend-inner-icon="mdi-magnify"
                clearable
                density="comfortable"
                hint="Filtert nach Name oder URL"
                @update:model-value="debouncedUpdateFilteredCount"
              ></v-text-field>
            </v-col>
            <v-col cols="12" md="6">
              <v-text-field
                v-model.number="crawlerFilter.limit"
                label="Maximale Anzahl"
                type="number"
                :min="1"
                :max="10000"
                prepend-inner-icon="mdi-numeric"
                clearable
                density="comfortable"
                hint="Leer = alle"
                persistent-hint
              ></v-text-field>
            </v-col>
          </v-row>

          <v-row>
            <v-col cols="12" md="6">
              <v-select
                v-model="crawlerFilter.status"
                :items="[
                  { value: 'ACTIVE', label: 'Aktiv' },
                  { value: 'PENDING', label: 'Ausstehend' },
                  { value: 'ERROR', label: 'Fehler' },
                ]"
                item-title="label"
                item-value="value"
                label="Status"
                clearable
                density="comfortable"
                @update:model-value="updateFilteredCount"
              ></v-select>
            </v-col>
            <v-col cols="12" md="6">
              <v-select
                v-model="crawlerFilter.source_type"
                :items="[
                  { value: 'WEBSITE', label: 'Website' },
                  { value: 'OPARL_API', label: 'OParl API' },
                  { value: 'RSS', label: 'RSS Feed' },
                ]"
                item-title="label"
                item-value="value"
                label="Quellentyp"
                clearable
                density="comfortable"
                @update:model-value="updateFilteredCount"
              ></v-select>
            </v-col>
          </v-row>

          <v-divider class="my-4"></v-divider>

          <v-alert v-if="filteredSourceCount > 500" type="error" variant="tonal" density="compact">
            <v-icon>mdi-alert</v-icon>
            Mehr als 500 Quellen - bitte Filter oder Limit setzen!
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-chip size="small" variant="tonal">
            {{ filteredSourceCount.toLocaleString() }} Quellen
          </v-chip>
          <v-spacer></v-spacer>
          <v-btn @click="showStartCrawlerDialog = false">Abbrechen</v-btn>
          <v-btn
            color="warning"
            :loading="startingCrawlers"
            :disabled="filteredSourceCount === 0"
            @click="startFilteredCrawlers"
          >
            <v-icon left>mdi-play</v-icon>
            Crawler starten
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { adminApi } from '@/services/api'

const stats = ref({
  categories: 0,
  sources: 0,
  documents: 0,
  extractions: 0,
})

const crawlerStatus = ref({
  running_jobs: 0,
  pending_jobs: 0,
  worker_count: 0,
  active_tasks: 0,
})

const recentJobs = ref<any[]>([])
const runningJobs = ref<any[]>([])
let refreshInterval: number | null = null

// Crawler start dialog
const showStartCrawlerDialog = ref(false)
const startingCrawlers = ref(false)
const crawlerCategories = ref<any[]>([])
const filteredSourceCount = ref(0)
const countryOptions = ref([
  { value: 'DE', label: 'Deutschland' },
  { value: 'GB', label: 'United Kingdom' },
])
const crawlerFilter = ref({
  category_id: null as string | null,
  country: null as string | null,
  search: null as string | null,
  limit: null as number | null,
  status: null as string | null,
  source_type: null as string | null,
})

const hasAnyFilter = computed(() => {
  return crawlerFilter.value.category_id ||
         crawlerFilter.value.country ||
         crawlerFilter.value.search ||
         crawlerFilter.value.status ||
         crawlerFilter.value.source_type
})

const resetCrawlerFilters = () => {
  crawlerFilter.value = {
    category_id: null,
    country: null,
    search: null,
    limit: null,
    status: null,
    source_type: null,
  }
  updateFilteredCount()
}

let filterTimeout: ReturnType<typeof setTimeout> | null = null
const debouncedUpdateFilteredCount = () => {
  if (filterTimeout) clearTimeout(filterTimeout)
  filterTimeout = setTimeout(() => updateFilteredCount(), 300)
}

const updateFilteredCount = async () => {
  try {
    const params: any = { per_page: 1 }  // We only need the count
    if (crawlerFilter.value.category_id) params.category_id = crawlerFilter.value.category_id
    if (crawlerFilter.value.country) params.country = crawlerFilter.value.country
    if (crawlerFilter.value.search) params.search = crawlerFilter.value.search
    if (crawlerFilter.value.status) params.status = crawlerFilter.value.status
    if (crawlerFilter.value.source_type) params.source_type = crawlerFilter.value.source_type

    const response = await adminApi.getSources(params)
    let count = response.data.total || 0

    // Apply limit if set
    if (crawlerFilter.value.limit && crawlerFilter.value.limit > 0) {
      count = Math.min(count, crawlerFilter.value.limit)
    }

    filteredSourceCount.value = count
  } catch (error) {
    console.error('Failed to get filtered count:', error)
    filteredSourceCount.value = stats.value.sources
  }
}

const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    COMPLETED: 'success',
    RUNNING: 'info',
    PENDING: 'warning',
    FAILED: 'error',
  }
  return colors[status] || 'grey'
}

const getStatusIcon = (status: string) => {
  const icons: Record<string, string> = {
    COMPLETED: 'mdi-check-circle',
    RUNNING: 'mdi-loading mdi-spin',
    PENDING: 'mdi-clock-outline',
    FAILED: 'mdi-alert-circle',
  }
  return icons[status] || 'mdi-help-circle'
}

const formatTime = (dateStr: string) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

const getRuntime = (startedAt: string) => {
  if (!startedAt) return '-'
  const start = new Date(startedAt)
  const now = new Date()
  const diffMs = now.getTime() - start.getTime()
  const diffSec = Math.floor(diffMs / 1000)
  const mins = Math.floor(diffSec / 60)
  const secs = diffSec % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const startFilteredCrawlers = async () => {
  startingCrawlers.value = true
  try {
    const params: any = {}
    if (crawlerFilter.value.category_id) params.category_id = crawlerFilter.value.category_id
    if (crawlerFilter.value.country) params.country = crawlerFilter.value.country
    if (crawlerFilter.value.search) params.search = crawlerFilter.value.search
    if (crawlerFilter.value.status) params.status = crawlerFilter.value.status
    if (crawlerFilter.value.source_type) params.source_type = crawlerFilter.value.source_type
    if (crawlerFilter.value.limit) params.limit = crawlerFilter.value.limit

    // Start crawler with filters
    await adminApi.startCrawl(params)
    showStartCrawlerDialog.value = false

    // Reset filters for next time
    resetCrawlerFilters()

    // Refresh data
    await loadData()
  } catch (error) {
    console.error('Failed to start crawlers:', error)
  } finally {
    startingCrawlers.value = false
  }
}

// Watch for dialog open to initialize count
watch(showStartCrawlerDialog, (isOpen) => {
  if (isOpen) {
    filteredSourceCount.value = stats.value.sources
    updateFilteredCount()
  }
})

const loadCategories = async () => {
  try {
    const response = await adminApi.getCategories({ per_page: 100 })
    crawlerCategories.value = response.data.items
  } catch (error) {
    console.error('Failed to load categories:', error)
  }
}

const loadData = async () => {
  try {
    // Load categories count
    const catResponse = await adminApi.getCategories({ per_page: 1 })
    stats.value.categories = catResponse.data.total

    // Load sources count
    const srcResponse = await adminApi.getSources({ per_page: 1 })
    stats.value.sources = srcResponse.data.total

    // Load crawler status
    const statusResponse = await adminApi.getCrawlerStatus()
    crawlerStatus.value = statusResponse.data

    // Load recent jobs
    const jobsResponse = await adminApi.getCrawlerJobs({ per_page: 10 })
    recentJobs.value = jobsResponse.data.items.filter((j: any) => j.status !== 'RUNNING').slice(0, 5)
    runningJobs.value = jobsResponse.data.items.filter((j: any) => j.status === 'RUNNING')

    // Load crawler stats for documents
    const statsResponse = await adminApi.getCrawlerStats()
    stats.value.documents = statsResponse.data.total_documents

    // Start/stop auto-refresh based on running jobs
    if (runningJobs.value.length > 0 && !refreshInterval) {
      refreshInterval = window.setInterval(loadData, 5000) // Refresh every 5 seconds
    } else if (runningJobs.value.length === 0 && refreshInterval) {
      clearInterval(refreshInterval)
      refreshInterval = null
    }
  } catch (error) {
    console.error('Failed to load dashboard data:', error)
  }
}

onMounted(() => {
  loadData()
  loadCategories()
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
/* Active Crawler Card - Theme-aware styling */
.active-crawler-card {
  border-color: rgb(var(--v-theme-info)) !important;
  border-width: 2px !important;
}

.active-crawler-item {
  background-color: rgba(var(--v-theme-info), 0.08);
  border: 1px solid rgba(var(--v-theme-info), 0.2);
}

.active-crawler-item:hover {
  background-color: rgba(var(--v-theme-info), 0.12);
}
</style>
