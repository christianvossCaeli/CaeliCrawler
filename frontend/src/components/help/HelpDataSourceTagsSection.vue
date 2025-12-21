<template>
  <HelpCard section-id="data-source-tags" :title="t('help.dataSourceTags.title')" icon="mdi-tag-multiple" color="orange">
    <p class="mb-4">{{ t('help.dataSourceTags.description') }}</p>

    <h3 class="text-h6 mb-3">{{ t('help.dataSourceTags.overview.title') }}</h3>
    <v-row class="mb-4">
      <v-col cols="12" md="6">
        <v-list density="compact">
          <v-list-item prepend-icon="mdi-map-marker">
            <v-list-item-title>{{ t('help.dataSourceTags.overview.geographic') }}</v-list-item-title>
            <v-list-item-subtitle>{{ t('help.dataSourceTags.overview.geographicDesc') }}</v-list-item-subtitle>
          </v-list-item>
          <v-list-item prepend-icon="mdi-earth">
            <v-list-item-title>{{ t('help.dataSourceTags.overview.country') }}</v-list-item-title>
            <v-list-item-subtitle>{{ t('help.dataSourceTags.overview.countryDesc') }}</v-list-item-subtitle>
          </v-list-item>
        </v-list>
      </v-col>
      <v-col cols="12" md="6">
        <v-list density="compact">
          <v-list-item prepend-icon="mdi-shape">
            <v-list-item-title>{{ t('help.dataSourceTags.overview.type') }}</v-list-item-title>
            <v-list-item-subtitle>{{ t('help.dataSourceTags.overview.typeDesc') }}</v-list-item-subtitle>
          </v-list-item>
          <v-list-item prepend-icon="mdi-tag">
            <v-list-item-title>{{ t('help.dataSourceTags.overview.topic') }}</v-list-item-title>
            <v-list-item-subtitle>{{ t('help.dataSourceTags.overview.topicDesc') }}</v-list-item-subtitle>
          </v-list-item>
        </v-list>
      </v-col>
    </v-row>

    <h3 class="text-h6 mb-3">{{ t('help.dataSourceTags.addTags.title') }}</h3>
    <v-alert type="info" variant="tonal" class="mb-4">
      {{ t('help.dataSourceTags.addTags.description') }}
    </v-alert>
    <v-table density="compact" class="mb-4">
      <thead>
        <tr>
          <th>{{ t('common.method') }}</th>
          <th>{{ t('common.description') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><v-icon size="small">mdi-pencil</v-icon> {{ t('help.dataSourceTags.addTags.manual') }}</td>
          <td>{{ t('help.dataSourceTags.addTags.manualDesc') }}</td>
        </tr>
        <tr>
          <td><v-icon size="small">mdi-file-import</v-icon> {{ t('help.dataSourceTags.addTags.bulkImport') }}</td>
          <td>{{ t('help.dataSourceTags.addTags.bulkImportDesc') }}</td>
        </tr>
        <tr>
          <td><v-icon size="small">mdi-api</v-icon> {{ t('help.dataSourceTags.addTags.apiImport') }}</td>
          <td>{{ t('help.dataSourceTags.addTags.apiImportDesc') }}</td>
        </tr>
      </tbody>
    </v-table>

    <h3 class="text-h6 mb-3">{{ t('help.dataSourceTags.categoryAssignment.title') }}</h3>
    <p class="mb-3">{{ t('help.dataSourceTags.categoryAssignment.description') }}</p>
    <v-list density="compact" class="mb-4">
      <v-list-item prepend-icon="mdi-numeric-1-circle">
        <v-list-item-subtitle>{{ t('help.dataSourceTags.categoryAssignment.step1') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-numeric-2-circle">
        <v-list-item-subtitle>{{ t('help.dataSourceTags.categoryAssignment.step2') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-numeric-3-circle">
        <v-list-item-subtitle>{{ t('help.dataSourceTags.categoryAssignment.step3') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-numeric-4-circle">
        <v-list-item-subtitle>{{ t('help.dataSourceTags.categoryAssignment.step4') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-numeric-5-circle">
        <v-list-item-subtitle>{{ t('help.dataSourceTags.categoryAssignment.step5') }}</v-list-item-subtitle>
      </v-list-item>
    </v-list>

    <h3 class="text-h6 mb-3">{{ t('help.dataSourceTags.categoryAssignment.matchModes.title') }}</h3>
    <v-row class="mb-4">
      <v-col cols="12" md="6">
        <v-card variant="outlined" class="pa-3" color="primary">
          <v-chip color="primary" class="mb-2">{{ t('help.dataSourceTags.categoryAssignment.matchModes.all') }}</v-chip>
          <div class="text-body-2">{{ t('help.dataSourceTags.categoryAssignment.matchModes.allDesc') }}</div>
        </v-card>
      </v-col>
      <v-col cols="12" md="6">
        <v-card variant="outlined" class="pa-3" color="secondary">
          <v-chip color="secondary" class="mb-2">{{ t('help.dataSourceTags.categoryAssignment.matchModes.any') }}</v-chip>
          <div class="text-body-2">{{ t('help.dataSourceTags.categoryAssignment.matchModes.anyDesc') }}</div>
        </v-card>
      </v-col>
    </v-row>

    <h3 class="text-h6 mb-3">{{ t('help.dataSourceTags.apiImport.title') }}</h3>
    <v-alert type="info" variant="tonal" class="mb-4">
      {{ t('help.dataSourceTags.apiImport.description') }}
    </v-alert>
    <v-table density="compact">
      <thead>
        <tr>
          <th>{{ t('common.importType') }}</th>
          <th>{{ t('common.description') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><v-chip size="small" color="info">{{ t('help.dataSourceTags.apiImport.wikidata') }}</v-chip></td>
          <td>{{ t('help.dataSourceTags.apiImport.wikidataDesc') }}</td>
        </tr>
        <tr>
          <td><v-chip size="small" color="success">{{ t('help.dataSourceTags.apiImport.oparl') }}</v-chip></td>
          <td>{{ t('help.dataSourceTags.apiImport.oparlDesc') }}</td>
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
