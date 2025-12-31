/**
 * Centralized error message extraction utilities.
 *
 * This module provides a single source of truth for extracting user-friendly
 * error messages from various error types (API errors, native Errors, etc.).
 *
 * @module utils/errorMessage
 */

/**
 * Type guard for API/Axios errors
 */
interface ApiErrorLike {
  response?: {
    data?: {
      detail?: string
      message?: string
      error?: string
    }
    status?: number
  }
  message?: string
  code?: string
  isAxiosError?: boolean
}

/**
 * Check if error looks like an API error (has response or axios properties)
 */
export function isApiError(error: unknown): error is ApiErrorLike {
  return (
    error !== null &&
    typeof error === 'object' &&
    ('response' in error || 'message' in error || 'isAxiosError' in error)
  )
}

/**
 * Check if error is a network/connectivity error
 */
export function isNetworkError(error: unknown): boolean {
  if (!isApiError(error)) return false
  return (
    error.code === 'ERR_NETWORK' ||
    error.message?.includes('Network Error') ||
    error.message?.includes('Failed to fetch') ||
    !error.response
  )
}

/**
 * Check if error has a specific HTTP status code
 */
export function hasStatus(error: unknown, status: number): boolean {
  return isApiError(error) && error.response?.status === status
}

// Alias for backward compatibility with types/sources.ts
export const isHttpStatus = hasStatus

/**
 * Get HTTP status code from error
 */
export function getStatusCode(error: unknown): number | undefined {
  return isApiError(error) ? error.response?.status : undefined
}

/**
 * Check if error is an authentication error (401)
 */
export function isAuthError(error: unknown): boolean {
  return hasStatus(error, 401)
}

/**
 * Check if error is a forbidden error (403)
 */
export function isForbiddenError(error: unknown): boolean {
  return hasStatus(error, 403)
}

/**
 * Check if error is a not found error (404)
 */
export function isNotFoundError(error: unknown): boolean {
  return hasStatus(error, 404)
}

/**
 * Check if error is a validation error (422)
 */
export function isValidationError(error: unknown): boolean {
  return hasStatus(error, 422)
}

/**
 * Check if error is a server error (5xx)
 */
export function isServerError(error: unknown): boolean {
  const status = getStatusCode(error)
  return status !== undefined && status >= 500
}

/**
 * Extract error message from unknown error.
 *
 * Priority order:
 * 1. response.data.error
 * 2. response.data.detail
 * 3. response.data.message
 * 4. error.message
 * 5. "Unknown error" fallback
 *
 * @param error - Error to extract message from
 * @returns Extracted error message or "Unknown error"
 *
 * @example
 * ```typescript
 * try {
 *   await api.post('/endpoint', data)
 * } catch (e) {
 *   showError(extractErrorMessage(e))
 * }
 * ```
 */
export function extractErrorMessage(error: unknown): string {
  if (isApiError(error)) {
    const data = error.response?.data
    if (data?.error) return data.error
    if (data?.detail) return data.detail
    if (data?.message) return data.message
    if (error.message) return error.message
  }

  if (error instanceof Error) {
    return error.message
  }

  if (typeof error === 'string') {
    return error
  }

  return 'Unknown error'
}

/**
 * Extract error message, returning undefined if none found.
 *
 * This is useful when you want to use a fallback only if no message exists:
 * ```typescript
 * showError(getErrorMessage(error) || t('fallback.message'))
 * ```
 *
 * @param error - Error to extract message from
 * @returns Extracted error message or undefined
 */
export function getErrorMessage(error: unknown): string | undefined {
  if (isApiError(error)) {
    const data = error.response?.data
    return data?.error || data?.detail || data?.message || error.message
  }

  if (error instanceof Error) {
    return error.message
  }

  if (typeof error === 'string') {
    return error
  }

  return undefined
}

/**
 * Extract user-friendly error message with fallback.
 *
 * Includes special handling for network errors.
 *
 * @param error - Error to extract message from
 * @param fallback - Fallback message if no message can be extracted
 * @returns Human-readable error message
 */
export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (isApiError(error)) {
    if (isNetworkError(error)) {
      return 'Netzwerkfehler - bitte Verbindung prüfen'
    }
    const data = error.response?.data
    return data?.detail || data?.message || data?.error || error.message || fallback
  }

  if (error instanceof Error) {
    return error.message
  }

  return fallback
}

/**
 * Extract field-specific validation errors from API response.
 * Supports both simple error objects and Pydantic validation format.
 *
 * @param error - Error to extract validation errors from
 * @returns Map of field names to error messages (empty object if none)
 */
export function extractFieldErrors(error: unknown): Record<string, string> {
  if (!isApiError(error)) return {}

  const data = error.response?.data as Record<string, unknown> | undefined
  if (!data) return {}

  // Handle simple errors object: { errors: { field: "message" } }
  if (data.errors && typeof data.errors === 'object') {
    const errors = data.errors as Record<string, unknown>
    const result: Record<string, string> = {}
    for (const [key, value] of Object.entries(errors)) {
      if (typeof value === 'string') {
        result[key] = value
      } else if (Array.isArray(value) && value.length > 0) {
        result[key] = String(value[0])
      }
    }
    return result
  }

  // Handle Pydantic validation errors: { detail_errors: [{ loc: ["body", "field"], msg: "..." }] }
  if (data.detail_errors && Array.isArray(data.detail_errors)) {
    const result: Record<string, string> = {}
    for (const err of data.detail_errors as Array<{ loc: unknown[]; msg: string }>) {
      const field = err.loc[err.loc.length - 1]?.toString() || 'unknown'
      result[field] = err.msg
    }
    return result
  }

  return {}
}

// Alias for backward compatibility
export const getFieldErrors = extractFieldErrors

/**
 * HTTP status category type
 */
export type HttpStatusCategory = 'success' | 'client_error' | 'server_error' | 'network_error'

/**
 * Get HTTP status category from status code
 *
 * @param status - HTTP status code (or undefined for network errors)
 * @returns Category: 'success' (2xx), 'client_error' (4xx), 'server_error' (5xx), or 'network_error'
 */
export function getHttpStatusCategory(status: number | undefined): HttpStatusCategory {
  if (!status) return 'network_error'
  if (status >= 200 && status < 300) return 'success'
  if (status >= 400 && status < 500) return 'client_error'
  if (status >= 500) return 'server_error'
  return 'network_error'
}

/**
 * Check if error should trigger a retry (network or 5xx errors)
 * Useful for implementing automatic retry logic
 *
 * @param error - Error to check
 * @returns True if error is network error, 5xx, or 429 (rate limit)
 */
export function isRetryableError(error: unknown): boolean {
  if (isNetworkError(error)) return true
  if (!isApiError(error)) return false
  const status = error.response?.status
  return status !== undefined && (status >= 500 || status === 429)
}
