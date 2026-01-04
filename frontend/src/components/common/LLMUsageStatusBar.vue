<template>
  <div v-if="status || loading" class="llm-usage-status-bar">
    <v-tooltip location="bottom" max-width="350">
      <template #activator="{ props: tooltipProps }">
        <v-chip
          v-bind="tooltipProps"
          :color="chipColor"
          variant="tonal"
          size="small"
          class="status-chip"
          :class="{ 'status-chip--blocked': status?.is_blocked }"
          role="button"
          :aria-label="ariaLabel"
          tabindex="0"
          @click="handleClick"
          @keydown.enter="handleClick"
          @keydown.space.prevent="handleClick"
        >
          <v-icon v-if="loading" size="x-small" class="mr-1">mdi-loading mdi-spin</v-icon>
          <v-icon v-else-if="status?.is_blocked" size="x-small" class="mr-1">mdi-lock</v-icon>
          <v-icon v-else size="x-small" class="mr-1">mdi-chart-donut</v-icon>
          <span v-if="!loading" class="status-text">
            {{ formatPercent(status?.usage_percent || 0) }}%
          </span>
          <span v-else>...</span>
        </v-chip>
      </template>

      <div class="status-tooltip">
        <template v-if="loading">
          <span>{{ t('llm.loading') }}</span>
        </template>
        <template v-else-if="status">
          <div class="tooltip-header">
            <v-icon size="small" class="mr-1">mdi-robot</v-icon>
            {{ t('llm.budgetStatus') }}
          </div>

          <div class="tooltip-progress">
            <v-progress-linear
              :model-value="Math.min(status.usage_percent, 100)"
              :color="progressColor"
              height="8"
              rounded
            />
          </div>

          <div class="tooltip-stats">
            <div class="tooltip-row">
              <span class="tooltip-label">{{ t('llm.used') }}:</span>
              <span>{{ formatCurrency(status.current_usage_cents) }}</span>
            </div>
            <div class="tooltip-row">
              <span class="tooltip-label">{{ t('llm.limit') }}:</span>
              <span>{{ formatCurrency(status.monthly_limit_cents) }}</span>
            </div>
            <div class="tooltip-row">
              <span class="tooltip-label">{{ t('llm.usage') }}:</span>
              <span :class="usageClass">{{ formatPercent(status.usage_percent) }}%</span>
            </div>
          </div>

          <div v-if="status.is_blocked" class="tooltip-warning blocked">
            <v-icon size="x-small" class="mr-1">mdi-alert-circle</v-icon>
            {{ t('llm.budgetBlocked') }}
          </div>
          <div v-else-if="status.is_critical" class="tooltip-warning critical">
            <v-icon size="x-small" class="mr-1">mdi-alert</v-icon>
            {{ t('llm.budgetCritical') }}
          </div>
          <div v-else-if="status.is_warning" class="tooltip-warning warning">
            <v-icon size="x-small" class="mr-1">mdi-alert</v-icon>
            {{ t('llm.budgetWarning') }}
          </div>

          <div class="tooltip-action">
            <span class="tooltip-hint">
              {{ t('llm.clickForDetails') }}
            </span>
          </div>
        </template>
      </div>
    </v-tooltip>

    <LimitIncreaseDialog
      v-model="showDialog"
      :status="status"
      @submitted="handleRequestSubmitted"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getMyLLMUsage } from '@/services/api/llm'
import type { UserBudgetStatus } from '@/types/llm-usage'
import { formatCurrency, formatPercent, getBudgetColor } from '@/utils/llmFormatting'
import LimitIncreaseDialog from './LimitIncreaseDialog.vue'

const { t } = useI18n()

const loading = ref(false)
const status = ref<UserBudgetStatus | null>(null)
const showDialog = ref(false)

const chipColor = computed(() => {
  if (loading.value) return 'grey'
  return getBudgetColor(status.value)
})

const progressColor = computed(() => getBudgetColor(status.value))

const usageClass = computed(() => {
  if (!status.value) return ''
  if (status.value.is_blocked) return 'text-error'
  if (status.value.is_critical) return 'text-error'
  if (status.value.is_warning) return 'text-warning'
  return 'text-success'
})

const ariaLabel = computed(() => {
  if (loading.value) return t('llm.loading')
  if (!status.value) return t('llm.budgetStatus')
  const percent = formatPercent(status.value.usage_percent)
  if (status.value.is_blocked) return t('llm.budgetBlocked')
  return `${t('llm.budgetStatus')}: ${percent}%`
})

function handleClick() {
  showDialog.value = true
}

function handleRequestSubmitted() {
  loadStatus()
}

async function loadStatus() {
  loading.value = true
  try {
    status.value = await getMyLLMUsage()
  } catch {
    status.value = null
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadStatus()
})

defineExpose({
  reload: loadStatus,
  status,
})
</script>

<style scoped>
.llm-usage-status-bar {
  display: inline-flex;
  align-items: center;
}

.status-chip {
  cursor: pointer;
  font-weight: 500;
  transition: transform 0.1s ease;
}

.status-chip:hover {
  transform: scale(1.05);
}

.status-chip--blocked {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

.status-tooltip {
  padding: 8px 4px;
  min-width: 200px;
}

.tooltip-header {
  font-weight: 600;
  font-size: 0.9rem;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
}

.tooltip-progress {
  margin-bottom: 12px;
}

.tooltip-stats {
  font-size: 0.875rem;
}

.tooltip-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin: 4px 0;
}

.tooltip-label {
  opacity: 0.7;
}

.tooltip-warning {
  margin-top: 12px;
  padding: 8px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  font-size: 0.875rem;
}

.tooltip-warning.blocked {
  background-color: rgba(var(--v-theme-error), 0.15);
  color: rgb(var(--v-theme-error));
}

.tooltip-warning.critical {
  background-color: rgba(var(--v-theme-error), 0.1);
  color: rgb(var(--v-theme-error));
}

.tooltip-warning.warning {
  background-color: rgba(var(--v-theme-warning), 0.1);
  color: rgb(var(--v-theme-warning));
}

.tooltip-action {
  margin-top: 12px;
  padding-top: 8px;
  border-top: 1px dashed rgba(255, 255, 255, 0.2);
}

.tooltip-hint {
  font-size: 0.75rem;
  opacity: 0.7;
  font-style: italic;
}

.text-error {
  color: rgb(var(--v-theme-error));
}

.text-warning {
  color: rgb(var(--v-theme-warning));
}

.text-success {
  color: rgb(var(--v-theme-success));
}
</style>
