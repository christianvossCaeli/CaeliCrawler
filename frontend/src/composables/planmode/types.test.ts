/**
 * Tests for Plan Mode Types and Utilities
 */

import { describe, it, expect } from 'vitest'
import {
  getErrorDetail,
  asAxiosError,
  MAX_CONVERSATION_MESSAGES,
  TRIM_THRESHOLD,
  TRIM_TARGET,
} from './types'
import type { AxiosLikeError, PlanMessage, GeneratedPrompt, PlanModeResult, ValidationResult, SSEEvent } from './types'

describe('Plan Mode Types', () => {
  describe('constants', () => {
    it('should have correct MAX_CONVERSATION_MESSAGES', () => {
      expect(MAX_CONVERSATION_MESSAGES).toBe(20)
    })

    it('should have correct TRIM_THRESHOLD', () => {
      expect(TRIM_THRESHOLD).toBe(25)
    })

    it('should have correct TRIM_TARGET', () => {
      expect(TRIM_TARGET).toBe(20)
    })

    it('TRIM_TARGET should be less than TRIM_THRESHOLD', () => {
      expect(TRIM_TARGET).toBeLessThan(TRIM_THRESHOLD)
    })
  })

  describe('getErrorDetail', () => {
    it('should extract detail from axios response', () => {
      const err: AxiosLikeError = {
        response: {
          status: 400,
          data: { detail: 'Bad request message' },
        },
      }
      expect(getErrorDetail(err)).toBe('Bad request message')
    })

    it('should fall back to message if no response detail', () => {
      const err: AxiosLikeError = {
        message: 'Network error',
      }
      expect(getErrorDetail(err)).toBe('Network error')
    })

    it('should prefer response detail over message', () => {
      const err: AxiosLikeError = {
        response: { data: { detail: 'Server detail' } },
        message: 'Generic message',
      }
      expect(getErrorDetail(err)).toBe('Server detail')
    })

    it('should return undefined for null', () => {
      expect(getErrorDetail(null)).toBeUndefined()
    })

    it('should return undefined for undefined', () => {
      expect(getErrorDetail(undefined)).toBeUndefined()
    })

    it('should return string value for string input', () => {
      // Strings are valid error messages, so they're returned as-is
      expect(getErrorDetail('error')).toBe('error')
    })

    it('should return undefined for non-string primitive types', () => {
      expect(getErrorDetail(123)).toBeUndefined()
      expect(getErrorDetail(true)).toBeUndefined()
    })

    it('should handle empty object', () => {
      expect(getErrorDetail({})).toBeUndefined()
    })
  })

  describe('asAxiosError', () => {
    it('should cast object to AxiosLikeError', () => {
      const err = { response: { status: 500 }, message: 'Error' }
      const result = asAxiosError(err)
      expect(result).toBe(err)
      expect(result?.response?.status).toBe(500)
    })

    it('should return null for null', () => {
      expect(asAxiosError(null)).toBeNull()
    })

    it('should return null for undefined', () => {
      expect(asAxiosError(undefined)).toBeNull()
    })

    it('should return null for primitive types', () => {
      expect(asAxiosError('error')).toBeNull()
      expect(asAxiosError(123)).toBeNull()
      expect(asAxiosError(true)).toBeNull()
    })

    it('should handle Error objects', () => {
      const err = new Error('Test error')
      const result = asAxiosError(err)
      expect(result).not.toBeNull()
      expect(result?.message).toBe('Test error')
    })
  })

  describe('type interfaces', () => {
    it('should allow valid PlanMessage', () => {
      const message: PlanMessage = {
        role: 'user',
        content: 'Hello',
        timestamp: new Date(),
        isStreaming: false,
      }
      expect(message.role).toBe('user')
      expect(message.content).toBe('Hello')
    })

    it('should allow PlanMessage without optional fields', () => {
      const message: PlanMessage = {
        role: 'assistant',
        content: 'Response',
      }
      expect(message.timestamp).toBeUndefined()
      expect(message.isStreaming).toBeUndefined()
    })

    it('should allow valid GeneratedPrompt', () => {
      const prompt: GeneratedPrompt = {
        prompt: 'Show all entities',
        suggested_mode: 'read',
      }
      expect(prompt.prompt).toBe('Show all entities')
      expect(prompt.suggested_mode).toBe('read')
    })

    it('should allow GeneratedPrompt without suggested_mode', () => {
      const prompt: GeneratedPrompt = {
        prompt: 'Some prompt',
      }
      expect(prompt.suggested_mode).toBeUndefined()
    })

    it('should allow valid PlanModeResult', () => {
      const result: PlanModeResult = {
        success: true,
        message: 'Here is your prompt',
        has_generated_prompt: true,
        generated_prompt: 'Show all municipalities',
        suggested_mode: 'read',
        mode: 'plan',
      }
      expect(result.success).toBe(true)
      expect(result.has_generated_prompt).toBe(true)
    })

    it('should allow PlanModeResult with null values', () => {
      const result: PlanModeResult = {
        success: true,
        message: 'No prompt generated',
        has_generated_prompt: false,
        generated_prompt: null,
        suggested_mode: null,
        mode: 'plan',
      }
      expect(result.generated_prompt).toBeNull()
      expect(result.suggested_mode).toBeNull()
    })

    it('should allow valid ValidationResult', () => {
      const result: ValidationResult = {
        valid: true,
        mode: 'read',
        interpretation: { operation: 'search' },
        preview: 'Will search for entities',
        warnings: [],
        original_prompt: 'Find entities',
      }
      expect(result.valid).toBe(true)
      expect(result.warnings).toHaveLength(0)
    })

    it('should allow ValidationResult with warnings', () => {
      const result: ValidationResult = {
        valid: true,
        mode: 'write',
        interpretation: null,
        preview: null,
        warnings: ['This will modify data', 'Make sure you want this'],
        original_prompt: 'Delete entity',
      }
      expect(result.warnings).toHaveLength(2)
    })

    it('should allow valid SSEEvent types', () => {
      const startEvent: SSEEvent = { event: 'start' }
      const chunkEvent: SSEEvent = { event: 'chunk', data: 'Hello' }
      const doneEvent: SSEEvent = { event: 'done' }
      const errorEvent: SSEEvent = { event: 'error', data: 'Failed', partial: true }

      expect(startEvent.event).toBe('start')
      expect(chunkEvent.data).toBe('Hello')
      expect(doneEvent.event).toBe('done')
      expect(errorEvent.partial).toBe(true)
    })
  })
})
