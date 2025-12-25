<template>
  <v-data-table-server
    :headers="tableHeaders"
    :items="entities"
    :items-length="totalEntities"
    :loading="loading"
    :items-per-page="itemsPerPage"
    :page="currentPage"
    @update:options="handleOptionsUpdate"
    @click:row="(_event: Event, { item }: { item: any }) => $emit('entity-click', item)"
    class="cursor-pointer"
  >
    <template v-slot:item.name="{ item }">
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

    <template v-slot:item.hierarchy_path="{ item }">
      <span class="text-medium-emphasis-darken-1 text-caption">{{ item.hierarchy_path || '-' }}</span>
    </template>

    <template v-slot:item.filled_facets="{ item }">
      <v-chip size="small" color="secondary" variant="tonal">
        <v-icon start size="small">mdi-tag-check</v-icon>
        {{ item.facet_count || 0 }}
      </v-chip>
    </template>

    <template v-slot:item.facet_count="{ item }">
      <v-chip size="small" color="primary" variant="tonal">
        <v-icon start size="small">mdi-tag-multiple</v-icon>
        {{ (item.facet_count || 0) + (item.core_attributes ? Object.keys(item.core_attributes).length : 0) }}
      </v-chip>
    </template>

    <template v-slot:item.relation_count="{ item }">
      <v-chip size="small" color="info" variant="tonal">
        <v-icon start size="small">mdi-sitemap</v-icon>
        {{ (item.relation_count || 0) + (item.children_count || 0) + (item.parent_id ? 1 : 0) }}
      </v-chip>
    </template>

    <template v-slot:item.facet_summary="{ item }">
      <div class="d-flex ga-1 flex-wrap">
        <v-tooltip
          v-for="facet in getTopFacetCounts(item)"
          :key="facet.slug"
          location="top"
        >
          <template v-slot:activator="{ props }">
            <v-chip
              v-bind="props"
              size="x-small"
              :color="facet.color"
              variant="tonal"
            >
              <v-icon start size="x-small" :icon="facet.icon"></v-icon>
              {{ facet.count }}
            </v-chip>
          </template>
          <span>{{ facet.name }}: {{ facet.count }}</span>
        </v-tooltip>
      </div>
    </template>

    <template v-slot:item.actions="{ item }">
      <div class="table-actions d-flex justify-end ga-1">
        <v-btn
          icon="mdi-eye"
          size="small"
          variant="tonal"
          color="primary"
          :title="t('common.details')"
          :aria-label="t('common.details')"
          @click.stop="$emit('entity-click', item)"
        ></v-btn>
        <v-btn
          icon="mdi-pencil"
          size="small"
          variant="tonal"
          :title="t('common.edit')"
          :aria-label="t('common.edit')"
          @click.stop="$emit('entity-edit', item)"
        ></v-btn>
        <v-btn
          icon="mdi-delete"
          size="small"
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

interface Props {
  entities: any[]
  totalEntities: number
  loading: boolean
  itemsPerPage: number
  currentPage: number
  currentEntityType: any
  flags: any
  getTopFacetCounts: (entity: any) => Array<{ slug: string; name: string; icon: string; color: string; count: number }>
}

interface Emits {
  (e: 'update:items-per-page', value: number): void
  (e: 'update:current-page', value: number): void
  (e: 'entity-click', entity: any): void
  (e: 'entity-edit', entity: any): void
  (e: 'entity-delete', entity: any): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const { t } = useI18n()

const tableHeaders = computed(() => {
  const headers: Array<{ title: string; key: string; align?: 'start' | 'center' | 'end'; sortable?: boolean }> = [
    { title: t('common.name'), key: 'name' },
  ]

  if (props.flags.entityHierarchyEnabled && props.currentEntityType?.supports_hierarchy) {
    headers.push({ title: t('entities.path'), key: 'hierarchy_path' })
  }

  headers.push(
    { title: t('entities.filledFacets'), key: 'filled_facets', align: 'center' },
    { title: t('entities.properties'), key: 'facet_count', align: 'center' },
    { title: t('entities.connections', 'Verknüpfungen'), key: 'relation_count', align: 'center' },
    { title: t('entities.summary'), key: 'facet_summary', sortable: false },
    { title: t('common.actions'), key: 'actions', sortable: false, align: 'end' },
  )

  return headers
})

function handleOptionsUpdate(options: { page: number; itemsPerPage: number }) {
  if (options.itemsPerPage !== props.itemsPerPage) {
    emit('update:items-per-page', options.itemsPerPage)
  }
  emit('update:current-page', options.page)
}
</script>

<style scoped>
.cursor-pointer :deep(tbody tr) {
  cursor: pointer;
}
.cursor-pointer :deep(tbody tr:hover) {
  background-color: rgba(var(--v-theme-primary), 0.1);
}
</style>
