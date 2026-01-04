/**
 * Assistant Reminders Composable
 *
 * Manages reminders for entities and general tasks.
 */

import { ref, type Ref } from 'vue'
import { assistantApi } from '@/services/api'
import { extractErrorMessage } from '@/utils/errorMessage'
import { useLogger } from '@/composables/useLogger'
import type {
  Reminder,
  ConversationMessage,
  AssistantContext,
} from './types'

const logger = useLogger('useAssistantReminders')

export interface UseAssistantRemindersOptions {
  messages: Ref<ConversationMessage[]>
  error: Ref<string | null>
  currentContext: Ref<AssistantContext>
  isOpen: Ref<boolean>
  hasUnread: Ref<boolean>
  saveHistory: () => void
}

export function useAssistantReminders(options: UseAssistantRemindersOptions) {
  const { messages, error, currentContext, isOpen, hasUnread, saveHistory } = options

  // Reminder state
  const reminders = ref<Reminder[]>([])
  const dueReminders = ref<Reminder[]>([])

  // Instance-level interval reference (moved from module level for multi-instance safety)
  let reminderPollInterval: ReturnType<typeof setInterval> | null = null

  /**
   * Load reminders for the current user
   */
  async function loadReminders() {
    try {
      const response = await assistantApi.getReminders()
      reminders.value = response.data.items || []
    } catch (e) {
      logger.error('Failed to load reminders:', e)
      reminders.value = []
    }
  }

  /**
   * Load due reminders (pending and past remind_at)
   */
  async function loadDueReminders() {
    try {
      const response = await assistantApi.getDueReminders()
      dueReminders.value = response.data.items || []

      // Show notification for due reminders
      if (dueReminders.value.length > 0 && !isOpen.value) {
        hasUnread.value = true
      }
    } catch (e) {
      logger.error('Failed to load due reminders:', e)
      dueReminders.value = []
    }
  }

  /**
   * Create a new reminder
   */
  async function createReminder(
    message: string,
    remindAt: Date,
    options?: {
      title?: string
      repeat?: 'NONE' | 'DAILY' | 'WEEKLY' | 'MONTHLY'
    }
  ): Promise<boolean> {
    try {
      const response = await assistantApi.createReminder({
        message,
        remind_at: remindAt.toISOString(),
        title: options?.title,
        entity_id: currentContext.value.current_entity_id || undefined,
        entity_type: currentContext.value.current_entity_type || undefined,
        repeat: options?.repeat || 'NONE',
      })

      if (response.data.success) {
        // Add confirmation message
        const confirmMessage: ConversationMessage = {
          role: 'assistant',
          content: response.data.message,
          timestamp: new Date(),
          response_type: 'success',
        }
        messages.value.push(confirmMessage)
        saveHistory()

        // Reload reminders
        await loadReminders()
        return true
      }
      return false
    } catch (e: unknown) {
      error.value = extractErrorMessage(e)
      return false
    }
  }

  /**
   * Dismiss a reminder
   */
  async function dismissReminder(reminderId: string): Promise<boolean> {
    try {
      await assistantApi.dismissReminder(reminderId)
      // Remove from due reminders list
      dueReminders.value = dueReminders.value.filter(r => r.id !== reminderId)
      await loadReminders()
      return true
    } catch (e) {
      logger.error('Failed to dismiss reminder:', e)
      return false
    }
  }

  /**
   * Delete a reminder
   */
  async function deleteReminder(reminderId: string): Promise<boolean> {
    try {
      await assistantApi.deleteReminder(reminderId)
      reminders.value = reminders.value.filter(r => r.id !== reminderId)
      dueReminders.value = dueReminders.value.filter(r => r.id !== reminderId)
      return true
    } catch (e) {
      logger.error('Failed to delete reminder:', e)
      return false
    }
  }

  /**
   * Snooze a reminder by a number of minutes
   */
  async function snoozeReminder(reminderId: string, minutes: number): Promise<boolean> {
    try {
      const newRemindAt = new Date(Date.now() + minutes * 60 * 1000)
      await assistantApi.snoozeReminder(reminderId, newRemindAt.toISOString())
      // Remove from due reminders list (will reappear when it's due again)
      dueReminders.value = dueReminders.value.filter(r => r.id !== reminderId)
      await loadReminders()
      return true
    } catch (e) {
      logger.error('Failed to snooze reminder:', e)
      return false
    }
  }

  /**
   * Start polling for due reminders
   */
  function startReminderPolling() {
    // Clear any existing interval first to prevent duplicates
    if (reminderPollInterval) {
      clearInterval(reminderPollInterval)
    }
    reminderPollInterval = setInterval(loadDueReminders, 60000) // Every minute
  }

  /**
   * Stop polling for due reminders
   */
  function stopReminderPolling() {
    if (reminderPollInterval) {
      clearInterval(reminderPollInterval)
      reminderPollInterval = null
    }
  }

  return {
    // State
    reminders,
    dueReminders,

    // Methods
    loadReminders,
    loadDueReminders,
    createReminder,
    dismissReminder,
    deleteReminder,
    snoozeReminder,
    startReminderPolling,
    stopReminderPolling,
  }
}
