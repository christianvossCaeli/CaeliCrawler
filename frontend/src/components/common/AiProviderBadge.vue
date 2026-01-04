<template>
  <div v-if="configInfo || loading || hasError" class="ai-provider-badge">
    <v-tooltip location="bottom" max-width="300">
      <template #activator="{ props: tooltipProps }">
        <v-chip
          v-bind="tooltipProps"
          :color="chipColor"
          :variant="variant"
          size="small"
          class="ai-badge-chip"
          role="status"
          :aria-label="ariaLabel"
        >
          <v-icon v-if="loading" size="x-small" class="mr-1">mdi-loading mdi-spin</v-icon>
          <v-icon v-else :icon="providerIcon" size="x-small" class="mr-1" />
          <span v-if="!loading">{{ displayText }}</span>
          <span v-else>{{ t('common.loading') }}</span>
        </v-chip>
      </template>
      <div class="ai-badge-tooltip">
        <template v-if="loading">
          <span>{{ t('aiProvider.loadingConfig') }}</span>
        </template>
        <template v-else-if="hasError">
          <div class="tooltip-error">
            <v-icon size="x-small" class="mr-1">mdi-alert-circle</v-icon>
            {{ t('aiProvider.loadError') }}
          </div>
        </template>
        <template v-else-if="configInfo">
          <div class="tooltip-title">{{ configInfo.purpose_name }}</div>
          <div v-if="configInfo.is_configured" class="tooltip-content">
            <div class="tooltip-row">
              <span class="tooltip-label">{{ t('aiProvider.provider') }}:</span>
              <span>{{ configInfo.provider_name }}</span>
            </div>
            <div v-if="configInfo.model" class="tooltip-row">
              <span class="tooltip-label">{{ t('aiProvider.model') }}:</span>
              <span>{{ configInfo.model }}</span>
            </div>
            <div v-if="hasPricing" class="tooltip-pricing">
              <div class="tooltip-row">
                <span class="tooltip-label">{{ t('aiProvider.inputCost') }}:</span>
                <span>${{ formatPrice(configInfo.pricing_input_per_1m) }}/1M Tokens</span>
              </div>
              <div class="tooltip-row">
                <span class="tooltip-label">{{ t('aiProvider.outputCost') }}:</span>
                <span>${{ formatPrice(configInfo.pricing_output_per_1m) }}/1M Tokens</span>
              </div>
            </div>
            <div v-if="estimatedCost !== null" class="tooltip-estimate">
              <v-icon size="x-small" class="mr-1">mdi-approximately-equal</v-icon>
              <span>{{ t('aiProvider.estimatedCost') }}: {{ formatCurrency(estimatedCost) }}</span>
            </div>
          </div>
          <div v-else class="tooltip-warning">
            <v-icon size="x-small" class="mr-1">mdi-alert</v-icon>
            {{ t('aiProvider.notConfigured') }}
          </div>
        </template>
      </div>
    </v-tooltip>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getActiveConfig, type ActiveConfigInfo, type LLMPurpose } from '@/services/api/admin'
import { useLogger } from '@/composables/useLogger'
import { getProviderIcon as getIcon, getProviderColor as getColor } from '@/utils/llmProviders'

const logger = useLogger('AiProviderBadge')

// Simple in-memory cache for config data (shared across instances)
const configCache = new Map<string, { data: ActiveConfigInfo; timestamp: number }>()
const CACHE_TTL_MS = 60_000 // 1 minute cache

const props = withDefaults(defineProps<{
  /**
   * The LLM purpose to show config for
   */
  purpose: LLMPurpose
  /**
   * Optional: estimated input tokens for cost calculation
   */
  inputTokens?: number
  /**
   * Optional: estimated output tokens for cost calculation
   */
  outputTokens?: number
  /**
   * Chip variant
   */
  variant?: 'flat' | 'text' | 'elevated' | 'tonal' | 'outlined' | 'plain'
  /**
   * Whether to show compact view (icon only)
   */
  compact?: boolean
}>(), {
  inputTokens: 0,
  outputTokens: 0,
  variant: 'tonal',
  compact: false,
})

