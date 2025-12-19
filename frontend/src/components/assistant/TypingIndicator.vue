<template>
  <div class="typing-indicator">
    <div class="typing-indicator__content">
      <v-avatar size="28" color="primary" class="mr-2">
        <v-icon size="16" color="on-primary">mdi-robot-happy</v-icon>
      </v-avatar>
      <div class="typing-indicator__dots">
        <span></span>
        <span></span>
        <span></span>
      </div>
      <span v-if="showText" class="typing-indicator__text ml-2">{{ text }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  text?: string
  showText?: boolean
}>()
</script>

<style scoped>
.typing-indicator {
  display: flex;
  padding: 12px 16px;
}

.typing-indicator__content {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background: rgb(var(--v-theme-surface-variant));
  border-radius: 16px;
  border-top-left-radius: 4px;
}

.typing-indicator__dots {
  display: flex;
  gap: 4px;
  align-items: center;
}

.typing-indicator__dots span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgb(var(--v-theme-primary));
  animation: typing-bounce 1.4s infinite ease-in-out both;
}

.typing-indicator__dots span:nth-child(1) {
  animation-delay: -0.32s;
}

.typing-indicator__dots span:nth-child(2) {
  animation-delay: -0.16s;
}

.typing-indicator__dots span:nth-child(3) {
  animation-delay: 0s;
}

.typing-indicator__text {
  font-size: 0.875rem;
  color: rgb(var(--v-theme-on-surface-variant));
}

@keyframes typing-bounce {
  0%, 80%, 100% {
    transform: scale(0.6);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}
</style>
