/**
 * Composable for safe file downloads with proper cleanup.
 *
 * Handles blob creation, download triggering, and cleanup to prevent memory leaks.
 */

import { ref } from 'vue'

export function useFileDownload() {
  const isDownloading = ref(false)
  const downloadError = ref<string | null>(null)

  /**
   * Download a blob as a file.
   * Properly cleans up object URLs to prevent memory leaks.
   */
  function downloadBlob(blob: Blob, filename: string): void {
    let url: string | null = null

    try {
      isDownloading.value = true
      downloadError.value = null

      // Sanitize filename - remove dangerous characters
      const safeFilename = filename
        .replace(/[<>:"/\\|?*\x00-\x1f]/g, '_')
        .slice(0, 200)

      url = window.URL.createObjectURL(blob)

      const link = document.createElement('a')
      link.href = url
      link.download = safeFilename
      link.style.display = 'none'

      // Append, click, and remove in a try-finally to ensure cleanup
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    } catch (e) {
      downloadError.value = e instanceof Error ? e.message : 'Download failed'
      throw e
    } finally {
      // Always revoke the object URL to free memory
      if (url) {
        window.URL.revokeObjectURL(url)
      }
      isDownloading.value = false
    }
  }

  /**
   * Download from a fetch response.
   */
  async function downloadFromResponse(
    response: Response,
    defaultFilename: string
  ): Promise<void> {
    if (!response.ok) {
      throw new Error(`Download failed: ${response.status}`)
    }

    // Try to get filename from Content-Disposition header
    const contentDisposition = response.headers.get('Content-Disposition')
    let filename = defaultFilename

    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1].replace(/['"]/g, '')
      }
    }

    const blob = await response.blob()
    downloadBlob(blob, filename)
  }

  /**
   * Download binary data (ArrayBuffer) as a file.
   */
  function downloadArrayBuffer(
    data: ArrayBuffer,
    filename: string,
    mimeType: string = 'application/octet-stream'
  ): void {
    const blob = new Blob([data], { type: mimeType })
    downloadBlob(blob, filename)
  }

  return {
    isDownloading,
    downloadError,
    downloadBlob,
    downloadFromResponse,
    downloadArrayBuffer,
  }
}
