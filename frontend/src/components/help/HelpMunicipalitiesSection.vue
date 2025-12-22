<template>
  <HelpCard section-id="municipalities" :title="t('help.municipalities.title')" icon="mdi-city" color="teal">
    <p class="mb-4">{{ t('help.municipalities.description') }}</p>

    <h3 class="text-h6 mb-3">{{ t('help.municipalities.statisticsCards') }}</h3>
    <v-row class="mb-4">
      <v-col cols="6" md="3">
        <v-card variant="outlined" class="text-center pa-2">
          <div class="text-subtitle-1">{{ t('help.municipalities.cards.municipalities') }}</div>
          <div class="text-caption">{{ t('help.municipalities.cards.municipalitiesDesc') }}</div>
        </v-card>
      </v-col>
      <v-col cols="6" md="3">
        <v-card variant="outlined" class="text-center pa-2" color="primary">
          <div class="text-subtitle-1">{{ t('help.municipalities.cards.documents') }}</div>
          <div class="text-caption">{{ t('help.municipalities.cards.documentsDesc') }}</div>
        </v-card>
      </v-col>
      <v-col cols="6" md="3">
        <v-card variant="outlined" class="text-center pa-2" color="success">
          <div class="text-subtitle-1">{{ t('help.municipalities.cards.relevant') }}</div>
          <div class="text-caption">{{ t('help.municipalities.cards.relevantDesc') }}</div>
        </v-card>
      </v-col>
      <v-col cols="6" md="3">
        <v-card variant="outlined" class="text-center pa-2" color="warning">
          <div class="text-subtitle-1">{{ t('help.municipalities.cards.highPriority') }}</div>
          <div class="text-caption">{{ t('help.municipalities.cards.highPriorityDesc') }}</div>
        </v-card>
      </v-col>
    </v-row>

    <h3 class="text-h6 mb-3">{{ t('help.municipalities.tableColumns.title') }}</h3>
    <v-table density="compact" class="mb-4">
      <thead><tr><th>{{ t('help.municipalities.tableColumns.columnHeader') }}</th><th>{{ t('help.municipalities.tableColumns.descriptionHeader') }}</th></tr></thead>
      <tbody>
        <tr><td><v-icon size="small">mdi-city</v-icon> <strong>{{ t('help.municipalities.tableColumns.name') }}</strong></td><td>{{ t('help.municipalities.tableColumns.nameDesc') }}</td></tr>
        <tr><td><strong>{{ t('help.municipalities.tableColumns.adminLevels') }}</strong></td><td>{{ t('help.municipalities.tableColumns.adminLevelsDesc') }}</td></tr>
        <tr><td><v-chip size="x-small" color="info">{{ t('help.municipalities.tableColumns.sources') }}</v-chip></td><td>{{ t('help.municipalities.tableColumns.sourcesDesc') }}</td></tr>
        <tr><td><strong>{{ t('help.municipalities.tableColumns.documents') }}</strong></td><td>{{ t('help.municipalities.tableColumns.documentsDesc') }}</td></tr>
        <tr><td><strong>{{ t('help.municipalities.tableColumns.confidence') }}</strong></td><td>{{ t('help.municipalities.tableColumns.confidenceDesc') }}</td></tr>
        <tr><td><v-chip size="x-small" color="info">{{ t('help.municipalities.tableColumns.decisionMakers') }}</v-chip></td><td>{{ t('help.municipalities.tableColumns.decisionMakersDesc') }}</td></tr>
      </tbody>
    </v-table>

    <h3 class="text-h6 mb-3">{{ t('help.municipalities.filters') }}</h3>
    <v-chip-group class="mb-4">
      <v-chip size="small" variant="outlined">{{ t('help.municipalities.filterList[0]') }}</v-chip>
      <v-chip size="small" variant="outlined">{{ t('help.municipalities.filterList[1]') }}</v-chip>
      <v-chip size="small" variant="outlined">{{ t('help.municipalities.filterList[2]') }}</v-chip>
      <v-chip size="small" variant="outlined">{{ t('help.municipalities.filterList[3]') }}</v-chip>
      <v-chip size="small" variant="outlined">{{ t('help.municipalities.filterList[4]') }}</v-chip>
      <v-chip size="small" variant="outlined">{{ t('help.municipalities.filterList[5]') }}</v-chip>
    </v-chip-group>

    <h3 class="text-h6 mb-3">{{ t('help.municipalities.municipalityReport.title') }}</h3>
    <p class="mb-2">{{ t('help.municipalities.municipalityReport.description') }}</p>

    <v-alert type="info" variant="tonal" class="mb-3">
      <strong>{{ t('help.municipalities.municipalityReport.reportHeader') }}</strong>
    </v-alert>

    <h4 class="text-subtitle-1 mb-2">{{ t('help.municipalities.municipalityReport.overviewCards') }}</h4>
    <v-row class="mb-3">
      <v-col cols="3"><v-chip size="small" variant="outlined">{{ t('help.municipalities.municipalityReport.overviewCardLabels.documents') }}</v-chip></v-col>
      <v-col cols="3"><v-chip size="small" variant="outlined" color="success">{{ t('help.municipalities.municipalityReport.overviewCardLabels.relevant') }}</v-chip></v-col>
      <v-col cols="3"><v-chip size="small" variant="outlined">{{ t('help.municipalities.municipalityReport.overviewCardLabels.confidence') }}</v-chip></v-col>
      <v-col cols="3"><v-chip size="small" variant="outlined" color="warning">{{ t('help.municipalities.municipalityReport.overviewCardLabels.priority') }}</v-chip></v-col>
    </v-row>

    <h4 class="text-subtitle-1 mb-2">{{ t('help.municipalities.municipalityReport.reportTabs') }}</h4>
    <v-expansion-panels variant="accordion" class="mb-4">
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon class="mr-2">mdi-account-group</v-icon> {{ t('help.municipalities.municipalityReport.tabs.decisionMakers') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          {{ t('help.municipalities.municipalityReport.tabs.decisionMakersDesc') }}
        </v-expansion-panel-text>
      </v-expansion-panel>
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon class="mr-2" color="error">mdi-alert</v-icon> {{ t('help.municipalities.municipalityReport.tabs.painPoints') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          {{ t('help.municipalities.municipalityReport.tabs.painPointsDesc') }}
        </v-expansion-panel-text>
      </v-expansion-panel>
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon class="mr-2" color="success">mdi-thumb-up</v-icon> {{ t('help.municipalities.municipalityReport.tabs.positiveSignals') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          {{ t('help.municipalities.municipalityReport.tabs.positiveSignalsDesc') }}
        </v-expansion-panel-text>
      </v-expansion-panel>
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon class="mr-2">mdi-text</v-icon> {{ t('help.municipalities.municipalityReport.tabs.summaries') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          {{ t('help.municipalities.municipalityReport.tabs.summariesDesc') }}
        </v-expansion-panel-text>
      </v-expansion-panel>
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon class="mr-2">mdi-web</v-icon> {{ t('help.municipalities.municipalityReport.tabs.dataSources') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          {{ t('help.municipalities.municipalityReport.tabs.dataSourcesDesc') }}
        </v-expansion-panel-text>
      </v-expansion-panel>
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon class="mr-2">mdi-database-sync</v-icon> {{ t('help.municipalities.municipalityReport.tabs.pysis') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          {{ t('help.municipalities.municipalityReport.tabs.pysisDesc') }}
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <h3 class="text-h6 mt-4 mb-3">{{ t('help.municipalities.locationManagement.title') }}</h3>
    <v-table density="compact">
      <thead><tr><th>{{ t('help.municipalities.locationManagement.functionColumn') }}</th><th>{{ t('help.municipalities.locationManagement.descriptionColumn') }}</th></tr></thead>
      <tbody>
        <tr><td><v-chip size="small" color="primary">{{ t('help.municipalities.locationManagement.newLocation') }}</v-chip></td><td>{{ t('help.municipalities.locationManagement.newLocationDesc') }}</td></tr>
        <tr><td><v-icon size="small">mdi-pencil</v-icon> {{ t('help.municipalities.locationManagement.edit') }}</td><td>{{ t('help.municipalities.locationManagement.editDesc') }}</td></tr>
        <tr><td><v-icon size="small">mdi-eye</v-icon> {{ t('help.municipalities.locationManagement.showReport') }}</td><td>{{ t('help.municipalities.locationManagement.showReportDesc') }}</td></tr>
        <tr><td><v-icon size="small">mdi-file-document-multiple</v-icon> {{ t('help.municipalities.locationManagement.documents') }}</td><td>{{ t('help.municipalities.locationManagement.documentsDesc') }}</td></tr>
        <tr><td><strong>{{ t('help.municipalities.locationManagement.linkSources') }}</strong></td><td>{{ t('help.municipalities.locationManagement.linkSourcesDesc') }}</td></tr>
        <tr><td><strong>{{ t('help.municipalities.locationManagement.enrichAdminLevels') }}</strong></td><td>{{ t('help.municipalities.locationManagement.enrichAdminLevelsDesc') }}</td></tr>
      </tbody>
    </v-table>
  </HelpCard>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import HelpCard from './HelpCard.vue'

const { t } = useI18n()
</script>
