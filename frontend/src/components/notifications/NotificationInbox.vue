<template>
  <v-card>
    <v-card-title class="d-flex justify-space-between align-center">
      <span>{{ t('notificationsView.inbox') }}</span>
      <v-btn
        variant="tonal"
        color="primary"
        :disabled="unreadCount === 0"
        :aria-label="t('notifications.messages.markAllRead')"
        @click="handleMarkAllRead"
      >
        {{ t('notifications.messages.markAllRead') }}
      </v-btn>
    </v-card-title>

    <v-card-text>
      <!-- Filters -->
      <v-row class="mb-4">
        <v-col cols="12" md="4">
          <v-select
            v-model="filters.status"
            :items="statusOptions"
            :label="t('common.status')"
            clearable
            hide-details
            density="compact"
          />
        </v-col>
        <v-col cols="12" md="4">
          <v-select
            v-model="filters.channel"
            :items="channelOptions"
            :label="t('notifications.inbox.channel')"
            clearable
            hide-details
            density="compact"
          />
        </v-col>
        <v-col cols="12" md="4">
          <v-select
            v-model="filters.event_type"
            :items="eventTypeOptions"
            :label="t('notifications.inbox.eventType')"
            clearable
            hide-details
            density="compact"
          />
        </v-col>
      </v-row>

      <!-- Loading -->
      <v-progress-linear v-if="loading" indeterminate class="mb-4" role="status" :aria-label="t('common.loading')" />

      <!-- Notification List -->
      <v-list v-if="notifications.length > 0" lines="three" role="list" :aria-label="t('notifications.inbox.notificationsList')">
        <v-list-item
          v-for="notification in notifications"
          :key="notification.id"
          :class="getUnreadClass(notification)"
          class="mb-2 rounded"
          role="listitem"
          :aria-label="`${notification.title} - ${notification.read_at ? t('notifications.read') : t('notifications.unread')}`"
          @click="openNotification(notification)"
        >
          <template #prepend>
            <v-icon :color="getEventTypeColor(notification.event_type)" class="mr-3" aria-hidden="true">
              {{ getEventTypeIcon(notification.event_type) }}
            </v-icon>
          </template>

          <v-list-item-title class="font-weight-medium">
            {{ notification.title }}
            <v-chip
              v-if="!notification.read_at"
              size="x-small"
              color="primary"
              class="ml-2"
              role="status"
            >
              {{ t('common.new') }}
            </v-chip>
          </v-list-item-title>
          <v-list-item-subtitle class="text-wrap">
            {{ notification.body.substring(0, 150) }}{{ notification.body.length > 150 ? '...' : '' }}
          </v-list-item-subtitle>

          <template #append>
            <div class="text-caption text-right">
              <div>{{ formatDate(notification.created_at) }}</div>
              <v-chip size="x-small" :color="getChannelColor(notification.channel)" class="mt-1">
                {{ getChannelLabel(notification.channel) }}
              </v-chip>
            </div>
          </template>
        </v-list-item>
      </v-list>

      <v-alert v-else-if="!loading" type="info" variant="tonal">
        {{ t('notifications.messages.noNotifications') }}
      </v-alert>

      <!-- Pagination -->
      <v-pagination
        v-if="totalPages > 1"
        v-model="currentPage"
        :length="totalPages"
        :total-visible="5"
        class="mt-4"
        @update:model-value="handlePageChange"
      />
    </v-card-text>
  </v-card>

  <!-- Notification Detail Dialog -->
  <v-dialog v-model="detailDialog" :max-width="DIALOG_SIZES.MD" role="dialog" aria-modal="true">
    <v-card v-if="selectedNotification">
      <v-card-title class="d-flex align-center">
        <v-icon :color="getEventTypeColor(selectedNotification.event_type)" class="mr-2" aria-hidden="true">
          {{ getEventTypeIcon(selectedNotification.event_type) }}
        </v-icon>
        {{ selectedNotification.title }}
      </v-card-title>
      <v-card-text>
        <p class="mb-4 text-body-1 text-pre-wrap">{{ selectedNotification.body }}</p>

        <v-divider class="mb-4" />

        <v-row>
          <v-col cols="6">
            <div class="text-caption text-medium-emphasis">{{ t('notifications.inbox.eventType') }}</div>
            <v-chip size="small" :color="getEventTypeColor(selectedNotification.event_type)">
              {{ getEventTypeLabel(selectedNotification.event_type) }}
            </v-chip>
          </v-col>
          <v-col cols="6">
            <div class="text-caption text-medium-emphasis">{{ t('notifications.inbox.channel') }}</div>
            <v-chip size="small" :color="getChannelColor(selectedNotification.channel)">
              {{ getChannelLabel(selectedNotification.channel) }}
            </v-chip>
          </v-col>
          <v-col cols="6">
            <div class="text-caption text-medium-emphasis">{{ t('notifications.inbox.created') }}</div>
            <div>{{ formatDateTime(selectedNotification.created_at) }}</div>
          </v-col>
          <v-col cols="6">
            <div class="text-caption text-medium-emphasis">{{ t('common.status') }}</div>
            <div>{{ getStatusLabel(selectedNotification.status) }}</div>
          </v-col>
        </v-row>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="tonal" @click="detailDialog = false">{{ t('common.close') }}</v-btn>
        <v-btn
          v-if="selectedNotification.related_entity_type"
          color="primary"
          @click="navigateToEntity(selectedNotification)"
        >
          {{ t('notifications.inbox.goTo', { entity: getEntityLabel(selectedNotification.related_entity_type) }) }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useTheme } from 'vuetify'
