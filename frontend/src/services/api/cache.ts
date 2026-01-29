/**
 * Request deduplication utility for API calls.
 *
 * Prevents duplicate concurrent requests to the same URL by caching
 * in-flight promises. When multiple components request the same data
 * simultaneously, only one actual HTTP request is made.
 *
 * This is especially useful for:
 * - Badge counts that multiple components need
 * - Entity details loaded in parallel by different views
 * - Dashboard widgets requesting the same stats
 */

import type { AxiosResponse } from 'axios'
import { api } from './client'

// Cache for in-flight GET requests
// Key: URL, Value: Promise that resolves to the response
const requestCache = new Map<string, Promise<AxiosResponse>>()

// Default cache TTL for completed requests (100ms)
// This prevents immediate re-fetches while allowing natural updates
const CACHE_CLEANUP_DELAY = 100

/**
 * Make a deduplicated GET request.
 *
 * If the same URL is already being fetched, returns the existing promise
 * instead of making a new request. The cache entry is cleaned up shortly
 * after the request completes to allow for updates.
 *
 * @param url - API endpoint URL
 * @param config - Optional Axios request config
 * @returns Promise resolving to the Axios response
 *
 * @example
 * // Multiple concurrent calls result in single HTTP request
 * const [badges1, badges2] = await Promise.all([
 *   deduplicatedGet('/api/v1/badges'),
 *   deduplicatedGet('/api/v1/badges')
 * ])
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function deduplicatedGet<T = any>(
  url: string,
  config?: Parameters<typeof api.get>[1]
): Promise<AxiosResponse<T>> {
  // Build cache key including query params from config if present
  const cacheKey = buildCacheKey(url, config)

  // Return existing promise if request is in-flight
  if (requestCache.has(cacheKey)) {
    return requestCache.get(cacheKey) as Promise<AxiosResponse<T>>
  }

  // Create new request and cache the promise
  const promise = api.get<T>(url, config).finally(() => {
    // Clean up cache after short delay to allow natural batching
    setTimeout(() => {
      requestCache.delete(cacheKey)
    }, CACHE_CLEANUP_DELAY)
  })

  requestCache.set(cacheKey, promise)
  return promise
}

/**
 * Build a cache key from URL and config.
 * Includes query params for accurate deduplication.
 */
function buildCacheKey(
  url: string,
  config?: Parameters<typeof api.get>[1]
): string {
  if (!config?.params) {
    return url
  }

  // Sort params for consistent key generation
  const params = new URLSearchParams()
  const sortedKeys = Object.keys(config.params).sort()

  for (const key of sortedKeys) {
    const value = config.params[key]
    if (value !== undefined && value !== null) {
      params.set(key, String(value))
    }
  }

  const queryString = params.toString()
  return queryString ? `${url}?${queryString}` : url
}

/**
 * Clear all cached requests.
 * Useful when authentication state changes.
 */
export function clearRequestCache(): void {
  requestCache.clear()
}

/**
 * Get the current size of the request cache.
 * Useful for debugging/monitoring.
 */
export function getRequestCacheSize(): number {
  return requestCache.size
}
