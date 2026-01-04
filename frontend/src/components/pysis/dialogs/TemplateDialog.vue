<template>
  <v-dialog :model-value="modelValue" :max-width="DIALOG_SIZES.SM" @update:model-value="$emit('update:modelValue', $event)">
    <v-card>
      <v-card-title>{{ t('pysis.template') }}</v-card-title>
      <v-card-text class="pt-4">
        <v-select
          v-model="selectedTemplateId"
          :items="templates"
          item-title="name"
          item-value="id"
          :label="t('pysis.selectTemplate')"
          class="mb-3"
        >
          <template #item="{ item, props: itemProps }">
            <v-list-item v-bind="itemProps">
              <v-list-item-subtitle>
                {{ item.raw.fields?.length || 0 }} {{ t('pysis.fields') }}
              </v-list-item-subtitle>
            </v-list-item>
          </template>
        </v-select>
        <v-switch
          v-model="overwriteExisting"
          :label="t('pysis.overwriteExisting')"
          color="warning"
        ></v-switch>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="tonal" @click="$emit('update:modelValue', false)">{{ t('common.cancel') }}</v-btn>
        <v-btn
          variant="tonal"
          color="primary"
          :loading="loading"
          :disabled="!selectedTemplateId"
          @click="handleSubmit"
        >
          {{ t('pysis.apply') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { DIALOG_SIZES } from '@/config/ui'

interface Template {
  id: string
  name?: string
  description?: string
  fields?: { internal_name: string; pysis_field_name: string; field_type: string }[]
}

const props = defineProps<{
  modelValue: boolean
  loading?: boolean
  templates: Template[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  submit: [templateId: string, overwrite: boolean]
}>()

const { t } = useI18n()

const selectedTemplateId = ref<string | null>(null)
const overwriteExisting = ref(false)

watch(() => props.modelValue, (isOpen) => {
  if (isOpen) {
    selectedTemplateId.value = null
    overwriteExisting.value = false
  }
})

function handleSubmit() {
  if (selectedTemplateId.value) {
    emit('submit', selectedTemplateId.value, overwriteExisting.value)
  }
}
</script>
