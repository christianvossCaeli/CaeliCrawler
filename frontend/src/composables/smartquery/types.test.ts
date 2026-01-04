/**
 * Tests for Smart Query types and utilities
 */

import { describe, it, expect } from 'vitest'
import { getErrorDetail } from './types'

describe('getErrorDetail', () => {
  it('should extract detail from axios-like response', () => {
    const error = {
      response: {
        data: {
          detail: 'Specific error message',
        },
      },
    }

    expect(getErrorDetail(error)).toBe('Specific error message')
  })

  it('should fall back to message property', () => {
    const error = {
      message: 'Error message',
    }

    expect(getErrorDetail(error)).toBe('Error message')
  })

  it('should extract message from Error instances', () => {
    const error = new Error('Standard error')

    expect(getErrorDetail(error)).toBe('Standard error')
  })

  it('should handle string errors and non-objects', () => {
    // Strings are valid error messages, returned as-is
    expect(getErrorDetail('string error')).toBe('string error')
    // Non-string primitives fall back to 'Unknown error'
    expect(getErrorDetail(123)).toBe('Unknown error')
    expect(getErrorDetail(null)).toBe('Unknown error')
    expect(getErrorDetail(undefined)).toBe('Unknown error')
  })

  it('should prefer response.data.detail over message', () => {
    const error = {
      response: {
        data: {
          detail: 'API error',
        },
      },
      message: 'Generic message',
    }

    expect(getErrorDetail(error)).toBe('API error')
  })
})
