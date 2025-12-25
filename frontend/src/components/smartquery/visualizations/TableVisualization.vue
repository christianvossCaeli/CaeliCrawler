<template>
  <div class="table-visualization">
    <v-data-table
      :headers="tableHeaders"
      :items="tableItems"
      :items-per-page="15"
      :sort-by="sortBy"
      density="comfortable"
      class="elevation-0"
      hover
      role="table"
      :aria-label="t('smartQuery.visualization.tableLabel')"
      :aria-rowcount="tableItems.length"
    >
      <!-- Entity Name Column with Link -->
      <template #item.entity_name="{ item }">
        <router-link
          v-if="item.entity_id"
          :to="`/entities/${item.entity_id}`"
          class="text-primary text-decoration-none font-weight-medium"
        >
          {{ item.entity_name }}
        </router-link>
        <span v-else class="font-weight-medium">{{ item.entity_name }}</span>
      </template>

      <!-- Dynamic Facet Columns -->
      <template v-for="col in facetColumns" :key="col.key" #[`item.${col.key}`]="{ item }">
        <span :class="getValueClass(col.type)">
          {{ formatCellValue(item, col) }}
        </span>
      </template>

      <!-- Tags Column -->
      <template #item.tags="{ item }">
        <div class="d-flex flex-wrap gap-1" v-if="item.tags?.length">
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
import type { VisualizationConfig, VisualizationColumn, ColumnType } from './types'
import { getNestedValue, formatValue } from './types'

const { t } = useI18n()

const props = defineProps<{
  data: Record<string, any>[]
  config?: VisualizationConfig
}>()

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
  const headers: any[] = []

  // Always add entity_name first if present
  if ('entity_name' in sample) {
    headers.push({
      title: t('smartQuery.visualization.columns.name'),
      key: 'entity_name',
      sortable: true,
    })
  }

  // Add facet columns
  if (sample.facets) {
    for (const [facetKey, facetValue] of Object.entries(sample.facets)) {
      const isNumeric = typeof (facetValue as any)?.value === 'number'
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
      const isNumeric = typeof (facetValue as any)?.value === 'number'
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
    const flat: Record<string, any> = { ...item }

    // Flatten facets for direct access
    if (item.facets) {
      for (const [facetKey, facetValue] of Object.entries(item.facets)) {
        if (typeof facetValue === 'object' && facetValue !== null) {
          flat[`facets.${facetKey}.value`] = (facetValue as any).value
          flat[`facets.${facetKey}.recorded_at`] = (facetValue as any).recorded_at
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

function formatCellValue(item: Record<string, any>, col: VisualizationColumn): string {
  const value = getNestedValue(item, col.key) ?? item[col.key]
  return formatValue(value, col.type, col.format)
}

function getValueClass(type: ColumnType): string {
  if (type === 'number' || type === 'currency' || type === 'percent') {
    return 'text-end font-weight-medium'
  }
  return ''
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
</style>
