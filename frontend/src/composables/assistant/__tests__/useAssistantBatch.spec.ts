/**
 * Tests for useAssistantBatch composable
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ref } from 'vue'
import { useAssistantBatch } from '../useAssistantBatch'
import type { ConversationMessage } from '../types'

// Mock the API
const mockBatchAction = vi.fn()
const mockGetBatchStatus = vi.fn()
const mockCancelBatch = vi.fn()

vi.mock('@/services/api', () => ({
  assistantApi: {
    batchAction: (...args: unknown[]) => mockBatchAction(...args),
    getBatchStatus: (...args: unknown[]) => mockGetBatchStatus(...args),
    cancelBatch: (...args: unknown[]) => mockCancelBatch(...args),
  },
}))

describe('useAssistantBatch', () => {
  const createOptions = () => ({
    messages: ref<ConversationMessage[]>([]),
    isLoading: ref(false),
    error: ref<string | null>(null),
    saveHistory: vi.fn(),
  })

  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('executeBatchAction', () => {
    it('should execute dry run and show preview', async () => {
      const options = createOptions()
      const { executeBatchAction, activeBatch, batchPreview, isBatchDryRun } = useAssistantBatch(options)

      mockBatchAction.mockResolvedValue({
        data: {
          affected_count: 10,
          message: '10 entities will be updated',
          preview: [
            { entity_id: '1', entity_name: 'Entity 1', entity_type: 'municipality' },
            { entity_id: '2', entity_name: 'Entity 2', entity_type: 'municipality' },
          ],
        },
      })

      const result = await executeBatchAction(
        'add_facet',
        { entity_type: 'municipality' },
        { facet_type: 'pain_point', value: 'Test' },
        true // dry run
      )

      expect(result).toBe(true)
      expect(isBatchDryRun.value).toBe(true)
      expect(activeBatch.value?.status).toBe('pending')
      expect(activeBatch.value?.total).toBe(10)
      expect(batchPreview.value).toHaveLength(2)
    })

    it('should execute actual batch and start polling', async () => {
      const options = createOptions()
      const { executeBatchAction, activeBatch, isBatchDryRun } = useAssistantBatch(options)

      mockBatchAction.mockResolvedValue({
        data: {
          batch_id: 'batch-123',
          affected_count: 5,
          message: 'Batch started',
        },
      })

      const result = await executeBatchAction(
        'add_facet',
        { entity_type: 'municipality' },
        { facet_type: 'pain_point', value: 'Test' },
        false // actual execution
      )

      expect(result).toBe(true)
      expect(isBatchDryRun.value).toBe(false)
      expect(activeBatch.value?.batch_id).toBe('batch-123')
      expect(activeBatch.value?.status).toBe('running')
    })

    it('should handle batch action error', async () => {
      const options = createOptions()
      const { executeBatchAction } = useAssistantBatch(options)

      mockBatchAction.mockRejectedValue({
        response: { data: { detail: 'Batch failed' } },
      })

      const result = await executeBatchAction(
        'add_facet',
        { entity_type: 'municipality' },
        { facet_type: 'pain_point' },
        true
      )

      expect(result).toBe(false)
      expect(options.error.value).toBe('Batch failed')
    })
  })

  describe('confirmBatchAction', () => {
    it('should confirm and execute pending batch', async () => {
      const options = createOptions()
      const { executeBatchAction, confirmBatchAction, isBatchDryRun } = useAssistantBatch(options)

      // First do a dry run
      mockBatchAction.mockResolvedValueOnce({
        data: {
          affected_count: 5,
          message: 'Preview',
          preview: [],
        },
      })

      await executeBatchAction('add_facet', { entity_type: 'test' }, { value: 'test' }, true)
      expect(isBatchDryRun.value).toBe(true)

      // Then confirm
      mockBatchAction.mockResolvedValueOnce({
        data: {
          batch_id: 'batch-456',
          affected_count: 5,
          message: 'Started',
        },
      })

      const result = await confirmBatchAction()
      expect(result).toBe(true)
      expect(isBatchDryRun.value).toBe(false)
    })

    it('should return false if no pending batch', async () => {
      const options = createOptions()
      const { confirmBatchAction } = useAssistantBatch(options)

      const result = await confirmBatchAction()
      expect(result).toBe(false)
    })
  })

  describe('cancelBatchAction', () => {
    it('should cancel running batch', async () => {
      const options = createOptions()
      const { executeBatchAction, cancelBatchAction, activeBatch, batchPreview, cleanup } = useAssistantBatch(options)

      mockBatchAction.mockResolvedValue({
        data: {
          batch_id: 'batch-789',
          affected_count: 10,
          message: 'Running',
        },
      })
      mockCancelBatch.mockResolvedValue({})

      await executeBatchAction('add_facet', {}, {}, false)

      await cancelBatchAction()

      expect(mockCancelBatch).toHaveBeenCalledWith('batch-789')
      expect(activeBatch.value).toBeNull()
      expect(batchPreview.value).toHaveLength(0)

      cleanup()
    })

    it('should reset state when cancelling preview', async () => {
      const options = createOptions()
      const { executeBatchAction, cancelBatchAction, activeBatch, isBatchDryRun } = useAssistantBatch(options)

      mockBatchAction.mockResolvedValue({
        data: {
          affected_count: 5,
          message: 'Preview',
          preview: [],
        },
      })

      await executeBatchAction('add_facet', {}, {}, true)
      expect(isBatchDryRun.value).toBe(true)

      await cancelBatchAction()

      expect(activeBatch.value).toBeNull()
      expect(isBatchDryRun.value).toBe(false)
    })
  })

  describe('closeBatchProgress', () => {
    it('should close batch progress and reset state', async () => {
      const options = createOptions()
      const { executeBatchAction, closeBatchProgress, activeBatch, batchPreview, isBatchDryRun, cleanup } = useAssistantBatch(options)

      mockBatchAction.mockResolvedValue({
        data: {
          batch_id: 'batch-999',
          affected_count: 3,
          message: 'Done',
        },
      })

      await executeBatchAction('add_facet', {}, {}, false)
      expect(activeBatch.value).not.toBeNull()

      closeBatchProgress()

      expect(activeBatch.value).toBeNull()
      expect(batchPreview.value).toHaveLength(0)
      expect(isBatchDryRun.value).toBe(false)

      cleanup()
    })
  })
})
