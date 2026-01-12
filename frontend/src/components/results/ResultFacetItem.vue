<template>
  <div
    class="pa-3 rounded-lg facet-item border mb-2"
    :class="{
      'bg-surface-light': !isDark,
      'bg-grey-darken-4': isDark,
      'inactive-facet': !facet.is_active
    }"
  >
    <!-- Header: Entity link + Status -->
    <div class="d-flex align-center justify-space-between mb-2">
      <router-link
        v-if="facet.target_entity_id"
        :to="`/entities/${facet.target_entity_id}`"
        class="text-decoration-none d-flex align-center ga-2"
      >
        <v-icon size="small" :color="targetEntityVisuals.color">{{ targetEntityVisuals.icon }}</v-icon>
        <span class="font-weight-medium" :style="{ color: targetEntityVisuals.color }">{{ facet.target_entity_name || $t('results.facets.unknownEntity') }}</span>
      </router-link>
      <span v-else class="text-medium-emphasis">{{ $t('results.facets.noEntity') }}</span>

      <div class="d-flex ga-1">
        <v-chip v-if="!facet.is_active" size="x-small" color="error" variant="tonal">
          {{ $t('results.facets.inactive') }}
        </v-chip>
        <v-chip v-if="facet.human_verified" size="x-small" color="success" variant="flat">
          <v-icon start size="x-small">mdi-check-circle</v-icon>
          {{ $t('results.facets.verified') }}
        </v-chip>
        <v-chip v-if="facet.human_corrections" size="x-small" color="info" variant="tonal">
          {{ $t('results.facets.corrected') }}
        </v-chip>
      </div>
    </div>

    <!-- Value Display -->
    <div class="facet-value mb-2">
      <span class="text-body-2">{{ facet.text_representation }}</span>
    </div>

    <!-- Meta: Confidence + Date -->
    <div class="d-flex align-center flex-wrap ga-3 text-caption text-medium-emphasis">
      <div v-if="facet.confidence_score" class="d-flex align-center ga-1">
        <v-icon size="x-small">mdi-chart-bar</v-icon>
        <span>{{ Math.round(facet.confidence_score * 100) }}%</span>
      </div>

      <div v-if="facet.occurrence_count && facet.occurrence_count > 1" class="d-flex align-center ga-1">
        <v-icon size="x-small">mdi-counter</v-icon>
        <span>{{ facet.occurrence_count }}x</span>
      </div>

      <div v-if="facet.created_at" class="d-flex align-center ga-1">
        <v-icon size="x-small">mdi-clock-outline</v-icon>
        <span>{{ formatDate(facet.created_at) }}</span>
      </div>
    </div>

    <!-- Actions -->
    <div v-if="canEdit" class="d-flex align-center ga-1 mt-3 pt-2 border-t">
      <!-- Verify (only if not verified and active) -->
      <v-btn
        v-if="!facet.human_verified && (facet.is_active ?? true)"
        size="small"
        color="success"
        variant="tonal"
        :loading="verifying"
        @click="$emit('verify', facet.id)"
      >
        <v-icon start size="small">mdi-check</v-icon>
        {{ $t('results.facets.verify') }}
      </v-btn>

      <!-- Reject/Deactivate (only if active and not protected) -->
      <v-btn
        v-if="(facet.is_active ?? true) && !isProtected"
        size="small"
        color="error"
        variant="tonal"
        :loading="rejecting"
        @click="$emit('reject', facet.id)"
      >
        <v-icon start size="small">mdi-close</v-icon>
        {{ $t('results.facets.reject') }}
      </v-btn>

      <!-- Reactivate (only if inactive) -->
      <v-btn
        v-if="facet.is_active === false"
        size="small"
        color="warning"
        variant="tonal"
        :loading="reactivating"
        @click="$emit('reactivate', facet.id)"
      >
        <v-icon start size="small">mdi-undo</v-icon>
        {{ $t('results.facets.reactivate') }}
      </v-btn>

      <v-spacer />

      <!-- Protected indicator -->
      <v-tooltip v-if="isProtected" location="top">
        <template #activator="{ props: tooltipProps }">
          <v-icon v-bind="tooltipProps" size="small" color="info">mdi-shield-check</v-icon>
        </template>
        {{ $t('results.facets.protectedTooltip') }}
      </v-tooltip>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useTheme } from 'vuetify'
import { useDateFormatter } from '@/composables/useDateFormatter'
import type { FacetValue } from '@/types/entity'

const props = defineProps<{
  facet: FacetValue
  canEdit?: boolean
  verifying?: boolean
  rejecting?: boolean
  reactivating?: boolean
}>()

defineEmits<{
  verify: [id: string]
  reject: [id: string]
  reactivate: [id: string]
}>()

// Default visuals when API doesn't provide icon/color
const DEFAULT_VISUALS = { icon: 'mdi-link-variant', color: 'grey' }

const theme = useTheme()
const { formatRelativeTime } = useDateFormatter()

const isDark = computed(() => theme.current.value.dark)

/**
 * Get the visual styling for the target entity type.
 * Uses API values (from entity_types table) with fallback to defaults.
 */
const targetEntityVisuals = computed(() => {
  const icon = props.facet.target_entity_type_icon || DEFAULT_VISUALS.icon
  const color = props.facet.target_entity_type_color || DEFAULT_VISUALS.color
  return { icon, color }
})

/**
 * A facet is protected if it's human-verified or has corrections.
 */
const isProtected = computed(() =>
  props.facet.human_verified || !!props.facet.human_corrections
)

function formatDate(date: string): string {
  return formatRelativeTime(date)
}
</script>

<style scoped>
.facet-item {
  transition: all 0.2s ease;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.facet-item:hover {
  border-color: rgba(var(--v-theme-primary), 0.3);
}

.facet-item.inactive-facet {
  opacity: 0.6;
  background: rgba(var(--v-theme-error), 0.05) !important;
}

.border-t {
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
