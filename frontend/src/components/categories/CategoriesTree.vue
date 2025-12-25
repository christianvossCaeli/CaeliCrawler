<template>
  <v-card>
    <v-data-table
      :headers="headers"
      :items="categories"
      :loading="loading"
      :items-per-page="20"
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
            icon="mdi-database-outline"
            size="small"
            variant="tonal"
            color="primary"
            :title="$t('categories.actions.viewSources')"
            :aria-label="$t('categories.actions.viewSources')"
            @click="emit('view-sources', item)"
          />
          <v-btn
            icon="mdi-pencil"
            size="small"
            variant="tonal"
            :title="$t('common.edit')"
            :aria-label="$t('common.edit')"
            @click="emit('edit', item)"
          />
          <v-btn
            icon="mdi-play"
            size="small"
            variant="tonal"
            color="success"
            :title="$t('categories.actions.startCrawl')"
            :aria-label="$t('categories.actions.startCrawl')"
            @click="emit('start-crawl', item)"
          />
          <v-btn
            icon="mdi-view-dashboard-variant"
            size="small"
            variant="tonal"
            color="info"
            :title="$t('categories.actions.createSummary')"
            :aria-label="$t('categories.actions.createSummary')"
            @click="emit('create-summary', item)"
          />
          <v-btn
            icon="mdi-refresh"
            size="small"
            variant="tonal"
            color="warning"
            :title="$t('categories.actions.reanalyze')"
            :aria-label="$t('categories.actions.reanalyze')"
            @click="emit('reanalyze', item)"
          />
          <v-btn
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
    </v-data-table>
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
}

export interface CategoriesTreeEmits {
  (e: 'edit', category: Category): void
  (e: 'delete', category: Category): void
  (e: 'view-sources', category: Category): void
  (e: 'start-crawl', category: Category): void
  (e: 'create-summary', category: Category): void
  (e: 'reanalyze', category: Category): void
}

const props = defineProps<CategoriesTreeProps>()
const emit = defineEmits<CategoriesTreeEmits>()

const { t } = useI18n()

const headers = computed(() => [
  { title: t('categories.columns.name'), key: 'name' },
  { title: t('categories.columns.purpose'), key: 'purpose', maxWidth: '300px' },
  { title: t('categories.columns.languages') },
  { title: t('categories.columns.status'), key: 'is_active' },
  { title: t('categories.columns.sources'), key: 'source_count' },
  { title: t('categories.columns.documents'), key: 'document_count' },
  { title: t('categories.columns.actions'), key: 'actions', sortable: false, align: 'end' as const },
])

const getLanguageFlag = (code: string): string => {
  const lang = props.languageOptions.find(l => l.code === code)
  return lang?.flag || code.toUpperCase()
}
</script>

<style scoped>
.table-actions {
  white-space: nowrap;
}
</style>
