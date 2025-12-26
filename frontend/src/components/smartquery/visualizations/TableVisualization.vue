<template>
  <div class="table-visualization">
    <v-data-table
      :headers="tableHeaders"
      :items="tableItems"
      :items-per-page="15"
      :sort-by="sortBy"
      density="comfortable"
      class="elevation-0 clickable-rows"
      hover
      role="table"
      :aria-label="t('visualization.tableLabel')"
      :aria-rowcount="tableItems.length"
      @click:row="onRowClick"
    >
      <!-- Entity Name Column with Link -->
      <template #item.entity_name="{ item }">
        <router-link
          v-if="item.entity_id"
          :to="`/entity/${item.entity_id}`"
          class="text-primary text-decoration-none font-weight-medium"
        >
          {{ item.entity_name }}
        </router-link>
        <span v-else class="font-weight-medium">{{ item.entity_name }}</span>
      </template>

      <!-- Name Column with Link (alternative for summaries) -->
      <template #item.name="{ item }">
        <router-link
          v-if="item.entity_id"
          :to="`/entity/${item.entity_id}`"
          class="text-primary text-decoration-none font-weight-medium"
        >
          {{ item.name }}
        </router-link>
        <span v-else class="font-weight-medium">{{ item.name }}</span>
      </template>

      <!-- Dynamic Facet Columns -->
      <template v-for="col in facetColumns" :key="col.key" #[`item.${col.key}`]="{ item }">
        <span :class="getValueClass(col.type)">
          {{ formatCellValue(item, col) }}
        </span>
      </template>

      <!-- Tags Column -->
      <template #item.tags="{ item }">
        <div v-if="item.tags?.length" class="d-flex flex-wrap gap-1">
          <v-chip
            v-for="tag in item.tags.slice(0, 3)"
            :key="tag"
            size="x-small"
            variant="tonal"
            color="primary"
          >
            {{ tag }}
          </v-chip>
          <v-chip v-if="item.tags.length > 3" size="x-small" variant="text">
            +{{ item.tags.length - 3 }}
          </v-chip>
        </div>
        <span v-else class="text-medium-emphasis">-</span>
      </template>

      <!-- No data slot -->
      <template #no-data>
        <div class="text-center py-8">
          <v-icon size="48" color="grey-lighten-1">mdi-table-off</v-icon>
          <p class="text-body-2 text-medium-emphasis mt-2">
            {{ t('smartQuery.visualization.noData') }}
          </p>
        </div>
      </template>
    </v-data-table>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import type { VisualizationConfig, VisualizationColumn, ColumnType } from './types'
import { getNestedValue, formatValue } from './types'

const props = defineProps<{
  data: Record<string, unknown>[]
  config?: VisualizationConfig
}>()
const { t } = useI18n()
const router = useRouter()

// Build table headers from config or auto-detect
const tableHeaders = computed(() => {
  if (props.config?.columns && props.config.columns.length > 0) {
    return props.config.columns.map(col => ({
      title: col.label,
      key: col.key,
      sortable: col.sortable !== false,
      align: col.align || 'start',
      width: col.width,
    }))
  }

  // Auto-detect from data
  if (!props.data || props.data.length === 0) return []

  const sample = props.data[0]
  const headers: Array<{ title: string; key: string; sortable?: boolean; align?: string; width?: string }> = []

  // Always add name column first if present (entity_name or name)
  if ('entity_name' in sample) {
    headers.push({
      title: t('smartQuery.visualization.columns.name'),
      key: 'entity_name',
      sortable: true,
    })
  } else if ('name' in sample) {
    headers.push({
      title: t('smartQuery.visualization.columns.name'),
      key: 'name',
      sortable: true,
    })
  }

  // Add facet columns
  if (sample.facets) {
    for (const [facetKey, facetValue] of Object.entries(sample.facets)) {
      const isNumeric = typeof (facetValue as { value?: unknown })?.value === 'number'
      headers.push({
        title: formatFacetLabel(facetKey),
        key: `facets.${facetKey}.value`,
        sortable: true,
        align: isNumeric ? 'end' : 'start',
      })
    }
  }

  // Add admin_level_1 if present
  if ('admin_level_1' in sample && sample.admin_level_1) {
    headers.push({
      title: t('smartQuery.visualization.columns.region'),
      key: 'admin_level_1',
      sortable: true,
    })
  }

  // Add tags if present
  if ('tags' in sample && Array.isArray(sample.tags)) {
    headers.push({
      title: t('smartQuery.visualization.columns.tags'),
      key: 'tags',
      sortable: false,
    })
  }

  return headers
})

