<template>
  <v-card class="crawl-preset-quick-actions">
    <v-card-title class="d-flex align-center">
      <v-icon class="mr-2" size="small">mdi-lightning-bolt</v-icon>
      {{ t('crawlPresets.quickStart') }}
      <v-spacer />
      <v-btn
        variant="text"
        size="small"
        :to="{ name: 'crawler' }"
      >
        {{ t('common.viewAll') }}
      </v-btn>
    </v-card-title>

    <v-card-text>
      <!-- Loading State -->
      <div v-if="presetsStore.isLoading" class="text-center pa-4">
        <v-progress-circular indeterminate size="24" />
      </div>

      <!-- Empty State -->
      <div v-else-if="favoritePresets.length === 0" class="text-center pa-4 text-medium-emphasis">
        <v-icon size="32" class="mb-2">mdi-star-outline</v-icon>
        <div class="text-body-2">{{ t('crawlPresets.noFavoritesYet') }}</div>
        <div class="text-caption">{{ t('crawlPresets.noFavoritesHint') }}</div>
      </div>

      <!-- Favorite Presets as Chips -->
      <div v-else class="d-flex flex-wrap gap-2">
        <v-chip
          v-for="preset in favoritePresets"
          :key="preset.id"
          color="primary"
          variant="tonal"
          :loading="executingId === preset.id"
          @click="executePreset(preset)"
        >
          <v-icon start size="small">mdi-play</v-icon>
          {{ preset.name }}
          <v-tooltip activator="parent" location="top">
            <div>{{ preset.filter_summary }}</div>
            <div v-if="preset.usage_count > 0" class="text-caption">
              {{ t('crawlPresets.usedTimes', { count: preset.usage_count }) }}
            </div>
          </v-tooltip>
        </v-chip>
      </div>

      <!-- Scheduled Presets Info -->
      <div v-if="scheduledCount > 0" class="mt-3 text-caption text-medium-emphasis d-flex align-center">
        <v-icon size="small" class="mr-1">mdi-clock-outline</v-icon>
        {{ t('crawlPresets.scheduledCount', { count: scheduledCount }) }}
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCrawlPresetsStore, type CrawlPreset, MAX_QUICK_ACTION_PRESETS } from '@/stores/crawlPresets'
import { useSnackbar } from '@/composables/useSnackbar'

const { t } = useI18n()
const presetsStore = useCrawlPresetsStore()
const { showSuccess, showError } = useSnackbar()

const executingId = ref<string | null>(null)

const favoritePresets = computed(() => presetsStore.favorites.slice(0, MAX_QUICK_ACTION_PRESETS))
const scheduledCount = computed(() => presetsStore.scheduledPresets.length)

async function executePreset(preset: CrawlPreset) {
  executingId.value = preset.id
  try {
    const result = await presetsStore.executePreset(preset.id)
    if (result) {
      showSuccess(t('crawlPresets.messages.executed', { count: result.jobs_created }))
    }
  } catch {
    showError(t('crawlPresets.messages.executeFailed'))
  } finally {
    executingId.value = null
  }
}

onMounted(() => {
  if (presetsStore.presets.length === 0) {
    presetsStore.loadPresets({ favorites_only: true })
  }
})
</script>

<style scoped lang="scss">
.crawl-preset-quick-actions {
  .v-chip {
    cursor: pointer;
    transition: all 0.2s ease;

    &:hover {
      transform: scale(1.05);
    }
  }
}
</style>
