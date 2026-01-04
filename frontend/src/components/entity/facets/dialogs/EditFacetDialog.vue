<template>
  <v-dialog :model-value="modelValue" :max-width="DIALOG_SIZES.LG" scrollable @update:model-value="$emit('update:modelValue', $event)">
    <v-card min-height="400">
      <v-card-title class="d-flex align-center">
        <v-icon start>mdi-pencil</v-icon>
        {{ t('entityDetail.dialog.editFacet') }}
        <span v-if="facetTypeName" class="text-body-2 text-medium-emphasis ml-2">
          ({{ facetTypeName }})
        </span>
      </v-card-title>
      <v-card-text>
        <DynamicSchemaForm
          v-if="schema"
          :model-value="value"
          :schema="schema"
          @update:model-value="$emit('update:value', $event)"
        />
        <v-textarea
          v-else
          :model-value="textValue"
          :label="t('entityDetail.dialog.facetValue')"
          rows="8"
          variant="outlined"
          auto-grow
          :hint="t('entityDetail.dialog.facetValueHint')"
          persistent-hint
          @update:model-value="$emit('update:textValue', $event)"
        ></v-textarea>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="tonal" @click="$emit('update:modelValue', false)">{{ t('common.cancel') }}</v-btn>
        <v-btn color="primary" variant="tonal" :loading="saving" @click="$emit('save')">{{ t('common.save') }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { DIALOG_SIZES } from '@/config/ui'
import DynamicSchemaForm from '@/components/DynamicSchemaForm.vue'
import type { FacetSchema } from '@/composables/facets'

defineProps<{
  modelValue: boolean
  value: Record<string, unknown>
  textValue: string
  schema: FacetSchema | null
  facetTypeName: string
  saving: boolean
}>()

defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'update:value', value: Record<string, unknown>): void
  (e: 'update:textValue', value: string): void
  (e: 'save'): void
}>()

const { t } = useI18n()
</script>
