import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useLogger } from './useLogger'
import { useSnackbar } from './useSnackbar'

/**
 * Type-safe error extraction from unknown errors
 */
function extractErrorMessage(error: unknown): string {
  if (error && typeof error === 'object') {
    const e = error as {
      response?: { data?: { detail?: string; message?: string; error?: string } }
      message?: string
    }
    if (e.response?.data?.error) {
      return e.response.data.error
    }
    if (e.response?.data?.detail) {
      return e.response.data.detail
    }
    if (e.response?.data?.message) {
      return e.response.data.message
    }
    if (e.message) {
      return e.message
    }
  }
  if (error instanceof Error) {
    return error.message
  }
  return 'Unknown error'
}

/**
 * Simple helper to extract error message - for use in catch blocks
 * @example
 * ```ts
 * try {
 *   await api.post(...)
 * } catch (error) {
 *   showMessage(getErrorMessage(error) || t('fallback'), 'error')
 * }
 * ```
 */
export function getErrorMessage(error: unknown): string | undefined {
  if (error && typeof error === 'object') {
    const e = error as {
      response?: { data?: { detail?: string; message?: string; error?: string } }
      message?: string
    }
    return e.response?.data?.error || e.response?.data?.detail || e.response?.data?.message || e.message
  }
  if (error instanceof Error) {
    return error.message
  }
  return undefined
}

/**
 * Check if error is a network/connectivity error
 */
function isNetworkError(error: unknown): boolean {
  if (error && typeof error === 'object') {
    const e = error as { code?: string; message?: string }
    return (
      e.code === 'ERR_NETWORK' ||
      e.message?.includes('Network Error') ||
      e.message?.includes('Failed to fetch') ||
      false
    )
  }
  return false
}

/**
 * Check if error is an authentication error
 */
function isAuthError(error: unknown): boolean {
  if (error && typeof error === 'object') {
    const e = error as { response?: { status?: number } }
    return e.response?.status === 401 || e.response?.status === 403
  }
  return false
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
// Note: getErrorMessage is already exported at definition, not re-exported here
export { extractErrorMessage, isNetworkError, isAuthError }
