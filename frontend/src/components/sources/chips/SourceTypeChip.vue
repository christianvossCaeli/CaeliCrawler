<template>
  <v-chip
    :color="getTypeColor(type)"
    :size="size"
    :variant="variant"
    :class="chipClass"
  >
    <v-icon v-if="showIcon" :start="!!label" size="small">{{ getTypeIcon(type) }}</v-icon>
    <span v-if="label">{{ label }}</span>
    <span v-else>{{ getTypeLabel(type) }}</span>
  </v-chip>
</template>

<script setup lang="ts">
/**
 * SourceTypeChip - Displays source type with icon and color
 *
 * @example
 * <SourceTypeChip type="WEBSITE" />
 * <SourceTypeChip type="OPARL_API" size="small" />
 */
import { useSourceHelpers } from '@/composables/useSourceHelpers'
import type { SourceType } from '@/types/sources'

interface Props {
  type: SourceType | string | null
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

const { getTypeColor, getTypeIcon, getTypeLabel } = useSourceHelpers()

const chipClass = ''
</script>
