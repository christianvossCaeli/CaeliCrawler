/**
 * Tests for useAssistantAttachments composable
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'
import { useAssistantAttachments } from '../useAssistantAttachments'
import type { ConversationMessage } from '../types'

// Mock the API
const mockUploadAttachment = vi.fn()
const mockDeleteAttachment = vi.fn()
const mockSaveToEntityAttachments = vi.fn()

vi.mock('@/services/api', () => ({
  assistantApi: {
    uploadAttachment: (...args: unknown[]) => mockUploadAttachment(...args),
    deleteAttachment: (...args: unknown[]) => mockDeleteAttachment(...args),
    saveToEntityAttachments: (...args: unknown[]) => mockSaveToEntityAttachments(...args),
  },
}))

describe('useAssistantAttachments', () => {
  const createOptions = () => ({
    messages: ref<ConversationMessage[]>([]),
    error: ref<string | null>(null),
    saveHistory: vi.fn(),
  })

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('uploadAttachment', () => {
    it('should reject unsupported file types', async () => {
      const options = createOptions()
      const { uploadAttachment } = useAssistantAttachments(options)

      const file = new File(['content'], 'test.exe', { type: 'application/x-msdownload' })
      const result = await uploadAttachment(file)

      expect(result).toBe(false)
      expect(options.error.value).toContain('Nicht unterstützter Dateityp')
    })

    it('should reject files larger than 10MB', async () => {
      const options = createOptions()
      const { uploadAttachment } = useAssistantAttachments(options)

      // Create a mock file that reports > 10MB
      const file = new File(['content'], 'test.png', { type: 'image/png' })
      Object.defineProperty(file, 'size', { value: 11 * 1024 * 1024 })

      const result = await uploadAttachment(file)

      expect(result).toBe(false)
      expect(options.error.value).toBe('Datei zu groß (max. 10MB)')
    })

    it('should upload valid image file', async () => {
      const options = createOptions()
      const { uploadAttachment, pendingAttachments } = useAssistantAttachments(options)

      mockUploadAttachment.mockResolvedValue({
        data: {
          attachment: {
            attachment_id: 'test-id',
            filename: 'test.png',
            content_type: 'image/png',
            size: 1024,
          },
        },
      })

      const file = new File(['content'], 'test.png', { type: 'image/png' })
      const result = await uploadAttachment(file)

      expect(result).toBe(true)
      expect(pendingAttachments.value).toHaveLength(1)
      expect(pendingAttachments.value[0].id).toBe('test-id')
    })

    it('should upload PDF file', async () => {
      const options = createOptions()
      const { uploadAttachment, pendingAttachments } = useAssistantAttachments(options)

      mockUploadAttachment.mockResolvedValue({
        data: {
          attachment: {
            attachment_id: 'pdf-id',
            filename: 'document.pdf',
            content_type: 'application/pdf',
            size: 5000,
          },
        },
      })

      const file = new File(['content'], 'document.pdf', { type: 'application/pdf' })
      const result = await uploadAttachment(file)

      expect(result).toBe(true)
      expect(pendingAttachments.value[0].contentType).toBe('application/pdf')
    })

    it('should handle upload error', async () => {
      const options = createOptions()
      const { uploadAttachment } = useAssistantAttachments(options)

      mockUploadAttachment.mockRejectedValue({
        response: { data: { detail: 'Server error' } },
      })

      const file = new File(['content'], 'test.png', { type: 'image/png' })
      const result = await uploadAttachment(file)

      expect(result).toBe(false)
      expect(options.error.value).toBe('Server error')
    })
  })

  describe('removeAttachment', () => {
    it('should remove attachment from pending list', async () => {
      const options = createOptions()
      const { uploadAttachment, removeAttachment, pendingAttachments } = useAssistantAttachments(options)

      mockUploadAttachment.mockResolvedValue({
        data: {
          attachment: {
            attachment_id: 'test-id',
            filename: 'test.png',
            content_type: 'image/png',
            size: 1024,
          },
        },
      })
      mockDeleteAttachment.mockResolvedValue({})

      const file = new File(['content'], 'test.png', { type: 'image/png' })
      await uploadAttachment(file)
      expect(pendingAttachments.value).toHaveLength(1)

      await removeAttachment('test-id')
      expect(pendingAttachments.value).toHaveLength(0)
      expect(mockDeleteAttachment).toHaveBeenCalledWith('test-id')
    })

    it('should handle delete error gracefully', async () => {
      const options = createOptions()
      const { pendingAttachments, removeAttachment } = useAssistantAttachments(options)

      pendingAttachments.value = [{
        id: 'test-id',
        filename: 'test.png',
        contentType: 'image/png',
        size: 1024,
      }]

      mockDeleteAttachment.mockRejectedValue(new Error('Delete failed'))

      await removeAttachment('test-id')
      // Should still remove from list even if API call fails
      expect(pendingAttachments.value).toHaveLength(0)
    })
  })

  describe('clearAttachments', () => {
    it('should clear all pending attachments', async () => {
      const options = createOptions()
      const { pendingAttachments, clearAttachments } = useAssistantAttachments(options)

      pendingAttachments.value = [
        { id: 'id1', filename: 'file1.png', contentType: 'image/png', size: 100 },
        { id: 'id2', filename: 'file2.png', contentType: 'image/png', size: 200 },
      ]

      mockDeleteAttachment.mockResolvedValue({})

      await clearAttachments()

      expect(pendingAttachments.value).toHaveLength(0)
      expect(mockDeleteAttachment).toHaveBeenCalledTimes(2)
    })
  })

  describe('getAttachmentIcon', () => {
    it('should return correct icon for images', () => {
      const options = createOptions()
      const { getAttachmentIcon } = useAssistantAttachments(options)

      expect(getAttachmentIcon('image/png')).toBe('mdi-image')
      expect(getAttachmentIcon('image/jpeg')).toBe('mdi-image')
      expect(getAttachmentIcon('image/gif')).toBe('mdi-image')
    })

    it('should return correct icon for PDF', () => {
      const options = createOptions()
      const { getAttachmentIcon } = useAssistantAttachments(options)

      expect(getAttachmentIcon('application/pdf')).toBe('mdi-file-pdf-box')
    })

    it('should return generic file icon for unknown types', () => {
      const options = createOptions()
      const { getAttachmentIcon } = useAssistantAttachments(options)

      expect(getAttachmentIcon('application/zip')).toBe('mdi-file')
      expect(getAttachmentIcon('text/plain')).toBe('mdi-file')
    })
  })

  describe('formatFileSize', () => {
    it('should format bytes correctly', () => {
      const options = createOptions()
      const { formatFileSize } = useAssistantAttachments(options)

      expect(formatFileSize(500)).toBe('500 B')
    })

    it('should format kilobytes correctly', () => {
      const options = createOptions()
      const { formatFileSize } = useAssistantAttachments(options)

      expect(formatFileSize(1024)).toBe('1.0 KB')
      expect(formatFileSize(2048)).toBe('2.0 KB')
    })

    it('should format megabytes correctly', () => {
      const options = createOptions()
      const { formatFileSize } = useAssistantAttachments(options)

      expect(formatFileSize(1024 * 1024)).toBe('1.0 MB')
      expect(formatFileSize(5 * 1024 * 1024)).toBe('5.0 MB')
    })
  })
})
