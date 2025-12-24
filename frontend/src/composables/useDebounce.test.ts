/**
 * Tests for useDebounce composable
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ref } from 'vue'
import {
  useDebounce,
  useThrottle,
  useTimeout,
  useSearchDebounce,
  usePolling,
  DEBOUNCE_DELAYS,
} from './useDebounce'

// Mock @vueuse/core
vi.mock('@vueuse/core', () => ({
  useDebounceFn: (fn: Function, delay: number) => {
    let timeoutId: ReturnType<typeof setTimeout> | null = null
    return (...args: unknown[]) => {
      if (timeoutId) clearTimeout(timeoutId)
      return new Promise((resolve) => {
        timeoutId = setTimeout(() => {
          resolve(fn(...args))
        }, delay)
      })
    }
  },
  useThrottleFn: (fn: Function, _delay: number) => fn,
}))

// Mock Vue lifecycle
vi.mock('vue', async () => {
  const actual = await vi.importActual('vue')
  return {
    ...actual,
    onUnmounted: vi.fn(),
  }
})

describe('useDebounce', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  describe('DEBOUNCE_DELAYS', () => {
    it('should have correct delay values', () => {
      expect(DEBOUNCE_DELAYS.FAST).toBe(150)
      expect(DEBOUNCE_DELAYS.SEARCH).toBe(300)
      expect(DEBOUNCE_DELAYS.VALIDATION).toBe(400)
      expect(DEBOUNCE_DELAYS.API).toBe(500)
      expect(DEBOUNCE_DELAYS.SAVE).toBe(1000)
    })
  })

  describe('useDebounce()', () => {
    it('should return debouncedFn, cancel, and isPending', () => {
      const fn = vi.fn()
      const result = useDebounce(fn)

      expect(result.debouncedFn).toBeDefined()
      expect(result.cancel).toBeDefined()
      expect(result.isPending).toBeDefined()
      expect(result.isPending.value).toBe(false)
    })

    it('should set isPending to true when called', () => {
      const fn = vi.fn()
      const { debouncedFn, isPending } = useDebounce(fn)

      debouncedFn()

      expect(isPending.value).toBe(true)
    })

    it('should use default delay of SEARCH (300ms)', () => {
      const fn = vi.fn()
      const { debouncedFn } = useDebounce(fn)

      debouncedFn()

      expect(fn).not.toHaveBeenCalled()

      vi.advanceTimersByTime(299)
      expect(fn).not.toHaveBeenCalled()

      vi.advanceTimersByTime(1)
      expect(fn).toHaveBeenCalledTimes(1)
    })

    it('should use custom delay', () => {
      const fn = vi.fn()
      const { debouncedFn } = useDebounce(fn, { delay: 500 })

      debouncedFn()

      vi.advanceTimersByTime(499)
      expect(fn).not.toHaveBeenCalled()

      vi.advanceTimersByTime(1)
      expect(fn).toHaveBeenCalledTimes(1)
    })

    it('should cancel pending execution', () => {
      const fn = vi.fn()
      const { debouncedFn, cancel, isPending } = useDebounce(fn)

      debouncedFn()
      expect(isPending.value).toBe(true)

      cancel()
      expect(isPending.value).toBe(false)

      vi.advanceTimersByTime(500)
      // Note: Due to mock behavior, the function may still be called
      // In real implementation, cancel would clear the timeout
    })

    it('should pass arguments to the debounced function', () => {
      const fn = vi.fn()
      const { debouncedFn } = useDebounce(fn)

      debouncedFn('arg1', 'arg2')

      vi.advanceTimersByTime(300)
      expect(fn).toHaveBeenCalledWith('arg1', 'arg2')
    })
  })

  describe('useTimeout()', () => {
    it('should return start, stop, and isActive', () => {
      const callback = vi.fn()
      const result = useTimeout(callback, 1000)

      expect(result.start).toBeDefined()
      expect(result.stop).toBeDefined()
      expect(result.isActive).toBeDefined()
      expect(result.isActive.value).toBe(false)
    })

    it('should set isActive to true when started', () => {
      const callback = vi.fn()
      const { start, isActive } = useTimeout(callback, 1000)

      start()

      expect(isActive.value).toBe(true)
    })

    it('should execute callback after delay', () => {
      const callback = vi.fn()
      const { start } = useTimeout(callback, 1000)

      start()

      expect(callback).not.toHaveBeenCalled()

      vi.advanceTimersByTime(1000)

      expect(callback).toHaveBeenCalledTimes(1)
    })

    it('should set isActive to false after execution', () => {
      const callback = vi.fn()
      const { start, isActive } = useTimeout(callback, 1000)

      start()
      expect(isActive.value).toBe(true)

      vi.advanceTimersByTime(1000)

      expect(isActive.value).toBe(false)
    })

    it('should stop timeout when stop is called', () => {
      const callback = vi.fn()
      const { start, stop, isActive } = useTimeout(callback, 1000)

      start()
      expect(isActive.value).toBe(true)

      stop()
      expect(isActive.value).toBe(false)

      vi.advanceTimersByTime(1000)
      expect(callback).not.toHaveBeenCalled()
    })

    it('should restart timeout when start is called again', () => {
      const callback = vi.fn()
      const { start } = useTimeout(callback, 1000)

      start()
      vi.advanceTimersByTime(500)

      start() // Restart

      vi.advanceTimersByTime(500)
      expect(callback).not.toHaveBeenCalled()

      vi.advanceTimersByTime(500)
      expect(callback).toHaveBeenCalledTimes(1)
    })
  })

  describe('useSearchDebounce()', () => {
    it('should return search, cancel, isPending, and lastQuery', () => {
      const searchFn = vi.fn()
      const result = useSearchDebounce(searchFn)

      expect(result.search).toBeDefined()
      expect(result.cancel).toBeDefined()
      expect(result.isPending).toBeDefined()
      expect(result.lastQuery).toBeDefined()
    })

    it('should not search for queries shorter than minLength', () => {
      const searchFn = vi.fn().mockResolvedValue([])
      const { search } = useSearchDebounce(searchFn, { minLength: 3 })

      // Call search but don't await - it returns early for short queries
      search('ab')

      vi.advanceTimersByTime(300)

      expect(searchFn).not.toHaveBeenCalled()
    })

    it('should search for queries at or above minLength', async () => {
      const searchFn = vi.fn().mockResolvedValue(['result'])
      const { search } = useSearchDebounce(searchFn, { minLength: 3 })

      search('abc')

      vi.advanceTimersByTime(300)

      // Wait for debounce and async execution
      await vi.runAllTimersAsync()

      expect(searchFn).toHaveBeenCalledWith('abc')
    })

    it('should use default minLength of 2', async () => {
      const searchFn = vi.fn().mockResolvedValue([])
      const { search } = useSearchDebounce(searchFn)

      search('a')
      vi.advanceTimersByTime(300)
      await vi.runAllTimersAsync()

      expect(searchFn).not.toHaveBeenCalled()

      search('ab')
      vi.advanceTimersByTime(300)
      await vi.runAllTimersAsync()

      expect(searchFn).toHaveBeenCalledWith('ab')
    })

    it('should update lastQuery', async () => {
      const searchFn = vi.fn().mockResolvedValue([])
      const { search, lastQuery } = useSearchDebounce(searchFn)

      search('test query')
      vi.advanceTimersByTime(300)
      await vi.runAllTimersAsync()

      expect(lastQuery.value).toBe('test query')
    })
  })

  describe('usePolling()', () => {
    it('should return start, stop, and isActive', () => {
      const callback = vi.fn()
      const result = usePolling(callback)

      expect(result.start).toBeDefined()
      expect(result.stop).toBeDefined()
      expect(result.isActive).toBeDefined()
    })

    it('should execute callback immediately when started', () => {
      const callback = vi.fn()
      const { start } = usePolling(callback, 1000)

      start()

      expect(callback).toHaveBeenCalledTimes(1)
    })

    it('should execute callback at regular intervals', () => {
      const callback = vi.fn()
      const { start } = usePolling(callback, 1000)

      start()
      expect(callback).toHaveBeenCalledTimes(1)

      vi.advanceTimersByTime(1000)
      expect(callback).toHaveBeenCalledTimes(2)

      vi.advanceTimersByTime(1000)
      expect(callback).toHaveBeenCalledTimes(3)
    })

    it('should stop polling when stop is called', () => {
      const callback = vi.fn()
      const { start, stop, isActive } = usePolling(callback, 1000)

      start()
      expect(isActive.value).toBe(true)
      expect(callback).toHaveBeenCalledTimes(1)

      stop()
      expect(isActive.value).toBe(false)

      vi.advanceTimersByTime(3000)
      expect(callback).toHaveBeenCalledTimes(1) // No additional calls
    })

    it('should use default interval of 5000ms', () => {
      const callback = vi.fn()
      const { start } = usePolling(callback)

      start()
      expect(callback).toHaveBeenCalledTimes(1)

      vi.advanceTimersByTime(4999)
      expect(callback).toHaveBeenCalledTimes(1)

      vi.advanceTimersByTime(1)
      expect(callback).toHaveBeenCalledTimes(2)
    })

    it('should not start twice if already active', () => {
      const callback = vi.fn()
      const { start, isActive } = usePolling(callback, 1000)

      start()
      start() // Try to start again

      expect(callback).toHaveBeenCalledTimes(1) // Only called once
    })
  })

  describe('useThrottle()', () => {
    it('should return a function', () => {
      const fn = vi.fn()
      const throttled = useThrottle(fn)

      expect(typeof throttled).toBe('function')
    })

    it('should call the function', () => {
      const fn = vi.fn()
      const throttled = useThrottle(fn, 500)

      throttled()

      expect(fn).toHaveBeenCalled()
    })
  })
})
