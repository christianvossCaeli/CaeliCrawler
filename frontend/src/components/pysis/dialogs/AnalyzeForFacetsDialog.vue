<template>
  <v-dialog :model-value="modelValue" max-width="500" @update:model-value="$emit('update:modelValue', $event)">
    <v-card>
      <v-card-title>
        <v-icon start color="info">mdi-brain</v-icon>
        {{ t('pysis.facets.analyzeForFacetsTitle') }}
      </v-card-title>
      <v-card-text>
        <v-alert type="info" variant="tonal" density="compact" class="mb-4">
          {{ t('pysis.facets.analyzeForFacetsDescription') }}
        </v-alert>
        <v-checkbox
          v-model="includeEmpty"
          :label="t('pysis.facets.includeEmptyFields')"
          density="compact"
          hide-details
          class="mb-2"
        ></v-checkbox>
        <v-slider
          v-model="minConfidence"
          :label="t('pysis.facets.minConfidence')"
          :min="0"
          :max="1"
          :step="0.1"
          thumb-label
          density="compact"
          class="mt-4"
        >
          <template #thumb-label="{ modelValue: val }">
            {{ Math.round(val * 100) }}%
          </template>
        </v-slider>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="tonal" @click="$emit('update:modelValue', false)">{{ t('common.cancel') }}</v-btn>
        <v-btn variant="tonal" color="info" :loading="loading" @click="handleSubmit">
          <v-icon start>mdi-brain</v-icon>
          {{ t('pysis.facets.startAnalysis') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{
  modelValue: boolean
  loading?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  submit: [options: { includeEmpty: boolean; minConfidence: number }]
}>()

const { t } = useI18n()

const includeEmpty = ref(false)
const minConfidence = ref(0)

watch(() => props.modelValue, (isOpen) => {
  if (isOpen) {
    includeEmpty.value = false
    minConfidence.value = 0
  }
})

function handleSubmit() {
  emit('submit', {
    includeEmpty: includeEmpty.value,
    minConfidence: minConfidence.value,
  })
}
</script>
