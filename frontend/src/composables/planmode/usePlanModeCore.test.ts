/**
 * Tests for usePlanModeCore composable
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { usePlanMode } from './usePlanModeCore'
import { api } from '@/services/api'
import { MAX_CONVERSATION_MESSAGES, TRIM_THRESHOLD } from './types'

// Mock the api module
vi.mock('@/services/api', () => ({
  api: {
    post: vi.fn(),
  },
}))

// Mock useI18n
vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string, fallback?: string) => fallback || key,
  }),
}))

// Mock usePlanModeSSE
vi.mock('./usePlanModeSSE', () => ({
  usePlanModeSSE: () => ({
    executePlanQueryStream: vi.fn().mockResolvedValue(true),
    cancelStream: vi.fn(),
    analyzeResponseForPrompt: vi.fn(),
  }),
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

describe('usePlanModeCore', () => {
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

    it('should initialize with validating false', () => {
      const { validating } = usePlanMode()
      expect(validating.value).toBe(false)
    })

    it('should initialize with no validationResult', () => {
      const { validationResult } = usePlanMode()
      expect(validationResult.value).toBeNull()
    })
  })

  describe('computed properties', () => {
    it('hasConversation should return false when empty', () => {
      const { hasConversation } = usePlanMode()
      expect(hasConversation.value).toBe(false)
    })

    it('hasConversation should return true after adding message', async () => {
      vi.mocked(api.post).mockResolvedValue(
        mockAxiosResponse({
          success: true,
          message: 'Response',
          has_generated_prompt: false,
          generated_prompt: null,
          suggested_mode: null,
        })
      )

      const { hasConversation, executePlanQuery } = usePlanMode()
      await executePlanQuery('Hello')
      expect(hasConversation.value).toBe(true)
    })

    it('generatedPrompt should return null when no prompt generated', () => {
      const { generatedPrompt } = usePlanMode()
      expect(generatedPrompt.value).toBeNull()
    })

    it('generatedPrompt should return prompt when available', async () => {
      vi.mocked(api.post).mockResolvedValue(
        mockAxiosResponse({
          success: true,
          message: 'Here is your prompt',
          has_generated_prompt: true,
          generated_prompt: 'Show all entities',
          suggested_mode: 'read',
        })
      )

      const { generatedPrompt, executePlanQuery } = usePlanMode()
      await executePlanQuery('Help me search')
      expect(generatedPrompt.value).toEqual({
        prompt: 'Show all entities',
        suggested_mode: 'read',
      })
    })

    it('conversationLength should reflect actual length', async () => {
      vi.mocked(api.post).mockResolvedValue(
        mockAxiosResponse({
          success: true,
          message: 'Response',
          has_generated_prompt: false,
          generated_prompt: null,
          suggested_mode: null,
        })
      )

      const { conversationLength, executePlanQuery } = usePlanMode()
      expect(conversationLength.value).toBe(0)
      await executePlanQuery('First')
      expect(conversationLength.value).toBe(2) // user + assistant
    })

    it('isNearLimit should return false when conversation is short', () => {
      const { isNearLimit } = usePlanMode()
      expect(isNearLimit.value).toBe(false)
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
      vi.mocked(api.post).mockResolvedValue(
        mockAxiosResponse({
          success: true,
          message: 'Response',
          has_generated_prompt: false,
          generated_prompt: null,
          suggested_mode: null,
        })
      )

      const { executePlanQuery, conversation } = usePlanMode()
      await executePlanQuery('Test question')
      expect(conversation.value[0].role).toBe('user')
      expect(conversation.value[0].content).toBe('Test question')
    })

    it('should add assistant response to conversation', async () => {
      vi.mocked(api.post).mockResolvedValue(
        mockAxiosResponse({
          success: true,
          message: 'Assistant response',
          has_generated_prompt: false,
          generated_prompt: null,
          suggested_mode: null,
        })
      )

      const { executePlanQuery, conversation } = usePlanMode()
      await executePlanQuery('Test question')
      expect(conversation.value[1].role).toBe('assistant')
      expect(conversation.value[1].content).toBe('Assistant response')
    })

    it('should set loading during request', async () => {
      let resolveRequest: (value: unknown) => void
      const requestPromise = new Promise((resolve) => {
        resolveRequest = resolve
      })
      vi.mocked(api.post).mockReturnValue(requestPromise as Promise<unknown>)

      const { executePlanQuery, loading } = usePlanMode()
      const queryPromise = executePlanQuery('Test')

      expect(loading.value).toBe(true)

      resolveRequest!(
        mockAxiosResponse({
          success: true,
          message: 'Done',
          has_generated_prompt: false,
          generated_prompt: null,
          suggested_mode: null,
        })
      )

      await queryPromise
      expect(loading.value).toBe(false)
    })

    it('should handle API errors', async () => {
      vi.mocked(api.post).mockRejectedValue(new Error('Network error'))

      const { executePlanQuery, error, conversation } = usePlanMode()
      const result = await executePlanQuery('Test')

      expect(result).toBe(false)
      expect(error.value).toBeTruthy()
      // User message should be removed on error
      expect(conversation.value).toHaveLength(0)
    })

    it('should handle rate limiting (429)', async () => {
      vi.mocked(api.post).mockRejectedValue({
        response: { status: 429 },
        message: 'Too many requests',
      })

      const { executePlanQuery, error } = usePlanMode()
      await executePlanQuery('Test')
      expect(error.value).toContain('warte')
    })

    it('should handle server errors (5xx)', async () => {
      vi.mocked(api.post).mockRejectedValue({
        response: { status: 500 },
        message: 'Server error',
      })

      const { executePlanQuery, error } = usePlanMode()
      await executePlanQuery('Test')
      expect(error.value).toContain('Server')
    })

    it('should reject when conversation is at max length', async () => {
      const { executePlanQuery, conversation, error } = usePlanMode()

      // Fill conversation to max
      for (let i = 0; i < MAX_CONVERSATION_MESSAGES; i++) {
        conversation.value.push({
          role: i % 2 === 0 ? 'user' : 'assistant',
          content: `Message ${i}`,
        })
      }

      const result = await executePlanQuery('New question')
      expect(result).toBe(false)
      expect(error.value).toContain('lang')
    })

    it('should store results when prompt is generated', async () => {
      vi.mocked(api.post).mockResolvedValue(
        mockAxiosResponse({
          success: true,
          message: 'Here is your prompt',
          has_generated_prompt: true,
          generated_prompt: 'Generated prompt text',
          suggested_mode: 'write',
        })
      )

      const { executePlanQuery, results } = usePlanMode()
      await executePlanQuery('Generate a prompt')
      expect(results.value).not.toBeNull()
      expect(results.value?.has_generated_prompt).toBe(true)
      expect(results.value?.generated_prompt).toBe('Generated prompt text')
    })

    it('should clear results when no prompt is generated', async () => {
      const { executePlanQuery, results } = usePlanMode()

      // First call generates a prompt
      vi.mocked(api.post).mockResolvedValueOnce(
        mockAxiosResponse({
          success: true,
          message: 'Prompt',
          has_generated_prompt: true,
          generated_prompt: 'Prompt text',
          suggested_mode: 'read',
        })
      )
      await executePlanQuery('Generate')
      expect(results.value).not.toBeNull()

      // Second call does not generate a prompt
      vi.mocked(api.post).mockResolvedValueOnce(
        mockAxiosResponse({
          success: true,
          message: 'Just a response',
          has_generated_prompt: false,
          generated_prompt: null,
          suggested_mode: null,
        })
      )
      await executePlanQuery('No prompt')
      expect(results.value).toBeNull()
    })
  })

  describe('validatePrompt', () => {
    it('should reject empty prompts', async () => {
      const { validatePrompt, error } = usePlanMode()
      const result = await validatePrompt('', 'read')
      expect(result).toBeNull()
      expect(error.value).toBeTruthy()
    })

    it('should return validation result on success', async () => {
      vi.mocked(api.post).mockResolvedValue(
        mockAxiosResponse({
          valid: true,
          mode: 'read',
          interpretation: { operation: 'search' },
          preview: 'Will search for entities',
          warnings: [],
          original_prompt: 'Find entities',
        })
      )

      const { validatePrompt, validationResult } = usePlanMode()
      const result = await validatePrompt('Find entities', 'read')

      expect(result).not.toBeNull()
      expect(result?.valid).toBe(true)
      expect(validationResult.value).toEqual(result)
    })

    it('should set validating during request', async () => {
      let resolveRequest: (value: unknown) => void
      const requestPromise = new Promise((resolve) => {
        resolveRequest = resolve
      })
      vi.mocked(api.post).mockReturnValue(requestPromise as Promise<unknown>)

      const { validatePrompt, validating } = usePlanMode()
      const validatePromise = validatePrompt('Test', 'read')

      expect(validating.value).toBe(true)

      resolveRequest!(
        mockAxiosResponse({
          valid: true,
          mode: 'read',
          interpretation: null,
          preview: null,
          warnings: [],
          original_prompt: 'Test',
        })
      )

      await validatePromise
      expect(validating.value).toBe(false)
    })

    it('should handle validation errors', async () => {
      vi.mocked(api.post).mockRejectedValue(new Error('Validation failed'))

      const { validatePrompt, error } = usePlanMode()
      const result = await validatePrompt('Test', 'write')

      expect(result).toBeNull()
      expect(error.value).toBeTruthy()
    })
  })

  describe('clearValidation', () => {
    it('should clear validation result', async () => {
      vi.mocked(api.post).mockResolvedValue(
        mockAxiosResponse({
          valid: true,
          mode: 'read',
          interpretation: null,
          preview: null,
          warnings: [],
          original_prompt: 'Test',
        })
      )

      const { validatePrompt, clearValidation, validationResult } = usePlanMode()
      await validatePrompt('Test', 'read')
      expect(validationResult.value).not.toBeNull()

      clearValidation()
      expect(validationResult.value).toBeNull()
    })
  })

  describe('reset', () => {
    it('should clear all state', async () => {
      vi.mocked(api.post).mockResolvedValue(
        mockAxiosResponse({
          success: true,
          message: 'Response',
          has_generated_prompt: true,
          generated_prompt: 'Prompt',
          suggested_mode: 'read',
        })
      )

      const { executePlanQuery, reset, conversation, results, error, loading, streaming } = usePlanMode()
      await executePlanQuery('Test')

      reset()

      expect(conversation.value).toEqual([])
      expect(results.value).toBeNull()
      expect(error.value).toBeNull()
      expect(loading.value).toBe(false)
      expect(streaming.value).toBe(false)
    })
  })

  describe('clearError', () => {
    it('should clear error state', async () => {
      const { executePlanQuery, clearError, error } = usePlanMode()
      await executePlanQuery('')
      expect(error.value).toBeTruthy()

      clearError()
      expect(error.value).toBeNull()
    })
  })

  describe('getDisplayConversation', () => {
    it('should return all messages when no limit', async () => {
      vi.mocked(api.post).mockResolvedValue(
        mockAxiosResponse({
          success: true,
          message: 'Response',
          has_generated_prompt: false,
          generated_prompt: null,
          suggested_mode: null,
        })
      )

      const { executePlanQuery, getDisplayConversation } = usePlanMode()
      await executePlanQuery('First')
      await executePlanQuery('Second')

      const messages = getDisplayConversation()
      expect(messages).toHaveLength(4) // 2 user + 2 assistant
    })

    it('should return limited messages when limit specified', async () => {
      vi.mocked(api.post).mockResolvedValue(
        mockAxiosResponse({
          success: true,
          message: 'Response',
          has_generated_prompt: false,
          generated_prompt: null,
          suggested_mode: null,
        })
      )

      const { executePlanQuery, getDisplayConversation } = usePlanMode()
      await executePlanQuery('First')
      await executePlanQuery('Second')
      await executePlanQuery('Third')

      const messages = getDisplayConversation(3)
      expect(messages).toHaveLength(3)
    })
  })

  describe('conversation trimming', () => {
    it('should trim conversation when exceeding threshold', async () => {
      vi.mocked(api.post).mockResolvedValue(
        mockAxiosResponse({
          success: true,
          message: 'Response',
          has_generated_prompt: false,
          generated_prompt: null,
          suggested_mode: null,
        })
      )

      const { executePlanQuery, conversation } = usePlanMode()

      // Fill conversation beyond trim threshold (TRIM_THRESHOLD = 25)
      // Trimming happens when length > TRIM_THRESHOLD, so we need 26+ messages
      for (let i = 0; i < TRIM_THRESHOLD + 1; i++) {
        conversation.value.push({
          role: i % 2 === 0 ? 'user' : 'assistant',
          content: `Message ${i}`,
        })
      }

      const lengthBeforeQuery = conversation.value.length

      // This should trigger trimming (trimConversation is called before API call)
      await executePlanQuery('New message')

      // Trimming should have reduced the conversation
      // After trimming: first message + (TRIM_TARGET - 1) recent messages
      // Then +2 for the new user message and assistant response
      // TRIM_TARGET is 20, so after trim: 1 + 19 = 20, then +2 = 22
      expect(conversation.value.length).toBeLessThan(lengthBeforeQuery)
    })
  })
})
