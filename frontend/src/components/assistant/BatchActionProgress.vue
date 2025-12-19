<template>
  <v-card class="batch-progress" :class="{ 'batch-progress--completed': isCompleted }">
    <v-card-title class="d-flex align-center">
      <v-icon start :color="statusColor">{{ statusIcon }}</v-icon>
      {{ t('assistant.batchTitle') }}
      <v-spacer />
      <v-chip size="small" :color="statusColor" variant="tonal">
        {{ statusLabel }}
      </v-chip>
    </v-card-title>

    <v-card-text>
      <!-- Progress info -->
      <div class="mb-3 d-flex justify-space-between align-center">
        <span class="text-body-2">
          {{ status.processed }} / {{ status.total }} {{ t('assistant.batchProcessed') }}
        </span>
        <span class="text-caption text-medium-emphasis">
          {{ progressPercent }}%
        </span>
      </div>

      <!-- Progress bar -->
      <v-progress-linear
        :model-value="progressPercent"
        :color="hasErrors ? 'warning' : statusColor"
        height="10"
        rounded
        class="mb-3"
      />

      <!-- Preview of affected entities -->
      <div v-if="preview.length > 0 && !isRunning" class="mb-3">
        <div class="text-caption text-medium-emphasis mb-1">
          {{ t('assistant.batchPreviewLabel') }}
        </div>
        <div class="batch-progress__preview">
          <v-chip
            v-for="entity in preview.slice(0, 5)"
            :key="entity.entity_id"
            size="small"
            variant="outlined"
            class="mr-1 mb-1"
          >
            {{ entity.entity_name }}
          </v-chip>
          <v-chip
            v-if="preview.length > 5"
            size="small"
            variant="text"
            class="mb-1"
          >
            +{{ preview.length - 5 }} {{ t('assistant.batchMore') }}
          </v-chip>
        </div>
      </div>

      <!-- Errors -->
      <v-expand-transition>
        <div v-if="hasErrors" class="batch-progress__errors">
          <v-alert
            type="warning"
            density="compact"
            variant="tonal"
            class="mb-2"
          >
            {{ status.errors.length }} {{ t('assistant.batchErrors') }}
          </v-alert>
          <v-list
            v-if="showErrors"
            density="compact"
            class="batch-progress__error-list"
          >
            <v-list-item
              v-for="(err, idx) in status.errors.slice(0, 5)"
              :key="idx"
              class="text-caption"
            >
              <template v-slot:prepend>
                <v-icon size="small" color="error">mdi-alert-circle</v-icon>
              </template>
              {{ err.entity_name }}: {{ err.error }}
            </v-list-item>
          </v-list>
          <v-btn
            v-if="status.errors.length > 0"
            variant="text"
            size="small"
            @click="showErrors = !showErrors"
          >
            {{ showErrors ? t('assistant.batchHideErrors') : t('assistant.batchShowErrors') }}
          </v-btn>
        </div>
      </v-expand-transition>

      <!-- Message -->
      <div v-if="status.message" class="text-body-2 text-medium-emphasis mt-2">
        {{ status.message }}
      </div>
    </v-card-text>

    <v-card-actions>
      <!-- Cancel button for running operations -->
      <v-btn
        v-if="isRunning"
        variant="outlined"
        color="error"
        size="small"
        :loading="isCancelling"
        @click="$emit('cancel')"
      >
        <v-icon start>mdi-stop</v-icon>
        {{ t('assistant.batchCancel') }}
      </v-btn>

      <!-- Close button for completed operations -->
      <v-btn
        v-if="isCompleted"
        variant="text"
        size="small"
        @click="$emit('close')"
      >
        {{ t('assistant.batchClose') }}
      </v-btn>

      <v-spacer />

      <!-- Confirm button for dry run preview -->
      <template v-if="isDryRun">
        <v-btn
          variant="outlined"
          size="small"
          @click="$emit('cancel')"
        >
          {{ t('assistant.cancel') }}
        </v-btn>
        <v-btn
          color="primary"
          size="small"
          :disabled="status.total === 0"
          @click="$emit('confirm')"
        >
          <v-icon start>mdi-play</v-icon>
          {{ t('assistant.batchExecute', { count: status.total }) }}
        </v-btn>
      </template>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

export interface BatchStatus {
  batch_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  processed: number
  total: number
  errors: Array<{ entity_id?: string; entity_name?: string; error: string }>
  message: string
}

export interface BatchPreviewEntity {
  entity_id: string
  entity_name: string
  entity_type: string
}

const props = defineProps<{
  status: BatchStatus
  preview?: BatchPreviewEntity[]
  isDryRun?: boolean
  isCancelling?: boolean
}>()

defineEmits<{
  cancel: []
  close: []
  confirm: []
}>()

const showErrors = ref(false)

const progressPercent = computed(() => {
  if (props.status.total === 0) return 0
  return Math.round((props.status.processed / props.status.total) * 100)
})

const hasErrors = computed(() => props.status.errors.length > 0)

const isRunning = computed(() => props.status.status === 'running')
const isCompleted = computed(() => ['completed', 'failed', 'cancelled'].includes(props.status.status))

const statusColor = computed(() => {
  switch (props.status.status) {
    case 'completed':
      return hasErrors.value ? 'warning' : 'success'
    case 'failed':
      return 'error'
    case 'cancelled':
      return 'grey'
    case 'running':
      return 'primary'
    default:
      return 'grey'
  }
})

const statusIcon = computed(() => {
  switch (props.status.status) {
    case 'completed':
      return hasErrors.value ? 'mdi-alert' : 'mdi-check-circle'
    case 'failed':
      return 'mdi-alert-circle'
    case 'cancelled':
      return 'mdi-stop-circle'
    case 'running':
      return 'mdi-cog-sync'
    default:
      return 'mdi-clock-outline'
  }
})

const statusLabel = computed(() => {
  switch (props.status.status) {
    case 'completed':
      return t('assistant.batchStatusCompleted')
    case 'failed':
      return t('assistant.batchStatusFailed')
    case 'cancelled':
      return t('assistant.batchStatusCancelled')
    case 'running':
      return t('assistant.batchStatusRunning')
    default:
      return t('assistant.batchStatusPending')
  }
})
</script>

<style scoped>
.batch-progress {
  margin: 8px 0;
  border: 1px solid rgb(var(--v-theme-outline-variant));
}

.batch-progress--completed {
  border-color: rgb(var(--v-theme-success));
}

.batch-progress__preview {
  display: flex;
  flex-wrap: wrap;
}

.batch-progress__errors {
  margin-top: 12px;
}

.batch-progress__error-list {
  max-height: 150px;
  overflow-y: auto;
  background: rgb(var(--v-theme-surface-variant));
  border-radius: 4px;
}
</style>
