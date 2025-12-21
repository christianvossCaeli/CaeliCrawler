<template>
  <div>
    <!-- Loading Overlay (only on initial load) -->
    <v-overlay :model-value="loading && initialLoad" class="align-center justify-center" persistent >
      <v-card class="pa-8 text-center" min-width="320" elevation="24">
        <v-progress-circular indeterminate size="80" width="6" color="primary" class="mb-4"></v-progress-circular>
        <div class="text-h6 mb-2">{{ $t('crawler.dataLoading') }}</div>
        <div class="text-body-2 text-medium-emphasis">{{ $t('crawler.loadingStatus') }}</div>
      </v-card>
    </v-overlay>

    <div class="d-flex align-center mb-6">
      <h1 class="text-h4">{{ $t('crawler.title') }}</h1>
      <v-spacer></v-spacer>
      <v-btn
        v-if="status.running_jobs > 0 || status.pending_jobs > 0"
        color="error"
        variant="outlined"
        prepend-icon="mdi-stop"
        :loading="stoppingAll"
        @click="stopAllCrawlers"
      >
        {{ $t('crawler.stopAll') }}
      </v-btn>
    </div>

    <!-- Live Status -->
    <v-row class="mb-4">
      <v-col cols="12" md="3">
        <v-card color="success" dark>
          <v-card-text class="text-center">
            <div class="text-h3">{{ status.worker_count }}</div>
            <div>{{ $t('crawler.activeWorkers') }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card color="info" dark>
          <v-card-text class="text-center">
            <div class="text-h3">{{ status.running_jobs }}</div>
            <div>{{ $t('crawler.runningJobs') }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card color="warning" dark>
          <v-card-text class="text-center">
            <div class="text-h3">{{ status.pending_jobs }}</div>
            <div>{{ $t('crawler.pendingJobs') }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card color="primary" dark>
          <v-card-text class="text-center">
            <div class="text-h3">{{ stats.total_documents }}</div>
            <div>{{ $t('crawler.totalDocuments') }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Running AI Tasks -->
    <v-card v-if="runningAiTasks.length > 0" class="mb-4" color="info-lighten-5">
      <v-card-title class="d-flex align-center">
        <v-icon color="info" class="mr-2 mdi-spin">mdi-loading</v-icon>
        {{ $t('crawler.aiTasks') }} ({{ runningAiTasks.length }})
        <v-spacer></v-spacer>
        <v-chip size="small" color="info">{{ $t('crawler.liveUpdates') }}</v-chip>
      </v-card-title>
      <v-card-text>
        <v-list dense>
          <v-list-item
            v-for="task in runningAiTasks"
            :key="task.id"
          >
            <template v-slot:prepend>
              <v-icon color="info" class="mdi-spin" size="small">mdi-brain</v-icon>
            </template>
            <v-list-item-title>{{ task.name }}</v-list-item-title>
            <v-list-item-subtitle>
              <span v-if="task.current_item">{{ $t('crawler.current') }}: {{ task.current_item }}</span>
              <span v-else>{{ $t('crawler.processing') }}</span>
              <span class="ml-2">{{ task.progress_current }}/{{ task.progress_total }}</span>
            </v-list-item-subtitle>
            <template v-slot:append>
              <div class="d-flex align-center">
                <v-progress-linear
                  :model-value="task.progress_percent"
                  height="8"
                  rounded
                  color="info"
                  style="width: 100px"
                  class="mr-2"
                ></v-progress-linear>
                <span class="text-caption mr-2">{{ Math.round(task.progress_percent) }}%</span>
                <v-btn
                  icon="mdi-stop"
                  size="small"
                  color="error"
                  variant="tonal"
                  @click.stop="cancelAiTask(task)"
                  :title="$t('crawler.cancel')"
                ></v-btn>
              </div>
            </template>
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>

    <!-- Active Crawlers with Live Log -->
    <v-card v-if="runningJobs.length > 0" class="mb-4 card-running">
      <v-card-title class="d-flex align-center">
        <v-icon color="info" class="mr-2 mdi-spin">mdi-loading</v-icon>
        {{ $t('crawler.activeCrawlers') }} ({{ runningJobs.length }})
        <v-spacer></v-spacer>
        <v-chip size="small" color="info">{{ $t('crawler.liveUpdatesInterval') }}</v-chip>
      </v-card-title>
      <v-card-text>
        <v-expansion-panels variant="accordion">
          <v-expansion-panel
            v-for="rj in runningJobs"
            :key="rj.id"
            @group:selected="loadJobLog(rj.id)"
          >
            <v-expansion-panel-title>
              <div class="d-flex align-center w-100">
                <v-icon color="info" class="mr-2 mdi-spin" size="small">mdi-web-sync</v-icon>
                <div class="flex-grow-1">
                  <div class="font-weight-bold">{{ rj.source_name }}</div>
                  <div class="text-caption text-primary">
                    <v-icon size="x-small" class="mr-1">mdi-tag</v-icon>
                    {{ rj.category_name || $t('crawler.noCategory') }}
                  </div>
                  <div class="text-caption text-truncate" style="max-width: 400px;">
                    {{ rj.current_url || rj.base_url }}
                  </div>
                </div>
                <div class="d-flex align-center mr-4">
                  <v-chip size="x-small" color="primary" class="mr-1">
                    {{ rj.pages_crawled }} {{ $t('crawler.pages') }}
                  </v-chip>
                  <v-chip size="x-small" color="success" class="mr-1">
                    {{ rj.documents_found }} {{ $t('crawler.docs') }}
                  </v-chip>
                  <v-chip size="x-small" color="warning" v-if="rj.error_count > 0">
                    {{ rj.error_count }} {{ $t('crawler.errors') }}
                  </v-chip>
                </div>
                <v-btn
                  icon="mdi-stop"
                  size="small"
                  color="error"
                  variant="tonal"
                  @click.stop="cancelJob(rj)"
                  :title="$t('crawler.cancel')"
                ></v-btn>
              </div>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <div v-if="jobLogs[rj.id]" class="pa-2">
                <div class="text-subtitle-2 mb-2">
                  {{ $t('crawler.currentUrl') }}:
                  <code class="text-caption">{{ jobLogs[rj.id].current_url || '-' }}</code>
                </div>
                <v-divider class="mb-2"></v-divider>
                <div class="text-subtitle-2 mb-1">{{ $t('crawler.recentActivities') }}:</div>
                <v-virtual-scroll
                  :items="jobLogs[rj.id].log_entries || []"
                  height="200"
                  item-height="32"
                >
                  <template v-slot:default="{ item }">
                    <div class="d-flex align-center py-1" style="font-family: monospace; font-size: 11px;">
                      <v-icon
                        :color="item.status === 'document' ? 'success' : (item.status === 'error' ? 'error' : 'grey')"
                        size="x-small"
                        class="mr-2"
                      >
                        {{ item.status === 'document' ? 'mdi-file-document' : (item.status === 'error' ? 'mdi-alert' : 'mdi-web') }}
                      </v-icon>
                      <span class="text-truncate flex-grow-1">{{ item.url }}</span>
                      <span class="text-caption text-medium-emphasis ml-2">{{ formatLogTime(item.timestamp) }}</span>
                    </div>
                  </template>
                </v-virtual-scroll>
              </div>
              <div v-else class="text-center pa-4">
                <v-progress-circular indeterminate size="24"></v-progress-circular>
                <div class="text-caption mt-2">{{ $t('crawler.loadingLog') }}</div>
              </div>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-card-text>
    </v-card>

    <!-- Jobs Table -->
    <v-card>
      <v-card-title>
        <v-row align="center">
          <v-col>{{ $t('crawler.crawlJobs') }}</v-col>
          <v-col cols="auto">
            <v-btn-toggle v-model="statusFilter" color="primary" mandatory>
              <v-btn value="">{{ $t('crawler.all') }}</v-btn>
              <v-btn value="RUNNING">{{ $t('crawler.running') }}</v-btn>
              <v-btn value="COMPLETED">{{ $t('crawler.completed') }}</v-btn>
              <v-btn value="FAILED">{{ $t('crawler.failed') }}</v-btn>
            </v-btn-toggle>
          </v-col>
        </v-row>
      </v-card-title>

      <v-data-table
        :headers="headers"
        :items="filteredJobs"
        :loading="loading"
        :items-per-page="20"
      >
        <template v-slot:item.status="{ item }">
          <v-chip :color="getStatusColor(item.status)" size="small">
            <v-icon v-if="item.status === 'RUNNING'" class="mr-1" size="small">mdi-loading mdi-spin</v-icon>
            {{ item.status }}
          </v-chip>
        </template>

        <template v-slot:item.scheduled_at="{ item }">
          {{ formatDate(item.scheduled_at) }}
        </template>

        <template v-slot:item.duration="{ item }">
          {{ item.duration_seconds ? formatDuration(item.duration_seconds) : '-' }}
        </template>

        <template v-slot:item.progress="{ item }">
          <div class="d-flex align-center">
            <span class="mr-2">{{ item.documents_processed }}/{{ item.documents_found }}</span>
            <v-progress-linear
              :model-value="item.documents_found > 0 ? (item.documents_processed / item.documents_found) * 100 : 0"
              height="8"
              rounded
              color="primary"
              style="width: 100px"
            ></v-progress-linear>
          </div>
        </template>

        <template v-slot:item.actions="{ item }">
          <div class="table-actions">
            <v-btn
              v-if="item.status === 'RUNNING'"
              icon="mdi-stop"
              size="small"
              variant="tonal"
              color="error"
              :title="$t('common.cancel')"
              @click="cancelJob(item)"
            ></v-btn>
            <v-btn
              icon="mdi-information"
              size="small"
              variant="tonal"
              :title="$t('common.details')"
              @click="showJobDetails(item)"
            ></v-btn>
          </div>
        </template>
      </v-data-table>
    </v-card>

    <!-- Job Details Dialog -->
    <v-dialog v-model="detailsDialog" max-width="800">
      <v-card v-if="selectedJob">
        <v-card-title>{{ $t('crawler.jobDetails') }}</v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="6">
              <strong>{{ $t('crawler.source') }}:</strong> {{ selectedJob.source_name }}
            </v-col>
            <v-col cols="6">
              <strong>{{ $t('crawler.category') }}:</strong> {{ selectedJob.category_name }}
            </v-col>
            <v-col cols="6">
              <strong>{{ $t('crawler.status') }}:</strong>
              <v-chip :color="getStatusColor(selectedJob.status)" size="small">
                {{ selectedJob.status }}
              </v-chip>
            </v-col>
            <v-col cols="6">
              <strong>{{ $t('crawler.duration') }}:</strong> {{ selectedJob.duration_seconds ? formatDuration(selectedJob.duration_seconds) : '-' }}
            </v-col>
          </v-row>

          <v-divider class="my-4"></v-divider>

          <v-row>
            <v-col cols="4">
              <v-card outlined>
                <v-card-text class="text-center">
                  <div class="text-h5">{{ selectedJob.pages_crawled }}</div>
                  <div class="text-caption">{{ $t('crawler.pagesCrawled') }}</div>
                </v-card-text>
              </v-card>
            </v-col>
            <v-col cols="4">
              <v-card outlined>
                <v-card-text class="text-center">
                  <div class="text-h5">{{ selectedJob.documents_found }}</div>
                  <div class="text-caption">{{ $t('crawler.documentsFound') }}</div>
                </v-card-text>
              </v-card>
            </v-col>
            <v-col cols="4">
              <v-card outlined>
                <v-card-text class="text-center">
                  <div class="text-h5">{{ selectedJob.documents_new }}</div>
                  <div class="text-caption">{{ $t('crawler.newDocuments') }}</div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>

          <div v-if="selectedJob.error_log && selectedJob.error_log.length > 0" class="mt-4">
            <strong>{{ $t('crawler.errors') }}:</strong>
            <v-alert
              v-for="(error, idx) in selectedJob.error_log"
              :key="idx"
              type="error"
              variant="tonal"
              class="mt-2"
            >
              {{ error.error }}
            </v-alert>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="detailsDialog = false">{{ $t('crawler.close') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { adminApi } from '@/services/api'
import { format } from 'date-fns'
import { de } from 'date-fns/locale'
import { useSnackbar } from '@/composables/useSnackbar'

interface LogEntry {
  status: string
  url: string
  timestamp: string
}

interface JobLog {
  current_url: string
  log_entries: LogEntry[]
}

const { t } = useI18n()
const { showSuccess, showError } = useSnackbar()

const loading = ref(true)
const initialLoad = ref(true)
const stoppingAll = ref(false)
const jobs = ref<any[]>([])
const runningJobs = ref<any[]>([])
const runningAiTasks = ref<any[]>([])
const jobLogs = ref<Record<string, JobLog>>({})
const statusFilter = ref('')
const detailsDialog = ref(false)
const selectedJob = ref<any>(null)
let refreshInterval: number | null = null
let logRefreshInterval: number | null = null

const status = ref({
  running_jobs: 0,
  pending_jobs: 0,
  worker_count: 0,
  active_tasks: 0,
  running_ai_tasks: 0,
})

const stats = ref({
  total_jobs: 0,
  total_documents: 0,
  completed_jobs: 0,
  failed_jobs: 0,
})

const headers = [
  { title: t('crawler.source'), key: 'source_name' },
  { title: t('crawler.category'), key: 'category_name' },
  { title: t('crawler.status'), key: 'status' },
  { title: t('crawler.startedAt'), key: 'scheduled_at' },
  { title: t('crawler.duration'), key: 'duration' },
  { title: t('crawler.progress'), key: 'progress' },
  { title: t('common.actions'), key: 'actions', sortable: false },
]

const filteredJobs = computed(() => {
  if (!statusFilter.value) return jobs.value
  return jobs.value.filter(j => j.status === statusFilter.value)
})

const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    COMPLETED: 'success',
    RUNNING: 'info',
    PENDING: 'warning',
    FAILED: 'error',
    CANCELLED: 'grey',
  }
  return colors[status] || 'grey'
}

const formatDate = (dateStr: string) => {
  return format(new Date(dateStr), 'dd.MM.yyyy HH:mm', { locale: de })
}

const formatDuration = (seconds: number) => {
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`
  return `${Math.round(seconds / 3600)}h ${Math.round((seconds % 3600) / 60)}m`
}

const formatLogTime = (timestamp: string) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

const loadData = async () => {
  loading.value = true
  try {
    const [statusRes, statsRes, jobsRes, runningRes, aiTasksRes] = await Promise.all([
      adminApi.getCrawlerStatus(),
      adminApi.getCrawlerStats(),
      adminApi.getCrawlerJobs({ per_page: 100 }),
      adminApi.getRunningJobs(),
      adminApi.getRunningAiTasks(),
    ])
    status.value = {
      running_jobs: statusRes.data.running_jobs ?? 0,
      pending_jobs: statusRes.data.pending_jobs ?? 0,
      worker_count: statusRes.data.worker_count ?? 0,
      active_tasks: statusRes.data.active_tasks ?? 0,
      running_ai_tasks: aiTasksRes.data.running_count ?? 0,
    }
    stats.value = statsRes.data
    jobs.value = jobsRes.data.items
    runningJobs.value = runningRes.data.jobs || []
    runningAiTasks.value = aiTasksRes.data.tasks || []

    // Start log refresh if there are running jobs
    if (runningJobs.value.length > 0 && !logRefreshInterval) {
      logRefreshInterval = window.setInterval(refreshRunningJobLogs, 3000)
    } else if (runningJobs.value.length === 0 && logRefreshInterval) {
      clearInterval(logRefreshInterval)
      logRefreshInterval = null
      jobLogs.value = {}
    }
  } finally {
    loading.value = false
    initialLoad.value = false
  }
}

const loadJobLog = async (jobId: string) => {
  try {
    const response = await adminApi.getJobLog(jobId)
    jobLogs.value[jobId] = response.data
  } catch (error) {
    console.error('Failed to load job log:', error)
  }
}

const refreshRunningJobLogs = async () => {
  // Refresh logs for all running jobs
  for (const rj of runningJobs.value) {
    try {
      const response = await adminApi.getJobLog(rj.id)
      jobLogs.value[rj.id] = response.data
    } catch (error) {
      // Ignore errors during refresh
    }
  }
  // Also refresh running jobs list
  try {
    const runningRes = await adminApi.getRunningJobs()
    runningJobs.value = runningRes.data.jobs || []
  } catch (error) {
    // Ignore
  }
}

const cancelJob = async (job: any) => {
  try {
    await adminApi.cancelJob(job.id)
    showSuccess(t('crawler.jobCancelling'))
    loadData()
  } catch (error: any) {
    showError(error.response?.data?.error || t('crawler.cancelJobError'))
  }
}

const cancelAiTask = async (task: any) => {
  try {
    await adminApi.cancelAiTask(task.id)
    showSuccess(t('crawler.aiTaskCancelling'))
    loadData()
  } catch (error: any) {
    showError(error.response?.data?.error || t('crawler.cancelAiTaskError'))
  }
}

const stopAllCrawlers = async () => {
  stoppingAll.value = true
  try {
    let cancelledCount = 0
    // Cancel all running jobs
    for (const job of runningJobs.value) {
      try {
        await adminApi.cancelJob(job.id)
        cancelledCount++
      } catch (e) {
        // Continue with other jobs
      }
    }
    // Also cancel all pending jobs from the jobs list
    for (const job of jobs.value.filter(j => j.status === 'PENDING' || j.status === 'RUNNING')) {
      try {
        await adminApi.cancelJob(job.id)
        cancelledCount++
      } catch (e) {
        // Continue with other jobs
      }
    }
    // Cancel all running AI tasks
    for (const task of runningAiTasks.value) {
      try {
        await adminApi.cancelAiTask(task.id)
      } catch (e) {
        // Continue
      }
    }
    showSuccess(t('crawler.jobsStopped', { count: cancelledCount }))
    await loadData()
  } catch (error: any) {
    showError(t('crawler.stopError'))
  } finally {
    stoppingAll.value = false
  }
}

const showJobDetails = async (job: any) => {
  const response = await adminApi.getCrawlerJob(job.id)
  selectedJob.value = response.data
  detailsDialog.value = true
}

onMounted(() => {
  loadData()
  // Auto-refresh every 5 seconds
  refreshInterval = window.setInterval(loadData, 5000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
  if (logRefreshInterval) {
    clearInterval(logRefreshInterval)
  }
})
</script>
