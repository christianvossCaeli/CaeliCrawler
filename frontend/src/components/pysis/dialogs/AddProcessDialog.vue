<template>
  <v-dialog :model-value="modelValue" max-width="500" @update:model-value="$emit('update:modelValue', $event)">
    <v-card>
      <v-card-title>{{ t('pysis.addProcess') }}</v-card-title>
      <v-card-text class="pt-4">
        <v-text-field
          v-model="form.pysis_process_id"
          :label="t('pysis.processId')"
          :placeholder="t('pysis.processIdPlaceholder')"
          :hint="t('pysis.processIdHint')"
          persistent-hint
          class="mb-3"
        ></v-text-field>
        <v-text-field
          v-model="form.name"
          :label="t('pysis.displayName')"
          :placeholder="t('pysis.displayNamePlaceholder')"
        ></v-text-field>
        <v-select
          v-if="showTemplates"
          v-model="form.template_id"
          :items="templates"
          item-title="name"
          item-value="id"
          :label="t('pysis.applyTemplate')"
          clearable
          class="mt-3"
        ></v-select>
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

interface Template {
  id: string
  name?: string
  description?: string
}

interface ProcessForm {
  pysis_process_id: string
  name: string
  template_id: string | null
}

const props = defineProps<{
  modelValue: boolean
  loading?: boolean
  showTemplates?: boolean
  templates?: Template[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  submit: [form: ProcessForm]
}>()

const { t } = useI18n()

const form = ref<ProcessForm>({
  pysis_process_id: '',
  name: '',
  template_id: null,
})

// Reset form when dialog opens
watch(() => props.modelValue, (isOpen) => {
  if (isOpen) {
    form.value = { pysis_process_id: '', name: '', template_id: null }
  }
})

function handleSubmit() {
  emit('submit', { ...form.value })
}
</script>
