/**
 * Assistant Batch Operations Composable
 *
 * Manages batch operations for bulk entity updates.
 */

import { ref, type Ref } from 'vue'
import { assistantApi } from '@/services/api'
import { extractErrorMessage } from '@/utils/errorMessage'
import { useLogger } from '@/composables/useLogger'
import type {
  BatchStatus,
  BatchPreviewEntity,
  BatchActionResponse,
  ConversationMessage,
} from './types'

const logger = useLogger('useAssistantBatch')

export interface UseAssistantBatchOptions {
  messages: Ref<ConversationMessage[]>
  isLoading: Ref<boolean>
  error: Ref<string | null>
  saveHistory: () => void
}

export function useAssistantBatch(options: UseAssistantBatchOptions) {
  const { messages, isLoading, error, saveHistory } = options

  // Batch operations state
  const activeBatch = ref<BatchStatus | null>(null)
  const batchPreview = ref<BatchPreviewEntity[]>([])
  const isBatchDryRun = ref(false)
  const pendingBatchRequest = ref<{
    action_type: string
    target_filter: Record<string, unknown>
    action_data: Record<string, unknown>
  } | null>(null)
  let batchPollInterval: ReturnType<typeof setInterval> | null = null

  // Get completion message for batch operation
  function getBatchCompletionMessage(status: BatchStatus): string {
    if (status.status === 'completed') {
      if (status.errors?.length > 0) {
        return `Batch-Operation abgeschlossen: ${status.processed} von ${status.total} verarbeitet. ${status.errors.length} Fehler aufgetreten.`
      }
      return `Batch-Operation erfolgreich abgeschlossen: ${status.processed} Entities verarbeitet.`
    } else if (status.status === 'cancelled') {
      return `Batch-Operation abgebrochen. ${status.processed} von ${status.total} wurden bereits verarbeitet.`
    } else {
      return `Batch-Operation fehlgeschlagen: ${status.message || 'Unbekannter Fehler'}`
    }
  }

  // Start polling for batch status
  function startBatchPolling(batchId: string) {
    stopBatchPolling() // Clear any existing interval

    batchPollInterval = setInterval(async () => {
      try {
        const response = await assistantApi.getBatchStatus(batchId)
        const status = response.data

        activeBatch.value = {
          batch_id: batchId,
          status: status.status,
          processed: status.processed,
          total: status.total,
          errors: status.errors || [],
          message: status.message || '',
        }

        // Stop polling when complete
        if (['completed', 'failed', 'cancelled'].includes(status.status)) {
          stopBatchPolling()

          // Add completion message to chat
          const completionMessage: ConversationMessage = {
            role: 'assistant',
            content: getBatchCompletionMessage(status),
            timestamp: new Date(),
            response_type: status.status === 'completed' ? 'success' : 'error',
          }
          messages.value.push(completionMessage)
          saveHistory()
        }
      } catch (e) {
        logger.error('Failed to poll batch status:', e)
        stopBatchPolling()
      }
    }, 2000) // Poll every 2 seconds
  }

  // Stop polling for batch status
  function stopBatchPolling() {
    if (batchPollInterval) {
      clearInterval(batchPollInterval)
      batchPollInterval = null
    }
  }

  // Execute a batch action (dry run first)
  async function executeBatchAction(
    actionType: string,
    targetFilter: Record<string, unknown>,
    actionData: Record<string, unknown>,
    dryRun: boolean = true
  ): Promise<boolean> {
    isLoading.value = true
    error.value = null

    try {
      const response = await assistantApi.batchAction({
        action_type: actionType,
        target_filter: targetFilter,
        action_data: actionData,
        dry_run: dryRun,
      })

      const data = response.data as BatchActionResponse

      if (dryRun) {
        // Show preview
        activeBatch.value = {
          batch_id: '',
          status: 'pending',
          processed: 0,
          total: data.affected_count,
          errors: [],
          message: data.message || '',
        }
        batchPreview.value = data.preview || []
        isBatchDryRun.value = true
        pendingBatchRequest.value = { action_type: actionType, target_filter: targetFilter, action_data: actionData }
      } else {
        // Start actual batch operation
        activeBatch.value = {
          batch_id: data.batch_id || '',
          status: 'running',
          processed: 0,
          total: data.affected_count,
          errors: [],
          message: data.message || '',
        }
        isBatchDryRun.value = false
        batchPreview.value = data.preview || []

        // Start polling for status
        if (data.batch_id) {
          startBatchPolling(data.batch_id)
        }
      }

      return true
    } catch (e: unknown) {
      error.value = extractErrorMessage(e)
      return false
    } finally {
      isLoading.value = false
    }
  }

  // Confirm and execute a pending batch action
  async function confirmBatchAction(): Promise<boolean> {
    if (!pendingBatchRequest.value) return false

    const { action_type, target_filter, action_data } = pendingBatchRequest.value
    pendingBatchRequest.value = null
    isBatchDryRun.value = false

    return await executeBatchAction(action_type, target_filter, action_data, false)
  }

  // Cancel a pending or running batch action
  async function cancelBatchAction(): Promise<void> {
    if (activeBatch.value?.batch_id && activeBatch.value.status === 'running') {
      try {
        await assistantApi.cancelBatch(activeBatch.value.batch_id)
      } catch (e) {
        logger.error('Failed to cancel batch:', e)
      }
    }

    stopBatchPolling()
    activeBatch.value = null
    batchPreview.value = []
    isBatchDryRun.value = false
    pendingBatchRequest.value = null
  }

  // Close batch progress display
  function closeBatchProgress() {
    stopBatchPolling()
    activeBatch.value = null
    batchPreview.value = []
    isBatchDryRun.value = false
    pendingBatchRequest.value = null
  }

  // Cleanup function for component unmount
  function cleanup() {
    stopBatchPolling()
  }

  return {
    // State
    activeBatch,
    batchPreview,
    isBatchDryRun,

    // Methods
    executeBatchAction,
    confirmBatchAction,
    cancelBatchAction,
    closeBatchProgress,
    cleanup,
  }
}
