<template>
  <div v-if="sources.length > 0">
    <v-card
      v-for="(source, index) in sources"
      :key="index"
      variant="outlined"
      class="mb-4"
    >
      <v-card-title class="d-flex align-center">
        <v-icon color="success" class="mr-2">mdi-api</v-icon>
        {{ source.api_name }}
        <v-chip size="small" color="primary" class="ml-2">{{ source.api_type }}</v-chip>
        <v-spacer />
        <v-chip color="success" size="small">
          {{ source.item_count }} {{ $t('sources.aiDiscovery.itemsFound') }}
        </v-chip>
      </v-card-title>
      <v-card-subtitle>{{ source.api_url }}</v-card-subtitle>
      <v-card-text>
        <!-- Tags -->
        <div class="mb-3">
          <v-chip
            v-for="tag in source.tags"
            :key="tag"
            size="small"
            variant="outlined"
            class="mr-1 mb-1"
          >
            {{ tag }}
          </v-chip>
        </div>

        <!-- Sample Data Preview -->
        <v-expansion-panels variant="accordion">
          <v-expansion-panel>
            <v-expansion-panel-title>
              <v-icon start size="small">mdi-table</v-icon>
              {{ $t('sources.aiDiscovery.sampleData') }} ({{ source.sample_items.length }})
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <v-table density="compact" class="text-body-2">
                <thead>
                  <tr>
                    <th v-for="key in sampleKeys(source)" :key="key">{{ key }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(item, idx) in source.sample_items.slice(0, 5)" :key="idx">
                    <td v-for="key in Object.keys(item)" :key="key">
                      {{ truncateValue(item[key]) }}
                    </td>
                  </tr>
                </tbody>
              </v-table>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-card-text>
      <v-card-actions>
        <v-checkbox
          :model-value="isSelected(index)"
          :label="$t('sources.aiDiscovery.selectForImport')"
          density="compact"
          hide-details
          @update:model-value="toggleSelection(index, $event)"
        ></v-checkbox>
        <v-spacer />
        <v-btn
          variant="outlined"
          size="small"
          color="primary"
          @click="$emit('saveTemplate', source)"
        >
          <v-icon start size="small">mdi-bookmark-plus</v-icon>
          {{ $t('sources.aiDiscovery.saveAsTemplate') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </div>
  <v-alert v-else type="info" variant="tonal">
    {{ $t('sources.aiDiscovery.noApiSources') }}
  </v-alert>
</template>

<script setup lang="ts">
/**
 * AiDiscoveryApiResults - Display validated API sources
 *
 * Shows API source cards with sample data preview and selection checkboxes.
 */
import type { ValidatedAPISource } from './types'

interface Props {
  sources: ValidatedAPISource[]
  selectedIndices: number[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'update:selectedIndices', value: number[]): void
  (e: 'saveTemplate', source: ValidatedAPISource): void
}>()

/** Get keys from first sample item */
const sampleKeys = (source: ValidatedAPISource): string[] => {
  return Object.keys(source.sample_items[0] || {})
}

/** Truncate long values for display */
const truncateValue = (value: unknown): string => {
  if (value === null || value === undefined) return '-'
  const str = String(value)
  return str.length > 50 ? str.slice(0, 47) + '...' : str
}

/** Check if index is selected */
const isSelected = (index: number): boolean => {
  return props.selectedIndices.includes(index)
}

/** Toggle selection for index */
const toggleSelection = (index: number, selected: boolean | null) => {
  const newSelection = selected
    ? [...props.selectedIndices, index]
    : props.selectedIndices.filter(i => i !== index)
  emit('update:selectedIndices', newSelection)
}
</script>
