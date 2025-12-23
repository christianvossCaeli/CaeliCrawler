<template>
  <div class="ai-discovery-input">
    <!-- Prompt Input -->
    <v-textarea
      :model-value="prompt"
      @update:model-value="$emit('update:prompt', $event)"
      :label="$t('sources.aiDiscovery.prompt')"
      :placeholder="$t('sources.aiDiscovery.promptPlaceholder')"
      variant="outlined"
      rows="3"
      prepend-inner-icon="mdi-magnify"
      class="mb-4"
      auto-grow
    ></v-textarea>

    <!-- Examples -->
    <v-card v-if="examples.length > 0" variant="tonal" class="mb-4" color="info">
      <v-card-title class="text-subtitle-2 pb-2">
        <v-icon start size="small">mdi-lightbulb-outline</v-icon>
        {{ $t('sources.aiDiscovery.examples') }}
      </v-card-title>
      <v-card-text class="pt-0">
        <v-chip-group>
          <v-chip
            v-for="example in examples"
            :key="example.prompt"
            size="small"
            variant="outlined"
            @click="$emit('update:prompt', example.prompt)"
          >
            {{ example.prompt }}
          </v-chip>
        </v-chip-group>
      </v-card-text>
    </v-card>

    <!-- Search Options -->
    <v-row>
      <v-col cols="12" md="4">
        <v-select
          :model-value="searchDepth"
          @update:model-value="$emit('update:searchDepth', $event)"
          :items="searchDepthOptions"
          :label="$t('sources.aiDiscovery.searchDepth')"
          variant="outlined"
          density="comfortable"
        >
          <template v-slot:item="{ item, props }">
            <v-list-item v-bind="props">
              <template v-slot:prepend>
                <v-icon :color="item.raw.color">{{ item.raw.icon }}</v-icon>
              </template>
            </v-list-item>
          </template>
        </v-select>
      </v-col>
      <v-col cols="12" md="4">
        <v-text-field
          :model-value="maxResults"
          @update:model-value="$emit('update:maxResults', Number($event))"
          :label="$t('sources.aiDiscovery.maxResults')"
          type="number"
          variant="outlined"
          density="comfortable"
          :min="minResults"
          :max="maxResultsLimit"
        ></v-text-field>
      </v-col>
      <v-col cols="12" md="4">
        <v-switch
          :model-value="skipApiDiscovery"
          @update:model-value="$emit('update:skipApiDiscovery', $event ?? false)"
          :label="$t('sources.aiDiscovery.skipApiDiscovery')"
          color="warning"
          density="comfortable"
          hide-details
          class="mt-2"
        ></v-switch>
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
/**
 * AiDiscoveryInputPhase - Input form for AI source discovery
 *
 * Provides prompt input, example suggestions, and search configuration options.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { DiscoveryExample } from './types'

interface Props {
  prompt: string
  searchDepth: string
  maxResults: number
  skipApiDiscovery: boolean
  examples?: DiscoveryExample[]
  minResults?: number
  maxResultsLimit?: number
}

const props = withDefaults(defineProps<Props>(), {
  examples: () => [],
  minResults: 10,
  maxResultsLimit: 200,
})

defineEmits<{
  (e: 'update:prompt', value: string): void
  (e: 'update:searchDepth', value: string): void
  (e: 'update:maxResults', value: number): void
  (e: 'update:skipApiDiscovery', value: boolean): void
}>()

const { t } = useI18n()

/** Search depth options - reactive to language changes */
const searchDepthOptions = computed(() => [
  { value: 'quick', title: t('sources.aiDiscovery.quick'), icon: 'mdi-speedometer', color: 'success' },
  { value: 'standard', title: t('sources.aiDiscovery.standard'), icon: 'mdi-speedometer-medium', color: 'primary' },
  { value: 'deep', title: t('sources.aiDiscovery.deep'), icon: 'mdi-speedometer-slow', color: 'warning' },
])
</script>
