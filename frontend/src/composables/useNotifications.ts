import { ref, computed } from 'vue'
import { notificationApi } from '@/services/api'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger('useNotifications')

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

export interface NotificationRule {
  id: string
  name: string
  description?: string
  event_type: string
  channel: string
  conditions: Record<string, any>
  channel_config: Record<string, any>
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

// State
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

export function useNotifications() {
  // Load notifications
  const loadNotifications = async (params?: {
    status?: string
    channel?: string
    event_type?: string
    page?: number
    per_page?: number
  }) => {
    loading.value = true
    error.value = null
    try {
      const response = await notificationApi.getNotifications(params)
      notifications.value = response.data.items
      totalNotifications.value = response.data.total
      currentPage.value = response.data.page
      perPage.value = response.data.per_page
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Fehler beim Laden der Benachrichtigungen'
      throw e
    } finally {
      loading.value = false
    }
  }

  // Load unread count
  const loadUnreadCount = async () => {
    try {
      const response = await notificationApi.getUnreadCount()
      unreadCount.value = response.data.count
    } catch (e) {
      logger.error('Failed to load unread count:', e)
    }
  }

  // Load rules
  const loadRules = async () => {
    loading.value = true
    error.value = null
    try {
      const response = await notificationApi.getRules()
      rules.value = response.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Fehler beim Laden der Regeln'
      throw e
    } finally {
      loading.value = false
    }
  }

  // Load email addresses
  const loadEmailAddresses = async () => {
    try {
      const response = await notificationApi.getEmailAddresses()
      emailAddresses.value = response.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Fehler beim Laden der Email-Adressen'
      throw e
    }
  }

  // Load event types and channels
  const loadMeta = async () => {
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

  // Load preferences
  const loadPreferences = async () => {
    try {
      const response = await notificationApi.getPreferences()
      preferences.value = response.data
    } catch (e) {
      logger.error('Failed to load preferences:', e)
    }
  }

  // Mark notification as read
  const markAsRead = async (id: string) => {
    try {
      await notificationApi.markAsRead(id)
      const notification = notifications.value.find((n) => n.id === id)
      if (notification && !notification.read_at) {
        notification.read_at = new Date().toISOString()
        notification.status = 'READ'
        if (unreadCount.value > 0) unreadCount.value--
      }
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Fehler beim Markieren als gelesen'
      throw e
    }
  }

  // Mark all as read
  const markAllAsRead = async () => {
    try {
      await notificationApi.markAllAsRead()
      notifications.value.forEach((n) => {
        if (!n.read_at) {
          n.read_at = new Date().toISOString()
          n.status = 'READ'
        }
      })
      unreadCount.value = 0
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Fehler beim Markieren aller als gelesen'
      throw e
    }
  }

  // Create rule
  const createRule = async (data: Partial<NotificationRule>) => {
    loading.value = true
    try {
      const response = await notificationApi.createRule(data)
      rules.value.unshift(response.data)
      return response.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Fehler beim Erstellen der Regel'
      throw e
    } finally {
      loading.value = false
    }
  }

  // Update rule
  const updateRule = async (id: string, data: Partial<NotificationRule>) => {
    loading.value = true
    try {
      const response = await notificationApi.updateRule(id, data)
      const index = rules.value.findIndex((r) => r.id === id)
      if (index !== -1) {
        rules.value[index] = response.data
      }
      return response.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Fehler beim Aktualisieren der Regel'
      throw e
    } finally {
      loading.value = false
    }
  }

  // Delete rule
  const deleteRule = async (id: string) => {
    try {
      await notificationApi.deleteRule(id)
      rules.value = rules.value.filter((r) => r.id !== id)
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Fehler beim Loeschen der Regel'
      throw e
    }
  }

  // Toggle rule active status
  const toggleRuleActive = async (rule: NotificationRule) => {
    return updateRule(rule.id, { is_active: !rule.is_active })
  }

  // Add email address
  const addEmailAddress = async (data: { email: string; label?: string }) => {
    try {
      const response = await notificationApi.addEmailAddress(data)
      emailAddresses.value.unshift(response.data)
      return response.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Fehler beim Hinzufuegen der Email-Adresse'
      throw e
    }
  }

  // Delete email address
  const deleteEmailAddress = async (id: string) => {
    try {
      await notificationApi.deleteEmailAddress(id)
      emailAddresses.value = emailAddresses.value.filter((ea) => ea.id !== id)
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Fehler beim Loeschen der Email-Adresse'
      throw e
    }
  }

  // Update preferences
  const updatePreferences = async (data: Partial<NotificationPreferences>) => {
    try {
      const response = await notificationApi.updatePreferences(data)
      preferences.value = response.data
      return response.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Fehler beim Aktualisieren der Einstellungen'
      throw e
    }
  }

  // Test webhook
  const testWebhook = async (url: string, auth?: any) => {
    try {
      const response = await notificationApi.testWebhook({ url, auth })
      return response.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Fehler beim Testen des Webhooks'
      throw e
    }
  }

  // Computed
  const hasUnread = computed(() => unreadCount.value > 0)
  const totalPages = computed(() => Math.ceil(totalNotifications.value / perPage.value))

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

    // Computed
    hasUnread,
    totalPages,

    // Actions
    loadNotifications,
    loadUnreadCount,
    loadRules,
    loadEmailAddresses,
    loadMeta,
    loadPreferences,
    markAsRead,
    markAllAsRead,
    createRule,
    updateRule,
    deleteRule,
    toggleRuleActive,
    addEmailAddress,
    deleteEmailAddress,
    updatePreferences,
    testWebhook,
  }
}
