<template>
  <v-tabs v-model="internalActiveTab" color="primary" class="mb-4">
    <v-tab value="facets">
      <v-icon start>mdi-tag-multiple</v-icon>
      {{ t('entityDetail.tabs.properties') }}
      <v-chip v-if="facetsSummary" size="x-small" class="ml-2">{{ facetsSummary.total_facet_values }}</v-chip>
    </v-tab>
    <v-tab value="connections">
      <v-icon start>mdi-sitemap</v-icon>
      {{ t('entityDetail.tabs.connections', 'Verknüpfungen') }}
      <v-chip v-if="totalConnectionsCount" size="x-small" class="ml-2">{{ totalConnectionsCount }}</v-chip>
    </v-tab>
    <v-tab value="sources">
      <v-icon start>mdi-web</v-icon>
      {{ t('entityDetail.tabs.dataSources') }}
      <v-chip v-if="dataSourcesCount" size="x-small" class="ml-2">{{ dataSourcesCount }}</v-chip>
    </v-tab>
    <v-tab value="documents">
      <v-icon start>mdi-file-document-multiple</v-icon>
      {{ t('entityDetail.tabs.documents') }}
    </v-tab>
    <v-tab v-if="supportsPysis" value="pysis">
      <v-icon start>mdi-database-sync</v-icon>
      {{ t('entityDetail.tabs.pysis') }}
    </v-tab>
    <v-tab v-if="hasExternalData" value="api-data">
      <v-icon start>mdi-code-json</v-icon>
      {{ t('entityDetail.tabs.apiData', 'API-Daten') }}
    </v-tab>
    <v-tab value="attachments">
      <v-icon start>mdi-paperclip</v-icon>
      {{ t('entityDetail.tabs.attachments') }}
      <v-chip v-if="attachmentCount" size="x-small" class="ml-2">{{ attachmentCount }}</v-chip>
    </v-tab>
    <v-tab v-if="referencedByCount > 0" value="referenced-by">
      <v-icon start>mdi-link-variant</v-icon>
      {{ t('entityDetail.tabs.referencedBy', 'Referenziert in') }}
      <v-chip v-if="referencedByCount" size="x-small" class="ml-2">{{ referencedByCount }}</v-chip>
    </v-tab>
  </v-tabs>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { FacetsSummary } from '@/types/entity'

const props = defineProps<{
  activeTab: string
  facetsSummary: FacetsSummary | null
  totalConnectionsCount: number
  dataSourcesCount: number
  attachmentCount: number
  supportsPysis: boolean
  hasExternalData: boolean
  referencedByCount: number
}>()

const emit = defineEmits<{
  'update:activeTab': [value: string]
}>()

const { t } = useI18n()

const internalActiveTab = computed({
  get: () => props.activeTab,
  set: (value) => emit('update:activeTab', value)
})
</script>
