/**
 * Global Crawler Event Bus
 *
 * Provides a simple pub/sub event system for crawler-related events.
 * Enables cross-view communication when crawls are started, completed, or cancelled.
 *
 * @example
 * // Emitting events (from any view that starts a crawl)
 * import { emitCrawlerEvent } from '@/composables/useCrawlerEvents'
 * emitCrawlerEvent('crawl-started', { sourceIds: ['123'] })
 *
 * @example
 * // Subscribing to events (in CrawlerView)
 * import { onCrawlerEvent } from '@/composables/useCrawlerEvents'
 * const unsubscribe = onCrawlerEvent((event) => {
 *   if (event.type === 'crawl-started') refreshData()
 * })
 * onUnmounted(() => unsubscribe())
 */

// =============================================================================
// Types
// =============================================================================

export type CrawlerEventType = 'crawl-started' | 'crawl-completed' | 'crawl-cancelled'

export interface CrawlerEvent {
  readonly type: CrawlerEventType
  readonly sourceIds?: string[]
  readonly jobId?: string
  readonly timestamp: number
}

type CrawlerEventListener = (event: CrawlerEvent) => void

// =============================================================================
// Global State (Module-level singleton)
// =============================================================================

const listeners = new Set<CrawlerEventListener>()

// =============================================================================
// Public API
// =============================================================================

/**
 * Emit a crawler event to all registered listeners
 */
export function emitCrawlerEvent(
  type: CrawlerEventType,
  data?: Partial<Omit<CrawlerEvent, 'type' | 'timestamp'>>
): void {
  const event: CrawlerEvent = Object.freeze({
    type,
    ...data,
    timestamp: Date.now(),
  })

  listeners.forEach(listener => {
    try {
      listener(event)
    } catch {
      // Silently ignore listener errors to prevent cascading failures
    }
  })
}

/**
 * Subscribe to crawler events
 * @returns Cleanup function to unsubscribe
 */
export function onCrawlerEvent(listener: CrawlerEventListener): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

/**
 * Composable wrapper for reactive usage in components
 */
export function useCrawlerEvents() {
  return {
    emit: emitCrawlerEvent,
    on: onCrawlerEvent,
  } as const
}
