<template>
  <HelpCard section-id="results" :title="t('help.results.title')" icon="mdi-chart-bar" color="orange">
    <p class="mb-4">{{ t('help.results.description') }}</p>

    <h3 class="text-h6 mb-3">{{ t('help.results.statisticsCards') }}</h3>
    <v-row class="mb-4">
      <v-col cols="6" md="3">
        <v-card variant="outlined" class="text-center pa-2">
          <div class="text-subtitle-1">{{ t('help.results.cards.total') }}</div>
          <div class="text-caption">{{ t('help.results.cards.totalDesc') }}</div>
        </v-card>
      </v-col>
      <v-col cols="6" md="3">
        <v-card variant="outlined" class="text-center pa-2" color="success">
          <div class="text-subtitle-1">{{ t('help.results.cards.verified') }}</div>
          <div class="text-caption">{{ t('help.results.cards.verifiedDesc') }}</div>
        </v-card>
      </v-col>
      <v-col cols="6" md="3">
        <v-card variant="outlined" class="text-center pa-2" color="info">
          <div class="text-subtitle-1">{{ t('help.results.cards.highConfidence') }}</div>
          <div class="text-caption">{{ t('help.results.cards.highConfidenceDesc') }}</div>
        </v-card>
      </v-col>
      <v-col cols="6" md="3">
        <v-card variant="outlined" class="text-center pa-2">
          <div class="text-subtitle-1">{{ t('help.results.cards.average') }}</div>
          <div class="text-caption">{{ t('help.results.cards.averageDesc') }}</div>
        </v-card>
      </v-col>
    </v-row>

    <h3 class="text-h6 mb-3">{{ t('help.results.bulkVerify.title') }}</h3>
    <v-alert type="success" variant="tonal" class="mb-3">
      <v-icon>mdi-check-all</v-icon>
      {{ t('help.results.bulkVerify.description') }}
    </v-alert>
    <v-list density="compact" class="mb-4">
      <v-list-item prepend-icon="mdi-checkbox-multiple-marked">
        <v-list-item-title>{{ t('help.results.bulkVerify.step1') }}</v-list-item-title>
      </v-list-item>
      <v-list-item prepend-icon="mdi-check-decagram">
        <v-list-item-title>{{ t('help.results.bulkVerify.step2') }}</v-list-item-title>
      </v-list-item>
      <v-list-item prepend-icon="mdi-shield-check">
        <v-list-item-title>{{ t('help.results.bulkVerify.step3') }}</v-list-item-title>
      </v-list-item>
    </v-list>

    <h3 class="text-h6 mb-3">{{ t('help.results.availableFilters') }}</h3>
    <v-chip-group class="mb-4">
      <v-chip size="small" variant="outlined">{{ t('help.results.filters[0]') }}</v-chip>
      <v-chip size="small" variant="outlined">{{ t('help.results.filters[1]') }}</v-chip>
      <v-chip size="small" variant="outlined">{{ t('help.results.filters[2]') }}</v-chip>
      <v-chip size="small" variant="outlined">{{ t('help.results.filters[3]') }}</v-chip>
    </v-chip-group>

    <h3 class="text-h6 mb-3">{{ t('help.results.whatIsExtracted') }}</h3>
    <v-list density="compact">
      <v-list-item prepend-icon="mdi-tag">
        <v-list-item-title>{{ t('help.results.extracted.topicSummary') }}</v-list-item-title>
      </v-list-item>
      <v-list-item prepend-icon="mdi-emoticon-sad">
        <v-list-item-title>{{ t('help.results.extracted.painPoints') }}</v-list-item-title>
        <v-list-item-subtitle>{{ t('help.results.extracted.painPointsDesc') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-emoticon-happy">
        <v-list-item-title>{{ t('help.results.extracted.opportunities') }}</v-list-item-title>
        <v-list-item-subtitle>{{ t('help.results.extracted.opportunitiesDesc') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-emoticon-neutral">
        <v-list-item-title>{{ t('help.results.extracted.sentiment') }}</v-list-item-title>
        <v-list-item-subtitle>{{ t('help.results.extracted.sentimentDesc') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-percent">
        <v-list-item-title>{{ t('help.results.extracted.confidence') }}</v-list-item-title>
        <v-list-item-subtitle>{{ t('help.results.extracted.confidenceDesc') }}</v-list-item-subtitle>
      </v-list-item>
    </v-list>

    <h3 class="text-h6 mt-4 mb-3">{{ t('help.results.detailDialog.title') }}</h3>
    <p class="mb-2">{{ t('help.results.detailDialog.description') }}</p>

    <h4 class="text-subtitle-1 mb-2">{{ t('help.results.detailDialog.header') }}</h4>
    <v-list density="compact" class="mb-3">
      <v-list-item prepend-icon="mdi-text">{{ t('help.results.detailDialog.headerItems[0]') }}</v-list-item>
      <v-list-item prepend-icon="mdi-percent">{{ t('help.results.detailDialog.headerItems[1]') }}</v-list-item>
      <v-list-item prepend-icon="mdi-link">{{ t('help.results.detailDialog.headerItems[2]') }}</v-list-item>
    </v-list>

    <h4 class="text-subtitle-1 mb-2">{{ t('help.results.detailDialog.infoCards') }}</h4>
    <v-row class="mb-3">
      <v-col cols="3"><v-chip size="small" variant="outlined" color="success">Relevant?</v-chip></v-col>
      <v-col cols="3"><v-chip size="small" variant="outlined">Relevanz</v-chip></v-col>
      <v-col cols="3"><v-chip size="small" variant="outlined">Gemeinde</v-chip></v-col>
      <v-col cols="3"><v-chip size="small" variant="outlined" color="warning">Priorität</v-chip></v-col>
    </v-row>

    <v-expansion-panels variant="accordion" class="mb-4">
      <v-expansion-panel :title="t('help.results.detailDialog.sections.summary')">
        <v-expansion-panel-text>
          {{ t('help.results.detailDialog.sections.summaryDesc') }}
        </v-expansion-panel-text>
      </v-expansion-panel>
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon class="mr-2" color="error">mdi-alert</v-icon> {{ t('help.results.detailDialog.sections.painPoints') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          {{ t('help.results.detailDialog.sections.painPointsDesc') }}
        </v-expansion-panel-text>
      </v-expansion-panel>
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon class="mr-2" color="success">mdi-thumb-up</v-icon> {{ t('help.results.detailDialog.sections.positiveSignals') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          {{ t('help.results.detailDialog.sections.positiveSignalsDesc') }}
        </v-expansion-panel-text>
      </v-expansion-panel>
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon class="mr-2" color="primary">mdi-account-group</v-icon> {{ t('help.results.detailDialog.sections.decisionMakers') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          {{ t('help.results.detailDialog.sections.decisionMakersDesc') }}
        </v-expansion-panel-text>
      </v-expansion-panel>
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon class="mr-2">mdi-code-json</v-icon> {{ t('help.results.detailDialog.sections.rawJson') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          {{ t('help.results.detailDialog.sections.rawJsonDesc') }}
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <v-alert type="success" variant="tonal" density="compact" class="mb-4">
      {{ t('help.results.detailDialog.tip') }}
    </v-alert>

    <h3 class="text-h6 mt-4 mb-3">{{ t('help.results.understandingConfidence.title') }}</h3>
    <v-table density="compact">
      <thead><tr><th>Bereich</th><th>Bedeutung</th><th>Empfehlung</th></tr></thead>
      <tbody>
        <tr>
          <td><v-chip size="small" color="error">0-50%</v-chip></td>
          <td>{{ t('help.results.understandingConfidence.lowDesc') }}</td>
          <td>{{ t('help.results.understandingConfidence.lowAction') }}</td>
        </tr>
        <tr>
          <td><v-chip size="small" color="warning">50-70%</v-chip></td>
          <td>{{ t('help.results.understandingConfidence.mediumDesc') }}</td>
          <td>{{ t('help.results.understandingConfidence.mediumAction') }}</td>
        </tr>
        <tr>
          <td><v-chip size="small" color="success">70-100%</v-chip></td>
          <td>{{ t('help.results.understandingConfidence.highDesc') }}</td>
          <td>{{ t('help.results.understandingConfidence.highAction') }}</td>
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
