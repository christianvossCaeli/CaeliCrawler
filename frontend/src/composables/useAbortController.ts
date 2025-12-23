/**
 * useAbortController - Composable for managing request cancellation
 *
 * Provides AbortController management for HTTP requests with automatic
 * cleanup on component unmount.
 *
 * @example
 * ```ts
 * const { signal, abort, reset, isAborted } = useAbortController()
 *
 * const fetchData = async () => {
 *   abort() // Cancel previous request
 *   reset() // Create new controller
 *   try {
 *     const response = await fetch('/api/data', { signal: signal.value })
 *     // handle response
 *   } catch (error) {
 *     if (!isAborted.value) throw error
 *   }
 * }
 * ```
 */
import { ref, onUnmounted, readonly } from 'vue'

export interface UseAbortControllerReturn {
  /** The current AbortSignal for passing to fetch/axios */
  signal: ReturnType<typeof ref<AbortSignal | undefined>>
  /** Whether the current request has been aborted */
  isAborted: ReturnType<typeof readonly<ReturnType<typeof ref<boolean>>>>
  /** Abort the current request */
  abort: (reason?: string) => void
  /** Reset the controller for a new request */
  reset: () => void
  /** Get raw abort controller (for advanced use) */
  getController: () => AbortController | null
}

export function useAbortController(): UseAbortControllerReturn {
  let controller: AbortController | null = null
  const signal = ref<AbortSignal | undefined>(undefined)
  const isAborted = ref(false)

  /**
   * Creates a new AbortController and updates the signal
   */
  const reset = () => {
    // Abort any existing request first
    if (controller) {
      controller.abort()
    }
    controller = new AbortController()
    signal.value = controller.signal
    isAborted.value = false
  }

  /**
   * Aborts the current request with optional reason
   */
  const abort = (reason?: string) => {
    if (controller) {
      controller.abort(reason)
      isAborted.value = true
    }
  }

  /**
   * Get the raw AbortController for advanced use cases
   */
  const getController = () => controller

  // Cleanup on unmount
  onUnmounted(() => {
    if (controller) {
      controller.abort('Component unmounted')
      controller = null
    }
  })

  // Initialize with a controller
  reset()

  return {
    signal,
    isAborted: readonly(isAborted),
    abort,
    reset,
    getController,
  }
}

/**
 * useMultiAbortController - Manage multiple named abort controllers
 *
 * Useful when a component needs to manage multiple independent requests.
 *
 * @example
 * ```ts
 * const { getSignal, abort, abortAll, reset } = useMultiAbortController()
 *
 * const fetchUsers = async () => {
 *   const signal = reset('users')
 *   await fetch('/api/users', { signal })
 * }
 *
 * const fetchPosts = async () => {
 *   const signal = reset('posts')
 *   await fetch('/api/posts', { signal })
 * }
 *
 * // Abort specific request
 * abort('users')
 *
 * // Abort all requests
 * abortAll()
 * ```
 */
export interface UseMultiAbortControllerReturn {
  /** Get signal for a named controller */
  getSignal: (name: string) => AbortSignal | undefined
  /** Abort a specific named controller */
  abort: (name: string, reason?: string) => void
  /** Abort all controllers */
  abortAll: (reason?: string) => void
  /** Reset/create a named controller, returns new signal */
  reset: (name: string) => AbortSignal
  /** Check if a named controller is aborted */
  isAborted: (name: string) => boolean
}

export function useMultiAbortController(): UseMultiAbortControllerReturn {
  const controllers = new Map<string, AbortController>()

  /**
   * Get signal for a named controller
   */
  const getSignal = (name: string): AbortSignal | undefined => {
    return controllers.get(name)?.signal
  }

  /**
   * Reset/create a named controller
   */
  const reset = (name: string): AbortSignal => {
    // Abort existing if any
    const existing = controllers.get(name)
    if (existing) {
      existing.abort()
    }

    const controller = new AbortController()
    controllers.set(name, controller)
    return controller.signal
  }

  /**
   * Abort a specific controller
   */
  const abort = (name: string, reason?: string) => {
    const controller = controllers.get(name)
    if (controller) {
      controller.abort(reason)
    }
  }

  /**
   * Abort all controllers
   */
  const abortAll = (reason?: string) => {
    controllers.forEach((controller) => {
      controller.abort(reason)
    })
    controllers.clear()
  }

  /**
   * Check if a controller is aborted
   */
  const isAborted = (name: string): boolean => {
    const controller = controllers.get(name)
    return controller?.signal.aborted ?? false
  }

  // Cleanup on unmount
  onUnmounted(() => {
    abortAll('Component unmounted')
  })

  return {
    getSignal,
    abort,
    abortAll,
    reset,
    isAborted,
  }
}

/**
 * Check if an error is an abort error
 */
export function isAbortError(error: unknown): boolean {
  if (error instanceof Error) {
    return error.name === 'AbortError' || error.message === 'canceled'
  }
  return false
}

/**
 * Create a timeout signal that auto-aborts after specified milliseconds
 */
export function createTimeoutSignal(ms: number): AbortSignal {
  const controller = new AbortController()
  setTimeout(() => controller.abort(`Timeout after ${ms}ms`), ms)
  return controller.signal
}

/**
 * Combine multiple signals into one (aborts when any signal aborts)
 */
export function combineSignals(...signals: (AbortSignal | undefined)[]): AbortSignal {
  const controller = new AbortController()
  const filteredSignals = signals.filter(Boolean) as AbortSignal[]

  for (const signal of filteredSignals) {
    if (signal.aborted) {
      controller.abort(signal.reason)
      return controller.signal
    }

    signal.addEventListener('abort', () => {
      controller.abort(signal.reason)
    }, { once: true })
  }

  return controller.signal
}
