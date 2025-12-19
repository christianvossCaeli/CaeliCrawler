<template>
  <HelpCard section-id="tips" :title="t('help.tips.title')" icon="mdi-lightbulb" color="amber">
    <v-expansion-panels variant="accordion">
      <v-expansion-panel :title="t('help.tips.efficientCrawling.title')">
        <v-expansion-panel-text>
          <v-list density="compact">
            <v-list-item prepend-icon="mdi-filter">
              <v-list-item-title>{{ t('help.tips.efficientCrawling.useBlacklist') }}</v-list-item-title>
              <v-list-item-subtitle>{{ t('help.tips.efficientCrawling.useBlacklistDesc') }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item prepend-icon="mdi-stairs">
              <v-list-item-title>{{ t('help.tips.efficientCrawling.limitDepth') }}</v-list-item-title>
              <v-list-item-subtitle>{{ t('help.tips.efficientCrawling.limitDepthDesc') }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item prepend-icon="mdi-file-document">
              <v-list-item-title>{{ t('help.tips.efficientCrawling.restrictDocTypes') }}</v-list-item-title>
              <v-list-item-subtitle>{{ t('help.tips.efficientCrawling.restrictDocTypesDesc') }}</v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-expansion-panel-text>
      </v-expansion-panel>

      <v-expansion-panel :title="t('help.tips.betterAiResults.title')">
        <v-expansion-panel-text>
          <v-list density="compact">
            <v-list-item prepend-icon="mdi-text-box">
              <v-list-item-title>{{ t('help.tips.betterAiResults.precisePrompts') }}</v-list-item-title>
              <v-list-item-subtitle>{{ t('help.tips.betterAiResults.precisePromptsDesc') }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item prepend-icon="mdi-tag-multiple">
              <v-list-item-title>{{ t('help.tips.betterAiResults.optimizeKeywords') }}</v-list-item-title>
              <v-list-item-subtitle>{{ t('help.tips.betterAiResults.optimizeKeywordsDesc') }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item prepend-icon="mdi-test-tube">
              <v-list-item-title>{{ t('help.tips.betterAiResults.testFirst') }}</v-list-item-title>
              <v-list-item-subtitle>{{ t('help.tips.betterAiResults.testFirstDesc') }}</v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-expansion-panel-text>
      </v-expansion-panel>

      <v-expansion-panel :title="t('help.tips.organization.title')">
        <v-expansion-panel-text>
          <v-list density="compact">
            <v-list-item prepend-icon="mdi-folder-multiple">
              <v-list-item-title>{{ t('help.tips.organization.separateCategories') }}</v-list-item-title>
              <v-list-item-subtitle>{{ t('help.tips.organization.separateCategoriesDesc') }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item prepend-icon="mdi-map-marker">
              <v-list-item-title>{{ t('help.tips.organization.maintainLocations') }}</v-list-item-title>
              <v-list-item-subtitle>{{ t('help.tips.organization.maintainLocationsDesc') }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item prepend-icon="mdi-update">
              <v-list-item-title>{{ t('help.tips.organization.regularMaintenance') }}</v-list-item-title>
              <v-list-item-subtitle>{{ t('help.tips.organization.regularMaintenanceDesc') }}</v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </HelpCard>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import HelpCard from './HelpCard.vue'

const { t } = useI18n()
</script>
