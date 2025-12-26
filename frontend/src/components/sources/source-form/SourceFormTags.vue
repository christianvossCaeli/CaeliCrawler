<template>
  <v-card variant="outlined" class="mt-4">
    <v-card-title class="text-subtitle-2 pb-2">
      <v-icon start size="small">mdi-tag-multiple</v-icon>
      {{ $t('sources.form.tags') }}
    </v-card-title>
    <v-card-text>
      <v-combobox
        :model-value="tags"
        :items="suggestions"
        :label="$t('sources.form.tagsLabel')"
        :hint="$t('sources.form.tagsHint')"
        persistent-hint
        multiple
        chips
        closable-chips
        variant="outlined"
        density="comfortable"
        prepend-inner-icon="mdi-tag"
        @update:model-value="$emit('update:tags', $event)"
      >
        <template #chip="{ props, item }">
          <v-chip
            v-bind="props"
            :color="getTagColor(item.value)"
            size="small"
          >
            {{ item.value }}
          </v-chip>
        </template>
      </v-combobox>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
/**
 * SourceFormTags - Tag selection component
 *
 * Combobox for selecting and creating tags with color coding.
 */
import { useSourceHelpers } from '@/composables/useSourceHelpers'

interface Props {
  tags: string[]
  suggestions: string[]
}

defineProps<Props>()

defineEmits<{
  (e: 'update:tags', value: string[]): void
}>()

const { getTagColor } = useSourceHelpers()
</script>
