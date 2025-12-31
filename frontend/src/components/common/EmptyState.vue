<template>
  <v-container
    :class="[
      'd-flex flex-column align-center justify-center text-center',
      dense ? 'pa-4' : 'pa-8',
    ]"
    :style="{ minHeight: minHeight }"
  >
    <!-- Icon -->
    <v-icon
      v-if="icon"
      :icon="icon"
      :size="dense ? 48 : 64"
      :color="iconColor"
      class="mb-4"
      aria-hidden="true"
    />

    <!-- Title -->
    <h3 v-if="title" class="text-h6 font-weight-medium mb-2">
      {{ title }}
    </h3>

    <!-- Description -->
    <p v-if="description" class="text-body-2 text-medium-emphasis mb-4" style="max-width: 400px">
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
      @click="$emit('action')"
    >
      {{ actionText }}
    </v-btn>
  </v-container>
</template>

<script setup lang="ts">
/**
 * EmptyState Component
 *
 * A reusable component for displaying empty state messages in lists,
 * tables, and other content areas. Provides consistent styling and
 * optional action buttons.
 *
 * @example
 * ```vue
 * <EmptyState
 *   icon="mdi-file-search-outline"
 *   :title="$t('common.noResults')"
 *   :description="$t('common.noResultsDescription')"
 *   :action-text="$t('common.createNew')"
 *   action-icon="mdi-plus"
 *   @action="handleCreate"
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
  /** Minimum height for the container */
  minHeight?: string
  /** Use compact spacing */
  dense?: boolean
}>(), {
  icon: 'mdi-folder-open-outline',
  iconColor: 'grey',
  actionColor: 'primary',
  actionVariant: 'tonal',
  minHeight: '200px',
  dense: false,
})

defineEmits<{
  /** Emitted when the action button is clicked */
  action: []
}>()
</script>
