/**
 * Assistant Attachments Composable
 *
 * Manages file uploads and attachments for the assistant.
 */

import { ref, type Ref } from 'vue'
import { assistantApi } from '@/services/api'
import type { AttachmentInfo, AttachmentUploadResponse, ConversationMessage } from './types'

export interface UseAssistantAttachmentsOptions {
  messages: Ref<ConversationMessage[]>
  error: Ref<string | null>
  saveHistory: () => void
}

export function useAssistantAttachments(options: UseAssistantAttachmentsOptions) {
  const { messages, error, saveHistory } = options

  // Attachment state
  const pendingAttachments = ref<AttachmentInfo[]>([])
  const isUploading = ref(false)

  // Create a preview image data URL
  function createImagePreview(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = (e) => resolve(e.target?.result as string)
      reader.onerror = reject
      reader.readAsDataURL(file)
    })
  }

  // Upload a file attachment
  async function uploadAttachment(file: File): Promise<boolean> {
    // Validate file type
    const allowedTypes = ['image/png', 'image/jpeg', 'image/gif', 'image/webp', 'application/pdf']
    if (!allowedTypes.includes(file.type)) {
      error.value = `Nicht unterstützter Dateityp: ${file.type}`
      return false
    }

    // Validate file size (10MB max)
    const maxSize = 10 * 1024 * 1024
    if (file.size > maxSize) {
      error.value = 'Datei zu groß (max. 10MB)'
      return false
    }

    isUploading.value = true
    error.value = null

    try {
      const response = await assistantApi.uploadAttachment(file)
      const data = response.data as AttachmentUploadResponse

      // Create preview for images
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
      const err = e as { response?: { data?: { detail?: string } }; message?: string }
      error.value = err.response?.data?.detail || err.message || 'Fehler beim Upload'
      return false
    } finally {
      isUploading.value = false
    }
  }

  // Remove a pending attachment
  async function removeAttachment(attachmentId: string) {
    try {
      await assistantApi.deleteAttachment(attachmentId)
    } catch (e) {
      // Ignore delete errors
    }
    pendingAttachments.value = pendingAttachments.value.filter(a => a.id !== attachmentId)
  }

  // Clear all pending attachments
  async function clearAttachments() {
    for (const attachment of pendingAttachments.value) {
      try {
        await assistantApi.deleteAttachment(attachment.id)
      } catch (e) {
        // Ignore delete errors
      }
    }
    pendingAttachments.value = []
  }

  // Get file icon based on content type
  function getAttachmentIcon(contentType: string): string {
    if (contentType.startsWith('image/')) {
      return 'mdi-image'
    }
    if (contentType === 'application/pdf') {
      return 'mdi-file-pdf-box'
    }
    return 'mdi-file'
  }

  // Format file size for display
  function formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  // Save temporary attachments to entity
  async function saveAttachmentsToEntity(actionValue: string): Promise<boolean> {
    error.value = null

    try {
      // Parse the action value (JSON with entity_id and attachment_ids)
      const { entity_id, attachment_ids } = JSON.parse(actionValue)

      if (!entity_id || !attachment_ids || attachment_ids.length === 0) {
        throw new Error('Keine Attachments zum Speichern')
      }

      const response = await assistantApi.saveToEntityAttachments(entity_id, attachment_ids)
      const result = response.data

      // Add result message to chat
      const resultMessage: ConversationMessage = {
        role: 'assistant',
        content: result.message,
        timestamp: new Date(),
        response_type: result.success ? 'success' : 'error',
      }
      messages.value.push(resultMessage)
      saveHistory()

      return result.success
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string }
      error.value = err.response?.data?.detail || err.message || 'Fehler beim Speichern'
      const errorMessage: ConversationMessage = {
        role: 'assistant',
        content: `Fehler: ${error.value}`,
        timestamp: new Date(),
        response_type: 'error',
      }
      messages.value.push(errorMessage)
      saveHistory()
      return false
    }
  }

  return {
    // State
    pendingAttachments,
    isUploading,

    // Methods
    uploadAttachment,
    removeAttachment,
    clearAttachments,
    getAttachmentIcon,
    formatFileSize,
    saveAttachmentsToEntity,
  }
}
