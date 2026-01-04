<template>
  <v-dialog :model-value="modelValue" :max-width="DIALOG_SIZES.MD" @update:model-value="$emit('update:modelValue', $event)">
    <v-card v-if="settings">
      <v-card-title>
        <v-icon start>mdi-cog</v-icon>
        {{ t('pysis.fieldSettings') }}: {{ settings.internal_name }}
      </v-card-title>
      <v-card-text class="pt-4">
        <v-text-field
          v-model="localSettings.internal_name"
          :label="t('pysis.internalName')"
          variant="outlined"
          density="compact"
          class="mb-3"
        ></v-text-field>
        <v-select
          v-model="localSettings.field_type"
          :items="fieldTypes"
          item-title="title"
          item-value="value"
          :label="t('pysis.fieldType')"
          variant="outlined"
          density="compact"
          class="mb-3"
        ></v-select>
        <v-switch
          v-model="localSettings.ai_extraction_enabled"
          :label="t('pysis.aiExtractionEnabled')"
          color="primary"
          class="mb-3"
        ></v-switch>
        <v-textarea
          v-model="localSettings.ai_extraction_prompt"
          :label="t('pysis.aiPrompt')"
          variant="outlined"
          rows="6"
          :placeholder="t('pysis.defaultPromptPlaceholder', { name: localSettings.internal_name })"
          :hint="t('pysis.aiPromptHint')"
          persistent-hint
        ></v-textarea>
        <v-alert v-if="!localSettings.ai_extraction_prompt" type="warning" variant="tonal" density="compact" class="mt-3">
          {{ t('pysis.noPromptWarning', { name: localSettings.internal_name }) }}
        </v-alert>
      </v-card-text>
      <v-card-actions>
        <v-btn variant="tonal" @click="$emit('update:modelValue', false)">{{ t('common.cancel') }}</v-btn>
        <v-spacer></v-spacer>
        <v-btn variant="tonal" color="primary" :loading="loading" @click="handleSave">{{ t('common.save') }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { DIALOG_SIZES } from '@/config/ui'

interface FieldSettings {
  id: string
  internal_name: string
  field_type: string
  ai_extraction_enabled?: boolean
  ai_extraction_prompt?: string
}

interface FieldTypeOption {
  title: string
  value: string
}

const props = defineProps<{
  modelValue: boolean
  settings: FieldSettings | null
  fieldTypes: FieldTypeOption[]
  loading?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  save: [settings: FieldSettings]
}>()

const { t } = useI18n()

const localSettings = ref<FieldSettings>({
  id: '',
  internal_name: '',
  field_type: 'text',
  ai_extraction_enabled: true,
  ai_extraction_prompt: '',
})

watch(() => props.settings, (newSettings) => {
  if (newSettings) {
    localSettings.value = { ...newSettings }
  }
}, { immediate: true })

function handleSave() {
  emit('save', { ...localSettings.value })
}
</script>
