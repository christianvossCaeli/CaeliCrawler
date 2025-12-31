/**
 * Error Handler Composable - Extended API Error Handling
 *
 * This composable extends useApiErrorHandler with additional features:
 * - Success feedback with snackbar
 * - Context-specific error handling
 * - Pre-configured error messages
 *
 * For most use cases, prefer useApiErrorHandler directly.
 */

import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSnackbar } from './useSnackbar'
import { useLogger } from '@/composables/useLogger'

// Re-export all utilities from centralized module
export {
  extractErrorMessage,
  getErrorMessage,
  getStatusCode,
  isApiError,
  isNetworkError,
  isAuthError,
  isForbiddenError,
  isNotFoundError,
  isValidationError,
  isServerError,
  hasStatus,
} from '@/utils/errorMessage'

import {
  extractErrorMessage,
  isNetworkError,
  isAuthError,
  isForbiddenError,
  isNotFoundError,
  isValidationError,
  isServerError,
  getStatusCode,
} from '@/utils/errorMessage'

const logger = useLogger('useErrorHandler')

/**
 * API Error structure (for type compatibility)
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
   * Handle an error with consistent behavior
   */
  function handleError(error: unknown, options: ErrorHandlerOptions = {}): string {
    const opts = { ...DEFAULT_OPTIONS, ...options }
    const message = extractErrorMessage(error) || opts.defaultMessage || t('common.error', 'An error occurred')

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

    // Error extraction (from centralized utility)
    extractErrorMessage,
    getStatusCode,

    // Error type checks (from centralized utility)
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
