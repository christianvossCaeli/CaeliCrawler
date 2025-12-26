<template>
  <div class="source-form-crawl-settings">
    <!-- Advanced Settings -->
    <v-card variant="outlined" class="mb-4">
      <v-card-title class="text-subtitle-2 pb-2">
        <v-icon start size="small">mdi-cog</v-icon>
        {{ $t('sources.form.advancedSettings') }}
      </v-card-title>
      <v-card-text>
        <v-row>
          <v-col cols="12" md="6">
            <v-number-input
              :model-value="config.max_depth"
              :label="$t('sources.form.maxDepth')"
              :hint="$t('sources.form.maxDepthHint')"
              :min="1"
              :max="10"
              variant="outlined"
              control-variant="stacked"
              persistent-hint
              @update:model-value="updateConfig('max_depth', $event)"
            />
          </v-col>
          <v-col cols="12" md="6">
            <v-number-input
              :model-value="config.max_pages"
              :label="$t('sources.form.maxPages')"
              :hint="$t('sources.form.maxPagesHint')"
              :min="1"
              :max="10000"
              variant="outlined"
              control-variant="stacked"
              persistent-hint
              @update:model-value="updateConfig('max_pages', $event)"
            />
          </v-col>
        </v-row>

        <v-switch
          :model-value="config.render_javascript"
          :label="$t('sources.form.renderJs')"
          :hint="$t('sources.form.renderJsHint')"
          persistent-hint
          color="primary"
          class="mt-4"
          @update:model-value="updateConfig('render_javascript', $event ?? false)"
        />
      </v-card-text>
    </v-card>

    <!-- URL Include Patterns -->
    <v-card variant="outlined" class="mb-4" color="success">
      <v-card-title class="text-subtitle-2 pb-2">
        <v-icon start size="small" color="success">mdi-check-circle</v-icon>
        {{ $t('sources.form.includePatterns') }}
      </v-card-title>
      <v-card-text class="pt-4">
        <v-combobox
          :model-value="config.url_include_patterns"
          :hint="$t('sources.form.includeHint')"
          persistent-hint
          multiple
          chips
          closable-chips
          clearable
          variant="outlined"
          density="comfortable"
          :error="hasInvalidIncludePatterns"
          :error-messages="invalidIncludePatternsMessage"
          @update:model-value="updateConfig('url_include_patterns', $event)"
        >
          <template #chip="{ item, props: chipProps }">
            <v-chip
              v-bind="chipProps"
              :color="isValidRegexPattern(item.raw) ? 'success' : 'error'"
              variant="tonal"
            >
              <v-icon start size="small">{{ isValidRegexPattern(item.raw) ? 'mdi-check' : 'mdi-alert' }}</v-icon>
              {{ item.raw }}
            </v-chip>
          </template>
        </v-combobox>
      </v-card-text>
    </v-card>

    <!-- URL Exclude Patterns -->
    <v-card variant="outlined" color="error">
      <v-card-title class="text-subtitle-2 pb-2">
        <v-icon start size="small" color="error">mdi-close-circle</v-icon>
        {{ $t('sources.form.excludePatterns') }}
      </v-card-title>
      <v-card-text class="pt-4">
        <v-combobox
          :model-value="config.url_exclude_patterns"
          :hint="$t('sources.form.excludeHint')"
          persistent-hint
          multiple
          chips
          closable-chips
          clearable
          variant="outlined"
          density="comfortable"
          :error="hasInvalidExcludePatterns"
          :error-messages="invalidExcludePatternsMessage"
          @update:model-value="updateConfig('url_exclude_patterns', $event)"
        >
          <template #chip="{ item, props: chipProps }">
            <v-chip
              v-bind="chipProps"
              :color="isValidRegexPattern(item.raw) ? 'error' : 'warning'"
              variant="tonal"
            >
              <v-icon start size="small">{{ isValidRegexPattern(item.raw) ? 'mdi-close' : 'mdi-alert' }}</v-icon>
              {{ item.raw }}
            </v-chip>
          </template>
        </v-combobox>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
/**
 * SourceFormCrawlSettings - Crawl configuration settings
 *
 * Handles max depth, max pages, JavaScript rendering, and URL patterns.
 */
import { computed } from 'vue'
import type { CrawlConfig } from '@/types/sources'
import { isValidRegexPattern } from '@/utils/csvParser'

interface Props {
  config: CrawlConfig
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'update:config', value: CrawlConfig): void
}>()

/** Update a single config property */
const updateConfig = <K extends keyof CrawlConfig>(key: K, value: CrawlConfig[K]) => {
  emit('update:config', { ...props.config, [key]: value })
}

/** Check for invalid include patterns (using centralized regex validator) */
const hasInvalidIncludePatterns = computed(() => {
  const patterns = props.config?.url_include_patterns || []
  return patterns.some(p => !isValidRegexPattern(p))
})

const invalidIncludePatternsMessage = computed(() => {
  if (!hasInvalidIncludePatterns.value) return []
  const patterns = props.config?.url_include_patterns || []
  const invalid = patterns.filter(p => !isValidRegexPattern(p))
  return [`Invalid regex pattern(s): ${invalid.join(', ')}`]
})

/** Check for invalid exclude patterns */
const hasInvalidExcludePatterns = computed(() => {
  const patterns = props.config?.url_exclude_patterns || []
  return patterns.some(p => !isValidRegexPattern(p))
})

const invalidExcludePatternsMessage = computed(() => {
  if (!hasInvalidExcludePatterns.value) return []
  const patterns = props.config?.url_exclude_patterns || []
  const invalid = patterns.filter(p => !isValidRegexPattern(p))
  return [`Invalid regex pattern(s): ${invalid.join(', ')}`]
})
</script>
