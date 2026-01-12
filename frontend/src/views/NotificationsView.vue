<template>
  <div>
    <PageHeader
      :title="t('notifications.title')"
      :subtitle="t('notifications.subtitle')"
      icon="mdi-bell"
    />

    <PageInfoBox :storage-key="INFO_BOX_STORAGE_KEYS.NOTIFICATIONS" :title="t('notifications.info.title')">
      {{ t('notifications.info.description') }}
    </PageInfoBox>

    <v-row>
      <v-col cols="12">
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useNotificationsStore } from '@/stores/notifications'
import NotificationInbox from '@/components/notifications/NotificationInbox.vue'
import NotificationRules from '@/components/notifications/NotificationRules.vue'
import NotificationSettings from '@/components/notifications/NotificationSettings.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import PageInfoBox from '@/components/common/PageInfoBox.vue'
import { INFO_BOX_STORAGE_KEYS } from '@/config/infoBox'

const { t } = useI18n()
const route = useRoute()

// Store
const store = useNotificationsStore()
const { unreadCount } = storeToRefs(store)

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
  await store.loadUnreadCount()
})
</script>
