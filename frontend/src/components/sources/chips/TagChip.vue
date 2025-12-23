<template>
  <v-chip
    :color="getTagColor(tag)"
    :size="size"
    :variant="variant"
    :closable="closable"
    @click:close="$emit('close')"
  >
    <v-icon v-if="showIcon" start size="small">mdi-tag</v-icon>
    {{ tag }}
  </v-chip>
</template>

<script setup lang="ts">
/**
 * TagChip - Displays a tag with consistent color coding
 *
 * @example
 * <TagChip tag="Open Data" />
 * <TagChip tag="API" closable @close="removeTag" />
 */
import { useSourceHelpers } from '@/composables/useSourceHelpers'

interface Props {
  tag: string
  size?: 'x-small' | 'small' | 'default' | 'large' | 'x-large'
  variant?: 'flat' | 'outlined' | 'text' | 'tonal' | 'elevated' | 'plain'
  showIcon?: boolean
  closable?: boolean
}

withDefaults(defineProps<Props>(), {
  size: 'small',
  variant: 'tonal',
  showIcon: false,
  closable: false,
})

defineEmits<{
  (e: 'close'): void
}>()

const { getTagColor } = useSourceHelpers()
</script>
