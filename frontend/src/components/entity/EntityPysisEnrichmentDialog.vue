<template>
  <div>
    <!-- Enrich from PySis Dialog -->
    <v-dialog v-model="showEnrichDialog" max-width="500">
      <v-card>
        <v-card-title>
          <v-icon start color="secondary">mdi-database-arrow-up</v-icon>
          {{ t('entityDetail.enrichFromPysisTitle') }}
        </v-card-title>
        <v-card-text>
          <v-alert type="info" variant="tonal" density="compact" class="mb-4">
            {{ t('entityDetail.enrichFromPysisDescription') }}
          </v-alert>
          <v-checkbox
            v-model="overwriteLocal"
            :label="t('entityDetail.enrichOverwrite')"
            density="compact"
            hide-details
            color="warning"
          ></v-checkbox>
          <v-alert v-if="overwriteLocal" type="warning" variant="tonal" density="compact" class="mt-3">
            {{ t('entityDetail.enrichOverwriteWarning') }}
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="closeDialog">{{ t('common.cancel') }}</v-btn>
          <v-btn variant="tonal" color="secondary" :loading="enriching" @click="startEnrichment">
            <v-icon start>mdi-database-arrow-up</v-icon>
            {{ t('entityDetail.startEnrichment') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Enrich Task Status Dialog -->
    <v-dialog v-model="showStatusDialog" max-width="500" persistent>
      <v-card>
        <v-card-title>
          <v-icon
            start
            :color="taskStatusColor"
          >
            {{ taskStatusIcon }}
          </v-icon>
          {{ taskStatusTitle }}
        </v-card-title>
        <v-card-text>
          <!-- Running state with progress -->
          <template v-if="taskStatus?.status === 'RUNNING'">
            <v-progress-linear
              :model-value="taskStatus.progress_percent"
              :indeterminate="taskStatus.progress_total === 0"
              color="primary"
              class="mb-3"
              rounded
            ></v-progress-linear>
            <p v-if="taskStatus.current_item" class="text-body-2 mb-1">
              {{ t('entityDetail.processing') }}: {{ taskStatus.current_item }}
            </p>
            <p v-if="taskStatus.progress_total > 0" class="text-caption text-medium-emphasis">
              {{ taskStatus.progress_current }} / {{ taskStatus.progress_total }}
            </p>
          </template>

          <!-- Completed state -->
          <template v-else-if="taskStatus?.status === 'COMPLETED'">
            <p class="text-success">
              {{ t('entityDetail.enrichSuccessMessage', { count: taskStatus.fields_extracted || 0 }) }}
            </p>
          </template>

          <!-- Failed state -->
          <template v-else-if="taskStatus?.status === 'FAILED'">
            <p class="text-error">
              {{ taskStatus.error_message || t('entityDetail.messages.enrichError') }}
            </p>
          </template>

          <!-- Initial state (waiting for first poll) -->
          <template v-else>
            <p>{{ t('entityDetail.enrichTaskStartedMessage') }}</p>
            <v-progress-linear indeterminate color="primary" class="mt-3"></v-progress-linear>
          </template>

          <p class="text-caption text-medium-emphasis mt-3">
            {{ t('entityDetail.taskId') }}: <code>{{ currentTaskId }}</code>
          </p>
        </v-card-text>
        <v-card-actions v-if="!taskStatus || ['COMPLETED', 'FAILED', 'CANCELLED'].includes(taskStatus.status)">
          <v-spacer></v-spacer>
          <v-btn variant="tonal" color="primary" @click="closeStatusDialog">
            {{ t('common.close') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { pysisApi, aiTasksApi } from '@/services/api'
import { useSnackbar } from '@/composables/useSnackbar'
import { useLogger } from '@/composables/useLogger'
import { getErrorMessage } from '@/composables/useApiErrorHandler'

const props = withDefaults(defineProps<Props>(), {
  overwrite: false,
})

const emit = defineEmits<{
  (e: 'update:showDialog', value: boolean): void
  (e: 'update:overwrite', value: boolean): void
  (e: 'enrichment-completed'): void
}>()

const logger = useLogger('EntityPysisEnrichmentDialog')

interface TaskStatus {
  status: string
  progress_current: number
  progress_total: number
  progress_percent: number
  current_item: string | null
  error_message: string | null
  fields_extracted: number
}

interface Props {
  entityId: string
  entityName: string
  showDialog: boolean
  overwrite?: boolean
}

const { t } = useI18n()
const { showSuccess, showError } = useSnackbar()

// Local state
const showEnrichDialog = computed({
  get: () => props.showDialog,
  set: (value) => emit('update:showDialog', value),
})

const overwriteLocal = computed({
  get: () => props.overwrite,
  set: (value) => emit('update:overwrite', value),
})

const showStatusDialog = ref(false)
const enriching = ref(false)
const currentTaskId = ref('')
const taskStatus = ref<TaskStatus | null>(null)
const taskPolling = ref<ReturnType<typeof setInterval> | null>(null)

// Computed
const taskStatusColor = computed(() => {
  if (!taskStatus.value) return 'primary'
  switch (taskStatus.value.status) {
    case 'COMPLETED': return 'success'
    case 'FAILED': return 'error'
    default: return 'primary'
  }
})

const taskStatusIcon = computed(() => {
  if (!taskStatus.value) return 'mdi-cog-sync'
  switch (taskStatus.value.status) {
    case 'COMPLETED': return 'mdi-check-circle'
    case 'FAILED': return 'mdi-alert-circle'
    default: return 'mdi-cog-sync'
  }
})

const taskStatusTitle = computed(() => {
  if (!taskStatus.value) return t('entityDetail.taskStarted')
  switch (taskStatus.value.status) {
    case 'COMPLETED': return t('entityDetail.enrichCompleted')
    case 'FAILED': return t('entityDetail.enrichFailed')
    case 'RUNNING': return t('entityDetail.enrichRunning')
    default: return t('entityDetail.taskStarted')
  }
})

// Methods
function closeDialog() {
  showEnrichDialog.value = false
}

function closeStatusDialog() {
  showStatusDialog.value = false
  taskStatus.value = null
  currentTaskId.value = ''
}

async function startEnrichment() {
  enriching.value = true
  try {
    const response = await pysisApi.enrichFacetsFromPysis({
      entity_id: props.entityId,
      overwrite: overwriteLocal.value,
    })

    if (response.data.success) {
      currentTaskId.value = response.data.task_id
      showEnrichDialog.value = false
      showStatusDialog.value = true
      startTaskPolling(response.data.task_id)
    } else {
      showError(response.data.message || t('entityDetail.messages.enrichError'))
    }
  } catch (e) {
    showError(getErrorMessage(e) || t('entityDetail.messages.enrichError'))
  } finally {
    enriching.value = false
  }
}

function startTaskPolling(taskId: string) {
  stopTaskPolling()

  taskPolling.value = setInterval(async () => {
    try {
      const response = await aiTasksApi.getStatus(taskId)
      taskStatus.value = response.data

      // Check if task is completed or failed
      if (['COMPLETED', 'FAILED', 'CANCELLED'].includes(response.data.status)) {
        stopTaskPolling()

        if (response.data.status === 'COMPLETED') {
          showSuccess(t('entityDetail.messages.enrichSuccess', {
            count: response.data.fields_extracted || 0
          }))
          emit('enrichment-completed')
        } else if (response.data.status === 'FAILED') {
          showError(response.data.error_message || t('entityDetail.messages.enrichError'))
        }

        // Close dialog after a short delay
        setTimeout(() => {
          closeStatusDialog()
        }, 2000)
      }
    } catch (e) {
      logger.error('Failed to poll task status', e)
    }
  }, 2000) // Poll every 2 seconds
}

function stopTaskPolling() {
  if (taskPolling.value) {
    clearInterval(taskPolling.value)
    taskPolling.value = null
  }
}

// Cleanup on unmount
onUnmounted(() => {
  stopTaskPolling()
})

// Watch for external dialog close
watch(showEnrichDialog, (newValue) => {
  if (!newValue) {
    overwriteLocal.value = false
  }
})
</script>
