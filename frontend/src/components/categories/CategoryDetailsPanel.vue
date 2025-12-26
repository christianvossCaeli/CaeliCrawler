<template>
  <div>
    <v-alert type="info" variant="tonal" class="mb-4">
      <div class="d-flex align-center">
        <v-icon start>mdi-tag-multiple</v-icon>
        {{ $t('categories.dataSourcesTab.description') }}
      </div>
    </v-alert>

    <!-- Tag Filter Section -->
    <v-card variant="outlined" class="mb-4">
      <v-card-title class="text-subtitle-1 pb-2">
        <v-icon start color="primary">mdi-filter</v-icon>
        {{ $t('categories.dataSourcesTab.filterByTags') }}
      </v-card-title>
      <v-card-text>
        <v-row>
          <v-col cols="12" md="8">
            <v-combobox
              :model-value="selectedTags"
              :items="availableTags"
              :label="$t('categories.dataSourcesTab.filterByTags')"
              multiple
              chips
              closable-chips
              variant="outlined"
              density="compact"
              @update:model-value="emit('update:selectedTags', $event)"
            >
              <template #chip="{ item, props }">
                <v-chip v-bind="props" color="primary" variant="tonal">
                  <v-icon start size="small">mdi-tag</v-icon>
                  {{ item.raw }}
                </v-chip>
              </template>
            </v-combobox>
          </v-col>
          <v-col cols="12" md="4">
            <v-radio-group
              :model-value="matchMode"
              inline
              hide-details
              @update:model-value="emit('update:matchMode', $event)"
            >
              <v-radio value="all">
                <template #label>
                  <span class="text-caption">{{ $t('categories.dataSourcesTab.matchAll') }}</span>
                </template>
              </v-radio>
              <v-radio value="any">
                <template #label>
                  <span class="text-caption">{{ $t('categories.dataSourcesTab.matchAny') }}</span>
                </template>
              </v-radio>
            </v-radio-group>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Results Section -->
    <v-card variant="outlined">
      <v-card-title class="text-subtitle-1 d-flex align-center justify-space-between">
        <div>
          <v-icon start color="secondary">mdi-database-search</v-icon>
          {{ $t('categories.dataSourcesTab.foundSources') }}
          <v-chip v-if="foundSources.length" size="small" color="info" class="ml-2">
            {{ foundSources.length }}
          </v-chip>
        </div>
        <div v-if="foundSources.length > 0">
          <v-btn
            size="small"
            variant="tonal"
            color="primary"
            :loading="assigning"
            @click="emit('assign-all')"
          >
            <v-icon start>mdi-link-plus</v-icon>
            {{ $t('categories.dataSourcesTab.assignAll') }} ({{ foundSources.length }})
          </v-btn>
        </div>
      </v-card-title>
      <v-card-text>
        <!-- Loading state -->
        <div v-if="loading" class="text-center py-8">
          <v-progress-circular indeterminate color="primary" class="mb-2" />
          <div class="text-caption">{{ $t('categories.dataSourcesTab.loading') }}</div>
        </div>

        <!-- No tags selected -->
        <v-alert v-else-if="!selectedTags.length" type="info" variant="tonal">
          {{ $t('categories.dataSourcesTab.noTagsSelected') }}
        </v-alert>

        <!-- No results -->
        <v-alert v-else-if="!foundSources.length" type="warning" variant="tonal">
          {{ $t('categories.dataSourcesTab.noSourcesFound') }}
        </v-alert>

        <!-- Results list -->
        <v-list v-else lines="two" class="sources-result-list">
          <v-list-item
            v-for="source in foundSources.slice(0, 50)"
            :key="source.id"
            :title="source.name"
            :subtitle="source.base_url"
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
                    v-for="tag in (source.tags || []).slice(0, 3)"
                    :key="tag"
                    size="x-small"
                    color="primary"
                    variant="outlined"
                  >
                    {{ tag }}
                  </v-chip>
                  <v-chip
                    v-if="(source.tags || []).length > 3"
                    size="x-small"
                    color="grey"
                  >
                    +{{ source.tags.length - 3 }}
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
          <v-list-item v-if="foundSources.length > 50" class="text-center text-medium-emphasis">
            ... {{ $t('sources.bulk.moreEntries', { count: foundSources.length - 50 }) }}
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>

    <!-- Current assigned count -->
    <v-alert v-if="currentSourceCount" type="success" variant="tonal" class="mt-4">
      <v-icon start>mdi-check-circle</v-icon>
      {{ $t('categories.dataSourcesTab.currentlyAssigned') }}: <strong>{{ currentSourceCount }}</strong> {{ $t('categories.crawler.sourcesCount') }}
    </v-alert>
  </div>
</template>

<script setup lang="ts">
import { getContrastColor } from '@/composables/useColorHelpers'

export interface CategoryDetailsPanelProps {
  selectedTags: string[]
  matchMode: 'all' | 'any'
  availableTags: string[]
  foundSources: { id: string; name: string; status?: string; source_type?: string }[]
  loading: boolean
  assigning: boolean
  currentSourceCount?: number
  getStatusColor: (status: string) => string
  getSourceTypeIcon: (type: string) => string
}

export interface CategoryDetailsPanelEmits {
  (e: 'update:selectedTags', tags: string[]): void
  (e: 'update:matchMode', mode: 'all' | 'any' | null): void
  (e: 'assign-all'): void
}

defineProps<CategoryDetailsPanelProps>()
const emit = defineEmits<CategoryDetailsPanelEmits>()
</script>

<style scoped>
.sources-result-list {
  max-height: 350px;
  overflow-y: auto;
}
</style>
