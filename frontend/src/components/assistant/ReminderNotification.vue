<template>
  <v-expand-transition>
    <div v-if="dueReminders.length > 0" class="reminder-notification">
      <div class="reminder-notification__header">
        <v-icon size="small" class="mr-2" color="warning">mdi-bell-ring</v-icon>
        <span class="text-subtitle-2">
          {{ t('assistant.reminderDueCount', dueReminders.length) }}
        </span>
        <v-spacer />
        <v-btn
          v-if="dueReminders.length > 1"
          variant="text"
          size="x-small"
          @click="expanded = !expanded"
        >
          <v-icon>{{ expanded ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
        </v-btn>
      </div>

      <v-list density="compact" class="reminder-list">
        <v-list-item
          v-for="reminder in visibleReminders"
          :key="reminder.id"
          class="reminder-item"
        >
          <template v-slot:prepend>
            <v-avatar size="32" :color="getReminderColor(reminder)" variant="tonal">
              <v-icon size="small">mdi-bell</v-icon>
            </v-avatar>
          </template>

          <v-list-item-title class="text-body-2 font-weight-medium">
            {{ reminder.title || reminder.message }}
          </v-list-item-title>

          <v-list-item-subtitle v-if="reminder.title" class="text-caption">
            {{ reminder.message }}
          </v-list-item-subtitle>

          <v-list-item-subtitle v-if="reminder.entity_name" class="text-caption mt-1">
            <v-icon size="x-small" class="mr-1">mdi-link-variant</v-icon>
            {{ t('assistant.reminderRelatedTo', { entity: reminder.entity_name }) }}
          </v-list-item-subtitle>

          <template v-slot:append>
            <div class="reminder-actions">
              <!-- Go to Entity -->
              <v-btn
                v-if="reminder.entity_id && reminder.entity_type"
                icon
                variant="text"
                size="x-small"
                @click="$emit('navigate', `/entities/${reminder.entity_type}/${reminder.entity_slug || reminder.entity_id}`)"
              >
                <v-icon size="small">mdi-open-in-new</v-icon>
                <v-tooltip activator="parent" location="top">
                  {{ t('assistant.reminderGoToEntity') }}
                </v-tooltip>
              </v-btn>

              <!-- Snooze Menu -->
              <v-menu>
                <template v-slot:activator="{ props }">
                  <v-btn
                    v-bind="props"
                    icon
                    variant="text"
                    size="x-small"
                  >
                    <v-icon size="small">mdi-clock-outline</v-icon>
                    <v-tooltip activator="parent" location="top">
                      {{ t('assistant.reminderSnooze') }}
                    </v-tooltip>
                  </v-btn>
                </template>
                <v-list density="compact">
                  <v-list-item @click="$emit('snooze', reminder.id, 15)">
                    <v-list-item-title>{{ t('assistant.reminderSnooze15') }}</v-list-item-title>
                  </v-list-item>
                  <v-list-item @click="$emit('snooze', reminder.id, 60)">
                    <v-list-item-title>{{ t('assistant.reminderSnooze1h') }}</v-list-item-title>
                  </v-list-item>
                  <v-list-item @click="$emit('snooze', reminder.id, 1440)">
                    <v-list-item-title>{{ t('assistant.reminderSnooze1d') }}</v-list-item-title>
                  </v-list-item>
                </v-list>
              </v-menu>

              <!-- Dismiss -->
              <v-btn
                icon
                variant="text"
                size="x-small"
                @click="$emit('dismiss', reminder.id)"
              >
                <v-icon size="small">mdi-check</v-icon>
                <v-tooltip activator="parent" location="top">
                  {{ t('assistant.reminderDismiss') }}
                </v-tooltip>
              </v-btn>
            </div>
          </template>
        </v-list-item>
      </v-list>

      <div v-if="!expanded && dueReminders.length > 1" class="reminder-more">
        <span class="text-caption text-medium-emphasis">
          {{ t('assistant.more', { count: dueReminders.length - 1 }) }}
        </span>
      </div>
    </div>
  </v-expand-transition>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

export interface Reminder {
  id: string
  message: string
  title?: string
  remind_at: string
  repeat: string
  status: string
  entity_id?: string
  entity_type?: string
  entity_name?: string
  entity_slug?: string
  created_at: string
}

const props = defineProps<{
  dueReminders: Reminder[]
}>()

defineEmits<{
  dismiss: [reminderId: string]
  snooze: [reminderId: string, minutes: number]
  navigate: [route: string]
}>()

const expanded = ref(false)

const visibleReminders = computed(() => {
  if (expanded.value || props.dueReminders.length <= 1) {
    return props.dueReminders
  }
  return props.dueReminders.slice(0, 1)
})

function getReminderColor(reminder: Reminder): string {
  // Overdue reminders are more urgent
  const remindAt = new Date(reminder.remind_at)
  const now = new Date()
  const minutesOverdue = (now.getTime() - remindAt.getTime()) / (1000 * 60)

  if (minutesOverdue > 60) {
    return 'error'
  } else if (minutesOverdue > 15) {
    return 'warning'
  }
  return 'primary'
}
</script>

<style scoped>
.reminder-notification {
  background: rgb(var(--v-theme-warning-container));
  color: rgb(var(--v-theme-on-warning-container));
  border-radius: 8px;
  margin: 8px 16px;
  overflow: hidden;
}

.reminder-notification__header {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background: rgba(var(--v-theme-warning), 0.15);
}

.reminder-list {
  background: transparent !important;
  padding: 0 !important;
}

.reminder-item {
  padding: 8px 12px !important;
  border-top: 1px solid rgba(var(--v-theme-outline), 0.1);
}

.reminder-item:first-child {
  border-top: none;
}

.reminder-actions {
  display: flex;
  gap: 4px;
}

.reminder-more {
  padding: 4px 12px 8px;
  text-align: center;
}
</style>
