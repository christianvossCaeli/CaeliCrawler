<template>
  <div
    class="mb-3 pa-3 rounded-lg facet-item border"
    :class="{
      'selected': isSelected,
      'bg-surface-light': !isDark,
      'bg-grey-darken-4': isDark
    }"
  >
    <!-- Checkbox for bulk selection -->
    <div class="d-flex align-start">
      <v-checkbox
        v-if="canEdit && bulkMode"
        :model-value="isSelected"
        hide-details
        density="compact"
        class="mr-2 mt-0"
        @update:model-value="$emit('toggle-selection', facet.id)"
      ></v-checkbox>
      <div class="flex-grow-1">
        <!-- Generic Facet Value Display -->
        <GenericFacetValueRenderer
          :value="normalizedValue || {}"
          :facet-type="facetType"
          show-icon
        />

        <!-- Entity Link Controls for Contact Types -->
        <div v-if="isContactType && (facet.target_entity_id || canEdit)" class="d-flex align-center ga-2 mt-2">
          <v-chip
            v-if="facet.target_entity_id"
            size="small"
            variant="tonal"
            color="primary"
            class="cursor-pointer"
            @click.stop="$emit('navigate-to-entity', facet)"
          >
            <v-icon start size="small">mdi-link-variant</v-icon>
            {{ facet.target_entity_name || t('entityDetail.viewEntity') }}
          </v-chip>
          <v-menu v-if="canEdit" location="bottom">
            <template #activator="{ props: menuProps }">
              <v-btn icon size="x-small" variant="text" :aria-label="t('summaries.moreActions')" v-bind="menuProps" @click.stop>
                <v-icon size="small">mdi-dots-vertical</v-icon>
              </v-btn>
            </template>
            <v-list density="compact">
              <v-list-item
                v-if="!facet.target_entity_id"
                prepend-icon="mdi-link-plus"
                :title="t('entityDetail.facets.linkToEntity', 'Mit Entity verknüpfen')"
                @click="$emit('open-link-dialog', facet)"
              ></v-list-item>
              <v-list-item
                v-if="facet.target_entity_id"
                prepend-icon="mdi-link-off"
                :title="t('entityDetail.facets.unlinkEntity', 'Verknüpfung entfernen')"
                @click="$emit('unlink-entity', facet)"
              ></v-list-item>
              <v-list-item
                v-if="facet.target_entity_id"
                prepend-icon="mdi-swap-horizontal"
                :title="t('entityDetail.facets.changeEntityLink', 'Andere Entity verknüpfen')"
                @click="$emit('open-link-dialog', facet)"
              ></v-list-item>
            </v-list>
          </v-menu>
        </div>

        <!-- Footer: Meta Info & Actions -->
        <div class="facet-footer mt-3 pt-3 border-t">
          <div class="d-flex align-center flex-wrap ga-3 mb-2">
            <v-chip
              size="small"
              variant="tonal"
              :color="sourceColor"
              class="cursor-pointer"
              @click.stop="$emit('open-source-details', facet)"
            >
              <v-icon start size="small">{{ sourceIcon }}</v-icon>
              {{ t('entityDetail.source') }}
            </v-chip>

            <div v-if="facet.confidence_score" class="d-flex align-center ga-2">
              <span class="text-caption text-medium-emphasis">{{ t('entityDetail.confidence') }}:</span>
              <v-progress-linear
                :model-value="facet.confidence_score * 100"
                :color="confidenceColor"
                height="6"
                rounded
                class="col-width-60"
              ></v-progress-linear>
              <span class="text-caption font-weight-medium">{{ Math.round(facet.confidence_score * 100) }}%</span>
            </div>

            <span v-if="facet.created_at" class="text-caption text-medium-emphasis">
              <v-icon size="small" class="mr-1">mdi-clock-outline</v-icon>
              {{ formatDate(facet.created_at) }}
            </span>

            <v-chip v-if="facet.human_verified" size="small" color="success" variant="flat">
              <v-icon start size="small">mdi-check-circle</v-icon>
              {{ t('entityDetail.verifiedLabel') }}
            </v-chip>
          </div>

          <div v-if="facet.id && canEdit" class="d-flex align-center ga-2">
            <v-btn
              v-if="!facet.human_verified"
              size="small"
              color="success"
              variant="tonal"
              @click.stop="$emit('verify', facet.id)"
            >
              <v-icon start size="small">mdi-check</v-icon>
              {{ t('entityDetail.verifyAction') }}
            </v-btn>
            <v-btn
              size="small"
              color="primary"
              variant="tonal"
              @click.stop="$emit('edit', facet)"
            >
              <v-icon start size="small">mdi-pencil</v-icon>
              {{ t('common.edit') }}
            </v-btn>
            <v-btn
              size="small"
              color="error"
              variant="tonal"
              @click.stop="$emit('delete', facet)"
            >
              <v-icon start size="small">mdi-delete</v-icon>
              {{ t('common.delete') }}
            </v-btn>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTheme } from 'vuetify'
import { useDateFormatter } from '@/composables/useDateFormatter'
import { useFacetHelpers } from '@/composables/facets'
import { GenericFacetValueRenderer } from '@/components/facets'
import type { FacetValue, FacetGroup } from '@/types/entity'
import type { FacetType } from '@/stores/facetTypes'

const props = defineProps<{
  facet: FacetValue
  facetGroup: FacetGroup
  facetType: FacetType
  selectedFacetIds: string[]
  bulkMode: boolean
  canEdit?: boolean
}>()

defineEmits<{
  (e: 'toggle-selection', id: string): void
  (e: 'navigate-to-entity', facet: FacetValue): void
  (e: 'open-link-dialog', facet: FacetValue): void
  (e: 'unlink-entity', facet: FacetValue): void
  (e: 'open-source-details', facet: FacetValue): void
  (e: 'verify', id: string): void
  (e: 'edit', facet: FacetValue): void
  (e: 'delete', facet: FacetValue): void
}>()

const { t } = useI18n()
const theme = useTheme()
const { formatRelativeTime } = useDateFormatter()
const { getConfidenceColor, getFacetSourceColor, getFacetSourceIcon } = useFacetHelpers()

const isDark = computed(() => theme.current.value.dark)
const isSelected = computed(() => props.selectedFacetIds.includes(props.facet.id))
const isContactType = computed(() => props.facetGroup.facet_type_slug === 'contact')

const normalizedValue = computed(() => {
  const value = props.facet.value
  if (value === null || value === undefined) return null
  if (typeof value === 'object') return value as Record<string, unknown>
  return { value } as Record<string, unknown>
})

const sourceColor = computed(() => getFacetSourceColor(props.facet.source_type))
const sourceIcon = computed(() => getFacetSourceIcon(props.facet.source_type))
const confidenceColor = computed(() => getConfidenceColor(props.facet.confidence_score ?? null))

function formatDate(date: string): string {
  return formatRelativeTime(date)
}
</script>

<style scoped>
.cursor-pointer {
  cursor: pointer;
}

.facet-item {
  transition: all 0.2s ease;
  border: 2px solid transparent;
}

.facet-item:hover {
  border-color: rgba(var(--v-theme-primary), 0.3);
}

.facet-item.selected {
  border-color: rgb(var(--v-theme-primary));
  background-color: rgba(var(--v-theme-primary), 0.08) !important;
}

.facet-footer {
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.border-t {
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
