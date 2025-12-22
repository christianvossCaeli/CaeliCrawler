<template>
  <HelpCard section-id="crawler" :title="t('help.crawler.title')" icon="mdi-robot" color="teal">
    <p class="mb-4">{{ t('help.crawler.description') }}</p>

    <h3 class="text-h6 mb-3">{{ t('help.crawler.statusCards') }}</h3>
    <v-row class="mb-4">
      <v-col cols="6" md="3">
        <v-card variant="outlined" class="text-center pa-3">
          <v-icon color="success" size="x-large">mdi-account-hard-hat</v-icon>
          <div class="text-subtitle-1">{{ t('help.crawler.cards.activeWorkers') }}</div>
          <div class="text-caption">{{ t('help.crawler.cards.activeWorkersDesc') }}</div>
        </v-card>
      </v-col>
      <v-col cols="6" md="3">
        <v-card variant="outlined" class="text-center pa-3">
          <v-icon color="info" size="x-large">mdi-run</v-icon>
          <div class="text-subtitle-1">{{ t('help.crawler.cards.runningJobs') }}</div>
          <div class="text-caption">{{ t('help.crawler.cards.runningJobsDesc') }}</div>
        </v-card>
      </v-col>
      <v-col cols="6" md="3">
        <v-card variant="outlined" class="text-center pa-3">
          <v-icon color="warning" size="x-large">mdi-clock-outline</v-icon>
          <div class="text-subtitle-1">{{ t('help.crawler.cards.pendingJobs') }}</div>
          <div class="text-caption">{{ t('help.crawler.cards.pendingJobsDesc') }}</div>
        </v-card>
      </v-col>
      <v-col cols="6" md="3">
        <v-card variant="outlined" class="text-center pa-3">
          <v-icon color="primary" size="x-large">mdi-file-document-multiple</v-icon>
          <div class="text-subtitle-1">{{ t('help.crawler.cards.documents') }}</div>
          <div class="text-caption">{{ t('help.crawler.cards.documentsDesc') }}</div>
        </v-card>
      </v-col>
    </v-row>

    <h3 class="text-h6 mb-3">{{ t('help.crawler.aiTasks.title') }}</h3>
    <v-alert type="info" variant="tonal" class="mb-3">
      {{ t('help.crawler.aiTasks.info') }}
      <v-list density="compact" class="bg-transparent">
        <v-list-item prepend-icon="mdi-brain">{{ t('help.crawler.aiTasks.items[0]') }}</v-list-item>
        <v-list-item prepend-icon="mdi-progress-check">{{ t('help.crawler.aiTasks.items[1]') }}</v-list-item>
        <v-list-item prepend-icon="mdi-stop"><v-chip size="x-small" color="error">{{ t('help.crawler.stopButton') }}</v-chip> {{ t('help.crawler.aiTasks.items[2]') }}</v-list-item>
      </v-list>
    </v-alert>

    <h3 class="text-h6 mb-3">{{ t('help.crawler.activeCrawlers.title') }}</h3>
    <p class="mb-2">{{ t('help.crawler.activeCrawlers.description') }}</p>
    <v-list density="compact" class="mb-4">
      <v-list-item prepend-icon="mdi-web">
        <v-list-item-title>{{ t('help.crawler.activeCrawlers.items[0]') }}</v-list-item-title>
      </v-list-item>
      <v-list-item prepend-icon="mdi-file-document">
        <v-list-item-title>{{ t('help.crawler.activeCrawlers.items[1]') }}</v-list-item-title>
      </v-list-item>
      <v-list-item prepend-icon="mdi-alert">
        <v-list-item-title>{{ t('help.crawler.activeCrawlers.items[2]') }}</v-list-item-title>
      </v-list-item>
      <v-list-item prepend-icon="mdi-stop">
        <v-list-item-title><v-chip size="x-small" color="error">{{ t('help.crawler.stopButton') }}</v-chip> {{ t('help.crawler.activeCrawlers.items[3]') }}</v-list-item-title>
      </v-list-item>
    </v-list>

    <h4 class="text-subtitle-1 mb-2">{{ t('help.crawler.activeCrawlers.liveLog') }}</h4>
    <v-alert type="info" variant="tonal" density="compact" class="mb-4">
      {{ t('help.crawler.activeCrawlers.liveLogDesc') }}
    </v-alert>

    <h3 class="text-h6 mb-3">{{ t('help.crawler.jobTable.title') }}</h3>
    <v-table density="compact" class="mb-4">
      <thead><tr><th>{{ t('help.crawler.jobTable.columnHeader') }}</th><th>{{ t('help.crawler.jobTable.descriptionHeader') }}</th></tr></thead>
      <tbody>
        <tr><td><strong>{{ t('help.crawler.jobTable.source') }}</strong></td><td>{{ t('help.crawler.jobTable.sourceDesc') }}</td></tr>
        <tr><td><strong>{{ t('help.crawler.jobTable.status') }}</strong></td><td>{{ t('help.crawler.jobTable.statusDesc') }}</td></tr>
        <tr><td><strong>{{ t('help.crawler.jobTable.started') }}</strong></td><td>{{ t('help.crawler.jobTable.startedDesc') }}</td></tr>
        <tr><td><strong>{{ t('help.crawler.jobTable.duration') }}</strong></td><td>{{ t('help.crawler.jobTable.durationDesc') }}</td></tr>
        <tr><td><strong>{{ t('help.crawler.jobTable.progress') }}</strong></td><td>{{ t('help.crawler.jobTable.progressDesc') }}</td></tr>
        <tr><td><strong>{{ t('help.crawler.jobTable.actions') }}</strong></td><td>{{ t('help.crawler.jobTable.actionsDesc') }}</td></tr>
      </tbody>
    </v-table>

    <h3 class="text-h6 mb-3">{{ t('help.crawler.jobDetails.title') }}</h3>
    <p class="mb-2">{{ t('help.crawler.jobDetails.description') }}</p>
    <v-row class="mb-3">
      <v-col cols="12" md="6">
        <v-list density="compact">
          <v-list-item prepend-icon="mdi-web"><v-list-item-title>{{ t('help.crawler.jobDetails.info[0]') }}</v-list-item-title></v-list-item>
          <v-list-item prepend-icon="mdi-check-circle"><v-list-item-title>{{ t('help.crawler.jobDetails.info[1]') }}</v-list-item-title></v-list-item>
          <v-list-item prepend-icon="mdi-clock"><v-list-item-title>{{ t('help.crawler.jobDetails.info[2]') }}</v-list-item-title></v-list-item>
        </v-list>
      </v-col>
      <v-col cols="12" md="6">
        <v-card variant="outlined" class="pa-2">
          <div class="text-subtitle-2 mb-2">{{ t('help.crawler.jobDetails.statistics') }}</div>
          <v-chip size="small" class="mr-1">{{ t('help.crawler.jobDetails.stats[0]') }}</v-chip>
          <v-chip size="small" class="mr-1" color="success">{{ t('help.crawler.jobDetails.stats[1]') }}</v-chip>
          <v-chip size="small" color="info">{{ t('help.crawler.jobDetails.stats[2]') }}</v-chip>
        </v-card>
      </v-col>
    </v-row>
    <v-alert type="warning" variant="tonal" density="compact" class="mb-4">
      {{ t('help.crawler.jobDetails.errorLog') }}
    </v-alert>

    <h3 class="text-h6 mt-4 mb-3">{{ t('help.crawler.statusFilter') }}</h3>
    <v-btn-toggle class="mb-2" density="compact" variant="outlined">
      <v-btn size="small">{{ t('help.crawler.filterButtons.all') }}</v-btn>
      <v-btn size="small" color="info">{{ t('help.crawler.filterButtons.running') }}</v-btn>
      <v-btn size="small" color="success">{{ t('help.crawler.filterButtons.completed') }}</v-btn>
      <v-btn size="small" color="error">{{ t('help.crawler.filterButtons.failed') }}</v-btn>
    </v-btn-toggle>
  </HelpCard>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import HelpCard from './HelpCard.vue'

const { t } = useI18n()
</script>
