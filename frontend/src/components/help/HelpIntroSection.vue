<template>
  <HelpCard section-id="intro" :title="t('help.intro.title')" icon="mdi-information" color="primary">
    <h3 class="text-h6 mb-3">{{ t('help.intro.what_is_title') }}</h3>
    <p class="mb-4">
      {{ t('help.intro.what_is_description') }}
    </p>

    <h3 class="text-h6 mb-3">{{ t('help.intro.main_functions_title') }}</h3>
    <v-table density="compact" class="mb-4">
      <thead>
        <tr><th>{{ t('help.intro.table.function') }}</th><th>{{ t('help.intro.table.description') }}</th></tr>
      </thead>
      <tbody>
        <tr><td><strong>{{ t('help.intro.functions.web_crawling.title') }}</strong></td><td>{{ t('help.intro.functions.web_crawling.description') }}</td></tr>
        <tr><td><strong>{{ t('help.intro.functions.document_processing.title') }}</strong></td><td>{{ t('help.intro.functions.document_processing.description') }}</td></tr>
        <tr><td><strong>{{ t('help.intro.functions.ai_analysis.title') }}</strong></td><td>{{ t('help.intro.functions.ai_analysis.description') }}</td></tr>
        <tr><td><strong>{{ t('help.intro.functions.relevance_filtering.title') }}</strong></td><td>{{ t('help.intro.functions.relevance_filtering.description') }}</td></tr>
        <tr><td><strong>{{ t('help.intro.functions.structured_results.title') }}</strong></td><td>{{ t('help.intro.functions.structured_results.description') }}</td></tr>
      </tbody>
    </v-table>

    <h3 class="text-h6 mb-3">{{ t('help.intro.workflow_title') }}</h3>
    <v-stepper :model-value="1" alt-labels class="elevation-0 bg-transparent">
      <v-stepper-header>
        <v-stepper-item :title="t('help.intro.workflow.step1.title')" :subtitle="t('help.intro.workflow.step1.subtitle')" value="1" complete></v-stepper-item>
        <v-divider></v-divider>
        <v-stepper-item :title="t('help.intro.workflow.step2.title')" :subtitle="t('help.intro.workflow.step2.subtitle')" value="2" complete></v-stepper-item>
        <v-divider></v-divider>
        <v-stepper-item :title="t('help.intro.workflow.step3.title')" :subtitle="t('help.intro.workflow.step3.subtitle')" value="3" complete></v-stepper-item>
        <v-divider></v-divider>
        <v-stepper-item :title="t('help.intro.workflow.step4.title')" :subtitle="t('help.intro.workflow.step4.subtitle')" value="4" complete></v-stepper-item>
        <v-divider></v-divider>
        <v-stepper-item :title="t('help.intro.workflow.step5.title')" :subtitle="t('help.intro.workflow.step5.subtitle')" value="5" complete></v-stepper-item>
        <v-divider></v-divider>
        <v-stepper-item :title="t('help.intro.workflow.step6.title')" :subtitle="t('help.intro.workflow.step6.subtitle')" value="6" complete></v-stepper-item>
      </v-stepper-header>
    </v-stepper>
  </HelpCard>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import HelpCard from './HelpCard.vue'

const { t } = useI18n()
</script>
