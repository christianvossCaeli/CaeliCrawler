/**
 * Crawler Admin Composable
 *
 * Manages state and logic for the Crawler admin view.
 * Handles real-time updates via SSE, job management, and AI task monitoring.
 */
import { ref, computed, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { adminApi } from '@/services/api'
import { useDateFormatter } from '@/composables/useDateFormatter'
import { useSnackbar } from '@/composables/useSnackbar'
import { useCrawlPresetsStore } from '@/stores/crawlPresets'
import { useAuthStore } from '@/stores/auth'
import { useLogger } from '@/composables/useLogger'
import { getErrorMessage } from '@/composables/useApiErrorHandler'
import { getStatusColor } from '@/composables/useStatusColors'

// ============================================================================
// Types
// ============================================================================

export interface LogEntry {
  status: string
  url: string
  timestamp: string
}

export interface JobLog {
  current_url: string
  log_entries: LogEntry[]
}

export interface CrawlerJobError {
  error: string
  timestamp?: string
  url?: string
}

export interface CrawlerJob {
  id: string
  source_name?: string
  category_name?: string
  status: string
  scheduled_at?: string
  started_at?: string
  completed_at?: string
  pages_crawled?: number
  documents_found?: number
  documents_processed?: number
  documents_new?: number
  duration?: number
  duration_seconds?: number
  error_log?: CrawlerJobError[] | string[]
  current_url?: string
  base_url?: string
  error_count?: number
}

export interface AiTask {
  id: string
  task_type?: string
  name?: string
  status: string
  started_at?: string
  progress?: number
  current_item?: string
  progress_current?: number
  progress_total?: number
  progress_percent?: number
}

export interface CrawlerStatus {
  running_jobs: number
  pending_jobs: number
  worker_count: number
  active_tasks: number
  running_ai_tasks: number
}

export interface CrawlerStats {
  total_jobs: number
  total_documents: number
  completed_jobs: number
  failed_jobs: number
}

// ============================================================================
// Composable
// ============================================================================

export function useCrawlerAdmin() {
  const logger = useLogger('CrawlerAdmin')
  const { t, locale } = useI18n()
  const { formatDate: formatLocaleDate } = useDateFormatter()
  const route = useRoute()
  const { showSuccess, showError } = useSnackbar()
  const presetsStore = useCrawlPresetsStore()
  const authStore = useAuthStore()

  // ============================================================================
  // State
  // ============================================================================

  const loading = ref(true)
  const presetsDrawer = ref(false)
  const initialLoad = ref(true)
  const stoppingAll = ref(false)
  const jobs = ref<CrawlerJob[]>([])
  const runningJobs = ref<CrawlerJob[]>([])
  const runningAiTasks = ref<AiTask[]>([])
  const jobLogs = ref<Record<string, JobLog>>({})
  const statusFilter = ref('')
  const detailsDialog = ref(false)
  const confirmDialog = ref(false)
  const confirmAction = ref<(() => Promise<void>) | null>(null)
  const confirmMessage = ref('')
  const confirmTitle = ref('')
  const selectedJob = ref<CrawlerJob | null>(null)

  let refreshInterval: number | null = null
  let logRefreshInterval: number | null = null
  let eventSource: EventSource | null = null
  const useSSE = ref(true)

  const status = ref<CrawlerStatus>({
    running_jobs: 0,
    pending_jobs: 0,
    worker_count: 0,
    active_tasks: 0,
    running_ai_tasks: 0,
  })

  const stats = ref<CrawlerStats>({
    total_jobs: 0,
    total_documents: 0,
    completed_jobs: 0,
    failed_jobs: 0,
  })

  // ============================================================================
  // Computed
  // ============================================================================

  const headers = computed(() => [
    { title: t('crawler.source'), key: 'source_name', sortable: true },
    { title: t('crawler.category'), key: 'category_name', sortable: true },
    { title: t('crawler.status'), key: 'status', sortable: true },
    { title: t('crawler.startedAt'), key: 'scheduled_at', sortable: true },
    { title: t('crawler.duration'), key: 'duration', sortable: true },
    { title: t('crawler.progress'), key: 'progress', sortable: false },
    { title: t('common.actions'), key: 'actions', sortable: false },
  ])

  const filteredJobs = computed(() => {
    if (!statusFilter.value) return jobs.value
    return jobs.value.filter(j => j.status === statusFilter.value)
  })

  // ============================================================================
  // Helper Functions
  // ============================================================================

  function formatDate(dateStr: string): string {
    return formatLocaleDate(dateStr, 'dd.MM.yyyy HH:mm')
  }

  function formatDuration(seconds: number): string {
    if (seconds < 60) return `${Math.round(seconds)}s`
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`
    return `${Math.round(seconds / 3600)}h ${Math.round((seconds % 3600) / 60)}m`
  }

  function formatLogTime(timestamp: string): string {
    if (!timestamp) return ''
    const date = new Date(timestamp)
    return date.toLocaleTimeString(locale.value, { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }

  // ============================================================================
  // Data Loading
  // ============================================================================

  async function loadData() {
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

  async function loadJobLog(jobId: string) {
    try {
      const response = await adminApi.getJobLog(jobId)
      jobLogs.value[jobId] = response.data
    } catch (error) {
      logger.error('Failed to load job log:', error)
    }
  }

  async function refreshRunningJobLogs() {
    for (const rj of runningJobs.value) {
      try {
        const response = await adminApi.getJobLog(rj.id)
        jobLogs.value[rj.id] = response.data
      } catch {
        // Ignore errors during refresh
      }
    }
    try {
      const runningRes = await adminApi.getRunningJobs()
      runningJobs.value = runningRes.data.jobs || []
    } catch {
      // Ignore
    }
  }

  // ============================================================================
  // Job Actions
  // ============================================================================

  async function cancelJob(job: CrawlerJob) {
    try {
      await adminApi.cancelJob(job.id)
      showSuccess(t('crawler.jobCancelling'))
      loadData()
    } catch (error) {
      showError(getErrorMessage(error) || t('crawler.cancelJobError'))
    }
  }

  async function retryJob(job: CrawlerJob) {
    try {
      await adminApi.retryJob(job.id)
      showSuccess(t('crawler.jobRetryStarted'))
      loadData()
    } catch (error) {
      showError(getErrorMessage(error) || t('crawler.retryJobError'))
    }
  }

  async function cancelAiTask(task: AiTask) {
    try {
      await adminApi.cancelAiTask(task.id)
      showSuccess(t('crawler.aiTaskCancelling'))
      loadData()
    } catch (error) {
      showError(getErrorMessage(error) || t('crawler.cancelAiTaskError'))
    }
  }

  async function showJobDetails(job: CrawlerJob) {
    const response = await adminApi.getCrawlerJob(job.id)
    selectedJob.value = response.data
    detailsDialog.value = true
  }

  // ============================================================================
  // Confirmation Dialog
  // ============================================================================

  function showConfirm(title: string, message: string, action: () => Promise<void>) {
    confirmTitle.value = title
    confirmMessage.value = message
    confirmAction.value = action
    confirmDialog.value = true
  }

  async function executeConfirmedAction() {
    confirmDialog.value = false
    if (confirmAction.value) {
      await confirmAction.value()
    }
  }

  // ============================================================================
  // Stop All Crawlers
  // ============================================================================

  function stopAllCrawlers() {
    const totalJobs = status.value.running_jobs + status.value.pending_jobs
    showConfirm(
      t('crawler.confirmStopAllTitle'),
      t('crawler.confirmStopAllMessage', { count: totalJobs }),
      doStopAllCrawlers
    )
  }

  async function doStopAllCrawlers() {
    stoppingAll.value = true
    try {
      let cancelledCount = 0
      const jobsToCancel = new Set<string>()

      for (const job of runningJobs.value) {
        jobsToCancel.add(job.id)
      }

      for (const job of jobs.value.filter(j => j.status === 'PENDING' || j.status === 'RUNNING')) {
        jobsToCancel.add(job.id)
      }

      for (const jobId of jobsToCancel) {
        try {
          await adminApi.cancelJob(jobId)
          cancelledCount++
        } catch {
          // Continue with other jobs
        }
      }

      for (const task of runningAiTasks.value) {
        try {
          await adminApi.cancelAiTask(task.id)
        } catch {
          // Continue
        }
      }

      showSuccess(t('crawler.jobsStopped', { count: cancelledCount }))
      await loadData()
    } catch {
      showError(t('crawler.stopError'))
    } finally {
      stoppingAll.value = false
    }
  }

  // ============================================================================
  // SSE Connection
  // ============================================================================

  async function connectSSE() {
    if (eventSource) {
      eventSource.close()
    }

    const baseUrl = import.meta.env.VITE_API_URL || ''

    let ticketParam = ''
    try {
      const response = await fetch(`${baseUrl}/api/auth/sse-ticket`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authStore.token}`,
          'Content-Type': 'application/json',
        },
      })
      if (response.ok) {
        const data = await response.json()
        ticketParam = `ticket=${encodeURIComponent(data.ticket)}`
      } else {
        logger.warn('Failed to get SSE ticket, SSE may not work')
      }
    } catch (error) {
      logger.warn('Error getting SSE ticket:', error)
    }

    const url = ticketParam
      ? `${baseUrl}/api/admin/crawler/events?${ticketParam}`
      : `${baseUrl}/api/admin/crawler/events`
    eventSource = new EventSource(url)

    eventSource.addEventListener('status', (event) => {
      const data = JSON.parse(event.data)
      status.value.running_jobs = data.running_jobs ?? 0
      status.value.pending_jobs = data.pending_jobs ?? 0
    })

    eventSource.addEventListener('jobs', (event) => {
      const data = JSON.parse(event.data)
      runningJobs.value = data.map((j: CrawlerJob) => ({
        ...j,
        id: j.id,
        source_name: j.source_name || 'Unknown',
        category_name: j.category_name || '-',
        pages_crawled: j.pages_crawled || 0,
        documents_found: j.documents_found || 0,
      }))
    })

    eventSource.addEventListener('error', () => {
      logger.warn('SSE connection failed, falling back to polling')
      useSSE.value = false
      disconnectSSE()
      startPolling()
    })
  }

  function disconnectSSE() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
  }

  function startPolling() {
    if (!refreshInterval) {
      refreshInterval = window.setInterval(loadData, 5000)
    }
  }

  function stopPolling() {
    if (refreshInterval) {
      clearInterval(refreshInterval)
      refreshInterval = null
    }
  }

  // ============================================================================
  // Initialization & Cleanup
  // ============================================================================

  async function initialize() {
    // Check for status filter from dashboard widget
    if (route.query.status) {
      const statusParam = route.query.status as string
      const validStatuses = ['RUNNING', 'COMPLETED', 'FAILED', 'PENDING']
      if (validStatuses.includes(statusParam)) {
        statusFilter.value = statusParam
      }
    }

    await loadData()

    // Check for job_id query parameter to auto-open job details
    if (route.query.job_id) {
      const jobId = route.query.job_id as string
      const job = jobs.value.find((j) => j.id === jobId)
      if (job) {
        selectedJob.value = job
        detailsDialog.value = true
      } else {
        try {
          const response = await adminApi.getCrawlerJob(jobId)
          selectedJob.value = response.data
          detailsDialog.value = true
        } catch (e) {
          logger.warn('Could not load job details:', e)
        }
      }
    }

    // Try SSE first, fallback to polling
    if (useSSE.value) {
      try {
        connectSSE()
      } catch {
        logger.warn('SSE not available, using polling')
        startPolling()
      }
    } else {
      startPolling()
    }
  }

  function cleanup() {
    disconnectSSE()
    stopPolling()
    if (logRefreshInterval) {
      clearInterval(logRefreshInterval)
    }
  }

  // Auto-cleanup on unmount
  onUnmounted(() => {
    cleanup()
  })

  // ============================================================================
  // Return
  // ============================================================================

  return {
    // State
    loading,
    presetsDrawer,
    initialLoad,
    stoppingAll,
    jobs,
    runningJobs,
    runningAiTasks,
    jobLogs,
    statusFilter,
    detailsDialog,
    confirmDialog,
    confirmMessage,
    confirmTitle,
    selectedJob,
    status,
    stats,

    // Computed
    headers,
    filteredJobs,

    // Stores
    presetsStore,

    // Helper Functions
    getStatusColor,
    formatDate,
    formatDuration,
    formatLogTime,

    // Data Loading
    loadData,
    loadJobLog,

    // Job Actions
    cancelJob,
    retryJob,
    cancelAiTask,
    showJobDetails,

    // Confirmation
    executeConfirmedAction,

    // Stop All
    stopAllCrawlers,

    // Initialization
    initialize,
    cleanup,
  }
}
