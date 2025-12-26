<template>
  <HelpCard section-id="quickstart" :title="t('help.quickstart.title')" icon="mdi-rocket-launch" color="success">
    <h3 class="text-h6 mb-3">{{ t('help.quickstart.subtitle') }}</h3>

    <v-timeline density="compact" side="end">
      <v-timeline-item dot-color="primary" size="small">
        <template #opposite><strong>{{ t('help.quickstart.step1.label') }}</strong></template>
        <v-card variant="outlined">
          <v-card-title class="text-subtitle-1">{{ t('help.quickstart.step1.title') }}</v-card-title>
          <v-card-text>
            <ol class="pl-4">
              <li>{{ t('help.quickstart.step1.instructions.1') }}</li>
              <li>{{ t('help.quickstart.step1.instructions.2') }}</li>
              <li>{{ t('help.quickstart.step1.instructions.3') }}</li>
              <li>{{ t('help.quickstart.step1.instructions.4') }}</li>
              <li>{{ t('help.quickstart.step1.instructions.5') }}</li>
            </ol>
          </v-card-text>
        </v-card>
      </v-timeline-item>

      <v-timeline-item dot-color="success" size="small">
        <template #opposite><strong>{{ t('help.quickstart.step2.label') }}</strong></template>
        <v-card variant="outlined">
          <v-card-title class="text-subtitle-1">{{ t('help.quickstart.step2.title') }}</v-card-title>
          <v-card-text>
            <ol class="pl-4">
              <li>{{ t('help.quickstart.step2.instructions.1') }}</li>
              <li>{{ t('help.quickstart.step2.instructions.2') }}</li>
              <li>{{ t('help.quickstart.step2.instructions.3') }}</li>
              <li>{{ t('help.quickstart.step2.instructions.4') }}</li>
              <li>{{ t('help.quickstart.step2.instructions.5') }}</li>
            </ol>
          </v-card-text>
        </v-card>
      </v-timeline-item>

      <v-timeline-item dot-color="warning" size="small">
        <template #opposite><strong>{{ t('help.quickstart.step3.label') }}</strong></template>
        <v-card variant="outlined">
          <v-card-title class="text-subtitle-1">{{ t('help.quickstart.step3.title') }}</v-card-title>
          <v-card-text>
            <ol class="pl-4">
              <li>{{ t('help.quickstart.step3.instructions.1') }}</li>
              <li>{{ t('help.quickstart.step3.instructions.2') }}</li>
              <li>{{ t('help.quickstart.step3.instructions.3') }}</li>
            </ol>
          </v-card-text>
        </v-card>
      </v-timeline-item>

      <v-timeline-item dot-color="info" size="small">
        <template #opposite><strong>{{ t('help.quickstart.step4.label') }}</strong></template>
        <v-card variant="outlined">
          <v-card-title class="text-subtitle-1">{{ t('help.quickstart.step4.title') }}</v-card-title>
          <v-card-text>
            <ol class="pl-4">
              <li>{{ t('help.quickstart.step4.instructions.1') }}</li>
              <li>{{ t('help.quickstart.step4.instructions.2') }}</li>
              <li>{{ t('help.quickstart.step4.instructions.3') }}</li>
            </ol>
          </v-card-text>
        </v-card>
      </v-timeline-item>
    </v-timeline>
  </HelpCard>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import HelpCard from './HelpCard.vue'

const { t } = useI18n()
</script>
