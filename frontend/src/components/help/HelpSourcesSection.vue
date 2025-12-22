<template>
  <HelpCard section-id="sources" :title="t('help.sources.title')" icon="mdi-web" color="teal">
    <p class="mb-4">{{ t('help.sources.description') }}</p>

    <h3 class="text-h6 mb-3">{{ t('help.sources.categoryAssignment.title') }}</h3>
    <v-alert type="info" variant="tonal" class="mb-3" :text="t('help.sources.categoryAssignment.info')" />
    <v-list density="compact" class="mb-4">
      <v-list-item prepend-icon="mdi-link-variant">
        <v-list-item-title>{{ t('help.sources.categoryAssignment.multipleAssignment') }}</v-list-item-title>
        <v-list-item-subtitle>{{ t('help.sources.categoryAssignment.multipleAssignmentDesc') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-play-circle">
        <v-list-item-title>{{ t('help.sources.categoryAssignment.crawlContext') }}</v-list-item-title>
        <v-list-item-subtitle>{{ t('help.sources.categoryAssignment.crawlContextDesc') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-brain">
        <v-list-item-title>{{ t('help.sources.categoryAssignment.smartQueryIntegration') }}</v-list-item-title>
        <v-list-item-subtitle>{{ t('help.sources.categoryAssignment.smartQueryIntegrationDesc') }}</v-list-item-subtitle>
      </v-list-item>
    </v-list>

    <h3 class="text-h6 mb-3">{{ t('help.sources.sourceTypes.title') }}</h3>
    <v-row class="mb-4">
      <v-col cols="12" md="4">
        <v-card variant="outlined" class="pa-3">
          <v-chip color="primary" class="mb-2">{{ t('help.sources.sourceTypes.website') }}</v-chip>
          <div class="text-body-2">{{ t('help.sources.sourceTypes.websiteDesc') }}</div>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card variant="outlined" class="pa-3">
          <v-chip color="success" class="mb-2">{{ t('help.sources.sourceTypes.oparlApi') }}</v-chip>
          <div class="text-body-2">{{ t('help.sources.sourceTypes.oparlApiDesc') }}</div>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card variant="outlined" class="pa-3">
          <v-chip color="warning" class="mb-2">{{ t('help.sources.sourceTypes.rss') }}</v-chip>
          <div class="text-body-2">{{ t('help.sources.sourceTypes.rssDesc') }}</div>
        </v-card>
      </v-col>
    </v-row>

    <h3 class="text-h6 mb-3">{{ t('help.sources.availableFilters') }}</h3>
    <p class="mb-3">{{ t('help.sources.filterDescription', 'Land, Gemeinde, Kategorie, Status, Suche') }}</p>

    <h3 class="text-h6 mb-3">{{ t('help.sources.actions.title') }}</h3>
    <v-table density="compact" class="mb-4">
      <thead><tr><th>{{ t('common.button') }}</th><th>{{ t('common.description') }}</th></tr></thead>
      <tbody>
        <tr><td><v-chip size="small" color="secondary">{{ t('help.sources.actions.bulkImport') }}</v-chip></td><td>{{ t('help.sources.actions.bulkImportDesc') }}</td></tr>
        <tr><td><v-chip size="small" color="primary">{{ t('help.sources.actions.newSource') }}</v-chip></td><td>{{ t('help.sources.actions.newSourceDesc') }}</td></tr>
        <tr><td><v-icon size="small">mdi-pencil</v-icon> {{ t('help.sources.actions.edit') }}</td><td>{{ t('help.sources.actions.editDesc') }}</td></tr>
        <tr><td><v-icon size="small" color="success">mdi-play</v-icon> {{ t('help.sources.actions.crawl') }}</td><td>{{ t('help.sources.actions.crawlDesc') }}</td></tr>
        <tr><td><v-icon size="small" color="warning">mdi-refresh</v-icon> {{ t('help.sources.actions.reset') }}</td><td>{{ t('help.sources.actions.resetDesc') }}</td></tr>
        <tr><td><v-icon size="small" color="error">mdi-delete</v-icon> {{ t('help.sources.actions.delete') }}</td><td>{{ t('help.sources.actions.deleteDesc') }}</td></tr>
      </tbody>
    </v-table>

    <h3 class="text-h6 mb-3">{{ t('help.sources.formFields.title') }}</h3>
    <v-table density="compact" class="mb-4">
      <thead><tr><th>{{ t('common.field') }}</th><th>{{ t('common.description') }}</th><th>{{ t('common.required') }}</th></tr></thead>
      <tbody>
        <tr><td><strong>{{ t('help.sources.formFields.category') }}</strong></td><td>{{ t('help.sources.formFields.categoryDesc') }}</td><td>{{ t('help.sources.formFields.required') }}</td></tr>
        <tr><td><strong>{{ t('help.sources.formFields.name') }}</strong></td><td>{{ t('help.sources.formFields.nameDesc') }}</td><td>{{ t('help.sources.formFields.required') }}</td></tr>
        <tr><td><strong>{{ t('help.sources.formFields.sourceType') }}</strong></td><td>{{ t('help.sources.formFields.sourceTypeDesc') }}</td><td>{{ t('help.sources.formFields.required') }}</td></tr>
        <tr><td><strong>{{ t('help.sources.formFields.baseUrl') }}</strong></td><td>{{ t('help.sources.formFields.baseUrlDesc') }}</td><td>{{ t('help.sources.formFields.required') }}</td></tr>
        <tr><td><strong>{{ t('help.sources.formFields.apiEndpoint') }}</strong></td><td>{{ t('help.sources.formFields.apiEndpointDesc') }}</td><td>{{ t('help.sources.formFields.optional') }}</td></tr>
        <tr><td><strong>{{ t('help.sources.formFields.country') }}</strong></td><td>{{ t('help.sources.formFields.countryDesc') }}</td><td>{{ t('help.sources.formFields.optional') }}</td></tr>
        <tr><td><strong>{{ t('help.sources.formFields.location') }}</strong></td><td>{{ t('help.sources.formFields.locationDesc') }}</td><td>{{ t('help.sources.formFields.optional') }}</td></tr>
      </tbody>
    </v-table>

    <h3 class="text-h6 mb-3">{{ t('help.sources.bulkImport.title') }}</h3>
    <v-alert type="info" variant="tonal" class="mb-4">
      {{ t('help.sources.bulkImport.info') }}
      <ol class="mt-2 pl-4">
        <li>{{ t('help.sources.bulkImport.step1') }}</li>
        <li>{{ t('help.sources.bulkImport.step2') }}</li>
      </ol>
      <pre class="mt-2 pa-2 d-block text-caption bg-grey-lighten-4 rounded" style="font-family: monospace;">[
  {"name": "Stadt X", "base_url": "https://...", "location_name": "Stadt X"},
  {"name": "Stadt Y", "base_url": "https://...", "location_name": "Stadt Y"}
]</pre>
    </v-alert>

    <h3 class="text-h6 mb-3">{{ t('help.sources.crawlConfig.title') }}</h3>
    <v-table density="compact" class="mb-4">
      <thead><tr><th>{{ t('common.setting') }}</th><th>{{ t('common.description') }}</th><th>{{ t('common.default') }}</th></tr></thead>
      <tbody>
        <tr><td><strong>{{ t('help.sources.crawlConfig.maxDepth') }}</strong></td><td>{{ t('help.sources.crawlConfig.maxDepthDesc') }}</td><td>{{ t('help.sources.crawlConfig.maxDepthDefault') }}</td></tr>
        <tr><td><strong>{{ t('help.sources.crawlConfig.maxPages') }}</strong></td><td>{{ t('help.sources.crawlConfig.maxPagesDesc') }}</td><td>{{ t('help.sources.crawlConfig.maxPagesDefault') }}</td></tr>
        <tr><td><strong>{{ t('help.sources.crawlConfig.externalLinks') }}</strong></td><td>{{ t('help.sources.crawlConfig.externalLinksDesc') }}</td><td>{{ t('help.sources.crawlConfig.externalLinksDefault') }}</td></tr>
        <tr><td><strong>{{ t('help.sources.crawlConfig.renderJs') }}</strong></td><td>{{ t('help.sources.crawlConfig.renderJsDesc') }}</td><td>{{ t('help.sources.crawlConfig.renderJsDefault') }}</td></tr>
        <tr><td><strong>{{ t('help.sources.crawlConfig.htmlCapture') }}</strong></td><td>{{ t('help.sources.crawlConfig.htmlCaptureDesc') }}</td><td>{{ t('help.sources.crawlConfig.htmlCaptureDefault') }}</td></tr>
      </tbody>
    </v-table>

    <h3 class="text-h6 mb-3">{{ t('help.sources.urlFiltersAdvanced.title') }}</h3>
    <v-alert type="info" variant="tonal" class="mb-3">
      {{ t('help.sources.urlFiltersAdvanced.info') }}
    </v-alert>
    <v-row class="mb-4">
      <v-col cols="12" md="6">
        <v-card variant="outlined" class="pa-3" color="error">
          <div class="text-subtitle-2 mb-2"><v-icon color="error">mdi-close</v-icon> {{ t('help.sources.urlFiltersAdvanced.excludeTitle') }}</div>
          <div class="text-body-2">{{ t('help.sources.urlFiltersAdvanced.excludeDesc') }}</div>
          <v-chip-group class="mt-2">
            <v-chip size="small">/impressum</v-chip>
            <v-chip size="small">/datenschutz</v-chip>
            <v-chip size="small">/login</v-chip>
            <v-chip size="small">/archiv</v-chip>
          </v-chip-group>
        </v-card>
      </v-col>
      <v-col cols="12" md="6">
        <v-card variant="outlined" class="pa-3">
          <div class="text-subtitle-2 mb-2"><v-icon>mdi-check</v-icon> {{ t('help.sources.urlFiltersAdvanced.includeTitle') }}</div>
          <div class="text-body-2">{{ t('help.sources.urlFiltersAdvanced.includeDesc') }}</div>
          <v-chip-group class="mt-2">
            <v-chip size="small" variant="outlined">/dokumente/</v-chip>
            <v-chip size="small" variant="outlined">/beschluesse/</v-chip>
          </v-chip-group>
        </v-card>
      </v-col>
    </v-row>

    <h3 class="text-h6 mb-3">{{ t('help.sources.statusMeaning.title') }}</h3>
    <v-table density="compact">
      <thead><tr><th>{{ t('common.status') }}</th><th>{{ t('common.meaning') }}</th></tr></thead>
      <tbody>
        <tr><td><v-chip size="small">{{ t('help.sources.statusMeaning.pending') }}</v-chip></td><td>{{ t('help.sources.statusMeaning.pendingDesc') }}</td></tr>
        <tr><td><v-chip size="small" color="info">{{ t('help.sources.statusMeaning.crawling') }}</v-chip></td><td>{{ t('help.sources.statusMeaning.crawlingDesc') }}</td></tr>
        <tr><td><v-chip size="small" color="success">{{ t('help.sources.statusMeaning.active') }}</v-chip></td><td>{{ t('help.sources.statusMeaning.activeDesc') }}</td></tr>
        <tr><td><v-chip size="small" color="error">{{ t('help.sources.statusMeaning.error') }}</v-chip></td><td>{{ t('help.sources.statusMeaning.errorDesc') }}</td></tr>
      </tbody>
    </v-table>
  </HelpCard>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import HelpCard from './HelpCard.vue'

const { t } = useI18n()
</script>
