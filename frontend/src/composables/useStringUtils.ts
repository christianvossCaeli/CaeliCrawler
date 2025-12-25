/**
 * String utility composable
 *
 * Provides common string manipulation functions for use across components.
 */

/**
 * Capitalize the first letter of a string
 *
 * @param str - The string to capitalize
 * @returns The string with first letter capitalized
 *
 * @example
 * capitalize('draft') // 'Draft'
 * capitalize('active') // 'Active'
 */
export function capitalize(str: string): string {
  if (!str) return ''
  return str.charAt(0).toUpperCase() + str.slice(1)
}

/**
 * Truncate a string to a maximum length with ellipsis
 *
 * @param str - The string to truncate
 * @param maxLength - Maximum length before truncation
 * @returns The truncated string with ellipsis if needed
 *
 * @example
 * truncate('Hello World', 5) // 'Hello...'
 */
export function truncate(str: string, maxLength: number): string {
  if (!str || str.length <= maxLength) return str
  return str.substring(0, maxLength) + '...'
}

/**
 * Convert a string to kebab-case
 *
 * @param str - The string to convert
 * @returns The kebab-case string
 *
 * @example
 * toKebabCase('helloWorld') // 'hello-world'
 */
export function toKebabCase(str: string): string {
  if (!str) return ''
  return str.replace(/([a-z])([A-Z])/g, '$1-$2').toLowerCase()
}

/**
 * Hook providing string utilities
 */
export function useStringUtils() {
  return {
    capitalize,
    truncate,
    toKebabCase,
  }
}
