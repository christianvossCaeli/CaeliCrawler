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
      <!-- Bulk Actions Bar -->
      <v-slide-y-transition>
        <v-toolbar v-if="selectedIds.length > 0" density="compact" color="primary" class="mb-4 rounded">
          <v-checkbox
            :model-value="isAllSelected"
            :indeterminate="isPartiallySelected"
            hide-details
            class="ml-2"
            @update:model-value="toggleSelectAll"
          />
          <span class="ml-2">{{ t('notifications.inbox.selected', { count: selectedIds.length }) }}</span>
          <v-spacer />
          <v-btn variant="text" size="small" @click="bulkMarkAsRead">
            <v-icon start>mdi-email-open</v-icon>
            {{ t('notifications.inbox.bulkMarkRead') }}
          </v-btn>
          <v-btn variant="text" size="small" color="error" @click="confirmBulkDelete">
            <v-icon start>mdi-delete</v-icon>
            {{ t('notifications.inbox.bulkDelete') }}
          </v-btn>
        </v-toolbar>
      </v-slide-y-transition>

      <!-- Filters -->
      <v-row class="mb-4">
        <v-col cols="12" md="3">
          <v-select
            v-model="filters.status"
            :items="statusOptions"
            :label="t('common.status')"
            clearable
            hide-details
            density="compact"
          />
        </v-col>
        <v-col cols="12" md="3">
          <v-select
            v-model="filters.channel"
            :items="channelOptions"
            :label="t('notifications.inbox.channel')"
            clearable
            hide-details
            density="compact"
          />
        </v-col>
        <v-col cols="12" md="3">
          <v-select
            v-model="filters.event_type"
            :items="eventTypeOptions"
            :label="t('notifications.inbox.eventType')"
            clearable
            hide-details
            density="compact"
          />
        </v-col>
        <v-col cols="12" md="3">
          <v-select
            v-model="sortBy"
            :items="sortOptions"
            :label="t('notifications.inbox.sortBy')"
            hide-details
            density="compact"
          />
        </v-col>
      </v-row>

      <!-- Loading -->
      <v-progress-linear v-if="loading" indeterminate class="mb-4" role="status" :aria-label="t('common.loading')" />

      <!-- Notification List -->
      <v-list v-if="sortedNotifications.length > 0" lines="three" role="list" :aria-label="t('notifications.inbox.notificationsList')">
        <v-list-item
          v-for="notification in sortedNotifications"
          :key="notification.id"
          :class="getUnreadClass(notification)"
          class="mb-2 rounded"
          role="listitem"
          :aria-label="`${notification.title} - ${notification.read_at ? t('notifications.read') : t('notifications.unread')}`"
          @click="openNotification(notification)"
        >
          <template #prepend>
            <v-checkbox
              :model-value="selectedIds.includes(notification.id)"
              hide-details
              class="mr-2"
              @update:model-value="toggleSelection(notification.id)"
              @click.stop
            />
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
            <div class="d-flex align-center">
              <div class="text-caption text-right mr-2">
                <div>{{ formatDate(notification.created_at) }}</div>
                <v-chip size="x-small" :color="getChannelColor(notification.channel)" class="mt-1">
                  {{ getChannelLabel(notification.channel) }}
                </v-chip>
              </div>
              <v-btn
                icon="mdi-delete"
                variant="text"
                size="small"
                color="error"
                :title="t('common.delete')"
                @click.stop="confirmDeleteSingle(notification)"
              />
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

  <!-- Delete Single Confirmation Dialog -->
  <v-dialog v-model="deleteDialog" :max-width="DIALOG_SIZES.XS">
    <v-card>
      <v-card-title>{{ t('common.delete') }}</v-card-title>
      <v-card-text>
        {{ t('notifications.inbox.deleteConfirm') }}
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="tonal" @click="deleteDialog = false">{{ t('common.cancel') }}</v-btn>
        <v-btn variant="tonal" color="error" :loading="deleting" @click="handleDeleteSingle">
          {{ t('common.delete') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- Bulk Delete Confirmation Dialog -->
  <v-dialog v-model="bulkDeleteDialog" :max-width="DIALOG_SIZES.XS">
    <v-card>
      <v-card-title>{{ t('notifications.inbox.bulkDelete') }}</v-card-title>
      <v-card-text>
        {{ t('notifications.inbox.bulkDeleteConfirm', { count: selectedIds.length }) }}
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="tonal" @click="bulkDeleteDialog = false">{{ t('common.cancel') }}</v-btn>
        <v-btn variant="tonal" color="error" :loading="deleting" @click="handleBulkDelete">
          {{ t('common.delete') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- Snackbar for feedback -->
  <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000">
    {{ snackbar.message }}
  </v-snackbar>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useTheme } from 'vuetify'
import { useI18n } from 'vue-i18n'
import { storeToRefs } from 'pinia'
import { useDebounceFn } from '@vueuse/core'
import { DIALOG_SIZES } from '@/config/ui'
import { useNotificationsStore, type Notification } from '@/stores/notifications'
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

// Store
const store = useNotificationsStore()
const {
  notifications,
  unreadCount,
  loading,
  eventTypes,
  channels,
  totalPages,
  currentPage,
} = storeToRefs(store)

// Use shared notification formatting utilities
const { getEventTypeLabel, getChannelLabel } = useNotificationFormatting(eventTypes, channels)

// Local state
const detailDialog = ref(false)
const deleteDialog = ref(false)
const bulkDeleteDialog = ref(false)
const deleting = ref(false)
const selectedNotification = ref<Notification | null>(null)
const notificationToDelete = ref<Notification | null>(null)
const selectedIds = ref<string[]>([])
const sortBy = ref('created_at_desc')

const filters = ref({
  status: null as string | null,
  channel: null as string | null,
  event_type: null as string | null,
})

const snackbar = ref({
  show: false,
  message: '',
  color: 'success',
})

// Computed for bulk selection
const isAllSelected = computed(() =>
  notifications.value.length > 0 &&
  selectedIds.value.length === notifications.value.length
)

const isPartiallySelected = computed(() =>
  selectedIds.value.length > 0 &&
  selectedIds.value.length < notifications.value.length
)

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

const sortOptions = computed(() => [
  { title: t('notifications.inbox.sortDate') + ' ↓', value: 'created_at_desc' },
  { title: t('notifications.inbox.sortDate') + ' ↑', value: 'created_at_asc' },
  { title: t('notifications.inbox.sortStatus'), value: 'status' },
])

// Client-side sorting (API always returns created_at desc)
const sortedNotifications = computed(() => {
  const items = [...notifications.value]
  switch (sortBy.value) {
    case 'created_at_asc':
      return items.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
    case 'status':
      // Unread first, then read
      return items.sort((a, b) => {
        const aRead = a.read_at ? 1 : 0
        const bRead = b.read_at ? 1 : 0
        return aRead - bRead
      })
    case 'created_at_desc':
    default:
      return items // Already sorted by API
  }
})

// Methods
const showSnackbar = (message: string, color: string = 'success') => {
  snackbar.value = { show: true, message, color }
}

const fetchNotifications = async () => {
  await store.loadNotifications({
    status: filters.value.status || undefined,
    channel: filters.value.channel || undefined,
    event_type: filters.value.event_type || undefined,
    page: currentPage.value,
  })
}

// Debounced fetch for filter changes
const debouncedFetch = useDebounceFn(() => {
  currentPage.value = 1
  selectedIds.value = [] // Clear selection when filters change
  fetchNotifications()
}, 300)

const handlePageChange = (page: number) => {
  currentPage.value = page
  selectedIds.value = [] // Clear selection on page change
  fetchNotifications()
}

const handleMarkAllRead = async () => {
  try {
    await store.markAllAsRead()
    showSnackbar(t('notifications.messages.markAllRead'))
  } catch {
    showSnackbar(t('notifications.errors.markAllAsRead'), 'error')
  }
}

const openNotification = async (notification: Notification) => {
  selectedNotification.value = notification
  detailDialog.value = true

  if (!notification.read_at) {
    try {
      await store.markAsRead(notification.id)
    } catch {
      // Silent fail for mark as read
    }
  }
}

const navigateToEntity = (notification: Notification) => {
  detailDialog.value = false

  if (notification.related_entity_type === 'document') {
    router.push({ path: '/documents', query: { document_id: notification.related_entity_id } })
  } else if (notification.related_entity_type === 'crawl_job') {
    router.push({ path: '/crawler', query: { job_id: notification.related_entity_id } })
  } else if (notification.related_entity_type === 'data_source') {
    router.push({ path: '/sources', query: { id: notification.related_entity_id } })
  }
}

// Selection methods
const toggleSelectAll = () => {
  if (isAllSelected.value) {
    selectedIds.value = []
  } else {
    selectedIds.value = notifications.value.map((n) => n.id)
  }
}

const toggleSelection = (id: string) => {
  const index = selectedIds.value.indexOf(id)
  if (index === -1) {
    selectedIds.value.push(id)
  } else {
    selectedIds.value.splice(index, 1)
  }
}

// Bulk actions
const bulkMarkAsRead = async () => {
  try {
    await store.bulkMarkAsRead(selectedIds.value)
    selectedIds.value = []
    showSnackbar(t('notifications.messages.markAllRead'))
  } catch {
    showSnackbar(t('notifications.errors.markAsRead'), 'error')
  }
}

const confirmBulkDelete = () => {
  bulkDeleteDialog.value = true
}

const handleBulkDelete = async () => {
  deleting.value = true
  try {
    await store.bulkDeleteNotifications(selectedIds.value)
    const count = selectedIds.value.length
    selectedIds.value = []
    bulkDeleteDialog.value = false
    showSnackbar(t('notifications.inbox.bulkDeleteSuccess', { count }))
  } catch {
    showSnackbar(t('notifications.errors.deleteNotification'), 'error')
  } finally {
    deleting.value = false
  }
}

// Single delete
const confirmDeleteSingle = (notification: Notification) => {
  notificationToDelete.value = notification
  deleteDialog.value = true
}

const handleDeleteSingle = async () => {
  if (!notificationToDelete.value) return

  deleting.value = true
  try {
    await store.deleteNotification(notificationToDelete.value.id)
    deleteDialog.value = false
    notificationToDelete.value = null
    showSnackbar(t('notifications.inbox.deleteSuccess'))
  } catch {
    showSnackbar(t('notifications.errors.deleteNotification'), 'error')
  } finally {
    deleting.value = false
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

// Watch filters and sort with debounce
watch(filters, debouncedFetch, { deep: true })
watch(sortBy, debouncedFetch)

// Init
onMounted(async () => {
  await store.loadMeta()
  await fetchNotifications()
  await store.loadUnreadCount()
})
</script>
