<template>
  <v-card variant="outlined" class="mt-4">
    <v-card-title class="text-subtitle-2 pb-2">
      <v-icon start size="small">mdi-folder-multiple</v-icon>
      {{ $t('sources.form.categories') }}
    </v-card-title>
    <v-card-text>
      <p class="text-caption text-medium-emphasis mb-3">{{ $t('sources.form.categoriesHint') }}</p>
      <div class="d-flex align-center">
        <v-select
          :model-value="categoryIds"
          :items="categories"
          item-title="name"
          item-value="id"
          multiple
          chips
          closable-chips
          class="flex-grow-1"
          variant="outlined"
          density="comfortable"
          @update:model-value="$emit('update:categoryIds', $event)"
        >
          <template #chip="{ item, index }">
            <v-chip
              :color="index === 0 ? 'primary' : 'default'"
              closable
              @click:close="removeCategory(index)"
            >
              {{ item.title }}
              <v-icon v-if="index === 0" end size="x-small">mdi-star</v-icon>
            </v-chip>
          </template>
        </v-select>
        <v-btn
          v-if="categoryIds.length > 0"
          icon="mdi-information-outline"
          variant="text"
          size="small"
          color="primary"
          class="ml-2"
          :title="$t('sources.form.primaryCategory')"
          @click="$emit('showCategoryInfo', categoryIds[0])"
        />
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
/**
 * SourceFormCategories - Category selection component
 *
 * Allows multi-selection with primary category indicator.
 */
import type { CategoryResponse } from '@/types/category'

interface Props {
  categoryIds: string[]
  categories: CategoryResponse[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'update:categoryIds', value: string[]): void
  (e: 'showCategoryInfo', categoryId: string): void
}>()

/** Remove category at index */
const removeCategory = (index: number) => {
  const newIds = [...props.categoryIds]
  newIds.splice(index, 1)
  emit('update:categoryIds', newIds)
}
</script>
