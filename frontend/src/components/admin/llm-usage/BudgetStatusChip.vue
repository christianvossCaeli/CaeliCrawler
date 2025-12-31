<template>
  <v-chip
    v-if="status"
    :color="chipColor"
    size="small"
    label
    :title="tooltipText"
  >
    <v-icon start size="small">{{ chipIcon }}</v-icon>
    {{ status.usage_percent.toFixed(0) }}%
  </v-chip>
  <v-chip v-else size="small" color="grey" label>
    -
  </v-chip>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { BudgetStatus } from '@/types/llm-usage'

const props = defineProps<{
  budgetId: string
  status?: BudgetStatus
}>()

const chipColor = computed(() => {
  if (!props.status) return 'grey'
  if (props.status.is_critical) return 'error'
  if (props.status.is_warning) return 'warning'
  return 'success'
})

const chipIcon = computed(() => {
  if (!props.status) return 'mdi-minus'
  if (props.status.is_critical) return 'mdi-alert-circle'
  if (props.status.is_warning) return 'mdi-alert'
  return 'mdi-check-circle'
})

const tooltipText = computed(() => {
  if (!props.status) return ''
  const current = (props.status.current_usage_cents / 100).toFixed(2)
  const limit = (props.status.monthly_limit_cents / 100).toFixed(2)
  return `$${current} / $${limit}`
})
</script>
