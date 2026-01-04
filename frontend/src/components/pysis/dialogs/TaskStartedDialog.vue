<template>
  <v-dialog :model-value="modelValue" :max-width="DIALOG_SIZES.XS" @update:model-value="$emit('update:modelValue', $event)">
    <v-card>
      <v-card-title>
        <v-icon start color="success">mdi-check-circle</v-icon>
        {{ t('pysis.facets.taskStarted') }}
      </v-card-title>
      <v-card-text>
        <p>{{ message }}</p>
        <p class="text-caption text-medium-emphasis mt-2">
          {{ t('pysis.facets.taskId') }}: <code>{{ taskId }}</code>
        </p>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="tonal" color="primary" @click="$emit('update:modelValue', false)">{{ t('common.ok') }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { DIALOG_SIZES } from '@/config/ui'

defineProps<{
  modelValue: boolean
  message: string
  taskId: string
}>()

defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const { t } = useI18n()
</script>
