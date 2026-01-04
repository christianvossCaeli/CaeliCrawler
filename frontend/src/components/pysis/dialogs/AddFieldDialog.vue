<template>
  <v-dialog :model-value="modelValue" max-width="500" @update:model-value="$emit('update:modelValue', $event)">
    <v-card>
      <v-card-title>{{ t('pysis.addField') }}</v-card-title>
      <v-card-text class="pt-4">
        <v-text-field
          v-model="form.internal_name"
          :label="t('pysis.internalName')"
          :placeholder="t('pysis.internalNamePlaceholder')"
          class="mb-3"
        ></v-text-field>
        <v-text-field
          v-model="form.pysis_field_name"
          :label="t('pysis.pysisFieldName')"
          :placeholder="t('pysis.pysisFieldNamePlaceholder')"
          :hint="t('pysis.pysisFieldNameHint')"
          persistent-hint
          class="mb-3"
        ></v-text-field>
        <v-select
          v-model="form.field_type"
          :items="fieldTypes"
          item-title="title"
          item-value="value"
          :label="t('pysis.fieldType')"
          class="mb-3"
        ></v-select>
        <v-switch
          v-model="form.ai_extraction_enabled"
          :label="t('pysis.aiExtractionEnabled')"
          color="primary"
        ></v-switch>
        <v-textarea
          v-if="form.ai_extraction_enabled"
          v-model="form.ai_extraction_prompt"
          :label="t('pysis.aiPrompt')"
          :placeholder="t('pysis.aiPromptPlaceholder')"
          rows="3"
        ></v-textarea>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="tonal" @click="$emit('update:modelValue', false)">{{ t('common.cancel') }}</v-btn>
        <v-btn variant="tonal" color="primary" :loading="loading" @click="handleSubmit">{{ t('common.add') }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

interface FieldForm {
  internal_name: string
  pysis_field_name: string
  field_type: string
  ai_extraction_enabled: boolean
  ai_extraction_prompt: string
}

interface FieldTypeOption {
  title: string
  value: string
}

const props = defineProps<{
  modelValue: boolean
  loading?: boolean
  fieldTypes: FieldTypeOption[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  submit: [form: FieldForm]
}>()

const { t } = useI18n()

const defaultForm = (): FieldForm => ({
  internal_name: '',
  pysis_field_name: '',
  field_type: 'text',
  ai_extraction_enabled: true,
  ai_extraction_prompt: '',
})

const form = ref<FieldForm>(defaultForm())

watch(() => props.modelValue, (isOpen) => {
  if (isOpen) {
    form.value = defaultForm()
  }
})

function handleSubmit() {
  emit('submit', { ...form.value })
}
</script>
