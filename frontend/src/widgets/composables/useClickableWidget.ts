/**
 * Composable for clickable widget elements with accessibility support
 */

import { computed, type Ref, type ComputedRef } from 'vue'

export interface ClickableOptions {
  isEditing?: Ref<boolean> | boolean
  disabled?: Ref<boolean> | boolean
}

/**
 * Unwrap a value that may be a ref or a plain value
 */
function unwrap<T>(value: Ref<T> | T): T {
  return typeof value === 'object' && value !== null && 'value' in value
    ? (value as Ref<T>).value
    : value
}

/**
 * Returns accessibility attributes for clickable widget elements
 */
export function useClickableAttrs(options: ClickableOptions = {}): {
  attrs: ComputedRef<{
    role: 'button'
    tabindex: number
    'aria-disabled': boolean
  }>
} {
  const attrs = computed(() => {
    const isInteractive = !unwrap(options.isEditing) && !unwrap(options.disabled)

    return {
      role: 'button' as const,
      tabindex: isInteractive ? 0 : -1,
      'aria-disabled': !isInteractive,
    }
  })

  return { attrs }
}

/**
 * Handle keyboard events for clickable elements
 * Supports Enter and Space keys
 */
export function handleKeyboardClick(event: KeyboardEvent, callback: () => void): void {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    callback()
  }
}

/**
 * Create a keydown handler for navigation
 * Returns a function that can be used directly in @keydown
 */
export function createKeydownHandler<T extends unknown[]>(
  callback: (...args: T) => void,
  ...args: T
): (event: KeyboardEvent) => void {
  return (event: KeyboardEvent) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      callback(...args)
    }
  }
}

/**
 * Composable for widget with clickable items
 * Provides common patterns for interactive widgets
 */
export function useWidgetInteraction(isEditing: Ref<boolean> | boolean) {
  const canInteract = computed(() => !unwrap(isEditing))

  const getClickableClass = (additionalClasses?: string) => {
    return computed(() => ({
      'clickable-item': true,
      'non-interactive': !canInteract.value,
      ...(additionalClasses ? { [additionalClasses]: true } : {}),
    }))
  }

  const getTabIndex = computed(() => (canInteract.value ? 0 : -1))

  return {
    canInteract,
    getClickableClass,
    getTabIndex,
    handleKeyboardClick,
  }
}
