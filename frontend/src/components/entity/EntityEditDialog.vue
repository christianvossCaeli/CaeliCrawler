<template>
  <v-dialog :model-value="modelValue" max-width="500" @update:model-value="$emit('update:modelValue', $event)">
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2">mdi-pencil</v-icon>
        {{ t('entityDetail.dialog.editEntity', { type: entityTypeName }) }}
      </v-card-title>
      <v-card-text>
        <v-form ref="formRef" @submit.prevent="handleSave">
          <v-text-field
            :model-value="name"
            @update:model-value="$emit('update:name', $event)"
            :label="t('entityDetail.dialog.name')"
            :rules="[v => !!v || t('entityDetail.dialog.nameRequired')]"
          ></v-text-field>
          <v-text-field
            :model-value="externalId"
            @update:model-value="$emit('update:externalId', $event)"
            :label="t('entityDetail.dialog.externalId')"
          ></v-text-field>
        </v-form>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="tonal" @click="$emit('update:modelValue', false)">{{ t('common.cancel') }}</v-btn>
        <v-btn variant="tonal" color="primary" :loading="saving" @click="handleSave">
          {{ t('common.save') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

// Props
defineProps<{
  modelValue: boolean
  name: string
  externalId: string
  entityTypeName?: string
  saving: boolean
}>()

// Emits
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'update:name': [value: string]
  'update:externalId': [value: string]
  save: []
}>()

const { t } = useI18n()
const formRef = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)

async function handleSave() {
  const { valid } = await formRef.value?.validate() || { valid: false }
  if (valid) {
    emit('save')
  }
}
</script>
