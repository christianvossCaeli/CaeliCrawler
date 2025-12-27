/**
 * Smart Query Attachments Composable
 *
 * Handles file attachment functionality for Smart Query including
 * upload, preview generation, and cleanup.
 */

import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { assistantApi } from '@/services/api'
import type { AttachmentInfo } from './types'
import { getErrorDetail } from './types'

/**
 * Composable for managing Smart Query attachments
 */
export function useSmartQueryAttachments() {
  const { t } = useI18n()

  // State
  const pendingAttachments = ref<AttachmentInfo[]>([])
  const isUploading = ref(false)
  const error = ref<string | null>(null)

  // Allowed file types and size limits
  const ALLOWED_TYPES = ['image/png', 'image/jpeg', 'image/gif', 'image/webp', 'application/pdf']
  const MAX_SIZE = 10 * 1024 * 1024 // 10MB

  /**
   * Create a preview image from a file
   */
  function createImagePreview(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = (e) => resolve(e.target?.result as string)
      reader.onerror = reject
      reader.readAsDataURL(file)
    })
  }

  /**
   * Upload an attachment file
   */
  async function uploadAttachment(file: File): Promise<boolean> {
    // Validate file type
    if (!ALLOWED_TYPES.includes(file.type)) {
      error.value = t('assistant.attachmentTypeError')
      return false
    }

    // Validate file size
    if (file.size > MAX_SIZE) {
      error.value = t('assistant.attachmentTooLarge')
      return false
    }

    isUploading.value = true
    error.value = null

    try {
      const response = await assistantApi.uploadAttachment(file)
      const data = response.data

      // Generate preview for images
      let preview: string | undefined
      if (file.type.startsWith('image/')) {
        preview = await createImagePreview(file)
      }

      pendingAttachments.value.push({
        id: data.attachment.attachment_id,
        filename: data.attachment.filename,
        contentType: data.attachment.content_type,
        size: data.attachment.size,
        preview,
      })

      return true
    } catch (e: unknown) {
      error.value = getErrorDetail(e) || t('assistant.attachmentError')
      return false
    } finally {
      isUploading.value = false
    }
  }

  /**
   * Remove an attachment by ID
   */
  async function removeAttachment(attachmentId: string): Promise<void> {
    try {
      await assistantApi.deleteAttachment(attachmentId)
    } catch {
      // Ignore delete errors - attachment may already be gone
    }
    pendingAttachments.value = pendingAttachments.value.filter((a) => a.id !== attachmentId)
  }

  /**
   * Clear all pending attachments
   */
  async function clearAttachments(): Promise<void> {
    for (const attachment of pendingAttachments.value) {
      try {
        await assistantApi.deleteAttachment(attachment.id)
      } catch {
        // Ignore cleanup errors
      }
    }
    pendingAttachments.value = []
  }

  /**
   * Get attachment IDs for API calls
   */
  function getAttachmentIds(): string[] {
    return pendingAttachments.value.map((a) => a.id)
  }

  /**
   * Check if there are pending attachments
   */
  function hasAttachments(): boolean {
    return pendingAttachments.value.length > 0
  }

  /**
   * Clear error state
   */
  function clearError(): void {
    error.value = null
  }

  return {
    // State
    pendingAttachments,
    isUploading,
    error,

    // Methods
    uploadAttachment,
    removeAttachment,
    clearAttachments,
    getAttachmentIds,
    hasAttachments,
    clearError,
    createImagePreview,
  }
}
