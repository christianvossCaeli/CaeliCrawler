<template>
  <v-card>
    <v-data-table
      :headers="headers"
      :items="entries"
      :loading="loading"
      :items-per-page="25"
      class="elevation-1"
    >
      <template #item.provider="{ item }">
        <v-chip :color="getProviderColor(item.provider)" size="small" variant="tonal">
          <v-icon :icon="getProviderIcon(item.provider)" size="x-small" start />
          {{ getProviderLabel(item.provider) }}
        </v-chip>
      </template>

      <template #item.model_name="{ item }">
        <div>
          <span class="font-weight-medium">{{ item.model_name }}</span>
          <br v-if="item.display_name">
          <span v-if="item.display_name" class="text-caption text-medium-emphasis">
            {{ item.display_name }}
          </span>
        </div>
      </template>

      <template #item.input_price_per_1m="{ item }">
        <span class="font-weight-medium">${{ item.input_price_per_1m.toFixed(2) }}</span>
      </template>

      <template #item.output_price_per_1m="{ item }">
        <span class="font-weight-medium">${{ item.output_price_per_1m.toFixed(2) }}</span>
      </template>

      <template #item.status="{ item }">
        <v-chip
          v-if="item.is_deprecated"
          size="small"
          color="error"
        >
          {{ t('admin.modelPricing.status.deprecated') }}
        </v-chip>
        <v-chip
          v-else-if="item.is_stale"
          size="small"
          color="warning"
        >
          {{ t('admin.modelPricing.status.stale') }}
          <v-tooltip activator="parent" location="top">
            {{ t('admin.modelPricing.daysAgo', { days: item.days_since_verified }) }}
          </v-tooltip>
        </v-chip>
        <v-chip
          v-else
          size="small"
          color="success"
        >
          {{ t('admin.modelPricing.status.active') }}
          <v-tooltip activator="parent" location="top">
            {{ t('admin.modelPricing.lastSynced', { date: formatDate(item.last_verified_at) }) }}
          </v-tooltip>
        </v-chip>
      </template>

      <template #item.actions="{ item }">
        <div class="d-flex justify-end ga-1">
          <v-btn
            icon="mdi-pencil"
            size="small"
            variant="tonal"
            :title="t('common.edit')"
            :aria-label="t('common.edit')"
            @click="$emit('edit', item)"
          />
          <v-btn
            icon="mdi-delete"
            size="small"
            variant="tonal"
            color="error"
            :title="t('common.delete')"
            :aria-label="t('common.delete')"
            @click="$emit('delete', item)"
          />
        </div>
      </template>

      <!-- Empty State -->
      <template #no-data>
        <div class="text-center py-8">
          <v-icon size="64" color="grey-lighten-1" class="mb-4">mdi-currency-usd</v-icon>
          <h3 class="text-h6 mb-2">{{ t('admin.modelPricing.emptyState.title') }}</h3>
          <p class="text-body-2 text-medium-emphasis mb-4">
            {{ t('admin.modelPricing.emptyState.description') }}
          </p>
          <v-btn color="primary" variant="tonal" @click="$emit('sync')">
            <v-icon start>mdi-cloud-sync</v-icon>
            {{ t('admin.modelPricing.actions.sync') }}
          </v-btn>
        </div>
      </template>
    </v-data-table>
  </v-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { PricingEntry } from '@/services/api/admin'
import {
  getProviderIcon,
  getProviderColor,
  getProviderLabel,
} from '@/utils/llmProviders'
import { useDateFormatter } from '@/composables'

defineProps<{
  entries: PricingEntry[]
  loading: boolean
}>()

defineEmits<{
  edit: [entry: PricingEntry]
  delete: [entry: PricingEntry]
  sync: []
}>()

const { formatDateShort } = useDateFormatter()

const { t } = useI18n()

const headers = computed(() => [
  { title: t('admin.modelPricing.columns.provider'), key: 'provider', width: '140px' },
  { title: t('admin.modelPricing.columns.model'), key: 'model_name' },
  { title: t('admin.modelPricing.columns.inputPrice'), key: 'input_price_per_1m', width: '120px' },
  { title: t('admin.modelPricing.columns.outputPrice'), key: 'output_price_per_1m', width: '120px' },
  { title: t('admin.modelPricing.columns.status'), key: 'status', width: '120px' },
  { title: t('admin.modelPricing.columns.actions'), key: 'actions', width: '100px', sortable: false },
])

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '-'
  return formatDateShort(dateStr)
}
</script>
