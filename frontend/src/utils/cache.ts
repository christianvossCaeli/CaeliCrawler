/**
 * Client-Side Caching Utilities
 *
 * Provides a simple yet powerful caching layer for API responses.
 * Supports TTL (time-to-live), automatic cache invalidation, and memory limits.
 *
 * @example
 * ```typescript
 * const cache = createCache<EntityResponse>({ ttl: 5 * 60 * 1000 })
 *
 * // Get or fetch
 * const entity = await cache.getOrFetch(
 *   `entity:${id}`,
 *   () => api.getEntity(id)
 * )
 *
 * // Invalidate after mutation
 * cache.invalidate(`entity:${id}`)
 * ```
 */

export interface CacheOptions {
  /** Time-to-live in milliseconds (default: 5 minutes) */
  ttl?: number
  /** Maximum number of entries (default: 100) */
  maxEntries?: number
  /** Storage backend: 'memory' | 'sessionStorage' (default: 'memory') */
  storage?: 'memory' | 'sessionStorage'
  /** Cache name for debugging */
  name?: string
}

export interface CacheEntry<T> {
  data: T
  timestamp: number
  expiresAt: number
}

export interface Cache<T> {
  /** Get value from cache */
  get(key: string): T | undefined
  /** Set value in cache */
  set(key: string, value: T): void
  /** Get value or fetch from async function */
  getOrFetch(key: string, fetcher: () => Promise<T>): Promise<T>
  /** Check if key exists and is not expired */
  has(key: string): boolean
  /** Invalidate a specific key */
  invalidate(key: string): void
  /** Invalidate all keys matching pattern */
  invalidatePattern(pattern: string | RegExp): void
  /** Clear entire cache */
  clear(): void
  /** Get cache statistics */
  stats(): CacheStats
}

export interface CacheStats {
  entries: number
  hits: number
  misses: number
  hitRate: number
}

/**
 * Create a typed cache instance.
 */
export function createCache<T>(options: CacheOptions = {}): Cache<T> {
  const {
    ttl = 5 * 60 * 1000, // 5 minutes default
    maxEntries = 100,
    storage = 'memory',
    name = 'cache',
  } = options

  // In-memory storage
  const memoryStore = new Map<string, CacheEntry<T>>()

  // Stats tracking
  let hits = 0
  let misses = 0

  // Session storage helpers
  const getStorageKey = (key: string) => `${name}:${key}`

  const getFromStorage = (key: string): CacheEntry<T> | undefined => {
    if (storage === 'memory') {
      return memoryStore.get(key)
    }

    try {
      const stored = sessionStorage.getItem(getStorageKey(key))
      if (stored) {
        return JSON.parse(stored) as CacheEntry<T>
      }
    } catch {
      // Session storage might be unavailable
    }
    return undefined
  }

  const setInStorage = (key: string, entry: CacheEntry<T>): void => {
    if (storage === 'memory') {
      // Enforce max entries in memory
      if (memoryStore.size >= maxEntries) {
        // Remove oldest entry
        const oldestKey = memoryStore.keys().next().value
        if (oldestKey) {
          memoryStore.delete(oldestKey)
        }
      }
      memoryStore.set(key, entry)
    } else {
      try {
        sessionStorage.setItem(getStorageKey(key), JSON.stringify(entry))
      } catch {
        // Session storage might be full or unavailable
      }
    }
  }

  const removeFromStorage = (key: string): void => {
    if (storage === 'memory') {
      memoryStore.delete(key)
    } else {
      try {
        sessionStorage.removeItem(getStorageKey(key))
      } catch {
        // Ignore
      }
    }
  }

  const isExpired = (entry: CacheEntry<T>): boolean => {
    return Date.now() > entry.expiresAt
  }

  return {
    get(key: string): T | undefined {
      const entry = getFromStorage(key)
      if (entry && !isExpired(entry)) {
        hits++
        return entry.data
      }
      if (entry) {
        // Clean up expired entry
        removeFromStorage(key)
      }
      misses++
      return undefined
    },

    set(key: string, value: T): void {
      const now = Date.now()
      const entry: CacheEntry<T> = {
        data: value,
        timestamp: now,
        expiresAt: now + ttl,
      }
      setInStorage(key, entry)
    },

    async getOrFetch(key: string, fetcher: () => Promise<T>): Promise<T> {
      const cached = this.get(key)
      if (cached !== undefined) {
        return cached
      }

      const data = await fetcher()
      this.set(key, data)
      return data
    },

    has(key: string): boolean {
      const entry = getFromStorage(key)
      return entry !== undefined && !isExpired(entry)
    },

    invalidate(key: string): void {
      removeFromStorage(key)
    },

    invalidatePattern(pattern: string | RegExp): void {
      const regex = typeof pattern === 'string' ? new RegExp(pattern) : pattern

      if (storage === 'memory') {
        for (const key of memoryStore.keys()) {
          if (regex.test(key)) {
            memoryStore.delete(key)
          }
        }
      } else {
        try {
          const keys = Object.keys(sessionStorage)
          for (const storageKey of keys) {
            if (storageKey.startsWith(`${name}:`)) {
              const key = storageKey.slice(`${name}:`.length)
              if (regex.test(key)) {
                sessionStorage.removeItem(storageKey)
              }
            }
          }
        } catch {
          // Ignore
        }
      }
    },

    clear(): void {
      if (storage === 'memory') {
        memoryStore.clear()
      } else {
        try {
          const keys = Object.keys(sessionStorage)
          for (const key of keys) {
            if (key.startsWith(`${name}:`)) {
              sessionStorage.removeItem(key)
            }
          }
        } catch {
          // Ignore
        }
      }
      hits = 0
      misses = 0
    },

    stats(): CacheStats {
      const entries = storage === 'memory'
        ? memoryStore.size
        : Object.keys(sessionStorage).filter(k => k.startsWith(`${name}:`)).length
      const total = hits + misses

      return {
        entries,
        hits,
        misses,
        hitRate: total > 0 ? hits / total : 0,
      }
    },
  }
}

