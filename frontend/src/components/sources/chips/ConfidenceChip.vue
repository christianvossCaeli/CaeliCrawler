<template>
  <v-chip
    :color="confidenceColor"
    :size="size"
    :variant="variant"
  >
    <v-icon v-if="showIcon" start size="small">{{ confidenceIcon }}</v-icon>
    {{ formattedConfidence }}
  </v-chip>
</template>

<script setup lang="ts">
/**
 * ConfidenceChip - Displays confidence score with color coding
 *
 * @example
 * <ConfidenceChip :confidence="0.85" />
 * <ConfidenceChip :confidence="0.45" size="x-small" />
 */
import { computed } from 'vue'

interface Props {
  /** Confidence value between 0 and 1 */
  confidence: number
  size?: 'x-small' | 'small' | 'default' | 'large' | 'x-large'
  variant?: 'flat' | 'outlined' | 'text' | 'tonal' | 'elevated' | 'plain'
  showIcon?: boolean
  /** Show as percentage (default) or decimal */
  showAsPercent?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  size: 'small',
  variant: 'tonal',
  showIcon: false,
  showAsPercent: true,
})

/** Get color based on confidence level */
const confidenceColor = computed(() => {
  if (props.confidence >= 0.8) return 'success'
  if (props.confidence >= 0.6) return 'primary'
  if (props.confidence >= 0.4) return 'warning'
  return 'error'
})

/** Get icon based on confidence level */
const confidenceIcon = computed(() => {
  if (props.confidence >= 0.8) return 'mdi-check-circle'
  if (props.confidence >= 0.6) return 'mdi-check'
  if (props.confidence >= 0.4) return 'mdi-alert'
  return 'mdi-alert-circle'
})

/** Format confidence for display */
const formattedConfidence = computed(() => {
  if (props.showAsPercent) {
    return `${Math.round(props.confidence * 100)}%`
  }
  return props.confidence.toFixed(2)
})
</script>
