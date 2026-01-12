<template>
  <v-row class="mb-4">
    <v-col cols="6" sm="4" md>
      <v-card>
        <v-card-text class="text-center">
          <v-icon size="32" color="primary" class="mb-2">mdi-counter</v-icon>
          <div class="text-h4">{{ totalCount }}</div>
          <div class="text-caption text-medium-emphasis">
            {{ t('admin.modelPricing.stats.totalModels') }}
          </div>
        </v-card-text>
      </v-card>
    </v-col>
    <v-col cols="6" sm="4" md>
      <v-card>
        <v-card-text class="text-center">
          <v-icon size="32" :color="getProviderColor('AZURE_OPENAI')" class="mb-2">
            {{ getProviderIcon('AZURE_OPENAI') }}
          </v-icon>
          <div class="text-h4">{{ azureCount }}</div>
          <div class="text-caption text-medium-emphasis">
            {{ t('admin.modelPricing.stats.azureModels') }}
          </div>
        </v-card-text>
      </v-card>
    </v-col>
    <v-col cols="6" sm="4" md>
      <v-card>
        <v-card-text class="text-center">
          <v-icon size="32" :color="getProviderColor('OPENAI')" class="mb-2">
            {{ getProviderIcon('OPENAI') }}
          </v-icon>
          <div class="text-h4">{{ openaiCount }}</div>
          <div class="text-caption text-medium-emphasis">
            {{ t('admin.modelPricing.stats.openaiModels') }}
          </div>
        </v-card-text>
      </v-card>
    </v-col>
    <v-col cols="6" sm="4" md>
      <v-card>
        <v-card-text class="text-center">
          <v-icon size="32" :color="getProviderColor('ANTHROPIC')" class="mb-2">
            {{ getProviderIcon('ANTHROPIC') }}
          </v-icon>
          <div class="text-h4">{{ anthropicCount }}</div>
          <div class="text-caption text-medium-emphasis">
            {{ t('admin.modelPricing.stats.anthropicModels') }}
          </div>
        </v-card-text>
      </v-card>
    </v-col>
    <v-col cols="6" sm="4" md>
      <v-card>
        <v-card-text class="text-center">
          <v-icon size="32" color="warning" class="mb-2">mdi-clock-alert</v-icon>
          <div class="text-h4">{{ staleCount }}</div>
          <div class="text-caption text-medium-emphasis">
            {{ t('admin.modelPricing.stats.staleCount') }}
          </div>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { getProviderIcon, getProviderColor } from '@/utils/llmProviders'

defineProps<{
  totalCount: number
  azureCount: number
  openaiCount: number
  anthropicCount: number
  staleCount: number
}>()

const { t } = useI18n()
</script>
