<template>
  <v-dialog
    v-model="dialogOpen"
    :max-width="DIALOG_SIZES.MD"
    role="dialog"
    aria-modal="true"
    aria-labelledby="category-info-dialog-title"
  >
    <v-card v-if="category">
      <v-card-title id="category-info-dialog-title" class="d-flex align-center">
        <v-icon class="mr-2" aria-hidden="true">mdi-folder-outline</v-icon>
        {{ category.name }}
        <v-chip :color="category.is_active ? 'success' : 'grey'" size="small" class="ml-2">
          {{ category.is_active ? t('sources.dialog.active') : t('sources.dialog.inactive') }}
        </v-chip>
      </v-card-title>

      <v-card-text>
        <!-- Purpose -->
        <div class="mb-4">
          <div class="text-overline text-medium-emphasis">{{ t('sources.dialog.purpose') }}</div>
          <div class="text-body-1">{{ category.purpose || t('sources.dialog.noPurpose') }}</div>
        </div>

        <!-- Description -->
        <div class="mb-4" v-if="category.description">
          <div class="text-overline text-medium-emphasis">{{ t('common.description') }}</div>
          <div class="text-body-2">{{ category.description }}</div>
        </div>

        <!-- Statistics -->
        <v-row class="mb-4">
          <v-col cols="4">
            <v-card variant="tonal" color="primary" class="pa-3 text-center">
              <div class="text-h5">{{ category.source_count || 0 }}</div>
              <div class="text-caption">{{ t('sources.dialog.dataSources') }}</div>
            </v-card>
          </v-col>
          <v-col cols="4">
            <v-card variant="tonal" color="info" class="pa-3 text-center">
              <div class="text-h5">{{ category.document_count || 0 }}</div>
              <div class="text-caption">{{ t('sources.columns.documents') }}</div>
            </v-card>
          </v-col>
          <v-col cols="4">
            <v-card variant="tonal" color="secondary" class="pa-3 text-center">
              <div class="text-h5">
                <span v-for="lang in (category.languages || ['de'])" :key="lang" class="mr-1">
                  {{ getLanguageFlag(lang) }}
                </span>
              </div>
              <div class="text-caption">{{ t('sources.dialog.languages') }}</div>
            </v-card>
          </v-col>
        </v-row>

        <!-- Search Terms -->
        <div class="mb-4" v-if="category.search_terms?.length">
          <div class="text-overline text-medium-emphasis">{{ t('sources.dialog.searchTerms') }}</div>
          <div>
            <v-chip
              v-for="term in category.search_terms"
              :key="term"
              size="small"
              class="mr-1 mb-1"
              color="primary"
              variant="outlined"
            >
              {{ term }}
            </v-chip>
          </div>
        </div>

        <!-- Document Types -->
        <div class="mb-4" v-if="category.document_types?.length">
          <div class="text-overline text-medium-emphasis">{{ t('sources.dialog.documentTypes') }}</div>
          <div>
            <v-chip
              v-for="type in category.document_types"
              :key="type"
              size="small"
              class="mr-1 mb-1"
              color="secondary"
              variant="outlined"
            >
              {{ type }}
            </v-chip>
          </div>
        </div>

        <!-- URL Patterns -->
        <v-expansion-panels
          variant="accordion"
          class="mb-4"
          v-if="category.url_include_patterns?.length || category.url_exclude_patterns?.length"
        >
          <v-expansion-panel>
            <v-expansion-panel-title>
              <v-icon size="small" class="mr-2">mdi-filter</v-icon>
              {{ t('sources.dialog.urlPatterns') }}
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <div v-if="category.url_include_patterns?.length" class="mb-3">
                <div class="text-caption text-medium-emphasis mb-1">
                  {{ t('sources.dialog.includePatterns') }}
                </div>
                <v-chip
                  v-for="p in category.url_include_patterns"
                  :key="p"
                  size="small"
                  class="mr-1 mb-1"
                  color="success"
                  variant="outlined"
                >
                  <v-icon start size="x-small">mdi-check</v-icon>{{ p }}
                </v-chip>
              </div>
              <div v-if="category.url_exclude_patterns?.length">
                <div class="text-caption text-medium-emphasis mb-1">
                  {{ t('sources.dialog.excludePatterns') }}
                </div>
                <v-chip
                  v-for="p in category.url_exclude_patterns"
                  :key="p"
                  size="small"
                  class="mr-1 mb-1"
                  color="error"
                  variant="outlined"
                >
                  <v-icon start size="x-small">mdi-close</v-icon>{{ p }}
                </v-chip>
              </div>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>

        <!-- AI Extraction Prompt Preview -->
        <v-expansion-panels variant="accordion" v-if="category.ai_extraction_prompt">
          <v-expansion-panel>
            <v-expansion-panel-title>
              <v-icon size="small" class="mr-2">mdi-robot</v-icon>
              {{ t('sources.dialog.aiPrompt') }}
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <pre class="text-caption scrollable-code">{{ category.ai_extraction_prompt }}</pre>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-card-text>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="tonal" @click="dialogOpen = false">
          {{ t('common.close') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
/**
 * CategoryInfoDialog - Dialog to display detailed category information
 *
 * Shows category metadata, statistics, search terms, document types,
 * URL patterns, and AI extraction prompts.
 */
import { useI18n } from 'vue-i18n'
import { useSourceHelpers } from '@/composables/useSourceHelpers'
import { DIALOG_SIZES } from '@/config/sources'
import type { CategoryResponse } from '@/types/category'

// =============================================================================
// Props & defineModel
// =============================================================================

interface Props {
  category: CategoryResponse | null
}

defineProps<Props>()

// defineModel() for two-way binding (Vue 3.4+)
const dialogOpen = defineModel<boolean>({ default: false })

// =============================================================================
// Composables
// =============================================================================

const { t } = useI18n()
const { getLanguageFlag } = useSourceHelpers()
</script>

<style scoped>
.scrollable-code {
  max-height: 300px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
  background: rgba(0, 0, 0, 0.05);
  padding: 12px;
  border-radius: 4px;
}
</style>
