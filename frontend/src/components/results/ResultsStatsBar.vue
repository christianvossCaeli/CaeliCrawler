<template>
  <v-row class="mb-4">
    <!-- Total Count -->
    <v-col cols="6" sm="3">
      <v-card variant="outlined">
        <v-card-text class="text-center py-3">
          <div class="text-h5 text-primary">{{ stats.total }}</div>
          <div class="text-caption">{{ $t('results.stats.total') }}</div>
        </v-card-text>
      </v-card>
    </v-col>

    <!-- Verified Count (clickable filter) -->
    <v-col cols="6" sm="3">
      <v-card
        :variant="verifiedFilter === true ? 'elevated' : 'outlined'"
        :color="verifiedFilter === true ? 'success' : undefined"
        class="cursor-pointer stats-card"
        @click="$emit('toggle-verified', true)"
      >
        <v-card-text class="text-center py-3">
          <div class="text-h5 text-success">{{ stats.verified }}</div>
          <div class="text-caption">{{ $t('results.stats.verified') }}</div>
        </v-card-text>
      </v-card>
    </v-col>

    <!-- High Confidence Count -->
    <v-col cols="6" sm="3">
      <v-card variant="outlined">
        <v-card-text class="text-center py-3">
          <div class="text-h5 text-info">{{ stats.high_confidence_count }}</div>
          <div class="text-caption">{{ $t('results.stats.highConfidence') }}</div>
        </v-card-text>
      </v-card>
    </v-col>

    <!-- Average Confidence -->
    <v-col cols="6" sm="3">
      <v-card variant="outlined">
        <v-card-text class="text-center py-3">
          <div class="text-h5">{{ formattedAvgConfidence }}</div>
          <div class="text-caption">{{ $t('results.stats.avgConfidence') }}</div>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
/**
 * ResultsStatsBar - Statistics cards for the Results view
 *
 * Displays key metrics: total, verified, high confidence, average confidence.
 * Verified card is clickable to filter by verified status.
 */
import { computed } from 'vue'
import type { ResultsStats } from '@/composables/results'

const props = defineProps<{
  stats: ResultsStats
  verifiedFilter: boolean | null
}>()

defineEmits<{
  'toggle-verified': [value: boolean]
}>()

const formattedAvgConfidence = computed(() => {
  if (props.stats.avg_confidence == null) return '-'
  return `${(props.stats.avg_confidence * 100).toFixed(0)}%`
})
</script>

<style scoped>
.stats-card {
  transition: all 0.2s ease;
}

.stats-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
</style>
