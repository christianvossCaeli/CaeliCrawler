/**
 * Tests for cache utility
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createCache, entityCache, categoryCache, facetTypeCache, searchCache } from './cache'

// Mock sessionStorage
const mockSessionStorage = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key]
    }),
    clear: vi.fn(() => {
      store = {}
    }),
    get length() {
      return Object.keys(store).length
    },
    key: vi.fn((index: number) => Object.keys(store)[index] || null),
    keys: () => Object.keys(store),
  }
})()

// Replace global sessionStorage
Object.defineProperty(global, 'sessionStorage', {
  value: mockSessionStorage,
  writable: true,
})

// Mock vue
vi.mock('vue', async () => {
  const actual = await vi.importActual('vue')
  return {
    ...actual,
    onUnmounted: vi.fn(),
  }
})

describe('createCache', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    mockSessionStorage.clear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  describe('memory storage', () => {
    it('should create a cache with default options', () => {
      const cache = createCache<string>()

      expect(cache.get).toBeDefined()
      expect(cache.set).toBeDefined()
      expect(cache.getOrFetch).toBeDefined()
      expect(cache.has).toBeDefined()
      expect(cache.invalidate).toBeDefined()
      expect(cache.invalidatePattern).toBeDefined()
      expect(cache.clear).toBeDefined()
      expect(cache.stats).toBeDefined()
    })

    it('should set and get values', () => {
      const cache = createCache<string>()

      cache.set('key1', 'value1')

      expect(cache.get('key1')).toBe('value1')
    })

    it('should return undefined for non-existent keys', () => {
      const cache = createCache<string>()

      expect(cache.get('nonexistent')).toBeUndefined()
    })

    it('should check if key exists with has()', () => {
      const cache = createCache<string>()

      expect(cache.has('key1')).toBe(false)

      cache.set('key1', 'value1')

      expect(cache.has('key1')).toBe(true)
    })

    it('should expire entries after TTL', () => {
      const cache = createCache<string>({ ttl: 1000 })

      cache.set('key1', 'value1')

      expect(cache.get('key1')).toBe('value1')

      // Advance time past TTL
      vi.advanceTimersByTime(1001)

      expect(cache.get('key1')).toBeUndefined()
      expect(cache.has('key1')).toBe(false)
    })

    it('should invalidate specific keys', () => {
      const cache = createCache<string>()

      cache.set('key1', 'value1')
      cache.set('key2', 'value2')

      cache.invalidate('key1')

      expect(cache.get('key1')).toBeUndefined()
      expect(cache.get('key2')).toBe('value2')
    })

    it('should invalidate keys matching pattern (string)', () => {
      const cache = createCache<string>()

      cache.set('user:1', 'user1')
      cache.set('user:2', 'user2')
      cache.set('entity:1', 'entity1')

      cache.invalidatePattern('^user:')

      expect(cache.get('user:1')).toBeUndefined()
      expect(cache.get('user:2')).toBeUndefined()
      expect(cache.get('entity:1')).toBe('entity1')
    })

    it('should invalidate keys matching pattern (RegExp)', () => {
      const cache = createCache<string>()

      cache.set('user:1', 'user1')
      cache.set('user:2', 'user2')
      cache.set('entity:1', 'entity1')

      cache.invalidatePattern(/^user:/)

      expect(cache.get('user:1')).toBeUndefined()
      expect(cache.get('user:2')).toBeUndefined()
      expect(cache.get('entity:1')).toBe('entity1')
    })

    it('should clear all entries', () => {
      const cache = createCache<string>()

      cache.set('key1', 'value1')
      cache.set('key2', 'value2')

      cache.clear()

      expect(cache.get('key1')).toBeUndefined()
      expect(cache.get('key2')).toBeUndefined()
      expect(cache.stats().entries).toBe(0)
    })

    it('should enforce maxEntries limit', () => {
      const cache = createCache<string>({ maxEntries: 2 })

      cache.set('key1', 'value1')
      cache.set('key2', 'value2')
      cache.set('key3', 'value3') // Should evict key1

      expect(cache.stats().entries).toBe(2)
      expect(cache.get('key1')).toBeUndefined() // Evicted
      expect(cache.get('key2')).toBe('value2')
      expect(cache.get('key3')).toBe('value3')
    })

    it('should track cache statistics', () => {
      const cache = createCache<string>()

      cache.set('key1', 'value1')

      // Hit
      cache.get('key1')
      cache.get('key1')

      // Miss
      cache.get('nonexistent')

      const stats = cache.stats()

      expect(stats.entries).toBe(1)
      expect(stats.hits).toBe(2)
      expect(stats.misses).toBe(1)
      expect(stats.hitRate).toBeCloseTo(0.667, 2)
    })

    it('should reset stats on clear', () => {
      const cache = createCache<string>()

      cache.set('key1', 'value1')
      cache.get('key1') // Hit
      cache.get('nonexistent') // Miss

      cache.clear()

      const stats = cache.stats()
      expect(stats.hits).toBe(0)
      expect(stats.misses).toBe(0)
      expect(stats.hitRate).toBe(0)
    })
  })

  describe('getOrFetch()', () => {
    it('should return cached value if available', async () => {
      const cache = createCache<string>()
      const fetcher = vi.fn().mockResolvedValue('fetched')

      cache.set('key1', 'cached')

      const result = await cache.getOrFetch('key1', fetcher)

      expect(result).toBe('cached')
      expect(fetcher).not.toHaveBeenCalled()
    })

    it('should fetch and cache if not available', async () => {
      const cache = createCache<string>()
      const fetcher = vi.fn().mockResolvedValue('fetched')

      const result = await cache.getOrFetch('key1', fetcher)

      expect(result).toBe('fetched')
      expect(fetcher).toHaveBeenCalledTimes(1)
      expect(cache.get('key1')).toBe('fetched')
    })

    it('should fetch again after expiration', async () => {
      const cache = createCache<string>({ ttl: 1000 })
      const fetcher = vi.fn()
        .mockResolvedValueOnce('first')
        .mockResolvedValueOnce('second')

      const result1 = await cache.getOrFetch('key1', fetcher)
      expect(result1).toBe('first')

      vi.advanceTimersByTime(1001)

      const result2 = await cache.getOrFetch('key1', fetcher)
      expect(result2).toBe('second')
      expect(fetcher).toHaveBeenCalledTimes(2)
    })
  })

  describe('sessionStorage backend', () => {
    it('should use sessionStorage when configured', () => {
      const cache = createCache<string>({ storage: 'sessionStorage', name: 'test' })

      cache.set('key1', 'value1')

      expect(mockSessionStorage.setItem).toHaveBeenCalledWith(
        'test:key1',
        expect.any(String)
      )
    })

    it('should retrieve from sessionStorage', () => {
      const cache = createCache<string>({ storage: 'sessionStorage', name: 'test' })

      // Manually set in mock storage
      const entry = {
        data: 'stored-value',
        timestamp: Date.now(),
        expiresAt: Date.now() + 60000,
      }
      mockSessionStorage.setItem('test:key1', JSON.stringify(entry))

      expect(cache.get('key1')).toBe('stored-value')
    })
  })

  describe('pre-configured caches', () => {
    it('should export entityCache', () => {
      expect(entityCache).toBeDefined()
      expect(entityCache.get).toBeDefined()
    })

    it('should export categoryCache', () => {
      expect(categoryCache).toBeDefined()
      expect(categoryCache.get).toBeDefined()
    })

    it('should export facetTypeCache', () => {
      expect(facetTypeCache).toBeDefined()
      expect(facetTypeCache.get).toBeDefined()
    })

    it('should export searchCache', () => {
      expect(searchCache).toBeDefined()
      expect(searchCache.get).toBeDefined()
    })
  })
})

describe('cache edge cases', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('should handle null values', () => {
    const cache = createCache<null>()

    cache.set('key1', null)

    // null is a valid cached value
    expect(cache.has('key1')).toBe(true)
  })

  it('should handle complex objects', () => {
    const cache = createCache<{ nested: { value: number } }>()

    const obj = { nested: { value: 42 } }
    cache.set('key1', obj)

    expect(cache.get('key1')).toEqual(obj)
  })

  it('should handle array values', () => {
    const cache = createCache<string[]>()

    cache.set('key1', ['a', 'b', 'c'])

    expect(cache.get('key1')).toEqual(['a', 'b', 'c'])
  })

  it('should handle concurrent getOrFetch calls', async () => {
    // Use real timers for this async test
    vi.useRealTimers()

    const cache = createCache<string>()
    let fetchCount = 0
    const fetcher = vi.fn(async () => {
      fetchCount++
      await new Promise(resolve => setTimeout(resolve, 10))
      return `value-${fetchCount}`
    })

    // Start multiple fetches concurrently
    const [result1, result2] = await Promise.all([
      cache.getOrFetch('key1', fetcher),
      cache.getOrFetch('key1', fetcher),
    ])

    // Both should complete, but they will both fetch since cache doesn't dedupe
    // This tests that the cache handles concurrent operations without errors
    expect(result1).toBeDefined()
    expect(result2).toBeDefined()

    // Restore fake timers for other tests
    vi.useFakeTimers()
  })

  it('should handle special characters in keys', () => {
    const cache = createCache<string>()

    const specialKey = 'key:with/special?chars&more=stuff'
    cache.set(specialKey, 'value')

    expect(cache.get(specialKey)).toBe('value')
  })

  it('should handle empty string keys', () => {
    const cache = createCache<string>()

    cache.set('', 'empty-key-value')

    expect(cache.get('')).toBe('empty-key-value')
  })

  it('should handle hit rate with no operations', () => {
    const cache = createCache<string>()

    const stats = cache.stats()

    expect(stats.hitRate).toBe(0)
  })
})
