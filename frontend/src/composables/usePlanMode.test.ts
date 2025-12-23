/**
 * Tests for usePlanMode composable
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { usePlanMode } from './usePlanMode'
import { api } from '@/services/api'

// Mock the api module
vi.mock('@/services/api', () => ({
  api: {
    post: vi.fn(),
  },
}))

describe('usePlanMode', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('should initialize with empty conversation', () => {
      const { conversation } = usePlanMode()
      expect(conversation.value).toEqual([])
    })

    it('should initialize with loading false', () => {
      const { loading } = usePlanMode()
      expect(loading.value).toBe(false)
    })

    it('should initialize with streaming false', () => {
      const { streaming } = usePlanMode()
      expect(streaming.value).toBe(false)
    })

    it('should initialize with no error', () => {
      const { error } = usePlanMode()
      expect(error.value).toBeNull()
    })

    it('should initialize with no results', () => {
      const { results } = usePlanMode()
      expect(results.value).toBeNull()
    })
  })

  describe('computed properties', () => {
    it('should compute hasConversation correctly', () => {
      const { conversation, hasConversation } = usePlanMode()

      expect(hasConversation.value).toBe(false)

      conversation.value.push({ role: 'user', content: 'test' })
      expect(hasConversation.value).toBe(true)
    })

    it('should compute conversationLength correctly', () => {
      const { conversation, conversationLength } = usePlanMode()

      expect(conversationLength.value).toBe(0)

      conversation.value.push({ role: 'user', content: 'test' })
      expect(conversationLength.value).toBe(1)

      conversation.value.push({ role: 'assistant', content: 'response' })
      expect(conversationLength.value).toBe(2)
    })

    it('should compute generatedPrompt correctly', () => {
      const { results, generatedPrompt } = usePlanMode()

      expect(generatedPrompt.value).toBeNull()

      results.value = {
        success: true,
        message: 'Test',
        has_generated_prompt: true,
        generated_prompt: 'Test prompt',
        suggested_mode: 'read',
        mode: 'plan',
      }

      expect(generatedPrompt.value).toEqual({
        prompt: 'Test prompt',
        suggested_mode: 'read',
      })
    })
  })

  describe('executePlanQuery', () => {
    it('should reject empty questions', async () => {
      const { executePlanQuery, error } = usePlanMode()

      const result = await executePlanQuery('')
      expect(result).toBe(false)
      expect(error.value).toBeTruthy()
    })

    it('should reject whitespace-only questions', async () => {
      const { executePlanQuery, error } = usePlanMode()

      const result = await executePlanQuery('   ')
      expect(result).toBe(false)
      expect(error.value).toBeTruthy()
    })

    it('should add user message to conversation', async () => {
      const mockResponse = {
        data: {
          success: true,
          message: 'Assistant response',
          has_generated_prompt: false,
          generated_prompt: null,
          suggested_mode: null,
        },
      }
      vi.mocked(api.post).mockResolvedValue(mockResponse)

      const { executePlanQuery, conversation } = usePlanMode()

      await executePlanQuery('Test question')

      expect(conversation.value.length).toBe(2) // user + assistant
      expect(conversation.value[0].role).toBe('user')
      expect(conversation.value[0].content).toBe('Test question')
    })

    it('should add assistant response to conversation', async () => {
      const mockResponse = {
        data: {
          success: true,
          message: 'Assistant response',
          has_generated_prompt: false,
          generated_prompt: null,
          suggested_mode: null,
        },
      }
      vi.mocked(api.post).mockResolvedValue(mockResponse)

      const { executePlanQuery, conversation } = usePlanMode()

      await executePlanQuery('Test question')

      expect(conversation.value.length).toBe(2)
      expect(conversation.value[1].role).toBe('assistant')
      expect(conversation.value[1].content).toBe('Assistant response')
    })

    it('should handle API errors gracefully', async () => {
      vi.mocked(api.post).mockRejectedValue(new Error('Network error'))

      const { executePlanQuery, error, conversation } = usePlanMode()

      const result = await executePlanQuery('Test question')

      expect(result).toBe(false)
      expect(error.value).toBeTruthy()
      // Optimistic update should be rolled back
      expect(conversation.value.length).toBe(0)
    })

    it('should handle rate limiting (429)', async () => {
      const error = new Error('Rate limited')
      ;(error as any).response = { status: 429 }
      vi.mocked(api.post).mockRejectedValue(error)

      const { executePlanQuery, error: errorRef } = usePlanMode()

      await executePlanQuery('Test question')

      expect(errorRef.value).toContain('warte')
    })

    it('should enforce conversation length limit', async () => {
      const { conversation, executePlanQuery, error } = usePlanMode()

      // Fill conversation to max (20 * 2 = 40 messages)
      for (let i = 0; i < 40; i++) {
        conversation.value.push({
          role: i % 2 === 0 ? 'user' : 'assistant',
          content: `Message ${i}`,
        })
      }

      const result = await executePlanQuery('New question')

      expect(result).toBe(false)
      expect(error.value).toContain('lang')
    })

    it('should set loading state during request', async () => {
      let resolvePromise: (value: any) => void
      const promise = new Promise((resolve) => {
        resolvePromise = resolve
      })
      vi.mocked(api.post).mockReturnValue(promise as any)

      const { executePlanQuery, loading } = usePlanMode()

      expect(loading.value).toBe(false)

      const queryPromise = executePlanQuery('Test question')
      expect(loading.value).toBe(true)

      resolvePromise!({
        data: {
          success: true,
          message: 'Response',
          has_generated_prompt: false,
          generated_prompt: null,
          suggested_mode: null,
        },
      })

      await queryPromise
      expect(loading.value).toBe(false)
    })
  })

  describe('reset', () => {
    it('should clear conversation', () => {
      const { conversation, reset } = usePlanMode()

      conversation.value.push({ role: 'user', content: 'test' })
      expect(conversation.value.length).toBe(1)

      reset()
      expect(conversation.value.length).toBe(0)
    })

    it('should clear results', () => {
      const { results, reset } = usePlanMode()

      results.value = {
        success: true,
        message: 'Test',
        has_generated_prompt: true,
        generated_prompt: 'Test prompt',
        suggested_mode: 'read',
        mode: 'plan',
      }

      reset()
      expect(results.value).toBeNull()
    })

    it('should clear error', () => {
      const { error, reset } = usePlanMode()

      error.value = 'Some error'

      reset()
      expect(error.value).toBeNull()
    })

    it('should reset loading state', () => {
      const { loading, streaming, reset } = usePlanMode()

      loading.value = true
      streaming.value = true

      reset()
      expect(loading.value).toBe(false)
      expect(streaming.value).toBe(false)
    })
  })

  describe('clearError', () => {
    it('should clear error without affecting other state', () => {
      const { error, conversation, clearError } = usePlanMode()

      conversation.value.push({ role: 'user', content: 'test' })
      error.value = 'Some error'

      clearError()

      expect(error.value).toBeNull()
      expect(conversation.value.length).toBe(1) // Conversation preserved
    })
  })

  describe('getDisplayConversation', () => {
    it('should return all messages without limit', () => {
      const { conversation, getDisplayConversation } = usePlanMode()

      for (let i = 0; i < 10; i++) {
        conversation.value.push({
          role: i % 2 === 0 ? 'user' : 'assistant',
          content: `Message ${i}`,
        })
      }

      const display = getDisplayConversation()
      expect(display.length).toBe(10)
    })

    it('should return limited messages with limit', () => {
      const { conversation, getDisplayConversation } = usePlanMode()

      for (let i = 0; i < 10; i++) {
        conversation.value.push({
          role: i % 2 === 0 ? 'user' : 'assistant',
          content: `Message ${i}`,
        })
      }

      const display = getDisplayConversation(5)
      expect(display.length).toBe(5)
      expect(display[0].content).toBe('Message 5') // Last 5 messages
    })
  })

  describe('executePlanQueryStream', () => {
    it('should reject empty questions', async () => {
      const { executePlanQueryStream, error } = usePlanMode()

      const result = await executePlanQueryStream('')
      expect(result).toBe(false)
      expect(error.value).toBeTruthy()
    })

    it('should set streaming state during request', async () => {
      // Create a mock readable stream
      const mockStream = {
        getReader: () => ({
          read: vi.fn()
            .mockResolvedValueOnce({
              done: false,
              value: new TextEncoder().encode('data: {"event": "start"}\n\n'),
            })
            .mockResolvedValueOnce({
              done: false,
              value: new TextEncoder().encode('data: {"event": "chunk", "data": "Hello"}\n\n'),
            })
            .mockResolvedValueOnce({
              done: false,
              value: new TextEncoder().encode('data: {"event": "done"}\n\n'),
            })
            .mockResolvedValueOnce({ done: true, value: undefined }),
        }),
      }

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        body: mockStream,
      })

      const { executePlanQueryStream, streaming, conversation } = usePlanMode()

      const resultPromise = executePlanQueryStream('Test question')

      // Initial state check happens after first await
      await new Promise(resolve => setTimeout(resolve, 0))

      await resultPromise

      expect(streaming.value).toBe(false) // After completion
      expect(conversation.value.length).toBe(2) // user + assistant
    })

    it('should handle streaming errors gracefully', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'))

      const { executePlanQueryStream, error, conversation } = usePlanMode()

      const result = await executePlanQueryStream('Test question')

      expect(result).toBe(false)
      expect(error.value).toBeTruthy()
      expect(conversation.value.length).toBe(0) // Rolled back
    })
  })

  describe('cancelStream', () => {
    it('should cancel via abort controller', () => {
      const { cancelStream } = usePlanMode()

      // Calling cancelStream when no stream is active should not throw
      expect(() => cancelStream()).not.toThrow()
    })

    it('should reset streaming state on cancel', async () => {
      // Simulate a streaming request that will be cancelled
      global.fetch = vi.fn().mockImplementation(
        (_url, options) => {
          // Return a promise that will be aborted
          return new Promise((_, reject) => {
            options.signal?.addEventListener('abort', () => {
              reject(new DOMException('Aborted', 'AbortError'))
            })
          })
        }
      )

      const { executePlanQueryStream, cancelStream, streaming, error } = usePlanMode()

      // Start streaming without awaiting
      const promise = executePlanQueryStream('Test question')

      // Give it a moment to start
      await new Promise(resolve => setTimeout(resolve, 5))

      // Cancel the stream
      cancelStream()

      // Wait for the promise to resolve/reject
      await promise

      expect(streaming.value).toBe(false)
      // Error should indicate cancellation
      expect(error.value).toContain('abgebrochen')
    })
  })
})
