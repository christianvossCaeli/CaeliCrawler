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

    <h3 class="text-h6 mb-3">{{ t('help.dashboard.widgetConfigurator.title') }}</h3>
    <v-alert type="info" variant="tonal" class="mb-3">
      <v-icon>mdi-view-dashboard-edit</v-icon>
      {{ t('help.dashboard.widgetConfigurator.description') }}
    </v-alert>
    <v-row class="mb-4">
      <v-col cols="12" md="6">
        <v-card variant="outlined" class="pa-3">
          <div class="text-subtitle-2 mb-2">{{ t('help.dashboard.widgetConfigurator.availableWidgets') }}</div>
          <v-list density="compact">
            <v-list-item prepend-icon="mdi-cube-outline">{{ t('help.dashboard.widgetConfigurator.widgets.statsEntities') }}</v-list-item>
            <v-list-item prepend-icon="mdi-tag-multiple">{{ t('help.dashboard.widgetConfigurator.widgets.statsFacets') }}</v-list-item>
            <v-list-item prepend-icon="mdi-file-document-multiple">{{ t('help.dashboard.widgetConfigurator.widgets.statsDocuments') }}</v-list-item>
            <v-list-item prepend-icon="mdi-robot">{{ t('help.dashboard.widgetConfigurator.widgets.statsCrawler') }}</v-list-item>
            <v-list-item prepend-icon="mdi-history">{{ t('help.dashboard.widgetConfigurator.widgets.activityFeed') }}</v-list-item>
          </v-list>
        </v-card>
      </v-col>
      <v-col cols="12" md="6">
        <v-card variant="outlined" class="pa-3">
          <div class="text-subtitle-2 mb-2">{{ t('help.dashboard.widgetConfigurator.moreWidgets') }}</div>
          <v-list density="compact">
            <v-list-item prepend-icon="mdi-robot-happy">{{ t('help.dashboard.widgetConfigurator.widgets.crawlerStatus') }}</v-list-item>
            <v-list-item prepend-icon="mdi-lightbulb">{{ t('help.dashboard.widgetConfigurator.widgets.insights') }}</v-list-item>
            <v-list-item prepend-icon="mdi-chart-pie">{{ t('help.dashboard.widgetConfigurator.widgets.chartDistribution') }}</v-list-item>
            <v-list-item prepend-icon="mdi-heart-pulse">{{ t('help.dashboard.widgetConfigurator.widgets.systemHealth') }}</v-list-item>
            <v-list-item prepend-icon="mdi-star">{{ t('help.dashboard.widgetConfigurator.widgets.favorites') }}</v-list-item>
          </v-list>
        </v-card>
      </v-col>
    </v-row>
    <v-chip-group class="mb-4">
      <v-chip variant="outlined" size="small">S</v-chip>
      <v-chip variant="outlined" size="small">M</v-chip>
      <v-chip variant="outlined" size="small">L</v-chip>
      <v-chip variant="outlined" size="small">XL</v-chip>
      <span class="text-caption ml-2 align-self-center">{{ t('help.dashboard.widgetConfigurator.sizes') }}</span>
    </v-chip-group>

    <h4 class="text-subtitle-1 mb-3">{{ t('help.dashboard.widgetConfigurator.widgetDetailsTitle', 'Widget-Details') }}</h4>
    <v-expansion-panels variant="accordion" class="mb-4">
      <v-expansion-panel v-for="widget in widgetKeys" :key="widget">
        <v-expansion-panel-title>
          <v-icon class="mr-2" size="small">{{ widgetIcons[widget] }}</v-icon>
          {{ t(`help.dashboard.widgetConfigurator.widgetDetails.${widget}.title`) }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <p class="mb-2">{{ t(`help.dashboard.widgetConfigurator.widgetDetails.${widget}.description`) }}</p>
          <v-row dense>
            <v-col cols="12" sm="4">
              <v-chip size="small" color="info" variant="tonal" class="mb-1">
                <v-icon start size="x-small">mdi-database</v-icon>
                {{ t(`help.dashboard.widgetConfigurator.widgetDetails.${widget}.data`) }}
              </v-chip>
            </v-col>
            <v-col cols="6" sm="4">
              <v-chip size="small" color="success" variant="tonal" class="mb-1">
                <v-icon start size="x-small">mdi-refresh</v-icon>
                {{ t(`help.dashboard.widgetConfigurator.widgetDetails.${widget}.refresh`) }}
              </v-chip>
            </v-col>
            <v-col cols="6" sm="4">
              <v-chip size="small" color="warning" variant="tonal" class="mb-1">
                <v-icon start size="x-small">mdi-resize</v-icon>
                {{ t(`help.dashboard.widgetConfigurator.widgetDetails.${widget}.size`) }}
              </v-chip>
            </v-col>
          </v-row>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

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

const widgetKeys = [
  'statsEntities',
  'statsFacets',
  'statsDocuments',
  'statsCrawler',
  'activityFeed',
  'crawlerStatus',
  'insights',
  'chartDistribution',
  'systemHealth',
  'favorites',
]

const widgetIcons: Record<string, string> = {
  statsEntities: 'mdi-cube-outline',
  statsFacets: 'mdi-tag-multiple',
  statsDocuments: 'mdi-file-document-multiple',
  statsCrawler: 'mdi-robot',
  activityFeed: 'mdi-history',
  crawlerStatus: 'mdi-robot-happy',
  insights: 'mdi-lightbulb',
  chartDistribution: 'mdi-chart-pie',
  systemHealth: 'mdi-heart-pulse',
  favorites: 'mdi-star',
}
</script>
