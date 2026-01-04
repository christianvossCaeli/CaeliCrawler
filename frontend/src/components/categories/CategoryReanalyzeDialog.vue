<template>
  <v-dialog
    v-model="modelValue"
    :max-width="DIALOG_SIZES.SM"
    role="alertdialog"
    :aria-labelledby="titleId"
    :aria-describedby="descriptionId"
  >
    <v-card>
      <v-card-title :id="titleId">{{ t('categories.dialog.reanalyze') }}</v-card-title>
      <v-card-text>
        <p :id="descriptionId" class="mb-4">
          {{ t('categories.dialog.reanalyzeConfirm', { name: categoryName }) }}
        </p>
        <v-switch
          :model-value="reanalyzeAll"
          :label="t('categories.dialog.reanalyzeAll')"
          color="warning"
          :aria-describedby="infoId"
          @update:model-value="handleReanalyzeAllChange"
        ></v-switch>
        <v-alert :id="infoId" type="info" variant="tonal" class="mt-2" role="status">
          {{ reanalyzeAll ? t('categories.dialog.reanalyzeAllDocs') : t('categories.dialog.reanalyzeOnlyLow') }} {{ t('categories.dialog.reanalyzeInfo') }}
        </v-alert>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn
          variant="tonal"
          :aria-label="t('common.cancel')"
          @click="modelValue = false"
        >
          {{ t('common.cancel') }}
        </v-btn>
        <v-btn
          variant="tonal"
          color="warning"
          :aria-label="t('categories.actions.reanalyze') + ' ' + categoryName"
          @click="$emit('confirm')"
        >
          {{ t('categories.actions.reanalyze') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { DIALOG_SIZES } from '@/config/ui'
import { generateAriaId } from '@/utils/dialogAccessibility'

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
// Accessibility IDs
const titleId = generateAriaId('reanalyze-dialog-title')
const descriptionId = generateAriaId('reanalyze-dialog-desc')
const infoId = generateAriaId('reanalyze-info')

const { t } = useI18n()

// Methods
const handleReanalyzeAllChange = (value: boolean | null) => {
  emit('update:reanalyzeAll', value ?? false)
}
</script>
