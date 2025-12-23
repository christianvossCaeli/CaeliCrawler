<template>
  <HelpCard section-id="entity-map" :title="t('help.entityMapView.title')" icon="mdi-map" color="success">
    <p class="mb-4">{{ t('help.entityMapView.description') }}</p>

    <h3 class="text-h6 mb-3">{{ t('help.entityMapView.overview.title') }}</h3>
    <v-alert type="info" variant="tonal" class="mb-4">
      {{ t('help.entityMapView.overview.description') }}
    </v-alert>

    <h3 class="text-h6 mb-3">{{ t('help.entityMapView.features.title') }}</h3>
    <v-row class="mb-4">
      <v-col cols="12" md="6">
        <v-card variant="outlined" class="pa-3">
          <div class="text-subtitle-1 mb-2">
            <v-icon class="mr-1" color="primary">mdi-map-marker-multiple</v-icon>
            {{ t('help.entityMapView.features.points.title') }}
          </div>
          <v-list density="compact">
            <v-list-item prepend-icon="mdi-dots-circle">
              {{ t('help.entityMapView.features.points.clustering') }}
            </v-list-item>
            <v-list-item prepend-icon="mdi-gesture-tap">
              {{ t('help.entityMapView.features.points.popup') }}
            </v-list-item>
            <v-list-item prepend-icon="mdi-magnify-plus">
              {{ t('help.entityMapView.features.points.zoom') }}
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>
      <v-col cols="12" md="6">
        <v-card variant="outlined" class="pa-3">
          <div class="text-subtitle-1 mb-2">
            <v-icon class="mr-1" color="success">mdi-vector-polygon</v-icon>
            {{ t('help.entityMapView.features.polygons.title') }}
          </div>
          <v-list density="compact">
            <v-list-item prepend-icon="mdi-shape-polygon-plus">
              {{ t('help.entityMapView.features.polygons.regions') }}
            </v-list-item>
            <v-list-item prepend-icon="mdi-cursor-default-click">
              {{ t('help.entityMapView.features.polygons.hover') }}
            </v-list-item>
            <v-list-item prepend-icon="mdi-border-color">
              {{ t('help.entityMapView.features.polygons.styling') }}
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>
    </v-row>

    <h3 class="text-h6 mb-3">{{ t('help.entityMapView.clustering.title') }}</h3>
    <p class="mb-3">{{ t('help.entityMapView.clustering.description') }}</p>
    <v-row class="mb-4">
      <v-col cols="4">
        <v-card variant="outlined" class="pa-3 text-center">
          <div class="cluster-example cluster-example--small mx-auto mb-2"></div>
          <div class="text-caption">&lt; 100 {{ t('help.entityMapView.clustering.entities') }}</div>
        </v-card>
      </v-col>
      <v-col cols="4">
        <v-card variant="outlined" class="pa-3 text-center">
          <div class="cluster-example cluster-example--medium mx-auto mb-2"></div>
          <div class="text-caption">100-1000 {{ t('help.entityMapView.clustering.entities') }}</div>
        </v-card>
      </v-col>
      <v-col cols="4">
        <v-card variant="outlined" class="pa-3 text-center">
          <div class="cluster-example cluster-example--large mx-auto mb-2"></div>
          <div class="text-caption">&gt; 1000 {{ t('help.entityMapView.clustering.entities') }}</div>
        </v-card>
      </v-col>
    </v-row>

    <h3 class="text-h6 mb-3">{{ t('help.entityMapView.filters.title') }}</h3>
    <v-table density="compact" class="mb-4">
      <thead>
        <tr>
          <th>{{ t('help.entityMapView.filters.table.filter') }}</th>
          <th>{{ t('help.entityMapView.filters.table.description') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>{{ t('help.entityMapView.filters.entityType.name') }}</strong></td>
          <td>{{ t('help.entityMapView.filters.entityType.description') }}</td>
        </tr>
        <tr>
          <td><strong>{{ t('help.entityMapView.filters.country.name') }}</strong></td>
          <td>{{ t('help.entityMapView.filters.country.description') }}</td>
        </tr>
        <tr>
          <td><strong>{{ t('help.entityMapView.filters.adminLevel1.name') }}</strong></td>
          <td>{{ t('help.entityMapView.filters.adminLevel1.description') }}</td>
        </tr>
        <tr>
          <td><strong>{{ t('help.entityMapView.filters.adminLevel2.name') }}</strong></td>
          <td>{{ t('help.entityMapView.filters.adminLevel2.description') }}</td>
        </tr>
        <tr>
          <td><strong>{{ t('help.entityMapView.filters.search.name') }}</strong></td>
          <td>{{ t('help.entityMapView.filters.search.description') }}</td>
        </tr>
      </tbody>
    </v-table>

    <h3 class="text-h6 mb-3">{{ t('help.entityMapView.interaction.title') }}</h3>
    <v-list density="compact" class="mb-4">
      <v-list-item prepend-icon="mdi-gesture-tap">
        <v-list-item-title>{{ t('help.entityMapView.interaction.clickCluster') }}</v-list-item-title>
      </v-list-item>
      <v-list-item prepend-icon="mdi-map-marker">
        <v-list-item-title>{{ t('help.entityMapView.interaction.clickEntity') }}</v-list-item-title>
      </v-list-item>
      <v-list-item prepend-icon="mdi-eye">
        <v-list-item-title>{{ t('help.entityMapView.interaction.viewDetails') }}</v-list-item-title>
      </v-list-item>
      <v-list-item prepend-icon="mdi-navigation">
        <v-list-item-title>{{ t('help.entityMapView.interaction.navigation') }}</v-list-item-title>
      </v-list-item>
    </v-list>

    <h3 class="text-h6 mb-3">{{ t('help.entityMapView.darkMode.title') }}</h3>
    <v-alert type="success" variant="tonal" density="compact">
      <v-icon>mdi-theme-light-dark</v-icon>
      {{ t('help.entityMapView.darkMode.description') }}
    </v-alert>
  </HelpCard>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import HelpCard from './HelpCard.vue'

const { t } = useI18n()
</script>

<style scoped>
.cluster-example {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 3px solid rgba(255, 255, 255, 0.9);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.cluster-example--small {
  width: 28px;
  height: 28px;
  background-color: #2E7D32;
}

.cluster-example--medium {
  width: 36px;
  height: 36px;
  background-color: #113634;
}

.cluster-example--large {
  width: 44px;
  height: 44px;
  background-color: #5c6bc0;
}
</style>
