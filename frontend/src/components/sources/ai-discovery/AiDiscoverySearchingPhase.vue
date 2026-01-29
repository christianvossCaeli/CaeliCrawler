<template>
  <v-card variant="outlined" class="pa-6 text-center">
    <v-progress-circular
      indeterminate
      color="primary"
      size="64"
      class="mb-4"
    ></v-progress-circular>
    <div class="text-h6 mb-2">{{ $t('sources.aiDiscovery.searching') }}</div>
    <v-list density="compact" class="text-left mx-auto" style="max-width: 400px">
      <v-list-item v-for="(step, index) in steps" :key="index">
        <template #prepend>
          <v-icon
            :color="step.done ? 'success' : (step.active ? 'primary' : 'grey')"
            size="small"
            :class="{ 'icon-spin': step.active && !step.done }"
          >
            {{ step.done ? 'mdi-check-circle' : (step.active ? 'mdi-loading' : 'mdi-circle-outline') }}
          </v-icon>
        </template>
        <v-list-item-title :class="{ 'text-grey': !step.active && !step.done }">
          {{ step.text }}
        </v-list-item-title>
      </v-list-item>
    </v-list>
  </v-card>
</template>

<script setup lang="ts">
/**
 * AiDiscoverySearchingPhase - Progress indicator for AI discovery search
 *
 * Shows animated steps during the search process with status indicators.
 */

export interface SearchStep {
  text: string
  active: boolean
  done: boolean
}

interface Props {
  steps: SearchStep[]
}

defineProps<Props>()
</script>

<style scoped>
.icon-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