// Extract facet columns for custom rendering
const facetColumns = computed(() => {
  if (props.config?.columns) {
    return props.config.columns.filter(col => col.key?.startsWith('facets.'))
  }

  // Auto-detect
  if (!props.data || props.data.length === 0) return []

  const sample = props.data[0]
  const columns: VisualizationColumn[] = []

  if (sample.facets) {
    for (const [facetKey, facetValue] of Object.entries(sample.facets)) {
      const isNumeric = typeof (facetValue as { value?: unknown })?.value === 'number'
      columns.push({
        key: `facets.${facetKey}.value`,
        label: formatFacetLabel(facetKey),
        type: isNumeric ? 'number' : 'text',
      })
    }
  }

  return columns
})

// Flatten nested data for v-data-table
const tableItems = computed(() => {
  return props.data.map(item => {
    const flat: Record<string, unknown> = { ...item }

    // Ensure entity_id is always available (could be named differently in source)
    if (!flat.entity_id && item.id) {
      flat.entity_id = item.id
    }

    // Flatten facets for direct access
    if (item.facets) {
      for (const [facetKey, facetValue] of Object.entries(item.facets)) {
        if (typeof facetValue === 'object' && facetValue !== null) {
          const fv = facetValue as { value?: unknown; recorded_at?: unknown }
          flat[`facets.${facetKey}.value`] = fv.value
          flat[`facets.${facetKey}.recorded_at`] = fv.recorded_at
        } else {
          flat[`facets.${facetKey}.value`] = facetValue
        }
      }
    }

    return flat
  })
})

// Sort configuration
const sortBy = computed(() => {
  if (props.config?.sort_column) {
    return [{
      key: props.config.sort_column,
      order: props.config.sort_order || 'asc',
    }]
  }
  return []
})

function formatFacetLabel(slug: string): string {
  return slug
    .replace(/-/g, ' ')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
}

function formatCellValue(item: Record<string, unknown>, col: VisualizationColumn): string {
  const value = getNestedValue(item, col.key) ?? item[col.key]
  return formatValue(value, col.type, col.format)
}

function getValueClass(type: ColumnType): string {
  if (type === 'number' || type === 'currency' || type === 'percent') {
    return 'text-end font-weight-medium'
  }
  return ''
}

function onRowClick(event: Event, { item }: { item: Record<string, unknown> }) {
  // Don't navigate if clicking on an existing link (entity_name column has router-link)
  if ((event.target as HTMLElement).closest('a')) {
    return
  }

  const entityId = item.entity_id
  if (entityId) {
    router.push(`/entity/${entityId}`)
  }
}
</script>

<style scoped>
.table-visualization {
  border-radius: 8px;
  overflow: hidden;
}

.table-visualization :deep(.v-data-table) {
  background: transparent;
}

.table-visualization :deep(.v-data-table-header) {
  background: rgba(var(--v-theme-surface-variant), 0.3);
}

.table-visualization :deep(.v-data-table__tr:hover) {
  background: rgba(var(--v-theme-primary), 0.04);
}

.clickable-rows :deep(.v-data-table__tr) {
  cursor: pointer;
}

.clickable-rows :deep(.v-data-table__tr:hover) {
  background: rgba(var(--v-theme-primary), 0.08);
}
</style>