// =============================================================================
// Pre-configured Cache Instances
// =============================================================================

/** Cache for entity data (5 min TTL) */
export const entityCache = createCache<Record<string, unknown>>({
  name: 'entities',
  ttl: 5 * 60 * 1000,
  maxEntries: 50,
})

/** Cache for category lists (10 min TTL) */
export const categoryCache = createCache<Record<string, unknown>[]>({
  name: 'categories',
  ttl: 10 * 60 * 1000,
  maxEntries: 10,
})

/** Cache for facet types (10 min TTL) */
export const facetTypeCache = createCache<Record<string, unknown>[]>({
  name: 'facet-types',
  ttl: 10 * 60 * 1000,
  maxEntries: 10,
})

/** Cache for search results (2 min TTL, shorter for freshness) */
export const searchCache = createCache<Record<string, unknown>>({
  name: 'search',
  ttl: 2 * 60 * 1000,
  maxEntries: 20,
})

// =============================================================================
// Composable for Cache Integration
// =============================================================================

import { ref, onUnmounted } from 'vue'

export interface UseCacheOptions<T> extends CacheOptions {
  /** Initial value while loading */
  initialValue?: T
  /** Auto-refresh interval in ms (0 = disabled) */
  refreshInterval?: number
}

/**
 * Vue composable for reactive caching.
 */
export function useCache<T>(
  key: string,
  fetcher: () => Promise<T>,
  options: UseCacheOptions<T> = {}
) {
  const { initialValue, refreshInterval = 0, ...cacheOptions } = options

  const cache = createCache<T>(cacheOptions)
  const data = ref<T | undefined>(initialValue)
  const loading = ref(false)
  const error = ref<Error | null>(null)

  let refreshTimer: ReturnType<typeof setInterval> | null = null

  async function refresh(force = false) {
    if (force) {
      cache.invalidate(key)
    }

    loading.value = true
    error.value = null

    try {
      data.value = await cache.getOrFetch(key, fetcher)
    } catch (e) {
      error.value = e instanceof Error ? e : new Error(String(e))
    } finally {
      loading.value = false
    }
  }

  function invalidate() {
    cache.invalidate(key)
  }

  // Initial fetch
  refresh()

  // Set up auto-refresh if configured
  if (refreshInterval > 0) {
    refreshTimer = setInterval(() => refresh(true), refreshInterval)
  }

  // Cleanup on unmount
  onUnmounted(() => {
    if (refreshTimer) {
      clearInterval(refreshTimer)
    }
  })

  return {
    data,
    loading,
    error,
    refresh,
    invalidate,
    stats: () => cache.stats(),
  }
}
