<template>
  <v-card>
    <v-data-table-server
      v-model:items-per-page="itemsPerPageModel"
      v-model:sort-by="sortByModel"
      :headers="headers"
      :items="categories"
      :items-length="total"
      :loading="loading"
      :page="page"
      :row-props="getRowProps"
      @update:options="handleOptionsUpdate"
    >
      <template #item.languages="{ item }">
        <span
          v-for="lang in (item.languages || ['de'])"
          :key="lang"
          :title="lang"
          class="mr-1"
        >
          {{ getLanguageFlag(lang) }}
        </span>
      </template>

      <template #item.is_active="{ item }">
        <v-chip
          :color="item.is_active ? 'success' : 'grey'"
          size="small"
        >
          {{ item.is_active ? $t('categories.statusOptions.active') : $t('categories.statusOptions.inactive') }}
        </v-chip>
      </template>

      <template #item.source_count="{ item }">
        <v-chip color="primary" size="small">
          {{ item.source_count }}
        </v-chip>
      </template>

      <template #item.document_count="{ item }">
        <v-chip color="info" size="small">
          {{ item.document_count }}
        </v-chip>
      </template>

      <template #item.actions="{ item }">
        <div class="table-actions d-flex justify-end ga-1">
          <v-btn
            v-if="canEdit"
            icon="mdi-database-outline"
            size="small"
            variant="tonal"
            color="primary"
            :title="$t('categories.actions.viewSources')"
            :aria-label="$t('categories.actions.viewSources')"
            @click="emit('view-sources', item)"
          />
          <v-btn
            v-if="canEdit"
            icon="mdi-pencil"
            size="small"
            variant="tonal"
            :title="$t('common.edit')"
            :aria-label="$t('common.edit')"
            @click="emit('edit', item)"
          />
          <v-btn
            v-if="canEdit"
            icon="mdi-play"
            size="small"
            variant="tonal"
            color="success"
            :title="$t('categories.actions.startCrawl')"
            :aria-label="$t('categories.actions.startCrawl')"
            @click="emit('start-crawl', item)"
          />
          <v-btn
            v-if="canEdit"
            icon="mdi-view-dashboard-variant"
            size="small"
            variant="tonal"
            color="info"
            :title="$t('categories.actions.createSummary')"
            :aria-label="$t('categories.actions.createSummary')"
            @click="emit('create-summary', item)"
          />
          <v-btn
            v-if="canAdmin"
            icon="mdi-refresh"
            size="small"
            variant="tonal"
            color="warning"
            :title="$t('categories.actions.reanalyze')"
            :aria-label="$t('categories.actions.reanalyze')"
            @click="emit('reanalyze', item)"
          />
          <v-btn
            v-if="canAdmin"
            icon="mdi-delete"
            size="small"
            variant="tonal"
            color="error"
            :title="$t('common.delete')"
            :aria-label="$t('common.delete')"
            @click="emit('delete', item)"
          />
        </div>
      </template>
    </v-data-table-server>
  </v-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Category } from '@/composables/useCategoriesView'

export interface CategoriesTreeProps {
  categories: Category[]
  loading: boolean
  languageOptions: Array<{ code: string; name: string; flag: string }>
  total: number
  page: number
  itemsPerPage: number
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
  canEdit?: boolean
  canAdmin?: boolean
}

export interface CategoriesTreeEmits {
  (e: 'edit', category: Category): void
  (e: 'delete', category: Category): void
  (e: 'view-sources', category: Category): void
  (e: 'start-crawl', category: Category): void
  (e: 'create-summary', category: Category): void
  (e: 'reanalyze', category: Category): void
  (e: 'update:options', options: { page: number; itemsPerPage: number; sortBy?: string; sortOrder?: 'asc' | 'desc' }): void
}

const props = withDefaults(defineProps<CategoriesTreeProps>(), {
  canEdit: true,
  canAdmin: true,
  sortBy: 'name',
  sortOrder: 'asc',
})
const emit = defineEmits<CategoriesTreeEmits>()

const { t } = useI18n()

// v-model for items per page
const itemsPerPageModel = computed({
  get: () => props.itemsPerPage,
  set: (value: number) => emit('update:options', { page: 1, itemsPerPage: value, sortBy: props.sortBy, sortOrder: props.sortOrder }),
})

// v-model for sort-by (Vuetify expects array format)
const sortByModel = computed({
  get: () => props.sortBy ? [{ key: props.sortBy, order: props.sortOrder }] : [],
  set: (value: Array<{ key: string; order: string }>) => {
    const sort = value[0]
    emit('update:options', {
      page: 1,
      itemsPerPage: props.itemsPerPage,
      sortBy: sort?.key || 'name',
      sortOrder: (sort?.order as 'asc' | 'desc') || 'asc',
    })
  },
})

// Handle pagination options update from data table
const handleOptionsUpdate = (options: { page: number; itemsPerPage: number; sortBy?: Array<{ key: string; order: string }> }) => {
  const sort = options.sortBy?.[0]
  emit('update:options', {
    page: options.page,
    itemsPerPage: options.itemsPerPage,
    sortBy: sort?.key || props.sortBy,
    sortOrder: (sort?.order as 'asc' | 'desc') || props.sortOrder,
  })
}

const headers = computed(() => [
  { title: t('categories.columns.name'), key: 'name', sortable: true },
  { title: t('categories.columns.purpose'), key: 'purpose', maxWidth: '300px', sortable: true },
  { title: t('categories.columns.languages'), key: 'languages', sortable: false },
  { title: t('categories.columns.status'), key: 'is_active', sortable: true },
  { title: t('categories.columns.sources'), key: 'source_count', sortable: false },
  { title: t('categories.columns.documents'), key: 'document_count', sortable: false },
  { title: t('categories.columns.actions'), key: 'actions', sortable: false, align: 'end' as const },
])

const getLanguageFlag = (code: string): string => {
  const lang = props.languageOptions.find(l => l.code === code)
  return lang?.flag || code.toUpperCase()
}

// Row styling based on category status
const getRowProps = ({ item }: { item: Category }) => {
  return {
    class: item.is_active ? '' : 'category-inactive',
  }
}
</script>

<style scoped>
.table-actions {
  white-space: nowrap;
}
</style>

<style>
/* Inactive categories styling - needs to be non-scoped for row styling */
.category-inactive {
  opacity: 0.5;
  background-color: rgba(0, 0, 0, 0.03);
}

.category-inactive td {
  color: rgba(var(--v-theme-on-surface), 0.5) !important;
}
</style>
