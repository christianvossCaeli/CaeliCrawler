/**
 * API Error Handler Composable
 *
 * @deprecated Use `useErrorHandler` from '@/composables/useErrorHandler' for composable error handling,
 * or import utilities directly from '@/utils/errorMessage'.
 *
 * Migration guide:
 * ```ts
 * // Before:
 * import { getErrorMessage } from '@/composables/useApiErrorHandler'
 *
 * // After (for utilities):
 * import { getErrorMessage } from '@/utils/errorMessage'
 *
 * // After (for composable with snackbar):
 * import { useErrorHandler } from '@/composables/useErrorHandler'
 * ```
 */

// Re-export all utilities from centralized module for backward compatibility
export {
  extractErrorMessage,
  getErrorMessage,
  getApiErrorMessage,
  isApiError,
  isNetworkError,
  isAuthError,
  isForbiddenError,
  isNotFoundError,
  isValidationError,
  isServerError,
  hasStatus,
  getStatusCode,
  extractFieldErrors,
  isRetryableError,
} from '@/utils/errorMessage'

// Re-export useErrorHandler as useApiErrorHandler for backward compatibility
export { useErrorHandler as useApiErrorHandler } from './useErrorHandler'
