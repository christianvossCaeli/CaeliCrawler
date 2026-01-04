<template>
  <v-dialog
    :model-value="modelValue"
    :max-width="DIALOG_SIZES.SM"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2">mdi-chart-arc</v-icon>
        {{ t('llm.requestLimitIncrease') }}
      </v-card-title>

      <v-card-text>
        <!-- Current Status -->
        <v-alert
          v-if="status"
          :type="alertType"
          variant="tonal"
          density="compact"
          class="mb-4"
        >
          <div class="d-flex justify-space-between align-center">
            <span>{{ t('llm.currentUsage') }}</span>
            <span class="font-weight-bold">
              {{ formatCurrency(status.current_usage_cents) }} / {{ formatCurrency(status.monthly_limit_cents) }}
              ({{ status.usage_percent.toFixed(0) }}%)
            </span>
          </div>
          <v-progress-linear
            :model-value="Math.min(status.usage_percent, 100)"
            :color="progressColor"
            height="6"
            rounded
            class="mt-2"
          />
        </v-alert>

        <!-- Pending Requests -->
        <v-alert
          v-if="hasPendingRequest"
          type="info"
          variant="tonal"
          density="compact"
          class="mb-4"
        >
          <div class="d-flex align-center">
            <v-icon class="mr-2" size="small">mdi-clock-outline</v-icon>
            {{ t('llm.pendingRequestExists') }}
          </div>
        </v-alert>

        <!-- Admin Self-Service Section -->
        <v-alert
          v-if="isAdmin"
          type="info"
          variant="tonal"
          density="compact"
          class="mb-4"
        >
          <div class="d-flex align-center">
            <v-icon class="mr-2" size="small">mdi-shield-account</v-icon>
            {{ t('llm.adminSelfService') }}
          </div>
        </v-alert>

        <!-- Request Form (different for admin vs regular user) -->
        <v-form
          v-if="isAdmin || !hasPendingRequest"
          ref="formRef"
          @submit.prevent="handleSubmit"
        >
          <v-text-field
            v-model.number="requestedLimitDollars"
            :label="isAdmin ? t('llm.newLimit') : t('llm.requestedLimit')"
            :hint="isAdmin ? t('llm.adminLimitHint') : t('llm.requestedLimitHint')"
            type="number"
            step="1"
            min="1"
            prefix="$"
            :rules="isAdmin ? [
              v => !!v || t('validation.required'),
              v => v > 0 || t('llm.mustBePositive'),
            ] : [
              v => !!v || t('validation.required'),
              v => v > currentLimitDollars || t('llm.mustBeGreaterThanCurrent'),
            ]"
            class="mb-4"
            persistent-hint
          />

          <v-textarea
            v-if="!isAdmin"
            v-model="reason"
            :label="t('llm.reason')"
            :hint="t('llm.reasonHint')"
            :rules="[
              v => !!v || t('validation.required'),
              v => v.length >= 10 || t('llm.reasonTooShort'),
            ]"
            rows="3"
            counter
            maxlength="1000"
            persistent-hint
          />
        </v-form>

        <!-- Request History -->
        <template v-if="requests.length > 0">
          <v-divider class="my-4" />
          <div class="text-subtitle-2 mb-2">{{ t('llm.requestHistory') }}</div>
          <v-list density="compact" class="request-history">
            <v-list-item
              v-for="request in requests"
              :key="request.id"
              :class="getRequestClass(request.status)"
            >
              <template #prepend>
                <v-icon :color="getStatusColor(request.status)" size="small">
                  {{ getStatusIcon(request.status) }}
                </v-icon>
              </template>
              <v-list-item-title class="text-body-2">
                {{ formatCurrency(request.requested_limit_cents) }}
                <v-chip
                  :color="getStatusColor(request.status)"
                  size="x-small"
                  variant="tonal"
                  class="ml-2"
                >
                  {{ t(`llm.requestStatus.${request.status}`) }}
                </v-chip>
              </v-list-item-title>
              <v-list-item-subtitle class="text-caption">
                {{ formatDate(request.created_at) }}
                <template v-if="request.admin_notes">
                  - {{ request.admin_notes }}
                </template>
              </v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </template>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn
          variant="text"
          @click="$emit('update:modelValue', false)"
        >
          {{ t('common.close') }}
        </v-btn>
        <v-btn
          v-if="isAdmin || !hasPendingRequest"
          color="primary"
          variant="flat"
          :loading="submitting"
          :disabled="!canSubmit"
          @click="handleSubmit"
        >
          {{ isAdmin ? t('llm.updateLimit') : t('llm.submitRequest') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { DIALOG_SIZES } from '@/config/ui'
import { getMyLimitRequests, requestLimitIncrease, updateOwnLimit } from '@/services/api/llm'
import type { LimitIncreaseRequest, LimitRequestStatus, UserBudgetStatus } from '@/types/llm-usage'
import { useSnackbar } from '@/composables/useSnackbar'
import { useAuthStore } from '@/stores/auth'
import {
  formatCurrency,
  formatDate,
  getStatusColor,
  getStatusIcon,
  getBudgetColor,
  getBudgetAlertType,
} from '@/utils/llmFormatting'

const props = defineProps<{
  modelValue: boolean
  status: UserBudgetStatus | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  submitted: []
}>()

const { t } = useI18n()
const { showSuccess, showError } = useSnackbar()
const authStore = useAuthStore()

// Check if user is admin for self-service limit update
const isAdmin = computed(() => authStore.isAdmin)

const formRef = ref()
const submitting = ref(false)
const requests = ref<LimitIncreaseRequest[]>([])
const requestedLimitDollars = ref(0)
const reason = ref('')

const currentLimitDollars = computed(() => {
  if (!props.status) return 0
  return props.status.monthly_limit_cents / 100
})

const hasPendingRequest = computed(() => {
  return requests.value.some(r => r.status === 'PENDING')
})

const canSubmit = computed(() => {
  if (isAdmin.value) {
    // Admins only need a positive value
    return requestedLimitDollars.value > 0
  }
  // Regular users need value > current AND a reason
  return requestedLimitDollars.value > currentLimitDollars.value && reason.value.length >= 10
})

const alertType = computed(() => getBudgetAlertType(props.status))

const progressColor = computed(() => getBudgetColor(props.status))

function getRequestClass(status: LimitRequestStatus): string {
  return `request-item request-item--${status}`
}

async function loadRequests() {
  try {
    requests.value = await getMyLimitRequests()
  } catch {
    requests.value = []
  }
}

async function handleSubmit() {
  const { valid } = await formRef.value?.validate() || { valid: false }
  if (!valid) return

  submitting.value = true
  try {
    if (isAdmin.value) {
      // Admin self-service: directly update own limit
      await updateOwnLimit(requestedLimitDollars.value * 100)
      showSuccess(t('llm.limitUpdated'))
    } else {
      // Regular user: submit request for approval
      await requestLimitIncrease({
        requested_limit_cents: requestedLimitDollars.value * 100,
        reason: reason.value,
      })
      showSuccess(t('llm.requestSubmitted'))
    }
    emit('submitted')
    emit('update:modelValue', false)
    reason.value = ''
    requestedLimitDollars.value = 0
    await loadRequests()
  } catch (error: unknown) {
    const message = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || t('common.error')
    showError(message)
  } finally {
    submitting.value = false
  }
}

watch(() => props.modelValue, (open) => {
  if (open) {
    loadRequests()
    if (props.status) {
      if (isAdmin.value) {
        // Admins see their current limit as default
        requestedLimitDollars.value = props.status.monthly_limit_cents / 100
      } else {
        // Suggest 50% increase as default for regular users
        requestedLimitDollars.value = Math.ceil((props.status.monthly_limit_cents / 100) * 1.5)
      }
    }
  }
})

onMounted(() => {
  if (props.modelValue) {
    loadRequests()
  }
})
</script>

<style scoped>
.request-history {
  max-height: 200px;
  overflow-y: auto;
}

.request-item {
  border-radius: 4px;
  margin-bottom: 4px;
}

.request-item--pending {
  background-color: rgba(var(--v-theme-warning), 0.05);
}

.request-item--approved {
  background-color: rgba(var(--v-theme-success), 0.05);
}

.request-item--denied {
  background-color: rgba(var(--v-theme-error), 0.05);
}
</style>
