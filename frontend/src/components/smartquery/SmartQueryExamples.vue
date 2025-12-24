<template>
  <div class="examples-section">
    <div class="d-flex align-center mb-4">
      <v-icon class="mr-2" :color="writeMode ? 'warning' : 'primary'">mdi-lightbulb-outline</v-icon>
      <span class="text-subtitle-1 font-weight-medium">
        {{ writeMode ? t('smartQueryView.examples.commandsTitle') : t('smartQueryView.examples.questionsTitle') }}
      </span>
    </div>
    <div class="examples-grid">
      <v-card
        v-for="example in examples"
        :key="example.question"
        class="example-card"
        :class="{ 'example-card--write': writeMode }"
        @click="$emit('select', example.question)"
        hover
        variant="outlined"
      >
        <v-card-text class="example-card-content pa-4">
          <div class="example-main">
            <v-avatar
              :color="writeMode ? 'warning' : 'primary'"
              size="44"
              class="example-avatar"
              variant="tonal"
            >
              <v-icon size="22">{{ example.icon }}</v-icon>
            </v-avatar>
            <div class="example-text-block">
              <div class="text-body-2 font-weight-medium example-title">{{ example.title }}</div>
              <div class="text-caption text-medium-emphasis example-question">{{ example.question }}</div>
            </div>
          </div>
          <v-icon size="18" class="example-arrow" color="grey">mdi-arrow-right</v-icon>
        </v-card-text>
      </v-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

interface Example {
  question: string
  icon: string
  title: string
}

defineProps<{
  examples: Example[]
  writeMode: boolean
}>()

defineEmits<{
  select: [question: string]
}>()

const { t } = useI18n()
</script>

<style scoped>
.examples-section {
  animation: fadeIn 0.3s ease;
}

.examples-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(280px, 100%), 1fr));
  gap: 12px;
}

.example-card {
  cursor: pointer;
  transition: all 0.2s ease;
  border-radius: 12px !important;
  display: flex;
  align-items: center;
}

.example-card:hover {
  transform: translateY(-2px);
  border-color: rgba(var(--v-theme-primary), 0.4) !important;
}

.example-card--write:hover {
  border-color: rgba(var(--v-theme-warning), 0.4) !important;
}

.example-card-content {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding-right: 40px;
  flex: 1 1 auto;
  width: 100%;
}

.example-main {
  display: flex;
  align-items: center;
  gap: 12px;
  max-width: 100%;
}

.example-avatar {
  transition: transform 0.2s ease;
}

.example-text-block {
  min-width: 0;
}

.example-title,
.example-question {
  white-space: normal;
  overflow-wrap: anywhere;
}

.example-card:hover .example-avatar {
  transform: scale(1.05);
}

.example-arrow {
  position: absolute;
  right: 16px;
  top: 50%;
  opacity: 0;
  transform: translateY(-50%) translateX(-4px);
  transition: all 0.2s ease;
}

.example-card:hover .example-arrow {
  opacity: 1;
  transform: translateY(-50%) translateX(0);
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@media (max-width: 768px) {
  .examples-grid {
    grid-template-columns: 1fr;
  }
}
</style>
