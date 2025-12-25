<template>
  <v-dialog v-model="modelValue" max-width="500">
    <v-card>
      <v-card-title>{{ t('categories.dialog.reanalyze') }}</v-card-title>
      <v-card-text>
        <p class="mb-4">
          {{ t('categories.dialog.reanalyzeConfirm', { name: categoryName }) }}
        </p>
        <v-switch
          :model-value="reanalyzeAll"
          @update:model-value="handleReanalyzeAllChange"
          :label="t('categories.dialog.reanalyzeAll')"
          color="warning"
        ></v-switch>
        <v-alert type="info" variant="tonal" class="mt-2">
          {{ reanalyzeAll ? t('categories.dialog.reanalyzeAllDocs') : t('categories.dialog.reanalyzeOnlyLow') }} {{ t('categories.dialog.reanalyzeInfo') }}
        </v-alert>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="tonal" @click="modelValue = false">{{ t('common.cancel') }}</v-btn>
        <v-btn variant="tonal" color="warning" @click="$emit('confirm')">{{ t('categories.actions.reanalyze') }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const modelValue = defineModel<boolean>()

// Props
defineProps<{
  categoryName: string
  reanalyzeAll: boolean
}>()

// Emits
const emit = defineEmits<{
  'update:reanalyzeAll': [value: boolean]
  'confirm': []
}>()

const { t } = useI18n()

// Methods
const handleReanalyzeAllChange = (value: boolean | null) => {
  emit('update:reanalyzeAll', value ?? false)
}
</script>
