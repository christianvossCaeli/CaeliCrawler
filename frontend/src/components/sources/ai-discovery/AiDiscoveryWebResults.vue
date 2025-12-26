<template>
  <v-card v-if="sources.length > 0" variant="outlined">
    <v-data-table
      :model-value="selectedUrls"
      :headers="tableHeaders"
      :items="sources"
      item-value="base_url"
      show-select
      density="compact"
      :items-per-page="10"
      @update:model-value="$emit('update:selectedUrls', $event)"
    >
      <template #item.name="{ item }">
        <div class="font-weight-medium">{{ item.name }}</div>
      </template>
      <template #item.base_url="{ item }">
        <a
          :href="item.base_url"
          target="_blank"
          rel="noopener noreferrer"
          class="text-decoration-none"
        >
          {{ truncateUrl(item.base_url) }}
          <v-icon size="x-small" class="ml-1">mdi-open-in-new</v-icon>
        </a>
      </template>
      <template #item.tags="{ item }">
        <v-chip-group>
          <v-chip
            v-for="tag in item.tags.slice(0, 4)"
            :key="tag"
            size="x-small"
            variant="outlined"
          >
            {{ tag }}
          </v-chip>
          <v-chip v-if="item.tags.length > 4" size="x-small" variant="text">
            +{{ item.tags.length - 4 }}
          </v-chip>
        </v-chip-group>
      </template>
      <template #item.confidence="{ item }">
        <v-chip :color="getConfidenceColor(item.confidence)" size="x-small">
          {{ Math.round(item.confidence * 100) }}%
        </v-chip>
      </template>
    </v-data-table>
  </v-card>
  <v-alert v-else type="info" variant="tonal">
    {{ $t('sources.aiDiscovery.noWebSources') }}
  </v-alert>
</template>

<script setup lang="ts">
/**
 * AiDiscoveryWebResults - Display discovered web sources
 *
 * Shows web sources in a selectable data table with confidence indicators.
 */
import type { DiscoverySource } from './types'

interface Props {
  sources: DiscoverySource[]
  selectedUrls: string[]
}

defineProps<Props>()

defineEmits<{
  (e: 'update:selectedUrls', value: string[]): void
}>()

const tableHeaders = [
  { title: 'Name', key: 'name', sortable: true },
  { title: 'URL', key: 'base_url', sortable: true },
  { title: 'Tags', key: 'tags', sortable: false },
  { title: 'Confidence', key: 'confidence', sortable: true, width: '100px' },
]

/** Truncate URL for display */
const truncateUrl = (url: string): string => {
  try {
    const parsed = new URL(url)
    return parsed.hostname + (parsed.pathname !== '/' ? parsed.pathname.slice(0, 20) + '...' : '')
  } catch {
    return url.slice(0, 40) + '...'
  }
}

/** Get color based on confidence score */
const getConfidenceColor = (confidence: number): string => {
  if (confidence >= 0.8) return 'success'
  if (confidence >= 0.6) return 'primary'
  if (confidence >= 0.4) return 'warning'
  return 'error'
}
</script>

<style scoped>
:deep(.v-data-table) {
  font-size: 0.875rem;
}
</style>
