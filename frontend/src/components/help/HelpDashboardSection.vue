<template>
  <HelpCard section-id="dashboard" :title="t('help.dashboard.title')" icon="mdi-view-dashboard" color="info">
    <p class="mb-4">{{ t('help.dashboard.description') }}</p>

    <h3 class="text-h6 mb-3">{{ t('help.dashboard.stats_cards_title') }}</h3>
    <v-row class="mb-4">
      <v-col cols="6" md="3">
        <v-card variant="outlined" class="text-center pa-3">
          <v-icon color="primary" size="x-large">mdi-folder-multiple</v-icon>
          <div class="text-h6">{{ t('help.dashboard.cards.categories.title') }}</div>
          <div class="text-caption">{{ t('help.dashboard.cards.categories.description') }}</div>
        </v-card>
      </v-col>
      <v-col cols="6" md="3">
        <v-card variant="outlined" class="text-center pa-3">
          <v-icon color="success" size="x-large">mdi-web</v-icon>
          <div class="text-h6">{{ t('help.dashboard.cards.sources.title') }}</div>
          <div class="text-caption">{{ t('help.dashboard.cards.sources.description') }}</div>
        </v-card>
      </v-col>
      <v-col cols="6" md="3">
        <v-card variant="outlined" class="text-center pa-3">
          <v-icon color="info" size="x-large">mdi-file-document-multiple</v-icon>
          <div class="text-h6">{{ t('help.dashboard.cards.documents.title') }}</div>
          <div class="text-caption">{{ t('help.dashboard.cards.documents.description') }}</div>
        </v-card>
      </v-col>
      <v-col cols="6" md="3">
        <v-card variant="outlined" class="text-center pa-3">
          <v-icon color="warning" size="x-large">mdi-robot</v-icon>
          <div class="text-h6">{{ t('help.dashboard.cards.active_crawlers.title') }}</div>
          <div class="text-caption">{{ t('help.dashboard.cards.active_crawlers.description') }}</div>
        </v-card>
      </v-col>
    </v-row>

    <h3 class="text-h6 mb-3">{{ t('help.dashboard.live_updates_title') }}</h3>
    <v-alert type="info" variant="tonal" class="mb-4">
      {{ t('help.dashboard.live_updates_description') }}
      <v-list density="compact" class="bg-transparent">
        <v-list-item prepend-icon="mdi-file-document">{{ t('help.dashboard.live_updates.documents') }}</v-list-item>
        <v-list-item prepend-icon="mdi-clock">{{ t('help.dashboard.live_updates.runtime') }}</v-list-item>
        <v-list-item prepend-icon="mdi-alert">{{ t('help.dashboard.live_updates.errors') }}</v-list-item>
      </v-list>
    </v-alert>

    <h3 class="text-h6 mb-3">{{ t('help.dashboard.status_jobs_title') }}</h3>
    <v-row class="mb-4">
      <v-col cols="12" md="6">
        <v-card variant="outlined" class="pa-3">
          <div class="text-subtitle-1 mb-2"><v-icon class="mr-1">mdi-robot</v-icon> {{ t('help.dashboard.status_section.title') }}</div>
          <v-list density="compact">
            <v-list-item><v-icon color="success" class="mr-2">mdi-circle</v-icon> {{ t('help.dashboard.status_section.active_workers') }}</v-list-item>
            <v-list-item><v-icon color="info" class="mr-2">mdi-run</v-icon> {{ t('help.dashboard.status_section.running_jobs') }}</v-list-item>
            <v-list-item><v-icon color="warning" class="mr-2">mdi-clock-outline</v-icon> {{ t('help.dashboard.status_section.waiting_jobs') }}</v-list-item>
          </v-list>
        </v-card>
      </v-col>
      <v-col cols="12" md="6">
        <v-card variant="outlined" class="pa-3">
          <div class="text-subtitle-1 mb-2"><v-icon class="mr-1">mdi-history</v-icon> {{ t('help.dashboard.recent_jobs.title') }}</div>
          <div class="text-body-2">{{ t('help.dashboard.recent_jobs.description') }}</div>
        </v-card>
      </v-col>
    </v-row>

    <h3 class="text-h6 mb-3">{{ t('help.dashboard.quick_actions_title') }}</h3>
    <v-chip-group class="mb-4">
      <v-chip color="primary" variant="elevated"><v-icon start>mdi-plus</v-icon> {{ t('help.dashboard.quick_actions.new_category') }}</v-chip>
      <v-chip color="success" variant="elevated"><v-icon start>mdi-web-plus</v-icon> {{ t('help.dashboard.quick_actions.new_source') }}</v-chip>
      <v-chip color="warning" variant="elevated"><v-icon start>mdi-play</v-icon> {{ t('help.dashboard.quick_actions.start_crawler') }}</v-chip>
      <v-chip color="info" variant="elevated"><v-icon start>mdi-export</v-icon> {{ t('help.dashboard.quick_actions.export_data') }}</v-chip>
    </v-chip-group>

    <h3 class="text-h6 mb-3">{{ t('help.dashboard.crawler_dialog_title') }}</h3>
    <v-table density="compact">
      <thead><tr><th>{{ t('help.dashboard.crawlerDialog.table.filter') }}</th><th>{{ t('help.dashboard.crawlerDialog.table.description') }}</th></tr></thead>
      <tbody>
        <tr><td><strong>{{ t('help.dashboard.crawlerDialog.filters.category.name') }}</strong></td><td>{{ t('help.dashboard.crawlerDialog.filters.category.description') }}</td></tr>
        <tr><td><strong>{{ t('help.dashboard.crawlerDialog.filters.country.name') }}</strong></td><td>{{ t('help.dashboard.crawlerDialog.filters.country.description') }}</td></tr>
        <tr><td><strong>{{ t('help.dashboard.crawlerDialog.filters.search.name') }}</strong></td><td>{{ t('help.dashboard.crawlerDialog.filters.search.description') }}</td></tr>
        <tr><td><strong>{{ t('help.dashboard.crawlerDialog.filters.max_count.name') }}</strong></td><td>{{ t('help.dashboard.crawlerDialog.filters.max_count.description') }}</td></tr>
        <tr><td><strong>{{ t('help.dashboard.crawlerDialog.filters.status.name') }}</strong></td><td>{{ t('help.dashboard.crawlerDialog.filters.status.description') }}</td></tr>
        <tr><td><strong>{{ t('help.dashboard.crawlerDialog.filters.source_type.name') }}</strong></td><td>{{ t('help.dashboard.crawlerDialog.filters.source_type.description') }}</td></tr>
      </tbody>
    </v-table>
    <v-alert type="warning" variant="tonal" density="compact" class="mt-3">
      <v-icon>mdi-alert</v-icon> {{ t('help.dashboard.crawlerDialog.warning') }}
    </v-alert>
  </HelpCard>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import HelpCard from './HelpCard.vue'

const { t } = useI18n()
</script>
