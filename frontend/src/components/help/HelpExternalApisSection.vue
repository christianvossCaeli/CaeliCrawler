<template>
  <HelpCard section-id="external-apis" :title="t('help.externalApis.title')" icon="mdi-cloud-sync" color="teal">
    <p class="mb-4">{{ t('help.externalApis.description') }}</p>

    <h3 class="text-h6 mb-3">{{ t('help.externalApis.concept.title') }}</h3>
    <v-alert type="info" variant="tonal" class="mb-4">
      {{ t('help.externalApis.concept.description') }}
    </v-alert>

    <h3 class="text-h6 mb-3">{{ t('help.externalApis.features.title') }}</h3>
    <v-row class="mb-4">
      <v-col cols="12" md="6">
        <v-card variant="outlined" class="pa-3">
          <div class="text-subtitle-1 mb-2">
            <v-icon class="mr-1" color="primary">mdi-sync</v-icon>
            {{ t('help.externalApis.features.syncRecords.title') }}
          </div>
          <v-list density="compact">
            <v-list-item prepend-icon="mdi-database">
              {{ t('help.externalApis.features.syncRecords.rawData') }}
            </v-list-item>
            <v-list-item prepend-icon="mdi-clock-check">
              {{ t('help.externalApis.features.syncRecords.timestamps') }}
            </v-list-item>
            <v-list-item prepend-icon="mdi-alert-circle">
              {{ t('help.externalApis.features.syncRecords.errorTracking') }}
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>
      <v-col cols="12" md="6">
        <v-card variant="outlined" class="pa-3">
          <div class="text-subtitle-1 mb-2">
            <v-icon class="mr-1" color="success">mdi-link-variant</v-icon>
            {{ t('help.externalApis.features.entityLinking.title') }}
          </div>
          <v-list density="compact">
            <v-list-item prepend-icon="mdi-arrow-left-right">
              {{ t('help.externalApis.features.entityLinking.bidirectional') }}
            </v-list-item>
            <v-list-item prepend-icon="mdi-identifier">
              {{ t('help.externalApis.features.entityLinking.externalIds') }}
            </v-list-item>
            <v-list-item prepend-icon="mdi-autorenew">
              {{ t('help.externalApis.features.entityLinking.autoUpdate') }}
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>
    </v-row>

    <h3 class="text-h6 mb-3">{{ t('help.externalApis.authentication.title') }}</h3>
    <v-table density="compact" class="mb-4">
      <thead>
        <tr>
          <th>{{ t('help.externalApis.authentication.table.method') }}</th>
          <th>{{ t('help.externalApis.authentication.table.description') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>
            <v-chip color="primary" size="small">
              <v-icon start size="small">mdi-key</v-icon>
              API Key
            </v-chip>
          </td>
          <td>{{ t('help.externalApis.authentication.apiKey') }}</td>
        </tr>
        <tr>
          <td>
            <v-chip color="success" size="small">
              <v-icon start size="small">mdi-shield-key</v-icon>
              OAuth 2.0
            </v-chip>
          </td>
          <td>{{ t('help.externalApis.authentication.oauth') }}</td>
        </tr>
        <tr>
          <td>
            <v-chip color="warning" size="small">
              <v-icon start size="small">mdi-account-key</v-icon>
              Basic Auth
            </v-chip>
          </td>
          <td>{{ t('help.externalApis.authentication.basic') }}</td>
        </tr>
        <tr>
          <td>
            <v-chip color="grey" size="small">
              <v-icon start size="small">mdi-earth</v-icon>
              {{ t('help.externalApis.authentication.none') }}
            </v-chip>
          </td>
          <td>{{ t('help.externalApis.authentication.noneDesc') }}</td>
        </tr>
      </tbody>
    </v-table>

    <h3 class="text-h6 mb-3">{{ t('help.externalApis.workflow.title') }}</h3>
    <v-timeline density="compact" side="end" class="mb-4">
      <v-timeline-item dot-color="primary" size="small">
        <div class="text-subtitle-2">{{ t('help.externalApis.workflow.step1.title') }}</div>
        <div class="text-caption text-medium-emphasis">{{ t('help.externalApis.workflow.step1.description') }}</div>
      </v-timeline-item>
      <v-timeline-item dot-color="success" size="small">
        <div class="text-subtitle-2">{{ t('help.externalApis.workflow.step2.title') }}</div>
        <div class="text-caption text-medium-emphasis">{{ t('help.externalApis.workflow.step2.description') }}</div>
      </v-timeline-item>
      <v-timeline-item dot-color="info" size="small">
        <div class="text-subtitle-2">{{ t('help.externalApis.workflow.step3.title') }}</div>
        <div class="text-caption text-medium-emphasis">{{ t('help.externalApis.workflow.step3.description') }}</div>
      </v-timeline-item>
      <v-timeline-item dot-color="warning" size="small">
        <div class="text-subtitle-2">{{ t('help.externalApis.workflow.step4.title') }}</div>
        <div class="text-caption text-medium-emphasis">{{ t('help.externalApis.workflow.step4.description') }}</div>
      </v-timeline-item>
    </v-timeline>

    <h3 class="text-h6 mb-3">{{ t('help.externalApis.viewingData.title') }}</h3>
    <v-alert type="success" variant="tonal" density="compact">
      <v-icon>mdi-eye</v-icon>
      {{ t('help.externalApis.viewingData.description') }}
    </v-alert>
  </HelpCard>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import HelpCard from './HelpCard.vue'

const { t } = useI18n()
</script>
