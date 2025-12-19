<template>
  <HelpCard section-id="notifications" :title="t('help.notifications.title')" icon="mdi-bell" color="orange-darken-2">
    <p class="mb-4">
      {{ t('help.notifications.description') }}
    </p>

    <h3 class="text-h6 mb-3">{{ t('help.notifications.overview.title') }}</h3>
    <p class="mb-4">
      {{ t('help.notifications.overview.description') }}
    </p>

    <v-list density="compact" class="mb-4">
      <v-list-item prepend-icon="mdi-inbox">
        <v-list-item-title><strong>{{ t('help.notifications.overview.inbox') }}</strong></v-list-item-title>
        <v-list-item-subtitle>{{ t('help.notifications.overview.inboxDesc') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-filter-cog">
        <v-list-item-title><strong>{{ t('help.notifications.overview.rules') }}</strong></v-list-item-title>
        <v-list-item-subtitle>{{ t('help.notifications.overview.rulesDesc') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-cog">
        <v-list-item-title><strong>{{ t('help.notifications.overview.settings') }}</strong></v-list-item-title>
        <v-list-item-subtitle>{{ t('help.notifications.overview.settingsDesc') }}</v-list-item-subtitle>
      </v-list-item>
    </v-list>

    <v-divider class="my-4"></v-divider>

    <h3 class="text-h6 mb-3">{{ t('help.notifications.eventTypes.title') }}</h3>
    <p class="mb-4">{{ t('help.notifications.eventTypes.description') }}</p>

    <v-table density="compact" class="mb-4">
      <thead>
        <tr><th>Event</th><th>{{ t('common.description') }}</th></tr>
      </thead>
      <tbody>
        <tr>
          <td><v-chip size="small" color="success">{{ t('help.notifications.eventTypes.newDocument') }}</v-chip></td>
          <td>{{ t('help.notifications.eventTypes.newDocumentDesc') }}</td>
        </tr>
        <tr>
          <td><v-chip size="small" color="info">{{ t('help.notifications.eventTypes.documentChanged') }}</v-chip></td>
          <td>{{ t('help.notifications.eventTypes.documentChangedDesc') }}</td>
        </tr>
        <tr>
          <td><v-chip size="small" color="error">{{ t('help.notifications.eventTypes.documentRemoved') }}</v-chip></td>
          <td>{{ t('help.notifications.eventTypes.documentRemovedDesc') }}</td>
        </tr>
        <tr>
          <td><v-chip size="small" color="purple">{{ t('help.notifications.eventTypes.crawlStarted') }}</v-chip></td>
          <td>{{ t('help.notifications.eventTypes.crawlStartedDesc') }}</td>
        </tr>
        <tr>
          <td><v-chip size="small" color="success">{{ t('help.notifications.eventTypes.crawlCompleted') }}</v-chip></td>
          <td>{{ t('help.notifications.eventTypes.crawlCompletedDesc') }}</td>
        </tr>
        <tr>
          <td><v-chip size="small" color="error">{{ t('help.notifications.eventTypes.crawlFailed') }}</v-chip></td>
          <td>{{ t('help.notifications.eventTypes.crawlFailedDesc') }}</td>
        </tr>
        <tr>
          <td><v-chip size="small" color="cyan">{{ t('help.notifications.eventTypes.aiAnalysisCompleted') }}</v-chip></td>
          <td>{{ t('help.notifications.eventTypes.aiAnalysisCompletedDesc') }}</td>
        </tr>
        <tr>
          <td><v-chip size="small" color="orange">{{ t('help.notifications.eventTypes.highConfidence') }}</v-chip></td>
          <td>{{ t('help.notifications.eventTypes.highConfidenceDesc') }}</td>
        </tr>
        <tr>
          <td><v-chip size="small" color="grey">{{ t('help.notifications.eventTypes.sourceStatusChanged') }}</v-chip></td>
          <td>{{ t('help.notifications.eventTypes.sourceStatusChangedDesc') }}</td>
        </tr>
        <tr>
          <td><v-chip size="small" color="error">{{ t('help.notifications.eventTypes.sourceError') }}</v-chip></td>
          <td>{{ t('help.notifications.eventTypes.sourceErrorDesc') }}</td>
        </tr>
      </tbody>
    </v-table>

    <v-divider class="my-4"></v-divider>

    <h3 class="text-h6 mb-3">{{ t('help.notifications.channels.title') }}</h3>

    <v-row class="mb-4">
      <v-col cols="12" md="4">
        <v-card variant="outlined" class="pa-3">
          <div class="d-flex align-center mb-2">
            <v-icon color="blue" class="mr-2">mdi-email</v-icon>
            <strong>{{ t('help.notifications.channels.email') }}</strong>
          </div>
          <p class="text-body-2">
            {{ t('help.notifications.channels.emailDesc') }}
          </p>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card variant="outlined" class="pa-3">
          <div class="d-flex align-center mb-2">
            <v-icon color="purple" class="mr-2">mdi-webhook</v-icon>
            <strong>{{ t('help.notifications.channels.webhook') }}</strong>
          </div>
          <p class="text-body-2">
            {{ t('help.notifications.channels.webhookDesc') }}
          </p>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card variant="outlined" class="pa-3">
          <div class="d-flex align-center mb-2">
            <v-icon color="green" class="mr-2">mdi-bell-ring</v-icon>
            <strong>{{ t('help.notifications.channels.inApp') }}</strong>
          </div>
          <p class="text-body-2">
            {{ t('help.notifications.channels.inAppDesc') }}
          </p>
        </v-card>
      </v-col>
    </v-row>

    <v-divider class="my-4"></v-divider>

    <h3 class="text-h6 mb-3">{{ t('help.notifications.createRules.title') }}</h3>
    <p class="mb-4">{{ t('help.notifications.createRules.description') }}</p>

    <v-timeline density="compact" side="end" class="mb-4">
      <v-timeline-item dot-color="primary" size="small">
        <template v-slot:opposite><strong>1</strong></template>
        <div><strong>{{ t('help.notifications.createRules.step1Title') }}</strong><br>{{ t('help.notifications.createRules.step1Desc') }}</div>
      </v-timeline-item>
      <v-timeline-item dot-color="success" size="small">
        <template v-slot:opposite><strong>2</strong></template>
        <div><strong>{{ t('help.notifications.createRules.step2Title') }}</strong><br>{{ t('help.notifications.createRules.step2Desc') }}</div>
      </v-timeline-item>
      <v-timeline-item dot-color="warning" size="small">
        <template v-slot:opposite><strong>3</strong></template>
        <div><strong>{{ t('help.notifications.createRules.step3Title') }}</strong><br>{{ t('help.notifications.createRules.step3Desc') }}</div>
      </v-timeline-item>
      <v-timeline-item dot-color="info" size="small">
        <template v-slot:opposite><strong>4</strong></template>
        <div><strong>{{ t('help.notifications.createRules.step4Title') }}</strong><br>{{ t('help.notifications.createRules.step4Desc') }}</div>
      </v-timeline-item>
    </v-timeline>

    <h3 class="text-h6 mb-3">{{ t('help.notifications.filterOptions.title') }}</h3>
    <v-table density="compact" class="mb-4">
      <thead>
        <tr><th>Filter</th><th>{{ t('common.description') }}</th></tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>{{ t('help.notifications.filterOptions.categories') }}</strong></td>
          <td>{{ t('help.notifications.filterOptions.categoriesDesc') }}</td>
        </tr>
        <tr>
          <td><strong>{{ t('help.notifications.filterOptions.dataSources') }}</strong></td>
          <td>{{ t('help.notifications.filterOptions.dataSourcesDesc') }}</td>
        </tr>
        <tr>
          <td><strong>{{ t('help.notifications.filterOptions.minConfidence') }}</strong></td>
          <td>{{ t('help.notifications.filterOptions.minConfidenceDesc') }}</td>
        </tr>
        <tr>
          <td><strong>{{ t('help.notifications.filterOptions.keywords') }}</strong></td>
          <td>{{ t('help.notifications.filterOptions.keywordsDesc') }}</td>
        </tr>
      </tbody>
    </v-table>

    <v-divider class="my-4"></v-divider>

    <h3 class="text-h6 mb-3">{{ t('help.notifications.digestMode.title') }}</h3>
    <p class="mb-4">
      {{ t('help.notifications.digestMode.description') }}
    </p>
    <v-alert type="info" variant="tonal" class="mb-4">
      {{ t('help.notifications.digestMode.info') }}
    </v-alert>

    <h3 class="text-h6 mb-3">{{ t('help.notifications.emailAddresses.title') }}</h3>
    <p class="mb-4">
      {{ t('help.notifications.emailAddresses.description') }}
    </p>
    <v-list density="compact" class="mb-4">
      <v-list-item prepend-icon="mdi-plus">
        <v-list-item-title>{{ t('help.notifications.emailAddresses.add') }}</v-list-item-title>
        <v-list-item-subtitle>{{ t('help.notifications.emailAddresses.addDesc') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-email-check">
        <v-list-item-title>{{ t('help.notifications.emailAddresses.verify') }}</v-list-item-title>
        <v-list-item-subtitle>{{ t('help.notifications.emailAddresses.verifyDesc') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-delete">
        <v-list-item-title>{{ t('help.notifications.emailAddresses.delete') }}</v-list-item-title>
        <v-list-item-subtitle>{{ t('help.notifications.emailAddresses.deleteDesc') }}</v-list-item-subtitle>
      </v-list-item>
    </v-list>

    <v-divider class="my-4"></v-divider>

    <h3 class="text-h6 mb-3">{{ t('help.notifications.webhookConfig.title') }}</h3>
    <p class="mb-4">
      {{ t('help.notifications.webhookConfig.description') }}
    </p>
    <v-table density="compact" class="mb-4">
      <thead>
        <tr><th>Methode</th><th>{{ t('common.description') }}</th></tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>{{ t('help.notifications.webhookConfig.none') }}</strong></td>
          <td>{{ t('help.notifications.webhookConfig.noneDesc') }}</td>
        </tr>
        <tr>
          <td><strong>{{ t('help.notifications.webhookConfig.bearer') }}</strong></td>
          <td>{{ t('help.notifications.webhookConfig.bearerDesc') }}</td>
        </tr>
        <tr>
          <td><strong>{{ t('help.notifications.webhookConfig.apiKey') }}</strong></td>
          <td>{{ t('help.notifications.webhookConfig.apiKeyDesc') }}</td>
        </tr>
        <tr>
          <td><strong>{{ t('help.notifications.webhookConfig.basicAuth') }}</strong></td>
          <td>{{ t('help.notifications.webhookConfig.basicAuthDesc') }}</td>
        </tr>
      </tbody>
    </v-table>

    <v-alert type="warning" variant="tonal" class="mb-4">
      {{ t('help.notifications.webhookConfig.warning') }}
    </v-alert>
  </HelpCard>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import HelpCard from './HelpCard.vue'

const { t } = useI18n()
</script>
