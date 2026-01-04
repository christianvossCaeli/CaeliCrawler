/**
 * useNotifications Composable
 *
 * Wrapper around the Pinia notifications store for backwards compatibility.
 * New code should prefer using useNotificationsStore() directly.
 *
 * @deprecated Use useNotificationsStore() from '@/stores/notifications' instead
 */

import { storeToRefs } from 'pinia'
import {
  useNotificationsStore,
  type Notification,
  type NotificationRule,
  type NotificationRuleConditions,
  type NotificationRuleChannelConfig,
  type UserEmailAddress,
  type EventType,
  type Channel,
  type NotificationPreferences,
} from '@/stores/notifications'

// Re-export types for backwards compatibility
export type {
  Notification,
  NotificationRule,
  NotificationRuleConditions,
  NotificationRuleChannelConfig,
  UserEmailAddress,
  EventType,
  Channel,
  NotificationPreferences,
}

/**
 * Composable for notifications management
 *
 * @deprecated Use useNotificationsStore() directly for better performance
 */
export function useNotifications() {
  const store = useNotificationsStore()

  // Use storeToRefs for reactive state
  const {
    notifications,
    rules,
    emailAddresses,
    eventTypes,
    channels,
    preferences,
    unreadCount,
    loading,
    error,
    totalNotifications,
    currentPage,
    perPage,
    hasUnread,
    totalPages,
    sseConnected,
  } = storeToRefs(store)

  return {
    // State (reactive refs from store)
    notifications,
    rules,
    emailAddresses,
    eventTypes,
    channels,
    preferences,
    unreadCount,
    loading,
    error,
    totalNotifications,
    currentPage,
    perPage,
    sseConnected,

    // Computed
    hasUnread,
    totalPages,

    // Actions (bound to store)
    loadNotifications: store.loadNotifications,
    loadUnreadCount: store.loadUnreadCount,
    loadRules: store.loadRules,
    loadEmailAddresses: store.loadEmailAddresses,
    loadMeta: store.loadMeta,
    loadPreferences: store.loadPreferences,
    markAsRead: store.markAsRead,
    markAllAsRead: store.markAllAsRead,
    createRule: store.createRule,
    updateRule: store.updateRule,
    deleteRule: store.deleteRule,
    toggleRuleActive: store.toggleRuleActive,
    addEmailAddress: store.addEmailAddress,
    deleteEmailAddress: store.deleteEmailAddress,
    updatePreferences: store.updatePreferences,
    testWebhook: store.testWebhook,

    // SSE actions
    initRealtime: store.initRealtime,
    cleanupRealtime: store.cleanupRealtime,
    connectSSE: store.connectSSE,
    disconnectSSE: store.disconnectSSE,
  }
}
