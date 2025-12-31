import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useLogger } from './useLogger'
import { useSnackbar } from './useSnackbar'

// Import from centralized utility
import {
  extractErrorMessage,
  getErrorMessage,
  isNetworkError,
  isApiError,
  isAuthError as isAuthErrorUtil,
  isForbiddenError,
  isNotFoundError,
  isValidationError,
  isServerError,
  hasStatus,
} from '@/utils/errorMessage'

// Re-export utilities for backward compatibility
export {
  getErrorMessage,
  isNetworkError,
  isApiError,
  isForbiddenError,
  isNotFoundError,
  isValidationError,
  isServerError,
  hasStatus,
}

/**
 * Check if error is an authentication error (401 or 403)
 */
function isAuthError(error: unknown): boolean {
  return isAuthErrorUtil(error) || isForbiddenError(error)
}

export interface ApiErrorHandlerOptions {
  /** Log prefix for the component/module using this handler */
  logPrefix?: string
  /** Show snackbar notifications on error */
  showNotifications?: boolean
  /** Rethrow errors after handling */
  rethrow?: boolean
}

export interface HandleErrorOptions {
  /** Custom error message to show (overrides extracted message) */
  message?: string
  /** i18n key for error message */
  messageKey?: string
  /** Show notification for this error */
  notify?: boolean
  /** Log this error */
  log?: boolean
  /** Rethrow this error */
  rethrow?: boolean
}

/**
 * useApiErrorHandler - Centralized API error handling
 *
 * Provides consistent error handling for API calls with:
 * - Type-safe error extraction
 * - Automatic logging
 * - Optional snackbar notifications
 * - Network/auth error detection
 *
 * @example
 * ```ts
 * const { handleError, wrapAsync, error, clearError } = useApiErrorHandler({
 *   logPrefix: 'EntityStore',
 *   showNotifications: true,
 * })
 *
 * // Option 1: Wrap entire async function
 * const loadData = wrapAsync(async () => {
 *   const response = await api.get('/data')
 *   return response.data
 * }, { messageKey: 'errors.loadFailed' })
 *
 * // Option 2: Handle errors manually
 * try {
 *   await api.post('/data', payload)
 * } catch (e) {
 *   handleError(e, { messageKey: 'errors.saveFailed' })
 * }
 * ```
 */
export function useApiErrorHandler(options: ApiErrorHandlerOptions = {}) {
  const { logPrefix = 'API', showNotifications = true, rethrow = false } = options

  const { t } = useI18n()
  const logger = useLogger(logPrefix)
  const { showError } = useSnackbar()

  const error = ref<string | null>(null)

  /**
   * Clear current error state
   */
  function clearError() {
    error.value = null
  }

  /**
   * Handle an error with consistent logging and notifications
   */
  function handleError(err: unknown, opts: HandleErrorOptions = {}): string {
    const {
      message,
      messageKey,
      notify = showNotifications,
      log = true,
      rethrow: shouldRethrow = rethrow,
    } = opts

    // Extract error message
    const extractedMessage = extractErrorMessage(err)
    const finalMessage = message || (messageKey ? t(messageKey) : extractedMessage)

    // Update error state
    error.value = finalMessage

    // Log error
    if (log) {
      if (isNetworkError(err)) {
        logger.warn('Network error:', extractedMessage)
      } else if (isAuthError(err)) {
        logger.warn('Authentication error:', extractedMessage)
      } else {
        logger.error('API error:', err)
      }
    }

    // Show notification
    if (notify) {
      showError(finalMessage)
    }

    // Rethrow if requested
    if (shouldRethrow) {
      throw err
    }

    return finalMessage
  }

  /**
   * Wrap an async function with error handling
   */
  function wrapAsync<T, Args extends unknown[]>(
    fn: (...args: Args) => Promise<T>,
    opts: HandleErrorOptions = {}
  ): (...args: Args) => Promise<T | undefined> {
    return async (...args: Args): Promise<T | undefined> => {
      clearError()
      try {
        return await fn(...args)
      } catch (e) {
        handleError(e, opts)
        return undefined
      }
    }
  }

  /**
   * Execute an async function with error handling (inline version)
   */
  async function tryAsync<T>(
    fn: () => Promise<T>,
    opts: HandleErrorOptions = {}
  ): Promise<T | undefined> {
    clearError()
    try {
      return await fn()
    } catch (e) {
      handleError(e, opts)
      return undefined
    }
  }

  return {
    // State
    error,

    // Methods
    clearError,
    handleError,
    wrapAsync,
    tryAsync,

    // Utilities
    extractErrorMessage,
    isNetworkError,
    isAuthError,
  }
}

// Export utility functions for use outside composable
// Note: Most utilities are already re-exported above from @/utils/errorMessage
// isAuthError is exported here since it's a local function combining 401 and 403 checks
export { extractErrorMessage, isAuthError }
