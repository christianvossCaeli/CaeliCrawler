<template>
  <v-menu>
    <template v-slot:activator="{ props }">
      <v-btn
        icon
        v-bind="props"
        :title="$t('user.language')"
        variant="tonal"
      >
        <v-icon>mdi-translate</v-icon>
      </v-btn>
    </template>
    <v-list density="compact" min-width="150">
      <v-list-item
        v-for="lang in languages"
        :key="lang.code"
        :active="currentLocale === lang.code"
        @click="changeLanguage(lang.code)"
      >
        <template v-slot:prepend>
          <span class="language-flag">{{ lang.flag }}</span>
        </template>
        <v-list-item-title>{{ lang.name }}</v-list-item-title>
        <template v-slot:append>
          <v-icon v-if="currentLocale === lang.code" size="small" color="primary">
            mdi-check
          </v-icon>
        </template>
      </v-list-item>
    </v-list>
  </v-menu>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useLocale } from 'vuetify'
import { setLocale, type SupportedLocale } from '@/locales'
import { useAuthStore } from '@/stores/auth'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger('LanguageSwitcher')

const { locale } = useI18n()
const vuetifyLocale = useLocale()
const auth = useAuthStore()

interface Language {
  code: SupportedLocale
  name: string
  flag: string
}

const languages: Language[] = [
  { code: 'de', name: 'Deutsch', flag: '🇩🇪' },
  { code: 'en', name: 'English', flag: '🇬🇧' },
]

const currentLocale = computed(() => locale.value as SupportedLocale)

async function changeLanguage(code: SupportedLocale) {
  // Update vue-i18n locale
  locale.value = code

  // Update Vuetify locale
  vuetifyLocale.current.value = code

  // Persist to localStorage and update HTML lang
  setLocale(code)

  // Update user preference in backend if logged in
  if (auth.isAuthenticated) {
    try {
      await auth.updateLanguage(code)
    } catch (error) {
      logger.error('Failed to save language preference:', error)
    }
  }
}
</script>

<style scoped>
.language-flag {
  font-size: 1.2rem;
  margin-right: 8px;
}
</style>
