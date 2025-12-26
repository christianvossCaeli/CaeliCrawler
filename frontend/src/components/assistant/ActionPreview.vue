<template>
  <v-card
    variant="tonal"
    :color="cardColor"
    class="action-preview"
  >
    <v-card-title class="text-subtitle-1 d-flex align-center">
      <v-icon start size="small">{{ titleIcon }}</v-icon>
      {{ titleText }}
    </v-card-title>

    <v-card-text>
      <div class="text-body-2 mb-3">{{ message }}</div>

      <!-- Delete Operation Warning -->
      <v-alert
        v-if="isDeleteOperation"
        type="warning"
        density="compact"
        variant="tonal"
        class="mb-3"
      >
        <template #prepend>
          <v-icon>mdi-alert</v-icon>
        </template>
        {{ t('assistant.deleteWarning') }}
      </v-alert>

      <!-- UNDO Operation Info -->
      <v-alert
        v-if="isUndoOperation"
        type="info"
        density="compact"
        variant="tonal"
        class="mb-3"
      >
        <template #prepend>
          <v-icon>mdi-history</v-icon>
        </template>
        {{ t('assistant.undoInfo') }}
      </v-alert>

      <!-- Changes Preview (for Edit operations) -->
      <v-list
        v-if="action.changes && Object.keys(action.changes).length"
        density="compact"
        class="bg-transparent"
      >
        <v-list-item
          v-for="(change, field) in action.changes"
          :key="field"
          class="px-0"
        >
          <template #prepend>
            <v-icon size="small" :color="changeIconColor">{{ changeIcon }}</v-icon>
          </template>
          <v-list-item-title class="text-body-2">
            <strong>{{ field }}:</strong>
          </v-list-item-title>
          <v-list-item-subtitle>
            <span class="text-decoration-line-through text-medium-emphasis">
              {{ change.from || t('assistant.empty') }}
            </span>
            <v-icon size="x-small" class="mx-1">mdi-arrow-right</v-icon>
            <span :class="isDeleteOperation ? 'text-error' : 'text-success'">
              {{ change.to || t('assistant.empty') }}
            </span>
          </v-list-item-subtitle>
        </v-list-item>
      </v-list>

      <!-- Delete Target Preview -->
      <div v-if="isDeleteOperation && action.delete_target" class="delete-preview">
        <div class="delete-preview__label">{{ t('assistant.deleteTarget') }}:</div>
        <v-chip
          color="error"
          variant="outlined"
          size="small"
          class="mt-1"
        >
          <v-icon start size="small">mdi-delete</v-icon>
          {{ action.delete_target }}
        </v-chip>
        <div v-if="action.delete_count" class="delete-preview__count mt-2">
          {{ t('assistant.deleteCount', { count: action.delete_count }) }}
        </div>
      </div>

      <!-- UNDO Preview -->
      <div v-if="isUndoOperation && action.undo_details" class="undo-preview">
        <div class="undo-preview__label">{{ t('assistant.undoTarget') }}:</div>
        <div class="undo-preview__details mt-1">
          <v-chip size="small" variant="tonal" color="info" class="mr-1">
            {{ action.undo_details.operation }}
          </v-chip>
          <span class="text-body-2">
            {{ action.undo_details.description }}
          </span>
        </div>
      </div>

      <!-- Target Entity -->
      <v-chip
        v-if="action.target_name && !isDeleteOperation"
        size="small"
        variant="outlined"
        class="mt-2"
      >
        <v-icon start size="small">mdi-target</v-icon>
        {{ action.target_name }}
      </v-chip>
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn
        variant="tonal"
        size="small"
        :disabled="loading"
        @click="$emit('cancel')"
      >
        {{ t('assistant.cancel') }}
      </v-btn>
      <v-btn
        :color="confirmButtonColor"
        variant="elevated"
        size="small"
        :loading="loading"
        @click="$emit('confirm')"
      >
        <v-icon start size="small">{{ confirmButtonIcon }}</v-icon>
        {{ confirmButtonText }}
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{
  message: string
  action: {
    type: string
    target_id?: string
    target_name?: string
    target_type?: string
    changes?: Record<string, { from: unknown; to: unknown }>
    // Delete-specific fields
    delete_target?: string
    delete_count?: number
    // UNDO-specific fields
    undo_details?: {
      operation: string
      description: string
    }
  }
  loading?: boolean
}>()

defineEmits<{
  confirm: []
  cancel: []
}>()

const { t } = useI18n()

// Computed properties for different operation types
const isDeleteOperation = computed(() =>
  ['delete_entity', 'delete_facet', 'batch_delete'].includes(props.action.type)
)

const isUndoOperation = computed(() =>
  props.action.type === 'undo_change'
)

const cardColor = computed(() => {
  if (isDeleteOperation.value) return 'error'
  if (isUndoOperation.value) return 'info'
  return 'warning'
})

const titleIcon = computed(() => {
  if (isDeleteOperation.value) return 'mdi-delete-alert'
  if (isUndoOperation.value) return 'mdi-undo'
  return 'mdi-alert-circle-outline'
})

const titleText = computed(() => {
  if (isDeleteOperation.value) return t('assistant.deleteConfirmTitle')
  if (isUndoOperation.value) return t('assistant.undoConfirmTitle')
  return t('assistant.confirmRequired')
})

const changeIcon = computed(() => {
  if (isDeleteOperation.value) return 'mdi-minus-circle'
  if (isUndoOperation.value) return 'mdi-undo-variant'
  return 'mdi-pencil'
})

const changeIconColor = computed(() => {
  if (isDeleteOperation.value) return 'error'
  if (isUndoOperation.value) return 'info'
  return 'warning'
})

const confirmButtonColor = computed(() => {
  if (isDeleteOperation.value) return 'error'
  if (isUndoOperation.value) return 'info'
  return 'success'
})

const confirmButtonIcon = computed(() => {
  if (isDeleteOperation.value) return 'mdi-delete'
  if (isUndoOperation.value) return 'mdi-undo'
  return 'mdi-check'
})

const confirmButtonText = computed(() => {
  if (isDeleteOperation.value) return t('assistant.deleteConfirm')
  if (isUndoOperation.value) return t('assistant.undoConfirm')
  return t('assistant.confirm')
})
</script>

<style scoped>
.action-preview {
  margin: 8px 0;
}

.delete-preview,
.undo-preview {
  padding: 8px 12px;
  background: rgba(var(--v-theme-surface-variant), 0.5);
  border-radius: 8px;
  margin-top: 8px;
}

.delete-preview__label,
.undo-preview__label {
  font-size: 0.75rem;
  font-weight: 500;
  color: rgba(var(--v-theme-on-surface), 0.7);
}

.delete-preview__count {
  font-size: 0.8rem;
  color: rgb(var(--v-theme-error));
  font-weight: 500;
}

.undo-preview__details {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}
</style>
