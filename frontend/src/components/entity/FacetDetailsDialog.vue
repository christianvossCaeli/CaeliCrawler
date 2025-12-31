<template>
  <v-dialog v-model="modelValue" max-width="800" scrollable>
    <v-card v-if="facetGroup">
      <v-card-title class="d-flex align-center">
        <v-icon :icon="facetGroup.facet_type_icon" :color="facetGroup.facet_type_color" class="mr-2"></v-icon>
        {{ facetGroup.facet_type_name }}
        <v-spacer></v-spacer>
        <v-btn icon="mdi-close" variant="tonal" :aria-label="t('common.close')" @click="modelValue = false"></v-btn>
      </v-card-title>
      <v-card-text>
        <div class="d-flex flex-column ga-3">
          <v-card
            v-for="fv in facetValues"
            :key="fv.id"
            variant="outlined"
            class="pa-3"
          >
            <!-- Generic Facet Value Display -->
            <GenericFacetValueRenderer
              :value="normalizeValue(fv.value)"
              :facet-type="facetGroupToFacetType(facetGroup)"
              show-icon
            />

            <!-- Meta Info (shown for all) -->
            <v-divider class="my-3"></v-divider>
            <div class="d-flex align-center ga-2 flex-wrap">
              <v-progress-linear
                :model-value="(fv.confidence_score || 0) * 100"
                :color="getConfidenceColor(fv.confidence_score)"
                height="4"
                style="max-width: 80px;"
              ></v-progress-linear>
              <span class="text-caption">{{ Math.round((fv.confidence_score || 0) * 100) }}%</span>
              <v-chip v-if="fv.human_verified" size="x-small" color="success">
                <v-icon start size="x-small">mdi-check</v-icon>
                {{ t('entityDetail.verified') }}
              </v-chip>
              <v-chip v-if="fv.source_url" size="x-small" variant="outlined" :href="fv.source_url" target="_blank" tag="a">
                <v-icon start size="x-small">mdi-link</v-icon>
                {{ t('entityDetail.source') }}
              </v-chip>
              <v-spacer></v-spacer>
              <v-btn
                v-if="canEdit && !fv.human_verified"
                size="small"
                color="success"
                variant="tonal"
                @click="$emit('verify', fv.id)"
              >
                <v-icon start size="small">mdi-check</v-icon>
                {{ t('entityDetail.verify') }}
              </v-btn>
            </div>

            <!-- Timestamps / History -->
            <div v-if="fv.created_at || fv.updated_at" class="mt-2 d-flex align-center ga-3 text-caption text-medium-emphasis">
              <span v-if="fv.created_at">
                <v-icon size="x-small" class="mr-1">mdi-clock-plus-outline</v-icon>
                {{ t('entityDetail.created') }}: {{ formatDate(fv.created_at) }}
              </span>
              <span v-if="fv.updated_at && fv.updated_at !== fv.created_at">
                <v-icon size="x-small" class="mr-1">mdi-clock-edit-outline</v-icon>
                {{ t('entityDetail.updated') }}: {{ formatDate(fv.updated_at) }}
              </span>
            </div>
          </v-card>
        </div>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useDateFormatter } from '@/composables/useDateFormatter'
import { useFacetTypeRenderer } from '@/composables/useFacetTypeRenderer'
import { GenericFacetValueRenderer } from '@/components/facets'
import type { FacetGroup, FacetValue } from '@/types/entity'

const modelValue = defineModel<boolean>()
// Props
withDefaults(defineProps<{
  facetGroup: FacetGroup | null
  facetValues: FacetValue[]
  canEdit?: boolean
}>(), {
  canEdit: true,
})

// Emits
defineEmits<{
  verify: [id: string]
  copyEmail: [email: string]
}>()

const { facetGroupToFacetType, normalizeValue } = useFacetTypeRenderer()

const { t } = useI18n()
const { formatDate: formatLocaleDate } = useDateFormatter()

// Helper functions
function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return ''
  try {
    return formatLocaleDate(dateStr, 'dd.MM.yyyy HH:mm')
  } catch {
    return dateStr
  }
}

function getConfidenceColor(score: number | null | undefined): string {
  if (score === null || score === undefined) return 'grey'
  if (score >= 0.8) return 'success'
  if (score >= 0.5) return 'warning'
  return 'error'
}
</script>
