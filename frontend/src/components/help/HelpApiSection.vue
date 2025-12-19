<template>
  <HelpCard section-id="api" :title="t('help.api.title')" icon="mdi-api" color="grey-darken-3">
    <p class="mb-4">
      {{ t('help.api.description') }}
    </p>

    <HelpApiTable />

    <v-alert type="info" variant="tonal" class="mt-4">
      <v-icon>mdi-information</v-icon>
      {{ t('help.api.fullDocumentation') }}
      <a href="/docs" target="_blank" class="text-primary">/docs</a> (Swagger UI) {{ t('help.api.or') }}
      <a href="/redoc" target="_blank" class="text-primary">/redoc</a> (ReDoc).
    </v-alert>
  </HelpCard>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import HelpCard from './HelpCard.vue'
import HelpApiTable from './HelpApiTable.vue'

const { t } = useI18n()
</script>
