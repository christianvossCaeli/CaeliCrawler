<template>
  <v-dialog v-model="modelValue" max-width="600">
    <v-card>
      <v-card-title class="d-flex align-center pa-4 bg-primary">
        <v-avatar color="primary-darken-1" size="40" class="mr-3">
          <v-icon color="on-primary">mdi-link-plus</v-icon>
        </v-avatar>
        <div>
          <div class="text-h6">{{ t('entityDetail.linkDataSourceTitle') }}</div>
          <div class="text-caption opacity-80">{{ t('entityDetail.linkDataSourceSubtitle') }}</div>
        </div>
      </v-card-title>
      <v-card-text class="pa-4">
        <p class="text-body-2 text-medium-emphasis mb-4">{{ t('entityDetail.linkDataSourceDesc') }}</p>

        <!-- Search existing sources -->
        <v-autocomplete
          :model-value="selectedSource"
          @update:model-value="$emit('update:selectedSource', $event)"
          :items="availableSources"
          item-title="name"
          item-value="id"
          :label="t('entityDetail.searchExistingSource')"
          :loading="searching"
          :no-data-text="searchQuery?.length >= 2 ? t('entityDetail.noSourcesFound') : t('entityDetail.typeToSearchSources')"
          variant="outlined"
          prepend-inner-icon="mdi-magnify"
          return-object
          clearable
          @update:search="$emit('search', $event)"
        >
          <template v-slot:item="{ props, item }">
            <v-list-item v-bind="props">
              <template v-slot:prepend>
                <v-icon :color="getSourceStatusColor(item.raw.status)">{{ getSourceTypeIcon(item.raw.source_type) }}</v-icon>
              </template>
              <v-list-item-subtitle>{{ item.raw.base_url }}</v-list-item-subtitle>
            </v-list-item>
          </template>
        </v-autocomplete>

        <v-divider class="my-4"></v-divider>

        <div class="text-center">
          <v-btn variant="text" color="primary" @click="$emit('createNew')">
            <v-icon start>mdi-plus</v-icon>
            {{ t('entityDetail.createNewSourceForEntity') }}
          </v-btn>
        </div>
      </v-card-text>
      <v-card-actions class="pa-4">
        <v-btn variant="tonal" @click="modelValue = false">{{ t('common.cancel') }}</v-btn>
        <v-spacer></v-spacer>
        <v-btn
          variant="tonal"
          color="primary"
          :disabled="!selectedSource"
          :loading="linking"
          @click="$emit('link')"
        >
          <v-icon start>mdi-link</v-icon>
          {{ t('entityDetail.linkSource') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const modelValue = defineModel<boolean>()

// Types
interface DataSource {
  id: string
  name: string
  base_url?: string | null
  source_type: string
  status: string
}

// Props
defineProps<{
  selectedSource: DataSource | null
  availableSources: DataSource[]
  searching: boolean
  searchQuery: string
  linking: boolean
}>()

// Emits
defineEmits<{
  'update:selectedSource': [source: DataSource | null]
  search: [query: string]
  link: []
  createNew: []
}>()

const { t } = useI18n()

// Helpers
function getSourceStatusColor(status: string): string {
  const colors: Record<string, string> = {
    active: 'success',
    inactive: 'grey',
    pending: 'warning',
    error: 'error',
    crawling: 'info'
  }
  return colors[status] || 'grey'
}

function getSourceTypeIcon(sourceType: string): string {
  const icons: Record<string, string> = {
    website: 'mdi-web',
    api: 'mdi-api',
    rss: 'mdi-rss',
    file: 'mdi-file',
    oparl: 'mdi-gavel',
    sharepoint: 'mdi-microsoft-sharepoint'
  }
  return icons[sourceType] || 'mdi-database'
}
</script>
