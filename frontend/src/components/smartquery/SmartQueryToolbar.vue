<template>
  <PageHeader
    :title="t('smartQueryView.title')"
    :subtitle="t('smartQueryView.subtitle')"
    icon="mdi-brain"
  >
    <template #actions>
      <div class="mode-toggle-block">
        <v-btn-toggle
          :model-value="mode"
          mandatory
          divided
          density="comfortable"
          class="mode-toggle"
          :disabled="disabled"
          @update:model-value="$emit('update:mode', $event)"
        >
          <v-btn value="read" min-width="110">
            <v-icon start :color="mode === 'read' ? 'primary' : undefined">mdi-magnify</v-icon>
            {{ t('smartQueryView.mode.read') }}
          </v-btn>
          <v-btn value="write" min-width="110">
            <v-icon start :color="mode === 'write' ? 'warning' : undefined">mdi-pencil-plus</v-icon>
            {{ t('smartQueryView.mode.write') }}
          </v-btn>
          <v-btn value="plan" min-width="110">
            <v-icon start :color="mode === 'plan' ? 'info' : undefined">mdi-lightbulb-on</v-icon>
            {{ t('smartQueryView.mode.plan') }}
          </v-btn>
        </v-btn-toggle>
        <div class="mode-toggle-hint text-caption text-medium-emphasis">
          {{ hint }}
        </div>
      </div>

      <v-btn
        icon
        variant="tonal"
        :color="showHistory ? 'primary' : undefined"
        @click="$emit('update:showHistory', !showHistory)"
      >
        <v-badge
          v-if="favoriteCount > 0"
          :content="favoriteCount"
          color="warning"
          floating
        >
          <v-icon>mdi-history</v-icon>
        </v-badge>
        <v-icon v-else>mdi-history</v-icon>
        <v-tooltip activator="parent" location="bottom">
          {{ t('smartQuery.history.title') }}
        </v-tooltip>
      </v-btn>
    </template>
  </PageHeader>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import PageHeader from '@/components/common/PageHeader.vue'
import type { QueryMode } from '@/composables/useSmartQuery'

interface Props {
  mode: QueryMode
  showHistory: boolean
  favoriteCount: number
  hint: string
  disabled?: boolean
}

defineProps<Props>()

defineEmits<{
  'update:mode': [mode: QueryMode]
  'update:showHistory': [value: boolean]
}>()

const { t } = useI18n()
</script>

<style scoped>
.mode-toggle-block {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.mode-toggle-hint {
  max-width: 320px;
  line-height: 1.35;
}

.mode-toggle {
  border-radius: 12px !important;
  overflow: hidden;
}

@media (max-width: 768px) {
  .mode-toggle-block {
    align-items: center;
    text-align: center;
  }

  .mode-toggle-hint {
    max-width: 100%;
  }
}
</style>
