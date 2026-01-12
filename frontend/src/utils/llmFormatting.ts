/**
 * LLM Formatting Utilities
 *
 * Pure functions for formatting currency, percentages, dates,
 * and status colors in LLM-related UI components.
 */

import type { LimitRequestStatus, UserBudgetStatus } from '@/types/llm-usage'

/**
 * Status color mapping for limit requests
 * Using consistent 'warning' for pending to draw attention
 */
export const LIMIT_REQUEST_COLORS: Record<LimitRequestStatus, string> = {
  PENDING: 'warning',
  APPROVED: 'success',
  DENIED: 'error',
}

/**
 * Status icons for limit requests
 */
export const LIMIT_REQUEST_ICONS: Record<LimitRequestStatus, string> = {
  PENDING: 'mdi-clock-outline',
  APPROVED: 'mdi-check-circle',
  DENIED: 'mdi-close-circle',
}

/**
 * Format cents as USD currency string
 * @param cents - Amount in cents
 * @returns Formatted string like "$12.34"
 */
export function formatCurrency(cents: number): string {
  return `$${(cents / 100).toFixed(2)}`
}

/**
 * Format token counts with K/M suffix for readability
 * @param tokens - Number of tokens
 * @returns Formatted string like "1.5M" or "150K"
 */
export function formatTokens(tokens: number): string {
  if (tokens >= 1000000) {
    return `${(tokens / 1000000).toFixed(1)}M`
  }
  if (tokens >= 1000) {
    return `${(tokens / 1000).toFixed(1)}K`
  }
  return tokens.toString()
}

/**
 * Format a percentage value
 * @param value - Percentage value
 * @param decimals - Number of decimal places (default: 0)
 * @returns Formatted string like "85"
 */
export function formatPercent(value: number, decimals = 0): string {
  return value.toFixed(decimals)
}

/**
 * Calculate percentage increase between two values
 * @param requested - New value
 * @param current - Original value
 * @returns Percentage increase as string
 */
export function formatPercentIncrease(requested: number, current: number): string {
  if (current === 0) return '0'
  const increase = ((requested - current) / current) * 100
  return increase.toFixed(0)
}

/**
 * Format date for display in lists and tables
 * @param dateStr - ISO date string
 * @param detailed - Include time if true
 * @returns Localized date string
 */
export function formatDate(dateStr: string, detailed = false): string {
  const date = new Date(dateStr)

  if (detailed) {
    return date.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return date.toLocaleDateString()
}

/**
 * Get the color for a limit request status
 * @param status - The request status
 * @returns Vuetify color name
 */
export function getStatusColor(status: LimitRequestStatus): string {
  return LIMIT_REQUEST_COLORS[status] ?? 'grey'
}

/**
 * Get the icon for a limit request status
 * @param status - The request status
 * @returns MDI icon name
 */
export function getStatusIcon(status: LimitRequestStatus): string {
  return LIMIT_REQUEST_ICONS[status] ?? 'mdi-help-circle'
}

/**
 * Get the appropriate color based on budget usage level
 * @param status - User budget status object
 * @returns Vuetify color name
 */
export function getBudgetColor(status: UserBudgetStatus | null): string {
  if (!status) return 'grey'
  if (status.is_blocked) return 'error'
  if (status.is_critical) return 'error'
  if (status.is_warning) return 'warning'
  return 'success'
}

/**
 * Vuetify alert types
 */
export type VuetifyAlertType = 'info' | 'error' | 'success' | 'warning'

/**
 * Get the appropriate alert type based on budget usage level
 * @param status - User budget status object
 * @returns Vuetify alert type
 */
export function getBudgetAlertType(status: UserBudgetStatus | null): VuetifyAlertType {
  if (!status) return 'info'
  if (status.is_blocked) return 'error'
  if (status.is_critical) return 'error'
  if (status.is_warning) return 'warning'
  return 'success'
}
