<template>
  <v-container class="fill-height" fluid>
    <v-row justify="center" align="center">
      <v-col cols="12" sm="8" md="5" lg="4">
        <v-card class="pa-6 elevation-8">
          <!-- Logo and Title -->
          <v-card-title class="text-center mb-4">
            <div class="d-flex flex-column align-center">
              <v-icon size="64" color="primary" class="mb-2">
                mdi-wind-turbine
              </v-icon>
              <span class="text-h4 font-weight-bold text-primary">
                CaeliCrawler
              </span>
              <span class="text-body-2 text-medium-emphasis mt-1">
                {{ $t('auth.loginSubtitle') }}
              </span>
            </div>
          </v-card-title>

          <v-divider class="mb-6" />

          <v-card-text>
            <v-form @submit.prevent="handleLogin" ref="formRef">
              <!-- Email Field -->
              <v-text-field
                v-model="email"
                :label="$t('auth.email')"
                type="email"
                prepend-inner-icon="mdi-email-outline"
                :rules="emailRules"
                :disabled="isLoading"
                variant="outlined"
                density="comfortable"
                class="mb-4"
                autocomplete="email"
                @keyup.enter="handleLogin"
              />

              <!-- Password Field -->
              <v-text-field
                v-model="password"
                :label="$t('auth.password')"
                :type="showPassword ? 'text' : 'password'"
                prepend-inner-icon="mdi-lock-outline"
                :append-inner-icon="showPassword ? 'mdi-eye-off' : 'mdi-eye'"
                @click:append-inner="showPassword = !showPassword"
                :rules="passwordRules"
                :disabled="isLoading"
                variant="outlined"
                density="comfortable"
                class="mb-4"
                autocomplete="current-password"
                @keyup.enter="handleLogin"
              />

              <!-- Error Alert -->
              <v-alert
                v-if="errorMessage"
                type="error"
                variant="tonal"
                class="mb-4"
                closable
                @click:close="errorMessage = null"
              >
                {{ errorMessage }}
              </v-alert>

              <!-- Login Button -->
              <v-btn
                type="submit"
                color="primary"
                size="large"
                block
                :loading="isLoading"
                :disabled="!isFormValid"
                class="mt-2"
              >
                <v-icon start>mdi-login</v-icon>
                {{ $t('auth.login') }}
              </v-btn>
            </v-form>
          </v-card-text>

          <!-- Footer -->
          <v-card-actions class="justify-center pt-4">
            <span class="text-caption text-medium-emphasis">
              &copy; {{ currentYear }} Caeli Wind
            </span>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const { t } = useI18n()

// Form state
const formRef = ref<any>(null)
const email = ref('')
const password = ref('')
const showPassword = ref(false)
const isLoading = ref(false)
const errorMessage = ref<string | null>(null)

// Computed
const currentYear = computed(() => new Date().getFullYear())

const isFormValid = computed(() => {
  return email.value.length > 0 && password.value.length > 0
})

// Validation rules
const emailRules = computed(() => [
  (v: string) => !!v || t('auth.validation.emailRequired'),
  (v: string) => /.+@.+\..+/.test(v) || t('auth.validation.emailInvalid'),
])

const passwordRules = computed(() => [
  (v: string) => !!v || t('auth.validation.passwordRequired'),
])

// Login handler
async function handleLogin() {
  if (!isFormValid.value) return

  isLoading.value = true
  errorMessage.value = null

  const success = await auth.login(email.value, password.value)

  if (success) {
    // Redirect to intended page or dashboard
    const redirectPath = route.query.redirect as string || '/'
    await router.push(redirectPath)
  } else {
    errorMessage.value = auth.error || t('auth.loginFailed')
  }

  isLoading.value = false
}
</script>

<style scoped>
.fill-height {
  min-height: 100vh;
}
</style>
