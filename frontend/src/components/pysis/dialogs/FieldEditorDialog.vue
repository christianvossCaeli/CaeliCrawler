<template>
  <v-dialog :model-value="modelValue" max-width="700" @update:model-value="$emit('update:modelValue', $event)">
    <v-card v-if="field">
      <v-card-title>
        {{ field.internal_name }}
        <v-chip v-if="field.value_source" size="small" class="ml-2" :color="getSourceColor(field.value_source)">
          {{ field.value_source }}
        </v-chip>
      </v-card-title>
      <v-card-subtitle>
        <code>{{ field.pysis_field_name }}</code>
      </v-card-subtitle>
      <v-card-text>
        <v-textarea
          v-model="currentValue"
          :label="t('common.value')"
          variant="outlined"
          rows="10"
          auto-grow
        ></v-textarea>
        <v-alert
          v-if="field.ai_extracted_value && field.ai_extracted_value !== currentValue"
          type="info"
          density="compact"
          class="mt-3"
        >
          <strong>{{ t('pysis.aiSuggestion') }}:</strong>
          <div class="text-body-2 mt-1">{{ field.ai_extracted_value }}</div>
          <v-btn size="small" class="mt-2" @click="useAiValue">{{ t('pysis.useAiValue') }}</v-btn>
        </v-alert>
      </v-card-text>
      <v-card-actions>
        <v-btn variant="tonal" @click="$emit('update:modelValue', false)">{{ t('common.cancel') }}</v-btn>
        <v-spacer></v-spacer>
        <v-btn variant="tonal" color="primary" @click="handleSave">{{ t('common.save') }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

interface Field {
  id: string
  internal_name: string
  pysis_field_name: string
  current_value?: string
  ai_extracted_value?: string
  value_source?: string
}

const props = defineProps<{
  modelValue: boolean
  field: Field | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  save: [value: string]
}>()

const { t } = useI18n()

const currentValue = ref('')

watch(() => props.field, (newField) => {
  if (newField) {
    currentValue.value = newField.current_value || ''
  }
}, { immediate: true })

function getSourceColor(source: string): string {
  const colors: Record<string, string> = {
    pysis: 'info',
    manual: 'success',
    ai: 'secondary',
    restored: 'warning',
  }
  return colors[source] || 'grey'
}

function useAiValue() {
  if (props.field?.ai_extracted_value) {
    currentValue.value = props.field.ai_extracted_value
  }
}

function handleSave() {
  emit('save', currentValue.value)
}
</script>
