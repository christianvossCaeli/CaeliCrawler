<template>
  <HelpCard section-id="export" :title="t('help.export.title')" icon="mdi-export" color="secondary">
    <h3 class="text-h6 mb-3">{{ t('help.export.exportFormats') }}</h3>
    <v-row class="mb-4">
      <v-col cols="6">
        <v-card variant="outlined" class="pa-3 text-center">
          <v-icon size="48" color="primary">mdi-code-json</v-icon>
          <div class="text-h6">{{ t('help.export.formats.json') }}</div>
          <div class="text-caption">{{ t('help.export.formats.jsonDesc') }}</div>
        </v-card>
      </v-col>
      <v-col cols="6">
        <v-card variant="outlined" class="pa-3 text-center">
          <v-icon size="48" color="success">mdi-file-delimited</v-icon>
          <div class="text-h6">{{ t('help.export.formats.csv') }}</div>
          <div class="text-caption">{{ t('help.export.formats.csvDesc') }}</div>
        </v-card>
      </v-col>
    </v-row>

    <h3 class="text-h6 mb-3">{{ t('help.export.exportFilters') }}</h3>
    <v-chip-group class="mb-4">
      <v-chip size="small" variant="outlined">{{ t('help.export.filters[0]') }}</v-chip>
      <v-chip size="small" variant="outlined">{{ t('help.export.filters[1]') }}</v-chip>
      <v-chip size="small" variant="outlined">{{ t('help.export.filters[2]') }}</v-chip>
      <v-chip size="small" variant="outlined">{{ t('help.export.filters[3]') }}</v-chip>
      <v-chip size="small" variant="outlined">{{ t('help.export.filters[4]') }}</v-chip>
    </v-chip-group>

    <h3 class="text-h6 mb-3">{{ t('help.export.webhookTest.title') }}</h3>
    <p class="mb-2">{{ t('help.export.webhookTest.description') }}</p>
    <v-list density="compact" class="mb-4">
      <v-list-item prepend-icon="mdi-link">
        <v-list-item-title>{{ t('help.export.webhookTest.items[0]') }}</v-list-item-title>
      </v-list-item>
      <v-list-item prepend-icon="mdi-send">
        <v-list-item-title>{{ t('help.export.webhookTest.items[1]') }}</v-list-item-title>
      </v-list-item>
      <v-list-item prepend-icon="mdi-check">
        <v-list-item-title>{{ t('help.export.webhookTest.items[2]') }}</v-list-item-title>
      </v-list-item>
    </v-list>

    <h3 class="text-h6 mb-3">{{ t('help.export.changesFeed.title') }}</h3>
    <p class="mb-2">{{ t('help.export.changesFeed.description') }}</p>
    <v-table density="compact" class="mb-4">
      <thead><tr><th>{{ t('common.changeType') }}</th><th>{{ t('common.description') }}</th></tr></thead>
      <tbody>
        <tr><td><v-chip size="small" color="success">NEW</v-chip></td><td>{{ t('help.export.changesFeed.newDesc') }}</td></tr>
        <tr><td><v-chip size="small" color="info">UPDATED</v-chip></td><td>{{ t('help.export.changesFeed.updatedDesc') }}</td></tr>
        <tr><td><v-chip size="small" color="warning">VERIFIED</v-chip></td><td>{{ t('help.export.changesFeed.verifiedDesc') }}</td></tr>
      </tbody>
    </v-table>

    <h3 class="text-h6 mb-3">{{ t('help.export.apiEndpoints.title') }}</h3>
    <v-table density="compact">
      <thead><tr><th>{{ t('common.endpoint') }}</th><th>{{ t('common.description') }}</th></tr></thead>
      <tbody>
        <tr><td><code>GET /api/v1/data</code></td><td>{{ t('help.export.apiEndpoints.getData') }}</td></tr>
        <tr><td><code>GET /api/v1/data/documents</code></td><td>{{ t('help.export.apiEndpoints.getDocuments') }}</td></tr>
        <tr><td><code>GET /api/v1/data/search?q=...</code></td><td>{{ t('help.export.apiEndpoints.search') }}</td></tr>
        <tr><td><code>GET /api/v1/export/json</code></td><td>{{ t('help.export.apiEndpoints.exportJson') }}</td></tr>
        <tr><td><code>GET /api/v1/export/csv</code></td><td>{{ t('help.export.apiEndpoints.exportCsv') }}</td></tr>
        <tr><td><code>GET /api/v1/export/changes</code></td><td>{{ t('help.export.apiEndpoints.getChanges') }}</td></tr>
        <tr><td><code>POST /api/v1/export/webhook/test</code></td><td>{{ t('help.export.apiEndpoints.testWebhook') }}</td></tr>
      </tbody>
    </v-table>
  </HelpCard>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import HelpCard from './HelpCard.vue'

const { t } = useI18n()
</script>
