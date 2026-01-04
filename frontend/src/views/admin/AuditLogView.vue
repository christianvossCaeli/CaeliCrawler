<template>
  <div>
    <!-- Header -->
    <PageHeader
      :title="t('admin.auditLog.title')"
      :subtitle="t('admin.auditLog.subtitle')"
      icon="mdi-history"
    >
      <template #actions>
        <v-btn
          color="error"
          variant="outlined"
          :disabled="totalLogs === 0"
          @click="showClearDialog"
        >
          <v-icon start>mdi-delete-sweep</v-icon>
          {{ t('admin.auditLog.clear.button') }}
        </v-btn>
      </template>
    </PageHeader>

    <!-- Stats Cards -->
    <v-row v-if="stats" class="mb-4">
      <v-col cols="12" md="3">
        <v-card>
          <v-card-text class="d-flex align-center">
            <v-avatar color="primary" class="mr-3">
              <v-icon>mdi-counter</v-icon>
            </v-avatar>
            <div>
              <div class="text-h5 font-weight-bold">{{ stats.total_entries }}</div>
              <div class="text-caption">{{ t('admin.auditLog.stats.total') }}</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card>
          <v-card-text class="d-flex align-center">
            <v-avatar color="success" class="mr-3">
              <v-icon>mdi-calendar-today</v-icon>
            </v-avatar>
            <div>
              <div class="text-h5 font-weight-bold">{{ stats.entries_today }}</div>
              <div class="text-caption">{{ t('admin.auditLog.stats.today') }}</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card>
          <v-card-text class="d-flex align-center">
            <v-avatar color="info" class="mr-3">
              <v-icon>mdi-calendar-week</v-icon>
            </v-avatar>
            <div>
              <div class="text-h5 font-weight-bold">{{ stats.entries_this_week }}</div>
              <div class="text-caption">{{ t('admin.auditLog.stats.thisWeek') }}</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card>
          <v-card-text class="d-flex align-center">
            <v-avatar color="warning" class="mr-3">
              <v-icon>mdi-account-multiple</v-icon>
            </v-avatar>
            <div>
              <div class="text-h5 font-weight-bold">{{ stats.top_users?.length || 0 }}</div>
              <div class="text-caption">{{ t('admin.auditLog.stats.activeUsers') }}</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Filters -->
    <v-card class="mb-4">
      <v-card-text>
        <v-row align="center">
          <v-col cols="12" md="3">
            <v-select
              v-model="actionFilter"
              :label="t('admin.auditLog.filters.action')"
              :items="actionOptions"
              clearable
              hide-details
              @update:model-value="fetchLogs"
            />
          </v-col>
          <v-col cols="12" md="3">
            <v-text-field
              v-model="entityTypeFilter"
              :label="t('admin.auditLog.filters.entityType')"
              clearable
              hide-details
              :placeholder="t('admin.auditLog.filters.entityTypePlaceholder')"
              @update:model-value="debouncedFetch"
            />
          </v-col>
          <v-col cols="12" md="3">
            <v-text-field
              v-model="startDate"
              :label="t('common.from')"
              type="date"
              clearable
              hide-details
              @update:model-value="fetchLogs"
            />
          </v-col>
          <v-col cols="12" md="3">
            <v-text-field
              v-model="endDate"
              :label="t('common.to')"
              type="date"
              clearable
              hide-details
              @update:model-value="fetchLogs"
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Audit Log Table -->
    <v-card>
      <v-data-table-server
        v-model:page="page"
        v-model:items-per-page="perPage"
        :headers="headers"
        :items="logs"
        :items-length="totalLogs"
        :loading="loading"
        :sort-by="sortBy"
        @update:options="onTableOptionsUpdate"
      >
        <!-- Action Column -->
        <template #item.action="{ item }">
          <v-chip
            :color="getActionColor(item.action)"
            size="small"
            label
          >
            <v-icon start size="small">{{ getActionIcon(item.action) }}</v-icon>
            {{ item.action }}
          </v-chip>
        </template>

        <!-- Entity Column -->
        <template #item.entity_type="{ item }">
          <div>
            <span class="font-weight-medium">{{ item.entity_type }}</span>
            <span v-if="item.entity_name" class="text-medium-emphasis ml-1">
              ({{ item.entity_name }})
            </span>
          </div>
        </template>

        <!-- User Column -->
        <template #item.user_email="{ item }">
          <span v-if="item.user_email">{{ item.user_email }}</span>
          <span v-else class="text-medium-emphasis">{{ t('admin.auditLog.system') }}</span>
        </template>

        <!-- Changes Column -->
        <template #item.changes="{ item }">
          <v-btn
            v-if="Object.keys(item.changes).length > 0"
            variant="tonal"
            size="small"
            @click="showChanges(item)"
          >
            <v-icon start>mdi-eye</v-icon>
            {{ t('common.details') }}
          </v-btn>
          <span v-else class="text-medium-emphasis">-</span>
        </template>

        <!-- Date Column -->
        <template #item.created_at="{ item }">
          {{ formatDate(item.created_at) }}
        </template>

        <!-- Empty State -->
        <template #no-data>
          <div class="text-center py-8">
            <v-icon size="64" color="grey-lighten-1" class="mb-4">mdi-history</v-icon>
            <h3 class="text-h6 mb-2">{{ t('admin.auditLog.emptyState.title', 'Keine Einträge') }}</h3>
            <p class="text-body-2 text-medium-emphasis">
              {{ t('admin.auditLog.emptyState.description', 'Es wurden noch keine Audit-Log-Einträge erfasst.') }}
            </p>
          </div>
        </template>
      </v-data-table-server>
    </v-card>

    <!-- Changes Dialog -->
    <v-dialog v-model="changesDialogOpen" :max-width="DIALOG_SIZES.MD">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon start>mdi-delta</v-icon>
          {{ t('admin.auditLog.changesTitle') }}
        </v-card-title>
        <v-card-text>
          <v-table v-if="selectedLog" density="compact">
            <thead>
              <tr>
                <th>{{ t('admin.auditLog.field') }}</th>
                <th>{{ t('admin.auditLog.before') }}</th>
                <th>{{ t('admin.auditLog.after') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(change, field) in selectedLog.changes" :key="field">
                <td class="font-weight-medium">{{ field }}</td>
                <td class="text-error">
                  <code>{{ formatValue(change.old) }}</code>
                </td>
                <td class="text-success">
                  <code>{{ formatValue(change.new) }}</code>
                </td>
              </tr>
            </tbody>
          </v-table>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="tonal" @click="changesDialogOpen = false">
            {{ t('common.close') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Clear Audit Log Dialog -->
    <v-dialog v-model="clearDialogOpen" :max-width="DIALOG_SIZES.SM" persistent>
      <v-card>
        <v-card-title class="d-flex align-center text-error">
          <v-icon start color="error">mdi-alert</v-icon>
          {{ t('admin.auditLog.clear.title') }}
        </v-card-title>
        <v-card-text>
          <v-alert type="warning" variant="tonal" class="mb-4">
            {{ t('admin.auditLog.clear.warning') }}
          </v-alert>

          <v-radio-group v-model="clearMode" class="mb-4">
            <v-radio
              value="all"
              :label="t('admin.auditLog.clear.deleteAll')"
            />
            <v-radio
              value="before_date"
              :label="t('admin.auditLog.clear.deleteOlderThan')"
            />
          </v-radio-group>

          <v-text-field
            v-if="clearMode === 'before_date'"
            v-model="clearBeforeDate"
            :label="t('admin.auditLog.clear.beforeDate')"
            type="date"
            class="mb-4"
          />

          <v-text-field
            v-model="clearConfirmText"
            :label="t('admin.auditLog.clear.confirmLabel')"
            :placeholder="t('admin.auditLog.clear.confirmPlaceholder')"
            :hint="t('admin.auditLog.clear.confirmHint')"
            persistent-hint
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="tonal" @click="clearDialogOpen = false">
            {{ t('common.cancel') }}
          </v-btn>
          <v-btn
            color="error"
            variant="flat"
            :disabled="clearConfirmText !== 'DELETE' || clearing"
            :loading="clearing"
            @click="clearAuditLogs"
          >
            {{ t('admin.auditLog.clear.confirm') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { DIALOG_SIZES } from '@/config/ui'
import api from '@/services/api'
import { useDebounce, DEBOUNCE_DELAYS } from '@/composables/useDebounce'
import PageHeader from '@/components/common/PageHeader.vue'
import { useLogger } from '@/composables/useLogger'
import { formatDate as formatViewDate } from '@/utils/viewHelpers'

const logger = useLogger('AuditLogView')

const { t } = useI18n()

interface AuditLog {
  id: string
  user_id: string | null
  user_email: string | null
  action: string
  entity_type: string
  entity_id: string | null
  entity_name: string | null
  changes: Record<string, { old: unknown; new: unknown }>
  ip_address: string | null
  created_at: string
}

interface AuditStats {
  total_entries: number
  entries_today: number
  entries_this_week: number
  actions_breakdown: Record<string, number>
  top_users: Array<{ email: string; count: number }>
  top_entity_types: Array<{ entity_type: string; count: number }>
}

// State
const logs = ref<AuditLog[]>([])
const totalLogs = ref(0)
const stats = ref<AuditStats | null>(null)
const loading = ref(false)

// Pagination & Filters
const page = ref(1)
const perPage = ref(50)
const actionFilter = ref<string | null>(null)
const entityTypeFilter = ref('')
const startDate = ref('')
const endDate = ref('')
const sortBy = ref<Array<{ key: string; order: 'asc' | 'desc' }>>([{ key: 'created_at', order: 'desc' }])

// Dialog
const changesDialogOpen = ref(false)
const selectedLog = ref<AuditLog | null>(null)

// Clear Dialog
const clearDialogOpen = ref(false)
const clearMode = ref<'all' | 'before_date'>('all')
const clearBeforeDate = ref('')
const clearConfirmText = ref('')
const clearing = ref(false)

// Table headers
const headers = computed(() => [
  { title: t('admin.auditLog.columns.action'), key: 'action', sortable: true, width: 130 },
  { title: t('admin.auditLog.columns.entity'), key: 'entity_type', sortable: true },
  { title: t('admin.auditLog.columns.user'), key: 'user_email', sortable: true, width: 200 },
  { title: t('admin.auditLog.columns.changes'), key: 'changes', sortable: false, width: 120 },
  { title: t('admin.auditLog.columns.timestamp'), key: 'created_at', sortable: true, width: 180 },
])

const actionOptions = computed(() => [
  // CRUD operations
  { title: t('admin.auditLog.actionTypes.CREATE'), value: 'CREATE' },
  { title: t('admin.auditLog.actionTypes.UPDATE'), value: 'UPDATE' },
  { title: t('admin.auditLog.actionTypes.DELETE'), value: 'DELETE' },
  // Authentication
  { title: t('admin.auditLog.actionTypes.LOGIN'), value: 'LOGIN' },
  { title: t('admin.auditLog.actionTypes.LOGOUT'), value: 'LOGOUT' },
  { title: t('admin.auditLog.actionTypes.PASSWORD_CHANGE'), value: 'PASSWORD_CHANGE' },
  { title: t('admin.auditLog.actionTypes.PASSWORD_RESET'), value: 'PASSWORD_RESET' },
  // Session Management
  { title: t('admin.auditLog.actionTypes.SESSION_REVOKE'), value: 'SESSION_REVOKE' },
  { title: t('admin.auditLog.actionTypes.SESSION_REVOKE_ALL'), value: 'SESSION_REVOKE_ALL' },
  { title: t('admin.auditLog.actionTypes.TOKEN_REFRESH'), value: 'TOKEN_REFRESH' },
  // Data Operations
  { title: t('admin.auditLog.actionTypes.EXPORT'), value: 'EXPORT' },
  { title: t('admin.auditLog.actionTypes.VIEW'), value: 'VIEW' },
  { title: t('admin.auditLog.actionTypes.IMPORT'), value: 'IMPORT' },
  { title: t('admin.auditLog.actionTypes.VERIFY'), value: 'VERIFY' },
  // Crawler Operations
  { title: t('admin.auditLog.actionTypes.CRAWLER_START'), value: 'CRAWLER_START' },
  { title: t('admin.auditLog.actionTypes.CRAWLER_STOP'), value: 'CRAWLER_STOP' },
  // Admin Operations
  { title: t('admin.auditLog.actionTypes.USER_CREATE'), value: 'USER_CREATE' },
  { title: t('admin.auditLog.actionTypes.USER_UPDATE'), value: 'USER_UPDATE' },
  { title: t('admin.auditLog.actionTypes.USER_DELETE'), value: 'USER_DELETE' },
  { title: t('admin.auditLog.actionTypes.ROLE_CHANGE'), value: 'ROLE_CHANGE' },
  // Security Events
  { title: t('admin.auditLog.actionTypes.SECURITY_ALERT'), value: 'SECURITY_ALERT' },
  { title: t('admin.auditLog.actionTypes.RATE_LIMIT_EXCEEDED'), value: 'RATE_LIMIT_EXCEEDED' },
])

// Helpers
function getActionColor(action: string): string {
  const colors: Record<string, string> = {
    // CRUD
    CREATE: 'success',
    UPDATE: 'info',
    DELETE: 'error',
    // Authentication
    LOGIN: 'primary',
    LOGOUT: 'grey',
    PASSWORD_CHANGE: 'warning',
    PASSWORD_RESET: 'warning',
    // Session
    SESSION_REVOKE: 'orange',
    SESSION_REVOKE_ALL: 'orange',
    TOKEN_REFRESH: 'grey',
    // Data Operations
    EXPORT: 'purple',
    VIEW: 'secondary',
    IMPORT: 'teal',
    VERIFY: 'cyan',
    // Crawler
    CRAWLER_START: 'light-green',
    CRAWLER_STOP: 'deep-orange',
    // Admin
    USER_CREATE: 'success',
    USER_UPDATE: 'info',
    USER_DELETE: 'error',
    ROLE_CHANGE: 'amber',
    // Security
    SECURITY_ALERT: 'red',
    RATE_LIMIT_EXCEEDED: 'red-darken-2',
  }
  return colors[action] || 'grey'
}

function getActionIcon(action: string): string {
  const icons: Record<string, string> = {
    // CRUD
    CREATE: 'mdi-plus',
    UPDATE: 'mdi-pencil',
    DELETE: 'mdi-delete',
    // Authentication
    LOGIN: 'mdi-login',
    LOGOUT: 'mdi-logout',
    PASSWORD_CHANGE: 'mdi-key-change',
    PASSWORD_RESET: 'mdi-lock-reset',
    // Session
    SESSION_REVOKE: 'mdi-account-cancel',
    SESSION_REVOKE_ALL: 'mdi-account-multiple-remove',
    TOKEN_REFRESH: 'mdi-refresh',
    // Data Operations
    EXPORT: 'mdi-download',
    VIEW: 'mdi-eye',
    IMPORT: 'mdi-upload',
    VERIFY: 'mdi-check-decagram',
    // Crawler
    CRAWLER_START: 'mdi-play',
    CRAWLER_STOP: 'mdi-stop',
    // Admin
    USER_CREATE: 'mdi-account-plus',
    USER_UPDATE: 'mdi-account-edit',
    USER_DELETE: 'mdi-account-remove',
    ROLE_CHANGE: 'mdi-shield-account',
    // Security
    SECURITY_ALERT: 'mdi-alert',
    RATE_LIMIT_EXCEEDED: 'mdi-speedometer',
  }
  return icons[action] || 'mdi-circle'
}

function formatDate(date: string): string {
  return formatViewDate(date, {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return '-'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

// Debounce search - uses composable with automatic cleanup
const { debouncedFn: debouncedFetch } = useDebounce(
  () => fetchLogs(),
  { delay: DEBOUNCE_DELAYS.SEARCH }
)

function showChanges(log: AuditLog) {
  selectedLog.value = log
  changesDialogOpen.value = true
}

// Clear dialog functions
function showClearDialog() {
  clearMode.value = 'all'
  clearBeforeDate.value = ''
  clearConfirmText.value = ''
  clearDialogOpen.value = true
}

async function clearAuditLogs() {
  clearing.value = true
  try {
    const params: Record<string, unknown> = { confirm: true }
    if (clearMode.value === 'before_date' && clearBeforeDate.value) {
      params.before_date = new Date(clearBeforeDate.value).toISOString()
    }

    const response = await api.delete('/admin/audit', { params })
    logger.info('Audit logs cleared:', response.data)

    // Reset dialog
    clearDialogOpen.value = false
    clearConfirmText.value = ''

    // Refresh data
    await Promise.all([fetchLogs(), fetchStats()])
  } catch (error) {
    logger.error('Failed to clear audit logs:', error)
  } finally {
    clearing.value = false
  }
}

// Table options handler
function onTableOptionsUpdate(options: { page: number; itemsPerPage: number; sortBy: Array<{ key: string; order: 'asc' | 'desc' }> }) {
  const sortChanged = JSON.stringify(options.sortBy) !== JSON.stringify(sortBy.value)
  page.value = options.page
  perPage.value = options.itemsPerPage
  sortBy.value = options.sortBy
  if (sortChanged) {
    fetchLogs()
  }
}

// API calls
async function fetchLogs() {
  loading.value = true
  try {
    const params: Record<string, unknown> = {
      page: page.value,
      per_page: perPage.value,
    }
    if (actionFilter.value) params.action = actionFilter.value
    if (entityTypeFilter.value) params.entity_type = entityTypeFilter.value
    if (startDate.value) params.start_date = new Date(startDate.value).toISOString()
    if (endDate.value) params.end_date = new Date(endDate.value).toISOString()
    if (sortBy.value.length > 0) {
      params.sort_by = sortBy.value[0].key
      params.sort_order = sortBy.value[0].order
    }

    const response = await api.get('/admin/audit', { params })
    logs.value = response.data.items
    totalLogs.value = response.data.total
  } catch (error) {
    logger.error('Failed to fetch audit logs:', error)
  } finally {
    loading.value = false
  }
}

async function fetchStats() {
  try {
    const response = await api.get('/admin/audit/stats')
    stats.value = response.data
  } catch (error) {
    logger.error('Failed to fetch stats:', error)
  }
}

onMounted(() => {
  fetchLogs()
  fetchStats()
})
</script>
