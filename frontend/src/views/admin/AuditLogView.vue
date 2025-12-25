<template>
  <v-container fluid>
    <!-- Header -->
    <PageHeader
      :title="t('admin.auditLog.title')"
      :subtitle="t('admin.auditLog.subtitle')"
      icon="mdi-history"
    />

    <!-- Stats Cards -->
    <v-row class="mb-4" v-if="stats">
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
        @update:page="fetchLogs"
        @update:items-per-page="fetchLogs"
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
        <template #item.entity="{ item }">
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
      </v-data-table-server>
    </v-card>

    <!-- Changes Dialog -->
    <v-dialog v-model="changesDialogOpen" max-width="600">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon start>mdi-delta</v-icon>
          {{ t('admin.auditLog.changesTitle') }}
        </v-card-title>
        <v-card-text>
          <v-table density="compact" v-if="selectedLog">
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
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/services/api'
import { useDebounce, DEBOUNCE_DELAYS } from '@/composables/useDebounce'
import PageHeader from '@/components/common/PageHeader.vue'
import { useLogger } from '@/composables/useLogger'

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
  changes: Record<string, { old: any; new: any }>
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

// Dialog
const changesDialogOpen = ref(false)
const selectedLog = ref<AuditLog | null>(null)

// Table headers
const headers = computed(() => [
  { title: t('admin.auditLog.columns.action'), key: 'action', sortable: false, width: 130 },
  { title: t('admin.auditLog.columns.entity'), key: 'entity', sortable: false },
  { title: t('admin.auditLog.columns.user'), key: 'user_email', sortable: false, width: 200 },
  { title: t('admin.auditLog.columns.changes'), key: 'changes', sortable: false, width: 120 },
  { title: t('admin.auditLog.columns.timestamp'), key: 'created_at', sortable: false, width: 180 },
])

const actionOptions = computed(() => [
  { title: t('admin.auditLog.actionTypes.CREATE'), value: 'CREATE' },
  { title: t('admin.auditLog.actionTypes.UPDATE'), value: 'UPDATE' },
  { title: t('admin.auditLog.actionTypes.DELETE'), value: 'DELETE' },
  { title: t('admin.auditLog.actionTypes.LOGIN'), value: 'LOGIN' },
  { title: t('admin.auditLog.actionTypes.LOGOUT'), value: 'LOGOUT' },
  { title: t('admin.auditLog.actionTypes.EXPORT'), value: 'EXPORT' },
  { title: t('admin.auditLog.actionTypes.VIEW'), value: 'VIEW' },
])

// Helpers
function getActionColor(action: string): string {
  const colors: Record<string, string> = {
    CREATE: 'success',
    UPDATE: 'info',
    DELETE: 'error',
    LOGIN: 'primary',
    LOGOUT: 'grey',
    EXPORT: 'warning',
    VIEW: 'secondary',
  }
  return colors[action] || 'grey'
}

function getActionIcon(action: string): string {
  const icons: Record<string, string> = {
    CREATE: 'mdi-plus',
    UPDATE: 'mdi-pencil',
    DELETE: 'mdi-delete',
    LOGIN: 'mdi-login',
    LOGOUT: 'mdi-logout',
    EXPORT: 'mdi-download',
    VIEW: 'mdi-eye',
  }
  return icons[action] || 'mdi-circle'
}

function formatDate(date: string): string {
  return new Date(date).toLocaleString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function formatValue(value: any): string {
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

// API calls
async function fetchLogs() {
  loading.value = true
  try {
    const params: Record<string, any> = {
      page: page.value,
      per_page: perPage.value,
    }
    if (actionFilter.value) params.action = actionFilter.value
    if (entityTypeFilter.value) params.entity_type = entityTypeFilter.value
    if (startDate.value) params.start_date = new Date(startDate.value).toISOString()
    if (endDate.value) params.end_date = new Date(endDate.value).toISOString()

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
