<template>
  <HelpCard section-id="ai-source-discovery" :title="t('help.aiSourceDiscovery.title')" icon="mdi-robot-outline" color="deep-purple">
    <p class="mb-4">{{ t('help.aiSourceDiscovery.description') }}</p>

    <h3 class="text-h6 mb-3">{{ t('help.aiSourceDiscovery.overview.title') }}</h3>
    <v-list density="compact" class="mb-4">
      <v-list-item prepend-icon="mdi-magnify">
        <v-list-item-title>{{ t('help.aiSourceDiscovery.overview.howItWorks') }}</v-list-item-title>
        <v-list-item-subtitle>{{ t('help.aiSourceDiscovery.overview.howItWorksDesc') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-tag-multiple">
        <v-list-item-title>{{ t('help.aiSourceDiscovery.overview.autoTags') }}</v-list-item-title>
        <v-list-item-subtitle>{{ t('help.aiSourceDiscovery.overview.autoTagsDesc') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-eye">
        <v-list-item-title>{{ t('help.aiSourceDiscovery.overview.preview') }}</v-list-item-title>
        <v-list-item-subtitle>{{ t('help.aiSourceDiscovery.overview.previewDesc') }}</v-list-item-subtitle>
      </v-list-item>
    </v-list>

    <h3 class="text-h6 mb-3">{{ t('help.aiSourceDiscovery.access.title') }}</h3>
    <v-alert type="info" variant="tonal" class="mb-4">
      {{ t('help.aiSourceDiscovery.access.description') }}
      <ul class="mt-2 pl-4">
        <li>{{ t('help.aiSourceDiscovery.access.sourcesView') }}</li>
        <li>{{ t('help.aiSourceDiscovery.access.smartQuery') }}</li>
        <li>{{ t('help.aiSourceDiscovery.access.assistant') }}</li>
      </ul>
    </v-alert>

    <h3 class="text-h6 mb-3">{{ t('help.aiSourceDiscovery.workflow.title') }}</h3>
    <v-stepper :items="workflowSteps" alt-labels class="mb-4">
      <template v-slot:item.1>
        <v-card flat>
          <v-card-text>{{ t('help.aiSourceDiscovery.workflow.step1Desc') }}</v-card-text>
        </v-card>
      </template>
      <template v-slot:item.2>
        <v-card flat>
          <v-card-text>{{ t('help.aiSourceDiscovery.workflow.step2Desc') }}</v-card-text>
        </v-card>
      </template>
      <template v-slot:item.3>
        <v-card flat>
          <v-card-text>{{ t('help.aiSourceDiscovery.workflow.step3Desc') }}</v-card-text>
        </v-card>
      </template>
      <template v-slot:item.4>
        <v-card flat>
          <v-card-text>{{ t('help.aiSourceDiscovery.workflow.step4Desc') }}</v-card-text>
        </v-card>
      </template>
      <template v-slot:item.5>
        <v-card flat>
          <v-card-text>{{ t('help.aiSourceDiscovery.workflow.step5Desc') }}</v-card-text>
        </v-card>
      </template>
    </v-stepper>

    <h3 class="text-h6 mb-3">{{ t('help.aiSourceDiscovery.searchDepth.title') }}</h3>
    <v-row class="mb-4">
      <v-col cols="12" md="4">
        <v-card variant="outlined" class="pa-3">
          <v-chip color="success" class="mb-2">{{ t('help.aiSourceDiscovery.searchDepth.quick') }}</v-chip>
          <div class="text-body-2">{{ t('help.aiSourceDiscovery.searchDepth.quickDesc') }}</div>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card variant="outlined" class="pa-3">
          <v-chip color="primary" class="mb-2">{{ t('help.aiSourceDiscovery.searchDepth.standard') }}</v-chip>
          <div class="text-body-2">{{ t('help.aiSourceDiscovery.searchDepth.standardDesc') }}</div>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card variant="outlined" class="pa-3">
          <v-chip color="warning" class="mb-2">{{ t('help.aiSourceDiscovery.searchDepth.deep') }}</v-chip>
          <div class="text-body-2">{{ t('help.aiSourceDiscovery.searchDepth.deepDesc') }}</div>
        </v-card>
      </v-col>
    </v-row>

    <h3 class="text-h6 mb-3">{{ t('help.aiSourceDiscovery.examples.title') }}</h3>
    <v-chip-group class="mb-4">
      <v-chip variant="outlined">{{ t('help.aiSourceDiscovery.examples.example1') }}</v-chip>
      <v-chip variant="outlined">{{ t('help.aiSourceDiscovery.examples.example2') }}</v-chip>
      <v-chip variant="outlined">{{ t('help.aiSourceDiscovery.examples.example3') }}</v-chip>
      <v-chip variant="outlined">{{ t('help.aiSourceDiscovery.examples.example4') }}</v-chip>
      <v-chip variant="outlined">{{ t('help.aiSourceDiscovery.examples.example5') }}</v-chip>
    </v-chip-group>
  </HelpCard>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import HelpCard from './HelpCard.vue'

const { t } = useI18n()

const workflowSteps = computed(() => [
  t('help.aiSourceDiscovery.workflow.step1'),
  t('help.aiSourceDiscovery.workflow.step2'),
  t('help.aiSourceDiscovery.workflow.step3'),
  t('help.aiSourceDiscovery.workflow.step4'),
  t('help.aiSourceDiscovery.workflow.step5'),
])
</script>
