<template>
  <div
    v-if="hasActiveFilters"
    class="d-flex flex-wrap gap-2 mb-4"
    role="region"
    :aria-label="$t('sources.filters.activeFilters')"
  >
    <!-- Category Filter -->
    <v-chip
      v-if="categoryId"
      closable
      color="primary"
      variant="tonal"
      role="button"
      tabindex="0"
      :aria-label="$t('sources.filters.removeCategory', { name: categoryName })"
      @click:close="$emit('clear:category')"
      @keydown.enter.prevent="$emit('clear:category')"
      @keydown.space.prevent="$emit('clear:category')"
      @keydown.delete="$emit('clear:category')"
      @keydown.backspace="$emit('clear:category')"
    >
      <v-icon start size="x-small" aria-hidden="true">mdi-folder</v-icon>
      {{ categoryName }}
    </v-chip>

    <!-- Type Filter -->
    <v-chip
      v-if="sourceType"
      closable
      :color="getTypeColor(sourceType)"
      variant="tonal"
      role="button"
      tabindex="0"
      :aria-label="$t('sources.filters.removeType', { name: getTypeLabel(sourceType) })"
      @click:close="$emit('clear:type')"
      @keydown.enter.prevent="$emit('clear:type')"
      @keydown.space.prevent="$emit('clear:type')"
      @keydown.delete="$emit('clear:type')"
      @keydown.backspace="$emit('clear:type')"
    >
      <v-icon start size="x-small" aria-hidden="true">{{ getTypeIcon(sourceType) }}</v-icon>
      {{ getTypeLabel(sourceType) }}
    </v-chip>

    <!-- Status Filter -->
    <v-chip
      v-if="status"
      closable
      :color="getStatusColor(status)"
      variant="tonal"
      role="button"
      tabindex="0"
      :aria-label="$t('sources.filters.removeStatus', { name: getStatusLabel(status) })"
      @click:close="$emit('clear:status')"
      @keydown.enter.prevent="$emit('clear:status')"
      @keydown.space.prevent="$emit('clear:status')"
      @keydown.delete="$emit('clear:status')"
      @keydown.backspace="$emit('clear:status')"
    >
      <v-icon start size="x-small" aria-hidden="true">{{ getStatusIcon(status) }}</v-icon>
      {{ getStatusLabel(status) }}
    </v-chip>

    <!-- Tag Filters -->
    <v-chip
      v-for="tag in tags"
      :key="tag"
      closable
      :color="getTagColor(tag)"
      variant="tonal"
      role="button"
      tabindex="0"
      :aria-label="$t('sources.filters.removeTag', { name: tag })"
      @click:close="$emit('clear:tag', tag)"
      @keydown.enter.prevent="$emit('clear:tag', tag)"
      @keydown.space.prevent="$emit('clear:tag', tag)"
      @keydown.delete="$emit('clear:tag', tag)"
      @keydown.backspace="$emit('clear:tag', tag)"
    >
      <v-icon start size="x-small" aria-hidden="true">mdi-tag</v-icon>
      {{ tag }}
    </v-chip>

    <!-- Clear All Button -->
    <v-btn
      variant="text"
      size="small"
      color="grey"
      :aria-label="$t('sources.filters.clearAllFilters')"
      @click="$emit('clear:all')"
    >
      <v-icon start size="small" aria-hidden="true">mdi-close-circle</v-icon>
      {{ $t('sources.filters.clearAll') }}
    </v-btn>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useSourceHelpers } from '@/composables/useSourceHelpers'
import type { SourceType, SourceStatus } from '@/types/sources'

interface Props {
  categoryId: string | null
  categoryName: string
  sourceType: SourceType | string | null
  status: SourceStatus | string | null
  tags: string[]
}

const props = defineProps<Props>()

defineEmits<{
  (e: 'clear:category'): void
  (e: 'clear:type'): void
  (e: 'clear:status'): void
  (e: 'clear:tag', tag: string): void
  (e: 'clear:all'): void
}>()

const {
  getTypeColor,
  getTypeIcon,
  getTypeLabel,
  getStatusColor,
  getStatusIcon,
  getStatusLabel,
  getTagColor,
} = useSourceHelpers()

const hasActiveFilters = computed(() => {
  return !!(
    props.categoryId ||
    props.sourceType ||
    props.status ||
    props.tags.length > 0
  )
})
</script>
