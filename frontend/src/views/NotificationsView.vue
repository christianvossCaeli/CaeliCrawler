<template>
  <v-container fluid>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-4">{{ t('notifications.title') }}</h1>

        <v-tabs v-model="activeTab" color="primary" class="mb-4">
          <v-tab value="inbox">
            <v-icon start>mdi-inbox</v-icon>
            {{ t('notificationsView.inbox') }}
            <v-badge
              v-if="unreadCount > 0"
              :content="unreadCount > 99 ? '99+' : unreadCount"
              color="error"
              inline
              class="ml-2"
            />
          </v-tab>
          <v-tab value="rules">
            <v-icon start>mdi-filter-cog</v-icon>
            {{ t('notificationsView.rules') }}
          </v-tab>
          <v-tab value="settings">
            <v-icon start>mdi-cog</v-icon>
            {{ t('notificationsView.settings') }}
          </v-tab>
        </v-tabs>

        <v-window v-model="activeTab">
          <v-window-item value="inbox">
            <NotificationInbox />
          </v-window-item>

          <v-window-item value="rules">
            <NotificationRules />
          </v-window-item>

          <v-window-item value="settings">
            <NotificationSettings />
          </v-window-item>
        </v-window>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { useNotifications } from '@/composables/useNotifications'
import NotificationInbox from '@/components/notifications/NotificationInbox.vue'
import NotificationRules from '@/components/notifications/NotificationRules.vue'
import NotificationSettings from '@/components/notifications/NotificationSettings.vue'

const { t } = useI18n()
const route = useRoute()
const { unreadCount, loadUnreadCount } = useNotifications()

// Tab management
const activeTab = ref('inbox')

// Watch route query for initial tab
onMounted(async () => {
  // Set initial tab from query param
  const tab = route.query.tab as string
  if (tab && ['inbox', 'rules', 'settings'].includes(tab)) {
    activeTab.value = tab
  }

  // Load unread count for badge
  await loadUnreadCount()
})
</script>
