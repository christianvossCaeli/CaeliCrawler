/**
 * Tests for useAsyncOperation composable
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useAsyncOperation, useAsyncState, useDebouncedOperation } from './useAsyncOperation'

// Mock Vue lifecycle
vi.mock('vue', async () => {
  const actual = await vi.importActual('vue')
  return {
    ...actual,
    onUnmounted: vi.fn(),
  }
})

describe('useAsyncOperation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('should return all expected properties', () => {
      const operation = useAsyncOperation(async () => 'result')

      expect(operation.data).toBeDefined()
      expect(operation.error).toBeDefined()
      expect(operation.loading).toBeDefined()
      expect(operation.executed).toBeDefined()
      expect(operation.execute).toBeInstanceOf(Function)
      expect(operation.abort).toBeInstanceOf(Function)
      expect(operation.reset).toBeInstanceOf(Function)
      expect(operation.isSuccess).toBeDefined()
      expect(operation.isError).toBeDefined()
    })

    it('should have correct initial values', () => {
      const operation = useAsyncOperation(async () => 'result')

      expect(operation.data.value).toBeNull()
      expect(operation.error.value).toBeNull()
      expect(operation.loading.value).toBe(false)
      expect(operation.executed.value).toBe(false)
      expect(operation.isSuccess.value).toBe(false)
      expect(operation.isError.value).toBe(false)
    })

    it('should use initialData option', () => {
      const operation = useAsyncOperation(async () => 'result', {
        initialData: 'initial',
      })

      expect(operation.data.value).toBe('initial')
    })
  })

  describe('execute()', () => {
    it('should set loading to true during execution', async () => {
      let resolvePromise: (value: string) => void
      const promise = new Promise<string>((resolve) => {
        resolvePromise = resolve
      })
      const operation = useAsyncOperation(async () => promise)

      const executePromise = operation.execute()

      expect(operation.loading.value).toBe(true)

      resolvePromise!('result')
      await executePromise

      expect(operation.loading.value).toBe(false)
    })

    it('should set executed to true after execution', async () => {
      const operation = useAsyncOperation(async () => 'result')

      expect(operation.executed.value).toBe(false)

      await operation.execute()

      expect(operation.executed.value).toBe(true)
    })

    it('should set data on success', async () => {
      const operation = useAsyncOperation(async () => 'success-data')

      await operation.execute()

      expect(operation.data.value).toBe('success-data')
    })

    it('should return the result', async () => {
      const operation = useAsyncOperation(async () => 'returned-value')

      const result = await operation.execute()

      expect(result).toBe('returned-value')
    })

    it('should set error on failure', async () => {
      const error = new Error('Test error')
      const operation = useAsyncOperation(async () => {
        throw error
      })

      await operation.execute()

      expect(operation.error.value).toBe(error)
      expect(operation.isError.value).toBe(true)
    })

    it('should return null on failure', async () => {
      const operation = useAsyncOperation(async () => {
        throw new Error('Test error')
      })

      const result = await operation.execute()

      expect(result).toBeNull()
    })

    it('should clear previous error on new execution', async () => {
      let shouldFail = true
      const operation = useAsyncOperation(async () => {
        if (shouldFail) throw new Error('Fail')
        return 'success'
      })

      await operation.execute()
      expect(operation.error.value).not.toBeNull()

      shouldFail = false
      await operation.execute()

      expect(operation.error.value).toBeNull()
    })

    it('should pass params to the function', async () => {
      const fn = vi.fn(async (params: { id: number }) => params.id)
      const operation = useAsyncOperation(fn)

      await operation.execute({ id: 42 })

      expect(fn).toHaveBeenCalledWith({ id: 42 }, expect.any(AbortSignal))
    })

    it('should pass abort signal to the function', async () => {
      let receivedSignal: AbortSignal | null = null
      const operation = useAsyncOperation(async (_params: void, signal: AbortSignal) => {
        receivedSignal = signal
        return 'result'
      })

      await operation.execute()

      expect(receivedSignal).toBeInstanceOf(AbortSignal)
    })
  })

  describe('callbacks', () => {
    it('should call onSuccess callback', async () => {
      const onSuccess = vi.fn()
      const operation = useAsyncOperation(async () => 'success', { onSuccess })

      await operation.execute()

      expect(onSuccess).toHaveBeenCalledWith('success')
    })

    it('should call onError callback', async () => {
      const error = new Error('Test error')
      const onError = vi.fn()
      const operation = useAsyncOperation(async () => {
        throw error
      }, { onError })

      await operation.execute()

      expect(onError).toHaveBeenCalledWith(error)
    })
  })

  describe('abort()', () => {
    it('should abort the current operation', async () => {
      let aborted = false
      const operation = useAsyncOperation(async (_params: void, signal: AbortSignal) => {
        signal.addEventListener('abort', () => {
          aborted = true
        })
        await new Promise((resolve) => setTimeout(resolve, 100))
        return 'result'
      })

      operation.execute()
      operation.abort()

      expect(aborted).toBe(true)
    })

    it('should ignore abort errors by default', async () => {
      const operation = useAsyncOperation(async (_params: void, signal: AbortSignal) => {
        await new Promise((_, reject) => {
          signal.addEventListener('abort', () => {
            const error = new DOMException('Aborted', 'AbortError')
            reject(error)
          })
        })
        return 'result'
      })

      const executePromise = operation.execute()
      operation.abort()

      const result = await executePromise

      expect(result).toBeNull()
      expect(operation.error.value).toBeNull()
    })
  })

  describe('reset()', () => {
    it('should reset all state to initial values', async () => {
      const operation = useAsyncOperation(async () => 'result', {
        initialData: 'initial',
      })

      await operation.execute()
      expect(operation.data.value).toBe('result')
      expect(operation.executed.value).toBe(true)

      operation.reset()

      expect(operation.data.value).toBe('initial')
      expect(operation.error.value).toBeNull()
      expect(operation.loading.value).toBe(false)
      expect(operation.executed.value).toBe(false)
    })
  })

  describe('computed states', () => {
    it('isSuccess should be true after successful execution', async () => {
      const operation = useAsyncOperation(async () => 'result')

      expect(operation.isSuccess.value).toBe(false)

      await operation.execute()

      expect(operation.isSuccess.value).toBe(true)
    })

    it('isSuccess should be false when loading', async () => {
      let resolvePromise: (value: string) => void
      const promise = new Promise<string>((resolve) => {
        resolvePromise = resolve
      })
      const operation = useAsyncOperation(async () => promise)

      const executePromise = operation.execute()

      expect(operation.isSuccess.value).toBe(false)

      resolvePromise!('result')
      await executePromise
    })

    it('isError should be true when there is an error', async () => {
      const operation = useAsyncOperation(async () => {
        throw new Error('Fail')
      })

      await operation.execute()

      expect(operation.isError.value).toBe(true)
    })
  })

  describe('abortPrevious option', () => {
    it('should abort previous request when executing new one', async () => {
      let abortCount = 0
      const operation = useAsyncOperation(
        async (_params: void, signal: AbortSignal) => {
          signal.addEventListener('abort', () => {
            abortCount++
          })
          await new Promise((resolve) => setTimeout(resolve, 100))
          return 'result'
        },
        { abortPrevious: true }
      )

      operation.execute()
      operation.execute()

      expect(abortCount).toBe(1)
    })

    it('should not abort when abortPrevious is false', async () => {
      let abortCount = 0
      const operation = useAsyncOperation(
        async (_params: void, signal: AbortSignal) => {
          signal.addEventListener('abort', () => {
            abortCount++
          })
          await new Promise((resolve) => setTimeout(resolve, 100))
          return 'result'
        },
        { abortPrevious: false }
      )

      operation.execute()
      operation.execute()

      expect(abortCount).toBe(0)
    })
  })
})

describe('useAsyncState', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('should execute immediately by default', async () => {
    const fn = vi.fn().mockResolvedValue('result')
    useAsyncState(fn)

    // The function should be called synchronously
    expect(fn).toHaveBeenCalled()
  })

  it('should not execute immediately when immediate is false', () => {
    const fn = vi.fn().mockResolvedValue('result')
    useAsyncState(fn, null, { immediate: false })

    expect(fn).not.toHaveBeenCalled()
  })

  it('should delay execution when delay option is set', () => {
    const fn = vi.fn().mockResolvedValue('result')
    useAsyncState(fn, null, { delay: 1000 })

    expect(fn).not.toHaveBeenCalled()

    vi.advanceTimersByTime(1000)

    expect(fn).toHaveBeenCalled()
  })

  it('should return refresh function', async () => {
    const fn = vi.fn().mockResolvedValue('result')
    const state = useAsyncState(fn, null, { immediate: false })

    expect(state.refresh).toBeInstanceOf(Function)

    await state.refresh()

    expect(fn).toHaveBeenCalled()
  })

  it('should use initial data', () => {
    const fn = vi.fn().mockResolvedValue('new')
    const state = useAsyncState(fn, 'initial', { immediate: false })

    expect(state.data.value).toBe('initial')
  })
})

describe('useDebouncedOperation', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('should debounce execution', async () => {
    const fn = vi.fn().mockResolvedValue('result')
    const operation = useDebouncedOperation(fn, { debounce: 300 })

    operation.execute()
    operation.execute()
    operation.execute()

    expect(fn).not.toHaveBeenCalled()

    vi.advanceTimersByTime(300)

    // Need to wait for the promise to resolve
    await Promise.resolve()

    expect(fn).toHaveBeenCalledTimes(1)
  })

  it('should use default debounce of 300ms', async () => {
    const fn = vi.fn().mockResolvedValue('result')
    const operation = useDebouncedOperation(fn)

    operation.execute()

    vi.advanceTimersByTime(299)
    expect(fn).not.toHaveBeenCalled()

    vi.advanceTimersByTime(1)
    await Promise.resolve()

    expect(fn).toHaveBeenCalled()
  })

  it('should cancel previous debounce when called again', async () => {
    const fn = vi.fn().mockResolvedValue('result')
    const operation = useDebouncedOperation(fn, { debounce: 300 })

    // First call starts debounce timer
    operation.execute()

    // Advance time but not enough for debounce
    vi.advanceTimersByTime(200)

    // Second call should reset the debounce timer
    operation.execute()

    // Wait the full debounce time from first call
    vi.advanceTimersByTime(200)
    await Promise.resolve()

    // Function should not have been called yet (timer was reset)
    expect(fn).not.toHaveBeenCalled()

    // Wait remaining time for second debounce
    vi.advanceTimersByTime(100)
    await Promise.resolve()

    // Now it should have been called once
    expect(fn).toHaveBeenCalledTimes(1)
  })

  it('should pass params to debounced function', async () => {
    const fn = vi.fn().mockResolvedValue('result')
    const operation = useDebouncedOperation(fn, { debounce: 300 })

    operation.execute({ query: 'test' })

    vi.advanceTimersByTime(300)
    await Promise.resolve()

    expect(fn).toHaveBeenCalledWith({ query: 'test' }, expect.any(AbortSignal))
  })
})
