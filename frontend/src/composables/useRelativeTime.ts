/**
 * Composable for relative time formatting with memoization.
 *
 * Provides a memoized formatRelativeTime function that caches results
 * for 30 seconds to avoid redundant calculations.
 */

import { useI18n } from 'vue-i18n'

// Simple LRU-like cache with TTL
const cache = new Map<string, { value: string; expires: number }>()
const CACHE_TTL = 30000 // 30 seconds

function getCached(key: string): string | undefined {
  const entry = cache.get(key)
  if (entry && entry.expires > Date.now()) {
    return entry.value
  }
  cache.delete(key)
  return undefined
}

function setCache(key: string, value: string): void {
  // Limit cache size
  if (cache.size > 100) {
    const firstKey = cache.keys().next().value
    if (firstKey) cache.delete(firstKey)
  }
  cache.set(key, { value, expires: Date.now() + CACHE_TTL })
}

export function useRelativeTime() {
  const { t, locale } = useI18n()

  /**
   * Format a date string as relative time (e.g., "5 minutes ago").
   * Results are cached for 30 seconds.
   */
  function formatRelativeTime(dateStr: string): string {
    // Create cache key from date and current minute (to invalidate on minute change)
    const currentMinute = Math.floor(Date.now() / 60000)
    const cacheKey = `${dateStr}:${currentMinute}:${locale.value}`

    const cached = getCached(cacheKey)
    if (cached) return cached

    const date = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)

    let result: string
    if (minutes < 1) {
      result = t('summaries.time.justNow')
    } else if (minutes < 60) {
      result = t('summaries.time.minutesAgo', { n: minutes })
    } else if (hours < 24) {
      result = t('summaries.time.hoursAgo', { n: hours })
    } else if (days < 7) {
      result = t('summaries.time.daysAgo', { n: days })
    } else {
      result = date.toLocaleDateString()
    }

    setCache(cacheKey, result)
    return result
  }

  /**
   * Format a date string as full date/time.
   */
  function formatDateTime(dateStr: string): string {
    return new Date(dateStr).toLocaleString(locale.value, {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  /**
   * Format a date string as date only.
   */
  function formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString(locale.value, {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    })
  }

  return {
    formatRelativeTime,
    formatDateTime,
    formatDate,
  }
}
