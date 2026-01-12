<template>
  <v-card variant="outlined" class="mb-4">
    <v-card-title class="text-subtitle-1">
      <v-icon start color="secondary">mdi-database-search</v-icon>
      {{ $t('categories.dataSourcesTab.foundSources') }}
      <v-chip v-if="sources.length" size="small" color="info" class="ml-2">
        {{ sources.length }}
      </v-chip>
    </v-card-title>
    <v-card-text>
      <!-- Loading state -->
      <div v-if="loading" class="text-center py-8">
        <v-progress-circular indeterminate color="primary" class="mb-2" />
        <div class="text-caption">{{ $t('categories.dataSourcesTab.loading') }}</div>
      </div>

      <!-- No tags selected -->
      <v-alert v-else-if="!hasSelectedTags" type="info" variant="tonal">
        {{ $t('categories.dataSourcesTab.noTagsSelected') }}
      </v-alert>

      <!-- No results -->
      <v-alert v-else-if="!sources.length" type="warning" variant="tonal">
        {{ $t('categories.dataSourcesTab.noSourcesFound') }}
      </v-alert>

      <!-- Results list with pagination -->
      <template v-else>
        <v-list lines="two" class="sources-result-list" role="list" :aria-label="$t('categories.dataSourcesTab.foundSources')">
          <v-list-item
            v-for="source in displayedSources"
            :key="source.id"
            :title="source.name"
            :subtitle="source.base_url"
            role="listitem"
          >
            <template #prepend>
              <v-avatar :color="getStatusColor(source.status)" size="36">
                <v-icon size="small" :color="getContrastColor(getStatusColor(source.status))">
                  {{ getSourceTypeIcon(source.source_type) }}
                </v-icon>
              </v-avatar>
            </template>
            <template #append>
              <div class="d-flex align-center ga-2">
                <div class="d-flex flex-wrap ga-1">
                  <v-chip
                    v-for="tag in (source.tags || []).slice(0, MAX_VISIBLE_TAGS)"
                    :key="tag"
                    size="x-small"
                    color="primary"
                    variant="outlined"
                  >
                    {{ tag }}
                  </v-chip>
                  <v-chip
                    v-if="(source.tags || []).length > MAX_VISIBLE_TAGS"
                    size="x-small"
                    color="grey"
                  >
                    +{{ (source.tags || []).length - MAX_VISIBLE_TAGS }}
                  </v-chip>
                </div>
                <v-chip
                  v-if="source.is_assigned"
                  size="x-small"
                  color="success"
                  variant="tonal"
                >
                  <v-icon start size="x-small">mdi-check</v-icon>
                  {{ $t('categories.dataSourcesTab.alreadyAssigned') }}
                </v-chip>
              </div>
            </template>
          </v-list-item>
        </v-list>

        <!-- Load More Button -->
        <div v-if="hasMore" class="text-center mt-2">
          <v-btn variant="text" color="primary" @click="loadMore">
            {{ $t('common.loadMore', { count: remainingCount }) }}
          </v-btn>
        </div>

        <!-- Assign All Button -->
        <div class="mt-4">
          <v-btn
            size="small"
            variant="tonal"
            color="primary"
            :loading="assigning"
            :aria-label="$t('categories.dataSourcesTab.assignAll')"
            @click="emit('assign-all')"
          >
            <v-icon start>mdi-link-plus</v-icon>
            {{ $t('categories.dataSourcesTab.assignAll') }} ({{ sources.length }})
          </v-btn>
        </div>
      </template>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { getContrastColor } from '@/composables/useColorHelpers'
import type { CategorySource } from '@/types/category'

interface Props {
  sources: CategorySource[]
  loading: boolean
  assigning: boolean
  hasSelectedTags: boolean
  getStatusColor: (status?: string) => string
  getSourceTypeIcon: (type?: string) => string
}

interface Emits {
  (e: 'assign-all'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// === Constants ===
const PAGE_SIZE = 50
const MAX_VISIBLE_TAGS = 3

// Local pagination state
const displayLimit = ref(PAGE_SIZE)

// Computed
const displayedSources = computed(() =>
  props.sources.slice(0, displayLimit.value)
)

const hasMore = computed(() =>
  props.sources.length > displayLimit.value
)

const remainingCount = computed(() =>
  props.sources.length - displayLimit.value
)

// Methods
const loadMore = () => {
  displayLimit.value += PAGE_SIZE
}

// Reset pagination when sources change
watch(() => props.sources, () => {
  displayLimit.value = PAGE_SIZE
})
</script>

<style scoped>
.sources-result-list {
  max-height: 350px;
  overflow-y: auto;
}
</style>
