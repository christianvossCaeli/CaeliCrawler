<template>
  <HelpCard section-id="categories" :title="t('help.categories.title')" icon="mdi-folder-multiple" color="purple">
    <p class="mb-4">{{ t('help.categories.description') }}</p>

    <v-expansion-panels variant="accordion">
      <v-expansion-panel :title="t('help.categories.basicSettings.title')">
        <v-expansion-panel-text>
          <v-table density="compact">
            <thead><tr><th>{{ t('common.field') }}</th><th>{{ t('common.description') }}</th><th>{{ t('common.example') }}</th></tr></thead>
            <tbody>
              <tr><td><strong>{{ t('help.categories.basicSettings.name') }}</strong></td><td>{{ t('help.categories.basicSettings.nameDesc') }}</td><td>{{ t('help.categories.basicSettings.nameExample') }}</td></tr>
              <tr><td><strong>{{ t('help.categories.basicSettings.description') }}</strong></td><td>{{ t('help.categories.basicSettings.descriptionDesc') }}</td><td>{{ t('help.categories.basicSettings.descriptionExample') }}</td></tr>
              <tr><td><strong>{{ t('help.categories.basicSettings.purpose') }}</strong></td><td>{{ t('help.categories.basicSettings.purposeDesc') }}</td><td>{{ t('help.categories.basicSettings.purposeExample') }}</td></tr>
              <tr><td><strong>{{ t('help.categories.basicSettings.status') }}</strong></td><td>{{ t('help.categories.basicSettings.statusDesc') }}</td><td>{{ t('common.active') }}</td></tr>
              <tr><td><strong>{{ t('help.categories.basicSettings.documentTypes') }}</strong></td><td>{{ t('help.categories.basicSettings.documentTypesDesc') }}</td><td>{{ t('help.categories.basicSettings.documentTypesExample') }}</td></tr>
              <tr><td><strong>{{ t('help.categories.basicSettings.schedule') }}</strong></td><td>{{ t('help.categories.basicSettings.scheduleDesc') }}</td><td>{{ t('help.categories.basicSettings.scheduleExample') }}</td></tr>
            </tbody>
          </v-table>
        </v-expansion-panel-text>
      </v-expansion-panel>

      <v-expansion-panel :title="t('help.categories.searchTerms.title')">
        <v-expansion-panel-text>
          <p class="mb-2">{{ t('help.categories.searchTerms.description') }}</p>
          <v-chip-group>
            <v-chip size="small">windkraft</v-chip>
            <v-chip size="small">windenergie</v-chip>
            <v-chip size="small">windpark</v-chip>
            <v-chip size="small">repowering</v-chip>
            <v-chip size="small">flächennutzungsplan</v-chip>
            <v-chip size="small">bebauungsplan</v-chip>
          </v-chip-group>
          <v-alert type="info" variant="tonal" density="compact" class="mt-3">
            {{ t('help.categories.searchTerms.info') }}
          </v-alert>
        </v-expansion-panel-text>
      </v-expansion-panel>

      <v-expansion-panel :title="t('help.categories.urlFilters.title')">
        <v-expansion-panel-text>
          <v-alert type="info" variant="tonal" density="compact" class="mb-3" :text="t('help.categories.urlFilters.info')" />

          <h4 class="mb-2"><v-icon color="error" size="small">mdi-close</v-icon> {{ t('help.categories.urlFilters.excludeTitle') }}</h4>
          <p class="text-body-2 mb-2">{{ t('help.categories.urlFilters.excludeDesc') }}</p>
          <v-chip-group class="mb-3">
            <v-chip size="small" color="error" variant="outlined">/impressum</v-chip>
            <v-chip size="small" color="error" variant="outlined">/datenschutz</v-chip>
            <v-chip size="small" color="error" variant="outlined">/login</v-chip>
            <v-chip size="small" color="error" variant="outlined">/archiv</v-chip>
            <v-chip size="small" color="error" variant="outlined">/suche</v-chip>
          </v-chip-group>

          <h4 class="mb-2"><v-icon color="success" size="small">mdi-check</v-icon> {{ t('help.categories.urlFilters.includeTitle') }}</h4>
          <p class="text-body-2 mb-2">{{ t('help.categories.urlFilters.includeDesc') }}</p>
          <v-chip-group>
            <v-chip size="small" color="grey" variant="outlined">/ratsinformation/</v-chip>
            <v-chip size="small" color="grey" variant="outlined">/beschluesse/</v-chip>
          </v-chip-group>

          <v-alert type="warning" variant="tonal" density="compact" class="mt-3" :text="t('help.categories.urlFilters.recommendation')" />
        </v-expansion-panel-text>
      </v-expansion-panel>

      <v-expansion-panel :title="t('help.categories.aiPrompt.title')">
        <v-expansion-panel-text>
          <p class="mb-2">{{ t('help.categories.aiPrompt.description') }}</p>
          <v-code class="pa-3 d-block text-caption" style="white-space: pre-wrap;">Analysiere das Dokument und extrahiere:
{
  "topic": "Hauptthema",
  "summary": "Zusammenfassung",
  "is_relevant": true/false,
  "municipality": "Gemeinde",
  "pain_points": ["Kritische Punkte"],
  "positive_signals": ["Positive Signale/Chancen"],
  "decision_makers": [{"person": "Name", "role": "Position"}],
  "sentiment": "positiv/neutral/negativ"
}</v-code>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <h3 class="text-h6 mt-4 mb-3">{{ t('help.categories.actions.title') }}</h3>
    <v-table density="compact">
      <thead><tr><th>{{ t('common.actions') }}</th><th>{{ t('common.icon') }}</th><th>{{ t('common.description') }}</th></tr></thead>
      <tbody>
        <tr><td>{{ t('help.categories.actions.edit') }}</td><td><v-icon size="small">mdi-pencil</v-icon></td><td>{{ t('help.categories.actions.editDesc') }}</td></tr>
        <tr><td>{{ t('help.categories.actions.crawl') }}</td><td><v-icon size="small" color="success">mdi-play</v-icon></td><td>{{ t('help.categories.actions.crawlDesc') }}</td></tr>
        <tr><td>{{ t('help.categories.actions.reanalyze') }}</td><td><v-icon size="small" color="warning">mdi-refresh</v-icon></td><td>{{ t('help.categories.actions.reanalyzeDesc') }}</td></tr>
        <tr><td>{{ t('help.categories.actions.delete') }}</td><td><v-icon size="small" color="error">mdi-delete</v-icon></td><td>{{ t('help.categories.actions.deleteDesc') }}</td></tr>
      </tbody>
    </v-table>
  </HelpCard>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import HelpCard from './HelpCard.vue'

const { t } = useI18n()
</script>
