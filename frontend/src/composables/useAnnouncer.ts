/**
 * ARIA Live Region Announcer Composable
 *
 * Provides a way to announce dynamic content changes to screen readers.
 * Uses ARIA live regions to notify users of updates without focus change.
 *
 * Usage:
 *   const { announce, announcePolite, announceAssertive } = useAnnouncer()
 *
 *   // For polite announcements (won't interrupt current speech)
 *   announcePolite('5 new results loaded')
 *
 *   // For assertive announcements (interrupts current speech)
 *   announceAssertive('Error: Failed to save')
 *
 *   // With custom options
 *   announce('Processing...', { politeness: 'polite', clearAfter: 5000 })
 */

import { ref, onMounted, onUnmounted } from 'vue'

interface AnnounceOptions {
  /** ARIA politeness level: 'polite' (default) or 'assertive' */
  politeness?: 'polite' | 'assertive'
  /** Clear the announcement after this many milliseconds (0 = don't clear) */
  clearAfter?: number
  /** Atomic update - read entire region when content changes */
  atomic?: boolean
}

interface AnnouncerState {
  politeMessage: string
  assertiveMessage: string
}

// Global state for announcer (singleton pattern)
const state = ref<AnnouncerState>({
  politeMessage: '',
  assertiveMessage: '',
})

let politeTimeout: ReturnType<typeof setTimeout> | null = null
let assertiveTimeout: ReturnType<typeof setTimeout> | null = null

/**
 * Get the global announcer instance.
 * Creates live regions in the DOM if they don't exist.
 */
export function useAnnouncer() {
  /**
   * Announce a message to screen readers.
   *
   * @param message - The message to announce
   * @param options - Announcement options
   */
  function announce(message: string, options: AnnounceOptions = {}): void {
    const {
      politeness = 'polite',
      clearAfter = 3000,
    } = options

    if (politeness === 'assertive') {
      // Clear any pending timeout
      if (assertiveTimeout) {
        clearTimeout(assertiveTimeout)
      }

      // Set message
      state.value.assertiveMessage = message

      // Auto-clear after delay
      if (clearAfter > 0) {
        assertiveTimeout = setTimeout(() => {
          state.value.assertiveMessage = ''
        }, clearAfter)
      }
    } else {
      // Polite announcement
      if (politeTimeout) {
        clearTimeout(politeTimeout)
      }

      state.value.politeMessage = message

      if (clearAfter > 0) {
        politeTimeout = setTimeout(() => {
          state.value.politeMessage = ''
        }, clearAfter)
      }
    }
  }

  /**
   * Make a polite announcement (won't interrupt current speech).
   * Use for non-urgent updates like "Results loaded" or "Item saved".
   */
  function announcePolite(message: string, clearAfter = 3000): void {
    announce(message, { politeness: 'polite', clearAfter })
  }

  /**
   * Make an assertive announcement (interrupts current speech).
   * Use for urgent updates like errors or critical notifications.
   */
  function announceAssertive(message: string, clearAfter = 5000): void {
    announce(message, { politeness: 'assertive', clearAfter })
  }

  /**
   * Clear all announcements.
   */
  function clearAnnouncements(): void {
    state.value.politeMessage = ''
    state.value.assertiveMessage = ''

    if (politeTimeout) {
      clearTimeout(politeTimeout)
      politeTimeout = null
    }
    if (assertiveTimeout) {
      clearTimeout(assertiveTimeout)
      assertiveTimeout = null
    }
  }

  /**
   * Announce when a list is updated with new items.
   */
  function announceListUpdate(count: number, itemType = 'Einträge'): void {
    if (count === 0) {
      announcePolite(`Keine ${itemType} gefunden`)
    } else if (count === 1) {
      announcePolite(`1 ${itemType.replace(/e$/, '')} gefunden`)
    } else {
      announcePolite(`${count} ${itemType} gefunden`)
    }
  }

  /**
   * Announce loading state changes.
   */
  function announceLoading(isLoading: boolean, context = ''): void {
    if (isLoading) {
      announcePolite(context ? `${context} wird geladen...` : 'Wird geladen...')
    } else {
      // Don't announce loading complete - let the content speak for itself
    }
  }

  /**
   * Announce an error.
   */
  function announceError(message: string): void {
    announceAssertive(`Fehler: ${message}`)
  }

  /**
   * Announce a success action.
   */
  function announceSuccess(message: string): void {
    announcePolite(message)
  }

  return {
    // State (for binding to live regions)
    state,

    // Core methods
    announce,
    announcePolite,
    announceAssertive,
    clearAnnouncements,

    // Helper methods for common patterns
    announceListUpdate,
    announceLoading,
    announceError,
    announceSuccess,
  }
}

// Type export for component props
export type { AnnounceOptions, AnnouncerState }
