<template>
  <v-dialog
    v-model="modelValue"
    :max-width="DIALOG_SIZES.XL"
    role="dialog"
    :aria-labelledby="titleId"
  >
    <v-card>
      <v-card-title :id="titleId" class="d-flex align-center">
        <v-icon class="mr-2" aria-hidden="true">mdi-database-outline</v-icon>
        {{ t('categories.dialog.sourcesFor') }} {{ category?.name }}
        <v-chip color="primary" size="small" class="ml-2">
          {{ total }} {{ t('categories.crawler.sourcesCount') }}
        </v-chip>
      </v-card-title>
      <v-card-text>
        <!-- Category Summary -->
        <v-alert type="info" variant="tonal" density="compact" class="mb-4">
          <div class="text-body-2">{{ category?.purpose }}</div>
        </v-alert>

        <!-- Search -->
        <v-text-field
          v-model="searchModel"
          :label="t('categories.dialog.searchSources')"
          prepend-inner-icon="mdi-magnify"
          variant="outlined"
          density="compact"
          clearable
          class="mb-4"
        ></v-text-field>

        <!-- Sources Table -->
        <v-data-table-server
          v-model:page="pageModel"
          v-model:items-per-page="perPageModel"
          :headers="headers"
          :items="sources"
          :items-length="total"
          :loading="loading"
          :no-data-text="noDataText"
          class="sources-table"
        >
          <template #item.name="{ item }">
            <div class="d-flex align-center">
              <v-avatar :color="getStatusColor(item.status)" size="36">
                <v-icon size="small" :color="getContrastColor(getStatusColor(item.status))">
                  {{ getSourceTypeIcon(item.source_type) }}
                </v-icon>
              </v-avatar>
              <div class="ml-3">
                <div class="text-body-2 font-weight-medium">{{ item.name }}</div>
                <div class="text-caption text-medium-emphasis">{{ item.base_url || '-' }}</div>
              </div>
            </div>
          </template>
          <template #item.status="{ item }">
            <v-chip size="x-small" :color="getStatusColor(item.status)">
              {{ item.status || '-' }}
            </v-chip>
          </template>
          <template #item.document_count="{ item }">
            <v-chip size="x-small" color="info" variant="outlined">
              {{ item.document_count || 0 }} {{ t('categories.dialog.docs') }}
            </v-chip>
          </template>
          <template #item.actions="{ item }">
            <v-btn
              icon="mdi-open-in-new"
              size="x-small"
              variant="tonal"
              :href="item.base_url"
              target="_blank"
              :title="t('categories.dialog.openUrl')"
            ></v-btn>
          </template>
        </v-data-table-server>

        <!-- Statistics -->
        <v-divider class="my-4"></v-divider>
        <v-row>
          <v-col cols="3">
            <div class="text-center">
              <div class="text-h5 text-primary">{{ stats.total }}</div>
              <div class="text-caption">{{ t('categories.stats.total') }}</div>
            </div>
          </v-col>
          <v-col cols="3">
            <div class="text-center">
              <div class="text-h5 text-success">{{ stats.active }}</div>
              <div class="text-caption">{{ t('categories.stats.active') }}</div>
            </div>
          </v-col>
          <v-col cols="3">
            <div class="text-center">
              <div class="text-h5 text-warning">{{ stats.pending }}</div>
              <div class="text-caption">{{ t('categories.stats.pending') }}</div>
            </div>
          </v-col>
          <v-col cols="3">
            <div class="text-center">
              <div class="text-h5 text-error">{{ stats.error }}</div>
              <div class="text-caption">{{ t('categories.stats.error') }}</div>
            </div>
          </v-col>
        </v-row>
      </v-card-text>
      <v-card-actions>
        <v-btn
          color="primary"
          variant="tonal"
          prepend-icon="mdi-filter"
          @click="$emit('navigateToSources')"
        >
          {{ t('categories.dialog.showAllInSourcesView') }}
        </v-btn>
        <v-spacer></v-spacer>
        <v-btn
          variant="tonal"
          :aria-label="t('common.close')"
          @click="modelValue = false"
        >
          {{ t('common.close') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { DIALOG_SIZES } from '@/config/ui'
import { getContrastColor } from '@/composables/useColorHelpers'
import { useStatusColors } from '@/composables'

// Types
interface Source {
  id: string
  name: string
  base_url?: string
  status?: string
  source_type?: string
  document_count?: number
  last_crawled_at?: string
  is_assigned?: boolean
}

interface Category {
  id: string
  name: string
  purpose?: string
}

interface Stats {
  total: number
  active: number
  pending: number
  error: number
}

const modelValue = defineModel<boolean>()

// Props
const props = defineProps<{
  category: Category | null
  sources: Source[]
  total: number
  stats: Stats
  loading: boolean
  page: number
  perPage: number
  search: string
}>()

// Emits
const emit = defineEmits<{
  (e: 'navigateToSources'): void
  (e: 'update:page', value: number): void
  (e: 'update:perPage', value: number): void
  (e: 'update:search', value: string): void
}>()

// Accessibility
const titleId = `sources-dialog-title-${Math.random().toString(36).slice(2, 9)}`

const { t } = useI18n()
const { getStatusColor } = useStatusColors()

// Local search with debounce
const localSearch = ref(props.search)
let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null

// Sync local search when prop changes externally
watch(() => props.search, (newVal) => {
  if (newVal !== localSearch.value) {
    localSearch.value = newVal
  }
})

// Debounced emit on local search change
watch(localSearch, (newVal) => {
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
  searchDebounceTimer = setTimeout(() => {
    emit('update:search', newVal)
  }, 300)
})

// Cleanup on unmount
onUnmounted(() => {
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
})

const searchModel = computed({
  get: () => localSearch.value,
  set: (value: string) => { localSearch.value = value },
})

const pageModel = computed({
  get: () => props.page,
  set: (value: number) => emit('update:page', value),
})

const perPageModel = computed({
  get: () => props.perPage,
  set: (value: number) => emit('update:perPage', value),
})

const headers = computed(() => [
  { title: t('common.name'), key: 'name', sortable: false },
  { title: t('common.status'), key: 'status', sortable: false, width: '120px' },
  { title: t('categories.dialog.docs'), key: 'document_count', sortable: false, width: '120px' },
  { title: t('common.actions'), key: 'actions', sortable: false, align: 'end' as const, width: '80px' },
])

const noDataText = computed(() => {
  if (props.search) {
    return `${t('categories.dialog.noSourcesSearch')} "${props.search}"`
  }
  return t('categories.dialog.noSources')
})

// Helper functions - getStatusColor now from useStatusColors composable

function getSourceTypeIcon(sourceType?: string): string {
  const icons: Record<string, string> = {
    website: 'mdi-web',
    api: 'mdi-api',
    rss: 'mdi-rss',
    sharepoint: 'mdi-microsoft-sharepoint',
  }
  return icons[sourceType?.toLowerCase() || ''] || 'mdi-web'
}
</script>

<style scoped>
.sources-table :deep(.v-data-table__wrapper) {
  max-height: 400px;
}
</style>
