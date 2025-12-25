/**
 * Tests for useFileDownload composable
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useFileDownload } from './useFileDownload'

const createMockBlob = (content: string = 'test content', type: string = 'text/plain') => {
  return new Blob([content], { type })
}

describe('useFileDownload', () => {
  let createObjectURLSpy: any
  let revokeObjectURLSpy: any

  beforeEach(() => {
    vi.clearAllMocks()

    // Mock URL methods
    createObjectURLSpy = vi.spyOn(window.URL, 'createObjectURL')
    revokeObjectURLSpy = vi.spyOn(window.URL, 'revokeObjectURL')

    // Default implementations
    createObjectURLSpy.mockReturnValue('blob:mock-url')
    revokeObjectURLSpy.mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('State Management', () => {
    it('should initialize with correct default state', () => {
      const { isDownloading, downloadError } = useFileDownload()

      expect(isDownloading.value).toBe(false)
      expect(downloadError.value).toBeNull()
    })
  })

  describe('downloadBlob', () => {
    it('should download blob successfully', () => {
      const { downloadBlob, isDownloading, downloadError } = useFileDownload()
      const blob = createMockBlob()

      downloadBlob(blob, 'test.txt')

      expect(createObjectURLSpy).toHaveBeenCalledWith(blob)
      expect(revokeObjectURLSpy).toHaveBeenCalledWith('blob:mock-url')
      expect(isDownloading.value).toBe(false)
      expect(downloadError.value).toBeNull()
    })

    it('should sanitize filename with dangerous characters', () => {
      const { downloadBlob } = useFileDownload()
      const blob = createMockBlob()

      // Should not throw
      expect(() => downloadBlob(blob, 'test<>:"/\\|?*file.txt')).not.toThrow()
      expect(createObjectURLSpy).toHaveBeenCalled()
    })

    it('should sanitize filename with control characters', () => {
      const { downloadBlob } = useFileDownload()
      const blob = createMockBlob()

      // Should not throw
      expect(() => downloadBlob(blob, 'test\x00\x01\x1ffile.txt')).not.toThrow()
      expect(createObjectURLSpy).toHaveBeenCalled()
    })

    it('should truncate very long filenames', () => {
      const { downloadBlob } = useFileDownload()
      const blob = createMockBlob()
      const longFilename = 'a'.repeat(250) + '.txt'

      // Should not throw
      expect(() => downloadBlob(blob, longFilename)).not.toThrow()
      expect(createObjectURLSpy).toHaveBeenCalled()
    })

    it('should clear download error before download', () => {
      const { downloadBlob, downloadError } = useFileDownload()
      const blob = createMockBlob()

      // Set an error
      downloadError.value = 'Previous error'

      downloadBlob(blob, 'test.txt')

      expect(downloadError.value).toBeNull()
    })

    it('should handle download errors', () => {
      createObjectURLSpy.mockImplementation(() => {
        throw new Error('Failed to create object URL')
      })

      const { downloadBlob, downloadError } = useFileDownload()
      const blob = createMockBlob()

      expect(() => downloadBlob(blob, 'test.txt')).toThrow()
      expect(downloadError.value).toBe('Failed to create object URL')
    })

    it('should revoke object URL even on error', () => {
      createObjectURLSpy.mockReturnValue('blob:mock-url')
      const createElementSpy = vi.spyOn(document, 'createElement')
      const mockLink = document.createElement('a')
      const mockClick = vi.fn(() => {
        throw new Error('Click failed')
      })
      mockLink.click = mockClick
      createElementSpy.mockReturnValue(mockLink)

      const { downloadBlob } = useFileDownload()
      const blob = createMockBlob()

      expect(() => downloadBlob(blob, 'test.txt')).toThrow()
      expect(revokeObjectURLSpy).toHaveBeenCalledWith('blob:mock-url')

      createElementSpy.mockRestore()
    })

    it('should set isDownloading to false even on error', () => {
      createObjectURLSpy.mockImplementation(() => {
        throw new Error('Failed')
      })

      const { downloadBlob, isDownloading } = useFileDownload()
      const blob = createMockBlob()

      try {
        downloadBlob(blob, 'test.txt')
      } catch (e) {
        // Expected error
      }

      expect(isDownloading.value).toBe(false)
    })

    it('should handle different blob types', () => {
      const { downloadBlob } = useFileDownload()

      const types = [
        'text/plain',
        'application/json',
        'application/pdf',
        'image/png',
        'application/octet-stream',
      ]

      types.forEach(type => {
        const blob = createMockBlob('content', type)
        downloadBlob(blob, `file.${type.split('/')[1]}`)
        expect(createObjectURLSpy).toHaveBeenCalled()
      })
    })
  })

  describe('downloadFromResponse', () => {
    it('should download from successful response', async () => {
      const mockResponse = {
        ok: true,
        headers: new Map([['Content-Type', 'text/plain']]),
        blob: vi.fn().mockResolvedValue(createMockBlob()),
      } as any

      mockResponse.headers.get = (key: string) => {
        if (key === 'Content-Type') return 'text/plain'
        return null
      }

      const { downloadFromResponse } = useFileDownload()

      await downloadFromResponse(mockResponse, 'default.txt')

      expect(mockResponse.blob).toHaveBeenCalled()
      expect(createObjectURLSpy).toHaveBeenCalled()
    })

    it('should extract filename from Content-Disposition header', async () => {
      const mockResponse = {
        ok: true,
        headers: {
          get: (key: string) => {
            if (key === 'Content-Disposition') {
              return 'attachment; filename="custom-file.pdf"'
            }
            return null
          },
        },
        blob: vi.fn().mockResolvedValue(createMockBlob()),
      } as any

      const { downloadFromResponse } = useFileDownload()

      await downloadFromResponse(mockResponse, 'default.txt')

      expect(createObjectURLSpy).toHaveBeenCalled()
    })

    it('should handle Content-Disposition without quotes', async () => {
      const mockResponse = {
        ok: true,
        headers: {
          get: (key: string) => {
            if (key === 'Content-Disposition') {
              return 'attachment; filename=simple-file.txt'
            }
            return null
          },
        },
        blob: vi.fn().mockResolvedValue(createMockBlob()),
      } as any

      const { downloadFromResponse } = useFileDownload()

      await downloadFromResponse(mockResponse, 'default.txt')

      expect(createObjectURLSpy).toHaveBeenCalled()
    })

    it('should throw error for non-ok response', async () => {
      const mockResponse = {
        ok: false,
        status: 404,
      } as any

      const { downloadFromResponse } = useFileDownload()

      await expect(downloadFromResponse(mockResponse, 'test.txt')).rejects.toThrow(
        'Download failed: 404'
      )
    })

    it('should use default filename if Content-Disposition is missing', async () => {
      const mockResponse = {
        ok: true,
        headers: {
          get: () => null,
        },
        blob: vi.fn().mockResolvedValue(createMockBlob()),
      } as any

      const { downloadFromResponse } = useFileDownload()

      await downloadFromResponse(mockResponse, 'fallback.txt')

      expect(createObjectURLSpy).toHaveBeenCalled()
    })

    it('should handle malformed Content-Disposition header', async () => {
      const mockResponse = {
        ok: true,
        headers: {
          get: (key: string) => {
            if (key === 'Content-Disposition') {
              return 'attachment; invalid-header'
            }
            return null
          },
        },
        blob: vi.fn().mockResolvedValue(createMockBlob()),
      } as any

      const { downloadFromResponse } = useFileDownload()

      await downloadFromResponse(mockResponse, 'default.txt')

      expect(createObjectURLSpy).toHaveBeenCalled()
    })

    it('should handle different HTTP error codes', async () => {
      const { downloadFromResponse } = useFileDownload()

      const errorCodes = [400, 401, 403, 404, 500, 502, 503]

      for (const status of errorCodes) {
        const mockResponse = { ok: false, status } as any

        await expect(downloadFromResponse(mockResponse, 'test.txt')).rejects.toThrow(
          `Download failed: ${status}`
        )
      }
    })
  })

  describe('downloadArrayBuffer', () => {
    it('should download ArrayBuffer successfully', () => {
      const { downloadArrayBuffer } = useFileDownload()
      const buffer = new ArrayBuffer(8)

      downloadArrayBuffer(buffer, 'data.bin')

      expect(createObjectURLSpy).toHaveBeenCalled()
    })

    it('should use custom MIME type', () => {
      const { downloadArrayBuffer } = useFileDownload()
      const buffer = new ArrayBuffer(8)

      downloadArrayBuffer(buffer, 'data.json', 'application/json')

      expect(createObjectURLSpy).toHaveBeenCalled()
    })

    it('should use default MIME type', () => {
      const { downloadArrayBuffer } = useFileDownload()
      const buffer = new ArrayBuffer(8)

      downloadArrayBuffer(buffer, 'data.bin')

      expect(createObjectURLSpy).toHaveBeenCalled()
    })

    it('should handle empty ArrayBuffer', () => {
      const { downloadArrayBuffer } = useFileDownload()
      const buffer = new ArrayBuffer(0)

      downloadArrayBuffer(buffer, 'empty.bin')

      expect(createObjectURLSpy).toHaveBeenCalled()
    })

    it('should handle large ArrayBuffer', () => {
      const { downloadArrayBuffer } = useFileDownload()
      const buffer = new ArrayBuffer(10 * 1024 * 1024) // 10MB

      downloadArrayBuffer(buffer, 'large.bin')

      expect(createObjectURLSpy).toHaveBeenCalled()
    })

    it('should handle different ArrayBuffer-like types', () => {
      const { downloadArrayBuffer } = useFileDownload()

      // Regular ArrayBuffer
      const buffer = new ArrayBuffer(8)
      downloadArrayBuffer(buffer, 'test.bin')
      expect(createObjectURLSpy).toHaveBeenCalled()

      // Typed arrays have an underlying ArrayBuffer
      const uint8 = new Uint8Array([1, 2, 3, 4])
      downloadArrayBuffer(uint8.buffer, 'test2.bin')
      expect(createObjectURLSpy).toHaveBeenCalledTimes(2)
    })
  })

  describe('Edge Cases', () => {
    it('should handle rapid successive downloads', () => {
      const { downloadBlob } = useFileDownload()

      for (let i = 0; i < 5; i++) {
        const blob = createMockBlob(`content ${i}`)
        downloadBlob(blob, `file${i}.txt`)
      }

      expect(createObjectURLSpy).toHaveBeenCalledTimes(5)
      expect(revokeObjectURLSpy).toHaveBeenCalledTimes(5)
    })

    it('should handle empty filename', () => {
      const { downloadBlob } = useFileDownload()
      const blob = createMockBlob()

      expect(() => downloadBlob(blob, '')).not.toThrow()
    })

    it('should handle filename with only special characters', () => {
      const { downloadBlob } = useFileDownload()
      const blob = createMockBlob()

      expect(() => downloadBlob(blob, '<>:"/\\|?*')).not.toThrow()
    })

    it('should handle filename with unicode characters', () => {
      const { downloadBlob } = useFileDownload()
      const blob = createMockBlob()

      expect(() => downloadBlob(blob, 'файл-文件-ファイル.txt')).not.toThrow()
    })

    it('should handle blob with no type', () => {
      const { downloadBlob } = useFileDownload()
      const blob = new Blob(['content'])

      downloadBlob(blob, 'test.txt')

      expect(createObjectURLSpy).toHaveBeenCalled()
    })
  })

  describe('Memory Management', () => {
    it('should always revoke object URL to prevent memory leaks', () => {
      const { downloadBlob } = useFileDownload()
      const blob = createMockBlob()

      downloadBlob(blob, 'test.txt')

      expect(revokeObjectURLSpy).toHaveBeenCalledTimes(1)
      expect(revokeObjectURLSpy).toHaveBeenCalledWith('blob:mock-url')
    })

    it('should revoke object URL even when click fails', () => {
      createObjectURLSpy.mockReturnValue('blob:mock-url')
      const createElementSpy = vi.spyOn(document, 'createElement')
      const mockLink = document.createElement('a')
      const mockClick = vi.fn(() => {
        throw new Error('Click failed')
      })
      mockLink.click = mockClick
      createElementSpy.mockReturnValue(mockLink)

      const { downloadBlob } = useFileDownload()
      const blob = createMockBlob()

      try {
        downloadBlob(blob, 'test.txt')
      } catch (e) {
        // Expected
      }

      expect(revokeObjectURLSpy).toHaveBeenCalledWith('blob:mock-url')
      createElementSpy.mockRestore()
    })

    it('should revoke object URL even when removeChild fails', () => {
      createObjectURLSpy.mockReturnValue('blob:mock-url')
      const removeChildSpy = vi.spyOn(document.body, 'removeChild')
      removeChildSpy.mockImplementation(() => {
        throw new Error('Remove failed')
      })

      const { downloadBlob } = useFileDownload()
      const blob = createMockBlob()

      try {
        downloadBlob(blob, 'test.txt')
      } catch (e) {
        // Expected
      }

      expect(revokeObjectURLSpy).toHaveBeenCalledWith('blob:mock-url')
      removeChildSpy.mockRestore()
    })
  })

  describe('State Tracking', () => {
    it('should track download state', () => {
      const { downloadBlob, isDownloading } = useFileDownload()
      const blob = createMockBlob()

      expect(isDownloading.value).toBe(false)

      downloadBlob(blob, 'test.txt')

      // After download completes, should be false again
      expect(isDownloading.value).toBe(false)
    })

    it('should track download errors', () => {
      createObjectURLSpy.mockImplementation(() => {
        throw new Error('Mock error')
      })

      const { downloadBlob, downloadError } = useFileDownload()
      const blob = createMockBlob()

      try {
        downloadBlob(blob, 'test.txt')
      } catch (e) {
        // Expected
      }

      expect(downloadError.value).toBe('Mock error')
    })

    it('should clear error on successful download', () => {
      const { downloadBlob, downloadError } = useFileDownload()
      const blob = createMockBlob()

      // Set an error first
      downloadError.value = 'Previous error'

      // Successful download should clear it
      downloadBlob(blob, 'test.txt')

      expect(downloadError.value).toBeNull()
    })
  })

  describe('Filename Sanitization', () => {
    it('should sanitize dangerous path characters', () => {
      const { downloadBlob } = useFileDownload()
      const blob = createMockBlob()

      // These characters should be sanitized
      const dangerousNames = [
        '../../../etc/passwd',
        'file<script>.txt',
        'file:zone.txt',
        'file"quoted".txt',
        'file/slash.txt',
        'file\\backslash.txt',
        'file|pipe.txt',
        'file?question.txt',
        'file*star.txt',
      ]

      dangerousNames.forEach(name => {
        expect(() => downloadBlob(blob, name)).not.toThrow()
      })

      expect(createObjectURLSpy).toHaveBeenCalledTimes(dangerousNames.length)
    })

    it('should handle very long filenames by truncating', () => {
      const { downloadBlob } = useFileDownload()
      const blob = createMockBlob()

      const longName = 'a'.repeat(300) + '.txt'

      expect(() => downloadBlob(blob, longName)).not.toThrow()
    })

    it('should preserve valid filename characters', () => {
      const { downloadBlob } = useFileDownload()
      const blob = createMockBlob()

      const validNames = [
        'simple-file.txt',
        'file_with_underscores.txt',
        'file.with.dots.txt',
        'file (with) parens.txt',
        'file-123.txt',
        'UPPERCASE.TXT',
      ]

      validNames.forEach(name => {
        expect(() => downloadBlob(blob, name)).not.toThrow()
      })
    })
  })
})
