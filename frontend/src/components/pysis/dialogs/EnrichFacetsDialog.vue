<template>
  <v-dialog :model-value="modelValue" :max-width="DIALOG_SIZES.SM" @update:model-value="$emit('update:modelValue', $event)">
    <v-card>
      <v-card-title>
        <v-icon start color="secondary">mdi-database-arrow-up</v-icon>
        {{ t('pysis.facets.enrichFacetsTitle') }}
      </v-card-title>
      <v-card-text>
        <v-alert type="info" variant="tonal" density="compact" class="mb-4">
          {{ t('pysis.facets.enrichFacetsDescription') }}
        </v-alert>
        <v-checkbox
          v-model="overwrite"
          :label="t('pysis.facets.overwriteExisting')"
          density="compact"
          hide-details
          color="warning"
        ></v-checkbox>
        <v-alert v-if="overwrite" type="warning" variant="tonal" density="compact" class="mt-3">
          {{ t('pysis.facets.overwriteWarning') }}
        </v-alert>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="tonal" @click="$emit('update:modelValue', false)">{{ t('common.cancel') }}</v-btn>
        <v-btn variant="tonal" color="secondary" :loading="loading" @click="handleSubmit">
          <v-icon start>mdi-database-arrow-up</v-icon>
          {{ t('pysis.facets.startEnrichment') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { DIALOG_SIZES } from '@/config/ui'

const props = defineProps<{
  modelValue: boolean
  loading?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  submit: [overwrite: boolean]
}>()

const { t } = useI18n()

const overwrite = ref(false)

watch(() => props.modelValue, (isOpen) => {
  if (isOpen) {
    overwrite.value = false
  }
})

function handleSubmit() {
  emit('submit', overwrite.value)
}
</script>
