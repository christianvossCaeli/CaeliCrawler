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

      <template #item.source="{ item }">
        <v-chip size="x-small" :color="getSourceColor(item.source)">
          {{ t(`admin.modelPricing.sources.${item.source}`) }}
        </v-chip>
      </template>

      <template #item.last_verified_at="{ item }">
        <div :class="{ 'text-warning': item.is_stale }">
          <v-icon v-if="item.is_stale" size="small" color="warning" class="mr-1">
            mdi-alert
          </v-icon>
          {{ formatDate(item.last_verified_at) }}
          <br>
          <span class="text-caption text-medium-emphasis">
            {{ t('admin.modelPricing.daysAgo', { days: item.days_since_verified }) }}
          </span>
        </div>
      </template>

      <template #item.status="{ item }">
        <v-chip
          v-if="item.is_deprecated"
          size="x-small"
          color="error"
        >
          {{ t('admin.modelPricing.status.deprecated') }}
        </v-chip>
        <v-chip
          v-else-if="item.is_stale"
          size="x-small"
          color="warning"
        >
          {{ t('admin.modelPricing.status.stale') }}
        </v-chip>
        <v-chip
          v-else
          size="x-small"
          color="success"
        >
          {{ t('admin.modelPricing.status.active') }}
        </v-chip>
      </template>

      <template #item.actions="{ item }">
        <div class="d-flex justify-end">
          <v-btn
            icon
            size="x-small"
            variant="text"
            :aria-label="t('admin.modelPricing.actions.edit')"
            @click="$emit('edit', item)"
          >
            <v-icon size="small">mdi-pencil</v-icon>
            <v-tooltip activator="parent" location="top">
              {{ t('admin.modelPricing.actions.edit') }}
            </v-tooltip>
          </v-btn>
          <v-btn
            icon
            size="x-small"
            variant="text"
            color="error"
            :aria-label="t('admin.modelPricing.actions.delete')"
            @click="$emit('delete', item)"
          >
            <v-icon size="small">mdi-delete</v-icon>
            <v-tooltip activator="parent" location="top">
              {{ t('admin.modelPricing.actions.delete') }}
            </v-tooltip>
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
  getSourceColor,
} from '@/utils/llmProviders'
import { useDateFormatter } from '@/composables'

defineProps<{
  entries: PricingEntry[]
  loading: boolean
}>()

defineEmits<{
  edit: [entry: PricingEntry]
  delete: [entry: PricingEntry]
}>()

const { formatDateShort } = useDateFormatter()

const { t } = useI18n()

const headers = computed(() => [
  { title: t('admin.modelPricing.columns.provider'), key: 'provider', width: '140px' },
  { title: t('admin.modelPricing.columns.model'), key: 'model_name' },
  { title: t('admin.modelPricing.columns.inputPrice'), key: 'input_price_per_1m', width: '100px' },
  { title: t('admin.modelPricing.columns.outputPrice'), key: 'output_price_per_1m', width: '100px' },
  { title: t('admin.modelPricing.columns.source'), key: 'source', width: '100px' },
  { title: t('admin.modelPricing.columns.lastVerified'), key: 'last_verified_at', width: '140px' },
  { title: t('admin.modelPricing.columns.status'), key: 'status', width: '100px' },
  { title: t('admin.modelPricing.columns.actions'), key: 'actions', width: '130px', sortable: false },
])

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '-'
  return formatDateShort(dateStr)
}
</script>
