<template>
  <v-card variant="outlined" class="mb-4">
    <v-card-title class="text-subtitle-1 pb-2">
      <v-icon start color="primary">mdi-filter</v-icon>
      {{ $t('categories.dataSourcesTab.filterByTags') }}
    </v-card-title>
    <v-card-text>
      <v-alert type="info" variant="tonal" density="compact" class="mb-3">
        {{ $t('categories.dataSourcesTab.description') }}
      </v-alert>
      <v-row>
        <v-col cols="12" md="8">
          <v-combobox
            :model-value="selectedTags"
            :items="availableTags"
            :label="$t('categories.dataSourcesTab.filterByTags')"
            multiple
            chips
            closable-chips
            variant="outlined"
            density="compact"
            :aria-label="$t('categories.dataSourcesTab.filterByTags')"
            @update:model-value="emit('update:selectedTags', $event)"
          >
            <template #chip="{ item, props }">
              <v-chip v-bind="props" color="primary" variant="tonal">
                <v-icon start size="small">mdi-tag</v-icon>
                {{ item.raw }}
              </v-chip>
            </template>
          </v-combobox>
        </v-col>
        <v-col cols="12" md="4">
          <v-radio-group
            :model-value="matchMode"
            inline
            hide-details
            :aria-label="$t('categories.dataSourcesTab.matchMode')"
            @update:model-value="handleMatchModeChange"
          >
            <v-radio value="all">
              <template #label>
                <span class="text-caption">{{ $t('categories.dataSourcesTab.matchAll') }}</span>
              </template>
            </v-radio>
            <v-radio value="any">
              <template #label>
                <span class="text-caption">{{ $t('categories.dataSourcesTab.matchAny') }}</span>
              </template>
            </v-radio>
          </v-radio-group>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
interface Props {
  selectedTags: string[]
  matchMode: 'all' | 'any'
  availableTags: string[]
}

interface Emits {
  (e: 'update:selectedTags', tags: string[]): void
  (e: 'update:matchMode', mode: 'all' | 'any'): void
}

defineProps<Props>()
const emit = defineEmits<Emits>()

const handleMatchModeChange = (mode: 'all' | 'any' | null) => {
  if (mode !== null) {
    emit('update:matchMode', mode)
  }
}
</script>
