/**
 * Tests for useAbortController composable
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  useAbortController,
  useMultiAbortController,
  isAbortError,
  createTimeoutSignal,
  combineSignals,
} from './useAbortController'

// Mock Vue lifecycle
vi.mock('vue', async () => {
  const actual = await vi.importActual('vue')
  return {
    ...actual,
    onUnmounted: vi.fn(),
  }
})

describe('useAbortController', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('should return all expected properties', () => {
      const controller = useAbortController()

      expect(controller.signal).toBeDefined()
      expect(controller.isAborted).toBeDefined()
      expect(controller.abort).toBeInstanceOf(Function)
      expect(controller.reset).toBeInstanceOf(Function)
      expect(controller.getController).toBeInstanceOf(Function)
    })

    it('should initialize with a valid signal', () => {
      const { signal } = useAbortController()

      expect(signal.value).toBeInstanceOf(AbortSignal)
      expect(signal.value?.aborted).toBe(false)
    })

    it('should initialize with isAborted false', () => {
      const { isAborted } = useAbortController()

      expect(isAborted.value).toBe(false)
    })
  })

  describe('abort()', () => {
    it('should abort the current signal', () => {
      const { signal, abort, isAborted } = useAbortController()

      abort()

      expect(signal.value?.aborted).toBe(true)
      expect(isAborted.value).toBe(true)
    })

    it('should accept an optional reason', () => {
      const { abort, getController } = useAbortController()

      abort('Test reason')

      const controller = getController()
      expect(controller?.signal.aborted).toBe(true)
    })
  })

  describe('reset()', () => {
    it('should create a new controller', () => {
      const { getController, reset } = useAbortController()
      const firstController = getController()

      reset()
      const secondController = getController()

      expect(secondController).not.toBe(firstController)
    })

    it('should reset isAborted to false', () => {
      const { abort, isAborted, reset } = useAbortController()

      abort()
      expect(isAborted.value).toBe(true)

      reset()
      expect(isAborted.value).toBe(false)
    })

    it('should abort previous controller when resetting', () => {
      const { getController, reset } = useAbortController()
      const firstController = getController()

      reset()

      expect(firstController?.signal.aborted).toBe(true)
    })

    it('should provide a new valid signal', () => {
      const { signal, reset } = useAbortController()
      const firstSignal = signal.value

      reset()

      expect(signal.value).not.toBe(firstSignal)
      expect(signal.value?.aborted).toBe(false)
    })
  })

  describe('getController()', () => {
    it('should return the current AbortController', () => {
      const { getController } = useAbortController()

      const controller = getController()

      expect(controller).toBeInstanceOf(AbortController)
    })
  })
})

describe('useMultiAbortController', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('should return all expected properties', () => {
      const multi = useMultiAbortController()

      expect(multi.getSignal).toBeInstanceOf(Function)
      expect(multi.abort).toBeInstanceOf(Function)
      expect(multi.abortAll).toBeInstanceOf(Function)
      expect(multi.reset).toBeInstanceOf(Function)
      expect(multi.isAborted).toBeInstanceOf(Function)
    })
  })

  describe('reset()', () => {
    it('should create a new controller for a name', () => {
      const { reset, getSignal } = useMultiAbortController()

      const signal = reset('users')

      expect(signal).toBeInstanceOf(AbortSignal)
      expect(getSignal('users')).toBe(signal)
    })

    it('should abort previous controller with same name', () => {
      const { reset } = useMultiAbortController()

      const firstSignal = reset('users')
      reset('users')

      expect(firstSignal.aborted).toBe(true)
    })

    it('should not affect other named controllers', () => {
      const { reset, getSignal } = useMultiAbortController()

      reset('users')
      reset('posts')
      reset('users') // Reset users again

      expect(getSignal('posts')?.aborted).toBe(false)
    })
  })

  describe('getSignal()', () => {
    it('should return undefined for non-existent name', () => {
      const { getSignal } = useMultiAbortController()

      expect(getSignal('nonexistent')).toBeUndefined()
    })

    it('should return signal for existing name', () => {
      const { reset, getSignal } = useMultiAbortController()

      reset('users')

      expect(getSignal('users')).toBeInstanceOf(AbortSignal)
    })
  })

  describe('abort()', () => {
    it('should abort a specific named controller', () => {
      const { reset, abort, isAborted } = useMultiAbortController()

      reset('users')
      reset('posts')

      abort('users')

      expect(isAborted('users')).toBe(true)
      expect(isAborted('posts')).toBe(false)
    })

    it('should do nothing for non-existent name', () => {
      const { abort } = useMultiAbortController()

      // Should not throw
      expect(() => abort('nonexistent')).not.toThrow()
    })
  })

  describe('abortAll()', () => {
    it('should abort all controllers', () => {
      const { reset, abortAll, getSignal } = useMultiAbortController()

      const usersSignal = reset('users')
      const postsSignal = reset('posts')
      const commentsSignal = reset('comments')

      abortAll()

      // After abortAll, the map is cleared, so we check the signals directly
      expect(usersSignal.aborted).toBe(true)
      expect(postsSignal.aborted).toBe(true)
      expect(commentsSignal.aborted).toBe(true)

      // After clear, getSignal returns undefined
      expect(getSignal('users')).toBeUndefined()
    })
  })

  describe('isAborted()', () => {
    it('should return false for non-aborted controller', () => {
      const { reset, isAborted } = useMultiAbortController()

      reset('users')

      expect(isAborted('users')).toBe(false)
    })

    it('should return true for aborted controller', () => {
      const { reset, abort, isAborted } = useMultiAbortController()

      reset('users')
      abort('users')

      expect(isAborted('users')).toBe(true)
    })

    it('should return false for non-existent name', () => {
      const { isAborted } = useMultiAbortController()

      expect(isAborted('nonexistent')).toBe(false)
    })
  })
})

describe('isAbortError', () => {
  it('should return true for AbortError', () => {
    const error = new DOMException('Aborted', 'AbortError')

    expect(isAbortError(error)).toBe(true)
  })

  it('should return true for error with message "canceled"', () => {
    const error = new Error('canceled')

    expect(isAbortError(error)).toBe(true)
  })

  it('should return false for regular errors', () => {
    const error = new Error('Network error')

    expect(isAbortError(error)).toBe(false)
  })

  it('should return false for non-Error values', () => {
    expect(isAbortError('string')).toBe(false)
    expect(isAbortError(null)).toBe(false)
    expect(isAbortError(undefined)).toBe(false)
    expect(isAbortError({})).toBe(false)
  })
})

describe('createTimeoutSignal', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('should return an AbortSignal', () => {
    const signal = createTimeoutSignal(1000)

    expect(signal).toBeInstanceOf(AbortSignal)
  })

  it('should not be aborted initially', () => {
    const signal = createTimeoutSignal(1000)

    expect(signal.aborted).toBe(false)
  })

  it('should abort after specified time', () => {
    const signal = createTimeoutSignal(1000)

    vi.advanceTimersByTime(999)
    expect(signal.aborted).toBe(false)

    vi.advanceTimersByTime(1)
    expect(signal.aborted).toBe(true)
  })
})

describe('combineSignals', () => {
  it('should return an AbortSignal', () => {
    const controller1 = new AbortController()
    const signal = combineSignals(controller1.signal)

    expect(signal).toBeInstanceOf(AbortSignal)
  })

  it('should abort when any signal aborts', () => {
    const controller1 = new AbortController()
    const controller2 = new AbortController()
    const combined = combineSignals(controller1.signal, controller2.signal)

    expect(combined.aborted).toBe(false)

    controller1.abort()

    expect(combined.aborted).toBe(true)
  })

  it('should be immediately aborted if any input is already aborted', () => {
    const controller1 = new AbortController()
    const controller2 = new AbortController()
    controller1.abort()

    const combined = combineSignals(controller1.signal, controller2.signal)

    expect(combined.aborted).toBe(true)
  })

  it('should filter out undefined signals', () => {
    const controller = new AbortController()
    const combined = combineSignals(undefined, controller.signal, undefined)

    expect(combined.aborted).toBe(false)

    controller.abort()
    expect(combined.aborted).toBe(true)
  })

  it('should handle empty signals array', () => {
    const combined = combineSignals()

    expect(combined).toBeInstanceOf(AbortSignal)
    expect(combined.aborted).toBe(false)
  })
})
