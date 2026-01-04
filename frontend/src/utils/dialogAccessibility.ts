/**
 * Dialog Accessibility Utilities
 *
 * Provides helper functions and composables for improving
 * accessibility in dialog components.
 */
import { ref, onMounted, onUnmounted, nextTick, type Ref } from 'vue'

/**
 * Generates a unique ID for ARIA attributes
 */
export function generateAriaId(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).substr(2, 9)}`
}

/**
 * Hook for managing focus trap within dialogs
 */
export function useFocusTrap(containerRef: Ref<HTMLElement | null>) {
  const previousActiveElement = ref<HTMLElement | null>(null)

  const focusableSelectors = [
    'button:not([disabled])',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    'a[href]',
    '[tabindex]:not([tabindex="-1"])',
  ].join(', ')

  function getFocusableElements(): HTMLElement[] {
    if (!containerRef.value) return []
    return Array.from(
      containerRef.value.querySelectorAll<HTMLElement>(focusableSelectors)
    ).filter((el) => el.offsetParent !== null)
  }

  function handleKeyDown(event: KeyboardEvent) {
    if (event.key !== 'Tab') return

    const focusable = getFocusableElements()
    if (focusable.length === 0) return

    const first = focusable[0]
    const last = focusable[focusable.length - 1]

    if (event.shiftKey) {
      if (document.activeElement === first) {
        event.preventDefault()
        last.focus()
      }
    } else {
      if (document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }
  }

  function activate() {
    previousActiveElement.value = document.activeElement as HTMLElement
    document.addEventListener('keydown', handleKeyDown)

    // Focus first focusable element after mount
    nextTick(() => {
      const focusable = getFocusableElements()
      if (focusable.length > 0) {
        focusable[0].focus()
      }
    })
  }

  function deactivate() {
    document.removeEventListener('keydown', handleKeyDown)

    // Restore focus to previous element
    if (previousActiveElement.value) {
      previousActiveElement.value.focus()
    }
  }

  return {
    activate,
    deactivate,
  }
}

/**
 * Hook for announcing messages to screen readers
 */
export function useAriaLive() {
  const announcer = ref<HTMLElement | null>(null)

  function createAnnouncer() {
    announcer.value = document.createElement('div')
    announcer.value.setAttribute('role', 'status')
    announcer.value.setAttribute('aria-live', 'polite')
    announcer.value.setAttribute('aria-atomic', 'true')
    announcer.value.className = 'sr-only'
    document.body.appendChild(announcer.value)
  }

  function announce(message: string, priority: 'polite' | 'assertive' = 'polite') {
    if (!announcer.value) return

    announcer.value.setAttribute('aria-live', priority)
    announcer.value.textContent = ''

    // Use timeout to ensure screen readers pick up the change
    setTimeout(() => {
      if (announcer.value) {
        announcer.value.textContent = message
      }
    }, 100)
  }

  function cleanup() {
    if (announcer.value && announcer.value.parentNode) {
      announcer.value.parentNode.removeChild(announcer.value)
    }
  }

  onMounted(createAnnouncer)
  onUnmounted(cleanup)

  return { announce }
}

/**
 * Hook for managing dialog accessibility
 */
export function useDialogAccessibility(options: {
  titleId?: string
  descriptionId?: string
}) {
  const dialogRef = ref<HTMLElement | null>(null)
  const titleId = options.titleId || generateAriaId('dialog-title')
  const descriptionId = options.descriptionId || generateAriaId('dialog-desc')

  const focusTrap = useFocusTrap(dialogRef)

  function getDialogAttrs() {
    return {
      role: 'dialog',
      'aria-modal': true,
      'aria-labelledby': titleId,
      'aria-describedby': descriptionId,
    }
  }

  function onOpen() {
    focusTrap.activate()
  }

  function onClose() {
    focusTrap.deactivate()
  }

  return {
    dialogRef,
    titleId,
    descriptionId,
    getDialogAttrs,
    onOpen,
    onClose,
  }
}

/**
 * Keyboard shortcuts for common dialog actions
 */
export interface DialogKeyboardOptions {
  onEscape?: () => void
  onEnter?: () => void
}

export function useDialogKeyboard(options: DialogKeyboardOptions) {
  function handleKeyDown(event: KeyboardEvent) {
    if (event.key === 'Escape' && options.onEscape) {
      event.preventDefault()
      options.onEscape()
    } else if (event.key === 'Enter' && options.onEnter) {
      // Only trigger if not in a textarea or input that uses Enter
      const target = event.target as HTMLElement
      const tagName = target.tagName.toLowerCase()
      const isMultiline = tagName === 'textarea' ||
        (tagName === 'input' && target.getAttribute('type') === 'search')

      if (!isMultiline) {
        event.preventDefault()
        options.onEnter()
      }
    }
  }

  onMounted(() => {
    document.addEventListener('keydown', handleKeyDown)
  })

  onUnmounted(() => {
    document.removeEventListener('keydown', handleKeyDown)
  })
}

/**
 * CSS class for screen reader only content
 * Should be defined in global styles
 */
export const SR_ONLY_CLASS = 'sr-only'

export default {
  generateAriaId,
  useFocusTrap,
  useAriaLive,
  useDialogAccessibility,
  useDialogKeyboard,
  SR_ONLY_CLASS,
}