import { useI18n } from 'vue-i18n'
import { DIALOG_SIZES } from '@/config/ui'
import { useNotifications, type Notification } from '@/composables/useNotifications'
import { useDateFormatter } from '@/composables/useDateFormatter'
import {
  getEventTypeColor,
  getEventTypeIcon,
  getChannelColor,
  useNotificationFormatting,
} from '@/utils/notificationFormatting'

const { t } = useI18n()
const { formatDate: formatLocaleDate } = useDateFormatter()

const router = useRouter()
const theme = useTheme()
const isDark = computed(() => theme.global.current.value.dark)
const {
  notifications,
  unreadCount,
  loading,
  eventTypes,
  channels,
  totalPages,
  currentPage,
  loadNotifications,
  loadUnreadCount,
  loadMeta,
  markAsRead,
  markAllAsRead,
} = useNotifications()

// Use shared notification formatting utilities
const { getEventTypeLabel, getChannelLabel } = useNotificationFormatting(eventTypes, channels)

// Local state
const detailDialog = ref(false)
const selectedNotification = ref<Notification | null>(null)
const filters = ref({
  status: null as string | null,
  channel: null as string | null,
  event_type: null as string | null,
})

// Options for filters
const statusOptions = computed(() => [
  { title: t('notifications.inbox.statusPending'), value: 'PENDING' },
  { title: t('notifications.inbox.statusQueued'), value: 'QUEUED' },
  { title: t('notifications.inbox.statusSent'), value: 'SENT' },
  { title: t('notifications.inbox.statusFailed'), value: 'FAILED' },
  { title: t('notifications.inbox.statusRead'), value: 'READ' },
])

const channelOptions = computed(() =>
  channels.value.map((c) => ({ title: c.label, value: c.value }))
)

const eventTypeOptions = computed(() =>
  eventTypes.value.map((e) => ({ title: e.label, value: e.value }))
)

// Methods
const fetchNotifications = async () => {
  await loadNotifications({
    status: filters.value.status || undefined,
    channel: filters.value.channel || undefined,
    event_type: filters.value.event_type || undefined,
    page: currentPage.value,
  })
}

const handlePageChange = (page: number) => {
  currentPage.value = page
  fetchNotifications()
}

const handleMarkAllRead = async () => {
  await markAllAsRead()
}

const openNotification = async (notification: Notification) => {
  selectedNotification.value = notification
  detailDialog.value = true

  if (!notification.read_at) {
    await markAsRead(notification.id)
  }
}

const navigateToEntity = (notification: Notification) => {
  detailDialog.value = false

  if (notification.related_entity_type === 'document') {
    router.push(`/documents?id=${notification.related_entity_id}`)
  } else if (notification.related_entity_type === 'crawl_job') {
    router.push(`/crawler?job=${notification.related_entity_id}`)
  } else if (notification.related_entity_type === 'data_source') {
    router.push(`/sources?id=${notification.related_entity_id}`)
  }
}

// Helpers
const formatDate = (dateStr: string) => {
  return formatLocaleDate(dateStr, 'dd.MM.yyyy HH:mm')
}

const formatDateTime = (dateStr: string) => {
  return formatLocaleDate(dateStr, 'dd.MM.yyyy HH:mm:ss')
}

const getStatusLabel = (status: string): string => {
  const labels: Record<string, string> = {
    PENDING: t('notifications.inbox.statusPending'),
    QUEUED: t('notifications.inbox.statusQueued'),
    SENT: t('notifications.inbox.statusSent'),
    FAILED: t('notifications.inbox.statusFailed'),
    READ: t('notifications.inbox.statusRead'),
  }
  return labels[status] || status
}

const getEntityLabel = (entityType: string): string => {
  const labels: Record<string, string> = {
    document: t('documents.document'),
    crawl_job: t('crawler.jobDetails'),
    data_source: t('sources.source'),
  }
  return labels[entityType] || entityType
}

// Dark mode aware styling
const getUnreadClass = (notification: Notification): string => {
  if (notification.read_at) return ''
  return isDark.value ? 'bg-grey-darken-3' : 'bg-grey-lighten-4'
}

// Watch filters
watch(filters, () => {
  currentPage.value = 1
  fetchNotifications()
}, { deep: true })

// Init
onMounted(async () => {
  await loadMeta()
  await fetchNotifications()
  await loadUnreadCount()
})
</script>
