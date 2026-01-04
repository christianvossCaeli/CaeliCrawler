<template>
  <div
    class="summary-suggestion-section"
    role="region"
    :aria-label="t('summaries.createDialog.title', 'Als Zusammenfassung speichern')"
  >
    <v-card
      class="summary-suggestion-card"
      color="info"
      variant="tonal"
    >
      <v-card-title class="d-flex align-center">
        <v-icon start aria-hidden="true">mdi-view-dashboard-variant</v-icon>
        {{ t('summaries.dashboard.suggestion', 'Als Zusammenfassung speichern?') }}
      </v-card-title>
      <v-card-text>
        <p class="text-body-2 mb-4">
          {{ t('summaries.dashboard.suggestionHint', 'Diese Abfrage kann als automatisch aktualisierte Zusammenfassung gespeichert werden.') }}
        </p>
        <div class="d-flex ga-2">
          <v-btn
            color="info"
            variant="elevated"
            @click="$emit('save', prompt)"
          >
            <v-icon start>mdi-content-save</v-icon>
            {{ t('summaries.createNew', 'Als Zusammenfassung speichern') }}
          </v-btn>
          <v-btn
            variant="text"
            @click="$emit('dismiss')"
          >
            {{ t('common.dismiss', 'Später') }}
          </v-btn>
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

defineProps<{
  prompt: string
}>()

defineEmits<{
  save: [prompt: string]
  dismiss: []
}>()

const { t } = useI18n()
</script>

<style scoped>
.summary-suggestion-section {
  padding: 0 16px;
  margin-bottom: 16px;
}

.summary-suggestion-card {
  border-radius: 12px !important;
}
</style>
