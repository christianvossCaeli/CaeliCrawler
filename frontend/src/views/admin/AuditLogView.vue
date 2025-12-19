<template>
  <v-container fluid>
    <!-- Header -->
    <v-row class="mb-4">
      <v-col>
        <h1 class="text-h4 font-weight-bold">
          <v-icon start size="32">mdi-history</v-icon>
          Audit-Log
        </h1>
        <p class="text-body-2 text-medium-emphasis mt-1">
          Alle Benutzeraktionen und Systemänderungen
        </p>
      </v-col>
    </v-row>

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
              <div class="text-caption">Gesamt</div>
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
              <div class="text-caption">Heute</div>
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
              <div class="text-caption">Diese Woche</div>
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
              <div class="text-caption">Aktive Benutzer</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Filters -->
    <v-row class="mb-4">
      <v-col cols="12" md="3">
        <v-select
          v-model="actionFilter"
          label="Aktion"
          :items="actionOptions"
          variant="outlined"
          density="compact"
          clearable
          @update:model-value="fetchLogs"
        />
      </v-col>
      <v-col cols="12" md="3">
        <v-text-field
          v-model="entityTypeFilter"
          label="Entity-Typ"
          variant="outlined"
          density="compact"
          clearable
          placeholder="z.B. Category, User"
          @update:model-value="debouncedFetch"
        />
      </v-col>
      <v-col cols="12" md="3">
        <v-text-field
          v-model="startDate"
          label="Von"
          type="date"
          variant="outlined"
          density="compact"
          clearable
          @update:model-value="fetchLogs"
        />
      </v-col>
      <v-col cols="12" md="3">
        <v-text-field
          v-model="endDate"
          label="Bis"
          type="date"
          variant="outlined"
          density="compact"
          clearable
          @update:model-value="fetchLogs"
        />
      </v-col>
    </v-row>

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
          <span v-else class="text-medium-emphasis">System</span>
        </template>

        <!-- Changes Column -->
        <template #item.changes="{ item }">
          <v-btn
            v-if="Object.keys(item.changes).length > 0"
            variant="text"
            size="small"
            @click="showChanges(item)"
          >
            <v-icon start>mdi-eye</v-icon>
            Details
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
          Änderungen
        </v-card-title>
        <v-card-text>
          <v-table density="compact" v-if="selectedLog">
            <thead>
              <tr>
                <th>Feld</th>
                <th>Vorher</th>
                <th>Nachher</th>
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
          <v-btn variant="text" @click="changesDialogOpen = false">
            Schließen
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/services/api'

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
const headers = [
  { title: 'Aktion', key: 'action', sortable: false, width: 130 },
  { title: 'Entity', key: 'entity', sortable: false },
  { title: 'Benutzer', key: 'user_email', sortable: false, width: 200 },
  { title: 'Änderungen', key: 'changes', sortable: false, width: 120 },
  { title: 'Zeitpunkt', key: 'created_at', sortable: false, width: 180 },
]

const actionOptions = [
  { title: 'CREATE', value: 'CREATE' },
  { title: 'UPDATE', value: 'UPDATE' },
  { title: 'DELETE', value: 'DELETE' },
  { title: 'LOGIN', value: 'LOGIN' },
  { title: 'LOGOUT', value: 'LOGOUT' },
  { title: 'EXPORT', value: 'EXPORT' },
  { title: 'VIEW', value: 'VIEW' },
]

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

// Debounce
let searchTimeout: ReturnType<typeof setTimeout>
function debouncedFetch() {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => fetchLogs(), 300)
}

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

    const response = await api.get('/api/admin/audit', { params })
    logs.value = response.data.items
    totalLogs.value = response.data.total
  } catch (error) {
    console.error('Failed to fetch audit logs:', error)
  } finally {
    loading.value = false
  }
}

async function fetchStats() {
  try {
    const response = await api.get('/api/admin/audit/stats')
    stats.value = response.data
  } catch (error) {
    console.error('Failed to fetch stats:', error)
  }
}

onMounted(() => {
  fetchLogs()
  fetchStats()
})
</script>
