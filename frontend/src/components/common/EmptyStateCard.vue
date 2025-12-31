<template>
  <v-card
    :variant="variant"
    :class="['empty-state-card', { 'empty-state-card--dense': dense }]"
  >
    <v-card-text class="d-flex flex-column align-center justify-center text-center py-8">
      <!-- Icon -->
      <v-icon
        v-if="icon"
        :icon="icon"
        :size="dense ? 40 : 56"
        :color="iconColor"
        class="mb-4"
        aria-hidden="true"
      />

      <!-- Title -->
      <h3 v-if="title" class="text-h6 font-weight-medium mb-2">
        {{ title }}
      </h3>

      <!-- Description -->
      <p
        v-if="description"
        class="text-body-2 text-medium-emphasis mb-4"
        style="max-width: 360px"
      >
        {{ description }}
      </p>

      <!-- Slot for custom content -->
      <slot></slot>

      <!-- Action Button -->
      <v-btn
        v-if="actionText"
        :color="actionColor"
        :variant="actionVariant"
        :prepend-icon="actionIcon"
        :size="dense ? 'small' : 'default'"
        class="mt-2"
        @click="$emit('action')"
      >
        {{ actionText }}
      </v-btn>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
/**
 * EmptyStateCard Component
 *
 * A card-based empty state component for lists, tables, and content areas.
 * Provides consistent styling with Vuetify card wrapper.
 *
 * @example
 * ```vue
 * <EmptyStateCard
 *   icon="mdi-file-search-outline"
 *   :title="$t('common.noResults')"
 *   :description="$t('common.tryAdjustingFilters')"
 *   :action-text="$t('common.clearFilters')"
 *   action-icon="mdi-filter-remove"
 *   @action="clearFilters"
 * />
 * ```
 */
withDefaults(defineProps<{
  /** MDI icon name to display */
  icon?: string
  /** Icon color (Vuetify color name) */
  iconColor?: string
  /** Main title text */
  title?: string
  /** Descriptive text below the title */
  description?: string
  /** Action button text (shows button if provided) */
  actionText?: string
  /** Action button icon */
  actionIcon?: string
  /** Action button color */
  actionColor?: string
  /** Action button variant */
  actionVariant?: 'flat' | 'text' | 'elevated' | 'tonal' | 'outlined' | 'plain'
  /** Card variant */
  variant?: 'flat' | 'text' | 'elevated' | 'tonal' | 'outlined' | 'plain'
  /** Use compact spacing */
  dense?: boolean
}>(), {
  icon: 'mdi-folder-open-outline',
  iconColor: 'grey-lighten-1',
  actionColor: 'primary',
  actionVariant: 'tonal',
  variant: 'outlined',
  dense: false,
})

defineEmits<{
  /** Emitted when the action button is clicked */
  action: []
}>()
</script>

<style scoped>
.empty-state-card {
  min-height: 200px;
}

.empty-state-card--dense {
  min-height: 140px;
}

.empty-state-card--dense .v-card-text {
  padding: 1rem !important;
}
</style>
