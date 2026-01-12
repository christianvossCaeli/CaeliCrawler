<template>
  <div role="region" :aria-label="$t('categories.dataSourcesTab.title')">
    <!-- Info for Create mode -->
    <v-alert v-if="!editMode" type="info" variant="tonal" density="compact" class="mb-4">
      {{ $t('categories.dataSourcesTab.createModeInfo') }}
    </v-alert>

    <!-- Direct Source Selection -->
    <DirectSourceSelector
      :selected-sources="directSelectedSources"
      :search-results="sourceSearchResults"
      :searching="searchingDirectSources"
      :assigning="assigning"
      :get-status-color="getStatusColor"
      :get-source-type-icon="getSourceTypeIcon"
      @update:selected-sources="emit('update:directSelectedSources', $event)"
      @search="emit('search-sources', $event)"
      @assign="emit('assign-direct', $event)"
    />

    <!-- Tag Filter Section -->
    <TagFilterSection
      :selected-tags="selectedTags"
      :match-mode="matchMode"
      :available-tags="availableTags"
      @update:selected-tags="emit('update:selectedTags', $event)"
      @update:match-mode="emit('update:matchMode', $event)"
    />

    <!-- Found Sources List (Tag Search Results) -->
    <FoundSourcesList
      :sources="foundSources"
      :loading="loading"
      :assigning="assigning"
      :has-selected-tags="selectedTags.length > 0"
      :get-status-color="getStatusColor"
      :get-source-type-icon="getSourceTypeIcon"
      @assign-all="emit('assign-all')"
    />

    <!-- Assigned Sources Table (Edit mode only) -->
    <v-alert v-if="editMode" type="info" density="compact" class="mb-2">
      <strong>DEBUG CategoryDetailsPanel:</strong> editMode={{ editMode }}, category.id={{ category?.id }}, assignedSources={{ assignedSources?.length ?? 'undefined' }}, total={{ assignedSourcesTotal ?? 'undefined' }}
    </v-alert>
    <template v-if="editMode && category?.id">
      <AssignedSourcesTable
        :sources="assignedSources ?? []"
        :total="assignedSourcesTotal ?? 0"
        :loading="assignedSourcesLoading ?? false"
        :page="assignedSourcesPage ?? 1"
        :per-page="assignedSourcesPerPage ?? 25"
        :search="assignedSourcesSearch ?? ''"
        :tag-filter="assignedSourcesTagFilter ?? []"
        :available-tags="availableTagsInAssigned ?? []"
        :get-status-color="getStatusColor"
        :get-source-type-icon="getSourceTypeIcon"
        @update:page="emit('update:assignedSourcesPage', $event)"
        @update:per-page="emit('update:assignedSourcesPerPage', $event)"
        @update:search="emit('update:assignedSourcesSearch', $event)"
        @update:tag-filter="emit('update:assignedSourcesTagFilter', $event)"
        @unassign="emit('unassign-source', $event)"
      />
    </template>

    <!-- Current assigned count (fallback for non-edit mode) -->
    <v-alert v-if="!editMode && currentSourceCount" type="success" variant="tonal" class="mt-4">
      {{ $t('categories.dataSourcesTab.currentlyAssigned') }}: <strong>{{ currentSourceCount }}</strong> {{ $t('categories.crawler.sourcesCount') }}
    </v-alert>
  </div>
</template>

<script setup lang="ts">
import type { CategorySource, CategoryResponse } from '@/types/category'
import {
  DirectSourceSelector,
  TagFilterSection,
  FoundSourcesList,
  AssignedSourcesTable,
} from './dataSourcesTab'

export interface CategoryDetailsPanelProps {
  // Tag-based search
  selectedTags: string[]
  matchMode: 'all' | 'any'
  availableTags: string[]
  foundSources: CategorySource[]
  loading: boolean
  assigning: boolean
  currentSourceCount?: number
  editMode?: boolean
  category?: CategoryResponse | null
  // Direct source selection
  directSelectedSources?: CategorySource[]
  sourceSearchResults?: CategorySource[]
  searchingDirectSources?: boolean
  // Assigned sources
  assignedSources?: CategorySource[]
  assignedSourcesTotal?: number
  assignedSourcesLoading?: boolean
  assignedSourcesPage?: number
  assignedSourcesPerPage?: number
  assignedSourcesSearch?: string
  assignedSourcesTagFilter?: string[]
  availableTagsInAssigned?: string[]
  // Helpers
  getStatusColor: (status?: string) => string
  getSourceTypeIcon: (type?: string) => string
}

export interface CategoryDetailsPanelEmits {
  (e: 'update:selectedTags', tags: string[]): void
  (e: 'update:matchMode', mode: 'all' | 'any'): void
  (e: 'assign-all'): void
  // Direct selection
  (e: 'search-sources', query: string): void
  (e: 'update:directSelectedSources', sources: CategorySource[]): void
  (e: 'assign-direct', sources: CategorySource[]): void
  // Assigned sources
  (e: 'update:assignedSourcesPage', page: number): void
  (e: 'update:assignedSourcesPerPage', perPage: number): void
  (e: 'update:assignedSourcesSearch', search: string): void
  (e: 'update:assignedSourcesTagFilter', tags: string[]): void
  (e: 'unassign-source', sourceId: string): void
}

withDefaults(defineProps<CategoryDetailsPanelProps>(), {
  directSelectedSources: () => [],
  sourceSearchResults: () => [],
  searchingDirectSources: false,
  assignedSources: () => [],
  assignedSourcesTotal: 0,
  assignedSourcesLoading: false,
  assignedSourcesPage: 1,
  assignedSourcesPerPage: 25,
  assignedSourcesSearch: '',
  assignedSourcesTagFilter: () => [],
  availableTagsInAssigned: () => [],
})

const emit = defineEmits<CategoryDetailsPanelEmits>()
</script>
