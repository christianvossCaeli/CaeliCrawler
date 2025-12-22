<template>
  <HelpCard section-id="troubleshooting" :title="t('help.troubleshooting.title')" icon="mdi-wrench" color="red">
    <v-expansion-panels variant="accordion">
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon color="error" class="mr-2">mdi-alert</v-icon>
          {{ t('help.troubleshooting.noDocuments.title') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <strong>{{ t('help.troubleshooting.noDocuments.possibleCauses') }}</strong>
          <ul class="pl-4 mb-3">
            <li>{{ t('help.troubleshooting.noDocuments.causes.excludePatterns') }}</li>
            <li>{{ t('help.troubleshooting.noDocuments.causes.includePatterns') }}</li>
            <li>{{ t('help.troubleshooting.noDocuments.causes.hiddenBehindJs') }}</li>
            <li>{{ t('help.troubleshooting.noDocuments.causes.blockedCrawler') }}</li>
          </ul>
          <strong>{{ t('help.troubleshooting.noDocuments.solutions') }}</strong>
          <ul class="pl-4">
            <li>{{ t('help.troubleshooting.noDocuments.solutionSteps.checkBlacklist') }}</li>
            <li>{{ t('help.troubleshooting.noDocuments.solutionSteps.emptyWhitelist') }}</li>
            <li>{{ t('help.troubleshooting.noDocuments.solutionSteps.enableJs') }}</li>
            <li>{{ t('help.troubleshooting.noDocuments.solutionSteps.increaseDepth') }}</li>
          </ul>
        </v-expansion-panel-text>
      </v-expansion-panel>

      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon color="error" class="mr-2">mdi-alert</v-icon>
          {{ t('help.troubleshooting.noAiResults.title') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <strong>{{ t('help.troubleshooting.noAiResults.possibleCauses') }}</strong>
          <ul class="pl-4 mb-3">
            <li>{{ t('help.troubleshooting.noAiResults.causes.strictKeywords') }}</li>
            <li>{{ t('help.troubleshooting.noAiResults.causes.noRelevantContent') }}</li>
            <li>{{ t('help.troubleshooting.noAiResults.causes.unsuitablePrompt') }}</li>
          </ul>
          <strong>{{ t('help.troubleshooting.noAiResults.solutions') }}</strong>
          <ul class="pl-4">
            <li>{{ t('help.troubleshooting.noAiResults.solutionSteps.expandKeywords') }}</li>
            <li>{{ t('help.troubleshooting.noAiResults.solutionSteps.analyzeFiltered') }}</li>
            <li>{{ t('help.troubleshooting.noAiResults.solutionSteps.optimizePrompt') }}</li>
          </ul>
        </v-expansion-panel-text>
      </v-expansion-panel>

      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon color="warning" class="mr-2">mdi-clock-alert</v-icon>
          {{ t('help.troubleshooting.pendingDocuments.title') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <strong>{{ t('help.troubleshooting.pendingDocuments.possibleCauses') }}</strong>
          <ul class="pl-4 mb-3">
            <li>{{ t('help.troubleshooting.pendingDocuments.causes.workerInactive') }}</li>
            <li>{{ t('help.troubleshooting.pendingDocuments.causes.queueOverloaded') }}</li>
          </ul>
          <strong>{{ t('help.troubleshooting.pendingDocuments.solutions') }}</strong>
          <ul class="pl-4">
            <li>{{ t('help.troubleshooting.pendingDocuments.solutionSteps.checkWorker') }}</li>
            <li>{{ t('help.troubleshooting.pendingDocuments.solutionSteps.manualProcess') }}</li>
          </ul>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <h3 class="text-h6 mt-4 mb-3">{{ t('help.troubleshooting.statusCodes.heading') }}</h3>
    <v-table density="compact">
      <thead><tr><th>{{ t('help.troubleshooting.statusCodes.status') }}</th><th>{{ t('help.troubleshooting.statusCodes.meaning') }}</th><th>{{ t('help.troubleshooting.statusCodes.action') }}</th></tr></thead>
      <tbody>
        <tr>
          <td><v-chip size="small" color="warning">PENDING</v-chip></td>
          <td>{{ t('help.troubleshooting.statusCodes.pending.meaning') }}</td>
          <td>{{ t('help.troubleshooting.statusCodes.pending.action') }}</td>
        </tr>
        <tr>
          <td><v-chip size="small" color="info">PROCESSING</v-chip></td>
          <td>{{ t('help.troubleshooting.statusCodes.processing.meaning') }}</td>
          <td>{{ t('help.troubleshooting.statusCodes.processing.action') }}</td>
        </tr>
        <tr>
          <td><v-chip size="small" color="secondary">ANALYZING</v-chip></td>
          <td>{{ t('help.troubleshooting.statusCodes.analyzing.meaning') }}</td>
          <td>{{ t('help.troubleshooting.statusCodes.analyzing.action') }}</td>
        </tr>
        <tr>
          <td><v-chip size="small" color="success">COMPLETED</v-chip></td>
          <td>{{ t('help.troubleshooting.statusCodes.completed.meaning') }}</td>
          <td>{{ t('help.troubleshooting.statusCodes.completed.action') }}</td>
        </tr>
        <tr>
          <td><v-chip size="small">FILTERED</v-chip></td>
          <td>{{ t('help.troubleshooting.statusCodes.filtered.meaning') }}</td>
          <td>{{ t('help.troubleshooting.statusCodes.filtered.action') }}</td>
        </tr>
        <tr>
          <td><v-chip size="small" color="error">FAILED</v-chip></td>
          <td>{{ t('help.troubleshooting.statusCodes.failed.meaning') }}</td>
          <td>{{ t('help.troubleshooting.statusCodes.failed.action') }}</td>
        </tr>
      </tbody>
    </v-table>
  </HelpCard>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import HelpCard from './HelpCard.vue'

const { t } = useI18n()
</script>
