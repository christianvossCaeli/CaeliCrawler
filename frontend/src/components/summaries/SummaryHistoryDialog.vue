<template>
  <v-dialog
    v-model="modelValue"
    max-width="700"
    role="dialog"
    aria-modal="true"
    :aria-labelledby="dialogTitleId"
  >
    <v-card>
      <v-card-title :id="dialogTitleId">
        <v-icon color="primary" class="mr-2">mdi-history</v-icon>
        {{ t('summaries.executionHistory') }}
      </v-card-title>

      <v-card-text>
        <!-- Loading -->
        <div v-if="isLoading" class="d-flex justify-center py-8">
          <v-progress-circular indeterminate color="primary" />
        </div>

        <!-- Empty State -->
        <div v-else-if="executions.length === 0" class="text-center py-8">
          <v-icon size="64" color="grey-lighten-1">mdi-history</v-icon>
          <p class="text-body-1 text-medium-emphasis mt-4">
            {{ t('summaries.noExecutions') }}
          </p>
        </div>

        <!-- Executions List -->
        <v-timeline v-else density="compact" side="end">
          <v-timeline-item
            v-for="exec in executions"
            :key="exec.id"
            :dot-color="getStatusColor(exec.status)"
            size="small"
          >
            <template #opposite>
              <span class="text-caption text-medium-emphasis">
                {{ formatDateTime(exec.created_at) }}
              </span>
            </template>

            <v-card variant="outlined" class="mb-2">
              <v-card-text class="py-2">
                <div class="d-flex align-center mb-1">
                  <v-chip
                    :color="getStatusColor(exec.status)"
                    size="x-small"
                    variant="tonal"
                    class="mr-2"
                  >
                    {{ exec.status }}
                  </v-chip>
                  <span class="text-body-2">
                    {{ t(`summaries.triggeredBy_${exec.triggered_by}`) }}
                  </span>
                  <v-spacer />
                  <span v-if="exec.duration_ms" class="text-caption text-medium-emphasis">
                    {{ exec.duration_ms }}ms
                  </span>
                </div>

                <div v-if="exec.has_changes" class="d-flex align-center text-success text-body-2">
                  <v-icon size="small" class="mr-1">mdi-check-circle</v-icon>
                  {{ t('summaries.hasChanges') }}
                </div>

                <div v-if="exec.relevance_reason" class="text-caption text-medium-emphasis mt-1">
                  {{ exec.relevance_reason }}
                </div>

                <div v-if="exec.error_message" class="text-caption text-error mt-1">
                  {{ exec.error_message }}
                </div>
              </v-card-text>
            </v-card>
          </v-timeline-item>
        </v-timeline>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-btn variant="text" @click="close">
          {{ t('common.close') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCustomSummariesStore, type SummaryExecution } from '@/stores/customSummaries'
import { useDialogFocus, useStatusColors } from '@/composables'

const { t } = useI18n()
const store = useCustomSummariesStore()

// ARIA
const dialogTitleId = `summary-history-dialog-title-${Math.random().toString(36).slice(2, 9)}`

const modelValue = defineModel<boolean>()

const props = defineProps<{
  summaryId: string
}>()

const emit = defineEmits<{}>()

// Focus management for accessibility
useDialogFocus({ isOpen: modelValue })

// Use centralized status colors
const { getStatusColor } = useStatusColors()

const executions = ref<SummaryExecution[]>([])
const isLoading = ref(false)

async function loadExecutions() {
  isLoading.value = true
  try {
    executions.value = await store.listExecutions(props.summaryId, 20)
  } finally {
    isLoading.value = false
  }
}

function formatDateTime(dateStr: string): string {
  // Use browser locale for consistent date formatting
  return new Date(dateStr).toLocaleString(undefined, {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function close() {
  modelValue.value = false
}

// Load executions when dialog opens
watch(modelValue, (isOpen) => {
  if (isOpen) {
    loadExecutions()
  }
})
</script>
