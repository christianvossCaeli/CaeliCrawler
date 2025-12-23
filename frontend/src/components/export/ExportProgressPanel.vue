<template>
  <v-card class="export-progress-panel">
    <v-card-title class="d-flex align-center">
      <v-icon start>mdi-export</v-icon>
      {{ t('export.asyncExport') }}
      <v-spacer />
      <v-btn
        v-if="!isLoading && activeJobs.length === 0"
        icon
        variant="text"
        size="small"
        @click="$emit('close')"
      >
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </v-card-title>

    <v-card-text>
      <!-- Active Jobs -->
      <div v-if="activeJobs.length > 0" class="mb-4">
        <div class="text-subtitle-2 mb-2">{{ t('export.activeJobs') }}</div>
        <v-card
          v-for="job in activeJobs"
          :key="job.id"
          variant="outlined"
          class="mb-2"
        >
          <v-card-text class="py-2">
            <div class="d-flex align-center justify-space-between mb-2">
              <div class="d-flex align-center">
                <v-chip
                  size="x-small"
                  :color="getStatusColor(job.status)"
                  class="mr-2"
                >
                  {{ getStatusLabel(job.status) }}
                </v-chip>
                <span class="text-body-2">{{ job.export_format.toUpperCase() }}</span>
              </div>
              <v-btn
                v-if="job.status === 'pending' || job.status === 'processing'"
                icon
                variant="text"
                size="x-small"
                color="error"
                :title="t('export.cancel')"
                @click="cancelJob(job.id)"
              >
                <v-icon size="small">mdi-close-circle</v-icon>
              </v-btn>
            </div>

            <!-- Progress Bar -->
            <v-progress-linear
              v-if="job.status === 'processing'"
              :model-value="job.progress_percent || 0"
              color="primary"
              height="6"
              rounded
              class="mb-1"
            />

            <div class="text-caption text-medium-emphasis">
              <span v-if="job.progress_message">{{ job.progress_message }}</span>
              <span v-else-if="job.status === 'pending'">{{ t('export.waiting') }}</span>
              <span v-else-if="job.total_records">
                {{ job.processed_records || 0 }} / {{ job.total_records }} {{ t('export.records') }}
              </span>
            </div>
          </v-card-text>
        </v-card>
      </div>

      <!-- Completed Jobs -->
      <div v-if="completedJobs.length > 0">
        <div class="text-subtitle-2 mb-2">{{ t('export.completedJobs') }}</div>
        <v-card
          v-for="job in completedJobs"
          :key="job.id"
          variant="outlined"
          class="mb-2"
        >
          <v-card-text class="py-2">
            <div class="d-flex align-center justify-space-between">
              <div class="d-flex align-center">
                <v-chip
                  size="x-small"
                  :color="getStatusColor(job.status)"
                  class="mr-2"
                >
                  {{ getStatusLabel(job.status) }}
                </v-chip>
                <span class="text-body-2">
                  {{ job.export_format.toUpperCase() }}
                  <span v-if="job.processed_records" class="text-medium-emphasis">
                    ({{ job.processed_records }} {{ t('export.records') }})
                  </span>
                </span>
              </div>

              <div class="d-flex align-center">
                <!-- Download Button -->
                <v-btn
                  v-if="job.is_downloadable"
                  icon
                  variant="text"
                  size="small"
                  color="success"
                  :title="t('export.download')"
                  :loading="downloadingId === job.id"
                  @click="downloadJob(job.id, job.export_format)"
                >
                  <v-icon>mdi-download</v-icon>
                </v-btn>

                <!-- Error Info -->
                <v-tooltip v-if="job.error_message" location="top">
                  <template v-slot:activator="{ props }">
                    <v-icon v-bind="props" color="error" size="small" class="ml-1">
                      mdi-alert-circle
                    </v-icon>
                  </template>
                  {{ job.error_message }}
                </v-tooltip>
              </div>
            </div>

            <div class="text-caption text-medium-emphasis mt-1">
              {{ formatTime(job.completed_at || job.created_at) }}
              <span v-if="job.file_size" class="ml-2">
                {{ formatFileSize(job.file_size) }}
              </span>
            </div>
          </v-card-text>
        </v-card>
      </div>

      <!-- Empty State -->
      <div
        v-if="!isLoading && activeJobs.length === 0 && completedJobs.length === 0"
        class="text-center py-4"
      >
        <v-icon size="48" color="grey-lighten-1">mdi-export-variant</v-icon>
        <p class="text-body-2 text-medium-emphasis mt-2">
          {{ t('export.noJobs') }}
        </p>
      </div>

      <!-- Loading State -->
      <div v-if="isLoading" class="text-center py-4">
        <v-progress-circular indeterminate color="primary" />
      </div>
    </v-card-text>

    <!-- Start New Export -->
    <v-card-actions>
      <v-btn
        variant="text"
        size="small"
        @click="refreshJobs"
        :loading="isLoading"
      >
        <v-icon start size="small">mdi-refresh</v-icon>
        {{ t('common.refresh') }}
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { exportApi } from '@/services/api'

