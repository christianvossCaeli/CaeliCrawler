<template>
  <v-card class="mb-4">
    <v-card-text>
      <v-row align="center">
        <v-col cols="12" sm="6" md="3">
          <v-select
            :model-value="provider"
            :items="providerOptions"
            :label="t('admin.modelPricing.filters.provider')"
            clearable
            density="compact"
            hide-details
            @update:model-value="$emit('update:provider', $event)"
          />
        </v-col>
        <v-col cols="12" sm="6" md="3">
          <v-switch
            :model-value="includeDeprecated"
            :label="t('admin.modelPricing.filters.includeDeprecated')"
            color="primary"
            hide-details
            density="compact"
            @update:model-value="$emit('update:includeDeprecated', $event ?? false)"
          />
        </v-col>
        <v-spacer />
        <v-col cols="auto">
          <v-btn
            v-if="showSeedButton"
            variant="tonal"
            color="primary"
            :loading="seeding"
            @click="$emit('seed')"
          >
            <v-icon start>mdi-database-plus</v-icon>
            {{ t('admin.modelPricing.actions.seedDefaults') }}
          </v-btn>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { getProviderLabel } from '@/utils/llmProviders'

defineProps<{
  provider: string | null
  includeDeprecated: boolean
  showSeedButton: boolean
  seeding: boolean
}>()

defineEmits<{
  'update:provider': [value: string | null]
  'update:includeDeprecated': [value: boolean]
  seed: []
}>()

const { t } = useI18n()

const providerOptions = computed(() => [
  { title: t('admin.modelPricing.filters.allProviders'), value: null },
  { title: getProviderLabel('azure_openai'), value: 'azure_openai' },
  { title: getProviderLabel('openai'), value: 'openai' },
  { title: getProviderLabel('anthropic'), value: 'anthropic' },
])
</script>
