<template>
  <v-chip
    :color="getStatusColor(status)"
    :size="size"
    :variant="variant"
  >
    <v-icon v-if="showIcon" :start="!!label" size="small">{{ getStatusIcon(status) }}</v-icon>
    <span v-if="label">{{ label }}</span>
    <span v-else>{{ getStatusLabel(status) }}</span>
  </v-chip>
</template>

<script setup lang="ts">
/**
 * SourceStatusChip - Displays source status with icon and color
 *
 * @example
 * <SourceStatusChip status="ACTIVE" />
 * <SourceStatusChip status="ERROR" size="x-small" />
 */
import { useSourceHelpers } from '@/composables/useSourceHelpers'
import type { SourceStatus } from '@/types/sources'

interface Props {
  status: SourceStatus | string | null
  size?: 'x-small' | 'small' | 'default' | 'large' | 'x-large'
  variant?: 'flat' | 'outlined' | 'text' | 'tonal' | 'elevated' | 'plain'
  showIcon?: boolean
  label?: string
}

withDefaults(defineProps<Props>(), {
  size: 'small',
  variant: 'tonal',
  showIcon: true,
})

const { getStatusColor, getStatusIcon, getStatusLabel } = useSourceHelpers()
</script>
