<template>
  <v-btn
    :icon="isOpen ? 'mdi-close' : 'mdi-robot-happy'"
    :color="isOpen ? 'grey' : 'primary'"
    size="large"
    class="chat-bubble"
    :class="{ 'chat-bubble--open': isOpen, 'chat-bubble--pulse': hasUnread && !isOpen }"
    elevation="8"
    @click="$emit('toggle')"
  >
    <v-badge
      v-if="hasUnread && !isOpen"
      color="error"
      dot
      floating
    >
      <v-icon>mdi-robot-happy</v-icon>
    </v-badge>
    <v-icon v-else>{{ isOpen ? 'mdi-close' : 'mdi-robot-happy' }}</v-icon>

    <v-tooltip activator="parent" location="left">
      {{ isOpen ? t('assistant.close') : t('assistant.open') }}
    </v-tooltip>
  </v-btn>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

defineProps<{
  isOpen: boolean
  hasUnread: boolean
}>()

defineEmits<{
  toggle: []
}>()

const { t } = useI18n()

</script>

<style scoped>
.chat-bubble {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 2401;
  transition: all 0.3s ease;
}

.chat-bubble--open {
  transform: rotate(90deg);
}

.chat-bubble--pulse {
  animation: pulse-bubble 2s ease-in-out infinite;
}

@keyframes pulse-bubble {
  0%, 100% {
    box-shadow: 0 4px 20px rgba(var(--v-theme-primary), 0.4);
  }
  50% {
    box-shadow: 0 4px 30px rgba(var(--v-theme-primary), 0.7);
  }
}

/* Mobile adjustments */
@media (max-width: 600px) {
  .chat-bubble {
    bottom: 16px;
    right: 16px;
  }
}
</style>
