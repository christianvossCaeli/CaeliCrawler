/**
 * Tests for useSmartQueryAttachments composable
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useSmartQueryAttachments } from './useSmartQueryAttachments'
import { assistantApi } from '@/services/api'

// Mock the api module
vi.mock('@/services/api', () => ({
  assistantApi: {
    uploadAttachment: vi.fn(),
    deleteAttachment: vi.fn(),
  },
}))

// Helper to create mock Axios response
function mockAxiosResponse<T>(data: T) {
  return {
    data,
    status: 200,
    statusText: 'OK',
    headers: {},
    config: {} as never,
  }
}

// Mock useI18n
vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string, fallback?: string) => fallback || key,
  }),
}))

describe('useSmartQueryAttachments', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('should initialize with empty attachments', () => {
      const { pendingAttachments } = useSmartQueryAttachments()
      expect(pendingAttachments.value).toEqual([])
    })

    it('should initialize with isUploading false', () => {
      const { isUploading } = useSmartQueryAttachments()
      expect(isUploading.value).toBe(false)
    })

    it('should initialize with no error', () => {
      const { error } = useSmartQueryAttachments()
      expect(error.value).toBeNull()
    })
  })

  describe('uploadAttachment', () => {
    it('should reject unsupported file types', async () => {
      const { uploadAttachment, error } = useSmartQueryAttachments()

      const file = new File(['test'], 'test.exe', { type: 'application/x-msdownload' })
      const result = await uploadAttachment(file)

      expect(result).toBe(false)
      expect(error.value).toBeTruthy()
    })

    it('should reject files that are too large', async () => {
      const { uploadAttachment, error } = useSmartQueryAttachments()

      // Create a file larger than 10MB
      const largeContent = new Uint8Array(11 * 1024 * 1024)
      const file = new File([largeContent], 'large.png', { type: 'image/png' })

      const result = await uploadAttachment(file)

      expect(result).toBe(false)
      expect(error.value).toBeTruthy()
    })

    it('should accept valid image files', async () => {
      vi.mocked(assistantApi.uploadAttachment).mockResolvedValue(
        mockAxiosResponse({
          attachment: {
            attachment_id: 'test-id',
            filename: 'test.png',
            content_type: 'image/png',
            size: 1000,
          },
        })
      )

      const { uploadAttachment, pendingAttachments } = useSmartQueryAttachments()

      const file = new File(['test'], 'test.png', { type: 'image/png' })
      const result = await uploadAttachment(file)

      expect(result).toBe(true)
      expect(pendingAttachments.value).toHaveLength(1)
      expect(pendingAttachments.value[0].id).toBe('test-id')
    })

    it('should accept PDF files', async () => {
      vi.mocked(assistantApi.uploadAttachment).mockResolvedValue(
        mockAxiosResponse({
          attachment: {
            attachment_id: 'pdf-id',
            filename: 'test.pdf',
            content_type: 'application/pdf',
            size: 5000,
          },
        })
      )

      const { uploadAttachment, pendingAttachments } = useSmartQueryAttachments()

      const file = new File(['test'], 'test.pdf', { type: 'application/pdf' })
      const result = await uploadAttachment(file)

      expect(result).toBe(true)
      expect(pendingAttachments.value).toHaveLength(1)
    })

    it('should set isUploading during upload', async () => {
      let resolveUpload: (value: ReturnType<typeof mockAxiosResponse>) => void
      const uploadPromise = new Promise<ReturnType<typeof mockAxiosResponse>>((resolve) => {
        resolveUpload = resolve
      })
      vi.mocked(assistantApi.uploadAttachment).mockReturnValue(uploadPromise)

      const { uploadAttachment, isUploading } = useSmartQueryAttachments()

      const file = new File(['test'], 'test.png', { type: 'image/png' })
      const uploadTask = uploadAttachment(file)

      expect(isUploading.value).toBe(true)

      resolveUpload!(
        mockAxiosResponse({
          attachment: {
            attachment_id: 'test-id',
            filename: 'test.png',
            content_type: 'image/png',
            size: 1000,
          },
        })
      )

      await uploadTask
      expect(isUploading.value).toBe(false)
    })

    it('should handle upload errors', async () => {
      vi.mocked(assistantApi.uploadAttachment).mockRejectedValue(new Error('Upload failed'))

      const { uploadAttachment, error, pendingAttachments } = useSmartQueryAttachments()

      const file = new File(['test'], 'test.png', { type: 'image/png' })
      const result = await uploadAttachment(file)

      expect(result).toBe(false)
      expect(error.value).toBeTruthy()
      expect(pendingAttachments.value).toHaveLength(0)
    })
  })

  describe('removeAttachment', () => {
    it('should remove attachment from pending list', async () => {
      vi.mocked(assistantApi.uploadAttachment).mockResolvedValue(
        mockAxiosResponse({
          attachment: {
            attachment_id: 'test-id',
            filename: 'test.png',
            content_type: 'image/png',
            size: 1000,
          },
        })
      )
      vi.mocked(assistantApi.deleteAttachment).mockResolvedValue(mockAxiosResponse({}))

      const { uploadAttachment, removeAttachment, pendingAttachments } = useSmartQueryAttachments()

      const file = new File(['test'], 'test.png', { type: 'image/png' })
      await uploadAttachment(file)

      expect(pendingAttachments.value).toHaveLength(1)

      await removeAttachment('test-id')

      expect(pendingAttachments.value).toHaveLength(0)
    })

    it('should handle delete errors gracefully', async () => {
      vi.mocked(assistantApi.uploadAttachment).mockResolvedValue(
        mockAxiosResponse({
          attachment: {
            attachment_id: 'test-id',
            filename: 'test.png',
            content_type: 'image/png',
            size: 1000,
          },
        })
      )
      vi.mocked(assistantApi.deleteAttachment).mockRejectedValue(new Error('Delete failed'))

      const { uploadAttachment, removeAttachment, pendingAttachments } = useSmartQueryAttachments()

      const file = new File(['test'], 'test.png', { type: 'image/png' })
      await uploadAttachment(file)

      // Should not throw
      await removeAttachment('test-id')

      // Should still remove from local list
      expect(pendingAttachments.value).toHaveLength(0)
    })
  })

  describe('clearAttachments', () => {
    it('should clear all attachments', async () => {
      vi.mocked(assistantApi.uploadAttachment).mockResolvedValue(
        mockAxiosResponse({
          attachment: {
            attachment_id: 'test-id',
            filename: 'test.png',
            content_type: 'image/png',
            size: 1000,
          },
        })
      )
      vi.mocked(assistantApi.deleteAttachment).mockResolvedValue(mockAxiosResponse({}))

      const { uploadAttachment, clearAttachments, pendingAttachments } = useSmartQueryAttachments()

      const file = new File(['test'], 'test.png', { type: 'image/png' })
      await uploadAttachment(file)

      expect(pendingAttachments.value).toHaveLength(1)

      await clearAttachments()

      expect(pendingAttachments.value).toHaveLength(0)
    })
  })

  describe('helper methods', () => {
    it('getAttachmentIds should return all IDs', async () => {
      vi.mocked(assistantApi.uploadAttachment)
        .mockResolvedValueOnce(
          mockAxiosResponse({
            attachment: {
              attachment_id: 'id-1',
              filename: 'test1.png',
              content_type: 'image/png',
              size: 1000,
            },
          })
        )
        .mockResolvedValueOnce(
          mockAxiosResponse({
            attachment: {
              attachment_id: 'id-2',
              filename: 'test2.png',
              content_type: 'image/png',
              size: 1000,
            },
          })
        )

      const { uploadAttachment, getAttachmentIds } = useSmartQueryAttachments()

      await uploadAttachment(new File(['test'], 'test1.png', { type: 'image/png' }))
      await uploadAttachment(new File(['test'], 'test2.png', { type: 'image/png' }))

      const ids = getAttachmentIds()
      expect(ids).toEqual(['id-1', 'id-2'])
    })

    it('hasAttachments should return correct boolean', async () => {
      vi.mocked(assistantApi.uploadAttachment).mockResolvedValue(
        mockAxiosResponse({
          attachment: {
            attachment_id: 'test-id',
            filename: 'test.png',
            content_type: 'image/png',
            size: 1000,
          },
        })
      )

      const { uploadAttachment, hasAttachments } = useSmartQueryAttachments()

      expect(hasAttachments()).toBe(false)

      await uploadAttachment(new File(['test'], 'test.png', { type: 'image/png' }))

      expect(hasAttachments()).toBe(true)
    })

    it('clearError should clear error state', async () => {
      const { uploadAttachment, error, clearError } = useSmartQueryAttachments()

      const file = new File(['test'], 'test.exe', { type: 'application/x-msdownload' })
      await uploadAttachment(file)

      expect(error.value).toBeTruthy()

      clearError()

      expect(error.value).toBeNull()
    })
  })
})
