<script setup lang="ts">
/**
 * WidgetEmptyState - Reusable empty state component for widgets
 *
 * Provides consistent styling for empty states across all widgets.
 */

defineProps<{
  icon: string
  message: string
  hint?: string
}>()
</script>

<template>
  <div class="text-center py-6 text-medium-emphasis empty-state" role="status">
    <v-icon size="32" class="mb-2">{{ icon }}</v-icon>
    <div class="text-body-2">{{ message }}</div>
    <div v-if="hint" class="text-caption mt-1">{{ hint }}</div>
    <slot />
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100px;
}
</style>
