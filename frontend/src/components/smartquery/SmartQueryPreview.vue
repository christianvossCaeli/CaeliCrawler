<template>
  <v-card class="mb-4" color="warning" variant="tonal">
    <v-card-title>
      <v-icon left>mdi-eye-check</v-icon>
      {{ t('smartQueryView.preview.title') }}
    </v-card-title>
    <v-card-text>
      <v-alert type="info" variant="tonal" class="mb-4">
        <strong>{{ preview.operation_de }}</strong>
        <div class="mt-1">{{ preview.description }}</div>
      </v-alert>

      <v-card variant="outlined" class="mb-4">
        <v-card-title class="text-subtitle-1">
          <v-icon left size="small">mdi-format-list-bulleted</v-icon>
          {{ t('common.details') }}
        </v-card-title>
        <v-card-text>
          <v-list density="compact" class="bg-transparent">
            <v-list-item
              v-for="(detail, idx) in preview.details || []"
              :key="idx"
              :title="detail"
            >
              <template #prepend>
                <v-icon size="small" color="primary">mdi-check</v-icon>
              </template>
            </v-list-item>
          </v-list>
        </v-card-text>
      </v-card>

      <!-- Technical Details -->
      <v-expansion-panels variant="accordion">
        <v-expansion-panel :title="t('smartQueryView.preview.technicalDetails')">
          <v-expansion-panel-text>
            <pre class="text-caption">{{ JSON.stringify(interpretation, null, 2) }}</pre>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-card-text>
    <v-card-actions>
      <v-spacer />
      <v-btn variant="tonal" @click="$emit('cancel')">
        <v-icon start>mdi-close</v-icon>
        {{ t('common.cancel') }}
      </v-btn>
      <v-btn color="success" variant="elevated" :loading="loading" @click="$emit('confirm')">
        <v-icon start>mdi-check</v-icon>
        {{ t('smartQueryView.preview.confirmAndCreate') }}
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

interface Preview {
  operation_de?: string
  description?: string
  details?: string[]
}

defineProps<{
  preview: Preview
  interpretation: Record<string, unknown>
  loading: boolean
}>()

defineEmits<{
  cancel: []
  confirm: []
}>()

const { t } = useI18n()
</script>
