import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSnackbar } from './useSnackbar'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger('useErrorHandler')

/**
 * API Error structure
 */
export interface ApiError {
  response?: {
    status?: number
    data?: {
      detail?: string
      message?: string
      error?: string
      errors?: Array<{ field: string; message: string }>
    }
  }
  message?: string
}

/**
 * Error handler options
 */
export interface ErrorHandlerOptions {
  /** Show snackbar notification on error */
  showNotification?: boolean
  /** Log error to console */
  logError?: boolean
  /** Default error message if none can be extracted */
  defaultMessage?: string
  /** Rethrow error after handling */
  rethrow?: boolean
}

const DEFAULT_OPTIONS: ErrorHandlerOptions = {
  showNotification: true,
  logError: true,
  defaultMessage: 'An error occurred',
  rethrow: false,
}

/**
 * Composable for consistent error handling across components
 *
 * Provides utilities for:
 * - Extracting error messages from API responses
 * - Displaying error notifications
 * - Logging errors
 * - Wrapping async operations with error handling
 */
export function useErrorHandler() {
  const { t } = useI18n()
  const { showError, showSuccess, showWarning, showInfo } = useSnackbar()

  // Track the last error for debugging
  const lastError = ref<ApiError | null>(null)

  /**
   * Extract error message from API error response
   */
  function extractErrorMessage(error: unknown, defaultMessage?: string): string {
    const fallback = defaultMessage || t('common.error', 'An error occurred')

    if (!error) return fallback

    const apiError = error as ApiError

    // Check for structured API response
    if (apiError.response?.data) {
      const data = apiError.response.data
      // Try different error message fields
      if (data.detail) return data.detail
      if (data.message) return data.message
      if (data.error) return data.error
      // Check for validation errors
      if (data.errors && Array.isArray(data.errors)) {
        return data.errors.map((e) => `${e.field}: ${e.message}`).join(', ')
      }
    }

    // Check for plain message
    if (apiError.message) return apiError.message

    // Check if error is a string
    if (typeof error === 'string') return error

    return fallback
  }

  /**
   * Get HTTP status code from error
   */
  function getStatusCode(error: unknown): number | undefined {
    const apiError = error as ApiError
    return apiError.response?.status
  }

  /**
   * Check if error is a network error
   */
  function isNetworkError(error: unknown): boolean {
    const apiError = error as ApiError
    return !apiError.response && !!apiError.message
  }

  /**
   * Check if error is an authentication error (401)
   */
  function isAuthError(error: unknown): boolean {
    return getStatusCode(error) === 401
  }

  /**
   * Check if error is a forbidden error (403)
   */
  function isForbiddenError(error: unknown): boolean {
    return getStatusCode(error) === 403
  }

  /**
   * Check if error is a not found error (404)
   */
  function isNotFoundError(error: unknown): boolean {
    return getStatusCode(error) === 404
  }

  /**
   * Check if error is a validation error (422)
   */
  function isValidationError(error: unknown): boolean {
    return getStatusCode(error) === 422
  }

  /**
   * Check if error is a server error (5xx)
   */
  function isServerError(error: unknown): boolean {
    const status = getStatusCode(error)
    return status !== undefined && status >= 500
  }

  /**
   * Handle an error with consistent behavior
   */
  function handleError(error: unknown, options: ErrorHandlerOptions = {}): string {
    const opts = { ...DEFAULT_OPTIONS, ...options }
    const message = extractErrorMessage(error, opts.defaultMessage)

    lastError.value = error as ApiError

    if (opts.logError) {
      logger.error('Error handled:', error)
    }

    if (opts.showNotification) {
      showError(message)
    }

    if (opts.rethrow) {
      throw error
    }

    return message
  }

  /**
   * Wrap an async function with error handling
   */
  async function withErrorHandling<T>(
    fn: () => Promise<T>,
    options: ErrorHandlerOptions = {}
  ): Promise<T | null> {
    try {
      return await fn()
    } catch (error) {
      handleError(error, options)
      return null
    }
  }

  /**
   * Wrap an async function with error handling and success message
   */
  async function withFeedback<T>(
    fn: () => Promise<T>,
    successMessage: string,
    errorOptions: ErrorHandlerOptions = {}
  ): Promise<T | null> {
    try {
      const result = await fn()
      showSuccess(successMessage)
      return result
    } catch (error) {
      handleError(error, errorOptions)
      return null
    }
  }

  /**
   * Create an error handler for a specific context
   */
  function createContextHandler(context: string, defaultMessages?: Record<string, string>) {
    return {
      handle: (error: unknown, key?: string) => {
        const defaultMessage = key && defaultMessages ? defaultMessages[key] : undefined
        return handleError(error, {
          defaultMessage: defaultMessage || `Error in ${context}`,
          logError: true,
        })
      },
      wrap: <T>(fn: () => Promise<T>, key?: string) => {
        const defaultMessage = key && defaultMessages ? defaultMessages[key] : undefined
        return withErrorHandling(fn, { defaultMessage })
      },
    }
  }

  return {
    // State
    lastError,

    // Error extraction
    extractErrorMessage,
    getStatusCode,

    // Error type checks
    isNetworkError,
    isAuthError,
    isForbiddenError,
    isNotFoundError,
    isValidationError,
    isServerError,

    // Error handling
    handleError,
    withErrorHandling,
    withFeedback,
    createContextHandler,

    // Re-export snackbar methods for convenience
    showError,
    showSuccess,
    showWarning,
    showInfo,
  }
}

/**
 * Pre-configured error messages for common operations
 */
export const ERROR_MESSAGES = {
  // CRUD operations
  CREATE_FAILED: 'Failed to create',
  UPDATE_FAILED: 'Failed to update',
  DELETE_FAILED: 'Failed to delete',
  LOAD_FAILED: 'Failed to load data',
  SAVE_FAILED: 'Failed to save',

  // Network
  NETWORK_ERROR: 'Network error. Please check your connection.',
  SERVER_ERROR: 'Server error. Please try again later.',
  TIMEOUT_ERROR: 'Request timed out. Please try again.',

  // Auth
  AUTH_REQUIRED: 'Authentication required. Please log in.',
  ACCESS_DENIED: 'Access denied. You do not have permission.',

  // Validation
  VALIDATION_ERROR: 'Please check your input.',
  NOT_FOUND: 'The requested resource was not found.',
}
