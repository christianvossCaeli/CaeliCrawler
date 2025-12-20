<template>
  <HelpCard section-id="facet-type-admin" :title="t('help.facetTypeAdmin.title')" icon="mdi-tag-multiple" color="teal">
    <v-alert type="info" variant="tonal" class="mb-4">
      {{ t('help.facetTypeAdmin.accessInfo') }}
    </v-alert>

    <p class="mb-4">{{ t('help.facetTypeAdmin.description') }}</p>

    <h3 class="text-h6 mb-3">{{ t('help.facetTypeAdmin.overview.title') }}</h3>
    <p class="mb-2">{{ t('help.facetTypeAdmin.overview.description') }}</p>
    <v-list density="compact" class="mb-4">
      <v-list-item prepend-icon="mdi-format-list-bulleted">
        <v-list-item-title>{{ t('help.facetTypeAdmin.overview.features.list') }}</v-list-item-title>
      </v-list-item>
      <v-list-item prepend-icon="mdi-plus">
        <v-list-item-title>{{ t('help.facetTypeAdmin.overview.features.create') }}</v-list-item-title>
      </v-list-item>
      <v-list-item prepend-icon="mdi-pencil">
        <v-list-item-title>{{ t('help.facetTypeAdmin.overview.features.edit') }}</v-list-item-title>
      </v-list-item>
      <v-list-item prepend-icon="mdi-link-variant">
        <v-list-item-title>{{ t('help.facetTypeAdmin.overview.features.assign') }}</v-list-item-title>
      </v-list-item>
      <v-list-item prepend-icon="mdi-robot">
        <v-list-item-title>{{ t('help.facetTypeAdmin.overview.features.aiExtraction') }}</v-list-item-title>
      </v-list-item>
    </v-list>

    <h3 class="text-h6 mb-3">{{ t('help.facetTypeAdmin.concept.title') }}</h3>
    <p class="mb-3">{{ t('help.facetTypeAdmin.concept.description') }}</p>
    <v-row class="mb-4">
      <v-col cols="12" md="4">
        <v-card variant="outlined" class="pa-3 text-center h-100">
          <v-icon color="success" size="x-large">mdi-source-branch</v-icon>
          <div class="text-subtitle-1 mt-2">{{ t('help.facetTypeAdmin.concept.inheritance') }}</div>
          <div class="text-caption">{{ t('help.facetTypeAdmin.concept.inheritanceDesc') }}</div>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card variant="outlined" class="pa-3 text-center h-100">
          <v-icon color="primary" size="x-large">mdi-checkbox-multiple-marked</v-icon>
          <div class="text-subtitle-1 mt-2">{{ t('help.facetTypeAdmin.concept.consistency') }}</div>
          <div class="text-caption">{{ t('help.facetTypeAdmin.concept.consistencyDesc') }}</div>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card variant="outlined" class="pa-3 text-center h-100">
          <v-icon color="warning" size="x-large">mdi-lightning-bolt</v-icon>
          <div class="text-subtitle-1 mt-2">{{ t('help.facetTypeAdmin.concept.efficiency') }}</div>
          <div class="text-caption">{{ t('help.facetTypeAdmin.concept.efficiencyDesc') }}</div>
        </v-card>
      </v-col>
    </v-row>

    <h3 class="text-h6 mb-3">{{ t('help.facetTypeAdmin.createFacetType.title') }}</h3>
    <v-expansion-panels variant="accordion" class="mb-4">
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon class="mr-2">mdi-form-textbox</v-icon>
          {{ t('help.facetTypeAdmin.createFacetType.basicSettings.title') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-table density="compact">
            <thead><tr><th>{{ t('help.facetTypeAdmin.createFacetType.basicSettings.name') }}</th><th>{{ t('help.dashboard.crawler_dialog.table.description') }}</th></tr></thead>
            <tbody>
              <tr><td><strong>{{ t('help.facetTypeAdmin.createFacetType.basicSettings.name') }}</strong></td><td>{{ t('help.facetTypeAdmin.createFacetType.basicSettings.nameDesc') }}</td></tr>
              <tr><td><strong>{{ t('help.facetTypeAdmin.createFacetType.basicSettings.namePlural') }}</strong></td><td>{{ t('help.facetTypeAdmin.createFacetType.basicSettings.namePluralDesc') }}</td></tr>
              <tr><td><strong>{{ t('help.facetTypeAdmin.createFacetType.basicSettings.slug') }}</strong></td><td>{{ t('help.facetTypeAdmin.createFacetType.basicSettings.slugDesc') }}</td></tr>
              <tr><td><strong>{{ t('help.facetTypeAdmin.createFacetType.basicSettings.description') }}</strong></td><td>{{ t('help.facetTypeAdmin.createFacetType.basicSettings.descriptionDesc') }}</td></tr>
              <tr><td><strong>{{ t('help.facetTypeAdmin.createFacetType.basicSettings.icon') }}</strong></td><td>{{ t('help.facetTypeAdmin.createFacetType.basicSettings.iconDesc') }}</td></tr>
              <tr><td><strong>{{ t('help.facetTypeAdmin.createFacetType.basicSettings.color') }}</strong></td><td>{{ t('help.facetTypeAdmin.createFacetType.basicSettings.colorDesc') }}</td></tr>
            </tbody>
          </v-table>
        </v-expansion-panel-text>
      </v-expansion-panel>
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon class="mr-2">mdi-format-list-checks</v-icon>
          {{ t('help.facetTypeAdmin.createFacetType.valueType.title') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-list density="compact">
            <v-list-item>
              <v-list-item-title><strong>{{ t('help.facetTypeAdmin.createFacetType.valueType.structured') }}</strong></v-list-item-title>
              <v-list-item-subtitle>{{ t('help.facetTypeAdmin.createFacetType.valueType.structuredDesc') }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title><strong>{{ t('help.facetTypeAdmin.createFacetType.valueType.text') }}</strong></v-list-item-title>
              <v-list-item-subtitle>{{ t('help.facetTypeAdmin.createFacetType.valueType.textDesc') }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title><strong>{{ t('help.facetTypeAdmin.createFacetType.valueType.number') }}</strong></v-list-item-title>
              <v-list-item-subtitle>{{ t('help.facetTypeAdmin.createFacetType.valueType.numberDesc') }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title><strong>{{ t('help.facetTypeAdmin.createFacetType.valueType.boolean') }}</strong></v-list-item-title>
              <v-list-item-subtitle>{{ t('help.facetTypeAdmin.createFacetType.valueType.booleanDesc') }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title><strong>{{ t('help.facetTypeAdmin.createFacetType.valueType.date') }}</strong></v-list-item-title>
              <v-list-item-subtitle>{{ t('help.facetTypeAdmin.createFacetType.valueType.dateDesc') }}</v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-expansion-panel-text>
      </v-expansion-panel>
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon class="mr-2">mdi-link-variant</v-icon>
          {{ t('help.facetTypeAdmin.createFacetType.entityTypeAssignment.title') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <p class="mb-2">{{ t('help.facetTypeAdmin.createFacetType.entityTypeAssignment.description') }}</p>
          <v-list density="compact">
            <v-list-item prepend-icon="mdi-select-all">
              <v-list-item-title><strong>{{ t('help.facetTypeAdmin.createFacetType.entityTypeAssignment.allTypes') }}</strong></v-list-item-title>
              <v-list-item-subtitle>{{ t('help.facetTypeAdmin.createFacetType.entityTypeAssignment.allTypesDesc') }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item prepend-icon="mdi-select-group">
              <v-list-item-title><strong>{{ t('help.facetTypeAdmin.createFacetType.entityTypeAssignment.specificTypes') }}</strong></v-list-item-title>
              <v-list-item-subtitle>{{ t('help.facetTypeAdmin.createFacetType.entityTypeAssignment.specificTypesDesc') }}</v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <h3 class="text-h6 mb-3">{{ t('help.facetTypeAdmin.schema.title') }}</h3>
    <p class="mb-2">{{ t('help.facetTypeAdmin.schema.description') }}</p>
    <v-card variant="outlined" class="mb-4 pa-3">
      <div class="text-caption mb-1">{{ t('help.facetTypeAdmin.schema.example') }}</div>
      <code class="text-body-2 text-pre-wrap">{{ t('help.facetTypeAdmin.schema.exampleSchema') }}</code>
    </v-card>
    <v-alert type="info" variant="tonal" density="compact" class="mb-4">
      {{ t('help.facetTypeAdmin.schema.tip') }}
    </v-alert>

    <h3 class="text-h6 mb-3">{{ t('help.facetTypeAdmin.aiExtraction.title') }}</h3>
    <v-table density="compact" class="mb-4">
      <tbody>
        <tr>
          <td><strong>{{ t('help.facetTypeAdmin.aiExtraction.enabled') }}</strong></td>
          <td>{{ t('help.facetTypeAdmin.aiExtraction.enabledDesc') }}</td>
        </tr>
        <tr>
          <td><strong>{{ t('help.facetTypeAdmin.aiExtraction.prompt') }}</strong></td>
          <td>{{ t('help.facetTypeAdmin.aiExtraction.promptDesc') }}</td>
        </tr>
        <tr>
          <td><strong>{{ t('help.facetTypeAdmin.aiExtraction.timeBased') }}</strong></td>
          <td>{{ t('help.facetTypeAdmin.aiExtraction.timeBasedDesc') }}</td>
        </tr>
      </tbody>
    </v-table>
    <v-card variant="outlined" class="mb-4 pa-3 bg-blue-grey-lighten-5">
      <div class="text-caption text-medium-emphasis">{{ t('help.facetTypeAdmin.aiExtraction.promptExample') }}</div>
    </v-card>

    <h3 class="text-h6 mb-3">{{ t('help.facetTypeAdmin.entityTypesView.title') }}</h3>
    <p class="mb-2">{{ t('help.facetTypeAdmin.entityTypesView.description') }}</p>
    <v-list density="compact">
      <v-list-item prepend-icon="mdi-table-column">
        <v-list-item-title>{{ t('help.facetTypeAdmin.entityTypesView.features.facetColumn') }}</v-list-item-title>
      </v-list-item>
      <v-list-item prepend-icon="mdi-palette">
        <v-list-item-title>{{ t('help.facetTypeAdmin.entityTypesView.features.colorCoded') }}</v-list-item-title>
      </v-list-item>
      <v-list-item prepend-icon="mdi-flash">
        <v-list-item-title>{{ t('help.facetTypeAdmin.entityTypesView.features.quickAssign') }}</v-list-item-title>
      </v-list-item>
    </v-list>
  </HelpCard>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import HelpCard from './HelpCard.vue'

const { t } = useI18n()
</script>
