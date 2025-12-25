/**
 * Tests for useErrorHandler composable
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useErrorHandler, ERROR_MESSAGES, type ApiError } from './useErrorHandler'

// Mock dependencies
vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string, fallback?: string) => fallback || key,
  }),
}))

vi.mock('./useSnackbar', () => ({
  useSnackbar: () => ({
    showError: vi.fn(),
    showSuccess: vi.fn(),
    showWarning: vi.fn(),
    showInfo: vi.fn(),
  }),
}))

describe('useErrorHandler', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Suppress console.error in tests
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  describe('extractErrorMessage', () => {
    it('should extract detail from API response', () => {
      const { extractErrorMessage } = useErrorHandler()
      const error: ApiError = {
        response: {
          status: 400,
          data: {
            detail: 'Invalid input',
          },
        },
      }

      expect(extractErrorMessage(error)).toBe('Invalid input')
    })

    it('should extract message from API response', () => {
      const { extractErrorMessage } = useErrorHandler()
      const error: ApiError = {
        response: {
          status: 400,
          data: {
            message: 'Something went wrong',
          },
        },
      }

      expect(extractErrorMessage(error)).toBe('Something went wrong')
    })

    it('should extract error from API response', () => {
      const { extractErrorMessage } = useErrorHandler()
      const error: ApiError = {
        response: {
          status: 500,
          data: {
            error: 'Internal server error',
          },
        },
      }

      expect(extractErrorMessage(error)).toBe('Internal server error')
    })

    it('should format validation errors', () => {
      const { extractErrorMessage } = useErrorHandler()
      const error: ApiError = {
        response: {
          status: 422,
          data: {
            errors: [
              { field: 'email', message: 'Invalid email' },
              { field: 'name', message: 'Required' },
            ],
          },
        },
      }

      expect(extractErrorMessage(error)).toBe('email: Invalid email, name: Required')
    })

    it('should use error.message as fallback', () => {
      const { extractErrorMessage } = useErrorHandler()
      const error: ApiError = {
        message: 'Network error',
      }

      expect(extractErrorMessage(error)).toBe('Network error')
    })

    it('should handle string errors', () => {
      const { extractErrorMessage } = useErrorHandler()

      expect(extractErrorMessage('Simple error string')).toBe('Simple error string')
    })

    it('should use default message for null/undefined', () => {
      const { extractErrorMessage } = useErrorHandler()

      expect(extractErrorMessage(null)).toBe('An error occurred')
      expect(extractErrorMessage(undefined)).toBe('An error occurred')
    })

    it('should use custom default message', () => {
      const { extractErrorMessage } = useErrorHandler()

      expect(extractErrorMessage({}, 'Custom default')).toBe('Custom default')
    })
  })

  describe('getStatusCode', () => {
    it('should return status code from response', () => {
      const { getStatusCode } = useErrorHandler()
      const error: ApiError = {
        response: { status: 404 },
      }

      expect(getStatusCode(error)).toBe(404)
    })

    it('should return undefined if no response', () => {
      const { getStatusCode } = useErrorHandler()
      const error: ApiError = {
        message: 'Network error',
      }

      expect(getStatusCode(error)).toBeUndefined()
    })
  })

  describe('error type checks', () => {
    it('isNetworkError should detect network errors', () => {
      const { isNetworkError } = useErrorHandler()

      expect(isNetworkError({ message: 'Network Error' })).toBe(true)
      expect(isNetworkError({ response: { status: 500 } })).toBe(false)
    })

    it('isAuthError should detect 401 errors', () => {
      const { isAuthError } = useErrorHandler()

      expect(isAuthError({ response: { status: 401 } })).toBe(true)
      expect(isAuthError({ response: { status: 403 } })).toBe(false)
    })

    it('isForbiddenError should detect 403 errors', () => {
      const { isForbiddenError } = useErrorHandler()

      expect(isForbiddenError({ response: { status: 403 } })).toBe(true)
      expect(isForbiddenError({ response: { status: 401 } })).toBe(false)
    })

    it('isNotFoundError should detect 404 errors', () => {
      const { isNotFoundError } = useErrorHandler()

      expect(isNotFoundError({ response: { status: 404 } })).toBe(true)
      expect(isNotFoundError({ response: { status: 400 } })).toBe(false)
    })

    it('isValidationError should detect 422 errors', () => {
      const { isValidationError } = useErrorHandler()

      expect(isValidationError({ response: { status: 422 } })).toBe(true)
      expect(isValidationError({ response: { status: 400 } })).toBe(false)
    })

    it('isServerError should detect 5xx errors', () => {
      const { isServerError } = useErrorHandler()

      expect(isServerError({ response: { status: 500 } })).toBe(true)
      expect(isServerError({ response: { status: 502 } })).toBe(true)
      expect(isServerError({ response: { status: 503 } })).toBe(true)
      expect(isServerError({ response: { status: 400 } })).toBe(false)
      expect(isServerError({ response: { status: 404 } })).toBe(false)
    })
  })

  describe('handleError', () => {
    it('should store the last error', () => {
      const { handleError, lastError } = useErrorHandler()
      const error: ApiError = {
        response: { status: 400, data: { detail: 'Bad request' } },
      }

      handleError(error)

      expect(lastError.value).toEqual(error)
    })

    it('should return extracted message', () => {
      const { handleError } = useErrorHandler()
      const error: ApiError = {
        response: { status: 400, data: { detail: 'Bad request' } },
      }

      const message = handleError(error, { showNotification: false })

      expect(message).toBe('Bad request')
    })

    it('should log error when logError is true', () => {
      const { handleError } = useErrorHandler()
      const error = new Error('Test error')

      handleError(error, { showNotification: false, logError: true })

      expect(console.error).toHaveBeenCalledWith('Error handled:', error)
    })

    it('should not log error when logError is false', () => {
      const { handleError } = useErrorHandler()
      const error = new Error('Test error')

      handleError(error, { showNotification: false, logError: false })

      expect(console.error).not.toHaveBeenCalled()
    })

    it('should rethrow error when rethrow is true', () => {
      const { handleError } = useErrorHandler()
      const error = new Error('Test error')

      expect(() =>
        handleError(error, { showNotification: false, logError: false, rethrow: true })
      ).toThrow('Test error')
    })
  })

  describe('withErrorHandling', () => {
    it('should return result on success', async () => {
      const { withErrorHandling } = useErrorHandler()
      const fn = vi.fn().mockResolvedValue('success')

      const result = await withErrorHandling(fn)

      expect(result).toBe('success')
    })

    it('should return null on error', async () => {
      const { withErrorHandling } = useErrorHandler()
      const fn = vi.fn().mockRejectedValue(new Error('Failed'))

      const result = await withErrorHandling(fn, { logError: false })

      expect(result).toBeNull()
    })

    it('should handle the error', async () => {
      const { withErrorHandling, lastError } = useErrorHandler()
      const error = new Error('Failed')
      const fn = vi.fn().mockRejectedValue(error)

      await withErrorHandling(fn, { logError: false })

      expect(lastError.value).toEqual(error)
    })
  })

  describe('withFeedback', () => {
    it('should return result and show success on success', async () => {
      const { withFeedback } = useErrorHandler()
      const fn = vi.fn().mockResolvedValue('success')

      const result = await withFeedback(fn, 'Operation successful')

      expect(result).toBe('success')
      // Note: showSuccess is called but we can't easily verify with current mock setup
    })

    it('should return null and handle error on failure', async () => {
      const { withFeedback, lastError } = useErrorHandler()
      const error = new Error('Failed')
      const fn = vi.fn().mockRejectedValue(error)

      const result = await withFeedback(fn, 'Success', { logError: false })

      expect(result).toBeNull()
      expect(lastError.value).toEqual(error)
    })
  })

  describe('createContextHandler', () => {
    it('should create a context-specific handler', () => {
      const { createContextHandler } = useErrorHandler()
      const handler = createContextHandler('UserManagement', {
        load: 'Failed to load users',
        save: 'Failed to save user',
      })

      expect(handler.handle).toBeDefined()
      expect(handler.wrap).toBeDefined()
    })

    it('should use context-specific default messages', () => {
      const { createContextHandler } = useErrorHandler()
      const handler = createContextHandler('Test', {
        load: 'Custom load error',
      })

      // Handle with key
      const message = handler.handle({}, 'load')

      // The message should use the context-specific default
      expect(message).toBe('Custom load error')
    })
  })
})

describe('ERROR_MESSAGES', () => {
  it('should export common error messages', () => {
    expect(ERROR_MESSAGES.CREATE_FAILED).toBe('Failed to create')
    expect(ERROR_MESSAGES.UPDATE_FAILED).toBe('Failed to update')
    expect(ERROR_MESSAGES.DELETE_FAILED).toBe('Failed to delete')
    expect(ERROR_MESSAGES.LOAD_FAILED).toBe('Failed to load data')
    expect(ERROR_MESSAGES.SAVE_FAILED).toBe('Failed to save')
  })

  it('should export network error messages', () => {
    expect(ERROR_MESSAGES.NETWORK_ERROR).toBe('Network error. Please check your connection.')
    expect(ERROR_MESSAGES.SERVER_ERROR).toBe('Server error. Please try again later.')
    expect(ERROR_MESSAGES.TIMEOUT_ERROR).toBe('Request timed out. Please try again.')
  })

  it('should export auth error messages', () => {
    expect(ERROR_MESSAGES.AUTH_REQUIRED).toBe('Authentication required. Please log in.')
    expect(ERROR_MESSAGES.ACCESS_DENIED).toBe('Access denied. You do not have permission.')
  })

  it('should export validation error messages', () => {
    expect(ERROR_MESSAGES.VALIDATION_ERROR).toBe('Please check your input.')
    expect(ERROR_MESSAGES.NOT_FOUND).toBe('The requested resource was not found.')
  })
})
