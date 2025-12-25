<template>
  <v-overlay :model-value="loading" class="align-center justify-center" persistent>
    <v-card class="pa-8 text-center" min-width="320" elevation="24">
      <v-progress-circular indeterminate size="80" width="6" color="primary" class="mb-4"></v-progress-circular>
      <div class="text-h6 mb-2">{{ t('entityDetail.loading') }}</div>
    </v-card>
  </v-overlay>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

defineProps<{
  loading: boolean
}>()

const { t } = useI18n()
</script>
