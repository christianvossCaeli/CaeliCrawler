<template>
  <v-data-table-server
    v-model="internalSelection"
    :headers="tableHeaders"
    :items="entities"
    :items-length="totalEntities"
    :loading="loading"
    :items-per-page="itemsPerPage"
    :page="currentPage"
    :sort-by="sortBy"
    :show-select="showSelect"
    item-value="id"
    return-object
    class="cursor-pointer"
    @update:options="handleOptionsUpdate"
    @click:row="(_event: Event, { item }: { item: Entity }) => $emit('entity-click', item)"
  >
    <!-- Error / Empty State -->
    <template #no-data>
      <TableErrorState
        v-if="error"
        :title="t('common.loadError')"
        :message="errorMessage || t('errors.generic')"
        :details="errorDetails"
        :retrying="loading"
        @retry="$emit('retry')"
      />
      <EmptyState
        v-else
        icon="mdi-database-search-outline"
        :title="t('entities.noEntities')"
        :description="t('entities.noEntitiesDescription')"
      />
    </template>
    <template #item.name="{ item }">
      <div class="d-flex align-center">
        <v-icon
          class="mr-2"
          :color="currentEntityType?.color || 'primary'"
          :icon="currentEntityType?.icon || 'mdi-folder'"
        ></v-icon>
        <div>
          <strong>{{ item.name }}</strong>
          <div v-if="item.external_id" class="text-caption text-medium-emphasis">
            {{ item.external_id }}
          </div>
        </div>
      </div>
    </template>

    <template #item.hierarchy_path="{ item }">
      <span class="text-medium-emphasis-darken-1 text-caption">{{ item.hierarchy_path || '-' }}</span>
    </template>

    <template #item.facet_count="{ item }">
      <v-chip size="small" color="secondary" variant="tonal">
        <v-icon start size="small">mdi-tag-check</v-icon>
        {{ item.facet_count || 0 }}
      </v-chip>
    </template>

    <template #item.relation_count="{ item }">
      <v-chip size="small" color="info" variant="tonal">
        <v-icon start size="small">mdi-sitemap</v-icon>
        {{ (item.relation_count || 0) + (item.children_count || 0) + (item.parent_id ? 1 : 0) }}
      </v-chip>
    </template>

    <template #item.actions="{ item }">
      <div class="table-actions d-flex justify-end ga-1">
        <v-btn
          icon="mdi-eye"
          size="default"
          variant="tonal"
          color="primary"
          :title="t('common.details')"
          :aria-label="t('common.details')"
          @click.stop="$emit('entity-click', item)"
        ></v-btn>
        <v-btn
          v-if="canEdit"
          icon="mdi-pencil"
          size="default"
          variant="tonal"
          :title="t('common.edit')"
          :aria-label="t('common.edit')"
          @click.stop="$emit('entity-edit', item)"
        ></v-btn>
        <v-btn
          v-if="canEdit"
          icon="mdi-delete"
          size="default"
          variant="tonal"
          color="error"
          :title="t('common.delete')"
          :aria-label="t('common.delete')"
          @click.stop="$emit('entity-delete', item)"
        ></v-btn>
      </div>
    </template>
  </v-data-table-server>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Entity, EntityType } from '@/types/entity'
import { TableErrorState, EmptyState } from '@/components/common'

interface FeatureFlags {
  entityHierarchyEnabled?: boolean
  [key: string]: boolean | undefined
}

interface SortItem {
  key: string
  order: 'asc' | 'desc'
}

interface Props {
  entities: Entity[]
  totalEntities: number
  loading: boolean
  itemsPerPage: number
  currentPage: number
  currentEntityType: EntityType | null
  flags: FeatureFlags
  sortBy?: SortItem[]
  canEdit?: boolean
  /** Whether an error occurred during data loading */
  error?: boolean
  /** User-friendly error message */
  errorMessage?: string
  /** Technical error details */
  errorDetails?: string
  /** Enable bulk selection mode */
  showSelect?: boolean
  /** Currently selected entities */
  selectedEntities?: Entity[]
}

interface Emits {
  (e: 'update:items-per-page', value: number): void
  (e: 'update:current-page', value: number): void
  (e: 'update:sort-by', value: SortItem[]): void
  (e: 'update:selectedEntities', value: Entity[]): void
  (e: 'entity-click', entity: Entity): void
  (e: 'entity-edit', entity: Entity): void
  (e: 'entity-delete', entity: Entity): void
  /** Emitted when user clicks retry after an error */
  (e: 'retry'): void
}

const props = withDefaults(defineProps<Props>(), {
  sortBy: () => [],
  canEdit: true,
  error: false,
  errorMessage: undefined,
  errorDetails: undefined,
  showSelect: false,
  selectedEntities: () => [],
})
const emit = defineEmits<Emits>()

const { t } = useI18n()

const tableHeaders = computed(() => {
  const headers: Array<{ title: string; key: string; align?: 'start' | 'center' | 'end'; sortable?: boolean }> = [
    { title: t('common.name'), key: 'name', sortable: true },
  ]

  if (props.flags.entityHierarchyEnabled && props.currentEntityType?.supports_hierarchy) {
    headers.push({ title: t('entities.path'), key: 'hierarchy_path', sortable: true })
  }

  headers.push(
    { title: t('entities.filledFacets'), key: 'facet_count', align: 'center', sortable: true },
    { title: t('entities.connections', 'Verknüpfungen'), key: 'relation_count', align: 'center', sortable: true },
    { title: t('common.actions'), key: 'actions', sortable: false, align: 'end' },
  )

  return headers
})

function handleOptionsUpdate(options: { page: number; itemsPerPage: number; sortBy: SortItem[] }) {
  if (options.itemsPerPage !== props.itemsPerPage) {
    emit('update:items-per-page', options.itemsPerPage)
  }
  if (JSON.stringify(options.sortBy) !== JSON.stringify(props.sortBy)) {
    emit('update:sort-by', options.sortBy)
  }
  emit('update:current-page', options.page)
}

// Selection handling with v-model pattern
const internalSelection = computed({
  get: () => props.selectedEntities,
  set: (value) => emit('update:selectedEntities', value)
})
</script>

<style scoped>
.cursor-pointer :deep(tbody tr) {
  cursor: pointer;
}
.cursor-pointer :deep(tbody tr:hover) {
  background-color: rgba(var(--v-theme-primary), 0.1);
}
</style>
