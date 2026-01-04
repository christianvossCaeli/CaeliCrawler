<template>
  <div
    class="generated-prompt-section"
    role="region"
    :aria-label="t('smartQueryView.plan.generatedPromptAriaLabel', 'Generierter Prompt')"
  >
    <v-card
      ref="cardRef"
      class="generated-prompt-card"
      color="success"
      variant="tonal"
      tabindex="-1"
    >
      <v-card-title class="d-flex align-center">
        <v-icon start aria-hidden="true">mdi-check-circle</v-icon>
        {{ t('smartQueryView.plan.generatedPrompt') }}
      </v-card-title>
      <v-card-text>
        <v-card variant="outlined" class="prompt-preview mb-4">
          <v-card-text class="text-body-1 font-weight-medium">
            {{ prompt.prompt }}
          </v-card-text>
        </v-card>

        <!-- Validation Result Display -->
        <v-expand-transition>
          <div v-if="validationResult" class="validation-result mb-4">
            <v-alert
              :type="validationResult.valid ? 'success' : 'warning'"
              variant="tonal"
              density="compact"
              class="mb-2"
            >
              <template #title>
                {{ validationResult.valid
                  ? t('smartQueryView.plan.validation.valid', 'Prompt ist gültig')
                  : t('smartQueryView.plan.validation.invalid', 'Prompt hat Probleme')
                }}
              </template>
              <template v-if="validationResult.preview" #text>
                <strong>{{ t('smartQueryView.plan.validation.preview', 'Vorschau') }}:</strong>
                {{ validationResult.preview }}
              </template>
            </v-alert>

            <!-- Warnings -->
            <v-alert
              v-for="(warning, idx) in validationResult.warnings"
              :key="idx"
              type="warning"
              variant="text"
              density="compact"
              class="mb-1"
            >
              {{ warning }}
            </v-alert>
          </div>
        </v-expand-transition>

        <div class="d-flex ga-2 flex-wrap" role="group" :aria-label="t('smartQueryView.plan.adoptActionsAriaLabel', 'Prompt-Aktionen')">
          <!-- Test Button -->
          <v-btn
            variant="outlined"
            color="info"
            :loading="validating"
            :aria-label="t('smartQueryView.plan.testPromptAriaLabel', 'Prompt testen')"
            @click="$emit('validate', prompt.prompt, prompt.suggested_mode || 'read')"
          >
            <v-icon start aria-hidden="true">mdi-test-tube</v-icon>
            {{ t('smartQueryView.plan.testPrompt', 'Testen') }}
          </v-btn>

          <v-btn
            v-if="prompt.suggested_mode === 'read' || !prompt.suggested_mode"
            color="primary"
            variant="elevated"
            :aria-label="t('smartQueryView.plan.adoptToReadAriaLabel', 'Prompt im Lese-Modus ausführen')"
            @click="$emit('adopt', prompt.prompt, 'read')"
          >
            <v-icon start aria-hidden="true">mdi-magnify</v-icon>
            {{ t('smartQueryView.plan.adoptToRead') }}
          </v-btn>
          <v-btn
            v-if="prompt.suggested_mode === 'write' || !prompt.suggested_mode"
            color="warning"
            variant="elevated"
            :aria-label="t('smartQueryView.plan.adoptToWriteAriaLabel', 'Prompt im Schreib-Modus ausführen')"
            @click="$emit('adopt', prompt.prompt, 'write')"
          >
            <v-icon start aria-hidden="true">mdi-pencil-plus</v-icon>
            {{ t('smartQueryView.plan.adoptToWrite') }}
          </v-btn>
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'

interface GeneratedPrompt {
  prompt: string
  suggested_mode?: 'read' | 'write'
}

interface ValidationResult {
  valid: boolean
  mode: string
  interpretation: Record<string, unknown> | null
  preview: string | null
  warnings: string[]
  original_prompt: string
}

const props = defineProps<{
  prompt: GeneratedPrompt
  validating?: boolean
  validationResult?: ValidationResult | null
}>()

defineEmits<{
  validate: [prompt: string, mode: 'read' | 'write']
  adopt: [prompt: string, mode: 'read' | 'write']
}>()

const { t } = useI18n()

const cardRef = ref<HTMLElement | null>(null)

// Focus the card when it appears
watch(() => props.prompt, async () => {
  await nextTick()
  if (cardRef.value) {
    (cardRef.value as HTMLElement).focus?.()
  }
}, { immediate: true })

defineExpose({
  focus: () => cardRef.value?.focus?.()
})
</script>

<style scoped>
.generated-prompt-section {
  padding: 0 16px;
}

.generated-prompt-card {
  border-radius: 12px !important;
}

.prompt-preview {
  background: rgba(var(--v-theme-surface), 0.9) !important;
}

.validation-result {
  margin-top: 8px;
}

@media (max-width: 600px) {
  .generated-prompt-section {
    padding: 0 12px;
  }

  .generated-prompt-card .v-card-text {
    padding: 12px;
  }

  .generated-prompt-card .d-flex {
    flex-direction: column;
  }

  .generated-prompt-card .v-btn {
    width: 100%;
  }
}
</style>
