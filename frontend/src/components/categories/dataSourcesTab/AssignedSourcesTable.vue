<template>
  <v-card variant="outlined" class="mb-4">
    <!-- Debug Panel - TODO: Remove after debugging -->
    <v-alert type="info" density="compact" class="ma-2">
      <div><strong>DEBUG:</strong> sources={{ sources.length }}, total={{ total }}, loading={{ loading }}</div>
    </v-alert>

    <v-card-title class="text-subtitle-1">
      <v-icon start color="success">mdi-link-variant</v-icon>
      {{ $t('categories.dataSourcesTab.assignedSources') }}
      <v-chip v-if="total" size="small" color="success" class="ml-2">
        {{ total }}
      </v-chip>
    </v-card-title>
    <v-card-text>
      <!-- Search and Filter Row -->
      <v-row class="mb-3">
        <v-col cols="12" md="6">
          <v-text-field
            v-model="localSearch"
            :label="$t('categories.dataSourcesTab.searchAssigned')"
            prepend-inner-icon="mdi-magnify"
            variant="outlined"
            density="compact"
            clearable
            :aria-label="$t('categories.dataSourcesTab.searchAssigned')"
            @update:model-value="debouncedSearch"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-combobox
            v-model="localTagFilter"
            :items="availableTags"
            :label="$t('categories.dataSourcesTab.filterByTags')"
            prepend-inner-icon="mdi-tag-multiple"
            variant="outlined"
            density="compact"
            multiple
            chips
            closable-chips
            clearable
            :aria-label="$t('categories.dataSourcesTab.filterByTagsAssigned')"
            @update:model-value="handleTagFilterChange"
          />
        </v-col>
      </v-row>

      <!-- Table -->
      <v-data-table-server
        v-model:page="localPage"
        v-model:items-per-page="localPerPage"
        :headers="headers"
        :items="sources"
        :items-length="total"
        :loading="loading"
        :items-per-page-options="ITEMS_PER_PAGE_OPTIONS"
        item-value="id"
        density="compact"
        :aria-label="$t('categories.dataSourcesTab.assignedSources')"
        @update:page="handlePageChange"
        @update:items-per-page="handlePerPageChange"
      >
        <template #item.name="{ item }">
          <div class="d-flex align-center">
            <v-avatar :color="props.getStatusColor(item.status)" size="32">
              <v-icon size="x-small">{{ props.getSourceTypeIcon(item.source_type) }}</v-icon>
            </v-avatar>
            <div class="ml-2">
              <div class="text-body-2">{{ item.name }}</div>
              <div class="text-caption text-truncate" style="max-width: 200px">{{ item.base_url }}</div>
            </div>
          </div>
        </template>
        <template #item.status="{ item }">
          <v-chip size="x-small" :color="props.getStatusColor(item.status)">{{ item.status }}</v-chip>
        </template>
        <template #item.tags="{ item }">
          <div class="d-flex flex-wrap ga-1">
            <v-chip
              v-for="tag in (item.tags || []).slice(0, MAX_VISIBLE_TAGS)"
              :key="tag"
              size="x-small"
              color="primary"
              variant="outlined"
            >
              {{ tag }}
            </v-chip>
            <v-chip
              v-if="(item.tags || []).length > MAX_VISIBLE_TAGS"
              size="x-small"
              color="grey"
            >
              +{{ (item.tags || []).length - MAX_VISIBLE_TAGS }}
            </v-chip>
          </div>
        </template>
        <template #item.actions="{ item }">
          <v-btn
            icon="mdi-link-off"
            size="x-small"
            variant="text"
            color="error"
            :title="$t('categories.dataSourcesTab.unassign')"
            :aria-label="$t('categories.dataSourcesTab.unassign') + ': ' + item.name"
            @click="confirmUnassign(item)"
          />
        </template>
        <template #no-data>
          <div class="text-center py-4 text-medium-emphasis">
            {{ $t('categories.dataSourcesTab.noAssignedSources') }}
          </div>
        </template>
      </v-data-table-server>
    </v-card-text>

    <!-- Unassign Confirmation Dialog -->
    <v-dialog v-model="unassignDialog" max-width="400" role="alertdialog">
      <v-card>
        <v-card-title class="text-h6">
          {{ $t('categories.dataSourcesTab.unassignConfirmTitle') }}
        </v-card-title>
        <v-card-text>
          {{ $t('categories.dataSourcesTab.unassignConfirmMessage', { name: sourceToUnassign?.name }) }}
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="unassignDialog = false">
            {{ $t('common.cancel') }}
          </v-btn>
          <v-btn color="error" variant="tonal" @click="executeUnassign">
            {{ $t('categories.dataSourcesTab.unassign') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useDebounce } from '@/composables/useDebounce'
import type { CategorySource } from '@/types/category'

interface Props {
  sources?: CategorySource[]
  total?: number
  loading?: boolean
  page?: number
  perPage?: number
  search?: string
  tagFilter?: string[]
  availableTags?: string[]
  getStatusColor: (status?: string) => string
  getSourceTypeIcon: (type?: string) => string
}

interface Emits {
  (e: 'update:page', page: number): void
  (e: 'update:perPage', perPage: number): void
  (e: 'update:search', search: string): void
  (e: 'update:tagFilter', tags: string[]): void
  (e: 'unassign', sourceId: string): void
}

const props = withDefaults(defineProps<Props>(), {
  sources: () => [],
  total: 0,
  loading: false,
  page: 1,
  perPage: 25,
  search: '',
  tagFilter: () => [],
  availableTags: () => [],
})

const emit = defineEmits<Emits>()

// === Constants ===
const SEARCH_DEBOUNCE_MS = 300
const ITEMS_PER_PAGE_OPTIONS = [10, 25, 50]
const MAX_VISIBLE_TAGS = 2

const { t } = useI18n()

// Local state for two-way binding
const localPage = ref(props.page)
const localPerPage = ref(props.perPage)
const localSearch = ref(props.search)
const localTagFilter = ref<string[]>(props.tagFilter)

// Unassign dialog state
const unassignDialog = ref(false)
const sourceToUnassign = ref<CategorySource | null>(null)

// Sync with props
watch(() => props.page, (v) => { localPage.value = v })
watch(() => props.perPage, (v) => { localPerPage.value = v })
watch(() => props.search, (v) => { localSearch.value = v })
watch(() => props.tagFilter, (v) => { localTagFilter.value = v || [] })

// Computed values to ensure reactivity
const sources = computed(() => props.sources ?? [])
const total = computed(() => props.total ?? 0)
const loading = computed(() => props.loading ?? false)
const availableTags = computed(() => props.availableTags ?? [])

// Table headers
const headers = computed(() => [
  { title: t('sources.columns.name'), key: 'name', sortable: false },
  { title: t('sources.columns.status'), key: 'status', sortable: false, width: '100px' },
  { title: t('sources.sidebar.tags'), key: 'tags', sortable: false, width: '150px' },
  { title: '', key: 'actions', sortable: false, width: '60px', align: 'end' as const },
])

// Methods
const debouncedSearch = useDebounce((value: string | null) => {
  emit('update:search', value || '')
}, SEARCH_DEBOUNCE_MS)

const handleTagFilterChange = (tags: string[]) => {
  emit('update:tagFilter', tags)
}

const handlePageChange = (page: number) => {
  emit('update:page', page)
}

const handlePerPageChange = (perPage: number) => {
  emit('update:perPage', perPage)
}

const confirmUnassign = (source: CategorySource) => {
  sourceToUnassign.value = source
  unassignDialog.value = true
}

const executeUnassign = () => {
  if (sourceToUnassign.value) {
    emit('unassign', sourceToUnassign.value.id)
  }
  unassignDialog.value = false
  sourceToUnassign.value = null
}
</script>
