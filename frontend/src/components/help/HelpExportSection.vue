<template>
  <HelpCard section-id="export" :title="t('help.export.title')" icon="mdi-export" color="secondary">
    <h3 class="text-h6 mb-3">{{ t('help.export.exportFormats') }}</h3>
    <v-row class="mb-4">
      <v-col cols="4">
        <v-card variant="outlined" class="pa-3 text-center">
          <v-icon size="48" color="primary">mdi-code-json</v-icon>
          <div class="text-h6">{{ t('help.export.formats.json') }}</div>
          <div class="text-caption">{{ t('help.export.formats.jsonDesc') }}</div>
        </v-card>
      </v-col>
      <v-col cols="4">
        <v-card variant="outlined" class="pa-3 text-center">
          <v-icon size="48" color="success">mdi-file-delimited</v-icon>
          <div class="text-h6">{{ t('help.export.formats.csv') }}</div>
          <div class="text-caption">{{ t('help.export.formats.csvDesc') }}</div>
        </v-card>
      </v-col>
      <v-col cols="4">
        <v-card variant="outlined" class="pa-3 text-center">
          <v-icon size="48" color="teal">mdi-microsoft-excel</v-icon>
          <div class="text-h6">{{ t('help.export.formats.excel') }}</div>
          <div class="text-caption">{{ t('help.export.formats.excelDesc') }}</div>
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
        <tr><td><v-chip size="small" color="success">NEW_DOCUMENT</v-chip></td><td>{{ t('help.export.changesFeed.newDocumentDesc') }}</td></tr>
        <tr><td><v-chip size="small" color="info">CONTENT_CHANGED</v-chip></td><td>{{ t('help.export.changesFeed.contentChangedDesc') }}</td></tr>
        <tr><td><v-chip size="small" color="error">REMOVED</v-chip></td><td>{{ t('help.export.changesFeed.removedDesc') }}</td></tr>
        <tr><td><v-chip size="small" color="warning">METADATA_CHANGED</v-chip></td><td>{{ t('help.export.changesFeed.metadataChangedDesc') }}</td></tr>
      </tbody>
    </v-table>

    <h3 class="text-h6 mb-3">{{ t('help.export.asyncExport.title') }}</h3>
    <p class="mb-3">{{ t('help.export.asyncExport.description') }}</p>
    <v-expansion-panels variant="accordion" class="mb-4">
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon class="mr-2">mdi-format-list-numbered</v-icon>
          {{ t('help.export.asyncExport.workflow.title') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-list density="compact">
            <v-list-item prepend-icon="mdi-numeric-1-circle">{{ t('help.export.asyncExport.workflow.step1') }}</v-list-item>
            <v-list-item prepend-icon="mdi-numeric-2-circle">{{ t('help.export.asyncExport.workflow.step2') }}</v-list-item>
            <v-list-item prepend-icon="mdi-numeric-3-circle">{{ t('help.export.asyncExport.workflow.step3') }}</v-list-item>
            <v-list-item prepend-icon="mdi-numeric-4-circle">{{ t('help.export.asyncExport.workflow.step4') }}</v-list-item>
            <v-list-item prepend-icon="mdi-numeric-5-circle">{{ t('help.export.asyncExport.workflow.step5') }}</v-list-item>
            <v-list-item prepend-icon="mdi-numeric-6-circle">{{ t('help.export.asyncExport.workflow.step6') }}</v-list-item>
          </v-list>
        </v-expansion-panel-text>
      </v-expansion-panel>
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon class="mr-2">mdi-star</v-icon>
          {{ t('help.export.asyncExport.features.title') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-list density="compact">
            <v-list-item prepend-icon="mdi-progress-clock">{{ t('help.export.asyncExport.features.progress') }}</v-list-item>
            <v-list-item prepend-icon="mdi-shape">{{ t('help.export.asyncExport.features.entityTypes') }}</v-list-item>
            <v-list-item prepend-icon="mdi-file-multiple">{{ t('help.export.asyncExport.features.formats') }}</v-list-item>
            <v-list-item prepend-icon="mdi-tag-multiple">{{ t('help.export.asyncExport.features.facets') }}</v-list-item>
            <v-list-item prepend-icon="mdi-download">{{ t('help.export.asyncExport.features.download') }}</v-list-item>
            <v-list-item prepend-icon="mdi-cancel">{{ t('help.export.asyncExport.features.cancel') }}</v-list-item>
          </v-list>
        </v-expansion-panel-text>
      </v-expansion-panel>
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon class="mr-2">mdi-information</v-icon>
          {{ t('help.export.asyncExport.statusTypes.title') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-list density="compact">
            <v-list-item><v-chip size="small" color="grey" class="mr-2">PENDING</v-chip>{{ t('help.export.asyncExport.statusTypes.pending') }}</v-list-item>
            <v-list-item><v-chip size="small" color="info" class="mr-2">RUNNING</v-chip>{{ t('help.export.asyncExport.statusTypes.running') }}</v-list-item>
            <v-list-item><v-chip size="small" color="success" class="mr-2">COMPLETED</v-chip>{{ t('help.export.asyncExport.statusTypes.completed') }}</v-list-item>
            <v-list-item><v-chip size="small" color="error" class="mr-2">FAILED</v-chip>{{ t('help.export.asyncExport.statusTypes.failed') }}</v-list-item>
            <v-list-item><v-chip size="small" color="warning" class="mr-2">CANCELLED</v-chip>{{ t('help.export.asyncExport.statusTypes.cancelled') }}</v-list-item>
          </v-list>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
    <v-alert type="info" variant="tonal" density="compact" class="mb-4">
      {{ t('help.export.asyncExport.retention') }}
    </v-alert>

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
