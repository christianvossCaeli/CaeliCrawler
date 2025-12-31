<template>
  <v-container class="fill-height" fluid>
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="6" lg="4">
        <v-card class="text-center pa-6">
          <v-icon
            size="80"
            color="error"
            class="mb-4"
          >
            mdi-shield-lock
          </v-icon>

          <v-card-title class="text-h4 mb-2">
            {{ $t('forbidden.title') }}
          </v-card-title>

          <v-card-subtitle class="text-body-1 mb-4">
            {{ $t('forbidden.subtitle') }}
          </v-card-subtitle>

          <v-card-text class="text-medium-emphasis">
            {{ $t('forbidden.message') }}
          </v-card-text>

          <v-card-text v-if="attemptedPath" class="text-caption text-medium-emphasis mt-2">
            {{ $t('forbidden.attemptedPath') }}: <code>{{ attemptedPath }}</code>
          </v-card-text>

          <v-card-actions class="justify-center mt-4 flex-wrap ga-2">
            <v-btn
              v-if="canGoBack"
              color="secondary"
              variant="tonal"
              prepend-icon="mdi-arrow-left"
              @click="goBack"
            >
              {{ $t('common.back') }}
            </v-btn>
            <v-btn
              color="primary"
              variant="elevated"
              :to="{ name: 'dashboard' }"
              prepend-icon="mdi-home"
            >
              {{ $t('forbidden.backToDashboard') }}
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

// Get the path the user attempted to access
const attemptedPath = computed(() => {
  const from = route.query.from
  return typeof from === 'string' ? from : null
})

// Check if we can go back in history (not from a direct navigation)
const canGoBack = computed(() => {
  return window.history.length > 2
})

const goBack = () => {
  router.back()
}
</script>
