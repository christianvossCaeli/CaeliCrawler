<template>
  <v-dialog :model-value="modelValue" :max-width="DIALOG_SIZES.MD" persistent @update:model-value="$emit('update:modelValue', $event)">
    <v-card>
      <v-card-title>
        {{ editingId ? t('admin.modelPricing.dialog.editTitle') : t('admin.modelPricing.dialog.addTitle') }}
      </v-card-title>
      <v-card-text>
        <v-form ref="formRef" @submit.prevent="handleSubmit">
          <v-select
            v-if="!editingId"
            v-model="localForm.provider"
            :items="providerSelectOptions"
            :label="t('admin.modelPricing.form.provider')"
            :rules="[v => !!v || t('validation.required')]"
            class="mb-4"
          />

          <v-text-field
            v-if="!editingId"
            v-model="localForm.model_name"
            :label="t('admin.modelPricing.form.modelName')"
            :placeholder="t('admin.modelPricing.form.modelNamePlaceholder')"
            :rules="[v => !!v || t('validation.required')]"
            class="mb-4"
          />

          <v-text-field
            v-model="localForm.display_name"
            :label="t('admin.modelPricing.form.displayName')"
            :placeholder="t('admin.modelPricing.form.displayNamePlaceholder')"
            class="mb-4"
          />

          <v-row>
            <v-col cols="6">
              <v-text-field
                v-model.number="localForm.input_price_per_1m"
                :label="t('admin.modelPricing.form.inputPrice')"
                type="number"
                step="0.01"
                min="0"
                :rules="[v => v >= 0 || t('validation.positiveNumber')]"
              />
            </v-col>
            <v-col cols="6">
              <v-text-field
                v-model.number="localForm.output_price_per_1m"
                :label="t('admin.modelPricing.form.outputPrice')"
                type="number"
                step="0.01"
                min="0"
                :rules="[v => v >= 0 || t('validation.positiveNumber')]"
              />
            </v-col>
          </v-row>

          <v-text-field
            v-model.number="localForm.cached_input_price_per_1m"
            :label="t('admin.modelPricing.form.cachedInputPrice')"
            type="number"
            step="0.01"
            min="0"
            class="mb-4"
          />

          <v-text-field
            v-if="!editingId"
            v-model="localForm.source_url"
            :label="t('admin.modelPricing.form.sourceUrl')"
            :placeholder="t('admin.modelPricing.form.sourceUrlPlaceholder')"
            class="mb-4"
          />

          <v-textarea
            v-model="localForm.notes"
            :label="t('admin.modelPricing.form.notes')"
            rows="2"
          />
        </v-form>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="$emit('update:modelValue', false)">
          {{ t('common.cancel') }}
        </v-btn>
        <v-btn
          color="primary"
          variant="flat"
          :loading="saving"
          @click="handleSubmit"
        >
          {{ t('common.save') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { DIALOG_SIZES } from '@/config/ui'
import { getProviderLabel } from '@/utils/llmProviders'

export interface PricingFormData {
  provider: string
  model_name: string
  display_name: string
  input_price_per_1m: number
  output_price_per_1m: number
  cached_input_price_per_1m: number | undefined
  source_url: string
  notes: string
}

const props = defineProps<{
  modelValue: boolean
  editingId: string | null
  initialData: PricingFormData
  saving: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  submit: [data: PricingFormData]
}>()

const { t } = useI18n()
const formRef = ref()

const providerSelectOptions = [
  { title: getProviderLabel('AZURE_OPENAI'), value: 'AZURE_OPENAI' },
  { title: getProviderLabel('OPENAI'), value: 'OPENAI' },
  { title: getProviderLabel('ANTHROPIC'), value: 'ANTHROPIC' },
]

const localForm = ref<PricingFormData>({ ...props.initialData })

// Sync form data when dialog opens
watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      localForm.value = { ...props.initialData }
    }
  },
  { immediate: true }
)

async function handleSubmit() {
  const result = await formRef.value?.validate()
  if (!result?.valid) return

  emit('submit', localForm.value)
}
</script>
