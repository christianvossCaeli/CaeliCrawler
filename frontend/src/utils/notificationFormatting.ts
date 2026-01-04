/**
 * Shared utilities for notification formatting
 * Used by NotificationInbox.vue and NotificationRules.vue
 */

import type { Ref } from 'vue'

export interface EventTypeOption {
  value: string
  label: string
  description?: string
}

export interface ChannelOption {
  value: string
  label: string
  description?: string
  available?: boolean
}

// Event Type Colors (Vuetify color names)
const EVENT_TYPE_COLORS: Record<string, string> = {
  NEW_DOCUMENT: 'success',
  DOCUMENT_CHANGED: 'info',
  DOCUMENT_REMOVED: 'error',
  CRAWL_STARTED: 'purple',
  CRAWL_COMPLETED: 'success',
  CRAWL_FAILED: 'error',
  AI_ANALYSIS_COMPLETED: 'cyan',
  HIGH_CONFIDENCE_RESULT: 'orange',
  SOURCE_STATUS_CHANGED: 'grey',
  SOURCE_ERROR: 'error',
  SUMMARY_UPDATED: 'teal',
  SUMMARY_RELEVANT_CHANGES: 'amber',
  FACET_TYPE_AUTO_CREATED: 'indigo',
}

// Event Type Icons (Material Design Icons)
const EVENT_TYPE_ICONS: Record<string, string> = {
  NEW_DOCUMENT: 'mdi-file-document-plus',
  DOCUMENT_CHANGED: 'mdi-file-document-edit',
  DOCUMENT_REMOVED: 'mdi-file-document-remove',
  CRAWL_STARTED: 'mdi-play-circle',
  CRAWL_COMPLETED: 'mdi-check-circle',
  CRAWL_FAILED: 'mdi-alert-circle',
  AI_ANALYSIS_COMPLETED: 'mdi-brain',
  HIGH_CONFIDENCE_RESULT: 'mdi-star',
  SOURCE_STATUS_CHANGED: 'mdi-sync',
  SOURCE_ERROR: 'mdi-alert',
  SUMMARY_UPDATED: 'mdi-file-document-check',
  SUMMARY_RELEVANT_CHANGES: 'mdi-file-document-alert',
  FACET_TYPE_AUTO_CREATED: 'mdi-tag-plus',
}

// Channel Colors (Vuetify color names)
const CHANNEL_COLORS: Record<string, string> = {
  EMAIL: 'blue',
  WEBHOOK: 'purple',
  IN_APP: 'green',
  MS_TEAMS: 'indigo',
  PUSH: 'orange',
}

// Channel Icons (Material Design Icons)
const CHANNEL_ICONS: Record<string, string> = {
  EMAIL: 'mdi-email',
  WEBHOOK: 'mdi-webhook',
  IN_APP: 'mdi-bell',
  MS_TEAMS: 'mdi-microsoft-teams',
  PUSH: 'mdi-cellphone-message',
}

/**
 * Get the color for an event type
 */
export function getEventTypeColor(eventType: string): string {
  return EVENT_TYPE_COLORS[eventType] || 'grey'
}

/**
 * Get the icon for an event type
 */
export function getEventTypeIcon(eventType: string): string {
  return EVENT_TYPE_ICONS[eventType] || 'mdi-bell'
}

/**
 * Get the color for a notification channel
 */
export function getChannelColor(channel: string): string {
  return CHANNEL_COLORS[channel] || 'grey'
}

/**
 * Get the icon for a notification channel
 */
export function getChannelIcon(channel: string): string {
  return CHANNEL_ICONS[channel] || 'mdi-bell'
}

/**
 * Composable for notification formatting with i18n support
 * Accepts reactive refs for eventTypes and channels
 */
export function useNotificationFormatting(
  eventTypes: Ref<EventTypeOption[]>,
  channels: Ref<ChannelOption[]>
) {
  /**
   * Get the localized label for an event type
   */
  const getEventTypeLabel = (eventType: string): string => {
    const type = eventTypes.value.find((e) => e.value === eventType)
    return type?.label || eventType
  }

  /**
   * Get the localized label for a channel
   */
  const getChannelLabel = (channel: string): string => {
    const ch = channels.value.find((c) => c.value === channel)
    return ch?.label || channel
  }

  return {
    getEventTypeColor,
    getEventTypeIcon,
    getEventTypeLabel,
    getChannelColor,
    getChannelIcon,
    getChannelLabel,
  }
}

// Export constants for direct access if needed
export { EVENT_TYPE_COLORS, EVENT_TYPE_ICONS, CHANNEL_COLORS, CHANNEL_ICONS }
