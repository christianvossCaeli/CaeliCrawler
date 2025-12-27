/**
 * Tests for usePlanModeSSE composable
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ref, type Ref } from 'vue'
import { usePlanModeSSE } from './usePlanModeSSE'
import type { PlanMessage, PlanModeResult } from './types'

// Mock useI18n
vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string, fallback?: string) => fallback || key,
  }),
}))

// Mock fetch for SSE
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('usePlanModeSSE', () => {
  // Shared refs for testing
  let conversation: Ref<PlanMessage[]>
  let loading: Ref<boolean>
  let streaming: Ref<boolean>
  let error: Ref<string | null>
  let results: Ref<PlanModeResult | null>

  beforeEach(() => {
    vi.clearAllMocks()
    conversation = ref<PlanMessage[]>([])
    loading = ref(false)
    streaming = ref(false)
    error = ref<string | null>(null)
    results = ref<PlanModeResult | null>(null)

    // Mock localStorage
    vi.stubGlobal('localStorage', {
      getItem: vi.fn().mockReturnValue('test-token'),
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  function createSSE() {
    return usePlanModeSSE({
      conversation,
      loading,
      streaming,
      error,
      results,
    })
  }

  describe('analyzeResponseForPrompt', () => {
    it('should detect generated prompt from response text', () => {
      const { analyzeResponseForPrompt } = createSSE()

      const responseText = `Here is your prompt:

**Fertiger Prompt:**
> Show all municipalities in Bavaria

**Modus:** Lese-Modus`

      analyzeResponseForPrompt(responseText)

      expect(results.value).not.toBeNull()
      expect(results.value?.has_generated_prompt).toBe(true)
      expect(results.value?.suggested_mode).toBe('read')
    })

    it('should detect write mode', () => {
      const { analyzeResponseForPrompt } = createSSE()

      const responseText = `**Fertiger Prompt:**
> Create new entity

**Modus:** Schreib-Modus`

      analyzeResponseForPrompt(responseText)

      expect(results.value?.suggested_mode).toBe('write')
    })

    it('should return null results when no prompt detected', () => {
      const { analyzeResponseForPrompt } = createSSE()

      analyzeResponseForPrompt('Just a regular response without any prompt markers')

      expect(results.value).toBeNull()
    })
  })

  describe('executePlanQueryStream', () => {
    it('should reject empty questions', async () => {
      const { executePlanQueryStream } = createSSE()

      const result = await executePlanQueryStream('')

      expect(result).toBe(false)
      expect(error.value).toBeTruthy()
    })

    it('should reject whitespace-only questions', async () => {
      const { executePlanQueryStream } = createSSE()

      const result = await executePlanQueryStream('   ')

      expect(result).toBe(false)
      expect(error.value).toBeTruthy()
    })

    it('should reject when conversation is at max length', async () => {
      const { executePlanQueryStream } = createSSE()

      // Fill conversation to max
      for (let i = 0; i < 20; i++) {
        conversation.value.push({
          role: i % 2 === 0 ? 'user' : 'assistant',
          content: `Message ${i}`,
        })
      }

      const result = await executePlanQueryStream('New question')

      expect(result).toBe(false)
      expect(error.value).toContain('lang')
    })

    it('should set loading and streaming during request', async () => {
      const mockReader = {
        read: vi.fn()
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('data: {"event":"start"}\n'),
          })
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('data: {"event":"done"}\n'),
          })
          .mockResolvedValueOnce({ done: true, value: undefined }),
      }

      mockFetch.mockResolvedValue({
        ok: true,
        body: { getReader: () => mockReader },
      })

      const { executePlanQueryStream } = createSSE()

      const promise = executePlanQueryStream('Test question')

      // Check loading states during execution
      expect(loading.value).toBe(true)
      expect(streaming.value).toBe(true)

      await promise

      expect(loading.value).toBe(false)
      expect(streaming.value).toBe(false)
    })

    it('should add user message optimistically', async () => {
      const mockReader = {
        read: vi.fn()
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('data: {"event":"start"}\n'),
          })
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('data: {"event":"done"}\n'),
          })
          .mockResolvedValueOnce({ done: true, value: undefined }),
      }

      mockFetch.mockResolvedValue({
        ok: true,
        body: { getReader: () => mockReader },
      })

      const { executePlanQueryStream } = createSSE()
      await executePlanQueryStream('User question')

      expect(conversation.value[0].role).toBe('user')
      expect(conversation.value[0].content).toBe('User question')
    })

    it('should accumulate streamed chunks', async () => {
      const mockReader = {
        read: vi.fn()
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('data: {"event":"start"}\n'),
          })
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('data: {"event":"chunk","data":"Hello "}\n'),
          })
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('data: {"event":"chunk","data":"World"}\n'),
          })
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('data: {"event":"done"}\n'),
          })
          .mockResolvedValueOnce({ done: true, value: undefined }),
      }

      mockFetch.mockResolvedValue({
        ok: true,
        body: { getReader: () => mockReader },
      })

      const { executePlanQueryStream } = createSSE()
      await executePlanQueryStream('Question')

      // Assistant message should have accumulated content
      const assistantMessage = conversation.value.find((m) => m.role === 'assistant')
      expect(assistantMessage?.content).toBe('Hello World')
      expect(assistantMessage?.isStreaming).toBe(false)
    })

    it('should handle HTTP errors', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 500,
      })

      const { executePlanQueryStream } = createSSE()
      const result = await executePlanQueryStream('Question')

      expect(result).toBe(false)
      expect(error.value).toBeTruthy()
    })

    it('should handle missing response body', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        body: null,
      })

      const { executePlanQueryStream } = createSSE()
      const result = await executePlanQueryStream('Question')

      expect(result).toBe(false)
      expect(error.value).toBeTruthy()
    })

    it('should handle partial responses on error', async () => {
      const mockReader = {
        read: vi.fn()
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('data: {"event":"start"}\n'),
          })
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('data: {"event":"chunk","data":"Partial content..."}\n'),
          })
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('data: {"event":"error","data":"Timeout","partial":true}\n'),
          })
          .mockResolvedValueOnce({ done: true, value: undefined }),
      }

      mockFetch.mockResolvedValue({
        ok: true,
        body: { getReader: () => mockReader },
      })

      const { executePlanQueryStream } = createSSE()
      const result = await executePlanQueryStream('Question')

      expect(result).toBe(true) // Returns true because we have partial content
      expect(error.value).toBeTruthy()
      const assistantMessage = conversation.value.find((m) => m.role === 'assistant')
      expect(assistantMessage?.content).toContain('Partial content')
      expect(assistantMessage?.content).toContain('Timeout')
    })

    it('should include auth token in request headers', async () => {
      const mockReader = {
        read: vi.fn()
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('data: {"event":"done"}\n'),
          })
          .mockResolvedValueOnce({ done: true, value: undefined }),
      }

      mockFetch.mockResolvedValue({
        ok: true,
        body: { getReader: () => mockReader },
      })

      const { executePlanQueryStream } = createSSE()
      await executePlanQueryStream('Question')

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/analysis/smart-query/stream',
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer test-token',
          }),
        })
      )
    })

    it('should send conversation history in request', async () => {
      conversation.value = [
        { role: 'user', content: 'Previous question' },
        { role: 'assistant', content: 'Previous answer' },
      ]

      const mockReader = {
        read: vi.fn()
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('data: {"event":"done"}\n'),
          })
          .mockResolvedValueOnce({ done: true, value: undefined }),
      }

      mockFetch.mockResolvedValue({
        ok: true,
        body: { getReader: () => mockReader },
      })

      const { executePlanQueryStream } = createSSE()
      await executePlanQueryStream('New question')

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: expect.stringContaining('Previous question'),
        })
      )
    })
  })

  describe('cancelStream', () => {
    it('should abort ongoing request', async () => {
      const mockAbort = vi.fn()
      vi.stubGlobal('AbortController', class {
        signal = { aborted: false }
        abort = mockAbort
      })

      const mockReader = {
        read: vi.fn().mockImplementation(
          () => new Promise((resolve) => setTimeout(() => resolve({ done: true, value: undefined }), 1000))
        ),
      }

      mockFetch.mockResolvedValue({
        ok: true,
        body: { getReader: () => mockReader },
      })

      const { executePlanQueryStream, cancelStream } = createSSE()

      // Start streaming (don't await)
      executePlanQueryStream('Question')

      // Cancel immediately
      cancelStream()

      expect(mockAbort).toHaveBeenCalled()
    })

    it('should do nothing if no active stream', () => {
      const { cancelStream } = createSSE()

      // Should not throw
      expect(() => cancelStream()).not.toThrow()
    })
  })

  describe('edge cases', () => {
    it('should handle malformed SSE data gracefully', async () => {
      const mockReader = {
        read: vi.fn()
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('data: not-valid-json\n'),
          })
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('data: {"event":"done"}\n'),
          })
          .mockResolvedValueOnce({ done: true, value: undefined }),
      }

      mockFetch.mockResolvedValue({
        ok: true,
        body: { getReader: () => mockReader },
      })

      const { executePlanQueryStream } = createSSE()
      const result = await executePlanQueryStream('Question')

      // Should complete without crashing
      expect(result).toBe(true)
    })

    it('should handle lines without data: prefix', async () => {
      const mockReader = {
        read: vi.fn()
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('event: ping\n'),
          })
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('data: {"event":"done"}\n'),
          })
          .mockResolvedValueOnce({ done: true, value: undefined }),
      }

      mockFetch.mockResolvedValue({
        ok: true,
        body: { getReader: () => mockReader },
      })

      const { executePlanQueryStream } = createSSE()
      const result = await executePlanQueryStream('Question')

      expect(result).toBe(true)
    })
  })
})
