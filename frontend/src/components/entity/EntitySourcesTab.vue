<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-icon start>mdi-web</v-icon>
      {{ t('entityDetail.tabs.dataSources') }}
      <v-chip v-if="dataSources.length" size="small" class="ml-2">{{ dataSources.length }}</v-chip>
      <v-spacer></v-spacer>
      <v-btn variant="tonal" color="primary" size="small" @click="$emit('linkSource')">
        <v-icon start>mdi-link-plus</v-icon>
        {{ t('entityDetail.linkDataSource') }}
      </v-btn>
    </v-card-title>
    <v-card-text>
      <div v-if="loading" class="text-center pa-4">
        <v-progress-circular indeterminate></v-progress-circular>
      </div>
      <div v-else-if="dataSources.length">
        <v-list lines="two">
          <v-list-item
            v-for="source in dataSources"
            :key="source.id"
            class="mb-2"
          >
            <template v-slot:prepend>
              <v-avatar :color="getSourceStatusColor(source.status)" size="40">
                <v-icon color="white">{{ getSourceTypeIcon(source.source_type) }}</v-icon>
              </v-avatar>
            </template>
            <v-list-item-title class="font-weight-medium">
              {{ source.name }}
              <v-chip v-if="source.hasRunningJob" size="x-small" color="info" class="ml-2">
                {{ t('entityDetail.running') }}
              </v-chip>
              <v-chip :color="getSourceStatusColor(source.status)" size="x-small" class="ml-1">
                {{ source.status }}
              </v-chip>
              <v-chip v-if="source.is_direct_link" size="x-small" color="primary" variant="outlined" class="ml-1">
                <v-icon start size="x-small">mdi-link</v-icon>
                {{ t('entityDetail.directLink') }}
              </v-chip>
            </v-list-item-title>
            <v-list-item-subtitle>
              <a :href="source.base_url" target="_blank" class="text-decoration-none text-info">
                <v-icon size="x-small" class="mr-1">mdi-open-in-new</v-icon>
                {{ source.base_url }}
              </a>
              <span v-if="source.document_count" class="ml-3 text-medium-emphasis">
                <v-icon size="x-small">mdi-file-document</v-icon>
                {{ source.document_count }} {{ t('entityDetail.documentsCount') }}
              </span>
              <span v-if="source.last_crawl" class="ml-3 text-medium-emphasis">
                <v-icon size="x-small">mdi-clock-outline</v-icon>
                {{ formatDate(source.last_crawl) }}
              </span>
            </v-list-item-subtitle>
            <template v-slot:append>
              <div class="d-flex ga-1">
                <v-btn
                  icon="mdi-pencil"
                  size="small"
                  variant="tonal"
                  :title="t('common.edit')"
                  @click="$emit('editSource', source)"
                ></v-btn>
                <v-btn
                  v-if="!source.hasRunningJob"
                  icon="mdi-play"
                  size="small"
                  variant="tonal"
                  color="success"
                  :title="t('entityDetail.crawl')"
                  @click="$emit('startCrawl', source)"
                  :loading="startingCrawlId === source.id"
                ></v-btn>
                <v-btn
                  v-if="source.is_direct_link"
                  icon="mdi-link-off"
                  size="small"
                  variant="tonal"
                  color="warning"
                  :title="t('entityDetail.unlinkSource')"
                  @click="$emit('unlinkSource', source)"
                ></v-btn>
                <v-btn
                  icon="mdi-delete"
                  size="small"
                  variant="tonal"
                  color="error"
                  :title="t('common.delete')"
                  @click="$emit('deleteSource', source)"
                ></v-btn>
              </div>
            </template>
          </v-list-item>
        </v-list>
      </div>
      <!-- Empty State for Data Sources -->
      <div v-else class="text-center pa-8">
        <v-icon size="80" color="grey-lighten-1" class="mb-4">mdi-web-off</v-icon>
        <h3 class="text-h6 mb-2">{{ t('entityDetail.emptyState.noDataSources') }}</h3>
        <p class="text-body-2 text-medium-emphasis mb-4">
          {{ t('entityDetail.emptyState.noDataSourcesDesc') }}
        </p>
        <v-btn variant="tonal" color="primary" @click="$emit('linkSource')">
          <v-icon start>mdi-link-plus</v-icon>
          {{ t('entityDetail.linkDataSource') }}
        </v-btn>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { format } from 'date-fns'
import { de } from 'date-fns/locale'

// Types
interface DataSource {
  id: string
  name: string
  base_url: string
  status: string
  source_type?: string
  is_direct_link?: boolean
  document_count?: number
  last_crawl?: string
  hasRunningJob?: boolean
}

// Props
defineProps<{
  dataSources: DataSource[]
  loading: boolean
  startingCrawlId: string | null
}>()

// Emits
defineEmits<{
  linkSource: []
  editSource: [source: DataSource]
  startCrawl: [source: DataSource]
  unlinkSource: [source: DataSource]
  deleteSource: [source: DataSource]
}>()

const { t } = useI18n()

// Helper functions
function getSourceStatusColor(status: string): string {
  const colors: Record<string, string> = {
    active: 'success',
    pending: 'warning',
    error: 'error',
    inactive: 'grey',
  }
  return colors[status?.toLowerCase()] || 'grey'
}

function getSourceTypeIcon(sourceType?: string): string {
  const icons: Record<string, string> = {
    website: 'mdi-web',
    api: 'mdi-api',
    rss: 'mdi-rss',
    sharepoint: 'mdi-microsoft-sharepoint',
  }
  return icons[sourceType?.toLowerCase() || ''] || 'mdi-web'
}

function formatDate(dateString?: string): string {
  if (!dateString) return ''
  try {
    return format(new Date(dateString), 'dd.MM.yyyy HH:mm', { locale: de })
  } catch {
    return dateString
  }
}
</script>
