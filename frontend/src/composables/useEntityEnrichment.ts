import { ref } from 'vue'
import { aiTasksApi, entityDataApi } from '@/services/api'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger('useEntityEnrichment')

export interface EnrichmentTaskStatus {
  status: string
  progress_current?: number
  progress_total?: number
  current_item?: string
  error_message?: string
}

export interface EnrichmentPreviewData {
  new_facets?: any[]
  updates?: any[]
  analysis_summary?: any
}

export function useEntityEnrichment() {
  const enrichmentTaskId = ref<string | null>(null)
  const enrichmentTaskPolling = ref<ReturnType<typeof setInterval> | null>(null)
  const enrichmentTaskStatus = ref<EnrichmentTaskStatus | null>(null)
  const enrichmentPreviewData = ref<EnrichmentPreviewData | null>(null)
  const showEnrichmentReviewDialog = ref(false)
  const showMinimizedTaskSnackbar = ref(false)

  function startEnrichmentTaskPolling(taskId: string) {
    stopEnrichmentTaskPolling()

    enrichmentTaskPolling.value = setInterval(async () => {
      try {
        const response = await aiTasksApi.getStatus(taskId)
        enrichmentTaskStatus.value = response.data

        // Check if task is completed
        if (response.data.status === 'COMPLETED') {
          stopEnrichmentTaskPolling()

          // Fetch the preview data
          try {
            const previewResponse = await entityDataApi.getAnalysisPreview(taskId)
            enrichmentPreviewData.value = previewResponse.data
          } catch (e) {
            logger.error('Failed to fetch preview', e)
          }
        } else if (response.data.status === 'FAILED' || response.data.status === 'CANCELLED') {
          stopEnrichmentTaskPolling()
        }
      } catch (e) {
        logger.error('Failed to poll task status', e)
      }
    }, 2000)
  }

  function stopEnrichmentTaskPolling() {
    if (enrichmentTaskPolling.value) {
      clearInterval(enrichmentTaskPolling.value)
      enrichmentTaskPolling.value = null
    }
  }

  function onEnrichmentReviewClose() {
    stopEnrichmentTaskPolling()
    showMinimizedTaskSnackbar.value = false
    enrichmentTaskId.value = null
    enrichmentTaskStatus.value = null
    enrichmentPreviewData.value = null
  }

  function onEnrichmentReviewMinimize() {
    showEnrichmentReviewDialog.value = false
    // Show minimized snackbar only if task is still running
    if (enrichmentTaskStatus.value?.status === 'RUNNING' || enrichmentTaskStatus.value?.status === 'PENDING') {
      showMinimizedTaskSnackbar.value = true
    }
  }

  function reopenEnrichmentReview() {
    showMinimizedTaskSnackbar.value = false
    showEnrichmentReviewDialog.value = true
  }

  function onEnrichmentStarted(taskId: string) {
    enrichmentTaskId.value = taskId
    enrichmentTaskStatus.value = { status: 'PENDING' }
    enrichmentPreviewData.value = null
    showEnrichmentReviewDialog.value = true
    showMinimizedTaskSnackbar.value = false
    startEnrichmentTaskPolling(taskId)
  }

  function cleanup() {
    stopEnrichmentTaskPolling()
  }

  return {
    enrichmentTaskId,
    enrichmentTaskStatus,
    enrichmentPreviewData,
    showEnrichmentReviewDialog,
    showMinimizedTaskSnackbar,
    startEnrichmentTaskPolling,
    stopEnrichmentTaskPolling,
    onEnrichmentReviewClose,
    onEnrichmentReviewMinimize,
    reopenEnrichmentReview,
    onEnrichmentStarted,
    cleanup,
  }
}
