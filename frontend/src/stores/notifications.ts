/**
 * Notifications Store
 *
 * Manages notification state including:
 * - Notification inbox
 * - Notification rules
 * - Email addresses for notifications
 * - User preferences
 * - SSE real-time updates
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { notificationApi } from '@/services/api'
import { useLogger } from '@/composables/useLogger'
import { getErrorMessage } from '@/utils/errorMessage'
import { useAuthStore } from './auth'

const logger = useLogger('NotificationsStore')

// SSE polling fallback interval (ms)
const POLLING_INTERVAL = 30000

// Types
export interface Notification {
  id: string
  event_type: string
  channel: string
  title: string
  body: string
  status: string
  related_entity_type?: string
  related_entity_id?: string
  sent_at?: string
  read_at?: string
  created_at: string
}

export interface NotificationRuleConditions {
  min_confidence?: number | null
  keywords?: string[]
  [key: string]: unknown
}

export interface NotificationRuleChannelConfig {
  email_address_ids?: string[]
  include_primary?: boolean
  url?: string
  auth?: {
    type: string
    token?: string
    username?: string
    password?: string
  }
  [key: string]: unknown
}

export interface NotificationRule {
  id: string
  name: string
  description?: string
  event_type: string
  channel: string
  conditions: NotificationRuleConditions
  channel_config: NotificationRuleChannelConfig
  digest_enabled: boolean
  digest_frequency?: string
  is_active: boolean
  trigger_count: number
  last_triggered?: string
  created_at: string
  updated_at: string
}

export interface UserEmailAddress {
  id: string
  email: string
  label?: string
  is_verified: boolean
  is_primary: boolean
  created_at: string
}

export interface EventType {
  value: string
  label: string
  description: string
}

export interface Channel {
  value: string
  label: string
  description: string
  available: boolean
}

export interface NotificationPreferences {
  notifications_enabled: boolean
  notification_digest_time?: string
}

export const useNotificationsStore = defineStore('notifications', () => {
  // ==================
  // State
  // ==================
  const notifications = ref<Notification[]>([])
  const rules = ref<NotificationRule[]>([])
  const emailAddresses = ref<UserEmailAddress[]>([])
  const eventTypes = ref<EventType[]>([])
  const channels = ref<Channel[]>([])
  const preferences = ref<NotificationPreferences>({
    notifications_enabled: true,
    notification_digest_time: undefined,
  })
  const unreadCount = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Pagination
  const totalNotifications = ref(0)
  const currentPage = ref(1)
  const perPage = ref(20)

  // SSE state
  const sseConnected = ref(false)
  const useSSE = ref(true)
  let eventSource: EventSource | null = null
  let pollingInterval: number | null = null

  // ==================
  // Computed
  // ==================
  const hasUnread = computed(() => unreadCount.value > 0)
  const totalPages = computed(() => Math.ceil(totalNotifications.value / perPage.value))

  // ==================
  // Actions - Notifications
  // ==================

  /**
   * Load notifications with optional filtering
   */
  async function loadNotifications(params?: {
    status?: string
    channel?: string
    event_type?: string
    page?: number
    per_page?: number
  }): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const response = await notificationApi.getNotifications(params)
      notifications.value = response.data.items
      totalNotifications.value = response.data.total
      currentPage.value = response.data.page
      perPage.value = response.data.per_page
    } catch (e: unknown) {
      error.value = getErrorMessage(e) || 'Fehler beim Laden der Benachrichtigungen'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * Load unread notification count
   */
  async function loadUnreadCount(): Promise<void> {
    try {
      const response = await notificationApi.getUnreadCount()
      unreadCount.value = response.data.count
    } catch (e) {
      logger.error('Failed to load unread count:', e)
    }
  }

  /**
   * Mark a notification as read
   */
  async function markAsRead(id: string): Promise<void> {
    try {
      await notificationApi.markAsRead(id)
      const notification = notifications.value.find((n) => n.id === id)
      if (notification && !notification.read_at) {
        notification.read_at = new Date().toISOString()
        notification.status = 'READ'
        if (unreadCount.value > 0) unreadCount.value--
      }
    } catch (e: unknown) {
      error.value = getErrorMessage(e) || 'Fehler beim Markieren als gelesen'
      throw e
    }
  }

  /**
   * Mark all notifications as read
   */
  async function markAllAsRead(): Promise<void> {
    try {
      await notificationApi.markAllAsRead()
      notifications.value.forEach((n) => {
        if (!n.read_at) {
          n.read_at = new Date().toISOString()
          n.status = 'READ'
        }
      })
      unreadCount.value = 0
    } catch (e: unknown) {
      error.value = getErrorMessage(e) || 'Fehler beim Markieren aller als gelesen'
      throw e
    }
  }

  // ==================
  // Actions - Rules
  // ==================

  /**
   * Load notification rules
   */
  async function loadRules(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const response = await notificationApi.getRules()
      rules.value = response.data
    } catch (e: unknown) {
      error.value = getErrorMessage(e) || 'Fehler beim Laden der Regeln'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * Create a new notification rule
   */
  async function createRule(data: Partial<NotificationRule>): Promise<NotificationRule> {
    loading.value = true
    try {
      const response = await notificationApi.createRule(data)
      rules.value.unshift(response.data)
      return response.data
    } catch (e: unknown) {
      error.value = getErrorMessage(e) || 'Fehler beim Erstellen der Regel'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * Update an existing notification rule
   */
  async function updateRule(id: string, data: Partial<NotificationRule>): Promise<NotificationRule> {
    loading.value = true
    try {
      const response = await notificationApi.updateRule(id, data)
      const index = rules.value.findIndex((r) => r.id === id)
      if (index !== -1) {
        rules.value[index] = response.data
      }
      return response.data
    } catch (e: unknown) {
      error.value = getErrorMessage(e) || 'Fehler beim Aktualisieren der Regel'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * Delete a notification rule
   */
  async function deleteRule(id: string): Promise<void> {
    try {
      await notificationApi.deleteRule(id)
      rules.value = rules.value.filter((r) => r.id !== id)
    } catch (e: unknown) {
      error.value = getErrorMessage(e) || 'Fehler beim Löschen der Regel'
      throw e
    }
  }

  /**
   * Toggle rule active status
   */
  async function toggleRuleActive(rule: NotificationRule): Promise<NotificationRule> {
    return updateRule(rule.id, { is_active: !rule.is_active })
  }

  // ==================
  // Actions - Email Addresses
  // ==================

  /**
   * Load email addresses
   */
  async function loadEmailAddresses(): Promise<void> {
    try {
      const response = await notificationApi.getEmailAddresses()
      emailAddresses.value = response.data
    } catch (e: unknown) {
      error.value = getErrorMessage(e) || 'Fehler beim Laden der Email-Adressen'
      throw e
    }
  }

  /**
   * Add a new email address
   */
  async function addEmailAddress(data: { email: string; label?: string }): Promise<UserEmailAddress> {
    try {
      const response = await notificationApi.addEmailAddress(data)
      emailAddresses.value.unshift(response.data)
      return response.data
    } catch (e: unknown) {
      error.value = getErrorMessage(e) || 'Fehler beim Hinzufügen der Email-Adresse'
      throw e
    }
  }

  /**
   * Delete an email address
   */
  async function deleteEmailAddress(id: string): Promise<void> {
    try {
      await notificationApi.deleteEmailAddress(id)
      emailAddresses.value = emailAddresses.value.filter((ea) => ea.id !== id)
    } catch (e: unknown) {
      error.value = getErrorMessage(e) || 'Fehler beim Löschen der Email-Adresse'
      throw e
    }
  }

  // ==================
  // Actions - Metadata & Preferences
  // ==================

  /**
   * Load event types and channels metadata
   */
  async function loadMeta(): Promise<void> {
    try {
      const [typesRes, channelsRes] = await Promise.all([
        notificationApi.getEventTypes(),
        notificationApi.getChannels(),
      ])
      eventTypes.value = typesRes.data
      channels.value = channelsRes.data
    } catch (e) {
      logger.error('Failed to load meta:', e)
    }
  }

  /**
   * Load user preferences
   */
  async function loadPreferences(): Promise<void> {
    try {
      const response = await notificationApi.getPreferences()
      preferences.value = response.data
    } catch (e) {
      logger.error('Failed to load preferences:', e)
    }
  }

  /**
   * Update user preferences
   */
  async function updatePreferences(data: Partial<NotificationPreferences>): Promise<NotificationPreferences> {
    try {
      const response = await notificationApi.updatePreferences(data)
      preferences.value = response.data
      return response.data
    } catch (e: unknown) {
      error.value = getErrorMessage(e) || 'Fehler beim Aktualisieren der Einstellungen'
      throw e
    }
  }

  // ==================
  // Actions - Testing
  // ==================

  /**
   * Test a webhook URL
   */
  async function testWebhook(
    url: string,
    auth?: { type?: string; username?: string; password?: string; token?: string }
  ): Promise<{ success: boolean; status_code?: number; error?: string }> {
    try {
      // Transform auth to match API expected format
      let transformedAuth: { type: string; config: Record<string, string> } | undefined
      if (auth?.type) {
        const config: Record<string, string> = {}
        if (auth.username) config.username = auth.username
        if (auth.password) config.password = auth.password
        if (auth.token) config.token = auth.token
        transformedAuth = { type: auth.type, config }
      }
      const response = await notificationApi.testWebhook({ url, auth: transformedAuth })
      return response.data
    } catch (e: unknown) {
      error.value = getErrorMessage(e) || 'Fehler beim Testen des Webhooks'
      throw e
    }
  }

  // ==================
  // Actions - SSE Real-time Updates
  // ==================

  /**
   * Connect to SSE for real-time notification updates
   */
  async function connectSSE(): Promise<void> {
    if (eventSource) {
      eventSource.close()
    }

    const authStore = useAuthStore()
    const baseUrl = import.meta.env.VITE_API_URL || ''

    // Get SSE ticket for authentication
    let ticketParam = ''
    try {
      const response = await fetch(`${baseUrl}/api/auth/sse-ticket`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${authStore.token}`,
          'Content-Type': 'application/json',
        },
      })
      if (response.ok) {
        const data = await response.json()
        ticketParam = `ticket=${encodeURIComponent(data.ticket)}`
      } else {
        logger.warn('Failed to get SSE ticket, falling back to polling')
        useSSE.value = false
        startPolling()
        return
      }
    } catch (err) {
      logger.warn('Error getting SSE ticket:', err)
      useSSE.value = false
      startPolling()
      return
    }

    const url = `${baseUrl}/api/admin/notifications/events?${ticketParam}`
    eventSource = new EventSource(url)

    eventSource.addEventListener('init', (event) => {
      const data = JSON.parse(event.data)
      unreadCount.value = data.unread_count ?? 0
      sseConnected.value = true
      logger.debug('SSE connected, initial count:', data.unread_count)
    })

    eventSource.addEventListener('new_notification', (event) => {
      const notification = JSON.parse(event.data) as Notification
      // Add to front of notifications list
      notifications.value.unshift(notification)
      unreadCount.value++
      totalNotifications.value++
      logger.debug('New notification received:', notification.title)
    })

    eventSource.addEventListener('notification_read', (event) => {
      const data = JSON.parse(event.data)
      const notification = notifications.value.find((n) => n.id === data.id)
      if (notification && !notification.read_at) {
        notification.read_at = new Date().toISOString()
        notification.status = 'READ'
      }
    })

    eventSource.addEventListener('all_read', () => {
      notifications.value.forEach((n) => {
        if (!n.read_at) {
          n.read_at = new Date().toISOString()
          n.status = 'READ'
        }
      })
    })

    eventSource.addEventListener('count_update', (event) => {
      const data = JSON.parse(event.data)
      unreadCount.value = data.unread_count ?? 0
    })

    eventSource.addEventListener('error', () => {
      logger.warn('SSE connection failed, falling back to polling')
      sseConnected.value = false
      useSSE.value = false
      disconnectSSE()
      startPolling()
    })
  }

  /**
   * Disconnect SSE connection
   */
  function disconnectSSE(): void {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
    sseConnected.value = false
  }

  /**
   * Start polling as fallback when SSE is unavailable
   */
  function startPolling(): void {
    if (!pollingInterval) {
      pollingInterval = window.setInterval(async () => {
        try {
          await loadUnreadCount()
        } catch (err) {
          logger.warn('Polling error:', err)
        }
      }, POLLING_INTERVAL)
      logger.debug('Started polling for notifications')
    }
  }

  /**
   * Stop polling
   */
  function stopPolling(): void {
    if (pollingInterval) {
      clearInterval(pollingInterval)
      pollingInterval = null
    }
  }

  /**
   * Initialize real-time updates (SSE with polling fallback)
   */
  async function initRealtime(): Promise<void> {
    if (useSSE.value) {
      await connectSSE()
    } else {
      startPolling()
    }
  }

  /**
   * Cleanup real-time updates
   */
  function cleanupRealtime(): void {
    disconnectSSE()
    stopPolling()
  }

  // ==================
  // Actions - Utility
  // ==================

  /**
   * Reset store state (on logout)
   */
  function $reset(): void {
    // Cleanup SSE/polling
    cleanupRealtime()

    notifications.value = []
    rules.value = []
    emailAddresses.value = []
    eventTypes.value = []
    channels.value = []
    preferences.value = {
      notifications_enabled: true,
      notification_digest_time: undefined,
    }
    unreadCount.value = 0
    loading.value = false
    error.value = null
    totalNotifications.value = 0
    currentPage.value = 1
    perPage.value = 20
    sseConnected.value = false
    useSSE.value = true
  }

  return {
    // State
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

    // Actions - Notifications
    loadNotifications,
    loadUnreadCount,
    markAsRead,
    markAllAsRead,

    // Actions - Rules
    loadRules,
    createRule,
    updateRule,
    deleteRule,
    toggleRuleActive,

    // Actions - Email Addresses
    loadEmailAddresses,
    addEmailAddress,
    deleteEmailAddress,

    // Actions - Metadata & Preferences
    loadMeta,
    loadPreferences,
    updatePreferences,

    // Actions - Testing
    testWebhook,

    // Actions - SSE
    initRealtime,
    cleanupRealtime,
    connectSSE,
    disconnectSSE,

    // Actions - Utility
    $reset,
  }
})
