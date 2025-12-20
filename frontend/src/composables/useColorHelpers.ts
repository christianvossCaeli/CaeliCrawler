/**
 * Color helper utilities for theme-aware icon/text colors
 */

/**
 * Check if a hex color is light (needs dark text/icons)
 */
export function isLightColor(color: string | undefined): boolean {
  if (!color) return false
  // Handle named colors - these are Vuetify theme colors, not hex
  if (!color.startsWith('#')) return false

  const hex = color.replace('#', '')
  if (hex.length !== 6 && hex.length !== 3) return false

  // Expand 3-digit hex
  const fullHex = hex.length === 3
    ? hex.split('').map(c => c + c).join('')
    : hex

  const r = parseInt(fullHex.substr(0, 2), 16)
  const g = parseInt(fullHex.substr(2, 2), 16)
  const b = parseInt(fullHex.substr(4, 2), 16)

  // Calculate relative luminance using ITU-R BT.709 formula
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  return luminance > 0.6
}

/**
 * Get the appropriate icon/text color for a given background color
 * @param bgColor - The background color (hex or Vuetify semantic color)
 * @param fallbackDark - Color to use for light backgrounds (default: 'black')
 * @param fallbackLight - Color to use for dark backgrounds (default: 'white')
 */
export function getContrastColor(
  bgColor: string | undefined,
  fallbackDark = 'black',
  fallbackLight = 'white'
): string {
  if (!bgColor) return fallbackLight

  // Handle Vuetify semantic colors - use on-* variant
  const semanticColors = ['primary', 'secondary', 'success', 'info', 'warning', 'error']
  const baseColor = bgColor.replace(/-darken-\d+|-lighten-\d+/, '')

  if (semanticColors.includes(baseColor)) {
    return `on-${baseColor}`
  }

  // Handle hex colors
  if (bgColor.startsWith('#')) {
    return isLightColor(bgColor) ? fallbackDark : fallbackLight
  }

  // Default for unknown colors
  return fallbackLight
}

/**
 * Vue composable for color helpers
 */
export function useColorHelpers() {
  return {
    isLightColor,
    getContrastColor
  }
}
