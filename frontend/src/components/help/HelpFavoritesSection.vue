<template>
  <HelpCard section-id="favorites" :title="t('help.favorites.title')" icon="mdi-star" color="amber">
    <p class="mb-4">
      {{ t('help.favorites.description') }}
    </p>

    <h3 class="text-h6 mb-3">{{ t('help.favorites.overview.title') }}</h3>
    <p class="mb-4">
      {{ t('help.favorites.overview.description') }}
    </p>

    <v-list density="compact" class="mb-4">
      <v-list-item prepend-icon="mdi-lightning-bolt">
        <v-list-item-title><strong>{{ t('help.favorites.overview.quickAccess') }}</strong></v-list-item-title>
        <v-list-item-subtitle>{{ t('help.favorites.overview.quickAccessDesc') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-cloud-sync">
        <v-list-item-title><strong>{{ t('help.favorites.overview.persistent') }}</strong></v-list-item-title>
        <v-list-item-subtitle>{{ t('help.favorites.overview.persistentDesc') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-view-dashboard">
        <v-list-item-title><strong>{{ t('help.favorites.overview.dashboardWidget') }}</strong></v-list-item-title>
        <v-list-item-subtitle>{{ t('help.favorites.overview.dashboardWidgetDesc') }}</v-list-item-subtitle>
      </v-list-item>
    </v-list>

    <v-divider class="my-4"></v-divider>

    <h3 class="text-h6 mb-3">{{ t('help.favorites.addFavorite.title') }}</h3>
    <p class="mb-4">{{ t('help.favorites.addFavorite.description') }}</p>

    <v-list density="compact" class="mb-4">
      <v-list-item prepend-icon="mdi-page-next">
        <v-list-item-subtitle>{{ t('help.favorites.addFavorite.methods.detailPage') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-format-list-bulleted">
        <v-list-item-subtitle>{{ t('help.favorites.addFavorite.methods.entityList') }}</v-list-item-subtitle>
      </v-list-item>
    </v-list>

    <v-alert type="info" variant="tonal" class="mb-4">
      {{ t('help.favorites.addFavorite.tip') }}
    </v-alert>

    <v-divider class="my-4"></v-divider>

    <h3 class="text-h6 mb-3">{{ t('help.favorites.removeFavorite.title') }}</h3>
    <p class="mb-4">{{ t('help.favorites.removeFavorite.description') }}</p>

    <v-list density="compact" class="mb-4">
      <v-list-item prepend-icon="mdi-star-off">
        <v-list-item-subtitle>{{ t('help.favorites.removeFavorite.methods.detailPage') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-delete">
        <v-list-item-subtitle>{{ t('help.favorites.removeFavorite.methods.managementPage') }}</v-list-item-subtitle>
      </v-list-item>
    </v-list>

    <v-divider class="my-4"></v-divider>

    <h3 class="text-h6 mb-3">{{ t('help.favorites.dashboardWidget.title') }}</h3>
    <p class="mb-4">{{ t('help.favorites.dashboardWidget.description') }}</p>

    <v-list density="compact" class="mb-4">
      <v-list-item prepend-icon="mdi-clock-outline">
        <v-list-item-subtitle>{{ t('help.favorites.dashboardWidget.features.recent') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-shape">
        <v-list-item-subtitle>{{ t('help.favorites.dashboardWidget.features.entityType') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-cursor-pointer">
        <v-list-item-subtitle>{{ t('help.favorites.dashboardWidget.features.navigation') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-link">
        <v-list-item-subtitle>{{ t('help.favorites.dashboardWidget.features.showAll') }}</v-list-item-subtitle>
      </v-list-item>
    </v-list>

    <v-divider class="my-4"></v-divider>

    <h3 class="text-h6 mb-3">{{ t('help.favorites.managementPage.title') }}</h3>
    <p class="mb-4">{{ t('help.favorites.managementPage.description') }}</p>

    <v-list density="compact" class="mb-4">
      <v-list-item prepend-icon="mdi-format-list-numbered">
        <v-list-item-subtitle>{{ t('help.favorites.managementPage.features.fullList') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-magnify">
        <v-list-item-subtitle>{{ t('help.favorites.managementPage.features.search') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-filter">
        <v-list-item-subtitle>{{ t('help.favorites.managementPage.features.filter') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-sort">
        <v-list-item-subtitle>{{ t('help.favorites.managementPage.features.sort') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-star-minus">
        <v-list-item-subtitle>{{ t('help.favorites.managementPage.features.remove') }}</v-list-item-subtitle>
      </v-list-item>
    </v-list>

    <v-divider class="my-4"></v-divider>

    <h3 class="text-h6 mb-3">{{ t('help.favorites.apiEndpoints.title') }}</h3>
    <v-table density="compact" class="mb-4">
      <thead>
        <tr>
          <th>Endpoint</th>
          <th>{{ t('common.description') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><code>GET /api/v1/favorites</code></td>
          <td>{{ t('help.favorites.apiEndpoints.list') }}</td>
        </tr>
        <tr>
          <td><code>POST /api/v1/favorites</code></td>
          <td>{{ t('help.favorites.apiEndpoints.add') }}</td>
        </tr>
        <tr>
          <td><code>GET /api/v1/favorites/check/{'{entity_id}'}</code></td>
          <td>{{ t('help.favorites.apiEndpoints.check') }}</td>
        </tr>
        <tr>
          <td><code>DELETE /api/v1/favorites/{'{favorite_id}'}</code></td>
          <td>{{ t('help.favorites.apiEndpoints.remove') }}</td>
        </tr>
        <tr>
          <td><code>DELETE /api/v1/favorites/entity/{'{entity_id}'}</code></td>
          <td>{{ t('help.favorites.apiEndpoints.removeByEntity') }}</td>
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
