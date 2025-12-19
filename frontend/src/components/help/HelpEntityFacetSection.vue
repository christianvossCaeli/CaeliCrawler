<template>
  <HelpCard section-id="entity-facet" :title="t('help.entityFacet.title')" icon="mdi-database" color="deep-purple">
    <v-alert type="info" variant="tonal" class="mb-4">
      {{ t('help.entityFacet.newInfo') }}
    </v-alert>

    <h3 class="text-h6 mb-3">{{ t('help.entityFacet.concept.title') }}</h3>
    <p class="mb-4">
      {{ t('help.entityFacet.concept.description') }}
    </p>

    <v-row class="mb-4">
      <v-col cols="12" md="6">
        <v-card variant="outlined" class="h-100">
          <v-card-title class="text-subtitle-1">
            <v-icon class="mr-2" color="primary">mdi-cube</v-icon>
            {{ t('help.entityFacet.concept.entities.title') }}
          </v-card-title>
          <v-card-text>
            <p class="mb-2">{{ t('help.entityFacet.concept.entities.description') }}</p>
            <v-list density="compact">
              <v-list-item prepend-icon="mdi-city">
                <v-list-item-title><strong>Municipality</strong> - {{ t('help.entityFacet.concept.entities.municipality') }}</v-list-item-title>
              </v-list-item>
              <v-list-item prepend-icon="mdi-account">
                <v-list-item-title><strong>Person</strong> - {{ t('help.entityFacet.concept.entities.person') }}</v-list-item-title>
              </v-list-item>
              <v-list-item prepend-icon="mdi-domain">
                <v-list-item-title><strong>Organization</strong> - {{ t('help.entityFacet.concept.entities.organization') }}</v-list-item-title>
              </v-list-item>
              <v-list-item prepend-icon="mdi-calendar">
                <v-list-item-title><strong>Event</strong> - {{ t('help.entityFacet.concept.entities.event') }}</v-list-item-title>
              </v-list-item>
            </v-list>
            <p class="text-caption mt-2">{{ t('help.entityFacet.concept.entities.note') }}</p>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="6">
        <v-card variant="outlined" class="h-100">
          <v-card-title class="text-subtitle-1">
            <v-icon class="mr-2" color="success">mdi-tag-multiple</v-icon>
            {{ t('help.entityFacet.concept.facets.title') }}
          </v-card-title>
          <v-card-text>
            <p class="mb-2">{{ t('help.entityFacet.concept.facets.description') }}</p>
            <v-list density="compact">
              <v-list-item prepend-icon="mdi-alert-circle" color="error">
                <v-list-item-title><strong>Pain Point</strong> - {{ t('help.entityFacet.concept.facets.painPoint') }}</v-list-item-title>
              </v-list-item>
              <v-list-item prepend-icon="mdi-thumb-up" color="success">
                <v-list-item-title><strong>Positive Signal</strong> - {{ t('help.entityFacet.concept.facets.positiveSignal') }}</v-list-item-title>
              </v-list-item>
              <v-list-item prepend-icon="mdi-card-account-details">
                <v-list-item-title><strong>Contact</strong> - {{ t('help.entityFacet.concept.facets.contact') }}</v-list-item-title>
              </v-list-item>
              <v-list-item prepend-icon="mdi-calendar-check">
                <v-list-item-title><strong>Event Attendance</strong> - {{ t('help.entityFacet.concept.facets.eventAttendance') }}</v-list-item-title>
              </v-list-item>
            </v-list>
            <p class="text-caption mt-2">{{ t('help.entityFacet.concept.facets.note') }}</p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <h3 class="text-h6 mb-3">{{ t('help.entityFacet.relations.title') }}</h3>
    <p class="mb-3">{{ t('help.entityFacet.relations.description') }}</p>
    <v-table density="compact" class="mb-4">
      <thead><tr><th>{{ t('help.entityFacet.relations.tableHeaders.relationType') }}</th><th>{{ t('help.entityFacet.relations.tableHeaders.description') }}</th><th>{{ t('help.entityFacet.relations.tableHeaders.example') }}</th></tr></thead>
      <tbody>
        <tr>
          <td><strong>{{ t('help.entityFacet.relations.types.worksFor') }}</strong></td>
          <td>{{ t('help.entityFacet.relations.types.worksForDesc') }}</td>
          <td>{{ t('help.entityFacet.relations.types.worksForExample') }}</td>
        </tr>
        <tr>
          <td><strong>{{ t('help.entityFacet.relations.types.memberOf') }}</strong></td>
          <td>{{ t('help.entityFacet.relations.types.memberOfDesc') }}</td>
          <td>{{ t('help.entityFacet.relations.types.memberOfExample') }}</td>
        </tr>
        <tr>
          <td><strong>{{ t('help.entityFacet.relations.types.attends') }}</strong></td>
          <td>{{ t('help.entityFacet.relations.types.attendsDesc') }}</td>
          <td>{{ t('help.entityFacet.relations.types.attendsExample') }}</td>
        </tr>
        <tr>
          <td><strong>{{ t('help.entityFacet.relations.types.organizes') }}</strong></td>
          <td>{{ t('help.entityFacet.relations.types.organizesDesc') }}</td>
          <td>{{ t('help.entityFacet.relations.types.organizesExample') }}</td>
        </tr>
      </tbody>
    </v-table>

    <h3 class="text-h6 mb-3">{{ t('help.entityFacet.timeBased.title') }}</h3>
    <v-alert type="warning" variant="tonal" class="mb-4">
      {{ t('help.entityFacet.timeBased.info') }}
      <v-list density="compact" class="bg-transparent">
        <v-list-item prepend-icon="mdi-calendar-arrow-right">
          <v-list-item-title>{{ t('help.entityFacet.timeBased.futureOnly') }}</v-list-item-title>
        </v-list-item>
        <v-list-item prepend-icon="mdi-calendar-arrow-left">
          <v-list-item-title>{{ t('help.entityFacet.timeBased.pastOnly') }}</v-list-item-title>
        </v-list-item>
        <v-list-item prepend-icon="mdi-calendar-range">
          <v-list-item-title>{{ t('help.entityFacet.timeBased.all') }}</v-list-item-title>
        </v-list-item>
      </v-list>
    </v-alert>

    <h3 class="text-h6 mb-3">{{ t('help.entityFacet.analysisTemplates.title') }}</h3>
    <p class="mb-3">
      {{ t('help.entityFacet.analysisTemplates.description') }}
    </p>
    <v-expansion-panels variant="accordion" class="mb-4">
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon class="mr-2">mdi-chart-timeline-variant</v-icon>
          {{ t('help.entityFacet.analysisTemplates.painPoint.title') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <p>{{ t('help.entityFacet.analysisTemplates.painPoint.description') }}</p>
          <v-list density="compact">
            <v-list-item>Primary Entity Type: <strong>Municipality</strong></v-list-item>
            <v-list-item>Aktive Facets: Pain Point, Positive Signal</v-list-item>
            <v-list-item>Gruppierung: Nach Gemeinde</v-list-item>
            <v-list-item>Sortierung: Nach Opportunity Score</v-list-item>
          </v-list>
        </v-expansion-panel-text>
      </v-expansion-panel>
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon class="mr-2">mdi-calendar-multiple</v-icon>
          {{ t('help.entityFacet.analysisTemplates.eventTracking.title') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <p>{{ t('help.entityFacet.analysisTemplates.eventTracking.description') }}</p>
          <v-list density="compact">
            <v-list-item>Primary Entity Type: <strong>Event</strong></v-list-item>
            <v-list-item>Aktive Facets: Event Attendance</v-list-item>
            <v-list-item>Zeitfilter: future_only (nur anstehende Events)</v-list-item>
            <v-list-item>Verknuepfungen: Person attends Event</v-list-item>
          </v-list>
        </v-expansion-panel-text>
      </v-expansion-panel>
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon class="mr-2">mdi-account-network</v-icon>
          {{ t('help.entityFacet.analysisTemplates.decisionMakerProfile.title') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <p>{{ t('help.entityFacet.analysisTemplates.decisionMakerProfile.description') }}</p>
          <v-list density="compact">
            <v-list-item>Primary Entity Type: <strong>Person</strong></v-list-item>
            <v-list-item>Aktive Facets: Contact, Event Attendance</v-list-item>
            <v-list-item>Verknuepfungen: works_for Municipality, member_of Organization</v-list-item>
          </v-list>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <h3 class="text-h6 mb-3">{{ t('help.entityFacet.entitiesView.title') }}</h3>
    <p class="mb-3">{{ t('help.entityFacet.entitiesView.description') }}</p>
    <v-table density="compact" class="mb-4">
      <thead><tr><th>{{ t('help.entityFacet.entitiesView.tableHeaders.function') }}</th><th>{{ t('help.entityFacet.entitiesView.tableHeaders.description') }}</th></tr></thead>
      <tbody>
        <tr><td><strong>{{ t('help.entityFacet.entitiesView.functions.entityTypeTabs') }}</strong></td><td>{{ t('help.entityFacet.entitiesView.functions.entityTypeTabsDesc') }}</td></tr>
        <tr><td><strong>{{ t('help.entityFacet.entitiesView.functions.tableCardView') }}</strong></td><td>{{ t('help.entityFacet.entitiesView.functions.tableCardViewDesc') }}</td></tr>
        <tr><td><strong>{{ t('help.entityFacet.entitiesView.functions.filter') }}</strong></td><td>{{ t('help.entityFacet.entitiesView.functions.filterDesc') }}</td></tr>
        <tr><td><strong>{{ t('help.entityFacet.entitiesView.functions.facetOverview') }}</strong></td><td>{{ t('help.entityFacet.entitiesView.functions.facetOverviewDesc') }}</td></tr>
      </tbody>
    </v-table>

    <h3 class="text-h6 mb-3">{{ t('help.entityFacet.entityDetailView.title') }}</h3>
    <p class="mb-3">{{ t('help.entityFacet.entityDetailView.description') }}</p>
    <v-row class="mb-4">
      <v-col cols="12" md="6">
        <v-card variant="outlined">
          <v-card-title class="text-subtitle-1">{{ t('help.entityFacet.entityDetailView.tabsTitle') }}</v-card-title>
          <v-card-text>
            <v-list density="compact">
              <v-list-item prepend-icon="mdi-tag-multiple">{{ t('help.entityFacet.entityDetailView.tabs.facets') }}</v-list-item>
              <v-list-item prepend-icon="mdi-link">{{ t('help.entityFacet.entityDetailView.tabs.relations') }}</v-list-item>
              <v-list-item prepend-icon="mdi-web">{{ t('help.entityFacet.entityDetailView.tabs.dataSources') }}</v-list-item>
              <v-list-item prepend-icon="mdi-file-document-multiple">{{ t('help.entityFacet.entityDetailView.tabs.documents') }}</v-list-item>
              <v-list-item prepend-icon="mdi-database-sync">{{ t('help.entityFacet.entityDetailView.tabs.pysis') }}</v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="6">
        <v-card variant="outlined">
          <v-card-title class="text-subtitle-1">{{ t('help.entityFacet.entityDetailView.actionsTitle') }}</v-card-title>
          <v-card-text>
            <v-list density="compact">
              <v-list-item prepend-icon="mdi-plus">{{ t('help.entityFacet.entityDetailView.actions.addFacet') }}</v-list-item>
              <v-list-item prepend-icon="mdi-check">{{ t('help.entityFacet.entityDetailView.actions.verify') }}</v-list-item>
              <v-list-item prepend-icon="mdi-pencil">{{ t('help.entityFacet.entityDetailView.actions.edit') }}</v-list-item>
              <v-list-item prepend-icon="mdi-play">{{ t('help.entityFacet.entityDetailView.actions.startCrawl') }}</v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <h3 class="text-h6 mb-3">{{ t('help.entityFacet.aiIntegration.title') }}</h3>
    <p class="mb-3">
      {{ t('help.entityFacet.aiIntegration.description') }}
    </p>
    <v-list density="compact" class="mb-4">
      <v-list-item prepend-icon="mdi-robot">
        <v-list-item-title><strong>{{ t('help.entityFacet.aiIntegration.automaticExtraction.title') }}</strong></v-list-item-title>
        <v-list-item-subtitle>{{ t('help.entityFacet.aiIntegration.automaticExtraction.description') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-text-box-search">
        <v-list-item-title><strong>{{ t('help.entityFacet.aiIntegration.facetPrompts.title') }}</strong></v-list-item-title>
        <v-list-item-subtitle>{{ t('help.entityFacet.aiIntegration.facetPrompts.description') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-percent">
        <v-list-item-title><strong>{{ t('help.entityFacet.aiIntegration.confidenceRating.title') }}</strong></v-list-item-title>
        <v-list-item-subtitle>{{ t('help.entityFacet.aiIntegration.confidenceRating.description') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-check-decagram">
        <v-list-item-title><strong>{{ t('help.entityFacet.aiIntegration.humanInLoop.title') }}</strong></v-list-item-title>
        <v-list-item-subtitle>{{ t('help.entityFacet.aiIntegration.humanInLoop.description') }}</v-list-item-subtitle>
      </v-list-item>
    </v-list>

    <h3 class="text-h6 mb-3">{{ t('help.entityFacet.bestPractices.title') }}</h3>
    <v-alert type="success" variant="tonal">
      <v-list density="compact" class="bg-transparent">
        <v-list-item prepend-icon="mdi-lightbulb">
          <v-list-item-title>{{ t('help.entityFacet.bestPractices.items.predefinedTypes') }}</v-list-item-title>
        </v-list-item>
        <v-list-item prepend-icon="mdi-lightbulb">
          <v-list-item-title>{{ t('help.entityFacet.bestPractices.items.useTemplates') }}</v-list-item-title>
        </v-list-item>
        <v-list-item prepend-icon="mdi-lightbulb">
          <v-list-item-title>{{ t('help.entityFacet.bestPractices.items.verifyResults') }}</v-list-item-title>
        </v-list-item>
        <v-list-item prepend-icon="mdi-lightbulb">
          <v-list-item-title>{{ t('help.entityFacet.bestPractices.items.timeFilters') }}</v-list-item-title>
        </v-list-item>
      </v-list>
    </v-alert>
  </HelpCard>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import HelpCard from './HelpCard.vue'

const { t } = useI18n()
</script>
