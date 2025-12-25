<template>
  <v-dialog v-model="modelValue" max-width="900">
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2">mdi-database-outline</v-icon>
        {{ t('categories.dialog.sourcesFor') }} {{ category?.name }}
        <v-chip color="primary" size="small" class="ml-2">
          {{ sources.length }} {{ t('categories.crawler.sourcesCount') }}
        </v-chip>
      </v-card-title>
      <v-card-text>
        <!-- Category Summary -->
        <v-alert type="info" variant="tonal" density="compact" class="mb-4">
          <div class="text-body-2">{{ category?.purpose }}</div>
        </v-alert>

        <!-- Search -->
        <v-text-field
          v-model="searchQuery"
          :label="t('categories.dialog.searchSources')"
          prepend-inner-icon="mdi-magnify"
          variant="outlined"
          density="compact"
          clearable
          class="mb-4"
        ></v-text-field>

        <!-- Sources List -->
        <v-list v-if="filteredSources.length > 0" lines="two" class="sources-list">
          <v-list-item
            v-for="source in filteredSources"
            :key="source.id"
            :title="source.name"
            :subtitle="source.base_url"
          >
            <template v-slot:prepend>
              <v-avatar :color="getStatusColor(source.status)" size="36">
                <v-icon size="small" :color="getContrastColor(getStatusColor(source.status))">{{ getSourceTypeIcon(source.source_type) }}</v-icon>
              </v-avatar>
            </template>
            <template v-slot:append>
              <div class="d-flex align-center">
                <v-chip size="x-small" class="mr-2" :color="getStatusColor(source.status)">
                  {{ source.status }}
                </v-chip>
                <v-chip size="x-small" color="info" variant="outlined" class="mr-2">
                  {{ source.document_count || 0 }} {{ t('categories.dialog.docs') }}
                </v-chip>
                <v-btn
                  icon="mdi-open-in-new"
                  size="x-small"
                  variant="tonal"
                  :href="source.base_url"
                  target="_blank"
                  :title="t('categories.dialog.openUrl')"
                ></v-btn>
              </div>
            </template>
          </v-list-item>
        </v-list>

        <v-alert v-else type="warning" variant="tonal">
          <span v-if="searchQuery">{{ t('categories.dialog.noSourcesSearch') }} "{{ searchQuery }}"</span>
          <span v-else>{{ t('categories.dialog.noSources') }}</span>
        </v-alert>

        <!-- Statistics -->
        <v-divider class="my-4"></v-divider>
        <v-row>
          <v-col cols="3">
            <div class="text-center">
              <div class="text-h5 text-primary">{{ stats.total }}</div>
              <div class="text-caption">{{ t('categories.stats.total') }}</div>
            </div>
          </v-col>
          <v-col cols="3">
            <div class="text-center">
              <div class="text-h5 text-success">{{ stats.active }}</div>
              <div class="text-caption">{{ t('categories.stats.active') }}</div>
            </div>
          </v-col>
          <v-col cols="3">
            <div class="text-center">
              <div class="text-h5 text-warning">{{ stats.pending }}</div>
              <div class="text-caption">{{ t('categories.stats.pending') }}</div>
            </div>
          </v-col>
          <v-col cols="3">
            <div class="text-center">
              <div class="text-h5 text-error">{{ stats.error }}</div>
              <div class="text-caption">{{ t('categories.stats.error') }}</div>
            </div>
          </v-col>
        </v-row>
      </v-card-text>
      <v-card-actions>
        <v-btn
          color="primary"
          variant="tonal"
          @click="$emit('navigateToSources')"
        >
          <v-icon left>mdi-filter</v-icon>{{ t('categories.dialog.showAllInSourcesView') }}
        </v-btn>
        <v-spacer></v-spacer>
        <v-btn variant="tonal" @click="modelValue = false">{{ t('common.close') }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { getContrastColor } from '@/composables/useColorHelpers'
import { useStatusColors } from '@/composables'

// Types
interface Source {
  id: string
  name: string
  base_url: string
  status: string
  source_type?: string
  document_count?: number
}

interface Category {
  id: string
  name: string
  purpose?: string
}

interface Stats {
  total: number
  active: number
  pending: number
  error: number
}

const modelValue = defineModel<boolean>()

// Props
const props = defineProps<{
  category: Category | null
  sources: Source[]
  stats: Stats
}>()

// Emits
defineEmits<{
  navigateToSources: []
}>()

const { t } = useI18n()
const { getStatusColor } = useStatusColors()

// Local state
const searchQuery = ref('')

// Computed
const filteredSources = computed(() => {
  if (!searchQuery.value) return props.sources
  const query = searchQuery.value.toLowerCase()
  return props.sources.filter(
    source =>
      source.name.toLowerCase().includes(query) ||
      source.base_url.toLowerCase().includes(query)
  )
})

// Helper functions - getStatusColor now from useStatusColors composable

function getSourceTypeIcon(sourceType?: string): string {
  const icons: Record<string, string> = {
    website: 'mdi-web',
    api: 'mdi-api',
    rss: 'mdi-rss',
    sharepoint: 'mdi-microsoft-sharepoint',
  }
  return icons[sourceType?.toLowerCase() || ''] || 'mdi-web'
}
</script>

<style scoped>
.sources-list {
  max-height: 400px;
  overflow-y: auto;
}
</style>
