<template>
  <v-card class="generation-card">
    <v-card-text class="pa-6">
      <div class="d-flex align-center mb-6">
        <v-avatar color="warning" size="48" class="mr-4">
          <v-icon size="24" class="generation-icon">mdi-robot</v-icon>
        </v-avatar>
        <div>
          <div class="text-h6">{{ t('smartQueryView.generation.running') }}</div>
          <div class="text-body-2 text-medium-emphasis">{{ t('smartQueryView.generation.processing') }}</div>
        </div>
      </div>

      <!-- Timeline Steps -->
      <v-timeline density="compact" side="end" class="generation-timeline">
        <v-timeline-item
          v-for="step in steps"
          :key="step.value"
          :dot-color="getStepColor(step.value)"
          size="small"
        >
          <template #icon>
            <v-icon v-if="currentStep > step.value" size="16" color="white">mdi-check</v-icon>
            <v-progress-circular
              v-else-if="currentStep === step.value"
              indeterminate
              size="16"
              width="2"
              color="white"
            />
          </template>
          <div class="d-flex align-center">
            <div>
              <div class="text-body-2 font-weight-medium" :class="{ 'text-medium-emphasis': currentStep < step.value }">
                {{ step.title }}
              </div>
              <div class="text-caption text-medium-emphasis">{{ step.subtitle }}</div>
            </div>
          </div>
        </v-timeline-item>
      </v-timeline>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

interface Step {
  value: number
  title: string
  subtitle: string
}

const props = withDefaults(defineProps<{
  currentStep?: number
}>(), {
  currentStep: 1
})

const { t } = useI18n()

const steps = computed<Step[]>(() => [
  {
    value: 1,
    title: t('smartQueryView.generation.stepperTitles.entityType'),
    subtitle: t('smartQueryView.generation.stepperSubtitles.entityType')
  },
  {
    value: 2,
    title: t('smartQueryView.generation.stepperTitles.category'),
    subtitle: t('smartQueryView.generation.stepperSubtitles.category')
  },
  {
    value: 3,
    title: t('smartQueryView.generation.stepperTitles.crawlConfig'),
    subtitle: t('smartQueryView.generation.stepperSubtitles.crawlConfig')
  }
])

function getStepColor(stepValue: number): string {
  if (props.currentStep > stepValue) return 'success'
  if (props.currentStep === stepValue) return 'warning'
  return 'grey'
}
</script>

<style scoped>
.generation-card {
  border-radius: 16px !important;
  border-left: 4px solid rgb(var(--v-theme-warning));
}

.generation-icon {
  animation: rotate 2s linear infinite;
}

.generation-timeline {
  margin-left: 8px;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
