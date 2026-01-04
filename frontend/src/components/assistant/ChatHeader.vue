<template>
  <div class="chat-header">
    <div class="chat-header__left">
      <v-icon class="mr-2">mdi-robot-happy</v-icon>
      <span class="chat-header__title">{{ t('assistant.title') }}</span>
    </div>

    <div class="chat-header__right">
      <!-- Mode Toggle -->
      <div class="mode-toggle mode-toggle--triple" role="group" :aria-label="t('assistant.modeToggle')">
        <button
          :class="{ active: mode === 'read' }"
          :title="t('assistant.modeRead')"
          :aria-label="t('assistant.modeRead')"
          :aria-pressed="mode === 'read'"
          @click="$emit('update:mode', 'read')"
        >
          <v-icon size="18">mdi-magnify</v-icon>
        </button>
        <button
          :class="{ active: mode === 'write' }"
          :title="t('assistant.modeWrite')"
          :aria-label="t('assistant.modeWrite')"
          :aria-pressed="mode === 'write'"
          @click="$emit('update:mode', 'write')"
        >
          <v-icon size="18">mdi-pencil</v-icon>
        </button>
        <button
          :class="{ active: mode === 'plan' }"
          :title="t('assistant.modePlan')"
          :aria-label="t('assistant.modePlan')"
          :aria-pressed="mode === 'plan'"
          @click="$emit('update:mode', 'plan')"
        >
          <v-icon size="18">mdi-lightbulb-on</v-icon>
        </button>
      </div>

      <button class="header-btn" :title="t('assistant.clear')" :aria-label="t('assistant.clear')" @click="$emit('clear')">
        <v-icon size="small">mdi-refresh</v-icon>
      </button>

      <button class="header-btn" :title="t('assistant.close')" :aria-label="t('assistant.close')" @click="$emit('close')">
        <v-icon size="small">mdi-close</v-icon>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

defineProps<{
  mode: 'read' | 'write' | 'plan'
}>()

defineEmits<{
  'update:mode': [mode: 'read' | 'write' | 'plan']
  clear: []
  close: []
}>()

const { t } = useI18n()
</script>

<style scoped>
@import './styles/chat-assistant.css';
</style>
