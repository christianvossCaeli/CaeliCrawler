/**
 * Global UI Constants
 *
 * Centralized configuration for consistent UI sizing across the application.
 */

/**
 * Standard Dialog Sizes
 *
 * Use these constants for all v-dialog max-width values to ensure consistency.
 *
 * Usage:
 * ```vue
 * <v-dialog :max-width="DIALOG_SIZES.MD">
 * ```
 *
 * Size Guide:
 * - XS: Simple confirmations, alerts (delete confirm, logout confirm)
 * - SM: Simple forms, info dialogs (add field, settings)
 * - MD: Medium forms, details dialogs (edit entity, notifications)
 * - LG: Complex forms, multi-section dialogs (source form, bulk import)
 * - XL: Full-featured dialogs with tables/wizards (AI discovery, API import)
 */
export const DIALOG_SIZES = {
  /** Extra small: Confirmations and alerts (400px) */
  XS: 400,
  /** Small: Simple forms and info dialogs (500px) */
  SM: 500,
  /** Medium: Standard forms and detail views (600px) */
  MD: 600,
  /** Medium-Large: Complex forms (700px) */
  ML: 700,
  /** Large: Multi-section dialogs (800px) */
  LG: 800,
  /** Extra large: Full-featured dialogs with tables (900px) */
  XL: 900,
  /** Extra-extra large: Wizards and comprehensive views (1200px) */
  XXL: 1200,
} as const

export type DialogSize = (typeof DIALOG_SIZES)[keyof typeof DIALOG_SIZES]

/**
 * Standard Breakpoints for responsive dialogs
 */
export const DIALOG_FULLSCREEN_BREAKPOINT = 'sm'

/**
 * Common table row heights
 */
export const TABLE_ROW_HEIGHT = {
  COMPACT: 40,
  DEFAULT: 52,
  COMFORTABLE: 64,
} as const

/**
 * Common card elevations
 */
export const CARD_ELEVATION = {
  FLAT: 0,
  SUBTLE: 1,
  DEFAULT: 2,
  RAISED: 4,
  FLOATING: 8,
} as const

/**
 * Common spacing values (based on 4px grid)
 */
export const SPACING = {
  XS: 1, // 4px
  SM: 2, // 8px
  MD: 4, // 16px
  LG: 6, // 24px
  XL: 8, // 32px
} as const
