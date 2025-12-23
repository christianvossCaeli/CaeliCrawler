<template>
  <HelpCard section-id="facet-history" :title="t('help.facetHistory.title')" icon="mdi-chart-timeline" color="info">
    <p class="mb-4">{{ t('help.facetHistory.description') }}</p>

    <h3 class="text-h6 mb-3">{{ t('help.facetHistory.overview.title') }}</h3>
    <v-alert type="info" variant="tonal" class="mb-4">
      {{ t('help.facetHistory.overview.description') }}
    </v-alert>

    <h3 class="text-h6 mb-3">{{ t('help.facetHistory.timeRanges.title') }}</h3>
    <p class="mb-3">{{ t('help.facetHistory.timeRanges.description') }}</p>
    <v-chip-group class="mb-4">
      <v-chip variant="outlined">7T</v-chip>
      <v-chip variant="outlined">30T</v-chip>
      <v-chip variant="outlined">90T</v-chip>
      <v-chip variant="outlined">1J</v-chip>
      <v-chip variant="outlined" color="primary">{{ t('common.all') }}</v-chip>
    </v-chip-group>

    <h3 class="text-h6 mb-3">{{ t('help.facetHistory.statistics.title') }}</h3>
    <v-row class="mb-4">
      <v-col cols="6" md="3">
        <v-card variant="outlined" class="pa-3 text-center">
          <v-icon color="primary" size="large">mdi-clock</v-icon>
          <div class="text-subtitle-2 mt-1">{{ t('help.facetHistory.statistics.current') }}</div>
          <div class="text-caption text-medium-emphasis">{{ t('help.facetHistory.statistics.currentDesc') }}</div>
        </v-card>
      </v-col>
      <v-col cols="6" md="3">
        <v-card variant="outlined" class="pa-3 text-center">
          <v-icon color="success" size="large">mdi-trending-up</v-icon>
          <div class="text-subtitle-2 mt-1">{{ t('help.facetHistory.statistics.change') }}</div>
          <div class="text-caption text-medium-emphasis">{{ t('help.facetHistory.statistics.changeDesc') }}</div>
        </v-card>
      </v-col>
      <v-col cols="6" md="3">
        <v-card variant="outlined" class="pa-3 text-center">
          <v-icon color="info" size="large">mdi-arrow-down</v-icon>
          <div class="text-subtitle-2 mt-1">{{ t('help.facetHistory.statistics.minimum') }}</div>
          <div class="text-caption text-medium-emphasis">{{ t('help.facetHistory.statistics.minimumDesc') }}</div>
        </v-card>
      </v-col>
      <v-col cols="6" md="3">
        <v-card variant="outlined" class="pa-3 text-center">
          <v-icon color="warning" size="large">mdi-arrow-up</v-icon>
          <div class="text-subtitle-2 mt-1">{{ t('help.facetHistory.statistics.maximum') }}</div>
          <div class="text-caption text-medium-emphasis">{{ t('help.facetHistory.statistics.maximumDesc') }}</div>
        </v-card>
      </v-col>
    </v-row>

    <h3 class="text-h6 mb-3">{{ t('help.facetHistory.trends.title') }}</h3>
    <v-table density="compact" class="mb-4">
      <thead>
        <tr>
          <th>{{ t('help.facetHistory.trends.table.indicator') }}</th>
          <th>{{ t('help.facetHistory.trends.table.meaning') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>
            <v-chip color="success" size="small">
              <v-icon start size="small">mdi-trending-up</v-icon>
              +5.2%
            </v-chip>
          </td>
          <td>{{ t('help.facetHistory.trends.up') }}</td>
        </tr>
        <tr>
          <td>
            <v-chip color="error" size="small">
              <v-icon start size="small">mdi-trending-down</v-icon>
              -3.1%
            </v-chip>
          </td>
          <td>{{ t('help.facetHistory.trends.down') }}</td>
        </tr>
        <tr>
          <td>
            <v-chip color="grey" size="small">
              <v-icon start size="small">mdi-trending-neutral</v-icon>
              0.0%
            </v-chip>
          </td>
          <td>{{ t('help.facetHistory.trends.neutral') }}</td>
        </tr>
      </tbody>
    </v-table>

    <h3 class="text-h6 mb-3">{{ t('help.facetHistory.actions.title') }}</h3>
    <v-list density="compact" class="mb-4">
      <v-list-item prepend-icon="mdi-plus">
        <v-list-item-title>{{ t('help.facetHistory.actions.addDataPoint') }}</v-list-item-title>
        <v-list-item-subtitle>{{ t('help.facetHistory.actions.addDataPointDesc') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-download">
        <v-list-item-title>{{ t('help.facetHistory.actions.export') }}</v-list-item-title>
        <v-list-item-subtitle>{{ t('help.facetHistory.actions.exportDesc') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-refresh">
        <v-list-item-title>{{ t('help.facetHistory.actions.refresh') }}</v-list-item-title>
        <v-list-item-subtitle>{{ t('help.facetHistory.actions.refreshDesc') }}</v-list-item-subtitle>
      </v-list-item>
    </v-list>

    <h3 class="text-h6 mb-3">{{ t('help.facetHistory.tracks.title') }}</h3>
    <v-alert type="success" variant="tonal" density="compact" class="mb-4">
      <v-icon>mdi-chart-multiple</v-icon>
      {{ t('help.facetHistory.tracks.description') }}
    </v-alert>

    <h3 class="text-h6 mb-3">{{ t('help.facetHistory.addDialog.title') }}</h3>
    <v-card variant="outlined" class="pa-3 mb-4">
      <v-list density="compact">
        <v-list-item prepend-icon="mdi-numeric">
          <v-list-item-title>{{ t('help.facetHistory.addDialog.value') }}</v-list-item-title>
        </v-list-item>
        <v-list-item prepend-icon="mdi-calendar-clock">
          <v-list-item-title>{{ t('help.facetHistory.addDialog.timestamp') }}</v-list-item-title>
        </v-list-item>
        <v-list-item prepend-icon="mdi-tag">
          <v-list-item-title>{{ t('help.facetHistory.addDialog.track') }}</v-list-item-title>
        </v-list-item>
        <v-list-item prepend-icon="mdi-note-text">
          <v-list-item-title>{{ t('help.facetHistory.addDialog.note') }}</v-list-item-title>
        </v-list-item>
      </v-list>
    </v-card>
  </HelpCard>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import HelpCard from './HelpCard.vue'

const { t } = useI18n()
</script>
