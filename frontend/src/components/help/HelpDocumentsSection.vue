<template>
  <HelpCard section-id="documents" :title="t('help.documents.title')" icon="mdi-file-document-multiple" color="blue-grey">
    <p class="mb-4">{{ t('help.documents.description') }}</p>

    <h3 class="text-h6 mb-3">{{ t('help.documents.statusOverview') }}</h3>
    <div class="d-flex flex-wrap ga-2 mb-4">
      <v-chip color="warning" variant="tonal">
        <v-icon start size="small">mdi-clock-outline</v-icon>
        {{ t('help.documents.statuses.pending') }}
      </v-chip>
      <v-chip color="info" variant="tonal">
        <v-icon start size="small">mdi-cog-sync</v-icon>
        {{ t('help.documents.statuses.processing') }}
      </v-chip>
      <v-chip color="success" variant="tonal">
        <v-icon start size="small">mdi-check-circle</v-icon>
        {{ t('help.documents.statuses.completed') }}
      </v-chip>
      <v-chip variant="tonal">
        <v-icon start size="small">mdi-filter-remove</v-icon>
        {{ t('help.documents.statuses.filtered') }}
      </v-chip>
      <v-chip color="error" variant="tonal">
        <v-icon start size="small">mdi-alert-circle</v-icon>
        {{ t('help.documents.statuses.failed') }}
      </v-chip>
    </div>

    <h3 class="text-h6 mb-3">{{ t('help.documents.actionButtons.title') }}</h3>
    <v-table density="compact">
      <thead><tr><th>{{ t('common.button') }}</th><th>{{ t('common.description') }}</th></tr></thead>
      <tbody>
        <tr><td><v-chip size="small" color="primary">{{ t('help.documents.actionButtons.processPending') }}</v-chip></td><td>{{ t('help.documents.actionButtons.processPendingDesc') }}</td></tr>
        <tr><td><v-chip size="small" color="warning">{{ t('help.documents.actionButtons.analyzeFiltered') }}</v-chip></td><td>{{ t('help.documents.actionButtons.analyzeFilteredDesc') }}</td></tr>
        <tr><td><v-chip size="small" color="error">{{ t('help.documents.actionButtons.stopProcessing') }}</v-chip></td><td>{{ t('help.documents.actionButtons.stopProcessingDesc') }}</td></tr>
      </tbody>
    </v-table>

    <h3 class="text-h6 mt-4 mb-3">{{ t('help.documents.bulkOperations.title') }}</h3>
    <v-alert type="info" variant="tonal" class="mb-3">
      <v-icon>mdi-checkbox-multiple-marked</v-icon>
      {{ t('help.documents.bulkOperations.description') }}
    </v-alert>
    <v-row class="mb-4">
      <v-col cols="12" md="6">
        <v-card variant="outlined" class="pa-3">
          <div class="text-subtitle-2 mb-2">{{ t('help.documents.bulkOperations.selection.title') }}</div>
          <v-list density="compact">
            <v-list-item prepend-icon="mdi-checkbox-marked">
              {{ t('help.documents.bulkOperations.selection.individual') }}
            </v-list-item>
            <v-list-item prepend-icon="mdi-checkbox-multiple-marked">
              {{ t('help.documents.bulkOperations.selection.selectAll') }}
            </v-list-item>
            <v-list-item prepend-icon="mdi-filter-check">
              {{ t('help.documents.bulkOperations.selection.filtered') }}
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>
      <v-col cols="12" md="6">
        <v-card variant="outlined" class="pa-3">
          <div class="text-subtitle-2 mb-2">{{ t('help.documents.bulkOperations.actions.title') }}</div>
          <v-list density="compact">
            <v-list-item prepend-icon="mdi-play-circle">
              {{ t('help.documents.bulkOperations.actions.processSelected') }}
            </v-list-item>
            <v-list-item prepend-icon="mdi-brain">
              {{ t('help.documents.bulkOperations.actions.analyzeSelected') }}
            </v-list-item>
            <v-list-item prepend-icon="mdi-delete">
              {{ t('help.documents.bulkOperations.actions.deleteSelected') }}
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>
    </v-row>

    <h3 class="text-h6 mt-4 mb-3">{{ t('help.documents.availableFilters') }}</h3>
    <v-chip-group>
      <v-chip size="small" variant="outlined" v-for="(filter, index) in (tm('help.documents.filters') as string[])" :key="index">
        {{ filter }}
      </v-chip>
    </v-chip-group>

    <h3 class="text-h6 mt-4 mb-3">{{ t('help.documents.documentDetails.title') }}</h3>
    <v-expansion-panels variant="accordion">
      <v-expansion-panel :title="t('help.documents.documentDetails.tabInfo')">
        <v-expansion-panel-text>
          <ul class="pl-4">
            <li v-for="(item, index) in (tm('help.documents.documentDetails.tabInfoItems') as string[])" :key="index">
              {{ item }}
            </li>
          </ul>
        </v-expansion-panel-text>
      </v-expansion-panel>
      <v-expansion-panel :title="t('help.documents.documentDetails.tabText')">
        <v-expansion-panel-text>
          {{ t('help.documents.documentDetails.tabTextDesc') }}
        </v-expansion-panel-text>
      </v-expansion-panel>
      <v-expansion-panel :title="t('help.documents.documentDetails.tabExtracted')">
        <v-expansion-panel-text>
          <ul class="pl-4">
            <li v-for="(item, index) in (tm('help.documents.documentDetails.tabExtractedItems') as string[])" :key="index">
              {{ item }}
            </li>
          </ul>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </HelpCard>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import HelpCard from './HelpCard.vue'

const { t, tm } = useI18n()
</script>
