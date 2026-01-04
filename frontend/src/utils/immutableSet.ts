/**
 * Immutable Set Utilities
 *
 * Provides helper functions for immutable Set operations that trigger Vue reactivity.
 * Direct mutations like set.add() or set.delete() on a reactive Set won't trigger
 * Vue's reactivity system properly. These utilities create new Set instances instead.
 *
 * @example
 * ```ts
 * import { addToSet, removeFromSet, clearSet } from '@/utils/immutableSet'
 *
 * const ids = ref<Set<string>>(new Set())
 *
 * // Add an item
 * ids.value = addToSet(ids.value, 'new-id')
 *
 * // Remove an item
 * ids.value = removeFromSet(ids.value, 'old-id')
 *
 * // Clear all items
 * ids.value = clearSet()
 * ```
 */

/**
 * Creates a new Set with the item added
 */
export function addToSet<T>(set: Set<T>, item: T): Set<T> {
  return new Set([...set, item])
}

/**
 * Creates a new Set with the item removed
 */
export function removeFromSet<T>(set: Set<T>, item: T): Set<T> {
  const newSet = new Set(set)
  newSet.delete(item)
  return newSet
}

/**
 * Creates a new Set with multiple items added
 */
export function addManyToSet<T>(set: Set<T>, items: T[]): Set<T> {
  return new Set([...set, ...items])
}

/**
 * Creates a new Set with multiple items removed
 */
export function removeManyFromSet<T>(set: Set<T>, items: T[]): Set<T> {
  const itemsToRemove = new Set(items)
  return new Set([...set].filter((item) => !itemsToRemove.has(item)))
}

/**
 * Returns an empty Set (for clearing)
 */
export function clearSet<T>(): Set<T> {
  return new Set<T>()
}

/**
 * Toggles an item in a Set - adds if not present, removes if present
 */
export function toggleInSet<T>(set: Set<T>, item: T): Set<T> {
  if (set.has(item)) {
    return removeFromSet(set, item)
  }
  return addToSet(set, item)
}
