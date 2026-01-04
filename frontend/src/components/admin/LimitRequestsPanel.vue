<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-icon class="mr-2">mdi-account-clock</v-icon>
      {{ t('llm.limitRequests') }}
      <v-chip
        v-if="pendingCount > 0"
        color="warning"
        size="small"
        class="ml-2"
      >
        {{ pendingCount }} {{ t('llm.pending') }}
      </v-chip>
      <v-spacer />
      <v-btn
        icon="mdi-refresh"
        variant="text"
        size="small"
        :loading="loading"
        @click="loadRequests"
      />
    </v-card-title>

    <v-card-text>
      <!-- Filters -->
      <v-row class="mb-4">
        <v-col cols="12" sm="4">
          <v-select
            v-model="statusFilter"
            :items="statusOptions"
            :label="t('llm.filterByStatus')"
            clearable
            density="compact"
            hide-details
          />
        </v-col>
      </v-row>

      <!-- Table -->
      <v-data-table
        :headers="headers"
        :items="requests"
        :loading="loading"
        :items-per-page="10"
        class="elevation-0"
      >
        <template #item.user_email="{ item }">
          <span class="font-weight-medium">{{ item.user_email }}</span>
        </template>

        <template #item.current_limit_cents="{ item }">
          {{ formatCurrency(item.current_limit_cents) }}
        </template>

        <template #item.requested_limit_cents="{ item }">
          <span class="font-weight-bold text-primary">
            {{ formatCurrency(item.requested_limit_cents) }}
          </span>
          <v-chip size="x-small" color="info" variant="tonal" class="ml-1">
            +{{ formatPercentIncrease(item.requested_limit_cents, item.current_limit_cents) }}%
          </v-chip>
        </template>

        <template #item.status="{ item }">
          <v-chip
            :color="getStatusColor(item.status)"
            size="small"
            variant="tonal"
          >
            {{ t(`llm.requestStatus.${item.status}`) }}
          </v-chip>
        </template>

        <template #item.created_at="{ item }">
          {{ formatDate(item.created_at, true) }}
        </template>

        <template #item.actions="{ item }">
          <template v-if="item.status === 'PENDING'">
            <v-btn
              icon="mdi-check"
              color="success"
              variant="text"
              size="small"
              :loading="processingId === item.id"
              :aria-label="t('llm.approveRequest')"
              @click="handleApprove(item)"
            />
            <v-btn
              icon="mdi-close"
              color="error"
              variant="text"
              size="small"
              :loading="processingId === item.id"
              :aria-label="t('llm.denyRequest')"
              @click="handleDeny(item)"
            />
          </template>
          <template v-else>
            <v-tooltip location="top">
              <template #activator="{ props: tooltipProps }">
                <v-icon
                  v-bind="tooltipProps"
                  size="small"
                  :color="item.reviewed_by ? 'grey' : 'grey-lighten-2'"
                >
                  mdi-account-check
                </v-icon>
              </template>
              <span v-if="item.reviewed_at">
                {{ t('llm.reviewedAt') }}: {{ formatDate(item.reviewed_at, true) }}
              </span>
            </v-tooltip>
          </template>
        </template>

        <template #expanded-row="{ columns, item }">
          <tr>
            <td :colspan="columns.length" class="pa-4 bg-grey-lighten-5">
              <div class="text-subtitle-2 mb-2">{{ t('llm.reason') }}:</div>
              <div class="text-body-2">{{ item.reason }}</div>
              <template v-if="item.admin_notes">
                <div class="text-subtitle-2 mt-3 mb-2">{{ t('llm.adminNotes') }}:</div>
                <div class="text-body-2">{{ item.admin_notes }}</div>
              </template>
            </td>
          </tr>
        </template>

        <template #no-data>
          <div class="text-center py-8 text-grey">
            <v-icon size="48" class="mb-2">mdi-inbox</v-icon>
            <div>{{ t('llm.noRequests') }}</div>
          </div>
        </template>
      </v-data-table>
    </v-card-text>

    <!-- Notes Dialog -->
    <v-dialog v-model="notesDialog" :max-width="DIALOG_SIZES.XS">
      <v-card>
        <v-card-title>
          {{ notesAction === 'approve' ? t('llm.approveRequest') : t('llm.denyRequest') }}
        </v-card-title>
        <v-card-text>
          <v-textarea
            v-model="adminNotes"
            :label="t('llm.adminNotes')"
            :hint="t('llm.adminNotesHint')"
            rows="3"
            persistent-hint
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="notesDialog = false">
            {{ t('common.cancel') }}
          </v-btn>
          <v-btn
            :color="notesAction === 'approve' ? 'success' : 'error'"
            variant="flat"
            :loading="processingId !== null"
            @click="confirmAction"
          >
            {{ notesAction === 'approve' ? t('llm.approve') : t('llm.deny') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  approveLimitRequest,
  denyLimitRequest,
  getLimitRequests,
} from '@/services/api/llm'
import type { LimitIncreaseRequest, LimitRequestStatus } from '@/types/llm-usage'
import { useSnackbar } from '@/composables/useSnackbar'
import {
  formatCurrency,
  formatDate,
  formatPercentIncrease,
  getStatusColor,
} from '@/utils/llmFormatting'
import { DIALOG_SIZES } from '@/config/ui'

const { t } = useI18n()
const { showSuccess, showError } = useSnackbar()

const loading = ref(false)
const requests = ref<LimitIncreaseRequest[]>([])
const pendingCount = ref(0)
const statusFilter = ref<LimitRequestStatus | '' | null>(null)
const processingId = ref<string | null>(null)
const notesDialog = ref(false)
const notesAction = ref<'approve' | 'deny'>('approve')
const adminNotes = ref('')
const selectedRequest = ref<LimitIncreaseRequest | null>(null)

const headers = computed(() => [
  { title: t('llm.user'), key: 'user_email', sortable: true },
  { title: t('llm.currentLimit'), key: 'current_limit_cents', sortable: true },
  { title: t('llm.requestedLimit'), key: 'requested_limit_cents', sortable: true },
  { title: t('llm.status'), key: 'status', sortable: true },
  { title: t('llm.requestedAt'), key: 'created_at', sortable: true },
  { title: t('common.actions'), key: 'actions', sortable: false, align: 'end' as const },
])

const statusOptions = computed(() => [
  { title: t('llm.requestStatus.PENDING'), value: 'PENDING' },
  { title: t('llm.requestStatus.APPROVED'), value: 'APPROVED' },
  { title: t('llm.requestStatus.DENIED'), value: 'DENIED' },
])

async function loadRequests() {
  loading.value = true
  try {
    // Ensure empty string is treated as no filter (v-select clearable may set '')
    const status = statusFilter.value || undefined
    const response = await getLimitRequests(status ? { status } : undefined)
    requests.value = response.requests
    pendingCount.value = response.pending_count
  } catch {
    showError(t('common.loadError'))
  } finally {
    loading.value = false
  }
}

function handleApprove(request: LimitIncreaseRequest) {
  selectedRequest.value = request
  notesAction.value = 'approve'
  adminNotes.value = ''
  notesDialog.value = true
}

function handleDeny(request: LimitIncreaseRequest) {
  selectedRequest.value = request
  notesAction.value = 'deny'
  adminNotes.value = ''
  notesDialog.value = true
}

async function confirmAction() {
  if (!selectedRequest.value) return

  processingId.value = selectedRequest.value.id
  try {
    if (notesAction.value === 'approve') {
      await approveLimitRequest(selectedRequest.value.id, adminNotes.value || undefined)
      showSuccess(t('llm.requestApproved'))
    } else {
      await denyLimitRequest(selectedRequest.value.id, adminNotes.value || undefined)
      showSuccess(t('llm.requestDenied'))
    }
    notesDialog.value = false
    await loadRequests()
  } catch {
    showError(t('common.error'))
  } finally {
    processingId.value = null
  }
}

watch(statusFilter, (newValue) => {
  // Normalize empty string to null for cleaner handling
  if (newValue === '') {
    statusFilter.value = null
    return // The assignment will trigger this watch again with null
  }
  loadRequests()
})

onMounted(() => {
  loadRequests()
})

defineExpose({
  reload: loadRequests,
  pendingCount,
})
</script>

<style scoped>
.v-data-table :deep(.v-data-table__tr--expanded) {
  background-color: transparent !important;
}
</style>
