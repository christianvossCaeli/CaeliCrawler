<template>
  <div class="chat-welcome">
    <div class="chat-welcome__icon">
      <v-icon>mdi-chat-processing-outline</v-icon>
    </div>
    <h1 class="chat-welcome__greeting">{{ greeting }}</h1>
    <p class="chat-welcome__subtitle">{{ t('chatHome.welcome.subtitle') }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'

const { t } = useI18n()
const auth = useAuthStore()

const greeting = computed(() => {
  const hour = new Date().getHours()
  const name = auth.user?.full_name || auth.user?.email || ''
  const firstName = name.split(' ')[0].split('@')[0] // Handle email case

  let timeGreeting: string
  if (hour >= 5 && hour < 12) {
    timeGreeting = t('chatHome.welcome.morning')
  } else if (hour >= 12 && hour < 18) {
    timeGreeting = t('chatHome.welcome.afternoon')
  } else {
    timeGreeting = t('chatHome.welcome.evening')
  }

  return firstName ? `${timeGreeting}, ${firstName}` : timeGreeting
})
</script>
