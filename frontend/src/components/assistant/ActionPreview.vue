<template>
  <v-card variant="tonal" color="warning" class="action-preview">
    <v-card-title class="text-subtitle-1 d-flex align-center">
      <v-icon start size="small">mdi-alert-circle-outline</v-icon>
      {{ t('assistant.confirmRequired') }}
    </v-card-title>

    <v-card-text>
      <div class="text-body-2 mb-3">{{ message }}</div>

      <!-- Changes Preview -->
      <v-list v-if="action.changes && Object.keys(action.changes).length" density="compact" class="bg-transparent">
        <v-list-item
          v-for="(change, field) in action.changes"
          :key="field"
          class="px-0"
        >
          <template v-slot:prepend>
            <v-icon size="small" color="warning">mdi-pencil</v-icon>
          </template>
          <v-list-item-title class="text-body-2">
            <strong>{{ field }}:</strong>
          </v-list-item-title>
          <v-list-item-subtitle>
            <span class="text-decoration-line-through text-medium-emphasis">{{ change.from || t('assistant.empty') }}</span>
            <v-icon size="x-small" class="mx-1">mdi-arrow-right</v-icon>
            <span class="text-success">{{ change.to }}</span>
          </v-list-item-subtitle>
        </v-list-item>
      </v-list>

      <!-- Target Entity -->
      <v-chip
        v-if="action.target_name"
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
        variant="text"
        size="small"
        :disabled="loading"
        @click="$emit('cancel')"
      >
        {{ t('assistant.cancel') }}
      </v-btn>
      <v-btn
        color="success"
        variant="elevated"
        size="small"
        :loading="loading"
        @click="$emit('confirm')"
      >
        <v-icon start size="small">mdi-check</v-icon>
        {{ t('assistant.confirm') }}
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

defineProps<{
  message: string
  action: {
    type: string
    target_id?: string
    target_name?: string
    target_type?: string
    changes?: Record<string, { from: any; to: any }>
  }
  loading?: boolean
}>()

defineEmits<{
  confirm: []
  cancel: []
}>()
</script>

<style scoped>
.action-preview {
  margin: 8px 0;
}
</style>
