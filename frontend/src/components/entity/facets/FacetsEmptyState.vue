<template>
  <div>
    <!-- Empty State for Facets -->
    <v-card v-if="isEmpty" class="mt-4 text-center pa-8" variant="outlined">
      <v-icon size="80" color="grey-lighten-1" class="mb-4">mdi-tag-off-outline</v-icon>
      <h3 class="text-h6 mb-2">{{ t('entityDetail.emptyState.noProperties') }}</h3>
      <p class="text-body-2 text-medium-emphasis mb-4">
        {{ t('entityDetail.emptyState.noPropertiesDesc') }}
      </p>
      <div class="d-flex justify-center ga-2">
        <v-btn v-if="canEdit" variant="tonal" color="primary" @click="$emit('add-facet')">
          <v-icon start>mdi-plus</v-icon>
          {{ t('entityDetail.emptyState.addManually') }}
        </v-btn>
        <v-btn variant="outlined" @click="$emit('switch-tab', 'sources')">
          <v-icon start>mdi-web</v-icon>
          {{ t('entityDetail.emptyState.checkDataSources') }}
        </v-btn>
      </div>
    </v-card>

    <!-- No Search Results -->
    <v-card v-else-if="hasSearchQuery && !hasSearchResults" class="mt-4 text-center pa-6" variant="outlined">
      <v-icon size="60" color="grey-lighten-1" class="mb-3">mdi-magnify-close</v-icon>
      <h3 class="text-h6 mb-2">{{ t('entityDetail.noSearchResults', { query: searchQuery }) }}</h3>
      <p class="text-body-2 text-medium-emphasis mb-3">
        {{ t('entityDetail.noSearchResultsDesc') }}
      </p>
      <v-btn variant="tonal" @click="$emit('clear-search')">
        <v-icon start>mdi-close</v-icon>
        {{ t('entityDetail.clearSearch') }}
      </v-btn>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = withDefaults(defineProps<{
  hasFacets: boolean
  searchQuery: string
  hasSearchResults: boolean
  canEdit?: boolean
}>(), {
  canEdit: true,
})

defineEmits<{
  (e: 'add-facet'): void
  (e: 'switch-tab', tab: string): void
  (e: 'clear-search'): void
}>()

const { t } = useI18n()

const isEmpty = computed(() => !props.hasFacets)
const hasSearchQuery = computed(() => !!props.searchQuery)
</script>
