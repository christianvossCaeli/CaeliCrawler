<template>
  <v-dialog v-model="modelValue" max-width="700" scrollable>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon start>mdi-plus-circle</v-icon>
        {{ t('entityDetail.dialog.addFacet') }}
      </v-card-title>
      <v-card-text>
        <v-form ref="formRef" @submit.prevent="$emit('save')">
          <!-- Facet Type Selection -->
          <v-select
            :model-value="facetTypeId"
            :items="facetTypes"
            item-title="name"
            item-value="id"
            :label="t('entityDetail.dialog.facetType')"
            :rules="[v => !!v || t('entityDetail.dialog.facetTypeRequired')]"
            variant="outlined"
            density="comfortable"
            class="mb-4"
            @update:model-value="$emit('update:facetTypeId', $event)"
          >
            <template #item="{ item, props: itemProps }">
              <v-list-item v-bind="itemProps">
                <template #prepend>
                  <v-icon :icon="item.raw.icon ?? 'mdi-tag'" :color="item.raw.color ?? undefined" size="small"></v-icon>
                </template>
              </v-list-item>
            </template>
            <template #selection="{ item }">
              <v-icon :icon="item.raw.icon ?? 'mdi-tag'" :color="item.raw.color ?? undefined" size="small" class="mr-2"></v-icon>
              {{ item.raw.name }}
            </template>
          </v-select>

          <!-- Dynamic Schema Form (when facet type has a schema) -->
          <template v-if="selectedFacetType?.value_schema">
            <v-divider class="mb-4"></v-divider>
            <div class="text-subtitle-2 mb-3 text-medium-emphasis-darken-1">
              {{ t('entityDetail.dialog.facetDetails') }}
            </div>
            <DynamicSchemaForm
              :model-value="value"
              :schema="selectedFacetType.value_schema"
              @update:model-value="$emit('update:value', $event)"
            />
          </template>

          <!-- Simple text input (when no schema) -->
          <template v-else-if="facetTypeId">
            <v-textarea
              :model-value="textRepresentation"
              :label="t('entityDetail.dialog.facetValue')"
              :rules="[v => !!v || t('entityDetail.dialog.facetValueRequired')]"
              rows="3"
              variant="outlined"
              density="comfortable"
              class="mb-3"
              @update:model-value="$emit('update:textRepresentation', $event)"
            ></v-textarea>
          </template>

          <v-divider class="my-4"></v-divider>

          <!-- Source URL -->
          <v-text-field
            :model-value="sourceUrl"
            :label="t('entityDetail.dialog.sourceUrl')"
            placeholder="https://..."
            variant="outlined"
            density="comfortable"
            class="mb-3"
            prepend-inner-icon="mdi-link"
            @update:model-value="$emit('update:sourceUrl', $event)"
          ></v-text-field>

          <!-- Confidence Score -->
          <div class="d-flex align-center ga-4">
            <span class="text-body-2">{{ t('entityDetail.dialog.confidence') }}:</span>
            <v-slider
              :model-value="confidenceScore"
              :min="0"
              :max="1"
              :step="0.1"
              thumb-label
              :color="getConfidenceColor(confidenceScore)"
              hide-details
              class="flex-grow-1"
              @update:model-value="$emit('update:confidenceScore', $event)"
            ></v-slider>
            <v-chip size="small" :color="getConfidenceColor(confidenceScore)">
              {{ Math.round(confidenceScore * 100) }}%
            </v-chip>
          </div>
        </v-form>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="tonal" @click="$emit('close')">{{ t('common.cancel') }}</v-btn>
        <v-btn
          color="primary"
          :loading="saving"
          :disabled="!canSave"
          @click="$emit('save')"
        >
          <v-icon start>mdi-check</v-icon>
          {{ t('common.save') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import DynamicSchemaForm from '@/components/DynamicSchemaForm.vue'

// Types
interface FacetType {
  id: string
  name: string
  icon?: string | null
  color?: string | null
  value_schema?: Record<string, unknown> | null
}

const modelValue = defineModel<boolean>()

// Props
const props = defineProps<{
  facetTypeId: string
  facetTypes: FacetType[]
  selectedFacetType: FacetType | null
  value: Record<string, unknown>
  textRepresentation: string
  sourceUrl: string
  confidenceScore: number
  saving: boolean
}>()

// Emits
defineEmits<{
  'update:facetTypeId': [value: string]
  'update:value': [value: Record<string, unknown>]
  'update:textRepresentation': [value: string]
  'update:sourceUrl': [value: string]
  'update:confidenceScore': [value: number]
  save: []
  close: []
}>()

const { t } = useI18n()

// Form ref for validation
const formRef = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)

// Computed
const canSave = computed(() => {
  if (!props.facetTypeId) return false
  if (props.selectedFacetType?.value_schema) {
    // Schema form - value should have some content
    return Object.keys(props.value).length > 0
  }
  // Simple text - needs text representation
  return !!props.textRepresentation
})

// Helpers
function getConfidenceColor(score: number): string {
  if (score >= 0.8) return 'success'
  if (score >= 0.5) return 'warning'
  return 'error'
}

defineExpose({ formRef })
</script>