const { t } = useI18n()

const loading = ref(false)
const configInfo = ref<ActiveConfigInfo | null>(null)
const hasError = ref(false)

const providerIcon = computed(() => {
  if (!configInfo.value?.provider) return 'mdi-help-circle'
  return getIcon(configInfo.value.provider)
})

const chipColor = computed(() => {
  if (loading.value) return 'grey'
  if (hasError.value) return 'error'
  if (!configInfo.value?.is_configured) return 'warning'
  if (!configInfo.value?.provider) return 'primary'
  return getColor(configInfo.value.provider)
})

const displayText = computed(() => {
  if (props.compact) return ''
  if (hasError.value) return t('common.error')
  if (!configInfo.value?.is_configured) return t('aiProvider.notConfigured')
  return configInfo.value?.provider_name || configInfo.value?.provider || ''
})

const ariaLabel = computed(() => {
  if (loading.value) return t('aiProvider.loadingConfig')
  if (hasError.value) return t('aiProvider.loadError')
  if (!configInfo.value?.is_configured) return t('aiProvider.notConfigured')
  const provider = configInfo.value?.provider_name || configInfo.value?.provider
  const model = configInfo.value?.model
  return model ? `${provider}: ${model}` : provider
})

const hasPricing = computed(() => {
  return configInfo.value?.pricing_input_per_1m != null &&
         configInfo.value?.pricing_output_per_1m != null
})

const estimatedCost = computed(() => {
  if (!hasPricing.value || !configInfo.value) return null
  if (props.inputTokens === 0 && props.outputTokens === 0) return null

  const inputCost = (props.inputTokens / 1_000_000) * (configInfo.value.pricing_input_per_1m || 0)
  const outputCost = (props.outputTokens / 1_000_000) * (configInfo.value.pricing_output_per_1m || 0)
  return inputCost + outputCost
})

function formatPrice(price: number | null): string {
  if (price === null) return '-'
  return price.toFixed(2)
}

function formatCurrency(amount: number): string {
  if (amount < 0.01) {
    return `$${(amount * 100).toFixed(2)} cents`
  }
  return `$${amount.toFixed(4)}`
}

async function loadConfig() {
  if (!props.purpose) return

  // Check cache first
  const cached = configCache.get(props.purpose)
  if (cached && Date.now() - cached.timestamp < CACHE_TTL_MS) {
    configInfo.value = cached.data
    hasError.value = false
    return
  }

  loading.value = true
  hasError.value = false

  try {
    const response = await getActiveConfig(props.purpose)
    configInfo.value = response.data

    // Update cache
    configCache.set(props.purpose, {
      data: response.data,
      timestamp: Date.now(),
    })
  } catch (error) {
    logger.error('Failed to load AI config', { purpose: props.purpose, error })
    configInfo.value = null
    hasError.value = true
  } finally {
    loading.value = false
  }
}

// Load on mount
onMounted(() => {
  loadConfig()
})

// Reload when purpose changes
watch(() => props.purpose, () => {
  loadConfig()
})

// Expose for parent components
defineExpose({
  reload: loadConfig,
  configInfo,
})
</script>

<style scoped>
.ai-provider-badge {
  display: inline-flex;
  align-items: center;
}

.ai-badge-chip {
  cursor: help;
  font-size: 0.75rem;
}

.ai-badge-tooltip {
  padding: 4px;
}

.tooltip-title {
  font-weight: 600;
  margin-bottom: 8px;
  border-bottom: 1px solid currentColor;
  opacity: 0.8;
  padding-bottom: 4px;
}

.tooltip-content {
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

.tooltip-pricing {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed currentColor;
  opacity: 0.8;
}

.tooltip-estimate {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid currentColor;
  font-weight: 600;
  color: rgb(var(--v-theme-success));
}

.tooltip-warning {
  color: rgb(var(--v-theme-warning));
  display: flex;
  align-items: center;
}

.tooltip-error {
  color: rgb(var(--v-theme-error));
  display: flex;
  align-items: center;
}
</style>
