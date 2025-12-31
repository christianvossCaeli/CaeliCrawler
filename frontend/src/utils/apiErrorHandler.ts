/**
 * API Error Handler Utilities
 *
 * Centralized error handling for API calls to reduce code duplication
 * and ensure consistent error handling across the application.
 *
 * @module utils/apiErrorHandler
 *
 * ## Features
 * - Standardized try-catch patterns with `withApiErrorHandling()`
 * - Loading state management with `withLoadingState()`
 * - Combined pattern with `executeApiCall()`
 *
 * ## Usage
 * ```typescript
 * import { withApiErrorHandling, executeApiCall } from '@/utils/apiErrorHandler'
 *
 * // Simple error handling
 * const data = await withApiErrorHandling(
 *   () => api.fetchData(),
 *   { errorRef: error, fallbackMessage: 'Failed to fetch' }
 * )
 *
 * // With loading state
 * const result = await executeApiCall(
 *   () => api.saveData(payload),
 *   { errorRef: error, loadingRef: saving, fallbackMessage: 'Save failed' }
 * )
 * ```
 *
 * ## Error Types
 * Uses `getApiErrorMessage()` from `@/types/sources` for consistent
 * error message extraction from Axios/fetch responses.
 *
 * @see {@link @/types/sources} for API error types and helpers
 */

import type { Ref } from 'vue'
import { getApiErrorMessage } from '@/utils/errorMessage'

/**
 * Options for API error handling
 */
export interface ApiErrorHandlerOptions {
  /** Ref to store error message */
  errorRef: Ref<string | null>
  /** Fallback message if error extraction fails */
  fallbackMessage: string
  /** Whether to re-throw the error after handling (default: true) */
  rethrow?: boolean
  /** Callback to execute on error (before rethrow) */
  onError?: (error: unknown) => void
}

/**
 * Execute an async function with standardized error handling.
 * Reduces boilerplate by centralizing try-catch patterns.
 *
 * @template T - Return type of the async function
 * @param fn - Async function to execute
 * @param options - Error handling options
 * @returns Promise resolving to result or null (if rethrow=false)
 * @throws Re-throws the error if rethrow=true (default)
 *
 * @example
 * ```typescript
 * // With rethrow (default) - caller handles the error
 * try {
 *   const result = await withApiErrorHandling(
 *     () => adminApi.getSources(params),
 *     { errorRef: error, fallbackMessage: 'Failed to load sources' }
 *   )
 * } catch (e) {
 *   // Error already stored in errorRef
 * }
 *
 * // Without rethrow - returns null on error
 * const result = await withApiErrorHandling(
 *   () => api.getData(),
 *   { errorRef: error, fallbackMessage: 'Failed', rethrow: false }
 * )
 * if (result) { /* success *\/ }
 * ```
 */
export async function withApiErrorHandling<T>(
  fn: () => Promise<T>,
  options: ApiErrorHandlerOptions
): Promise<T | null> {
  const { errorRef, fallbackMessage, rethrow = true, onError } = options

  try {
    errorRef.value = null
    return await fn()
  } catch (error: unknown) {
    errorRef.value = getApiErrorMessage(error, fallbackMessage)

    if (onError) {
      onError(error)
    }

    if (rethrow) {
      throw error
    }

    return null
  }
}

/**
 * Execute an async function with loading state management.
 * Automatically sets loading=true before and loading=false after (in finally).
 *
 * @template T - Return type of the async function
 * @param fn - Async function to execute
 * @param loadingRef - Ref<boolean> to track loading state
 * @returns Promise resolving to the function result
 * @throws Re-throws any error from fn (loading state is reset in finally)
 *
 * @example
 * ```typescript
 * // Simple usage
 * await withLoadingState(() => fetchData(), loadingRef)
 *
 * // With error handling
 * try {
 *   await withLoadingState(() => api.save(data), saving)
 * } catch (e) {
 *   // saving.value is false here
 * }
 * ```
 */
export async function withLoadingState<T>(
  fn: () => Promise<T>,
  loadingRef: Ref<boolean>
): Promise<T> {
  loadingRef.value = true
  try {
    return await fn()
  } finally {
    loadingRef.value = false
  }
}

/**
 * Combined error handling with loading state.
 * Most common pattern for API calls - combines withApiErrorHandling and withLoadingState.
 *
 * @template T - Return type of the async function
 * @param fn - Async function to execute
 * @param options - Combined options (error handling + loading ref)
 * @returns Promise resolving to result or null on error
 *
 * @example
 * ```typescript
 * // CRUD operation with loading indicator
 * const result = await executeApiCall(
 *   () => adminApi.createSource(data),
 *   {
 *     errorRef: error,
 *     loadingRef: saving,
 *     fallbackMessage: 'Failed to create source'
 *   }
 * )
 *
 * if (result) {
 *   // Success - result contains the created source
 *   showSuccessMessage()
 * }
 * // Error is stored in error.value, saving.value is false
 * ```
 */
export async function executeApiCall<T>(
  fn: () => Promise<T>,
  options: ApiErrorHandlerOptions & { loadingRef: Ref<boolean> }
): Promise<T | null> {
  const { loadingRef, ...errorOptions } = options

  return withLoadingState(
    () => withApiErrorHandling(fn, errorOptions),
    loadingRef
  )
}
