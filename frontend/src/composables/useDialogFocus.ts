/**
 * Dialog focus management composable.
 *
 * Handles proper focus management for dialogs and modals:
 * - Saves the previously focused element when dialog opens
 * - Restores focus when dialog closes
 * - Optionally focuses a specific element inside the dialog
 *
 * This is important for accessibility (WCAG 2.1) and keyboard navigation.
 */

import { ref, watch, nextTick, type Ref, type ModelRef } from 'vue'

export interface UseDialogFocusOptions {
  /**
   * Ref to the dialog's open state.
   * Accepts both Ref<boolean> and ModelRef<boolean | undefined> from defineModel()
   */
  isOpen: Ref<boolean> | Ref<boolean | undefined> | ModelRef<boolean | undefined>

  /**
   * Optional: Selector for the element to focus when dialog opens.
   * If not provided, the first focusable element in the dialog will be focused.
   */
  initialFocusSelector?: string

  /**
   * Optional: Ref to the dialog container element.
   * If provided, will auto-focus first focusable element.
   */
  dialogRef?: Ref<HTMLElement | null>

  /**
   * Whether to restore focus on close. Default: true
   */
  restoreFocusOnClose?: boolean
}

export interface UseDialogFocusReturn {
  /**
   * Call this when the dialog opens to save the current focus.
   */
  saveFocus: () => void

  /**
   * Call this when the dialog closes to restore focus.
   */
  restoreFocus: () => void

  /**
   * The element that was focused before the dialog opened.
   */
  previousActiveElement: Ref<HTMLElement | null>
}

/**
 * Focusable element selectors for finding the first focusable element.
 */
const FOCUSABLE_SELECTORS = [
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  'a[href]',
  '[tabindex]:not([tabindex="-1"])',
].join(', ')

/**
 * Composable for managing dialog focus.
 *
 * @example
 * const { saveFocus, restoreFocus } = useDialogFocus({
 *   isOpen: dialogOpen,
 *   dialogRef: dialogElement,
 * })
 *
 * // Or with manual control:
 * watch(dialogOpen, (open) => {
 *   if (open) {
 *     saveFocus()
 *   } else {
 *     restoreFocus()
 *   }
 * })
 */
export function useDialogFocus(options: UseDialogFocusOptions): UseDialogFocusReturn {
  const {
    isOpen,
    initialFocusSelector,
    dialogRef,
    restoreFocusOnClose = true,
  } = options

  const previousActiveElement = ref<HTMLElement | null>(null)

  /**
   * Save the currently focused element.
   */
  function saveFocus(): void {
    previousActiveElement.value = document.activeElement as HTMLElement
  }

  /**
   * Restore focus to the previously focused element.
   */
  function restoreFocus(): void {
    if (previousActiveElement.value && typeof previousActiveElement.value.focus === 'function') {
      // Use nextTick to ensure the dialog is fully closed
      nextTick(() => {
        previousActiveElement.value?.focus()
        previousActiveElement.value = null
      })
    }
  }

  /**
   * Focus the first focusable element in the dialog.
   */
  function focusFirstElement(): void {
    nextTick(() => {
      const container = dialogRef?.value

      if (!container) return

      // Try to focus the specified element first
      if (initialFocusSelector) {
        const target = container.querySelector<HTMLElement>(initialFocusSelector)
        if (target) {
          target.focus()
          return
        }
      }

      // Fall back to first focusable element
      const firstFocusable = container.querySelector<HTMLElement>(FOCUSABLE_SELECTORS)
      if (firstFocusable) {
        firstFocusable.focus()
      }
    })
  }

  // Auto-manage focus when isOpen changes
  watch(isOpen, (open) => {
    if (open) {
      saveFocus()
      if (dialogRef) {
        focusFirstElement()
      }
    } else if (restoreFocusOnClose) {
      restoreFocus()
    }
  })

  return {
    saveFocus,
    restoreFocus,
    previousActiveElement,
  }
}

/**
 * Simple focus trap for dialogs.
 *
 * Keeps focus within the dialog when tabbing.
 */
export function useFocusTrap(containerRef: Ref<HTMLElement | null>) {
  function handleKeyDown(event: KeyboardEvent): void {
    if (event.key !== 'Tab' || !containerRef.value) return

    const focusableElements = containerRef.value.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTORS)
    const firstElement = focusableElements[0]
    const lastElement = focusableElements[focusableElements.length - 1]

    if (!firstElement || !lastElement) return

    if (event.shiftKey) {
      // Shift + Tab: If on first element, go to last
      if (document.activeElement === firstElement) {
        event.preventDefault()
        lastElement.focus()
      }
    } else {
      // Tab: If on last element, go to first
      if (document.activeElement === lastElement) {
        event.preventDefault()
        firstElement.focus()
      }
    }
  }

  return {
    handleKeyDown,
  }
}
