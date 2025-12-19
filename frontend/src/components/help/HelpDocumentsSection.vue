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
      <v-chip color="grey" variant="tonal">
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

    <h3 class="text-h6 mt-4 mb-3">{{ t('help.documents.availableFilters') }}</h3>
    <v-chip-group>
      <v-chip size="small" variant="outlined" v-for="(filter, index) in t('help.documents.filters')" :key="index">
        {{ filter }}
      </v-chip>
    </v-chip-group>

    <h3 class="text-h6 mt-4 mb-3">{{ t('help.documents.documentDetails.title') }}</h3>
    <v-expansion-panels variant="accordion">
      <v-expansion-panel :title="t('help.documents.documentDetails.tabInfo')">
        <v-expansion-panel-text>
          <ul class="pl-4">
            <li v-for="(item, index) in t('help.documents.documentDetails.tabInfoItems')" :key="index">
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
            <li v-for="(item, index) in t('help.documents.documentDetails.tabExtractedItems')" :key="index">
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

const { t } = useI18n()
</script>