const { t } = useI18n()

interface ExportJob {
  id: string
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled'
  export_format: string
  total_records: number | null
  processed_records: number | null
  progress_percent: number | null
  progress_message: string | null
  file_size: number | null
  error_message: string | null
  created_at: string | null
  started_at: string | null
  completed_at: string | null
  is_downloadable: boolean
}

const emit = defineEmits<{
  close: []
}>()

const jobs = ref<ExportJob[]>([])
const isLoading = ref(false)
const downloadingId = ref<string | null>(null)
let pollInterval: ReturnType<typeof setInterval> | null = null

const activeJobs = computed(() =>
  jobs.value.filter(j => j.status === 'pending' || j.status === 'processing')
)

const completedJobs = computed(() =>
  jobs.value
    .filter(j => j.status === 'completed' || j.status === 'failed' || j.status === 'cancelled')
    .slice(0, 5)
)

function getStatusColor(status: string): string {
  switch (status) {
    case 'pending': return 'grey'
    case 'processing': return 'primary'
    case 'completed': return 'success'
    case 'failed': return 'error'
    case 'cancelled': return 'warning'
    default: return 'grey'
  }
}

function getStatusLabel(status: string): string {
  return t(`export.status.${status}`)
}

function formatTime(dateString: string | null): string {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleString()
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

async function refreshJobs() {
  isLoading.value = true
  try {
    const response = await exportApi.listExportJobs({ limit: 10 })
    jobs.value = response.data
  } catch (error) {
    console.error('Failed to load export jobs:', error)
  } finally {
    isLoading.value = false
  }
}

async function cancelJob(jobId: string) {
  try {
    await exportApi.cancelExportJob(jobId)
    await refreshJobs()
  } catch (error) {
    console.error('Failed to cancel job:', error)
  }
}

async function downloadJob(jobId: string, format: string) {
  downloadingId.value = jobId
  try {
    const response = await exportApi.downloadExport(jobId)
    const blob = new Blob([response.data])
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const normalizedFormat = format.toLowerCase()
    const extensionMap: Record<string, string> = {
      json: 'json',
      csv: 'csv',
      excel: 'xlsx',
    }
    a.download = `export.${extensionMap[normalizedFormat] || normalizedFormat}`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  } catch (error) {
    console.error('Failed to download:', error)
  } finally {
    downloadingId.value = null
  }
}

function startPolling() {
  if (pollInterval) return
  pollInterval = setInterval(() => {
    if (activeJobs.value.length > 0) {
      refreshJobs()
    }
  }, 3000) // Poll every 3 seconds when there are active jobs
}

function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

onMounted(() => {
  refreshJobs()
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})

// Expose refresh for parent components
defineExpose({ refreshJobs })
</script>

<style scoped>
.export-progress-panel {
  width: 100%;
}
</style>
