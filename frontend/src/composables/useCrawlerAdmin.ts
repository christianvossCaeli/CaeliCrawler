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
import { getErrorMessage } from '@/utils/errorMessage'
import { getStatusColor } from '@/composables/useStatusColors'
import { onCrawlerEvent } from '@/composables/useCrawlerEvents'
import type { JobLog, JobLogEntry } from '@/types/admin'

// ============================================================================
// Types
// ============================================================================

// Re-export for backwards compatibility
export type { JobLog, JobLogEntry }

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

  // Bulk selection state
  const selectedJobIds = ref<Set<string>>(new Set())
  const bulkActionLoading = ref(false)

  let refreshInterval: number | null = null
  let logRefreshInterval: number | null = null
  let eventSource: EventSource | null = null
  let unsubscribeCrawlerEvents: (() => void) | null = null
  // SSE disabled - causes flickering when connection fails partially
  const useSSE = ref(false)

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
    { title: '', key: 'select', sortable: false, width: '50px' },
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

  // Jobs that can be selected for bulk actions (failed, cancelled, completed)
  const selectableJobs = computed(() => {
    return filteredJobs.value.filter(j =>
      j.status === 'FAILED' || j.status === 'CANCELLED' || j.status === 'COMPLETED'
    )
  })

  // Jobs that can be retried (failed or cancelled)
  const retryableSelectedJobs = computed(() => {
    return Array.from(selectedJobIds.value)
      .map(id => jobs.value.find(j => j.id === id))
      .filter((j): j is CrawlerJob => !!j && (j.status === 'FAILED' || j.status === 'CANCELLED'))
  })

  // Jobs that can be deleted (failed, cancelled, or completed)
  const deletableSelectedJobs = computed(() => {
    return Array.from(selectedJobIds.value)
      .map(id => jobs.value.find(j => j.id === id))
      .filter((j): j is CrawlerJob =>
        !!j && (j.status === 'FAILED' || j.status === 'CANCELLED' || j.status === 'COMPLETED')
      )
  })

  // Check if all selectable jobs in current filter are selected
  const allSelectableSelected = computed(() => {
    if (selectableJobs.value.length === 0) return false
    return selectableJobs.value.every(j => selectedJobIds.value.has(j.id))
  })

  // Check if some but not all are selected (indeterminate state)
  const someSelected = computed(() => {
    if (selectedJobIds.value.size === 0) return false
    return !allSelectableSelected.value
  })

  const selectedCount = computed(() => selectedJobIds.value.size)

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
    try {
      const response = await adminApi.getCrawlerJob(job.id)
      selectedJob.value = response.data
      detailsDialog.value = true
    } catch (error) {
      logger.error('Failed to load job details:', error)
      showError(getErrorMessage(error) || t('common.error'))
    }
  }

  // ============================================================================
  // Bulk Selection & Actions
  // ============================================================================

  function toggleJobSelection(jobId: string) {
    const newSet = new Set(selectedJobIds.value)
    if (newSet.has(jobId)) {
      newSet.delete(jobId)
    } else {
      newSet.add(jobId)
    }
    selectedJobIds.value = newSet
  }

  function toggleSelectAll() {
    if (allSelectableSelected.value) {
      // Deselect all selectable jobs in current filter
      const newSet = new Set(selectedJobIds.value)
      selectableJobs.value.forEach(j => newSet.delete(j.id))
      selectedJobIds.value = newSet
    } else {
      // Select all selectable jobs in current filter
      const newSet = new Set(selectedJobIds.value)
      selectableJobs.value.forEach(j => newSet.add(j.id))
      selectedJobIds.value = newSet
    }
  }

  function clearSelection() {
    selectedJobIds.value = new Set()
  }

  function isJobSelected(jobId: string): boolean {
    return selectedJobIds.value.has(jobId)
  }

  async function bulkRetryJobs() {
    const jobsToRetry = retryableSelectedJobs.value
    if (jobsToRetry.length === 0) return

    showConfirm(
      t('crawler.bulkRetryTitle'),
      t('crawler.bulkRetryMessage', { count: jobsToRetry.length }),
      async () => {
        bulkActionLoading.value = true

        // Execute all retries in parallel
        const results = await Promise.allSettled(
          jobsToRetry.map(job => adminApi.retryJob(job.id))
        )

        const successCount = results.filter(r => r.status === 'fulfilled').length
        const errorCount = results.filter(r => r.status === 'rejected').length

        // Remove successfully retried jobs from selection
        const successfulJobIds = jobsToRetry
          .filter((_, index) => results[index].status === 'fulfilled')
          .map(job => job.id)

        const newSelection = new Set(selectedJobIds.value)
        successfulJobIds.forEach(id => newSelection.delete(id))
        selectedJobIds.value = newSelection

        if (successCount > 0) {
          showSuccess(t('crawler.bulkRetrySuccess', { count: successCount }))
        }
        if (errorCount > 0) {
          showError(t('crawler.bulkRetryPartialError', { count: errorCount }))
        }

        bulkActionLoading.value = false
        await loadData()
      }
    )
  }

  async function bulkDeleteJobs() {
    const jobsToDelete = deletableSelectedJobs.value
    if (jobsToDelete.length === 0) return

    showConfirm(
      t('crawler.bulkDeleteTitle'),
      t('crawler.bulkDeleteMessage', { count: jobsToDelete.length }),
      async () => {
        bulkActionLoading.value = true

        // Execute all deletes in parallel
        const results = await Promise.allSettled(
          jobsToDelete.map(job => adminApi.deleteJob(job.id))
        )

        const successCount = results.filter(r => r.status === 'fulfilled').length
        const errorCount = results.filter(r => r.status === 'rejected').length

        // Remove successfully deleted jobs from selection
        const successfulJobIds = jobsToDelete
          .filter((_, index) => results[index].status === 'fulfilled')
          .map(job => job.id)

        const newSelection = new Set(selectedJobIds.value)
        successfulJobIds.forEach(id => newSelection.delete(id))
        selectedJobIds.value = newSelection

        if (successCount > 0) {
          showSuccess(t('crawler.bulkDeleteSuccess', { count: successCount }))
        }
        if (errorCount > 0) {
          showError(t('crawler.bulkDeletePartialError', { count: errorCount }))
        }

        bulkActionLoading.value = false
        await loadData()
      }
    )
  }

  async function cleanupFailedJobs() {
    const failedJobs = jobs.value.filter(j => j.status === 'FAILED')
    if (failedJobs.length === 0) {
      showError(t('crawler.noFailedJobsToCleanup'))
      return
    }

    showConfirm(
      t('crawler.cleanupFailedTitle'),
      t('crawler.cleanupFailedMessage', { count: failedJobs.length }),
      async () => {
        bulkActionLoading.value = true

        // Execute all deletes in parallel
        const results = await Promise.allSettled(
          failedJobs.map(job => adminApi.deleteJob(job.id))
        )

        const successCount = results.filter(r => r.status === 'fulfilled').length

        if (successCount > 0) {
          showSuccess(t('crawler.cleanupSuccess', { count: successCount }))
          // Clear selection as deleted jobs are no longer valid
          clearSelection()
        }

        bulkActionLoading.value = false
        await loadData()
      }
    )
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
      // Collect all job IDs to cancel
      const jobsToCancel = new Set<string>()
      runningJobs.value.forEach(job => jobsToCancel.add(job.id))
      jobs.value
        .filter(j => j.status === 'PENDING' || j.status === 'RUNNING')
        .forEach(job => jobsToCancel.add(job.id))

      // Cancel all jobs in parallel
      const jobResults = await Promise.allSettled(
        Array.from(jobsToCancel).map(jobId => adminApi.cancelJob(jobId))
      )
      const cancelledCount = jobResults.filter(r => r.status === 'fulfilled').length

      // Cancel all AI tasks in parallel
      await Promise.allSettled(
        runningAiTasks.value.map(task => adminApi.cancelAiTask(task.id))
      )

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
        source_name: j.source_name || '',
        category_name: j.category_name || '',
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

  // Adaptive polling interval based on running jobs
  const POLL_INTERVAL_ACTIVE = 3000  // 3s when jobs running (faster updates)
  const POLL_INTERVAL_IDLE = 10000   // 10s when idle (quicker detection of new jobs)
  let currentPollInterval = POLL_INTERVAL_IDLE

  function startPolling() {
    if (refreshInterval) return

    const poll = async () => {
      await loadData()

      // Adjust interval based on running jobs
      const newInterval = status.value.running_jobs > 0 ? POLL_INTERVAL_ACTIVE : POLL_INTERVAL_IDLE
      if (newInterval !== currentPollInterval) {
        currentPollInterval = newInterval
        stopPolling()
        refreshInterval = window.setInterval(poll, currentPollInterval)
      }
    }

    currentPollInterval = status.value.running_jobs > 0 ? POLL_INTERVAL_ACTIVE : POLL_INTERVAL_IDLE
    refreshInterval = window.setInterval(poll, currentPollInterval)
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

    // Subscribe to global crawler events (e.g., when crawl started from other views)
    unsubscribeCrawlerEvents = onCrawlerEvent((event) => {
      if (event.type === 'crawl-started') {
        logger.debug('Received crawl-started event, refreshing data')
        // Immediate refresh when a crawl is started
        loadData()
        // Switch to active polling interval
        if (currentPollInterval !== POLL_INTERVAL_ACTIVE) {
          currentPollInterval = POLL_INTERVAL_ACTIVE
          stopPolling()
          startPolling()
        }
      } else if (event.type === 'crawl-completed' || event.type === 'crawl-cancelled') {
        // Refresh on completion/cancellation
        loadData()
      }
    })

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
    if (unsubscribeCrawlerEvents) {
      unsubscribeCrawlerEvents()
      unsubscribeCrawlerEvents = null
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
    selectedJobIds,
    bulkActionLoading,

    // Computed
    headers,
    filteredJobs,
    selectableJobs,
    retryableSelectedJobs,
    deletableSelectedJobs,
    allSelectableSelected,
    someSelected,
    selectedCount,

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

    // Bulk Selection & Actions
    toggleJobSelection,
    toggleSelectAll,
    clearSelection,
    isJobSelected,
    bulkRetryJobs,
    bulkDeleteJobs,
    cleanupFailedJobs,

    // Confirmation
    executeConfirmedAction,

    // Stop All
    stopAllCrawlers,

    // Initialization
    initialize,
    cleanup,
  }
}
